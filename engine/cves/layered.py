"""Control mode: render the edit as separate layers and write Export/control/layers.json (schema cves.layers/1, see
docs/CONTROL-MODE.md §3). The exporters in cves/export/ turn it into a DaVinci Resolve or Kdenlive project.
  V1  graded A-roll per segment (zoom, exposure balance and roto baked; no captions, no chest graphics)  ProRes 422 HQ;
      on a voiceover / music / broll spine: one clip per B-roll shot (framing baked, no captions)
  V2  every cutaway (incl. its transition frames inside the window) + the end card, cut from the final frames  ProRes 422 HQ
  V3  chest graphics (wordmark, logo lockup) on transparent                                            ProRes 4444 + alpha
  A1-A3  voice / music / sfx stems as mixed; captions as editable subtitle events (not burned in).
Frame rate and size come from the project (timeline.json `fps_rational` / `size`, else edl.json, else the renderer's).
Needs a final render + mix first (`cves build`); renders the extra A-roll and overlay passes itself.

`build(pr)` writes everything; `update(pr, ids)` re-renders only the named layers (`cves control update --only c3`)
and refreshes their entries (frames, hash) and the captions in layers.json, leaving every other layer untouched."""
import os, json, shutil, subprocess, hashlib, tempfile, time
from fractions import Fraction
from . import config as C
from .render import Timeline, render

LAYERS = "layers.json"


# ------------------------------------------------------------------ project timebase
def timebase(pr, TL=None):
    """(fps_rational (num, den), size (w, h)) of the cut: timeline.json, else edl.json, else the Timeline's."""
    tl = pr.json("timeline.json", {}) or {}; edl = pr.json("edl.json", {}) or {}
    fr = tl.get("fps_rational") or edl.get("fps_rational")
    if not fr:
        TL = TL or Timeline(pr); fr = TL.fps_rational
    size = tl.get("size") or edl.get("size")
    if not size:
        TL = TL or Timeline(pr); size = TL.size
    return (int(fr[0]), int(fr[1])), (int(size[0]), int(size[1]))


def _rate(fps): return f"{fps[0]}/{fps[1]}"


def _enc(src_pattern, start_frame, n, out, fps, alpha=False):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    v = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16"] if alpha else \
        ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-framerate", _rate(fps), "-start_number", str(start_frame), "-i", src_pattern,
                    "-frames:v", str(n), *v, "-vf", "scale=out_color_matrix=bt709:out_range=tv", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709", out], check=True)


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def _pat(d): return os.path.join(d, "%05d.png")


# ------------------------------------------------------------------ layer plan (what each layer is, from the Timeline)
def chest_groups(TL):
    """chest entries -> V3 layers. Entries whose segments overlap share one layer (chest mode draws every chest graphic of a
    segment together). -> [(layer id, [entry indices], first frame, end frame)]"""
    spans = [(k, a, b) for k, (a, b) in enumerate(TL.chest_spans()) if b > a]
    groups = []
    for k, a, b in sorted(spans, key=lambda x: x[1]):
        if groups and a < groups[-1][3]:
            g = groups[-1]; groups[-1] = (g[0], g[1] + [k], g[2], max(g[3], b))
        else: groups.append((f"chest_{k}", [k], a, b))
    return groups


def plan(TL):
    """every video layer: {id, track, kind, f0, f1, rel path, edit_ref, alpha}"""
    F = TL.FPS; out = []
    for s in TL.segs:
        ref = f"edl.{s['id']}" if TL.aroll else (f"broll.{s['id']}" if s.get("kind") == "broll" else f"gap.{s['id']}")
        out.append({"id": f"a_{s['id']}", "track": "V1", "kind": "aroll", "f0": s["f0"], "f1": s["f0"] + s["n"],
                    "rel": os.path.join("media", "aroll", f"{s['id']}.mov"), "edit_ref": ref, "alpha": False})
    for c in TL.cuts:
        if c.get("broll") and not TL.aroll: continue          # B-roll shots are the V1 picture on the non-aroll spines
        out.append({"id": str(c["id"]), "track": "V2", "kind": "cutaway", "f0": round(c["start"] * F), "f1": round(c["end"] * F),
                    "rel": os.path.join("media", "cutaways", f"{c['id']}.mov"), "edit_ref": f"{'broll' if c.get('broll') else 'cutaways'}.{c['id']}", "alpha": False})
    if TL.END:
        out.append({"id": "end_card", "track": "V2", "kind": "end", "f0": TL.A_FRAMES, "f1": TL.N,
                    "rel": os.path.join("media", "cutaways", "end_card.mov"), "edit_ref": "end_card", "alpha": False})
    for gid, ks, a, b in chest_groups(TL):
        out.append({"id": gid, "track": "V3", "kind": "chest", "f0": a, "f1": b,
                    "rel": os.path.join("media", "overlays", f"{gid}.mov"), "edit_ref": "chest." + "+".join(map(str, ks)), "alpha": True})
    return out


def captions(TL):
    """captions as editable subtitles (only where they show in the final: A-roll, no chest graphic, not the snap punch-in).
    `ref` is the index into the Timeline's caption events, so an edited caption maps back to edit.yaml."""
    F = TL.FPS; caps, idx, last_end = [], 1, 0.0
    chest_t = [(s["t0"], s["t1"]) for sid in TL.chest for s in TL.segs if s["id"] == sid]
    hidden = lambda t: (TL.in_cut(t) and not TL.in_cut(t).get("broll")) or any(a <= t < b for a, b in chest_t) or any(a <= t < b for a, b in getattr(TL, "cap_hide", [])) or \
                       (TL.snap and TL.snap[0] <= t < TL.snap[1]) or t >= TL.T_END
    for ref, (a, b, words) in enumerate(TL.caps):
        a, b = max(a, last_end, 0.0), min(b, TL.T_END)
        if b - a < 2 / F or hidden((a + b) / 2): continue
        caps.append({"index": idx, "ref": ref, "start": round(a, 3), "end": round(b, 3), "text": " ".join(w for w, _ in words)}); idx += 1; last_end = b
    return caps


def _clip(L, ctl, fps, size, F):
    p = os.path.join(ctl, L["rel"])
    return {"id": L["id"], "track": L["track"], "path": L["rel"].replace(os.sep, "/"), "start": L["f0"] / F, "end": L["f1"] / F,
            "source_in": 0.0, "fps": list(fps), "size": list(size), "alpha": L["alpha"], "edit_ref": L["edit_ref"],
            "frames": L["f1"] - L["f0"], "hash": _sha(p)}


def _audio_clips(pr, med, ctl, T):
    import soundfile as sf
    out = []
    for name, tr in (("voice", "A1"), ("music", "A2"), ("sfx", "A3")):
        src = pr.e("stems", f"{name}.wav")
        if not os.path.exists(src): continue
        dst = os.path.join(med, "audio", f"{name}.wav"); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
        info = sf.info(dst)
        out.append({"id": name, "track": tr, "path": os.path.relpath(dst, ctl).replace(os.sep, "/"), "start": 0.0, "end": min(T, info.duration),
                    "source_in": 0.0, "channels": info.channels, "sample_rate": info.samplerate, "edit_ref": f"stems.{name}", "hash": _sha(dst)})
    return out


def _snapshot(pr, TL):
    """what the cut looked like at export: the importer maps editor changes against this, not against today's files"""
    ef = pr.e("edit.yaml")
    return {"exported": time.strftime("%Y-%m-%d %H:%M:%S"), "edit_sha256": _sha(ef) if os.path.exists(ef) else None,
            "segments": [{k: s.get(k) for k in ("id", "clip", "in", "out", "f0", "n")} for s in TL.segs],
            "a_frames": TL.A_FRAMES, "frames": TL.N}


def _render_layer(pr, TL, L, final, tmp):
    """render the frames a layer needs; returns the folder its PNGs are in"""
    fr = list(range(L["f0"], L["f1"]))
    if L["kind"] in ("cutaway", "end"):
        render(pr, only=fr, out_dir=final, mode="final"); return final
    d = os.path.join(tmp, L["kind"]); os.makedirs(d, exist_ok=True)
    render(pr, only=fr, out_dir=d, mode="aroll" if L["kind"] == "aroll" else "chest"); return d


# ------------------------------------------------------------------ full build
def build(pr):
    TL = Timeline(pr); F = TL.FPS; fps, size = timebase(pr, TL)
    ctl = pr.p("Export", "control"); med = os.path.join(ctl, "media"); final = pr.e("frames")
    if not os.path.exists(os.path.join(final, f"{TL.N - 1:05d}.png")) or not os.path.exists(pr.e("stems", "voice.wav")):
        raise SystemExit("run `cves build` first (final frames + stems are needed)")
    shutil.rmtree(med, ignore_errors=True)
    layers = plan(TL); clips = []
    ar = pr.e("frames_aroll"); render(pr, out_dir=ar, mode="aroll")                       # V1: one A-roll pass
    chest_fr = sorted({f for L in layers if L["kind"] == "chest" for f in range(L["f0"], L["f1"])})
    ov = pr.e("frames_overlay")
    if chest_fr: render(pr, only=chest_fr, out_dir=ov, mode="chest")                       # V3: one chest pass
    for L in layers:
        src = {"aroll": ar, "chest": ov}.get(L["kind"], final)
        _enc(_pat(src), L["f0"], L["f1"] - L["f0"], os.path.join(ctl, L["rel"]), fps, alpha=L["alpha"])
        clips.append(_clip(L, ctl, fps, size, F))
    T = TL.N / F
    clips += _audio_clips(pr, med, ctl, T)
    man = {"schema": "cves.layers/1", "name": pr.edit.get("project", {}).get("title", os.path.basename(pr.root)), "fps": list(fps),
           "size": list(size), "audio_rate": 48000, "duration": T, "clips": clips, "captions": captions(TL), "source": _snapshot(pr, TL)}
    json.dump(man, open(os.path.join(ctl, LAYERS), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for d in (ar, ov): shutil.rmtree(d, ignore_errors=True)
    return ctl


# ------------------------------------------------------------------ partial update
AUDIO_IDS = {"voice", "music", "sfx", "audio", "stems"}

def update(pr, ids):
    """re-render only the named layers (cutaway / segment / chest / end-card ids, `roto.N`, `captions`, `audio`) into
    Export/control/media at the same paths, and refresh their entries + the captions in layers.json.
    Refuses (one actionable line) when the cut itself changed, because then every later layer moved: rebuild with
    `cves export`. Returns a list of what changed."""
    ctl = pr.p("Export", "control"); mp = os.path.join(ctl, LAYERS)
    if not os.path.exists(mp): raise SystemExit("no Export/control/layers.json: run `cves export resolve|kdenlive|all` first")
    man = json.load(open(mp, encoding="utf-8"))
    TL = Timeline(pr); F = TL.FPS; fps, size = timebase(pr, TL)
    if list(fps) != list(man.get("fps", [])) or list(size) != list(man.get("size", [])):
        raise SystemExit(f"the project is now {fps[0]}/{fps[1]} {size[0]}x{size[1]} but layers.json is {man.get('fps')} {man.get('size')}: rebuild with `cves export all`")
    old_v1 = {c["id"]: (round(c["start"] * F), round(c["end"] * F)) for c in man["clips"] if c["track"] == "V1"}
    new_v1 = {f"a_{s['id']}": (s["f0"], s["f0"] + s["n"]) for s in TL.segs}
    if old_v1 != new_v1:
        raise SystemExit("the cut changed since the export (A-roll segments moved or were re-timed): rebuild with `cves export resolve|kdenlive|all`")
    layers = {L["id"]: L for L in plan(TL)}
    by_id = {c["id"]: c for c in man["clips"]}
    want, notes = [], []
    tg = TL.only_targets()
    for it in [x.strip() for x in (ids.split(",") if isinstance(ids, str) else ids) if str(x).strip()]:
        if it in layers: want.append(it)
        elif it in by_id: want.append(it)                                       # a layer that no longer exists in edit.yaml
        elif it in ("captions", "subs"): pass
        elif it in AUDIO_IDS: want.append("audio")
        elif it.startswith("roto") and it in tg:                                 # roto is baked into its A-roll segment
            sid = it.split(":", 1)[1] if ":" in it else TL.E["roto"][int(it.split(".")[1])]["segment"]; want.append(f"a_{sid}")
        elif it in tg and tg[it][2] == "aroll": want.append(f"a_{it}")
        elif it.startswith("chest") and it in tg:                                # chest.k -> its layer group
            k = int(it.replace("_", ".").split(".")[1]); want += [L["id"] for L in layers.values() if L["kind"] == "chest" and k in [int(x) for x in L["edit_ref"].split(".")[1].split("+")]]
        else:
            raise SystemExit(f"control update: unknown layer '{it}'; layers: {', '.join(sorted(list(layers) + ['captions', 'audio']))}")
    tmp = tempfile.mkdtemp(prefix="cves_layers_")
    try:
        for lid in dict.fromkeys(want):
            if lid == "audio":
                aud = _audio_clips(pr, os.path.join(ctl, "media"), ctl, TL.N / F)
                man["clips"] = [c for c in man["clips"] if c["track"] not in ("A1", "A2", "A3")] + aud
                notes.append(f"audio stems refreshed ({', '.join(c['id'] for c in aud)})"); continue
            if lid not in layers:                                                # gone from edit.yaml: drop the layer
                c = by_id[lid]; man["clips"] = [x for x in man["clips"] if x["id"] != lid]
                p = os.path.join(ctl, c["path"])
                if os.path.exists(p): os.remove(p)
                notes.append(f"{lid}: removed (no longer in edit.yaml)"); continue
            L = layers[lid]
            if L["kind"] in ("cutaway", "end") and lid in by_id:
                o = by_id[lid]
                if (round(o["start"] * F), round(o["end"] * F)) != (L["f0"], L["f1"]):
                    notes.append(f"{lid}: timing {o['start']:.3f}-{o['end']:.3f} -> {L['f0'] / F:.3f}-{L['f1'] / F:.3f}")
            src = _render_layer(pr, TL, L, pr.e("frames"), tmp)
            _enc(_pat(src), L["f0"], L["f1"] - L["f0"], os.path.join(ctl, L["rel"]), fps, alpha=L["alpha"])
            new = _clip(L, ctl, fps, size, F); old = by_id.get(lid)
            man["clips"] = [new if x["id"] == lid else x for x in man["clips"]] if old else man["clips"] + [new]
            notes.append(f"{lid}: re-rendered {new['frames']} frames -> {L['rel']} (sha256 {new['hash'][:12]})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    caps = captions(TL)
    if caps != man.get("captions"): notes.append(f"captions refreshed ({len(caps)} cues)")
    man["captions"] = caps
    man["duration"] = TL.N / F
    from .export.layers import parse_manifest, LayersError
    try: parse_manifest(man, __import__("pathlib").Path(mp))
    except LayersError as e: raise SystemExit(f"layers.json would be invalid after the update: {e.problems[0]}")
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return notes
