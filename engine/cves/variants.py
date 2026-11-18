"""Delivery variants, driven by edit.yaml `variants:` (docs/DELIVERY.md). Every variant goes through QC; one that fails is not
delivered (the manifest lists it as failed, with the reason).

  variants:
    reframes: ["4:5", "1:1", "16:9"]          # face-aware crops of the QC'd master, any master aspect to any target (narrower targets
                                              # crop the width, wider ones the height; portrait -> landscape = crop on a blurred fill)
    hooks:    [{id: hook_b, first: [04_competitors_0], title_card: {template: ..., duration: 1.5, params: {...}}}]
    end_cards: [{id: end_b, end_card: {template: logo_end, duration: 1.25, params: {...}}}]
    music:    [{id: music_b, file: Music/other.wav, drop_track: 12.0, drop_cut: 31.13, bed_lu: -8}]
    cutdowns: [15, 30]                         # or [{id: cut15, seconds: 15, segments: [ids...]}]

Re-timed variants (hooks, cut-downs) build a variant project in a temp folder (symlinks to the plates and mattes, re-timed
edl.json / words.json / voice_final.wav / edit.yaml) and re-run render + mix + encode + `cves qc --fast` there. End-card
variants re-render the same way without re-timing. Music variants re-mix and re-mux only (the master picture is copied)."""
import os, re, json, copy, shutil, subprocess, tempfile
import numpy as np
from fractions import Fraction
from . import config as C, style as STY
from .encode import stream_params, video_args, audio_args

REFRAMES = ("4:5", "1:1", "16:9")
STOP = set("a an the and or but so to of in on at for with is are was were be been it its it's this that i you we they he she "
           "my your our their me us them do does did not no yes just very really can will would could should have has had "
           "what who where when how why which there here then than as by from up down out if about into over".split())
NON_TIME = {"y", "ys", "x", "xs", "width", "height", "w", "h", "size", "value", "top", "zoom", "duration", "scale", "gain", "radius",
            "opacity", "alpha", "cols", "rows_n", "decimals", "pitch"}


# ------------------------------------------------------------------ planning
def vid(aspect): return aspect.replace(":", "x")

def plan(pr, requested=None):
    """-> list of variant specs {id, kind, ...}. requested: None = all in edit.yaml, [] = none, or ids / kinds / ad-hoc
    ("4:5", "cut15", "reframes", "cutdowns", "hooks", "end_cards", "music", "all")."""
    V = pr.edit.get("variants") or {}
    specs = []
    for a in V.get("reframes") or []: specs.append({"id": vid(str(a)), "kind": "reframe", "aspect": str(a)})
    for h in V.get("hooks") or []: specs.append(dict(h, kind="hook"))
    for e in V.get("end_cards") or []: specs.append(dict(e, kind="end_card"))
    for m in V.get("music") or []: specs.append(dict(m, kind="music"))
    for c in V.get("cutdowns") or []:
        c = {"seconds": c} if isinstance(c, (int, float)) else dict(c)
        specs.append(dict(c, kind="cutdown", id=c.get("id") or f"cut{int(c['seconds'])}"))
    for s in specs:
        if not s.get("id"): raise SystemExit(f"edit.yaml variants: every {s['kind']} needs an `id`")
    if requested is None: return specs
    out = []
    kinds = {"reframes": "reframe", "hooks": "hook", "end_cards": "end_card", "music": "music", "cutdowns": "cutdown"}
    for r in requested:
        r = r.strip()
        if not r: continue
        if r == "all": out += specs; continue
        if r in kinds: out += [s for s in specs if s["kind"] == kinds[r]]; continue
        hit = [s for s in specs if s["id"] in (r, vid(r))]
        if hit: out += hit; continue
        if re.fullmatch(r"\d+(\.\d+)?:\d+(\.\d+)?", r): out.append({"id": vid(r), "kind": "reframe", "aspect": r}); continue
        m = re.fullmatch(r"cut(\d+)", r)
        if m: out.append({"id": r, "kind": "cutdown", "seconds": int(m.group(1))}); continue
        raise SystemExit(f"unknown variant '{r}': define it under edit.yaml variants: or use 4:5 / 1:1 / 16:9 / cut15 / cut30")
    seen, uniq = set(), []
    for s in out:
        if s["id"] not in seen: seen.add(s["id"]); uniq.append(s)
    return uniq


# ------------------------------------------------------------------ small helpers
def _ff(): return C.get("ffmpeg")

def probe(path):
    r = subprocess.run([C.get("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,codec_name,profile,width,height,sample_aspect_ratio,"
                        "r_frame_rate,avg_frame_rate,nb_frames,pix_fmt,color_space,color_primaries,color_transfer,color_range,sample_rate,bit_rate"
                        ":format=duration,size", "-of", "json", path], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")

def _yunet(w, h):
    import cv2
    return cv2.FaceDetectorYN.create(C.get("yunet"), "", (w, h), .7, .3, 5000)

def _frames_valid(pr, master, n):
    """True if Edit/frames holds exactly the frames of this master (same count, none newer than the master file)"""
    d = pr.e("frames")
    if not os.path.isdir(d): return False
    pngs = [e for e in os.scandir(d) if e.name.endswith(".png")]
    return len(pngs) == n and max(e.stat().st_mtime for e in pngs) <= os.path.getmtime(master) + 1

def iter_frames(pr, master, n, size, use_png):
    import cv2
    W, H = size
    if use_png:
        for i in range(n): yield cv2.imread(pr.e("frames", f"{i:05d}.png"), cv2.IMREAD_COLOR)
        return
    p = subprocess.Popen([_ff(), "-v", "error", "-i", master, "-vf", "scale=in_color_matrix=bt709:in_range=tv:flags=accurate_rnd+full_chroma_int,format=bgr24",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"], stdout=subprocess.PIPE)
    fb = W * H * 3
    for _ in range(n):
        b = p.stdout.read(fb)
        if len(b) < fb: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.stdout.close(); p.wait()


# ------------------------------------------------------------------ reframes
def _aspect(a):
    x, y = (float(v) for v in a.split(":")); return x, y

def reframe_geometry(aspect, W, H, S):
    """reframe from any master (docs/DELIVERY.md): a wider target crops the height (full width; `axis` y), a narrower one
    crops the width (full height; `axis` x). A landscape target from a portrait master puts a foreground crop on a blurred
    fill (`wide`, output height = master width). -> {axis, crop (px along the axis), crop_h, out, fg, wide}"""
    ax, ay = _aspect(aspect); ev = lambda v: int(round(v / 2)) * 2; t, m = ax / ay, W / H
    if abs(t - m) < .01: raise SystemExit(f"reframe {aspect}: the {W}x{H} master already has that aspect")
    if t > m:
        if ax > ay and H > W:    # portrait master -> landscape: foreground crop on a blurred fill, output height = master width
            fx, fy = _aspect(str(S.get("delivery.reframe.wide_fg", "4:5")))
            ch = min(H, ev(W * fy / fx)); oh = W; ow = ev(oh * ax / ay)
            return {"axis": "y", "crop": ch, "crop_h": ch, "out": (ow, oh), "fg": (ev(oh * W / ch), oh), "wide": True}
        ch = min(H, ev(W * ay / ax)); return {"axis": "y", "crop": ch, "crop_h": ch, "out": (W, ch), "fg": None, "wide": False}
    cw = min(W, ev(H * ax / ay)); return {"axis": "x", "crop": cw, "crop_h": H, "out": (cw, H), "fg": None, "wide": False}

def _load_elements(pr, axis="y"):
    """{frame: [lo, hi, ids]} extents along the crop axis of caption / chest text and of graphics"""
    cap, gfx = {}, {}
    p = pr.e("elements.jsonl")
    if not os.path.exists(p): return cap, gfx
    with open(p, encoding="utf-8") as f:
        for l in f:
            e = json.loads(l)
            if (e.get("alpha") or 0) < .3: continue
            tgt = cap if e["role"] in ("caption", "chest") else gfx if e["role"] in ("cutaway", "end") else None
            if tgt is None: continue
            x0, y0, x1, y1 = e["bbox"]
            if axis == "x": y0, y1 = x0, x1
            cur = tgt.get(e["f"])
            tgt[e["f"]] = [y0, y1, [e["id"]]] if cur is None else [min(cur[0], y0), max(cur[1], y1), cur[2] + [e["id"]]]
    return cap, gfx

def _shots(tl, n, fps):
    b = {0, n}
    for s in tl.get("segments", []): b.add(int(s["f0"]))
    for c in tl.get("cutaways", []): b.add(int(round(c["start"] * fps))); b.add(int(round(c["end"] * fps)))
    sn = tl.get("snap")
    if sn: b.add(int(round(sn[0] * fps))); b.add(int(round(sn[1] * fps)))
    if tl.get("a_frames"): b.add(int(tl["a_frames"]))
    b = sorted(x for x in b if 0 <= x <= n); return [(a, c) for a, c in zip(b[:-1], b[1:]) if c > a]

def _gauss(x, sigma):
    if sigma <= 0 or len(x) < 3: return x
    r = int(3 * sigma); k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sigma ** 2)); k /= k.sum()
    return np.convolve(np.pad(x, r, mode="edge"), k, "valid")

def crop_path(n, H, ch, shots, is_gfx, face, cap, gfx, S, fps, fy=None):
    """per-frame crop start along the axis (y0, ints) + notes. Static crop per shot when one crop can hold face + captions;
    else a smoothed path. Captions/chest text are hard constraints (never cut); the face is kept when it can be; graphics
    are centred. H / ch: the master and crop length along the axis; face {i: (c_other, c_axis, lo, hi)}."""
    R = S.get("delivery.reframe") or {}; m = R.get("margin", 24); fy = R.get("face_y", .40) if fy is None else fy
    y0 = np.zeros(n); notes = {"caption_cut": [], "face_cut": [], "gfx_cut": set(), "moving_shots": 0}
    hiF = H - ch
    for a, b in shots:
        lo = np.zeros(b - a); hi = np.full(b - a, float(hiF)); d = np.full(b - a, hiF / 2)
        graphic = all(is_gfx[a:b])
        if graphic:      # one crop for the whole graphic shot, centred on everything drawn in it
            ys = [gfx[i] for i in range(a, b) if i in gfx] + [cap[i] for i in range(a, b) if i in cap]
            if ys:
                g0, g1 = min(v[0] for v in ys), max(v[1] for v in ys)
                if g1 - g0 + 2 * m <= ch: c = np.clip((g0 + g1) / 2 - ch / 2, max(0, g1 + m - ch), min(hiF, g0 - m))
                else:
                    c = (g0 + g1) / 2 - ch / 2
                    for v in ys:
                        if v[0] < c or v[1] > c + ch: notes["gfx_cut"].update(v[2])
                y0[a:b] = np.clip(c, 0, hiF)
            else: y0[a:b] = hiF / 2
            continue
        for k, i in enumerate(range(a, b)):
            f = face.get(i)
            if f is not None:
                cx, cy, top, bot = f; d[k] = cy - fy * ch
                flo, fhi = bot + m - ch, top - m
            else: flo, fhi = 0, hiF
            if i in cap:
                c0, c1 = cap[i][0], cap[i][1]; clo, chi = c1 + m - ch, c0 - m
                l2, h2 = max(clo, flo), min(chi, fhi)
                if l2 > h2:
                    l2, h2 = clo, chi
                    if f is not None: notes["face_cut"].append(i)
                if l2 > h2: notes["caption_cut"].append(i); l2 = h2 = (c0 + c1) / 2 - ch / 2
            else:
                l2, h2 = flo, fhi
                if l2 > h2: l2 = h2 = (f[1] - ch / 2) if f else hiF / 2
            lo[k], hi[k] = max(0, min(l2, hiF)), min(hiF, max(h2, 0))
        if not any(i in face for i in range(a, b)): d[:] = hiF * .35
        else:   # fill missing detections from neighbours
            idx = [k for k, i in enumerate(range(a, b)) if i in face]
            d = np.interp(np.arange(b - a), idx, d[idx])
        L, U = lo.max(), hi.min()
        if L <= U: y0[a:b] = np.clip(np.median(d), L, U); continue
        notes["moving_shots"] += 1; p = np.clip(d, lo, hi); sg = R.get("smooth_s", .4) * fps
        for _ in range(4): p = np.clip(_gauss(p, sg), lo, hi)
        y0[a:b] = p
    notes["gfx_cut"] = sorted(notes["gfx_cut"])
    return np.round(y0).astype(int), notes

def detect_faces(frames, is_gfx, n):
    """{frame: (cx, cy, top, bottom)} in full-res px, YuNet on a quarter-size copy of every A-roll frame"""
    import cv2
    out, det = {}, None
    for i, fr in enumerate(frames):
        if i >= n: break
        if is_gfx[i]: continue
        h, w = fr.shape[:2]; sw, sh = w // 4, h // 4
        if det is None: det = _yunet(sw, sh)
        _, f = det.detect(cv2.resize(fr, (sw, sh), interpolation=cv2.INTER_AREA))
        if f is not None and len(f):
            b = max(f, key=lambda r: r[2] * r[3] * r[14]); x, y, bw, bh = (float(v) * 4 for v in b[:4])
            out[i] = (x + bw / 2, y + bh / 2, y, y + bh, x, x + bw)
    return out

def reframe_all(pr, S, master, specs, outdir, title):
    """one decode pass per stage: detection, then every aspect encoded at once. -> {id: result}"""
    import cv2
    fr, (W, H) = stream_params(pr); fps = float(Fraction(fr)); tl = pr.json("timeline.json", {}) or {}
    pm = probe(master); vs = next(s for s in pm["streams"] if s["codec_type"] == "video")
    if (vs["width"], vs["height"]) != (W, H): raise SystemExit(f"master is {vs['width']}x{vs['height']}, timeline.json says {W}x{H}: re-encode first")
    n = int(vs.get("nb_frames") or round(float(pm["format"]["duration"]) * fps))
    use_png = _frames_valid(pr, master, n)
    a_frames = int(tl.get("a_frames") or n); cuts = tl.get("cutaways", [])
    is_gfx = [i >= a_frames or any(c["start"] <= i / fps < c["end"] for c in cuts) for i in range(n)]
    face = detect_faces(iter_frames(pr, master, n, (W, H), use_png), is_gfx, n)
    face_x = {i: (f[1], f[0], f[4], f[5]) for i, f in face.items()}            # the same faces seen along x (narrower targets)
    shots = _shots(tl, n, fps); els = {"y": _load_elements(pr, "y"), "x": _load_elements(pr, "x")}
    jobs = []
    for sp in specs:
        g = reframe_geometry(sp["aspect"], W, H, S)
        geo_fg = reframe_geometry(str(S.get("delivery.reframe.wide_fg", "4:5")), W, H, S) if g["wide"] else g
        cap, gfx = els[g["axis"]]
        if g["axis"] == "x": y0, notes = crop_path(n, W, g["crop"], shots, is_gfx, face_x, cap, gfx, S, fps, fy=.5)
        else: y0, notes = crop_path(n, H, geo_fg["crop_h"], shots, is_gfx, face, cap, gfx, S, fps)
        out = os.path.join(outdir, f"{title}_{sp['id']}.mp4"); ow, oh = g["out"]
        p = subprocess.Popen([_ff(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}", "-framerate", fr, "-i", "pipe:0",
                              "-i", master, "-map", "0:v", "-map", "1:a?"] + video_args(S) + ["-c:a", "copy", "-shortest", out], stdin=subprocess.PIPE)
        jobs.append({"spec": sp, "g": g, "ch": g["crop"] if g["axis"] == "x" else geo_fg["crop_h"], "y0": y0, "notes": notes, "out": out, "p": p})
    R = S.get("delivery.reframe") or {}; dim = float(R.get("fill_dim", .55)); blur = float(R.get("fill_blur", 40))
    for i, frm in enumerate(iter_frames(pr, master, n, (W, H), use_png)):
        for j in jobs:
            c = frm[:, j["y0"][i]:j["y0"][i] + j["ch"]] if j["g"]["axis"] == "x" else frm[j["y0"][i]:j["y0"][i] + j["ch"]]
            if j["g"]["wide"]:
                ow, oh = j["g"]["out"]; fw, fh = j["g"]["fg"]
                sc = ow / W; bh = int(H * sc); cy = int((j["y0"][i] + j["ch"] / 2) * sc)
                q = 8; small = cv2.resize(frm, (ow // q, bh // q), interpolation=cv2.INTER_AREA)
                small = cv2.GaussianBlur(small, (0, 0), max(.5, blur / q))
                ty = int(np.clip(cy - oh / 2, 0, bh - oh)) // q
                bg = cv2.resize(small[ty:ty + oh // q + 1], (ow, oh), interpolation=cv2.INTER_LINEAR)[:oh]
                if bg.shape[0] < oh: bg = cv2.resize(small, (ow, oh))
                bg = (bg.astype(np.float32) * dim).astype(np.uint8)
                fg = cv2.resize(c, (fw, fh), interpolation=cv2.INTER_AREA); x0 = (ow - fw) // 2
                bg[:, x0:x0 + fw] = fg; c = bg
            j["p"].stdin.write(np.ascontiguousarray(c).tobytes())
    res = {}
    for j in jobs:
        j["p"].stdin.close(); rc = j["p"].wait()
        if rc != 0: res[j["spec"]["id"]] = {"status": "failed", "reason": f"ffmpeg exit {rc}"}; continue
        res[j["spec"]["id"]] = {"file": j["out"], "y0": j["y0"], "notes": j["notes"], "geometry": j["g"], "crop_h": j["ch"],
                                "face": face, "is_gfx": is_gfx, "n": n, "fps": fps, "fr": fr, "source_frames": "Edit/frames (lossless)" if use_png else "decoded master"}
    return res

def qc_reframe(pr, S, master, r, aspect, master_stamp):
    """delivery gates for a reframe (the master's own gates already ran on the same pixels): size, fps, codec, tags, length,
    audio identical, captions inside the frame, face inside the frame where the master had one, graphics clipped."""
    import cv2
    Rg = []
    def gate(gid, ok, summary, details="", status=None): Rg.append((gid, status or ("PASS" if ok else "FAIL"), summary, details))
    v = r["file"]; pj = probe(v); vs = next(s for s in pj["streams"] if s["codec_type"] == "video"); a = next((s for s in pj["streams"] if s["codec_type"] == "audio"), {})
    pm = probe(master); am = next((s for s in pm["streams"] if s["codec_type"] == "audio"), {})
    ow, oh = r["geometry"]["out"]
    gate("RF-00", master_stamp and master_stamp.get("fail", 1) == 0, f"master QC: {master_stamp.get('fail', '?') if master_stamp else '?'} FAIL (a reframe inherits the master's gates)")
    gate("DEL-01", (vs.get("width"), vs.get("height")) == (ow, oh) and vs.get("sample_aspect_ratio", "1:1") in ("1:1", "N/A"), f"{vs.get('width')}x{vs.get('height')} (want {ow}x{oh}, {aspect})")
    gate("DEL-02", vs.get("r_frame_rate") == vs.get("avg_frame_rate") and Fraction(vs.get("r_frame_rate", "0/1")) == Fraction(r["fr"]), f"{vs.get('r_frame_rate')} (master {r['fr']})")
    head = open(v, "rb").read(300000); fs = (head.find(b"moov") < head.find(b"mdat")) if b"mdat" in head else True
    D = S.get("delivery") or {}
    ok3 = vs.get("codec_name") == "h264" and str(vs.get("profile", "")).lower() == str((D.get("video") or {}).get("profile", "high")).lower() and vs.get("pix_fmt") == "yuv420p" \
        and a.get("codec_name") == "aac" and fs == bool(D.get("faststart", True))
    gate("DEL-03", ok3, f"{vs.get('codec_name')} {vs.get('profile')} {vs.get('pix_fmt')} | {a.get('codec_name')} {a.get('sample_rate')} | faststart {fs}")
    col = D.get("color", "bt709"); tags = (vs.get("color_space"), vs.get("color_primaries"), vs.get("color_transfer"), vs.get("color_range"))
    gate("COL-01", tags == (col, col, col, "tv"), "/".join(map(str, tags)))
    nf = int(vs.get("nb_frames") or 0); gate("RF-LEN", abs(nf - r["n"]) <= 1, f"{nf} frames (master {r['n']})")
    gate("RF-AUD", a.get("codec_name") == am.get("codec_name") and a.get("bit_rate") == am.get("bit_rate") and a.get("sample_rate") == am.get("sample_rate"),
         f"audio copied from the master ({a.get('codec_name')} {a.get('bit_rate')} b/s)")
    nt = r["notes"]
    gate("RF-CAP", not nt["caption_cut"], f"captions/chest text inside the {aspect} frame on every frame" if not nt["caption_cut"] else f"{len(nt['caption_cut'])} frames with text cropped",
         ", ".join(f"f{i}" for i in nt["caption_cut"][:20]))
    # face presence in the ENCODED reframe vs the master detections (every 12th A-roll frame)
    idx = [i for i in range(0, r["n"], 12) if not r["is_gfx"][i] and i in r["face"]]
    want = set(idx); W2, H2 = ow, oh; sw, sh = W2 // 4 // 2 * 2, H2 // 4 // 2 * 2
    p = subprocess.run([_ff(), "-v", "error", "-i", v, "-vf", f"select='not(mod(n,12))',scale={sw}:{sh}", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"], capture_output=True)
    buf = np.frombuffer(p.stdout, np.uint8); det = _yunet(sw, sh); seen = 0; miss = []
    for k in range(len(buf) // (sw * sh * 3)):
        i = k * 12
        if i not in want: continue
        _, f = det.detect(buf[k * sw * sh * 3:(k + 1) * sw * sh * 3].reshape(sh, sw, 3))
        if f is not None and len(f): seen += 1
        else: miss.append(i)
    share = seen / max(1, len(want))
    gate("RF-FACE", share >= .95, f"face found on {seen}/{len(want)} sampled A-roll frames ({share:.0%})", ", ".join(f"f{i}" for i in miss[:20]),
         status=None if share >= .95 or share < .80 else "WARN")
    gate("RF-FACECUT", not nt["face_cut"], f"{len(nt['face_cut'])} frames where keeping the captions cost part of the face",
         ", ".join(f"f{i}" for i in nt["face_cut"][:20]), status="PASS" if not nt["face_cut"] else "WARN")
    gate("RF-GFX", not nt["gfx_cut"], f"{len(nt['gfx_cut'])} graphic elements taller than the {aspect} frame (cropped)", ", ".join(nt["gfx_cut"][:20]),
         status="PASS" if not nt["gfx_cut"] else "WARN")
    return Rg


# ------------------------------------------------------------------ variant projects
NO_LINK = {"edit.yaml", "edl.json", "words.json", "voice_final.wav", "frames", "elements.jsonl", "timeline.json", "mix.wav",
           "mix_premaster.wav", "mix.json", "stems", "QC-REPORT.txt", "qc.json", "variants", "exposure.json"}

def _link(src, dst):
    try: os.symlink(src, dst, target_is_directory=os.path.isdir(src))
    except OSError:
        if os.path.isdir(src): shutil.copytree(src, dst, symlinks=True)
        else: shutil.copy2(src, dst)

def make_project(pr, dst, keep=()):
    """a variant project: top-level folders linked, Edit/ inputs linked (big) or copied (small), writable outputs never linked.
    `keep` = names from NO_LINK to COPY over anyway (e.g. timeline.json for a music re-mux)."""
    os.makedirs(os.path.join(dst, "Edit"), exist_ok=True); os.makedirs(os.path.join(dst, "Export"), exist_ok=True)
    for name in os.listdir(pr.root):
        if name in ("Edit", "Export") or name.startswith("."): continue
        _link(os.path.realpath(pr.p(name)), os.path.join(dst, name))
    for name in os.listdir(pr.e()):
        src = pr.e(name); d = os.path.join(dst, "Edit", name)
        if name in NO_LINK and name not in keep: continue
        if name in keep or name == "exposure.json": shutil.copy2(src, d) if os.path.isfile(src) else shutil.copytree(src, d); continue
        if os.path.isfile(src) and os.path.getsize(src) < 20 << 20: shutil.copy2(src, d)
        else: _link(os.path.realpath(src), d)
    if os.path.exists(pr.e("exposure.json")) and not os.path.exists(os.path.join(dst, "Edit", "exposure.json")):
        shutil.copy2(pr.e("exposure.json"), os.path.join(dst, "Edit", "exposure.json"))
    from .project import Project
    return Project(dst)

def old_segments(pr):
    edl = pr.json("edl.json"); fps = edl["fps"]; out = []; f0 = 0
    beat = {c["id"]: c.get("beat") for c in edl.get("clips", [])}
    for s in edl["segments"]:
        n = round((s["out"] - s["in"]) * fps); out.append(dict(s, f0=f0, n=n, t0=f0 / fps, t1=(f0 + n) / fps, beat=beat.get(s.get("clip")))); f0 += n
    return edl, out, fps

def _shift_nums(o, d, lo, hi, key=None):
    if isinstance(o, bool) or o is None: return o
    if isinstance(o, (int, float)): return round(o + d, 4) if (key not in NON_TIME and lo <= o <= hi) else o
    if isinstance(o, list): return [_shift_nums(x, d, lo, hi, key) for x in o]
    if isinstance(o, dict): return {k: _shift_nums(v, d, lo, hi, k) for k, v in o.items()}
    return o

def retime(pr, order, E=None, trims=None):
    """re-time the edit for a new segment order/subset. -> (edit, edl, words, voice, notes). Rigid items (cutaways, roto, chest)
    move with their segments; an item whose segments are not all kept together is dropped (noted)."""
    import soundfile as sf
    E = copy.deepcopy(E if E is not None else pr.edit); edl, segs, fps = old_segments(pr); by = {s["id"]: s for s in segs}
    bad = [o for o in order if o not in by]
    if bad: raise SystemExit(f"variant: unknown segment(s) {bad}; ids are in Edit/edl.json")
    if len(set(order)) != len(order): raise SystemExit("variant: a segment is used twice")
    new_t0, t = {}, 0.0; f = 0
    trims = trims or {}; nn = {sid: min(by[sid]["n"], int(trims.get(sid, by[sid]["n"]))) for sid in order}    # tail trims (frames kept)
    for sid in order: new_t0[sid] = f / fps; f += nn[sid]
    T_new = f / fps; T_old = segs[-1]["t1"] if segs else 0
    delta = {sid: new_t0[sid] - by[sid]["t0"] for sid in order}; eps = .5 / fps; notes = []
    def seg_of(t, end=False):
        for s in segs:
            if (s["t0"] < t <= s["t1"] + 1e-6) if end else (s["t0"] - 1e-6 <= t < s["t1"]): return s
        return None
    def span(a, b): return [s for s in segs if s["t0"] < b - eps and s["t1"] > a + eps]
    def rigid(ss):
        ds = {round(delta[s["id"]], 6) for s in ss if s["id"] in delta}
        return (next(iter(ds)) if ss and all(s["id"] in delta for s in ss) and len(ds) == 1 else None)
    def mt(t, end=False):
        if t >= T_old - 1e-6 and end: return T_new
        s = seg_of(t, end); return round(t + delta[s["id"]], 4) if s and s["id"] in delta else None
    cuts = []
    for c in E.get("cutaways") or []:
        ss = span(c["start"], c["end"]); d = rigid(ss)
        if d is None:
            if any(s["id"] in delta for s in ss): notes.append(f"cutaway {c.get('id')} dropped (its shots are not all kept together)")
            continue
        lo, hi = c["start"] - 1.5, c["end"] + 1.5
        cuts.append(dict(c, start=round(c["start"] + d, 4), end=round(c["end"] + d, 4), params=_shift_nums(c.get("params") or {}, d, lo, hi)))
    E["cutaways"] = cuts
    roto = []
    for r in E.get("roto") or []:
        if r["segment"] not in delta: continue
        s = by[r["segment"]]; d = delta[r["segment"]]
        roto.append(dict(r, params=_shift_nums(r.get("params") or {}, d, s["t0"] - 1.5, s["t1"] + 1.5)))
    E["roto"] = roto
    chest = []
    for c in E.get("chest") or []:
        ids = [c["segment"]] if isinstance(c["segment"], str) else list(c["segment"]); kept = [i for i in ids if i in delta]
        if not kept: continue
        d = rigid([by[i] for i in kept])
        if d is None: notes.append(f"chest {ids} dropped (its shots were split up)"); continue
        lo, hi = min(by[i]["t0"] for i in ids) - 1.5, max(by[i]["t1"] for i in ids) + 1.5
        chest.append(dict(c, segment=kept if len(kept) > 1 else kept[0], params=_shift_nums(c.get("params") or {}, d, lo, hi)))
    E["chest"] = chest
    ar = E.get("aroll") or {}
    if ar.get("zoom"): ar["zoom"] = {k: v for k, v in ar["zoom"].items() if k in delta}
    if ar.get("snap"):
        a, b = mt(ar["snap"]["start"]), mt(ar["snap"]["end"], end=True)
        ar["snap"] = dict(ar["snap"], start=a, end=b) if a is not None and b is not None and abs((b - a) - (ar["snap"]["end"] - ar["snap"]["start"])) < 1e-3 else None
    E["aroll"] = ar
    cap = dict(E.get("captions") or {})
    if cap.get("hide"):
        hid = []
        for a, b in cap["hide"]:
            d = rigid(span(a, b))
            if d is not None: hid.append([round(a + d, 4), round(b + d, 4)])
        cap["hide"] = hid
    if cap.get("events"): cap.pop("events"); notes.append("captions.events dropped: rebuilt from the re-timed words")
    E["captions"] = cap
    sfx = dict(E.get("sfx") or {}); ex = []
    for x in sfx.get("extra") or []:
        m = mt(x["t"])
        if m is not None: ex.append(dict(x, t=m))
    sfx["extra"] = ex; E["sfx"] = sfx
    if E.get("transitions"): E["transitions"] = [dict(x, t=mt(x["t"])) for x in E["transitions"] if mt(x["t"]) is not None]
    mu = dict(E.get("music") or {})
    if mu.get("file") and mu.get("drop_cut") is not None:
        m = mt(mu["drop_cut"])
        if m is not None: mu["drop_cut"] = m
        else: notes.append("music drop shot not kept: track keeps the master's offset")
    E["music"] = mu
    words = []
    for w in pr.json("words.json", []) or []:
        s = seg_of((w[0] + w[1]) / 2)      # by midpoint: word times straddle cut points
        if s and s["id"] in delta and (w[0] + w[1]) / 2 < s["t0"] + nn[s["id"]] / fps: words.append([round(w[0] + delta[s["id"]], 4), round(w[1] + delta[s["id"]], 4)] + list(w[2:]))
    words.sort(key=lambda w: w[0])
    vo, sr = sf.read(pr.e("voice_final.wav"), always_2d=True); parts = []; fade = int(.004 * sr); prev = None
    for sid in order:
        s = by[sid]; a, b = int(round(s["t0"] * sr)), int(round((s["t0"] + nn[sid] / fps) * sr)); x = vo[a:b].copy()
        if prev is None or by[prev]["t1"] != s["t0"] or nn[prev] != by[prev]["n"]:      # a new join: 4 ms fades kill the click
            if len(x) > 2 * fade: x[:fade] *= np.linspace(0, 1, fade)[:, None]
            if parts and len(parts[-1]) > 2 * fade: parts[-1][-fade:] *= np.linspace(1, 0, fade)[:, None]
        parts.append(x); prev = sid
    tail = vo[int(round(T_old * sr)):]
    if order and order[-1] != segs[-1]["id"] and len(tail): tail = tail * 0
    voice = np.concatenate(parts + [tail]) if parts else vo[:0]
    new_edl = dict(edl, segments=[dict({k: v for k, v in by[sid].items() if k not in ("f0", "n", "t0", "t1", "beat")},
                                       **({"out": round(by[sid]["in"] + (nn[sid] + .25) / fps, 5)} if nn[sid] != by[sid]["n"] else {})) for sid in order])
    for sid in order:
        if nn[sid] != by[sid]["n"]: notes.append(f"{sid}: tail trimmed {(by[sid]['n'] - nn[sid]) / fps:.2f} s to end on a whole sentence")
    return E, new_edl, words, (voice, sr), notes

def _write_variant(vpr, E, edl=None, words=None, voice=None):
    import soundfile as sf
    vpr.save_edit(E)
    if edl is not None: vpr.save_json("edl.json", edl)
    if words is not None: vpr.save_json("words.json", words)
    if voice is not None: sf.write(vpr.e("voice_final.wav"), voice[0], voice[1])

def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items(): out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


# ------------------------------------------------------------------ cut-downs
def _word_score(w, kws):
    k = re.sub(r"[^a-z0-9'₹$%]", "", w.lower())
    if not k or k in STOP: return 0.0
    s = 1.0 + (2.0 if any(q.lower() in k for q in kws) else 0) + (1.5 if re.search(r"[\d₹$%]", k) else 0) + (.5 if len(k) > 6 else 0)
    return s

def cutdown_order(pr, seconds, S):
    """segments for a cut-down: keep the beats in delivery.cutdown.keep (H, C) whole, fill with the densest of the
    compressible beats; segments tied together by a cutaway or chest graphic move as one unit. Falls back to a greedy
    word-importance pick when the selects carry no beat tags. -> (order, notes)"""
    edl, segs, fps = old_segments(pr); E = pr.edit; CD = S.get("delivery.cutdown") or {}
    keep_b = set(CD.get("keep", ["H", "C"])); tol = CD.get("tolerance_s", .5)
    end = (E.get("end_card") or {}).get("duration", 0); budget = seconds - end
    parent = list(range(len(segs)))
    def find(i):
        while parent[i] != i: i = parent[i]
        return i
    eps = .5 / fps
    spans = [(c["start"], c["end"]) for c in E.get("cutaways") or []]
    for c in E.get("chest") or []:
        ids = [c["segment"]] if isinstance(c["segment"], str) else c["segment"]
        ss = [s for s in segs if s["id"] in ids]
        if ss: spans.append((min(s["t0"] for s in ss) + eps * 2, max(s["t1"] for s in ss) - eps * 2))
    for a, b in spans:
        ix = [k for k, s in enumerate(segs) if s["t0"] < b - eps and s["t1"] > a + eps]
        for k in ix[1:]: parent[find(k)] = find(ix[0])
    words = pr.json("words.json", []) or []
    units = {}
    for k in range(len(segs)): units.setdefault(find(k), []).append(k)
    units = [sorted(v) for _, v in sorted(units.items(), key=lambda kv: min(kv[1]))]
    kws = list((E.get("qc") or {}).get("topic_keywords") or []) + list((E.get("qc") or {}).get("brand_tail") or [])
    def info(u):
        ss = [segs[k] for k in u]; dur = sum(s["n"] for s in ss) / fps
        sc = sum(_word_score(w[2], kws) for w in words if any(s["t0"] <= (w[0] + w[1]) / 2 < s["t1"] for s in ss))
        prev = [w for w in words if (w[0] + w[1]) / 2 < ss[0]["t0"]]      # does the unit open mid-sentence? (heads cannot be trimmed)
        bad = bool(prev) and not str(prev[-1][2]).rstrip().endswith((".", "?", "!"))
        last = [w for w in words if ss[-1]["t0"] <= (w[0] + w[1]) / 2 < ss[-1]["t1"]]       # ends mid-sentence with nothing to trim back to
        if last and not str(last[-1][2]).rstrip().endswith((".", "?", "!")) and not any(str(w[2]).rstrip().endswith((".", "?", "!", ",")) and w[1] - ss[-1]["t0"] >= .4 for w in last): bad = True
        return {"u": u, "dur": dur, "score": sc, "bad": bad, "beats": {s["beat"] for s in ss if s["beat"]}}
    U = [info(u) for u in units]; tagged = any(x["beats"] for x in U); notes = []
    if tagged:
        must = [x for x in U if x["beats"] & keep_b]
        if sum(x["dur"] for x in must) > budget + tol:      # even hook + CTA are too long: keep the first and the last unit, then the best
            notes.append(f"{'/'.join(sorted(keep_b))} beats alone run {sum(x['dur'] for x in must):.1f} s > {budget:.1f} s: trimmed by word importance")
            pool = must[1:-1]; must = [must[0], must[-1]] if len(must) > 1 else must[:1]
        else: pool = [x for x in U if x not in must]
    else:
        notes.append("no beat tags in selects: greedy pick by word importance")
        must = [U[0], U[-1]] if len(U) > 1 else U[:1]; pool = U[1:-1]
    chosen = list(must); left = budget - sum(x["dur"] for x in chosen)
    for x in sorted([x for x in pool if not x["bad"]], key=lambda x: -x["score"] / max(x["dur"], .1)):     # fill only with whole sentences
        if x["dur"] <= left + 1e-6: chosen.append(x); left -= x["dur"]      # never over the target
    order = [segs[k]["id"] for x in sorted(chosen, key=lambda x: x["u"][0]) for k in x["u"]]
    notes.append(f"{len(order)} of {len(segs)} shots, {sum(x['dur'] for x in chosen) + end:.2f} s with the end card")
    # a kept shot followed by a dropped one must not end mid-sentence ("... near me. If"): trim its tail back to the last
    # sentence / clause end (tail trims only: plates decode from their first frame)
    trims = {}; keep = set(order)
    for k, s in enumerate(segs):
        if s["id"] not in keep or (k + 1 < len(segs) and segs[k + 1]["id"] in keep): continue
        ws = [w for w in words if s["t0"] <= (w[0] + w[1]) / 2 < s["t1"]]
        if not ws or str(ws[-1][2]).rstrip().endswith((".", "?", "!")): continue
        ends = [w for w in ws if str(w[2]).rstrip().endswith((".", "?", "!", ",")) and w[1] - s["t0"] >= .4]
        if ends:
            nxt = next((w[0] for w in words if w[0] > ends[-1][0] + 1e-3), ends[-1][1] + .06)       # cut in the gap before the next word
            trims[s["id"]] = max(1, min(s["n"], int(np.floor((min(ends[-1][1] + .06, max(nxt, ends[-1][1])) - s["t0"]) * fps))))
        else: notes.append(f"{s['id']} ends mid-sentence ('{ws[-1][2]}') and has no sentence end to trim back to")
    for k, s in enumerate(segs):
        if s["id"] in keep and k > 0 and segs[k - 1]["id"] not in keep:
            prev = [w for w in words if (w[0] + w[1]) / 2 < s["t0"]]
            if prev and not str(prev[-1][2]).rstrip().endswith((".", "?", "!")): notes.append(f"{s['id']} opens mid-sentence (after '{prev[-1][2]}')")
    return order, notes, trims


# ------------------------------------------------------------------ building one rendered variant
def _qc_lines(rep): return rep

def render_variant(pr, S, spec, workdir, out_mp4, master):
    """build + render + mix + encode + QC one variant. -> result dict"""
    from . import qc as QC
    kind = spec["kind"]; root = os.path.join(workdir, spec["id"]); notes = []
    E0 = pr.edit; E0.pop("variants", None)
    if kind == "music":
        vpr = make_project(pr, root, keep=("timeline.json", "elements.jsonl"))
        mu = {k: v for k, v in spec.items() if k not in ("id", "kind")}
        if mu.get("file") and not os.path.exists(pr.p(mu["file"])): return {"status": "failed", "reason": f"music file {mu['file']} not found"}
        E = dict(E0, music=_merge(E0.get("music") or {}, mu)); _write_variant(vpr, E)
        shutil.copy2(pr.e("words.json"), vpr.e("words.json")) if os.path.exists(pr.e("words.json")) else None
        shutil.copy2(pr.e("edl.json"), vpr.e("edl.json")); _link(os.path.realpath(pr.e("voice_final.wav")), vpr.e("voice_final.wav"))
        from .mix import mix
        mix(vpr)
        subprocess.run([_ff(), "-v", "error", "-y", "-i", master, "-i", vpr.e("mix.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy"]
                       + audio_args(S) + (["-movflags", "+faststart"] if S.get("delivery.faststart", True) else []) + ["-shortest", out_mp4], check=True)
    else:
        vpr = make_project(pr, root)
        if kind == "end_card":
            E = dict(E0, end_card=_merge(E0.get("end_card") or {}, spec.get("end_card") or {}))
            _write_variant(vpr, E); shutil.copy2(pr.e("edl.json"), vpr.e("edl.json")); shutil.copy2(pr.e("words.json"), vpr.e("words.json"))
            _link(os.path.realpath(pr.e("voice_final.wav")), vpr.e("voice_final.wav"))
        else:
            _, segs, _ = old_segments(pr); ids = [s["id"] for s in segs]
            if kind == "hook":
                first = []
                for x in spec.get("first") or spec.get("segments") or []:      # segment ids or clip (select) ids
                    hit = [s["id"] for s in segs if s["id"] == x or s.get("clip") == x]
                    if not hit: return {"status": "failed", "reason": f"hook {spec['id']}: '{x}' is not a segment or select id"}
                    first += [h for h in hit if h not in first]
                order = first + [i for i in ids if i not in first]
            else:
                if spec.get("segments"): order = list(spec["segments"])
                else: order, n2, trims = cutdown_order(pr, float(spec["seconds"]), S); notes += n2
            E, edl, words, voice, n3 = retime(pr, order, E0, trims if kind == "cutdown" and not spec.get("segments") else None); notes += n3
            if kind == "hook" and spec.get("title_card"):
                tc = spec["title_card"]; d = float(tc.get("duration", 1.5))
                drop = [c.get("id") for c in E["cutaways"] if c["start"] < d]
                if drop: notes.append(f"title card replaces cutaway(s) {drop}")
                E["cutaways"] = [{"id": "title_card", "template": tc["template"], "start": 0.0, "end": d, "snap": tc.get("snap", True),
                                  "in": "cut", "out": tc.get("out", S.get("transitions.out", "cut")), "params": tc.get("params") or {}}] + \
                                [c for c in E["cutaways"] if c["start"] >= d]
            if kind == "cutdown":
                sec = float(spec["seconds"]); tol = S.get("delivery.cutdown.tolerance_s", .5)
                E.setdefault("qc", {}); E["qc"] = dict(E["qc"] or {}, duration=[round(sec * .6, 2), sec + tol])
            _write_variant(vpr, E, edl, words, voice)
        from .render import render
        from .mix import mix
        from .encode import encode
        render(vpr); mix(vpr); encode(vpr, out_mp4)
    nf, rep = QC.run(vpr, out_mp4, fast=True)
    stamp = json.load(open(vpr.e("qc.json"), encoding="utf-8"))
    return {"status": "passed" if nf == 0 else "failed", "file": out_mp4, "qc": stamp, "report": rep, "notes": notes, "project": vpr,
            "reason": None if nf == 0 else "QC FAIL: " + "; ".join(f"{g['id']} {g['summary']}" for g in stamp["gates"] if g["status"] == "FAIL")}
