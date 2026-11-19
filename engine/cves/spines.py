"""Timeline spines: what drives the length and the cut points of an edit (docs/FORMATS.md).

    edit.yaml  spine: aroll | voiceover | music | broll        (default aroll: today's talking-head path)

  aroll      the presenter's takes (selects.yaml -> edl.json segments, plates, mattes, faces). The `broll:` track, when
             present, adds cutaway footage over the A-roll (compiled to `broll_shot` cutaways).
  voiceover  a VO file (recorded, or ElevenLabs-generated and registered with `cves assets add`) is the spine: ingest
             tightens its pauses into voice_final.wav and transcribes it into words.json (cut time). The picture is the
             `broll:` track, written by Claude against words.json. Captions come from the VO words.
  music      no voice. Length = edit.yaml `duration`, else the music track. Cut points come from Edit/beats.json:
             `cves autocut` proposes a broll: track snapped to beats / downbeats / bars. Captions off (text cards are
             cutaways).
  broll      a shot-led edit: the broll: track with optional native clip audio (`audio: true`) and an optional music bed.
             Length = `duration`, else the end of the track.

The broll: track (cut-time seconds; shots tile the timeline on the non-aroll spines):
    broll:
      - {src: Raw/city.mp4, start: 0.0, end: 2.4, in: 3.0}                       # fill (crop to the canvas) is the default
      - {asset: hero_img, start: 2.4, end: 4.0, framing: kenburns, kenburns: {zoom: [1.0, 1.12], pan: [0.3, 0]}}
      - {src: Raw/talk.mov, start: 4.0, end: 6.2, in: 12.5, framing: fit, speed: 0.5, audio: true, gain: -14}
  src | asset   a footage path (project-relative) or an asset id (edit.yaml assets: / Edit/assets.json)
  start, end    cut time; in = source seconds where the shot starts (default 0); speed = constant source speed (default 1)
  framing       fill (cover-crop to the canvas) | fit (whole picture on a blurred, dimmed fill of itself) | kenburns
                (fill + a slow zoom; stills default to kenburns); `kenburns: {zoom: [a, b], pan: [x, y] | [[x0, y0], [x1, y1]]}`
  anchor        [x, y] 0..1: the point of the source a fill crop keeps centred (default [0.5, 0.5])
  after         hold (default) | loop: what a source shorter than its shot does
  transition    cut (default) | whip | glitch | fade into this shot; audio / gain: the clip's own sound in the mix
Any size, rotation and frame rate of source works: shots are decoded with PyAV (rotation applied) and sampled by time."""
import os, re, json, math, shutil, datetime
from fractions import Fraction

SPINES = ("aroll", "voiceover", "music", "broll")
FRAMINGS = ("fill", "fit", "kenburns")
STILL_EXT = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif")
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".m4v", ".mts", ".m2ts", ".avi", ".webm", ".mxf")


def spine_of(E):
    s = str((E or {}).get("spine") or "aroll").strip().lower()
    if s not in SPINES: raise SystemExit(f"edit.yaml spine: '{s}' is not one of {', '.join(SPINES)}")
    return s

def has_voice(spine): return spine in ("aroll", "voiceover")
def has_aroll(spine): return spine == "aroll"


# ------------------------------------------------------------------ the broll: track
def ref_of(x):
    """the source reference of a shot: asset id or path"""
    return x.get("asset") or x.get("src")

def shots(E, fps, S=None, pr=None):
    """edit.yaml broll: -> normalised, frame-snapped shots (sorted by start). pr resolves asset ids (stills default to kenburns)"""
    out = []
    kb_default = (S.get("broll.ken_burns", None) if S is not None else None) or [1.0, 1.08]
    for j, x in enumerate(E.get("broll") or []):
        if not isinstance(x, dict): raise SystemExit(f"broll[{j}]: expected a mapping {{src|asset, start, end}}")
        ref = ref_of(x)
        if not ref: raise SystemExit(f"broll[{j}]: needs src (a footage path) or asset (an asset id)")
        a, b = round(float(x["start"]) * fps) / fps, round(float(x["end"]) * fps) / fps
        if b <= a: raise SystemExit(f"broll[{j}]: end {x['end']} is not after start {x['start']} (after frame snapping)")
        still = str((_path(pr, ref) if pr is not None else None) or ref).lower().endswith(STILL_EXT)
        fr = x.get("framing") or ("kenburns" if still else ((S.get("broll.framing", "fill") if S is not None else "fill")))
        if fr not in FRAMINGS: raise SystemExit(f"broll[{j}].framing: '{fr}' is not one of {', '.join(FRAMINGS)}")
        kb = x.get("kenburns") or ({"zoom": kb_default} if fr == "kenburns" else None)
        out.append({"id": str(x.get("id") or f"b{j + 1:02d}"), "ref": ref, "start": a, "end": b, "in": float(x.get("in", 0) or 0),
                    "speed": float(x.get("speed", 1) or 1), "framing": "fit" if fr == "fit" else "fill", "kenburns": kb,
                    "anchor": x.get("anchor"), "after": x.get("after", "hold"), "transition": x.get("transition", "cut"),
                    "audio": bool(x.get("audio")), "gain": x.get("gain"), "snap": x.get("snap"), "index": j,
                    "ramp": x.get("ramp"), "camera": x.get("camera"), "match": x.get("match"), "out": x.get("out"), "depth": x.get("depth")})
    out.sort(key=lambda s: s["start"])
    return out

def shot_params(sh):
    """the broll_shot template params of a shot"""
    p = {"asset": sh["ref"], "in": sh["in"], "speed": sh["speed"], "framing": sh["framing"], "after": sh["after"], "name": f"broll.{sh['id']}"}
    if sh.get("kenburns"): p["kenburns"] = sh["kenburns"]
    if sh.get("anchor"): p["anchor"] = sh["anchor"]
    for k in ("ramp", "camera", "out", "depth"):          # motion craft (docs/MOTION.md "Craft")
        if sh.get(k) is not None: p[k] = sh[k]
    if sh.get("audio"):
        p["audio"] = True
        if sh.get("gain") is not None: p["gain"] = sh["gain"]
    return p

def cutaways(shs, aroll):
    """shots -> Timeline cutaway entries (flagged broll: True). On the aroll spine they snap to segment boundaries
    like any cutaway unless the shot says snap: false; on the other spines they never snap."""
    out = []
    for j, sh in enumerate(shs):
        p = shot_params(sh); prev = shs[j - 1] if j else None
        if sh.get("match") and prev is not None and abs(prev["end"] - sh["start"]) < 1e-6:     # match cut: line up on the outgoing shot
            p["match"] = sh["match"] if isinstance(sh["match"], dict) else {"mode": sh["match"] if isinstance(sh["match"], str) else None}
            p["match_prev"] = {"params": shot_params(prev), "start": prev["start"], "end": prev["end"]}
        out.append({"id": sh["id"], "template": "broll_shot", "start": sh["start"], "end": sh["end"], "params": p,
                    "in": sh["transition"], "out": "cut", "broll": True,
                    "snap": (sh["snap"] if sh["snap"] is not None else True) if aroll else False})
    return out

def _shot_out(sh, dur, S=None):
    """source seconds where a shot ends: its explicit out, else in + what its speed (or its ramp) consumes"""
    if sh.get("out") is not None: return float(sh["out"])
    if sh.get("ramp"):
        from . import craft as CR
        return sh["in"] + CR.ramp_span(dur, sh["ramp"], S, sh["speed"])
    return sh["in"] + dur * sh["speed"]

def tiles(shs, T, fps, S=None):
    """picture segments of a non-aroll timeline: one per shot plus 'gap' segments where nothing is scheduled.
    Returns [{id, kind: broll|gap, f0, n, t0, t1, in, out, src, clip}]"""
    segs, f = [], 0; N = int(round(T * fps)); k = 0
    for sh in shs:
        a, b = int(round(sh["start"] * fps)), min(N, int(round(sh["end"] * fps)))
        if a >= N: break
        if a < f: a = f                                       # overlap: the later shot wins from where the earlier one ends
        if a > f: segs.append({"id": f"gap{k}", "kind": "gap", "f0": f, "n": a - f}); k += 1
        if b > a:
            segs.append({"id": sh["id"], "kind": "broll", "f0": a, "n": b - a, "src": sh["ref"], "clip": sh["id"],
                         "in": round(sh["in"], 5), "out": round(_shot_out(sh, (b - a) / fps, S), 5)})
            f = b
    if f < N: segs.append({"id": f"gap{k}", "kind": "gap", "f0": f, "n": N - f})
    for s in segs:
        s["t0"], s["t1"] = s["f0"] / fps, (s["f0"] + s["n"]) / fps
        s.setdefault("in", 0.0); s.setdefault("out", 0.0); s.setdefault("clip", s["id"])
    return segs


# ------------------------------------------------------------------ length and rate of a non-aroll timeline
def _path(pr, ref):
    if not ref: return None
    try:
        from . import assets as AS
        p = AS.resolve(pr, ref, strict=False)
        if p: return p
    except (ImportError, SystemExit): pass
    q = ref if os.path.isabs(ref) else pr.p(ref)
    return q if os.path.exists(q) else None

def voiceover_file(pr, E=None):
    E = E if E is not None else pr.edit; V = E.get("voiceover") or {}
    ref = V.get("asset") or V.get("file")
    if not ref: raise SystemExit("spine: voiceover needs edit.yaml voiceover: {file: <path>} or {asset: <id>} (register an ElevenLabs VO with `cves assets add`)")
    p = _path(pr, ref)
    if not p: raise SystemExit(f"voiceover: {ref} not found (a project-relative path or a registered asset id)")
    return p

def _audio_dur(path):
    try:
        import soundfile as sf; return sf.info(path).duration
    except Exception:
        from . import assets as AS
        return float(AS.probe(path).get("duration") or 0)

def duration(pr, spine, E=None, fps=None):
    """timeline length (s) of a non-aroll spine, before the end card"""
    E = E if E is not None else pr.edit
    if spine == "voiceover":
        vf = pr.e("voice_final.wav")
        if not os.path.exists(vf): raise SystemExit("spine voiceover: Edit/voice_final.wav missing: run `cves ingest` (it tightens and transcribes the VO)")
        return _audio_dur(vf)
    if E.get("duration"): return float(E["duration"])
    if spine == "music":
        from . import beats as BT
        mf = BT.music_file(pr)
        if not mf: raise SystemExit("spine music: set music.file (the track that drives the cut) or edit.yaml duration")
        return _audio_dur(mf)
    shs = E.get("broll") or []
    if not shs: raise SystemExit("spine broll: the broll: track is empty (or set edit.yaml duration)")
    return max(float(x["end"]) for x in shs if isinstance(x, dict) and "end" in x)

def project_rate(pr, S, E=None):
    """the frame rate of a non-aroll timeline: style platform.fps, else the first video shot / Raw video, else 30"""
    from . import ingest as ING
    r = ING._rational(S.get("platform.fps", "source"))
    if r: return r
    E = E if E is not None else pr.edit
    cands = [_path(pr, ref_of(x)) for x in (E.get("broll") or []) if isinstance(x, dict)]
    if os.path.isdir(pr.p("Raw")): cands += [pr.p("Raw", f) for f in sorted(os.listdir(pr.p("Raw"))) if f.lower().endswith(VIDEO_EXT)]
    for p in cands:
        if p and p.lower().endswith(VIDEO_EXT):
            try: return ING.source_rate(ING.probe_file(p))
            except SystemExit: continue
    return Fraction(30, 1)

def sync_edl(pr, S=None, force=False):
    """Edit/edl.json for a non-aroll spine: {spine, fps, fps_rational, size, duration, clips, segments: []}. The picture
    segments live in the broll: track (render builds them); edl.json carries the rate and the canvas. Idempotent."""
    from . import style as STY, gfx as G
    E = pr.edit; spine = spine_of(E); S = S or STY.load(pr)
    old = pr.json("edl.json", {}) or {}
    if old.get("spine") == spine and old.get("fps") and not force:
        fr = Fraction(*old["fps_rational"]) if old.get("fps_rational") else Fraction(old["fps"]).limit_denominator(1001)
    else: fr = project_rate(pr, S, E)
    edl = dict(old) if old.get("spine") == spine else {}
    edl.update({"spine": spine, "fps": float(fr), "fps_rational": [fr.numerator, fr.denominator], "size": list(G.canvas_of(S, pr)),
                "segments": [], "clips": edl.get("clips", [])})
    try: edl["duration"] = round(duration(pr, spine, E), 5)
    except SystemExit: edl.pop("duration", None)
    if edl != old: pr.save_json("edl.json", edl)
    return edl


# ------------------------------------------------------------------ voiceover ingest
VO_INGEST_VERSION = 1

def vo_signature(pr, E=None):
    """what voice_final.wav was made from: the VO file's sha256 + the voiceover settings. ingest_voiceover skips its work
    when edl.json records the same signature and the outputs exist (re-running `cves ingest` changes nothing)."""
    import hashlib
    E = E if E is not None else pr.edit; V = E.get("voiceover") or {}; src = voiceover_file(pr, E); h = hashlib.sha256()
    with open(src, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return {"version": VO_INGEST_VERSION, "source": os.path.relpath(src, pr.root).replace(os.sep, "/"), "sha256": h.hexdigest(),
            "denoise": bool(V.get("denoise", False)), "tighten": bool(V.get("tighten", True)), "chain": bool(V.get("chain", True))}

def ingest_voiceover(pr, words=True, force=False):
    """VO file -> Edit/voice_raw.wav (as recorded, 48 kHz mono), voice_final.wav (pauses tightened, optional DeepFilterNet,
    the voice chain), voice_chain.json, words.json (cut time, whisper) and edl.json. edit.yaml voiceover: {file | asset,
    denoise (false), tighten (true), chain (true)}."""
    import numpy as np, soundfile as sf
    from . import ingest as ING, config as C
    E = pr.edit; V = E.get("voiceover") or {}; src = voiceover_file(pr, E); SR = ING.SR
    sig = vo_signature(pr, E); old = pr.json("edl.json", {}) or {}
    if not force and old.get("vo_sig") == sig and all(os.path.exists(pr.e(f)) for f in ("voice_final.wav", "voice_raw.wav", "voice_chain.json")):
        sync_edl(pr)                                 # same VO, same settings: nothing to redo (idempotent)
        n = ING.words(pr) if words and not os.path.exists(pr.e("words.json")) else None
        return {"skipped": "voice_final.wav is current (same VO file and voiceover settings)", "words": n}
    raw = pr.e("voice_raw.wav")
    ING.sh([C.get("ffmpeg"), "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), raw])
    steps = [{"name": "extract", "generative": False, "params": {"rate": SR, "channels": 1, "tool": "ffmpeg", "source": os.path.relpath(src, pr.root)}}]
    work = raw
    if V.get("denoise", False):
        os.makedirs(pr.e("voice", "df"), exist_ok=True)
        ING.sh([C.get("deepfilter"), "-o", pr.e("voice", "df"), raw])
        hits = sorted(f for f in os.listdir(pr.e("voice", "df")) if f.startswith("voice_raw"))
        if not hits: raise SystemExit("DeepFilterNet produced no output for the VO: check `cves doctor` (or set voiceover.denoise: false)")
        work = pr.e("voice", "df", hits[-1]); steps.append({"name": "deepfilternet", "generative": False, "params": {"binary": os.path.basename(C.get("deepfilter"))}})
    y, sr = sf.read(work); y = y.mean(1) if y.ndim > 1 else y
    if sr != SR:
        import librosa
        y = librosa.resample(y, orig_sr=sr, target_sr=SR); sr = SR
    dur = len(y) / sr; kept = [(0.0, dur)]
    if V.get("tighten", True):
        kept = ING._tighten({"in": 0.0, "out": dur}, y, sr, 0.0) or [(0.0, dur)]
        steps.append({"name": "pause_tighten", "generative": False, "params": {"max_gap_s": ING.MAXGAP, "breath_s": ING.BREATH, "edge_s": ING.EDGE, "threshold_db_below_peak": 32}})
    parts = []; f = int(.008 * sr)
    for a, b in kept:
        seg = y[int(a * sr):int(b * sr)].copy()
        if len(seg) > 2 * f: seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        parts.append(seg)
    steps.append({"name": "crossfade", "generative": False, "params": {"ms": 8}})
    tight = pr.e("voice_tight.wav"); sf.write(tight, np.concatenate(parts) if parts else y, SR)
    if V.get("chain", True):
        ING.sh([C.get("ffmpeg"), "-v", "error", "-y", "-i", tight, "-af", ING.voice_af(), "-ar", str(SR), pr.e("voice_final.wav")])
        steps += [{"name": n, "generative": False, "params": dict(p, tool="ffmpeg")} for n, p in ING.VOICE_CHAIN]
    else: shutil.copyfile(tight, pr.e("voice_final.wav"))
    pr.save_json("voice_chain.json", {"steps": steps, "output": "voice_final.wav"})
    edl = sync_edl(pr, force=True)
    edl["clips"] = [{"id": "vo", "in": 0.0, "out": round(dur, 5), "src": os.path.relpath(src, pr.root)}]
    edl["vo_kept"] = [[round(a, 5), round(b, 5)] for a, b in kept]; edl["vo_sig"] = sig
    pr.save_json("edl.json", edl)
    n = ING.words(pr) if words else None
    return {"vo_s": round(dur, 2), "tight_s": round(sum(b - a for a, b in kept), 2), "pieces": len(kept), "words": n}

def ingest_spine(pr, words=True):
    """`cves ingest` on a non-aroll spine: voiceover -> ingest_voiceover; music / broll -> edl.json (rate + canvas)"""
    sp = spine_of(pr.edit)
    if sp == "voiceover": return ingest_voiceover(pr, words=words)
    e = sync_edl(pr, force=True); return {"spine": sp, "fps": e["fps"], "size": e["size"], "duration": e.get("duration")}


# ------------------------------------------------------------------ autocut: a broll: track snapped to the music
def _media_in(folder):
    out = []
    for f in sorted(os.listdir(folder)):
        if f.startswith("."): continue
        if f.lower().endswith(VIDEO_EXT + STILL_EXT): out.append(os.path.join(folder, f))
    return out

def autocut(pr, every="downbeats", min_shot=None, folder=None, bars=2, max_shots=None):
    """propose a broll: track whose cuts land on the music grid (cut time, from beats.plan). every: beats | downbeats
    (every bar) | bars (every `bars` bars). min_shot: grid points closer than this to the previous cut are skipped.
    Clips come from `folder` (default Raw/), in name order, round-robin; a clip used again continues where it left off."""
    from . import beats as BT, render as R, assets as AS
    if every not in ("beats", "downbeats", "bars"): raise SystemExit("--every must be beats | downbeats | bars")
    if not BT.music_file(pr): raise SystemExit("autocut needs music: set music.file in edit.yaml (then `cves beats`)")
    TL = R.Timeline(pr); P = BT.plan(pr, TL, need_beats=True)
    if not P or not P.get("lay"): raise SystemExit("no beat grid: run `cves beats` first (music.fit bars needs the analysis)")
    T = TL.T_END; grid = P["beats"] if every == "beats" else P["downbeats"]
    if every == "bars": grid = grid[::max(1, int(bars))]
    min_shot = float(min_shot if min_shot is not None else (P["lay"]["bar_s"] / 2 if every == "beats" else 0.5))
    pts = [0.0]
    for g in sorted(grid):
        if g - pts[-1] >= min_shot - 1e-6 and T - g >= min_shot - 1e-6: pts.append(round(g, 4))
    pts.append(round(T, 4))
    if max_shots: pts = pts[:int(max_shots)] + [pts[-1]]
    folder = pr.p(folder or "Raw"); clips = _media_in(folder) if os.path.isdir(folder) else []
    if not clips: raise SystemExit(f"no clips in {folder}: put footage (or stills) there or pass --folder")
    durs = {}
    for c in clips:
        try: durs[c] = float(AS.probe(c).get("duration") or 0) or None
        except SystemExit: durs[c] = None
    cursor = {c: 0.0 for c in clips}; out = []
    for k, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        c = clips[k % len(clips)]; need = b - a; d = durs.get(c)
        start_in = cursor[c]
        if d and start_in + need > d: start_in = 0.0
        shot = {"src": os.path.relpath(c, pr.root).replace(os.sep, "/"), "start": round(a, 4), "end": round(b, 4)}
        if d is not None: shot["in"] = round(start_in, 3); cursor[c] = start_in + need
        else: shot["framing"] = "kenburns"
        out.append(shot)
    return out, {"every": every, "grid": len(grid), "shots": len(out), "min_shot": round(min_shot, 3), "tempo": (P.get("B") or {}).get("tempo"),
                 "cuts": pts[1:-1]}

def write_broll(pr, track):
    """replace edit.yaml broll: with `track` (a timestamped backup of edit.yaml first)"""
    f = pr.e("edit.yaml")
    if os.path.exists(f): shutil.copy2(f, f + datetime.datetime.now().strftime(".bak-%Y%m%d-%H%M%S"))
    E = pr.edit; E["broll"] = track; pr.save_edit(E)
