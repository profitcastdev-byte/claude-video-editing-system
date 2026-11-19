"""`cves review build|apply|signoff|show`: watch the render, not the plan (docs/REVIEW.md).

`cves review build [vNNN|master]` writes one review pack per round, `PROJECT/Edit/review/rNNN/`:
  cuts/cut_NN.jpg   one contact image per cut: the frames at style `review.cut_offsets` around it (0 = first frame after the cut)
  index.jpg         every cut on one sheet (last frame before | first frame after), flagged cuts marked
  hook.jpg          the first `review.hook_s` seconds at `review.hook_fps`
  payoff.jpg        frames across the payoff window (`structure.payoff_window`) before the end card
  endcard.jpg       the end card (entry, settle, middle, last frame)
  audio.json        loudness per section, vocal-to-music ratio (stems), clicks at cuts, silence gaps, `earshot measure`
  findings.json     [{id, severity: high|med|low, t, kind, message, patch?}]; `patch` = {set: {edit.yaml path: value}, safe}
  REVIEW.md         the facts, the findings and a rubric of questions Claude answers by looking at the images
`cves review apply` applies the safe patches of the latest round (edit.yaml backup kept) and records them.
`cves review signoff --verdict ship|revise --notes "..."` records Claude's verdict and what is still wrong in the journal.
Rounds live in `Edit/review/state.json`; a loop is capped at `review.max_rounds` (3) and closed by a sign-off.
The engine measures; Claude looks, judges and fixes. QC gates and the critique facts are read, never re-implemented."""
import copy, datetime, hashlib, json, os, re, shutil, subprocess
import numpy as np
from PIL import Image, ImageDraw

from . import config as C, style as STY
from .critique import FOOTAGE, _font, _probe, resolve_video, structure

SEVERITIES = ("high", "med", "low")
FADES = {"fade", "dip", "luma_fade", "dissolve", "xfade", "crossfade"}      # transitions that legitimately pass through black / white
QC_KIND = {"RET-24": "dead_hook", "RET-09": "dead_hook", "RET-31": "silence", "SND-04": "music_masks_voice", "GFX-27": "roto_hidden"}

def _R(S, k, d): return S.get(f"review.{k}", d)

# ======================================================================== state (rounds)
def state_path(pr): return pr.e("review", "state.json")

def load_state(pr):
    p = state_path(pr)
    st = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: st = json.load(f)
    st.setdefault("loop", 1); st.setdefault("rounds", []); st.setdefault("history", []); st.setdefault("next_dir", 1)
    return st

def save_state(pr, st):
    os.makedirs(pr.e("review"), exist_ok=True)
    with open(state_path(pr), "w", encoding="utf-8") as f: json.dump(st, f, indent=1, ensure_ascii=False)

def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

# ======================================================================== media
def _even(x): return max(2, int(round(x / 2)) * 2)

def decode(video, W, H, need, sizes):
    """one pass: small gray frames (detectors) + RGB tiles for the frame indices in `need` ({index: size key})"""
    import cv2
    from .qc import small_size
    sw, sh = small_size(W, H, area=160 * 284)
    cap = cv2.VideoCapture(video); gray, tiles, i = [], {}, 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        gray.append(cv2.cvtColor(cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
        for key in need.get(i, ()):
            tw, th = sizes[key]
            tiles[(i, key)] = Image.fromarray(cv2.cvtColor(cv2.resize(fr, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB))
        i += 1
    cap.release()
    g = np.stack(gray) if gray else np.zeros((0, sh, sw), np.uint8)
    return g, tiles

def _audio(path, sr=48000, ch=2):
    r = subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", path, "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    if r.returncode or not r.stdout: return np.zeros((0, ch), np.float32)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, ch)

def _biquad(kind, G, Q, fc, sr):
    A = 10 ** (G / 40); w0 = 2 * np.pi * fc / sr; al = np.sin(w0) / (2 * Q); c = np.cos(w0); sA = np.sqrt(A)
    if kind == "shelf":
        b = [A * ((A + 1) + (A - 1) * c + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - 2 * sA * al)]
        a = [(A + 1) - (A - 1) * c + 2 * sA * al, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - 2 * sA * al]
    else:
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]; a = [1 + al, -2 * c, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]

def lufs(x, sr):
    """ITU-R BS.1770 integrated loudness (K-weighting, 400 ms blocks, -70 LUFS absolute and -10 LU relative gates); None if < 400 ms"""
    from scipy.signal import lfilter
    if x.ndim == 1: x = x[:, None]
    blk, hop = int(.4 * sr), int(.1 * sr)
    if len(x) < blk: return None
    y = x.astype(np.float64)
    for kind, G, Q, fc in (("shelf", 4.0, 1 / np.sqrt(2), 1500.0), ("hp", 0.0, .5, 38.0)):
        b, a = _biquad(kind, G, Q, fc, sr); y = lfilter(b, a, y, axis=0)
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y ** 2, 0)])
    idx = np.arange(1 + (len(y) - blk) // hop) * hop
    z = ((cs[idx + blk] - cs[idx]) / blk).sum(1); l = -0.691 + 10 * np.log10(z + 1e-20)
    g = l > -70
    if not g.any(): return -70.0
    rel = -0.691 + 10 * np.log10(z[g].mean()) - 10; g &= l > rel
    return round(float(-0.691 + 10 * np.log10(z[g].mean())), 1)

def _db(v): return float(20 * np.log10(max(float(v), 1e-9)))

# ======================================================================== structure helpers
def cut_list(pr, dur, fps, video, nframes):
    """[(frame, t, label)] of every picture cut: shot starts from critique.structure (timeline segments, cutaway edges, B-roll shots)"""
    shots, _, trans = structure(pr, dur, video)
    tl = pr.json("timeline.json") or {}
    segs = [s for s in tl.get("segments") or [] if "t0" in s]
    cuts_ = tl.get("cutaways") or []
    out, seen = [], set()
    for a, _, _ in shots[1:]:
        f = int(round(a * fps))
        if f <= 0 or f >= nframes or any(abs(f - s) <= 1 for s in seen): continue
        seen.add(f); t = f / fps; lab = []
        for c in cuts_:
            if abs(float(c["start"]) - a) < 1.5 / fps: lab.append(f"{c['id']} in ({c.get('template')})")
            if abs(float(c["end"]) - a) < 1.5 / fps: lab.append(f"{c['id']} out")
        prev = next((s["id"] for s in segs if abs(float(s["t1"]) - a) < 1.5 / fps), None)
        nxt = next((s["id"] for s in segs if abs(float(s["t0"]) - a) < 1.5 / fps), None)
        if prev and nxt and not lab: lab.append(f"{prev} -> {nxt}")
        out.append((f, t, ", ".join(lab) or "cut"))
    return sorted(out), trans

def refine_cuts(cuts, g):
    """move each timeline cut to the frame where the picture actually changes (within 2 frames); a cut hidden under a full-frame
    graphic (no picture change) keeps its timeline frame. Returns [(frame, t, label, timeline_frame)]"""
    N = len(g); out = []
    for fc, t, lab in cuts:
        lo, hi = max(1, fc - 2), min(N - 1, fc + 2)
        if hi < lo: out.append((fc, t, lab, fc)); continue
        D = [float(np.abs(g[f].astype(np.int16) - g[f - 1].astype(np.int16)).mean()) for f in range(max(1, lo - 6), min(N, hi + 7))]
        base = float(np.median(D)) if D else 0.0
        step = {f: float(np.abs(g[f].astype(np.int16) - g[f - 1].astype(np.int16)).mean()) for f in range(lo, hi + 1)}
        best = max(step, key=step.get)
        f2 = best if step[best] >= max(4.0, 3 * base) and step[best] > 1.5 * step.get(fc, 0.0) else fc
        out.append((f2, t, lab, fc))
    return out

def _transition_at(trans, t, fps, E):
    """kind of a non-cut transition within 2 frames of t (timeline.json transitions + edit.yaml transitions:)"""
    ks = [(float(tt), str(k)) for tt, k in trans] + [(float(x.get("t", -1)), str(x.get("kind"))) for x in E.get("transitions") or []
                                                     if isinstance(x, dict) and isinstance(x.get("t"), (int, float))]
    for tt, k in ks:
        if abs(tt - t) <= 2.0 / fps and k not in ("cut", "None"): return k
    return None

def read_elements(pr, nframes):
    """caption signature per frame + first frame of every other element (graphic entries) from Edit/elements.jsonl"""
    p = pr.e("elements.jsonl"); cap, first = {}, {}
    if not os.path.exists(p): return None, {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            try: e = json.loads(line)
            except ValueError: continue
            fr = e.get("f")
            if not isinstance(fr, int) or fr > nframes + 2: continue
            if e.get("role") == "caption":
                if float(e.get("alpha", 1)) >= .5: cap.setdefault(fr, set()).add((str(e.get("id")), str(e.get("text"))))
            else:
                k = str(e.get("id")); first[k] = min(first.get(k, fr), fr)
    return cap, first

def caption_changes(cap, nframes):
    if not cap: return []
    hi = min(max(cap), nframes); out = []
    for f in range(1, hi + 2):
        if cap.get(f, set()) != cap.get(f - 1, set()): out.append(f)
    return out

def _edge_of(tl, t, fps):
    """the edit.yaml cutaway edge a cut sits on: (id, 'start'|'end') or None"""
    for c in tl.get("cutaways") or []:
        if c.get("broll"): continue
        for edge in ("start", "end"):
            if abs(float(c[edge]) - t) < 1.5 / fps: return c["id"], edge
    return None

# ======================================================================== detectors (picture)
def picture_findings(S, g, cuts, trans, fps, E, tl, body_end=None):
    """flash / black / glitch frames, duplicate frames (freeze) and big luma jumps at every cut -> (findings, flagged frames per cut)"""
    N = len(g); out = []; flagged = {}
    if N < 3: return out, flagged
    Y = g.reshape(N, -1).mean(1)
    D = np.zeros(N); D[1:] = np.abs(g[1:].astype(np.int16) - g[:-1].astype(np.int16)).reshape(N - 1, -1).mean(1)
    black, delta, glr = _R(S, "black_luma", 18), _R(S, "flash_delta", 60), _R(S, "glitch_ratio", .35)
    frr, frm, lj = _R(S, "freeze_ratio", .15), _R(S, "freeze_motion", 1.0), _R(S, "luma_jump", 45)
    for ci, (fc, t, lab, *_) in enumerate(cuts):
        tr = _transition_at(trans, t, fps, E); bad = set()
        ref_a, ref_b = Y[max(0, fc - 4)], Y[min(N - 1, fc + 4)]
        # 1. black / white flash, or a one-frame glitch, in the 5 frames around the cut
        if tr not in FADES:
            for f in range(max(1, fc - 2), min(N - 1, fc + 3)):
                why = None
                if Y[f] < black and min(ref_a, ref_b) > black + 20: why = f"black frame (mean luma {Y[f]:.0f} between {ref_a:.0f} and {ref_b:.0f})"
                elif Y[f] > max(ref_a, ref_b) + delta: why = f"white flash (mean luma {Y[f]:.0f} vs {ref_a:.0f} / {ref_b:.0f})"
                elif D[f] > 8 and D[f + 1] > 8 and f != fc:
                    across = float(np.abs(g[f + 1].astype(np.int16) - g[f - 1].astype(np.int16)).mean())
                    if across < glr * min(D[f], D[f + 1]): why = f"one-frame glitch (frame differs from both neighbours: {D[f]:.0f}/{D[f + 1]:.0f} vs {across:.1f} across)"
                if why:
                    bad.add(f)
                    out.append({"severity": "high", "t": round(f / fps, 3), "kind": "flash_frame", "cut": ci + 1,
                                "message": f"{why} at {f / fps:.2f} s (frame {f}, cut {ci + 1}: {lab}). A render or snap fault: find the layer that "
                                           f"draws it (`cves render --only {max(0, f - 2)}-{f + 2}`) and fix the edge in edit.yaml"})
        # 2. duplicate frame / freeze on a moving shot
        win = np.r_[D[max(1, fc - 15):max(1, fc - 3)], D[min(N, fc + 4):min(N, fc + 16)]]
        motion = float(np.median(win)) if len(win) else 0.0
        if motion >= frm:
            for f in range(max(1, fc - 2), min(N, fc + 3)):
                if f in bad or (f == fc and tr in FADES): continue
                if D[f] < frr * motion:
                    bad.add(f)
                    what = "the cut does not change the picture" if f == fc else "a repeated frame"
                    out.append({"severity": "med", "t": round(f / fps, 3), "kind": "freeze_frame", "cut": ci + 1,
                                "message": f"duplicate frame at {f / fps:.2f} s (frame {f} = frame {f - 1}; step {D[f]:.2f} vs local motion {motion:.2f}): "
                                           f"{what} at cut {ci + 1} ({lab}). Check the segment in/out points and cutaway edges"})
        # 3. big luma jump across a hard cut
        dy = float(Y[min(N - 1, fc)] - Y[max(0, fc - 1)])
        if abs(dy) > lj and tr is None and not bad:
            # into / out of a designed graphic or the end card the step is usually the design (dark stage): low; footage to footage: med
            gfx_edge = any(not c.get("broll") and c.get("template") not in FOOTAGE and min(abs(float(c["start"]) - t), abs(float(c["end"]) - t)) < 1.5 / fps
                           for c in tl.get("cutaways") or []) or (body_end is not None and abs(t - body_end) < 1.5 / fps)
            item = {"severity": "med" if abs(dy) > 1.5 * lj and not gfx_edge else "low", "t": round(t, 3), "kind": "luma_jump", "cut": ci + 1,
                    "message": f"luma jumps {dy:+.0f} (0-255) across the hard cut at {t:.2f} s ({lab})"
                               + (": into / out of a graphic, check it reads as designed, not as a flash" if gfx_edge else ": reads as a flash")
                               + ". Match exposure, or cover it with a transition (counts against creative.transition_kinds_max)"}
            item["patch"] = {"append": {"transitions": {"t": round(t, 3), "kind": "fade"}}, "safe": False}
            out.append(item)
        flagged[ci + 1] = bad
    return out, flagged

def caption_findings(S, changes, cuts, fps, tl):
    near = int(_R(S, "caption_near_f", 2)); out = []
    if not changes: return out
    ch = np.array(changes)
    for ci, (fc, t, lab, *_) in enumerate(cuts):
        if (ch == fc).any(): continue                   # a caption that changes ON the cut is the clean case
        d = ch - fc; k = int(np.argmin(np.abs(d))); off = int(d[k])
        if 1 <= abs(off) <= near:
            ct = round(int(ch[k]) / fps, 3)
            item = {"severity": "med" if abs(off) == 1 else "low", "t": round(t, 3), "kind": "caption_cut", "cut": ci + 1,
                    "message": f"the caption changes {abs(off)} frame(s) {'after' if off > 0 else 'before'} the cut at {t:.2f} s ({lab}): "
                               f"a flicker across the cut. Move the cut onto the caption change ({ct:.3f} s) or the caption break onto the cut"}
            edge = _edge_of(tl, t, fps)
            if edge: item["patch"] = {"set": {f"cutaways[{edge[0]}].{edge[1]}": ct}, "safe": False}
            out.append(item)
    return out

def hook_findings(S, g, cuts, first, fps, dur):
    """dead hook: no picture change, cut or graphic entry before structure.hook_change_s"""
    hc = float(S.get("structure.hook_change_s", 1.5) or 1.5); n = min(len(g), int(round(hc * fps)) + 1)
    if n < 2: return [], {}
    D = np.abs(g[1:n].astype(np.int16) - g[:n - 1].astype(np.int16)).reshape(n - 1, -1).mean(1)
    thr = float(S.get("retention.scene_diff", 12.0)); big = float(D.max()) if len(D) else 0.0
    cut0 = next((c[1] for c in cuts if c[1] <= hc), None)
    gfx0 = min((f / fps for f in first.values() if 0 < f / fps <= hc), default=None)
    facts = {"hook_change_s": hc, "max_step": round(big, 1), "scene_diff": thr, "first_cut_s": cut0, "first_graphic_s": gfx0}
    if big >= thr or cut0 is not None or gfx0 is not None: return [], facts
    return [{"severity": "high", "t": 0.0, "kind": "dead_hook",
             "message": f"dead hook: no visual change in the first {hc:g} s (largest frame step {big:.1f} < {thr:g}; no cut, no graphic entry). "
                        f"Add a cut, a punch-in step or a graphic entry before {hc:g} s (structure.hook_change_s)"}], facts

# ======================================================================== audio
def audio_review(pr, S, video, cuts, fps, dur, body_end):
    sr = 48000; X = _audio(video, sr, 2); x = X.mean(1) if len(X) else np.zeros(0, np.float32)
    A = {"integrated_lufs": lufs(X, sr) if len(X) else None, "sections": [], "cuts": [], "silences": [], "vmr": None, "earshot": None}
    out = []
    # ---- loudness per section: hook / body / payoff / end card
    hs = min(float(_R(S, "hook_s", 3.0)), body_end); pw = float(S.get("structure.payoff_window", .2) or .2)
    p0 = max(hs, body_end * (1 - pw))
    for name, a, b in (("hook", 0.0, hs), ("body", hs, p0), ("payoff", p0, body_end), ("end_card", body_end, dur)):
        if b - a > 1 / fps:
            A["sections"].append({"name": name, "t0": round(a, 2), "t1": round(b, 2), "lufs": lufs(X[int(a * sr):int(b * sr)], sr) if len(X) else None})
    sec = {s["name"]: s for s in A["sections"]}; jump = float(_R(S, "section_jump_lu", 6.0))
    for a, b in (("hook", "body"), ("body", "payoff")):
        la, lb = (sec.get(a) or {}).get("lufs"), (sec.get(b) or {}).get("lufs")
        if la is not None and lb is not None and la > -60 and lb > -60 and abs(la - lb) > jump:
            out.append({"severity": "low", "t": sec[b]["t0"], "kind": "section_level",
                        "message": f"{a} {la:.1f} LUFS vs {b} {lb:.1f} LUFS ({lb - la:+.1f} LU > {jump:g}): a level step between sections. "
                                   f"Intentional (a drop)? Otherwise even out the bed (music.bed_lu) or the voice"})
    # ---- clicks / discontinuities at cuts (master, attributed to the loudest offending stem)
    stems = {n: pr.e("stems", f"{n}.wav") for n in ("voice", "music", "sfx") if os.path.exists(pr.e("stems", f"{n}.wav"))}
    stem_x = {n: _audio(p, sr, 1)[:, 0] for n, p in stems.items()}
    ratio_min, floor = float(_R(S, "click_ratio", 4.0)), float(_R(S, "click_floor_db", -45))
    def click(y, t):
        c0, c1 = int((t - 1.0 / fps) * sr), int((t + 1.0 / fps) * sr)
        a, b = max(0, int((t - .3) * sr)), min(len(y), int((t + .3) * sr))
        if c0 <= a or c1 >= b or b - a < 100: return 0.0, -120.0
        d2 = np.abs(np.diff(y[a:b].astype(np.float64), 2)); cc0, cc1 = c0 - a, c1 - a; pad = int(.005 * sr)
        ref = np.r_[d2[:max(0, cc0 - pad)], d2[cc1 + pad:]]
        if not len(ref): return 0.0, -120.0
        peak = float(d2[cc0:cc1].max()) if cc1 > cc0 else 0.0
        return peak / (float(np.percentile(ref, 99.5)) + 1e-7), _db(np.abs(y[c0:c1]).max())
    for ci, (fc, t, lab, *_) in enumerate(cuts):
        r, pk = click(x, t) if len(x) else (0.0, -120.0)
        rec = {"cut": ci + 1, "t": round(t, 3), "click_ratio": round(r, 2), "peak_db": round(pk, 1)}
        if r > ratio_min and pk > floor:
            per = {n: click(y, t)[0] for n, y in stem_x.items() if len(y)}
            src = max(per, key=per.get) if per else None; rec["stem"] = src
            out.append({"severity": "high" if r > 2 * ratio_min else "med", "t": round(t, 3), "kind": "audio_pop", "cut": ci + 1,
                        "message": f"audio pop at the cut at {t:.2f} s ({lab}): sample step {r:.1f}x the surrounding p99.5 at {pk:.0f} dBFS"
                                   + (f", loudest in the {src} stem" if src else "") + ". Needs a short crossfade or a cut on a zero crossing / a pause"})
        A["cuts"].append(rec)
    # ---- silence gaps (master, 50 ms windows)
    hop = int(.05 * sr); k = len(x) // hop
    if k:
        env = 20 * np.log10(np.sqrt((x[:k * hop].astype(np.float64).reshape(k, hop) ** 2).mean(1)) + 1e-9)
        sil = env < float(_R(S, "silence_db", -50)); smin = float(_R(S, "silence_s", .6)); i = 0
        while i < k:
            if sil[i]:
                j = i
                while j < k and sil[j]: j += 1
                a, b = i * .05, j * .05
                if b - a >= smin: A["silences"].append({"t0": round(a, 2), "t1": round(b, 2)})
                i = j
            else: i += 1
        for s in A["silences"]:
            if s["t0"] > .2 and s["t1"] < body_end - .1:
                out.append({"severity": "low", "t": s["t0"], "kind": "silence",
                            "message": f"silence {s['t0']:.2f}-{s['t1']:.2f} s ({s['t1'] - s['t0']:.2f} s under {_R(S, 'silence_db', -50)} dBFS) inside the body: "
                                       f"dead air unless it is a deliberate drop-out"})
        tail = env[-1] if len(env) else -120
        A["end_tail_db"] = round(float(tail), 1)
        if tail > float(_R(S, "end_tail_db", -30)):
            out.append({"severity": "low", "t": round(dur - .05, 2), "kind": "abrupt_end",
                        "message": f"the audio is still at {tail:.0f} dBFS in the last 50 ms: it is cut off, not faded or ended on a hit "
                                   f"(music.fit: bars ends on a downbeat with a tail)"})
    # ---- vocal-to-music ratio over speech (needs the voice + music stems)
    A["vmr"], f_vmr = vmr(pr, S, stems)
    out += f_vmr
    # ---- earshot (optional)
    A["earshot"] = earshot(S, video)
    return A, out

def vmr(pr, S, stems):
    if "voice" not in stems or "music" not in stems: return {"skipped": "needs Edit/stems/voice.wav and music.wav"}, []
    sr = 16000; v, m = _audio(stems["voice"], sr, 1)[:, 0], _audio(stems["music"], sr, 1)[:, 0]
    n = min(len(v), len(m)); v, m = v[:n], m[:n]
    if n < sr: return {"skipped": "stems too short"}, []
    words = pr.json("words.json") or []
    sp = sorted((float(w[0]), float(w[1])) for w in words if isinstance(w, (list, tuple)) and len(w) >= 2)
    win, hop = int(.4 * sr), int(.1 * sr); hann = np.hanning(win); fr = np.fft.rfftfreq(win, 1 / sr); band = (fr >= 1000) & (fr <= 4000)
    rows = []
    for i0 in range(0, n - win, hop):
        tc = (i0 + win / 2) / sr
        if sp and not any(a - .05 <= tc <= b + .05 for a, b in sp): continue
        V = np.abs(np.fft.rfft(v[i0:i0 + win] * hann)) ** 2; M = np.abs(np.fft.rfft(m[i0:i0 + win] * hann)) ** 2
        rows.append((tc, 10 * np.log10(V[band].sum() + 1e-12), 10 * np.log10(M[band].sum() + 1e-12),
                     10 * np.log10(V.sum() + 1e-12), 10 * np.log10(M.sum() + 1e-12)))
    if not rows: return {"skipped": "no speech windows"}, []
    R = np.array(rows)
    if not sp: R = R[R[:, 3] > R[:, 3].max() - 30]                        # no words.json: voiced windows only
    R = R[R[:, 1] > np.median(R[:, 1]) - 20]                              # drop the gaps between words
    if not len(R): return {"skipped": "no voiced windows"}, []
    band_vmr = np.minimum(R[:, 1] - R[:, 2], 60); broad = np.minimum(R[:, 3] - R[:, 4], 60)
    vmin = float(_R(S, "vmr_min_db", 6.0)); under = band_vmr < vmin; share = float(under.mean())
    worst = np.argsort(band_vmr)[:5]
    info = {"windows": int(len(R)), "band_hz": [1000, 4000], "median_db": round(float(np.median(band_vmr)), 1),
            "p10_db": round(float(np.percentile(band_vmr, 10)), 1), "broadband_median_db": round(float(np.median(broad)), 1),
            "share_under_min": round(share, 3), "min_db": vmin, "worst": [{"t": round(float(R[i, 0]), 2), "vmr_db": round(float(band_vmr[i]), 1)} for i in worst]}
    if share <= float(_R(S, "mask_share", .1)): return info, []
    E = pr.edit or {}; mu = E.get("music") if isinstance(E.get("music"), dict) else {}
    bed = float(mu.get("bed_lu", S.get("sound.bed_lu", -10)))
    step = round(min(float(_R(S, "bed_step_max_db", 6.0)), max(1.0, vmin - info["p10_db"])), 1)
    t0 = info["worst"][0]["t"]
    item = {"severity": "high" if info["p10_db"] < 0 else "med", "t": t0, "kind": "music_masks_voice",
            "message": f"music masks the voice: {share:.0%} of speech windows have a 1-4 kHz vocal-to-music ratio under {vmin:g} dB "
                       f"(median {info['median_db']} dB, p10 {info['p10_db']} dB, worst at {t0:.2f} s). Lower the bed "
                       f"(music.bed_lu {bed:g} -> {bed - step:g}) or deepen the voice-band duck (sound.duck_voice_band_db)"}
    if mu.get("file") and mu.get("slot") != "platform":
        item["patch"] = {"set": {"music.bed_lu": round(bed - step, 1)}, "safe": True}
    return info, [item]

def earshot(S, video):
    """`earshot measure --json --light` on the master when earshot is installed (review.earshot: auto | off); never fails the pack"""
    if str(_R(S, "earshot", "auto")) == "off": return {"skipped": "review.earshot: off"}
    exe = shutil.which(C.get("earshot")) or (C.get("earshot") if os.path.isfile(C.get("earshot")) else None)
    if not exe: return {"skipped": "earshot not installed (optional: setup installs it as a uv tool)"}
    try:
        r = subprocess.run([exe, "measure", "--json", "--light", video], capture_output=True, text=True, timeout=float(_R(S, "earshot_timeout_s", 180)))
        if r.returncode: return {"skipped": f"earshot exit {r.returncode}: {(r.stderr or '').strip()[-200:]}"}
        d = json.loads(r.stdout); d.pop("file", None); return d
    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        return {"skipped": f"earshot failed: {type(e).__name__}"}

# ======================================================================== QC + critique (read, never re-measured)
def qc_findings(pr, sha):
    st = pr.json("qc.json")
    if not st: return [{"severity": "med", "t": None, "kind": "qc_missing", "message": "no Edit/qc.json: run `cves qc` on this render first"}], None
    if st.get("sha256") and st["sha256"] != sha:
        return [{"severity": "med", "t": None, "kind": "qc_stale", "message": "Edit/qc.json judged another file: run `cves qc` on this render"}], st
    out = []
    for g_ in st.get("gates") or []:
        if g_.get("status") not in ("FAIL", "WARN"): continue
        item = {"severity": "high" if g_["status"] == "FAIL" else "low", "t": None, "kind": QC_KIND.get(g_["id"], "qc"), "gate": g_["id"],
                "message": f"QC {g_['status']} {g_['id']}: {g_.get('summary', '')} (QC-REPORT.txt; never loosen the gate)"}
        if g_["id"] == "GFX-27":            # a roto card mostly behind the head reads as a dark rectangle
            m = re.search(r"\(([\w.#]+) at ([\d.]+) s\)", g_.get("summary", ""))
            item["severity"] = "high" if g_["status"] == "FAIL" else "med"
            if m: item["t"] = float(m.group(2))
            item["message"] = (f"QC {g_['status']} GFX-27: {g_.get('summary', '')}. The roto card sits behind the presenter's head and reads as a "
                               f"dark rectangle: let it find the free space beside / above the head (roto.place: auto, the default; "
                               f"lower roto.min_scale if it does not fit), or move the moment to a cutaway. Look at the frame, never loosen the gate")
        out.append(item)
    return out, st

def critique_findings(pr):
    p = pr.e("critique", "critique.json")
    if not os.path.exists(p):
        return [{"severity": "low", "t": None, "kind": "critique_missing", "message": "no critique pack: run `cves critique` and fill CRITIQUE.md"}], None
    with open(p, encoding="utf-8") as f: cq = json.load(f)
    out = [{"severity": "low", "t": None, "kind": "restraint", "message": f"restraint budget OVER: {b['item']} {b['used']} > {b['budget']} (creative.*): cut one"}
           for b in cq.get("budget") or [] if b.get("status") == "OVER"]
    return out, cq

# ======================================================================== images
def _label(d, xy, text, size=14, fill=(230, 230, 230)): d.text(xy, text, font=_font(size), fill=fill)

def _sheet(tiles, cols, tw, th, title, labels, marks=None, lh=22, title_h=30):
    marks = marks or {}; rows = max(1, (len(tiles) + cols - 1) // cols)
    im = Image.new("RGB", (cols * (tw + 8) + 8, title_h + rows * (th + lh + 8) + 8), (18, 18, 20)); d = ImageDraw.Draw(im)
    _label(d, (8, 6), title, 16)
    for i, tile in enumerate(tiles):
        x, y = 8 + (i % cols) * (tw + 8), title_h + (i // cols) * (th + lh + 8)
        im.paste(tile if tile is not None else Image.new("RGB", (tw, th), (40, 40, 40)), (x, y))
        col = marks.get(i)
        if col: d.rectangle([x - 3, y - 3, x + tw + 2, y + th + 2], outline=col, width=3)
        _label(d, (x + 2, y + th + 3), labels[i], 13, (255, 120, 110) if col == (230, 60, 60) else (225, 225, 225))
    return im

def write_images(out, tiles, cuts, offsets, flagged, cut_kinds, sizes, fps, hook_idx, payoff_idx, end_idx, hook_first):
    os.makedirs(os.path.join(out, "cuts"), exist_ok=True); paths = {"cuts": []}
    RED, YEL, GRN = (230, 60, 60), (255, 200, 90), (90, 210, 120)
    tw, th = sizes["cut"]
    for ci, (fc, t, lab, *_) in enumerate(cuts):
        frs = [fc + o for o in offsets]; ts = [tiles.get((f, "cut")) for f in frs]
        labels = [f"{'+' if o > 0 else ''}{o} f  {f / fps:.2f}s" + ("  CUT" if o == 0 else "") for o, f in zip(offsets, frs)]
        marks = {i: RED for i, f in enumerate(frs) if f in flagged.get(ci + 1, set())}
        for i, o in enumerate(offsets):
            if o == 0 and i not in marks: marks[i] = YEL
        kinds = cut_kinds.get(ci + 1)
        title = f"cut {ci + 1:02d} @ {t:.2f}s (frame {fc}): {lab}" + (f"   FLAGGED: {', '.join(sorted(kinds))}" if kinds else "")
        p = os.path.join(out, "cuts", f"cut_{ci + 1:02d}.jpg"); _sheet(ts, len(offsets), tw, th, title[:150], labels, marks).save(p, quality=88)
        paths["cuts"].append(p)
    # index: last frame before | first frame after, every cut
    iw, ih = sizes["index"]; pairs, labs, mk = [], [], {}
    for ci, (fc, t, lab, *_) in enumerate(cuts):
        pair = Image.new("RGB", (2 * iw + 4, ih), (18, 18, 20))
        for j, f in enumerate((fc - 1, fc)):
            tl_ = tiles.get((f, "index"))
            if tl_ is not None: pair.paste(tl_, (j * (iw + 4), 0))
        pairs.append(pair); kinds = cut_kinds.get(ci + 1)
        labs.append(f"#{ci + 1:02d} {t:.2f}s " + (",".join(sorted(kinds))[:24] if kinds else "ok"))
        if kinds: mk[ci] = RED
    cols = 6 if ih >= iw else 4
    p = os.path.join(out, "index.jpg")
    _sheet(pairs or [None], cols, 2 * iw + 4, ih, f"{len(cuts)} cuts: last frame before | first frame after (red = machine finding)",
           labs or ["no cuts"], mk).save(p, quality=88)
    paths["index"] = p
    hw, hh = sizes["hook"]
    labels = [f"{f / fps:.2f}s" for f in hook_idx]
    mk = {i: GRN for i, f in enumerate(hook_idx) if hook_first is not None and f == hook_first}
    p = os.path.join(out, "hook.jpg")
    _sheet([tiles.get((f, "hook")) for f in hook_idx], 10 if hh >= hw else 6, hw, hh,
           "hook at 10 fps (green = first visual change)" if hook_first is not None else "hook at 10 fps (NO visual change detected)", labels, mk).save(p, quality=88)
    paths["hook"] = p
    for name, idx, title in (("payoff", payoff_idx, "payoff window"), ("endcard", end_idx, "end card")):
        p = os.path.join(out, f"{name}.jpg")
        _sheet([tiles.get((f, "cut")) for f in idx] or [None], max(1, min(6, len(idx))), tw, th, title, [f"{f / fps:.2f}s" for f in idx] or ["none"]).save(p, quality=88)
        paths[name] = p
    return paths

# ======================================================================== build
def build(pr, which=None):
    video = resolve_video(pr, which); version = which or "master"
    S = STY.load(pr); E = pr.edit or {}; tl = pr.json("timeline.json") or {}
    dur, W, H, fps = _probe(video); sha = _sha(video)
    st = load_state(pr); mx = int(_R(S, "max_rounds", 3)); rounds = st["rounds"]
    if rounds and rounds[-1].get("sha256") == sha: rec = rounds.pop(); n, dname = rec["n"], rec["dir"]        # same render: redo this round
    elif len(rounds) >= mx:
        raise SystemExit(f"review round cap reached ({len(rounds)}/{mx}): sign off now with `cves review signoff --verdict ship|revise --notes \"...\"` "
                         f"and record what is still wrong (docs/REVIEW.md)")
    else: n, dname = len(rounds) + 1, f"r{st['next_dir']:03d}"; st["next_dir"] += 1
    out = pr.e("review", dname)
    if os.path.isdir(out): shutil.rmtree(out)
    os.makedirs(out)

    # ---- what to decode
    nframes = int(round(dur * fps)); cuts, trans = cut_list(pr, dur, fps, video, nframes)
    offsets = [int(o) for o in _R(S, "cut_offsets", [-2, -1, 0, 1, 2])]
    portrait = H >= W
    sizes = {"cut": (216, _even(216 * H / W)) if portrait else (384, _even(384 * H / W)),
             "index": (120, _even(120 * H / W)) if portrait else (200, _even(200 * H / W)),
             "hook": (144, _even(144 * H / W)) if portrait else (256, _even(256 * H / W))}
    ec = E.get("end_card") if isinstance(E.get("end_card"), dict) else None
    a_frames = tl.get("a_frames") if ec else None
    body_end = (a_frames / fps) if a_frames and a_frames / fps < dur - 1 / fps else (max(0.0, dur - float(ec["duration"])) if ec and ec.get("duration") else dur)
    hook_s, hook_fps = float(_R(S, "hook_s", 3.0)), float(_R(S, "hook_fps", 10))
    hook_idx = sorted({min(nframes - 1, int(round(k / hook_fps * fps))) for k in range(int(min(hook_s, dur) * hook_fps))})
    pw = float(S.get("structure.payoff_window", .2) or .2); p0 = max(min(hook_s, body_end), body_end * (1 - pw)); npf = int(_R(S, "payoff_frames", 6))
    payoff_idx = sorted({min(nframes - 1, int((p0 + (body_end - p0) * (k + .5) / npf) * fps)) for k in range(npf)}) if body_end > p0 else []
    e0 = body_end if body_end < dur - 1 / fps else max(0.0, dur - 1.0)
    end_idx = sorted({min(nframes - 1, int(round(t * fps))) for t in (e0, e0 + .25, (e0 + dur) / 2, dur - 1.0 / fps) if t < dur})
    need = {}
    for fc, _, _ in cuts:                     # +-2 spare frames: the picture cut may land a frame off the timeline time (refined below)
        for o in range(min(offsets) - 2, max(offsets) + 3): need.setdefault(fc + o, set()).add("cut")
        for f in range(fc - 3, fc + 3): need.setdefault(f, set()).add("index")
    for f in hook_idx: need.setdefault(f, set()).add("hook")
    for f in payoff_idx + end_idx: need.setdefault(f, set()).add("cut")
    g, tiles = decode(video, W, H, need, sizes)
    N = len(g); cuts = refine_cuts([c for c in cuts if c[0] < N], g)

    # ---- detectors
    F = []
    pf, flagged = picture_findings(S, g, cuts, trans, fps, E, tl, body_end); F += pf
    cap, first = read_elements(pr, N)
    F += caption_findings(S, caption_changes(cap, N), cuts, fps, tl)
    hf, hook_facts = hook_findings(S, g, cuts, first, fps, dur)
    qf, qcst = qc_findings(pr, sha)
    if not any(x["kind"] == "dead_hook" for x in qf): F += hf      # QC (RET-24 / RET-09) already says it: one finding, not two
    F += qf
    cf, cq = critique_findings(pr); F += cf
    for a, b, lab in structure(pr, dur, video)[0][1:-1]:
        if 0 < (b - a) * fps < int(_R(S, "min_shot_f", 3)):
            F.append({"severity": "med", "t": round(a, 3), "kind": "micro_shot",
                      "message": f"a {round((b - a) * fps)}-frame shot at {a:.2f} s ({lab}): reads as a glitch, not a cut. Extend it or remove it"})
    if ec and ec.get("duration") is not None and float(ec["duration"]) < float(_R(S, "end_card_min_s", 1.0)):
        mn = float(_R(S, "end_card_min_s", 1.0))
        F.append({"severity": "med", "t": round(body_end, 3), "kind": "end_card",
                  "message": f"end card {float(ec['duration']):g} s is shorter than review.end_card_min_s {mn:g} s: nobody can read the CTA",
                  "patch": {"set": {"end_card.duration": mn}, "safe": True}})
    A, af = audio_review(pr, S, video, cuts, fps, dur, body_end)
    if qcst and any(x.get("gate") == "RET-31" for x in qf): af = [x for x in af if x["kind"] != "silence"]
    F += af
    order = {s: i for i, s in enumerate(SEVERITIES)}
    F.sort(key=lambda x: (order[x["severity"]], x["t"] if x["t"] is not None else -1))
    for i, x in enumerate(F): x["id"] = f"F{i + 1:02d}"
    F = [{k: x[k] for k in ("id", "severity", "t", "kind", "message", "patch", "cut", "gate") if k in x} for x in F]

    # ---- images
    cut_kinds = {}
    for x in F:
        if x.get("cut"): cut_kinds.setdefault(x["cut"], set()).add(x["kind"])
    hook_first = None
    if hook_idx:
        Dh = [float(np.abs(g[b].astype(np.int16) - g[a].astype(np.int16)).mean()) for a, b in zip(hook_idx, hook_idx[1:]) if b < N]
        thr = float(S.get("retention.scene_diff", 12.0))
        hook_first = next((hook_idx[i + 1] for i, d in enumerate(Dh) if d >= thr), None)
        if hook_first is None and hook_facts.get("first_graphic_s") is not None:
            hook_first = min(hook_idx, key=lambda f: abs(f / fps - hook_facts["first_graphic_s"]))
    paths = write_images(out, tiles, cuts, offsets, flagged, cut_kinds, sizes, fps, hook_idx, payoff_idx, end_idx, hook_first)

    with open(os.path.join(out, "cuts.json"), "w", encoding="utf-8") as f:
        json.dump([{"cut": i + 1, "t": round(c[1], 3), "frame": c[0], "timeline_frame": c[3], "picture_offset_f": c[0] - c[3], "label": c[2],
                    "image": f"cuts/cut_{i + 1:02d}.jpg", "findings": sorted(cut_kinds.get(i + 1, ()))} for i, c in enumerate(cuts)], f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "audio.json"), "w", encoding="utf-8") as f: json.dump(A, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "findings.json"), "w", encoding="utf-8") as f: json.dump(F, f, indent=1, ensure_ascii=False)
    counts = {s: sum(1 for x in F if x["severity"] == s) for s in SEVERITIES}
    qc_fail = (qcst or {}).get("fail") if qcst and qcst.get("sha256") in (None, sha) else None
    cap_reached = n >= mx
    rec = {"n": n, "dir": dname, "video": os.path.basename(video), "version": version, "sha256": sha, "created": _now(), "counts": counts,
           "qc_fail": qc_fail, "high": [x["id"] for x in F if x["severity"] == "high"], "applied": [], "cap_reached": cap_reached}
    st["rounds"].append(rec); save_state(pr, st)
    facts = {"video": os.path.basename(video), "version": version, "duration_s": round(dur, 2), "size": [W, H], "fps": round(fps, 3),
             "cuts": len(cuts), "cut_offsets": offsets, "body_end_s": round(body_end, 2), "end_card_s": round(dur - body_end, 2), **{(k if k.startswith("hook") else f"hook_{k}"): v for k, v in hook_facts.items()}}
    md = write_md(out, rec, mx, F, A, facts, paths, cq)
    from . import learn
    learn.on_review(pr, {"round": n, "loop": st["loop"], "dir": dname, "video": os.path.basename(video), "counts": counts, "qc_fail": qc_fail,
                         "high": [x["kind"] for x in F if x["severity"] == "high"]})
    return {"dir": out, "md": md, "round": n, "max_rounds": mx, "cap_reached": cap_reached, "counts": counts, "qc_fail": qc_fail,
            "findings": F, "audio": A, "paths": paths}

RUBRIC = [
    ("cuts", "index.jpg, then every flagged cuts/cut_NN.jpg (and 3 unflagged ones)",
     ["Does every cut land on a word or action boundary, never mid-gesture or mid-word?",
      "Any black, white, duplicated or half-rendered frame in the -2..+2 strip?",
      "After each cut, does the eye land where the last shot left it (eye trace), or does it hunt?",
      "Do captions change on the cut, not a frame or two either side?",
      "Does the framing change enough at A-roll cuts (or is the jump covered)?"]),
    ("hook", "hook.jpg", ["Is there a visual change by the hook time (green tile)? Would you stop scrolling on frame 0?",
                          "Is the topic or subject readable in the first second, sound off?"]),
    ("payoff", "payoff.jpg", ["Does the payoff deliver what the hook promised, and is it the visual peak of the piece?"]),
    ("end card", "endcard.jpg", ["Is the end card on long enough to read twice? CTA legible, inside the safe zone, brand right?"]),
    ("sound", "audio.json (+ earshot)", ["Is the voice clear over the music everywhere (vmr)? Any pop at a cut? Any section jumping in level?",
                                         "Any silence that is not a deliberate drop-out?"]),
    ("verdict", "everything above", ["Would a senior editor show this to the owner now? If not: the one change that matters most."]),
]

def write_md(out, rec, mx, F, A, facts, paths, cq):
    rel = lambda p: os.path.relpath(p, out).replace(os.sep, "/")
    hi = rec["counts"]["high"]; qf = rec.get("qc_fail")
    ready = hi == 0 and qf == 0
    L = [f"# Review round {rec['n']} of {mx}: {facts['video']} ({facts['version']})", ""]
    if rec["cap_reached"]:
        L += [f"> **Round cap reached ({rec['n']}/{mx}).** This is the last round of this loop: fix only what is quick and safe, then sign off "
              "(`cves review signoff --verdict ship|revise --notes \"...\"`) and record what is still wrong.", ""]
    L += [f"**Ready to show the owner: {'YES' if ready else 'NO'}** "
          f"({hi} high finding(s); QC FAIL: {qf if qf is not None else 'unknown, run `cves qc` on this render'}).", "",
          "Claude: look at the images below with the Read tool (index first, then every flagged cut), answer the rubric, fix what edit.yaml can "
          "fix, re-render and run the loop again (docs/REVIEW.md). The engine measured; you judge.", "",
          "## Images", "", f"- `{rel(paths['index'])}`: every cut (last frame before | first after)",
          f"- `cuts/cut_NN.jpg`: {len(paths['cuts'])} cut strips (frames {', '.join(f'{o:+d}' for o in facts.get('cut_offsets', []))} around each cut; yellow = the cut frame, red = flagged)",
          f"- `{rel(paths['hook'])}`, `{rel(paths['payoff'])}`, `{rel(paths['endcard'])}`", "",
          "## Facts", "", "| fact | value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in facts.items()]
    L += ["", f"## Findings ({len(F)}: {rec['counts']['high']} high, {rec['counts']['med']} med, {rec['counts']['low']} low)", ""]
    if F:
        L += ["| id | sev | t (s) | kind | finding | patch |", "|---|---|---|---|---|---|"]
        for x in F:
            p = x.get("patch")
            ps = ("safe: `cves review apply`" if p.get("safe") else "suggested (apply by hand)") + ": `" + json.dumps({k: v for k, v in p.items() if k != "safe"}) + "`" if p else ""
            L.append(f"| {x['id']} | {x['severity']} | {'' if x['t'] is None else x['t']} | {x['kind']} | {x['message'].replace('|', '/')} | {ps} |")
    else: L.append("No machine findings. That proves nothing about taste: answer the rubric.")
    v = A.get("vmr") or {}
    L += ["", "## Sound (audio.json)", "", f"- integrated: {A.get('integrated_lufs')} LUFS; sections: "
          + ", ".join(f"{s['name']} {s['lufs']}" for s in A.get("sections") or []),
          f"- vocal-to-music (1-4 kHz, speech): " + (f"median {v.get('median_db')} dB, p10 {v.get('p10_db')} dB, {v.get('share_under_min', 0):.0%} under {v.get('min_db')} dB"
                                                       if "median_db" in v else str(v.get("skipped", "n/a"))),
          f"- clicks at cuts: {sum(1 for c in A.get('cuts') or [] if c.get('stem') is not None or c['click_ratio'] > 4)} flagged of {len(A.get('cuts') or [])}; "
          f"silences: {len(A.get('silences') or [])}; end tail {A.get('end_tail_db')} dBFS",
          f"- earshot: " + ((A.get("earshot") or {}).get("summary") or str((A.get("earshot") or {}).get("skipped", "n/a")))]
    if cq: L += ["", f"Critique facts: `Edit/critique/critique.json` (shots {cq.get('facts', {}).get('shots')}, first change {cq.get('facts', {}).get('first_change_s')} s)."]
    L += ["", "## Rubric (answer each by looking; yes / no + timecode + the fix)", ""]
    for name, src, qs in RUBRIC:
        L += [f"### {name} ({src})", ""] + [f"- [ ] {q}  \n  answer: " for q in qs] + [""]
    L += ["## Loop", "", "1. Fix: `cves review apply` (safe patches), then the rest by hand in edit.yaml.",
          "2. Re-render: `cves build` (or `cves render --only ...` + `cves mix` + `cves encode` + `cves qc`), `cves critique`, `cves review build`.",
          f"3. Stop when QC has 0 FAIL and there are no high findings, or at round {mx}. Then sign off:", "",
          "```", "cves review signoff --verdict ship --notes \"<what is still not perfect>\"", "cves review signoff --verdict revise --notes \"<why it cannot ship>\"", "```", ""]
    md = os.path.join(out, "REVIEW.md")
    with open(md, "w", encoding="utf-8") as f: f.write("\n".join(L))
    return md

# ======================================================================== apply
_SEG = re.compile(r"^([^\[\]]+)(?:\[([^\]]+)\])?$")

def _walk(E, path, create=True):
    """parent container + last key of a dotted edit.yaml path (`end_card.duration`, `cutaways[c3].start`, `music.bed_lu`)"""
    parts = path.split("."); cur = E
    for i, part in enumerate(parts):
        m = _SEG.match(part)
        if not m: raise ValueError(f"bad path {path}")
        key, sel = m.group(1), m.group(2); last = i == len(parts) - 1
        if sel is None:
            if last: return cur, key
            if not isinstance(cur.get(key), dict):
                if not create: raise KeyError(path)
                cur[key] = {}
            cur = cur[key]
        else:
            lst = cur.get(key) or []
            hit = next((x for x in lst if isinstance(x, dict) and str(x.get("id", x.get("segment"))) == sel), None)
            if hit is None and sel.isdigit() and int(sel) < len(lst): hit = lst[int(sel)]
            if hit is None: raise KeyError(path)
            if last: raise ValueError(f"path ends on a list item: {path}")
            cur = hit
    return cur, None

def apply_patch(E, patch):
    """apply one finding patch to an edit dict (in place); returns [(path, old, new)]"""
    ch = []
    for path, v in (patch.get("set") or {}).items():
        parent, k = _walk(E, path); ch.append((path, parent.get(k), v)); parent[k] = v
    for path, v in (patch.get("append") or {}).items():
        parent, k = _walk(E, path)
        if not isinstance(parent.get(k), list): parent[k] = []
        parent[k].append(v); ch.append((path, None, v))
    return ch

def _fmt(v):
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, float): return ("%.3f" % v).rstrip("0").rstrip(".")
    if isinstance(v, int): return str(v)
    return json.dumps(v, ensure_ascii=False)

def _text_edits(E_new, changes):
    """beats._patch edits for simple `a.b` / `a[id].b` sets (comments kept); None if a change has another shape"""
    out = []
    for path, _, new in changes:
        parts = path.split(".")
        if len(parts) != 2 or isinstance(new, (dict, list)): return None
        m = _SEG.match(parts[0])
        if m.group(2) is None:
            blk = E_new.get(m.group(1)) or {}
            sib = next((k for k in blk if k != parts[1]), None) if isinstance(blk, dict) else None
            out.append((r"^" + re.escape(m.group(1)) + r":", parts[1], None, _fmt(new), sib))
        else:
            out.append((r"^\s*-\s*\{?\s*(id|segment):\s*" + re.escape(m.group(2)) + r"\s*(#.*)?(,.*)?$", parts[1], None, _fmt(new), None))
    return out

def latest(pr):
    st = load_state(pr)
    if not st["rounds"]: raise SystemExit("no review round yet: run `cves review build`")
    rec = st["rounds"][-1]; d = pr.e("review", rec["dir"])
    with open(os.path.join(d, "findings.json"), encoding="utf-8") as f: F = json.load(f)
    return st, rec, d, F

def apply(pr, only=None, dry_run=False):
    """apply the safe patches of the latest round to edit.yaml (backup first; comments kept when the text patch verifies)"""
    import yaml
    from .beats import _patch
    st, rec, d, F = latest(pr)
    want = {x.strip() for x in only.split(",")} if only else None
    todo = [x for x in F if x.get("patch") and x["patch"].get("safe") and not x.get("applied") and (want is None or x["id"] in want)]
    skipped = [x["id"] for x in F if x.get("patch") and not x["patch"].get("safe") and (want is None or x["id"] in want)]
    src = pr.e("edit.yaml")
    with open(src, encoding="utf-8") as f: text = f.read()
    E = yaml.safe_load(text) or {}; En = copy.deepcopy(E); done, changes = [], []
    for x in todo:
        try: ch = apply_patch(En, x["patch"])
        except (KeyError, ValueError) as e:
            skipped.append(f"{x['id']} ({e})"); continue
        changes += ch; done.append({"id": x["id"], "kind": x["kind"], "changes": [{"path": p, "old": o, "new": n_} for p, o, n_ in ch]})
    res = {"round": rec["n"], "applied": done, "skipped_unsafe_or_failed": skipped, "backup": None, "how": None, "dry_run": dry_run}
    if not done or dry_run: return res
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); bak = pr.e(f"edit.yaml.bak-{stamp}"); shutil.copy2(src, bak)
    eds = _text_edits(En, changes); out = _patch(text, En, eds) if eds else None; how = "text patch (comments kept)"
    if out is None: out = yaml.safe_dump(En, sort_keys=False, allow_unicode=True, width=140); how = "re-dumped (comments lost; see the backup)"
    with open(src, "w", encoding="utf-8") as f: f.write(out)
    ids = {a["id"] for a in done}
    for x in F:
        if x["id"] in ids: x["applied"] = True
    with open(os.path.join(d, "findings.json"), "w", encoding="utf-8") as f: json.dump(F, f, indent=1, ensure_ascii=False)
    prev = []
    p = os.path.join(d, "applied.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: prev = json.load(f)
    with open(p, "w", encoding="utf-8") as f: json.dump(prev + [{"t": _now(), "backup": os.path.basename(bak), "how": how, "applied": done}], f, indent=1, ensure_ascii=False)
    rec["applied"] = sorted(set(rec.get("applied") or []) | ids); save_state(pr, st)
    from . import learn
    learn.on_review_apply(pr, {"round": rec["n"], "applied": done, "how": how})
    res.update(backup=bak, how=how); return res

# ======================================================================== sign-off + show
def signoff(pr, verdict, notes=""):
    if verdict not in ("ship", "revise"): raise SystemExit("--verdict must be ship or revise")
    if not (notes or "").strip(): raise SystemExit("--notes is required: record what is still wrong (or why it cannot ship)")
    st, rec, d, F = latest(pr)
    open_ = [x for x in F if not x.get("applied") and x["severity"] in ("high", "med")]
    out = {"round": rec["n"], "loop": st["loop"], "verdict": verdict, "notes": notes.strip(), "video": rec["video"], "qc_fail": rec.get("qc_fail"),
           "open": [{"id": x["id"], "severity": x["severity"], "kind": x["kind"], "t": x["t"], "message": x["message"][:200]} for x in open_],
           "counts": rec["counts"], "rounds_used": len(st["rounds"]), "cap_reached": bool(rec.get("cap_reached"))}
    warn = []
    if verdict == "ship" and any(x["severity"] == "high" for x in open_): warn.append(f"shipping with {sum(1 for x in open_ if x['severity'] == 'high')} open high finding(s): recorded")
    if verdict == "ship" and rec.get("qc_fail"): warn.append(f"QC has {rec['qc_fail']} FAIL: `cves deliver` will refuse this master")
    out["warnings"] = warn
    rec["verdict"] = verdict; rec["notes"] = out["notes"]; rec["signed"] = _now()
    st["history"].append({"loop": st["loop"], "closed": rec["signed"], "verdict": verdict, "rounds": st["rounds"]})
    st["loop"] += 1; st["rounds"] = []; save_state(pr, st)
    with open(os.path.join(d, "signoff.json"), "w", encoding="utf-8") as f: json.dump(out, f, indent=1, ensure_ascii=False)
    from . import learn
    learn.on_review_signoff(pr, out)
    return out

def show(pr, as_json=False):
    st = load_state(pr)
    rounds = st["rounds"] or (st["history"][-1]["rounds"] if st["history"] else [])
    if not rounds: return "no review round yet: run `cves review build`"
    rec = rounds[-1]; d = pr.e("review", rec["dir"])
    with open(os.path.join(d, "findings.json"), encoding="utf-8") as f: F = json.load(f)
    if as_json: return json.dumps({"state": st, "round": rec, "findings": F}, indent=1, ensure_ascii=False)
    mx = int(_R(STY.load(pr), "max_rounds", 3))
    L = [f"loop {st['loop'] if st['rounds'] else st['loop'] - 1}, round {rec['n']}/{mx} ({rec['dir']}): {rec['video']}"
         + (f"; signed off: {rec['verdict']}" if rec.get("verdict") else ""),
         f"  {rec['counts']['high']} high, {rec['counts']['med']} med, {rec['counts']['low']} low; QC FAIL {rec.get('qc_fail')}; applied {', '.join(rec.get('applied') or []) or '-'}",
         f"  {os.path.join(d, 'REVIEW.md')}"]
    for x in F:
        if x["severity"] != "low":
            L.append(f"  {x['id']} {x['severity']:4s} {'' if x['t'] is None else '%.2fs' % x['t']:>7s} {x['kind']:18s} {x['message'][:150]}"
                     + ("  [safe patch]" if (x.get("patch") or {}).get("safe") and not x.get("applied") else "") + ("  [applied]" if x.get("applied") else ""))
    return "\n".join(L)
