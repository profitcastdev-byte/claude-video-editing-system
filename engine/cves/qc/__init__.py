"""QC runner: every gate from knowledge-base/QC-GATES.md measurable on the delivered file, stems, word timings, face
landmarks, the timeline and the renderer element log. Writes Edit/QC-REPORT.txt (one line per gate; details on failures).
Statuses: FAIL blocks delivery; WARN needs an eye; PASS; N/A (the gate cannot apply to this spine: presenter gates on a
voiceover / music / broll edit, voice gates on a music / broll edit; docs/FORMATS.md). Gate ids match QC-GATES.md."""
import os, re, json, subprocess, tempfile
import numpy as np, cv2, soundfile as sf
from .. import config as C
from . import audio_gates as AG

# gates that measure the presenter (face, matte, plate, punch-in, skin) or the voice: N/A when the spine has none
NA_NO_AROLL = {"CUT-03", "CUT-05", "FRAME-01", "FRAME-02", "FRAME-03", "FRAME-04", "FRAME-05", "FRAME-06", "FRAME-09", "FRAME-10", "FRAME-11",
               "RET-22", "RET-22b", "COL-03", "COL-04", "COL-05", "COL-06", "COL-07", "COL-08", "COL-09", "COL-10", "COL-12", "GFX-25", "GFX-26"}
NA_NO_VOICE = {"CUT-01", "CUT-02", "SND-04", "SND-11", "SND-19", "SND-22", "SND-30", "RET-01", "RET-03", "PLAT-11", "STORY-09", "STORY-10"}
NA_NO_CAPTIONS = {"PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07", "PLAT-08", "PLAT-09", "PLAT-10", "GFX-16"}

def small_size(w, h, area=270 * 480):
    """an analysis size with the canvas aspect and ~270x480 pixels (never squashes a landscape frame into portrait)"""
    k = (area / (w * h)) ** .5; return max(2, int(round(w * k / 2)) * 2), max(2, int(round(h * k / 2)) * 2)

def na_gate(gate, spine, captions):
    """wrap gate(): gates that cannot apply to this spine report N/A (never FAIL)"""
    from .. import spines as SP
    no_ar, no_vo = not SP.has_aroll(spine), not SP.has_voice(spine)
    def g(gid, ok, summary, details="", status=None):
        if no_ar and gid in NA_NO_AROLL: return gate(gid, True, f"not applicable: the {spine} spine has no presenter", status="N/A")
        if no_vo and gid in NA_NO_VOICE: return gate(gid, True, f"not applicable: the {spine} spine has no voice", status="N/A")
        if not captions and gid in NA_NO_CAPTIONS: return gate(gid, True, f"not applicable: no captions in this {spine} edit", status="N/A")
        return gate(gid, ok, summary, details, status)
    return g

import time as _time
_T0 = [0.0]
def tick(label):
    """CVES_QC_TIMING=1: wall-clock checkpoints on stderr (profiling the QC families; no effect on any gate)"""
    if os.environ.get("CVES_QC_TIMING"):
        import sys; t = _time.time(); import resource; ch = resource.getrusage(resource.RUSAGE_CHILDREN)
        sys.stderr.write(f"[qc {_time.strftime('%H:%M:%S', _time.localtime(t))}.{int(t % 1 * 10)} pid {os.getpid()} cpu {_time.process_time():.0f}s children {ch.ru_utime + ch.ru_stime:.0f}s] {label}\n"); sys.stderr.flush()


# ---------------------------------------------------------------- shared measurements of the master (qc/cache.py)
def picture_pass(pr, video, SW, SH, review=False):
    """the one OpenCV decode of the master: per-frame mean luma step at SWxSH (float32, as before), YuNet face present
    on every 2nd frame (copied to the next; detection on a worker thread while the next frames decode), frame 0 luma and
    the frame count. Streamed: no frame list in memory. Cached per master in Edit/qc_cache/. With `review` the same
    decode also keeps the small grey frames `cves review` reads (off by default: a full-size area resize per frame costs
    QC ~20 s of CPU; review caches its own decode instead)."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from . import cache as QCC
    meta = {"size": [SW, SH], "yunet": os.path.basename(C.get("yunet")), "cv2": cv2.__version__}
    hit = QCC.load_arrays(pr, video, "picture", meta)
    if hit is not None and (not review or QCC.load_arrays(pr, video, "review_gray") is not None):
        return {"diff": hit["diff"], "face": hit["face"].astype(bool), "g0": float(hit["g0"]), "N": int(hit["N"])}
    cap = cv2.VideoCapture(video); diff, faces, prev, g0, i = [0.0], {}, None, 0.0, 0
    rg, rsize = [], None
    tl = threading.local(); jobs = int(os.environ.get("CVES_QC_FACE_JOBS", "") or 1)
    def detect(im):
        if not hasattr(tl, "det"): tl.det = cv2.FaceDetectorYN.create(C.get("yunet"), "", (SW, SH), .7, .3, 5000)
        _, f = tl.det.detect(im); return f is not None and len(f) > 0
    slots = threading.BoundedSemaphore(4 * jobs)
    def job(im):
        try: return detect(im)
        finally: slots.release()
    with ThreadPoolExecutor(jobs) as ex:
        while True:
            ok, fr = cap.read()
            if not ok: break
            sm = cv2.resize(fr, (SW, SH), interpolation=cv2.INTER_AREA)
            if i % 2 == 0: slots.acquire(); faces[i] = ex.submit(job, sm)
            g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if prev is None: g0 = float(g.mean())
            else: diff.append(float(np.mean(np.abs(g - prev))))
            prev = g
            if review:
                if rsize is None: rsize = small_size(fr.shape[1], fr.shape[0], area=160 * 284)
                rg.append(cv2.cvtColor(cv2.resize(fr, rsize, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY))
            i += 1
        cap.release()
        N = i; face = np.zeros(N, bool)
        for k, fu in faces.items():
            face[k] = fu.result()
            if k + 1 < N: face[k + 1] = face[k]
    d = np.array(diff[:N] if N else [], np.float64)
    out = {"diff": d, "face": face, "g0": g0, "N": N}
    QCC.save_arrays(pr, video, "picture", {"diff": d, "face": face, "g0": np.float64(g0), "N": np.int64(N)}, meta)
    if review and rsize is not None:
        QCC.save_arrays(pr, video, "review_gray", {"g": np.stack(rg)}, {"size": list(rsize)})
    return out


def media_pass(pr, video, ret_size=None):
    """one ffmpeg decode for three measurements: blackdetect runs (PLAT-12), the luma of every 12th frame (COL-02) and,
    with ret_size=(w, h), the area-scaled grey frames of the retention gates. A split filter graph: each branch sees the
    same decoded frames the three separate commands saw (byte-identical outputs, DECISIONS.md). Cached per master."""
    from . import cache as QCC
    meta = {"ret": list(ret_size) if ret_size else None}
    hit = QCC.load_arrays(pr, video, "media", meta)
    if hit is not None:
        return {"blk": [tuple(map(float, x)) for x in hit["blk"].reshape(-1, 2)], "pct": float(hit["pct"]), "ext": int(hit["ext"]),
                "ysize": int(hit["ysize"]), "ret": hit["ret"] if ret_size else None}
    d = tempfile.mkdtemp(prefix="cves_qcmedia_"); yp, rp = os.path.join(d, "y.raw"), os.path.join(d, "r.raw")
    ff = C.get("ffmpeg"); vfB = "select='not(mod(n,12))',extractplanes=y"
    graph = f"[0:v]split={3 if ret_size else 2}[a][b]{'[c]' if ret_size else ''};[a]blackdetect=d=0.03:pix_th=0.10[ao];[b]{vfB}[bo]"
    if ret_size: graph += f";[c]scale={ret_size[0]}:{ret_size[1]}:flags=area,format=gray[co]"
    cmd = [ff, "-hide_banner", "-i", video, "-filter_complex", graph, "-map", "[ao]", "-f", "null", "-",
           "-map", "[bo]", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-y", yp]
    if ret_size: cmd += ["-map", "[co]", "-f", "rawvideo", "-pix_fmt", "gray", "-y", rp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        if r.returncode == 0:
            bd = r.stderr; Y = np.fromfile(yp, np.uint8); R_ = np.fromfile(rp, np.uint8) if ret_size else None
        else:            # an ffmpeg without the split graph: the three commands as before
            bd = subprocess.run([ff, "-hide_banner", "-i", video, "-vf", "blackdetect=d=0.03:pix_th=0.10", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
            Y = np.frombuffer(subprocess.run([ff, "-v", "error", "-i", video, "-vf", vfB, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True).stdout, np.uint8)
            R_ = np.frombuffer(subprocess.run([ff, "-v", "error", "-i", video, "-vf", f"scale={ret_size[0]}:{ret_size[1]}:flags=area,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"],
                                              capture_output=True).stdout, np.uint8) if ret_size else None
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)
    blk = [(float(x), float(y)) for x, y in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)]
    pct = float(((Y < 16) | (Y > 235)).mean() * 100); ext = int(((Y < 5) | (Y > 246)).sum())
    ret = None
    if ret_size:
        w, h = ret_size; n = len(R_) // (w * h); ret = R_[:n * w * h].reshape(n, h, w)
    QCC.save_arrays(pr, video, "media", {"blk": np.array(blk, np.float64).reshape(-1, 2), "pct": np.float64(pct), "ext": np.int64(ext),
                                         "ysize": np.int64(Y.size), "ret": ret if ret is not None else np.zeros(0, np.uint8)}, meta)
    return {"blk": blk, "pct": pct, "ext": ext, "ysize": int(Y.size), "ret": ret}


# every threshold below comes from the style profile (cves.style; docs/STYLE.md). The QC gates judge the edit against
# the look the client asked for, not a fixed house look. Platform constants (safe zone, delivery size) live in `platform:`.

def run(pr, video, fast=False, stage=None, tier=None):
    """tier: full (default) | fast (= fast=True: no CUT-01 / CUT-03 whisper re-checks) | draft (qc/tiers.py: the cheap
    gates, never a delivery stamp). Independent families measure side by side: the extra gates in a worker process,
    ffmpeg / whisper on threads, the OpenCV picture pass here; rows are joined in the serial order, so the report and
    Edit/qc.json are the ones the serial run wrote (DECISIONS.md, QC speed)."""
    from .tiers import resolve, DRAFT
    from . import cache as QCC, _worker
    from concurrent.futures import ThreadPoolExecutor
    tier = resolve(tier, fast); fast = tier != "full"; draft = tier == "draft"; _T0[0] = _time.time(); tick(f"start tier {tier}")
    old_wd = QCC.WHISPER_DIR; QCC.WHISPER_DIR = pr.e("qc_cache", "whisper")
    bg = ThreadPoolExecutor(6)
    try: return _run(pr, video, tier, fast, draft, DRAFT, bg, _worker)
    finally:
        bg.shutdown(wait=True); QCC.WHISPER_DIR = old_wd


def _run(pr, video, tier, fast, draft, DRAFT, bg, _worker):
    R = []; tmp = tempfile.mkdtemp()
    def gate0(gid, ok, summary, details="", status=None):
        if draft and gid not in DRAFT: return
        R.append((gid, status or ("PASS" if ok else "FAIL"), summary, details))
    def sh(cmd, text=True): return subprocess.run(cmd, capture_output=True, text=True) if text else subprocess.run(cmd, capture_output=True)
    def lufs(path):        # audio only (-vn): the same ebur128 numbers without decoding the picture
        r = sh([C.get("ffmpeg"), "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
        I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); P = re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", r)
        return (float(I[-1]) if I else float("nan")), (float(P[-1]) if P else float("nan"))
    from .. import style as STY
    S = STY.load(pr); E = pr.edit; Q = E.get("qc", {}) or {}; TLm = pr.json("timeline.json", {})
    FPS = TLm.get("fps") or 30.0; FR = TLm.get("fps_rational")
    from .. import gfx as G, spines as SP
    PW, PH = TLm.get("size") or G.canvas_of(S, pr); G.set_canvas(PW, PH)
    from .. import platforms as PF      # platform.target: UI safe zone as fractions of THIS frame (any canvas size)
    META_ZONE = tuple(G.safe_zone(S, (PW, PH)) or (0, 0, PW, PH)); HOUSE_MARGIN = round(S.get("platform.margin", 60) * min(PW, PH) / 1080, 1)
    CAP_BOTTOM = PF.caption_bottom(S, PH) if PF.profile_fits(S, PW, PH) else None
    ZONE_NAME = S.get("platform.target") or "style platform.safe_zone"
    spine = TLm.get("spine") or SP.spine_of(E); has_ar, has_vo = SP.has_aroll(spine), SP.has_voice(spine)
    els_ = pr.e("elements.jsonl")
    captions = not os.path.exists(els_) or any('"role": "caption"' in l for l in open(els_, encoding="utf-8"))
    gate = na_gate(gate0, spine, captions)
    def na(*ids):
        for g_ in ids: gate(g_, True, f"not applicable: the {spine} spine", status="N/A")
    SW, SH = small_size(PW, PH)
    G_ = S.get("grammar") or {}
    faces = pr.json("faces.json", {})

    # ---------------- the independent families start now and are joined where the serial run measured them
    j_extra = _worker.Job("extra", pr, video, spine, captions, tier)             # extra gates: their own process
    from . import retention as RT
    j_lufs = bg.submit(lufs, video)
    tail = Q.get("brand_tail", []) if has_vo else []
    def tail_words():
        tw_ = os.path.join(tmp, "tail.wav"); sh([C.get("ffmpeg"), "-v", "error", "-y", "-sseof", "-6", "-i", pr.e("voice_final.wav"), "-ac", "1", "-ar", "16000", tw_])
        return re.sub(r"[^a-z ]", " ", AG._whisper(tw_, lang=__import__("cves.ingest", fromlist=["x"]).whisper_language(pr)).lower()).split()
    j_tail = bg.submit(tail_words) if tail and not draft else None
    j_words = bg.submit(AG.words, pr.e("voice_final.wav"), pr.e("voice_raw.wav")) if not fast and has_vo else None
    j_stut = bg.submit(AG.stutters, pr) if not fast and has_ar else None

    # ---------------- delivery
    pj = json.loads(sh([C.get("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,width,height,sample_aspect_ratio,r_frame_rate,avg_frame_rate,codec_name,profile,pix_fmt,color_space,color_primaries,color_transfer,color_range,sample_rate,bit_rate:format=duration,size", "-of", "json", video]).stdout)
    v = next(s for s in pj["streams"] if s["codec_type"] == "video"); a = next((s for s in pj["streams"] if s["codec_type"] == "audio"), {})
    ret_size = None
    if not draft:
        from fractions import Fraction as _Fr
        ret_size = RT.gray_size(int(v["width"]), int(v["height"])); ret_fps = float(_Fr(v.get("r_frame_rate", "30/1")))
        j_media = bg.submit(media_pass, pr, video, ret_size)
        j_audio = bg.submit(RT.decode_audio, video)
    for nm_, j_ in (("lufs", j_lufs), ("tail", j_tail), ("words", j_words), ("stutters", j_stut)) + ((("media", j_media), ("audio", j_audio)) if not draft else ()):
        if j_ is not None: j_.add_done_callback(lambda f, nm_=nm_: tick(f"{nm_} done"))
    tick("probe done")
    gate("DEL-01", (v.get("width"), v.get("height")) == (PW, PH) and v.get("sample_aspect_ratio", "1:1") in ("1:1", "N/A"), f"{v.get('width')}x{v.get('height')}")
    want = f"{FR[0]}/{FR[1]}" if FR else None
    from fractions import Fraction as _F
    rr = v.get("r_frame_rate", "0/1"); same = rr == v.get("avg_frame_rate") and (want is None or _F(rr) == _F(want))
    gate("DEL-02", same, f"{rr} (timeline {want or FPS}); constant frame rate")
    head = open(video, "rb").read(300000); fast_start = (head.find(b"moov") < head.find(b"mdat")) if b"mdat" in head else True
    ok3 = v.get("codec_name") == "h264" and v.get("profile") == "High" and v.get("pix_fmt") == "yuv420p" and a.get("codec_name") == "aac" and a.get("sample_rate") == "48000" and int(a.get("bit_rate") or 0) >= 128000 and fast_start
    gate("DEL-03", ok3, f"{v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} | {a.get('codec_name')} {a.get('sample_rate')} | faststart {fast_start}")
    dur = float(pj["format"]["duration"]); lo, hi = Q.get("duration") or S.get("platform.duration") or [0, 1e9]
    gate("DEL-04", lo <= dur <= hi, f"{dur:.2f} s (brief {lo}-{hi} s)")
    m = re.search(rb"x264 - core .{0,3000}?options: (.{0,1500}?)\x00", open(video, "rb").read(4_000_000), re.S); opts = m.group(1).decode(errors="ignore") if m else ""
    gate("DEL-05", "crf=16" in opts and "tune=film" not in opts, "x264 crf 16, no tune=film" if "crf=16" in opts else opts[:80])
    tags = (v.get("color_space"), v.get("color_primaries"), v.get("color_transfer"), v.get("color_range"))
    gate("COL-01", tags == ("bt709", "bt709", "bt709", "tv"), "/".join(map(str, tags)))

    # ---------------- picture (decode once small; streamed, never the whole clip in memory)
    if not draft:
        P_ = picture_pass(pr, video, SW, SH); N = P_["N"]; T = N / FPS; diff = P_["diff"]; face = P_["face"]; g0 = P_["g0"]
        if G_.get("face_on_first_frame"): gate("RET-13", face[0] and g0 > 16, f"face at frame 0: {bool(face[0])}, luma {g0:.0f}")
        else: gate("RET-13", g0 > 16, f"frame 0 not black (luma {g0:.0f}); face {bool(face[0])} (style does not require one)")
        ev = np.where(diff > max(6.0, np.median(diff[1:]) * 4))[0]; first_ev = ev[0] / FPS if len(ev) else T
        gate("RET-09", first_ev <= 1.0, f"first visual event {first_ev:.2f} s")
        gate("RET-10", diff[1:16].mean() >= 3 * max(.05, np.percentile(diff[1:], 5)), f"frame-1 motion {diff[1:16].mean():.2f}")
        runs, cur = [], 0
        for x in face: cur = 0 if x else cur + 1; runs.append(cur)
        body = int(TLm.get("a_frames", N)); share = 1 - face[:body].mean(); nf = max(runs[:body] or [0]) / FPS   # body only: the end card is not a cutaway
        mx = G_.get("max_cutaway_s", 8); band = G_.get("cutaway_share")
        in_band = band is None or band[0] <= share <= band[1]
        gate("RET-22", nf <= mx and in_band, f"longest without face {nf:.1f} s (max {mx}); cutaway share {share:.0%}" + (f" (style {band[0]:.0%}-{band[1]:.0%})" if band else ""),
             status=None if nf <= mx else "FAIL") if any(face) else gate("RET-22", True, "no presenter in this edit: face pacing not applicable", status="PASS")
        MP = j_media.result(); blk = MP["blk"]
        gate("PLAT-12", not [b for b in blk if b[0] < .5 or b[1] > T - 1], f"{len(blk)} black runs")
        pct, ext = MP["pct"], MP["ext"]
        gate("COL-02", pct <= .5 and ext / max(1, MP["ysize"]) < 1e-5, f"{pct:.2f}% luma outside 16-235")
    else:        # draft: no decode. The frame count is the video packet count (one packet per frame), for PLAT-11 and the header
        try: N = int(json.loads(sh([C.get("ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "json", video]).stdout)["streams"][0]["nb_read_packets"])
        except (Exception, SystemExit): N = int(round(dur * FPS))
        T = N / FPS

    tick("picture done")
    # ---------------- timeline + element log gates
    segs = TLm.get("segments", []); cuts = TLm.get("cutaways", []); zoom = TLm.get("zoom", {}); creep = TLm.get("creep", 0.0)
    in_broll = lambda t: any(c.get("broll") and c["start"] <= t < c["end"] for c in cuts)
    step_min = S.get("framing.min_step", 1.15)
    in_cut = lambda t: any(c["start"] <= t < c["end"] for c in cuts)
    steps = []
    for x, y in zip(segs[:-1], segs[1:]):
        if in_cut(y["t0"] + .5 / FPS) or in_cut(x["t1"] - .5 / FPS): continue
        za, zb = zoom.get(x["id"], 1) * (1 + creep), zoom.get(y["id"], 1); r = max(za, zb) / min(za, zb)
        if r < step_min - 1e-6: steps.append(f"{x['id']} -> {y['id']}: {r:.3f}x")
    gate("CUT-05", not steps, f"punch-in step >= {step_min}x at every direct A-roll cut", "\n".join(steps))
    snap = TLm.get("snap"); big = [k for k, z in zoom.items() if z >= 1.4] + (["snap"] if snap and snap[2] >= 1.4 else [])
    xm = S.get("framing.extreme_max", 1); gate("FRAME-09", len(big) <= xm, f"{len(big)} extreme punch-in(s) (max {xm})")
    # FRAME-11: upscale factor actually applied to source pixels. ingest records the plate scale (source px -> canvas px);
    # without it we derive it from the source's short side vs the canvas width (a vertical crop of a landscape source).
    ing = pr.json("ingest.json", {}) or {}
    try:
        st0 = json.loads(sh([C.get("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height,width", "-of", "json", pr.raw]).stdout)["streams"][0]
        sw, shh = int(st0.get("width", PW)), int(st0.get("height", PH))
    except (Exception, SystemExit): sw, shh = PW, PH
    plate = ing.get("plate_scale") or max(PW / max(min(sw, shh) if sw > shh else sw, 1), PH / max(shh if shh >= sw else max(sw, shh), 1))
    zmax = max(list(zoom.values()) + [snap[2] if snap else 1]) * (1 + creep); up = zmax * plate
    gate("FRAME-11", up <= 1.0, f"max zoom {zmax:.2f}x x plate scale {plate:.2f} = {up:.2f}x of native source pixels",
         "above 1.0 the punch-in is upscaled: soft detail. Shoot 4K or cap framing.zoom_levels", status="PASS" if up <= 1.0 else ("WARN" if up <= 1.5 else "FAIL"))
    els = [json.loads(l) for l in open(pr.e("elements.jsonl"), encoding="utf-8")] if os.path.exists(pr.e("elements.jsonl")) else []
    if els:
        seg_by_f = {}
        for s in segs:
            for k in range(s["n"]): seg_by_f[s["f0"] + k] = (s["id"], k)
        over, zone_bad, early, margin_bad = [], [], [], []
        first_seen = {}
        for e in els:
            first_seen.setdefault(e["id"], e)
            x0, y0, x1, y1 = e["bbox"]
            if e["role"] in ("caption", "chest") and e["f"] in seg_by_f and has_ar and not in_broll(e["f"] / FPS):    # no face on B-roll frames
                sid, k = seg_by_f[e["f"]]; fb = faces.get(sid, [[0] * 14])[min(k, len(faces.get(sid, [0])) - 1)]
                t = e["f"] / FPS; s = next(q for q in segs if q["id"] == sid)
                z = zoom.get(sid, 1) * (1 + creep * min(1, max(0, (t - s["t0"]) / max(.5, s["t1"] - s["t0"]))))
                if snap and snap[0] <= t < snap[1]: z = snap[2]
                cx, cy = fb[0] + fb[2] / 2, (PH if sid in TLm.get("lift", []) else fb[1] + fb[3] / 2 - fb[3] * .05)
                tx = min(0, max(PW - z * PW, cx - z * cx)); ty = min(0, max(PH - z * PH, cy - z * cy))
                fx0, fy0, fx1, fy1 = fb[0] * z + tx, fb[1] * z + ty, (fb[0] + fb[2]) * z + tx, (fb[1] + fb[3]) * z + ty
                pad = .1 * (fx1 - fx0)
                if x0 < fx1 + pad and x1 > fx0 - pad and y0 < fy1 + pad * .5 and y1 > fy0 - pad:
                    over.append(f"f{e['f']} {e['id']} '{(e.get('text') or '')[:30]}' bbox {e['bbox']} vs face {[round(fx0), round(fy0), round(fx1), round(fy1)]}")
            if e["role"] in ("caption", "chest", "cutaway", "end") and e.get("text"):
                if min(x0, y0) < HOUSE_MARGIN or x1 > PW - HOUSE_MARGIN or y1 > PH - HOUSE_MARGIN: margin_bad.append(f"f{e['f']} {e['id']} {e['bbox']}")
                if (x0 < META_ZONE[0] or y0 < META_ZONE[1] or x1 > META_ZONE[2] or y1 > META_ZONE[3]): zone_bad.append((e["id"], e["bbox"], e["role"]))
                elif CAP_BOTTOM is not None and e["role"] == "caption" and y1 > CAP_BOTTOM: zone_bad.append((e["id"], e["bbox"], e["role"]))   # under the platform's caption line
        gate("FRAME-01", not over, f"text/graphics vs face on {len(els)} element-frames", "\n".join(over[:12]))
        gate("PLAT-01", not margin_bad, f"all text inside the {HOUSE_MARGIN} px margin", "\n".join(margin_bad[:8]))
        # CTA, prices, pills and end-card elements must sit inside the Reels zone. An on-chest brand logo under a close framing
        # cannot fit between chin and y 1248; it warns (the end card carries the in-zone logo). DECISIONS.md #2
        key_roles = [z for z in zone_bad if any(k in z[0] for k in ("price", "pill", "end."))]
        others = sorted(set(z[0] for z in zone_bad if z not in key_roles))
        gate("PLAT-02", not key_roles, f"platform safe zone ({ZONE_NAME}) {META_ZONE}: {len(set(z[0] for z in key_roles))} key elements outside, {len(others)} other text elements outside",
             "\n".join(sorted(set(f"{z[0]} {z[1]}" for z in key_roles))[:8]) + ("\nother (warn): " + ", ".join(others[:10]) if others else ""),
             status=None if key_roles else ("WARN" if others else "PASS"))
        for i_, e in first_seen.items():
            if e.get("t_key") is not None and e["role"] in ("cutaway", "chest", "roto") and e["f"] / FPS < e["t_key"] - .25:
                early.append(f"{i_} shown at {e['f'] / FPS:.2f}s, its word at {e['t_key']:.2f}s")
        gate("GFX-01", not early, "nothing shown before it is said (<= 0.25 s lead for entries)", "\n".join(early[:10]), status=None if not early else "WARN")
        icons = [e for e in els if e.get("asset") and "/" in str(e["asset"]) and e.get("role") != "media"
                 and not str(e["asset"]).startswith(("assets/icons", "Brand", "assets/logos", "Assets/"))]
        gate("GFX-23", not icons, "icons only from the Material set")
    else:
        gate("ELEMENT-LOG", False, "Edit/elements.jsonl missing: render with `cves render` first", status="WARN")
    if not draft:
        holds = sorted(set([round(s["t0"], 2) for s in segs] + [round(x / FPS, 2) for x in ev] + [round(T, 2)]))
        worst = max((b - a, a) for a, b in zip(holds[:-1], holds[1:]))
        ms = G_.get("max_shot_s", 4.0); gate("RET-16", worst[0] <= ms, f"longest visual hold {worst[0]:.2f} s at {worst[1]:.2f} s", "frame-diff misses small graphic events: check by eye", status=None if worst[0] <= ms else "WARN")

    tick("els done")
    # ---------------- sound
    I, P = j_lufs.result(); LT = S.get("sound.master_lufs", -14); TP = S.get("sound.true_peak", -1.0)
    gate("SND-01", LT - .5 <= I <= LT + .5, f"{I:.1f} LUFS (target {LT})", status=None if not (LT - .5 <= I <= LT + .5) else ("WARN" if I > LT else "PASS"))
    gate("SND-02", P <= TP, f"true peak {P:.1f} dBTP (max {TP})")
    if has_vo and os.path.exists(pr.e("stems", "voice.wav")):
        vo, sr = sf.read(pr.e("voice_final.wav")); vo = vo.mean(1) if vo.ndim > 1 else vo
        mu, _ = sf.read(pr.e("stems", "music.wav")); mu = mu.mean(1) if mu.ndim > 1 else mu
        sx, _ = sf.read(pr.e("stems", "sfx.wav")); n = min(len(vo), len(mu), len(sx))
        from .. import guide as GD
        if GD.is_slot(pr):     # music.slot: platform: the sound is added in the app; the master must carry no music at all
            mpk = 20 * np.log10(np.abs(mu).max() + 1e-12) if len(mu) else -240.0
            gate("SND-04", mpk <= -60, f"music.slot: platform: music stem peak {mpk:.0f} dBFS (none in the master); the bed level is set in the app (POSTING.md)")
        else:
            sf.write(os.path.join(tmp, "bed.wav"), mu[:n] + sx[:n], sr); sf.write(os.path.join(tmp, "vo.wav"), sf.read(pr.e("stems", "voice.wav"))[0][:n], sr)
            lu = lufs(os.path.join(tmp, "bed.wav"))[0] - lufs(os.path.join(tmp, "vo.wav"))[0]
            bed = (E.get("music") or {}).get("bed_lu", S.get("sound.bed_lu", -10))
            gate("SND-04", bed - 2.5 <= lu <= bed + 3, f"music+SFX bed {lu:+.1f} LU vs voice (target {bed})")
        pm, _ = sf.read(pr.e("mix_premaster.wav")); clip = int((np.abs(pm) >= .999).sum())
        gate("SND-03", clip == 0, f"{clip} clipped samples")
        h = int(.02 * sr); dbv = 20 * np.log10(np.array([np.sqrt(np.mean(vo[i:i + h] ** 2)) for i in range(0, len(vo) - h, h)]) + 1e-9)
        gate("SND-19", np.percentile(dbv, 5) <= -60, f"voice floor (p5) {np.percentile(dbv, 5):.1f} dBFS")
        onset = next((i * .02 for i, x in enumerate(dbv) if x > dbv.max() - 30), 99); gate("RET-03", onset <= .25, f"first speech {onset:.2f} s")
        last = (len(dbv) - next(i for i, x in enumerate(dbv[::-1]) if x > dbv.max() - 30)) * .02
        gate("PLAT-11", T - last <= 3.0, f"{T - last:.2f} s after the last word (end card <= 3 s)")
    if not has_vo:
        na("SND-04", "SND-19", "RET-03", "PLAT-11", "CUT-02", "SND-30")
        pm, _ = sf.read(pr.e("mix_premaster.wav")); clip = int((np.abs(pm) >= .999).sum()); gate("SND-03", clip == 0, f"{clip} clipped samples")
    if has_vo:
        g = AG.gaps(pr.e("voice_final.wav")); gate("CUT-02", not g, f"{len(g)} gaps > 0.25 s", "\n".join(f"gap at {a:.2f}s {b:.2f}s" for a, b in g))
    vc = pr.json("voice_chain.json")           # written by ingest: the processors actually run on this voice
    if not has_vo: pass
    elif vc is None: gate("SND-30", False, "Edit/voice_chain.json missing: re-run `cves ingest`", status="WARN")
    else:
        gen = [p for p in vc.get("steps", []) if p.get("generative")]
        gate("SND-30", not gen, "voice chain: " + " -> ".join(p.get("name", "?") for p in vc.get("steps", [])), "generative steps: " + ", ".join(p["name"] for p in gen))

    tick("sound done")
    # ---------------- words, hook, sign-off (whisper)
    Wd = pr.json("words.json", []); words = [re.sub(r"[^a-z0-9']", "", w[2].lower()) for w in Wd]
    kws = Q.get("topic_keywords", [])
    if kws:
        kw_t = next((Wd[i][0] for i, w in enumerate(words) if any(k.split()[0] in w for k in kws)), 99)
        gate("RET-01", kw_t <= 2.0, f"first topic keyword {kw_t:.2f} s", status=None if kw_t <= 3 else "FAIL")
    hd = " ".join(w[2] for w in Wd if w[0] < 3).lower()
    bans = [p for p in [r"craziest", r"won'?t believe", r"watch till the end", r"wait for it", r"stay till the end", r"^\s*(hi|hello|hey) (guys|everyone)"] if re.search(p, hd)]
    gate("RET-08", not bans, "no banned openers in the first 3 s", ", ".join(bans))
    if j_tail is not None:
        tt = j_tail.result(); joined = "".join(tt[-6:])
        gate("STORY-10", all(t in joined for t in tail), f"sign-off heard: {' '.join(tt[-5:])}")
        gate("STORY-09", bool(tt) and any(t in tt[-1] for t in tail), f"last spoken word: {tt[-1] if tt else '?'}")
    if not fast:
        if has_vo:
            r, bad, ok = j_words.result()
            gate("CUT-01", ok, f"voice stem vs raw: match {r:.3f}", "\n".join(bad))
        else: na("CUT-01")
        if has_ar: st = j_stut.result(); gate("CUT-03", not st, f"{len(pr.json('edl.json')['segments'])} kept segments checked verbatim", "\n".join(st))
        else: na("CUT-03")
    tick("whisper joined")
    R.extend(j_extra.result())                                       # run_extra's rows, through the same N/A wrapper (and tier filter)
    tick("extra joined")
    try:
        from ..assets import qc_assets; qc_assets(pr, gate)          # AST-01: every asset registered, unchanged, with provenance
    except ImportError: pass
    if not draft:                                                     # RET-24..RET-32: hook, interrupts, loop, payoff, platform, dead air, guide
        try: RT.run_retention(pr, video, gate, S, pre={"frames": j_media.result()["ret"], "fps": ret_fps, "audio": j_audio.result()})
        except Exception as e:
            done = {r[0] for r in R}
            for g in RT.IDS:
                if g not in done: gate(g, False, f"not measured: {type(e).__name__}: {e}", status="WARN")
    tick("retention done")
    if draft: R[:] = [r for r in R if r[0] in DRAFT]

    order = {"FAIL": 0, "WARN": 1, "PASS": 2, "N/A": 3}; R.sort(key=lambda x: (order.get(x[1], 4), x[0]))
    nf, nw, npass, nna = (sum(r[1] == s for r in R) for s in ("FAIL", "WARN", "PASS", "N/A"))
    if draft:
        lines = [f"DRAFT QC (NOT DELIVERABLE)  {os.path.basename(video)}  ({T:.2f} s, {PW}x{PH}, spine {spine})",
                 f"{nf} FAIL   {nw} WARN   {npass} PASS   {nna} N/A   of {len(R)} draft gates; the picture, speech and retention gates were NOT run.",
                 "This is a draft check for iteration: it never stamps the master. Run `cves qc` (full) before `cves deliver`.", ""]
    else: lines = [f"QC REPORT  {os.path.basename(video)}  ({T:.2f} s, {PW}x{PH}, spine {spine})", f"{nf} FAIL   {nw} WARN   {npass} PASS   {nna} N/A   of {len(R)} gates", ""]
    for gid, st_, summ, det_ in R:
        lines.append(f"[{st_:4s}] {gid:10s} {summ}")
        if st_ not in ("PASS", "N/A") and det_: lines += ["             " + l for l in det_.splitlines() if l.strip()]
    if draft:        # never Edit/qc.json or QC-REPORT.txt: a draft cannot stand in for the delivery QC (cves deliver, qc_guard)
        lines.append("\nDRAFT QC: not a delivery check. `cves deliver` needs `cves qc`.")
        dp = (lambda n: os.path.join(pr.work, n)) if getattr(pr, "work", None) else pr.e   # a draft build (Edit/draft/) keeps its own report
        open(dp("QC-DRAFT.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        write_stamp(pr, video, R, fast=True, out=dp("qc_draft.json"), tier="draft")
        return nf, "\n".join(lines)
    open(pr.e("QC-REPORT.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    write_stamp(pr, video, R, fast=fast, tier=tier)     # Edit/qc.json: the machine-readable stamp `cves deliver` and the hook check
    return nf, "\n".join(lines)


def sha256(path, bs=1 << 20):
    from .cache import sha256 as _s
    return _s(path, bs)


def write_stamp(pr, video, R, fast=False, out=None, tier=None):
    """qc.json = {video, sha256, fail, warn, pass, gates: [{id, status, summary}], created, cves_version, fast, tier}.
    `cves deliver` refuses unless fail == 0 AND sha256 matches the master it is about to deliver (docs/DELIVERY.md).
    A draft stamp is never written to Edit/qc.json (it goes to Edit/qc_draft.json with deliverable: false)."""
    if tier == "draft" and os.path.abspath(out or pr.e("qc.json")) == os.path.abspath(pr.e("qc.json")):
        raise ValueError("a draft QC never writes Edit/qc.json")
    import datetime
    from .. import __version__
    from .cache import master_sha      # memoised on (path, size, mtime): the QC cache key and the stamp hash the file once
    d = {"video": os.path.abspath(video), "sha256": master_sha(video), "size": os.path.getsize(video),
         "fail": sum(r[1] == "FAIL" for r in R), "warn": sum(r[1] == "WARN" for r in R), "pass": sum(r[1] == "PASS" for r in R),
         "na": sum(r[1] == "N/A" for r in R),
         "gates": [{"id": g, "status": s, "summary": m} for g, s, m, _ in R],
         "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "cves_version": __version__, "fast": bool(fast)}
    if tier: d["tier"] = tier
    if tier == "draft": d["deliverable"] = False
    with open(out or pr.e("qc.json"), "w", encoding="utf-8") as f: json.dump(d, f, indent=1, ensure_ascii=False)
    return d


def run_stage(pr, stage):
    """early gates that need no render. story: after `cves select` (voice + edl). plan: after edit.yaml is filled."""
    R = []
    def gate0(gid, ok, summary, details="", status=None): R.append((gid, status or ("PASS" if ok else "FAIL"), summary, details))
    from .. import style as STY, spines as SP
    gate = na_gate(gate0, SP.spine_of(pr.edit), True)
    S = STY.load(pr); G_ = S.get("grammar") or {}; Q = pr.edit.get("qc", {}) or {}; step_min = S.get("framing.min_step", 1.15)
    if stage == "story" and not SP.has_voice(SP.spine_of(pr.edit)):
        for g_ in ("CUT-02", "CUT-03", "STORY-01", "STORY-17"): gate(g_, True, f"not applicable: the {SP.spine_of(pr.edit)} spine has no story voice", status="N/A")
    elif stage == "story":
        g = AG.gaps(pr.e("voice_final.wav")); gate("CUT-02", not g, f"{len(g)} gaps > 0.25 s", "\n".join(f"gap at {a:.2f}s {b:.2f}s" for a, b in g))
        st = AG.stutters(pr); gate("CUT-03", not st, f"{len(pr.json('edl.json')['segments'])} kept segments checked verbatim", "\n".join(st))
        # STORY-17: every chosen word is heard. Each clip's own span of voice_final.wav vs its text: (word recall)
        from .. import align as AL, ingest as ING_
        thr = float(Q.get("words_recall_min") or S.get("qc.words_recall_min", .85))
        try:
            rows = AL.clip_recall(pr, ING_.whisper_language(pr, S), names=Q.get("names") or S.get("qc.names") or [])
            got = [r for r in rows if r["score"] is not None]; skip = [r["clip"] for r in rows if r["score"] is None]
            strict = (Q.get("words_edges") if Q.get("words_edges") is not None else S.get("qc.words_edges", True)) is not False
            edge_ = lambda r: strict and any(r.get("edge") or [])          # a lost first / last word = a clipped take
            low = [r for r in got if r["score"] < thr or edge_(r)]
            sk = f"; {len(skip)} clip(s) without text: skipped ({', '.join(map(str, skip))})" if skip else ""
            if not got:
                gate("STORY-17", False, f"no clip has text: (add each clip's words to selects.yaml){sk}", status="WARN")
            else:
                gate("STORY-17", not low, f"{len(got)} clip(s) heard, lowest word recall {min(r['score'] for r in got):.0%} (>= {thr:.0%}"
                     f"{', first and last words kept' if strict else ''}){sk}",
                     "\n".join(f"{r['clip']} ({r['score']:.0%}, cut {r['span'][0]:.2f}-{r['span'][1]:.2f}s): missing {' '.join(r['missing'])}"
                                f"{' [' + ' and '.join(n for n, e in zip(('first word', 'last word'), r['edge']) if e) + ' lost: clipped take]' if edge_(r) else ''}"
                                f" | heard: {r['heard'][:100]}" for r in low))
        except Exception as e:
            gate("STORY-17", False, f"not measured: {type(e).__name__}: {e}", status="WARN")
        tail = Q.get("brand_tail", [])
        if tail:
            tmp = tempfile.mkdtemp(); tw_ = os.path.join(tmp, "tail.wav")
            subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-sseof", "-6", "-i", pr.e("voice_final.wav"), "-ac", "1", "-ar", "16000", tw_])
            tt = re.sub(r"[^a-z ]", " ", AG._whisper(tw_, lang=__import__("cves.ingest", fromlist=["x"]).whisper_language(pr)).lower()).split(); joined = "".join(tt[-6:])
            gate("STORY-10", all(t in joined for t in tail), f"sign-off heard: {' '.join(tt[-5:])}")
            gate("STORY-09", bool(tt) and any(t in tt[-1] for t in tail), f"last spoken word: {tt[-1] if tt else '?'}")
        import soundfile as _sf; dur = _sf.info(pr.e("voice_final.wav")).duration; lo, hi = Q.get("duration") or S.get("platform.duration") or [0, 1e9]
        gate("DEL-04", lo <= dur <= hi, f"cut length {dur:.1f} s (brief {lo}-{hi} s)")
        # story structure from the beat tags in selects.yaml / edl.json (H P A PR O C; X = cut)
        edl = pr.json("edl.json"); beat_of = {c["id"]: c.get("beat") for c in edl["clips"]}
        F = edl["fps"]; t = 0.0; spans = []
        for s in edl["segments"]:
            L = round((s["out"] - s["in"]) * F) / F; spans.append((beat_of.get(s["clip"]), t, t + L)); t += L
        T = t; tagged = [b for b, _, _ in spans if b]
        from .. import structure as STR
        order = STR.beats_of(S); sname = STR.name_of(S) if not G_.get("beats") else (STR.preset_for(order) or "custom")
        if not tagged:
            gate("STORY-01", False, f"no beat tags: add `beat:` ({'/'.join(order)}, structure {sname}) to each clip in selects.yaml", status="WARN")
        else:
            run = []
            for b in tagged:
                if not run or run[-1] != b: run.append(b)
            present = [b for b in order if b in run]; rank = [order.index(b) for b in run if b in order]
            ok_order = all(x <= y for x, y in zip(rank[:-1], rank[1:])) or bool("PR" in order and rank and rank[0] == order.index("PR") and all(x <= y for x, y in zip(rank[1:-1], rank[2:])))
            unknown = sorted({b for b in run if b not in order and b != "X"})
            gate("STORY-01", set(order) <= set(run) and ok_order, f"beats in order ({sname}: {' > '.join(order)}): {' > '.join(run)}",
                 "\n".join(x for x in ["" if set(order) <= set(run) else f"missing: {', '.join(b for b in order if b not in run)}",
                                        f"not in this structure: {', '.join(unknown)} (grammar.structure / grammar.beats)" if unknown else ""] if x))
            first = lambda b: next((a for x, a, _ in spans if x == b), None)
            pS, prS, oS, cS, rS = first("P"), first("PR"), first("O"), first("C"), first("R")
            # each structure gate applies only where its beats are in the order
            if "P" in order and pS is not None: gate("STORY-13", pS <= .25 * T, f"problem starts at {pS:.1f} s = {pS / T:.0%} of runtime (<= 25%)")
            if prS is not None: gate("STORY-05", prS <= .50 * T, f"proof starts at {prS:.1f} s = {prS / T:.0%} (<= 50%)", status=None if prS <= .5 * T else "WARN")
            if "O" in order and prS is not None and oS is not None: gate("STORY-07", oS > prS, f"offer/price after the proof ({oS:.1f} s > {prS:.1f} s)")
            elif "R" in order and prS is not None and rS is not None: gate("STORY-07", rS > prS, f"risk reversal after the proof ({rS:.1f} s > {prS:.1f} s)")
            if cS is not None: gate("STORY-09b", cS >= .80 * T, f"CTA starts at {cS:.1f} s = {cS / T:.0%} (target >= 85%, CALIBRATE)", status="PASS" if cS >= .85 * T else "WARN")
    else:
        from ..render import Timeline
        from .. import templates as T
        TL = Timeline(pr); FPS = TL.FPS
        bad = [c.get("id") for c in TL.cuts if c.get("template") not in T.REGISTRY]
        gate("PLAN-00", not bad, "every template exists", ", ".join(map(str, bad)))
        steps = []
        for x, y in zip(TL.segs[:-1], TL.segs[1:]):
            if TL.in_cut(y["t0"] + .5 / FPS) or TL.in_cut(x["t1"] - .5 / FPS) or x["id"] not in TL.zoom or y["id"] not in TL.zoom: continue
            za, zb = TL.zoom[x["id"]] * (1 + TL.creep), TL.zoom[y["id"]]; r = max(za, zb) / min(za, zb)
            if r < step_min - 1e-6: steps.append(f"{x['id']} -> {y['id']}: {r:.3f}x")
        gate("CUT-05", not steps, f"punch-in step >= {step_min}x at every direct A-roll cut", "\n".join(steps))
        big = [k for k, z in TL.zoom.items() if z >= 1.4] + (["snap"] if TL.snap and TL.snap[2] >= 1.4 else [])
        xm = S.get("framing.extreme_max", 1); gate("FRAME-09", len(big) <= xm, f"{len(big)} extreme punch-in(s) (max {xm})")
        rm = G_.get("roto_max", 4); gate("GFX-25", len(TL.roto) <= rm, f"{len(TL.roto)} roto moments (max {rm})")
        share = sum(c["end"] - c["start"] for c in TL.cuts) / max(TL.T_END, 1e-6); band = G_.get("cutaway_share")   # B-roll over A-roll is a cutaway too
        if band: gate("RET-22", band[0] <= share <= band[1], f"cutaway share {share:.0%} of the body (style {band[0]:.0%}-{band[1]:.0%})")
        else: gate("RET-22", True, f"cutaway share {share:.0%} (style sets no band)")
        cut_t = sorted([(c["start"], c["end"]) for c in TL.cuts]); longest, last = 0, 0.0
        for a, b in cut_t: longest = max(longest, b - a); last = b
        mx = G_.get("max_cutaway_s", 8); gate("RET-22b", longest <= mx, f"longest cutaway {longest:.1f} s (face back within {mx} s)")
        early = []
        for c in TL.cuts:
            for k, v in (c.get("params") or {}).items():
                if k.endswith("_at") and isinstance(v, (int, float)) and v < c["start"] - .3: early.append(f"{c['id']}.{k} {v} < cutaway start {c['start']:.2f}")
        gate("GFX-01", not early, "no element keyed before its cutaway starts", "\n".join(early), status=None if not early else "WARN")
    order = {"FAIL": 0, "WARN": 1, "PASS": 2, "N/A": 3}; R.sort(key=lambda x: (order.get(x[1], 4), x[0]))
    nf = sum(r[1] == "FAIL" for r in R)
    lines = [f"QC ({stage} stage)  {nf} FAIL  {sum(r[1] == 'WARN' for r in R)} WARN  {sum(r[1] == 'PASS' for r in R)} PASS  {sum(r[1] == 'N/A' for r in R)} N/A", ""]
    for gid, st_, summ, det_ in R:
        lines.append(f"[{st_:4s}] {gid:10s} {summ}")
        if st_ not in ("PASS", "N/A") and det_: lines += ["             " + l for l in det_.splitlines() if l.strip()]
    return nf, "\n".join(lines)
