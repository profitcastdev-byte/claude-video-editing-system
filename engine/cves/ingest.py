"""Ingest: any footage -> transcript, tightened selects, clean voice, lossless conformed plate, matte, faces.
Steps (each idempotent, run by `cves ingest --steps a,b` or individually):
  probe           ffprobe every source -> Edit/ingest.json (size, SAR, rotation, VFR, HDR, bit depth, audio)
  transcribe_raw  every source's audio -> Edit/raw_words.json + raw_transcript.txt (Claude reads this to pick selects)
  select          Edit/selects.yaml (Claude-written; clips may carry `src:`) -> conform plans, DeepFilterNet voice clips,
                  pause tightening, edl.json, voice stems, voice_chain.json
  conform         per referenced source: rotation, SAR, HDR->SDR tonemap, frame-rate conform, face-aware crop path
  words           voice_final.wav -> words.json (cut-time word timings for captions and cues)
  plate           one lossless 10-bit FFV1 decode per segment, conform filters applied in that single decode
  matte           Robust Video Matting per segment (MPS / CUDA / CPU)
  faces           YuNet box + 5 landmarks per frame -> faces.json
Canvas = style `platform.size`; rate = style `platform.fps` ("source" = the primary source's rate). See docs/INGEST.md.
Lessons baked in: no generative voice enhancement; frame-snapped segments; drop slivers < 4 frames; edge-accurate mattes;
never squash (crop to the canvas aspect, then scale); long sources are streamed, never loaded whole."""
import os, sys, json, glob, subprocess, re, tempfile, shutil
from fractions import Fraction
import numpy as np, soundfile as sf, yaml
from concurrent.futures import ThreadPoolExecutor
from . import config as C, style as STY

SR = 48000
VIDEO_EXT = (".mp4", ".mov", ".mkv", ".m4v", ".mts", ".m2ts", ".avi", ".webm", ".mxf")
STD_RATES = [(24000, 1001), (24, 1), (25, 1), (30000, 1001), (30, 1), (48, 1), (50, 1), (60000, 1001), (60, 1)]   # lint: ok the table of standard CFR rates VFR snaps to
HDR_TRC = ("smpte2084", "arib-std-b67")
INGEST_VERSION = 2

def sh(cmd, **kw): return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)

# ------------------------------------------------------------------ settings from the style profile / edit.yaml
def _S(pr): return STY.load(pr)

def canvas(pr, S=None):
    """master canvas (w, h): edit.yaml project.size if set, else style platform.size"""
    S = S or _S(pr)
    w, h = (pr.edit.get("project") or {}).get("size") or S.get("platform.size")
    return int(w), int(h)

def whisper_language(pr, S=None):
    """whisper language code: edit.yaml project.language > style captions.language > 'auto' (whisper auto-detect)"""
    S = S or _S(pr)
    lang = (pr.edit.get("project") or {}).get("language") or S.get("captions.language") or "auto"
    return str(lang).strip().lower() or "auto"

def _rational(v):
    """style platform.fps value -> Fraction (None = 'source')"""
    if v is None or str(v).strip().lower() == "source": return None
    if isinstance(v, (list, tuple)): return Fraction(int(v[0]), int(v[1]))
    if isinstance(v, str) and "/" in v: return Fraction(v)
    x = float(v); n, d = _nearest_std(x)
    return Fraction(n, d) if abs(n / d - x) < 0.01 else Fraction(x).limit_denominator(1001)

def _nearest_std(x): return min(STD_RATES, key=lambda r: abs(r[0] / r[1] - x))

# ------------------------------------------------------------------ sources
def _abs(pr, src): return src if os.path.isabs(src) else pr.p(src)
def _rel(pr, path): return os.path.relpath(os.path.abspath(path), pr.root)
def primary(pr): return _rel(pr, pr.raw)

def norm_src(pr, src):
    """a clip's `src` (or None) -> canonical project-relative path"""
    if not src: return primary(pr)
    p = _abs(pr, src)
    if not os.path.exists(p): raise SystemExit(f"source not found: {src} (paths in selects.yaml are relative to the project folder, e.g. Raw/<file>)")
    return _rel(pr, p)

def _slug(src): return re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.splitext(src)[0]).strip("_")

def source_audio(pr, src=None):
    """48 kHz mono audio of a source: Edit/raw_audio.wav for the primary (unchanged layout), Edit/sources/<slug>.wav otherwise"""
    src = norm_src(pr, src)
    if src == primary(pr): return pr.e("raw_audio.wav")
    os.makedirs(pr.e("sources"), exist_ok=True); return pr.e("sources", _slug(src) + ".wav")

def all_sources(pr):
    """primary first; then edit.yaml project.sources, else every other video in Raw/; plus any src named in selects.yaml"""
    out = [primary(pr)]
    extra = (pr.edit.get("project") or {}).get("sources")
    if extra is None and os.path.isdir(pr.p("Raw")):
        extra = [os.path.join("Raw", f) for f in sorted(os.listdir(pr.p("Raw"))) if f.lower().endswith(VIDEO_EXT) and not f.startswith(".")]
    for s in (extra or []) + [c.get("src") for c in _clips(pr, missing_ok=True) if c.get("src")]:
        s = norm_src(pr, s)
        if s not in out: out.append(s)
    return out

def _clips(pr, missing_ok=False):
    if not os.path.exists(pr.e("selects.yaml")):
        if missing_ok: return []
        raise SystemExit("Edit/selects.yaml missing: write it from Edit/raw_transcript.txt first")
    sel = yaml.safe_load(open(pr.e("selects.yaml"), encoding="utf-8")) or []
    return (sel.get("clips") or []) if isinstance(sel, dict) else sel

# ------------------------------------------------------------------ 0. probe
def probe_file(path):
    """ffprobe one file -> dict (display size after rotation + SAR, fps, VFR, HDR, bit depth, audio)"""
    try: j = json.loads(sh([C.get("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", path]).stdout)
    except subprocess.CalledProcessError as e: raise SystemExit(f"ffprobe cannot read {path}: {e.stderr.strip()[:200]}")
    vids = [s for s in j.get("streams", []) if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")]
    if not vids: raise SystemExit(f"no video stream in {path}")
    v = vids[0]; vk = [s for s in j["streams"] if s.get("codec_type") == "video"].index(v)
    auds = [s for s in j["streams"] if s.get("codec_type") == "audio"]; a = auds[0] if auds else None
    rot = 0
    for sd in v.get("side_data_list") or []:
        if "rotation" in sd: rot = int(round(float(sd["rotation"])))
    if not rot and (v.get("tags") or {}).get("rotate"): rot = -int(v["tags"]["rotate"])   # legacy tag is clockwise
    rot %= 360
    sar = v.get("sample_aspect_ratio") or "1:1"
    try: n_, d_ = (int(x) for x in sar.split(":")); sarf = Fraction(n_, d_) if n_ and d_ else Fraction(1)
    except ValueError: sarf = Fraction(1)
    w, h = int(v["width"]), int(v["height"])
    fw, fh, fs = (h, w, 1 / sarf) if rot in (90, 270) else (w, h, sarf)   # ffmpeg autorotates before our filters
    if fs != 1: fw = int(round(fw * fs / 2)) * 2                            # SAR fix: scale width to square pixels
    def fr(x):
        try: f = Fraction(x); return f if f > 0 else None
        except (ValueError, ZeroDivisionError, TypeError): return None
    r, avg = fr(v.get("r_frame_rate")), fr(v.get("avg_frame_rate"))
    vfr = bool(r and avg and abs(float(r) - float(avg)) / float(r) > 0.005)
    pf = v.get("pix_fmt") or ""; m = re.search(r"p(\d+)(le|be)?$", pf)
    depth = int(m.group(1)) if m else int(v.get("bits_per_raw_sample") or 8)
    trc = v.get("color_transfer") or "unknown"
    dur = float(j.get("format", {}).get("duration") or v.get("duration") or 0)
    return {"w": w, "h": h, "sar": f"{sarf.numerator}:{sarf.denominator}", "rotation": rot, "display": [fw, fh],
            "codec": v.get("codec_name"), "stream": vk, "r_frame_rate": [r.numerator, r.denominator] if r else None,
            "avg_frame_rate": [avg.numerator, avg.denominator] if avg else None, "vfr": vfr,
            "pix_fmt": pf, "bit_depth": depth, "color_transfer": trc, "color_primaries": v.get("color_primaries") or "unknown",
            "color_space": v.get("color_space") or "unknown", "color_range": v.get("color_range") or "unknown",
            "hdr": trc in HDR_TRC, "duration": round(dur, 4),
            "audio": {"codec": a.get("codec_name"), "channels": int(a.get("channels") or 0), "rate": int(a.get("sample_rate") or 0)} if a else None}

def source_rate(P):
    """the source's CFR rate as a Fraction: r_frame_rate when CFR, nearest standard rate when VFR or exotic"""
    r = Fraction(*P["r_frame_rate"]) if P.get("r_frame_rate") else None
    avg = Fraction(*P["avg_frame_rate"]) if P.get("avg_frame_rate") else None
    if P.get("vfr") or r is None or float(r) > 121:
        return Fraction(*_nearest_std(float(avg or r or 30)))
    n, d = _nearest_std(float(r))
    return Fraction(n, d) if abs(n / d - float(r)) < 1e-6 else r

def project_rate(pr, S, P_primary):
    return _rational(S.get("platform.fps", "source")) or source_rate(P_primary)

# ------------------------------------------------------------------ conform plan (computed once per source, cached by path + mtime)
_FILTERS = None
def _has_filter(name):
    global _FILTERS
    if _FILTERS is None:
        try: _FILTERS = set(re.findall(r"^\s*[TSC.]{2,3}\s+(\w+)", sh([C.get("ffmpeg"), "-hide_banner", "-filters"]).stdout, re.M))
        except Exception: _FILTERS = set()
    return name in _FILTERS

def _tonemap_chain(P, S):
    """HDR (PQ / HLG) -> SDR BT.709. zscale+tonemap when ffmpeg has them, else a documented matrix-only fallback."""
    alg, npl = S.get("ingest.hdr.tonemap", "hable"), S.get("ingest.hdr.npl", 100)
    prim = "bt2020" if P["color_primaries"] in ("unknown", "bt2020") else P["color_primaries"]
    mat = "bt2020nc" if P["color_space"] in ("unknown", "bt2020nc", "bt2020_ncl") else P["color_space"]
    rin = "full" if P.get("color_range") in ("pc", "full") else "limited"
    if _has_filter("zscale") and _has_filter("tonemap"):
        return ("zscale", f"zscale=tin={P['color_transfer']}:min={mat}:pin={prim}:rin={rin}:t=linear:npl={npl},format=gbrpf32le,"
                          f"zscale=p=bt709,tonemap={alg}:desat=0,zscale=t=bt709:m=bt709:r=limited,format=yuv420p10le")
    return ("fallback-matrix-only", "scale=in_color_matrix=bt2020:out_color_matrix=bt709:in_range=auto:out_range=tv,format=yuv420p10le")

def _even(x): return max(2, int(round(x / 2)) * 2)

def _face_path(path, P, S, axis, cw, ch):
    """sample YuNet faces on the (rotated, square-pixel) source, smooth, convert to a crop offset path [[t, px], ...].
    Streams frames through an ffmpeg pipe at ingest.face_crop.sample_fps: never holds the video in RAM."""
    import cv2
    from scipy.ndimage import median_filter, gaussian_filter1d
    fc = S.get("ingest.face_crop", {}) or {}
    sfps = float(fc.get("sample_fps", 2)); smooth = float(fc.get("smooth_s", 1.0)); ax, ay = (fc.get("anchor") or [0.5, 0.4])[:2]
    fw, fh = P["display"]; k = 640 / max(fw, fh); dw, dh = _even(fw * k), _even(fh * k)
    pre = "scale=trunc(iw*sar/2)*2:ih,setsar=1," if P["sar"] != "1:1" else ""
    proc = subprocess.Popen([C.get("ffmpeg"), "-v", "error", "-i", path, "-map", f"0:v:{P['stream']}", "-vf", f"{pre}fps={sfps},scale={dw}:{dh}",
                             "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    det = cv2.FaceDetectorYN.create(C.get("yunet"), "", (dw, dh), .6, .3, 5000); vals, nb = [], dw * dh * 3
    try:
        while True:
            buf = proc.stdout.read(nb)
            if len(buf) < nb: break
            _, f = det.detect(np.frombuffer(buf, np.uint8).reshape(dh, dw, 3))
            if f is not None and len(f):
                b = max(f, key=lambda r: r[2] * r[3]); vals.append(((b[0] + b[2] / 2) / dw, (b[1] + b[3] / 2) / dh))
            else: vals.append((np.nan, np.nan))
    finally:
        proc.stdout.close(); proc.wait()
    v = np.array([p[0] if axis == "x" else p[1] for p in vals], float)
    found = int(np.isfinite(v).sum())
    if not found: return None, 0, len(v)
    i = np.arange(len(v)); ok = np.isfinite(v); v = np.interp(i, i[ok], v[ok])
    v = median_filter(v, size=5, mode="nearest"); v = gaussian_filter1d(v, max(smooth * sfps, .01), mode="nearest")
    full, crop, anchor = (fw, cw, ax) if axis == "x" else (fh, ch, ay)
    off = np.clip(v * full - anchor * crop, 0, full - crop)
    return [[round(n / sfps, 3), int(round(o))] for n, o in enumerate(off)], found, len(v)

def _plan(pr, src, S, fps, size):
    path = _abs(pr, src); st = os.stat(path); P = probe_file(path); W, H = size
    fw, fh = P["display"]; target = W / H
    plan = {"mtime": st.st_mtime, "bytes": st.st_size, "probe": P, "canvas": [W, H], "fps_rational": [fps.numerator, fps.denominator]}
    plan["sar_fix"] = P["sar"] != "1:1"
    plan["fps_convert"] = bool(P["vfr"] or source_rate(P) != fps)
    tm = _tonemap_chain(P, S) if P["hdr"] else None
    plan["tonemap"] = tm[0] if tm else None; plan["tonemap_filter"] = tm[1] if tm else None
    crop = None
    if abs(fw / fh - target) > 0.002:
        axis = "x" if fw / fh > target else "y"
        cw, ch = (_even(fh * target), fh) if axis == "x" else (fw, _even(fw / target))
        cw, ch = min(cw, fw), min(ch, fh)
        mode = S.get("ingest.reframe", "face"); fpath, found, n = (None, 0, 0)
        if mode == "face": fpath, found, n = _face_path(path, P, S, axis, cw, ch)
        full, c = (fw, cw) if axis == "x" else (fh, ch)
        tol = float(S.get("ingest.face_crop.static_tolerance", 0.04)) * c
        static = (full - c) // 2
        if fpath:
            offs = [o for _, o in fpath]
            if max(offs) - min(offs) <= tol: static, fpath = int(np.median(offs)), None
        crop = {"axis": axis, "w": cw, "h": ch, "mode": "face" if (mode == "face" and found) else "center",
                "offset": static, "path": fpath, "faces_found": found, "samples": n}
    plan["crop"] = crop
    cw = crop["w"] if crop else fw
    plan["plate_scale"] = round(W / cw, 4)                 # canvas px per source px (FRAME-11)
    return plan

def _cfg_key(S):
    return json.dumps([S.get("ingest.reframe", "face"), S.get("ingest.face_crop", {}), S.get("ingest.hdr", {})], sort_keys=True, default=str)

def conform_sources(pr, srcs=None, S=None):
    """conform plans for the referenced sources -> Edit/ingest.json; returns (project rate Fraction, {src: plan}).
    Cached per source by path + mtime + size + settings."""
    S = S or _S(pr); size = canvas(pr, S)
    if srcs is None:
        cl = _clips(pr, missing_ok=True)
        srcs = sorted({norm_src(pr, c.get("src")) for c in cl}, key=lambda s: (s != primary(pr), s)) if cl else [primary(pr)]
    ing = pr.json("ingest.json", {}) or {}
    old = ing.get("sources", {}) if ing.get("version") == INGEST_VERSION else {}
    P0 = old.get(primary(pr), {}).get("probe") if old.get(primary(pr), {}).get("mtime") == os.stat(pr.raw).st_mtime else None
    fps = project_rate(pr, S, P0 or probe_file(pr.raw)); key = _cfg_key(S)
    out = dict(old)
    for s in srcs:
        st = os.stat(_abs(pr, s)); c = old.get(s)
        if not (c and c.get("mtime") == st.st_mtime and c.get("bytes") == st.st_size and c.get("canvas") == list(size)
                and c.get("fps_rational") == [fps.numerator, fps.denominator] and c.get("cfg") == key and "crop" in c):
            c = _plan(pr, s, S, fps, size); c["cfg"] = key
            print(f"conform {s}: {c['probe']['display'][0]}x{c['probe']['display'][1]} rot {c['probe']['rotation']} "
                  f"{'VFR ' if c['probe']['vfr'] else ''}{'HDR ' if c['probe']['hdr'] else ''}-> {size[0]}x{size[1]} @ {fps} "
                  f"(crop {c['crop']['mode'] if c['crop'] else 'none'}, plate_scale {c['plate_scale']})", flush=True)
        out[s] = c
    used = [out[s] for s in srcs]
    ing.update({"version": INGEST_VERSION, "canvas": list(size), "fps": float(fps), "fps_rational": [fps.numerator, fps.denominator],
                "primary": primary(pr), "sources": out, "plate_scale": max(c["plate_scale"] for c in used)})
    pr.save_json("ingest.json", ing)
    return fps, out

def conform(pr):
    """step: conform plans for the sources selects.yaml references (primary only when there are no selects yet)"""
    fr, plans = conform_sources(pr)
    return f"{len(plans)} source(s) @ {fr} fps, plate_scale {max(p['plate_scale'] for p in plans.values())}"

def probe(pr):
    """step: probe every source (no crop analysis) into ingest.json"""
    ing = pr.json("ingest.json", {}) or {}; pro = ing.setdefault("probes", {})
    for s in all_sources(pr):
        pro[s] = probe_file(_abs(pr, s)); P = pro[s]
        print(f"{s}: {P['display'][0]}x{P['display'][1]} rot {P['rotation']} sar {P['sar']} {P['avg_frame_rate']} "
              f"{'VFR' if P['vfr'] else 'CFR'} {P['color_transfer']} {P['pix_fmt']} ({P['bit_depth']}-bit) audio {P['audio']}", flush=True)
    pr.save_json("ingest.json", ing); return len(pro)

# ------------------------------------------------------------------ whisper (language from style, chunked on long files)
def _whisper_once(wav16, out_base, prompt, lang):
    cmd = [C.get("whisper"), "-m", C.get("whisper_model"), "-f", wav16, "-l", lang, "-ml", "1", "-sow", "-oj", "-of", out_base]
    if prompt: cmd += ["--prompt", prompt]
    sh(cmd)
    j = json.load(open(out_base + ".json", encoding="utf-8"))
    W = [[s["offsets"]["from"] / 1000, s["offsets"]["to"] / 1000, s["text"].strip()] for s in j["transcription"] if s["text"].strip()]
    return W, (j.get("result") or {}).get("language")

def _silence_cuts(wav, max_s, search_s=None):
    """chunk boundaries (seconds) <= max_s apart, each placed at the quietest 0.5 s inside the last `search_s` of the chunk.
    Streams the file in blocks."""
    info = sf.info(wav); sr = info.samplerate; dur = info.frames / sr; hop = int(.05 * sr)
    e = np.array([float(np.sqrt(np.mean((b.mean(1) if b.ndim > 1 else b) ** 2))) for b in sf.blocks(wav, blocksize=hop) if len(b)])
    e = np.convolve(e, np.ones(10) / 10, "same"); search_s = search_s or min(60.0, max_s / 2)
    cuts, pos = [0.0], 0.0
    while dur - pos > max_s:
        a, b = int((pos + max_s - search_s) / .05), int((pos + max_s) / .05)
        pos = (a + int(np.argmin(e[a:b]))) * .05; cuts.append(round(pos, 3))
    return list(zip(cuts, cuts[1:] + [dur]))

def whisper_words(wav16, out_base, prompt=None, lang="en", S=None, info=None):
    """[[t0, t1, word]] for a 16 kHz wav. Files longer than ingest.whisper.chunk_over_s are split on silences into chunks
    of <= ingest.whisper.chunk_s, transcribed separately, offset and merged. `info` (dict) receives the detected language."""
    S = S if S is not None else STY.load()
    over, chunk = float(S.get("ingest.whisper.chunk_over_s", 600)), float(S.get("ingest.whisper.chunk_s", 300))
    sfi = sf.info(wav16); dur = sfi.frames / sfi.samplerate
    if dur <= over:
        W, lg = _whisper_once(wav16, out_base, prompt, lang)
        if info is not None: info["language"] = lg; info["chunks"] = 1
        return W
    W, langs, d = [], [], tempfile.mkdtemp(prefix="cves_whisper_")
    try:
        cuts = _silence_cuts(wav16, chunk)
        for k, (a, b) in enumerate(cuts):
            y, sr = sf.read(wav16, start=int(a * sfi.samplerate), stop=int(b * sfi.samplerate))
            p = os.path.join(d, f"c{k}.wav"); sf.write(p, y, sr)
            w, lg = _whisper_once(p, os.path.join(d, f"c{k}"), prompt, lang); langs.append(lg)
            W += [[round(s + a, 3), round(e + a, 3), t] for s, e, t in w]
        json.dump({"chunks": [[a, b] for a, b in cuts], "language": langs, "words": W}, open(out_base + ".json", "w", encoding="utf-8"), indent=1)
    finally: shutil.rmtree(d, ignore_errors=True)
    if info is not None: info["language"] = max(set(langs), key=langs.count) if langs else None; info["chunks"] = len(cuts)
    return W

def to16k(src, dst, extra=()):
    sh([C.get("ffmpeg"), "-v", "error", "-y", *extra, "-i", src, "-vn", "-ac", "1", "-ar", "16000", dst])

def _extract_audio(pr, src):
    out = source_audio(pr, src); path = _abs(pr, src)
    if os.path.exists(out) and os.path.getmtime(out) >= os.stat(path).st_mtime and src != primary(pr): return out
    try: sh([C.get("ffmpeg"), "-v", "error", "-y", "-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(SR), out])
    except subprocess.CalledProcessError: raise SystemExit(f"{src} has no readable audio track: CVES edits on the voice, add the take with sound")
    return out

def _record_language(pr, info):
    ing = pr.json("ingest.json", {}) or {}
    if info.get("language"): ing["language_detected"] = info["language"]
    ing["language"] = info.get("requested"); pr.save_json("ingest.json", ing)

# ------------------------------------------------------------------ 1. transcript of the raw take(s)
def _lines(W):
    lines, cur, t0 = [], [], None
    for s, e, w in W:
        if t0 is None: t0 = s
        cur.append(w)
        if w.endswith((".", "?", "!", "।", "॥")) or len(cur) > 22:
            lines.append(f"[{t0:7.2f}-{e:7.2f}] {' '.join(cur)}"); cur, t0 = [], None
    if cur: lines.append(f"[{t0:7.2f}-{W[-1][1]:7.2f}] {' '.join(cur)}")
    return lines

def transcribe_raw(pr):
    S = _S(pr); lang = whisper_language(pr, S); srcs = all_sources(pr); probe(pr); total, out = 0, []
    for src in srcs:
        a = _extract_audio(pr, src); prim = src == primary(pr); info = {"requested": lang}
        w16 = pr.e("raw16.wav") if prim else pr.e("sources", _slug(src) + ".16k.wav"); to16k(a, w16)
        W = whisper_words(w16, pr.e("raw_whisper") if prim else pr.e("sources", _slug(src) + ".whisper"), lang=lang, S=S, info=info)
        if prim: pr.save_json("raw_words.json", W); _record_language(pr, info)
        else: pr.save_json(os.path.join("sources", _slug(src) + ".words.json"), W)
        total += len(W)
        out += ([f"# src: {src}"] if len(srcs) > 1 else []) + _lines(W) + ([""] if len(srcs) > 1 else [])
    # readable transcript in ~sentence lines with raw timestamps, for the story step (one section per source)
    open(pr.e("raw_transcript.txt"), "w", encoding="utf-8").write("\n".join(out).rstrip("\n") + "\n")
    return total

# ------------------------------------------------------------------ 2. selects -> tightened EDL + clean voice
MAXGAP, BREATH, EDGE, PAD = .22, .11, .05, .5

def _df_out(pr, cid):
    hit = glob.glob(pr.e("voice", "df", f"{glob.escape(cid)}_DeepFilterNet*.wav")) or glob.glob(pr.e("voice", "df", f"{glob.escape(cid)}*.wav"))
    if not hit: raise SystemExit(f"DeepFilterNet produced no output for clip {cid}: check `cves doctor`")
    return sorted(hit)[-1]

def _df_clip(pr, c, audio):
    os.makedirs(pr.e("voice", "in"), exist_ok=True); os.makedirs(pr.e("voice", "df"), exist_ok=True)
    a, b = max(0, c["in"] - PAD), c["out"] + PAD
    y, sr = sf.read(audio, start=int(a * SR), stop=int(b * SR))      # windowed read: long sources never load whole
    p = pr.e("voice", "in", f"{c['id']}.wav"); sf.write(p, y, sr)
    sh([C.get("deepfilter"), "-o", pr.e("voice", "df"), p])
    return _df_out(pr, c["id"])

def _tighten(c, y, sr, off):
    from scipy.ndimage import binary_opening
    hop = int(.01 * sr)
    rms = np.array([np.sqrt(np.mean(y[i:i + 2 * hop] ** 2)) for i in range(0, len(y) - 2 * hop, hop)])
    db = 20 * np.log10(rms + 1e-9); thr = max(db.max() - 32, -50)
    t = off + np.arange(len(db)) * .01
    speech = binary_opening(db > thr, np.ones(5))
    idx = np.where(((t >= c["in"] - .02) & (t <= c["out"] + .02)) & speech)[0]
    if not len(idx): return []
    s0, s1 = max(t[idx[0]] - EDGE, c["in"]), min(t[idx[-1]] + .01 + EDGE, c["out"])
    segs, cur, k, run = [], s0, np.searchsorted(t, s0), None
    while k < len(t) and t[k] < s1:
        if not speech[k]: run = run if run is not None else t[k]
        else:
            if run is not None and t[k] - run > MAXGAP: segs.append((cur, run + BREATH / 2)); cur = t[k] - BREATH / 2
            run = None
        k += 1
    segs.append((cur, s1)); return segs

def select(pr):
    clips = _clips(pr); S = _S(pr)
    ids = [c.get("id") for c in clips]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup or None in ids: raise SystemExit(f"selects.yaml: every clip needs a unique id (duplicates: {', '.join(map(str, dup)) or 'missing id'})")
    srcs = {c["id"]: norm_src(pr, c.get("src")) for c in clips}
    order = sorted(set(srcs.values()), key=lambda s: (s != primary(pr), s))
    fr, _plans = conform_sources(pr, order, S); fps = float(fr)
    audio = {s: _extract_audio(pr, s) if (s != primary(pr) or not os.path.exists(pr.e("raw_audio.wav"))) else pr.e("raw_audio.wav") for s in order}
    with ThreadPoolExecutor(4) as ex: dfs = list(ex.map(lambda c: _df_clip(pr, c, audio[srcs[c["id"]]]), clips))
    segments = []
    for c, dfp in zip(clips, dfs):
        y, sr = sf.read(dfp); y = y.mean(1) if y.ndim > 1 else y
        for j, (a, b) in enumerate(_tighten(c, y, sr, max(0, c["in"] - PAD))):
            a, b = round(round(a * fps) / fps, 5), round(round(b * fps) / fps, 5)
            if round((b - a) * fps) >= 4: segments.append({"id": f"{c['id']}_{j}", "clip": c["id"], "in": a, "out": b, "src": srcs[c["id"]]})
    if not segments: raise SystemExit("no speech found inside the selected clips: check the in/out times in selects.yaml")
    edl = {"source": primary(pr), "fps": fps, "fps_rational": [fr.numerator, fr.denominator], "size": list(canvas(pr, S)),
           "clips": clips, "segments": segments}
    pr.save_json("edl.json", edl)
    assemble_voice(pr)
    return len(segments), sum(s["out"] - s["in"] for s in segments)

# the voice chain: podcast-style polish on the DeepFilterNet stem. No generative models: they rewrite words (SND-30).
VOICE_CHAIN = [("highpass", {"f": 75}), ("equalizer", {"f": 170, "t": "q", "w": 1, "g": 1.5}), ("equalizer", {"f": 380, "t": "q", "w": 1.2, "g": -2}),
               ("equalizer", {"f": 3800, "t": "q", "w": 1, "g": 2}), ("highshelf", {"f": 10000, "g": 1.5}), ("deesser", {"i": 0.35, "m": 0.5, "f": 0.55}),
               ("acompressor", {"threshold": "-22dB", "ratio": 3, "attack": 8, "release": 120, "makeup": "4dB"}),
               ("agate", {"threshold": 0.02, "ratio": 6, "range": 0.015, "attack": 3, "release": 90})]
def voice_af(chain=VOICE_CHAIN): return ",".join(f"{n}=" + ":".join(f"{k}={v}" for k, v in p.items()) for n, p in chain)

def assemble_voice(pr):
    import librosa
    edl = pr.json("edl.json"); clips = {c["id"]: c for c in edl["clips"]}; resampled = set(); df_model = set()
    for stem in ("df", "raw"):
        out, cache = [], {}
        for s in edl["segments"]:
            if s["clip"] not in cache:
                p = _df_out(pr, s["clip"]) if stem == "df" else pr.e("voice", "in", f"{s['clip']}.wav")
                if stem == "df": df_model.add(re.sub(r".*_(DeepFilterNet\w*)\.wav$", r"\1", os.path.basename(p)))
                y, sr = sf.read(p); y = y.mean(1) if y.ndim > 1 else y
                if sr != SR: resampled.add(sr)
                cache[s["clip"]] = librosa.resample(y, orig_sr=sr, target_sr=SR) if sr != SR else y
            y = cache[s["clip"]]; off = max(0, clips[s["clip"]]["in"] - PAD)
            seg = y[int((s["in"] - off) * SR):int((s["out"] - off) * SR)].copy(); f = int(.008 * SR)
            seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f); out.append(seg)
        sf.write(pr.e(f"voice_{stem}.wav"), np.concatenate(out), SR)
    sh([C.get("ffmpeg"), "-v", "error", "-y", "-i", pr.e("voice_df.wav"), "-af", voice_af(), "-ar", str(SR), pr.e("voice_final.wav")])
    steps = [{"name": "extract", "generative": False, "params": {"rate": SR, "channels": 1, "tool": "ffmpeg"}},
             {"name": "deepfilternet", "generative": False, "params": {"model": ",".join(sorted(df_model)) or "DeepFilterNet", "pad_s": PAD,
                                                                        "binary": os.path.basename(C.get("deepfilter"))}},
             {"name": "pause_tighten", "generative": False, "params": {"max_gap_s": MAXGAP, "breath_s": BREATH, "edge_s": EDGE, "threshold_db_below_peak": 32}}]
    if resampled: steps.append({"name": "resample", "generative": False, "params": {"from": sorted(resampled), "to": SR, "tool": "librosa"}})
    steps.append({"name": "crossfade", "generative": False, "params": {"ms": 8}})
    steps += [{"name": n, "generative": False, "params": dict(p, tool="ffmpeg")} for n, p in VOICE_CHAIN]
    pr.save_json("voice_chain.json", {"steps": steps, "output": "voice_final.wav"})

# ------------------------------------------------------------------ 3. cut-time words
def words(pr):
    S = _S(pr); lang = whisper_language(pr, S); info = {"requested": lang}
    to16k(pr.e("voice_final.wav"), pr.e("v16.wav"))
    W = whisper_words(pr.e("v16.wav"), pr.e("v_whisper"), lang=lang, S=S, info=info); pr.save_json("words.json", W)
    _record_language(pr, info); return len(W)

# ------------------------------------------------------------------ 4. plate (single lossless decode, conform applied in it)
def _crop_filter(cp, s_in, s_out):
    if not cp: return None
    w, h, ax = cp["w"], cp["h"], cp["axis"]; path = cp.get("path")
    def f(x): return f"crop={w}:{h}:{x}:0" if ax == "x" else f"crop={w}:{h}:0:{x}"
    if not path: return f(int(cp["offset"]))
    T = np.array([p[0] for p in path]); V = np.array([p[1] for p in path], float)
    dt = (T[1] - T[0]) if len(T) > 1 else 1.0
    ts = np.arange(s_in - dt, s_out + dt + 1e-9, dt); vs = np.round(np.interp(ts, T, V)).astype(int)
    if vs.max() - vs.min() <= 1: return f(int(np.median(vs)))
    if len(ts) > 48: k = np.unique(np.linspace(0, len(ts) - 1, 48).round().astype(int)); ts, vs = ts[k], vs[k]
    tr = [round(t - s_in, 4) for t in ts]                 # filter time t starts at 0 at the -ss seek point
    e = str(vs[-1])
    for i in range(len(tr) - 2, -1, -1):
        e = f"if(lt(t,{tr[i + 1]}),{vs[i]}+({vs[i + 1] - vs[i]})*(t-({tr[i]}))/{round(tr[i + 1] - tr[i], 4)},{e})"
    e = f"if(lt(t,{tr[0]}),{vs[0]},{e})"
    return f"crop={w}:{h}:'{e}':0" if ax == "x" else f"crop={w}:{h}:0:'{e}'"

def plate_vf(plan, seg, size, fps):
    """the -vf chain for one segment: [SAR fix] [HDR->SDR] [fps conform] [face/centre crop] scale-to-canvas"""
    W, H = size; f = []
    if plan.get("sar_fix"): f.append("scale=trunc(iw*sar/2)*2:ih,setsar=1")
    if plan.get("tonemap_filter"): f.append(plan["tonemap_filter"])
    if plan.get("fps_convert"): f.append(f"fps={fps.numerator}/{fps.denominator}")
    c = _crop_filter(plan.get("crop"), seg["in"], seg["out"])
    if c: f.append(c)
    f.append(f"scale={W}:{H}:flags=lanczos+accurate_rnd+full_chroma_int")
    if len(f) > 1: f.append("setsar=1")
    return ",".join(f)

def _edl_rate(edl):
    fr = edl.get("fps_rational")
    return Fraction(*fr) if fr else Fraction(edl["fps"]).limit_denominator(1001)

def plate(pr):
    edl = pr.json("edl.json"); F = edl["fps"]; fr = _edl_rate(edl); S = _S(pr); os.makedirs(pr.e("plate"), exist_ok=True)
    size = tuple(edl.get("size") or canvas(pr, S))
    srcs = sorted({s.get("src") or primary(pr) for s in edl["segments"]}, key=lambda s: (s != primary(pr), s))
    _, plans = conform_sources(pr, [norm_src(pr, s) for s in srcs], S)
    def job(s):
        out = pr.e("plate", f"{s['id']}.mkv")
        if os.path.exists(out): return
        src = norm_src(pr, s.get("src")); plan = plans[src]; P = plan["probe"]
        tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if plan.get("tonemap") else []
        sh([C.get("ffmpeg"), "-v", "error", "-y", "-ss", f"{s['in']:.5f}", "-i", _abs(pr, src), "-map", f"0:v:{P['stream']}", "-frames:v", str(round((s["out"] - s["in"]) * F)),
            "-vf", plate_vf(plan, s, size, fr), "-c:v", "ffv1", "-level", "3", "-pix_fmt", "yuv420p10le", *tags, out])
    with ThreadPoolExecutor(4) as ex: list(ex.map(job, edl["segments"]))

# ------------------------------------------------------------------ 5. matte (RVM)
def matte(pr, variant="resnet50", ds=0.4):
    import torch, av
    sys.path.insert(0, C.get("rvm_repo")); from model import MattingNetwork
    dev = C.device(); m = MattingNetwork(variant).eval().to(dev)
    m.load_state_dict(torch.load(C.get("rvm_weights"), map_location="cpu"))
    os.makedirs(pr.e("matte"), exist_ok=True); edl = pr.json("edl.json"); rate = _edl_rate(edl)
    for s in edl["segments"]:
        out = pr.e("matte", f"{s['id']}.mkv")
        if os.path.exists(out): continue
        cin = av.open(pr.e("plate", f"{s['id']}.mkv")); vs = cin.streams.video[0]
        o = av.open(out, "w"); st = o.add_stream("ffv1", rate=rate); st.pix_fmt = "gray"; st.width, st.height = vs.width, vs.height
        rec = [None] * 4
        with torch.no_grad():
            for fr in cin.decode(vs):
                x = torch.from_numpy(fr.to_ndarray(format="rgb24")).permute(2, 0, 1).float().div(255).unsqueeze(0).to(dev)
                _, pha, *rec = m(x, *rec, downsample_ratio=ds)
                for p in st.encode(av.VideoFrame.from_ndarray(pha[0, 0].clamp(0, 1).mul(255).byte().cpu().numpy(), format="gray")): o.mux(p)
        for p in st.encode(): o.mux(p)
        o.close(); cin.close()

# ------------------------------------------------------------------ 6. faces (box + landmarks)
def faces(pr):
    import av, cv2
    W, H = tuple(pr.json("edl.json").get("size") or canvas(pr)); dw, dh = W // 2, H // 2; kx, ky = W / dw, H / dh
    det = cv2.FaceDetectorYN.create(C.get("yunet"), "", (dw, dh), .6, .3, 5000); out = {}
    for s in pr.json("edl.json")["segments"]:
        rows, last = [], None
        with av.open(pr.e("plate", f"{s['id']}.mkv")) as cin:
            for f in cin.decode(video=0):
                im = cv2.resize(f.to_ndarray(format="bgr24"), (dw, dh), interpolation=cv2.INTER_AREA)
                _, fc = det.detect(im)
                if fc is not None and len(fc): last = [round(float(v) * (kx if i % 2 == 0 else ky), 1) for i, v in enumerate(max(fc, key=lambda r: r[2] * r[3])[:14])]
                rows.append(last)
        first = next((r for r in rows if r), [round(380 * W / 1080), round(420 * H / 1920), round(320 * W / 1080), round(420 * H / 1920)] + [0] * 10)
        out[s["id"]] = [r or first for r in rows]     # [x, y, w, h, reye x,y, leye x,y, nose x,y, rmouth x,y, lmouth x,y]
    pr.save_json("faces.json", out)

def run_all(pr, steps=("transcribe_raw",)):
    for s in steps: print(s, "->", globals()[s](pr), flush=True)
