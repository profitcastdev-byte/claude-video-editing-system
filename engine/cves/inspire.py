"""`cves inspire PROJECT [--refs DIR] [--dry-run]`: measure the client's reference edits -> PROJECT/Edit/style.yaml.

The reference edits (videos and/or screenshots in PROJECT/Inspirations/ or --refs) are the spec. Everything that can be
measured from pixels and audio is measured, and written as style keys (styles/default.yaml schema, docs/STYLE.md) together
with `_evidence: {key: "how, n samples, confidence"}`. Keys whose confidence is below `--min-conf` are left out (their
evidence is still printed). `style.load()` merges Edit/style.yaml over the preset, under Brand/style.yaml and edit.yaml.

What is measured (per video, then pooled across references):
  pacing      cuts (frame-difference peaks), shot lengths -> grammar.max_shot_s (p90); cuts per minute; cutaway share
              (time without a presenter face, YuNet) -> grammar.cutaway_share band; longest cutaway -> grammar.max_cutaway_s;
              face in the first frame -> grammar.face_on_first_frame
  framing     face height ratio between consecutive A-roll shots -> framing.min_step, framing.zoom_levels
  grade       relative to THIS project's own footage (Edit/plate, else Raw/): wall vs skin -> grade.relight / background_stops;
              skin and frame luminance -> gamma; wall chroma -> background_saturation; skin / wall colour -> subject_tint /
              background_tint; top-corner vs near-wall -> vignette; blacks -> black_lift
  palette     k-means on graphics (no-face) frames -> stage.background, stage.glow_bottom, colors.accent, colors.accent_dark
  captions    burned-in text lines on A-roll frames -> captions.position (chin / lower_third / center / y:px), size, case, box,
              color, highlight_color, style (one_word / word_reveal / highlight / box), max_lines; OCR (tesseract) is optional
  transitions per cut: zoom/motion blur spike (whip), RGB split (glitch), luma dip (fade) -> transitions.in / out (+ *_s)
  sound       ebur128 integrated loudness (a note only: downloads are platform-normalised)
Inspire v2 (per reference, then MIXED per dimension instead of averaged: inspire_mix.py):
  hear        inspire_audio.py: voice / music presence, bed vs voice, ducking, tempo + beat grid, SFX density, drop-outs,
              music energy -> sound.bed_lu, sound.duck_other_db, rhythm.*
  feel        inspire_feel.py: cut-on-beat, cut-rate curve, hook timing, pattern interrupts, loop seam, energy arc ->
              rhythm.*, structure.*, music.sync
  see         inspire_see.py: contact sheet Edit/inspire/<ref>-sheet.jpg + grain, tone curve, saturation, temperature,
              vignette, letterbox, aspect, motion blur -> `_inspire.aesthetics` notes; aesthetic-review.md for Claude
  report      Edit/inspire/REPORT.md (inspire_report.py)"""
import os, sys, json, math, shutil, subprocess, tempfile, datetime, collections
import numpy as np, cv2, yaml

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
from .gfx import DESIGN as _DESIGN
DESIGN_W, DESIGN_H = _DESIGN                     # the project canvas (style canvas.size; set_frame); caption px are reported in it
AW, AH = DESIGN_W // 2, DESIGN_H // 2              # analysis frame: half the canvas; references of another aspect are letter-fitted

def set_frame(w, h):
    """measure references on the project's canvas (docs/FORMATS.md). Spawned workers get it through their job args."""
    global DESIGN_W, DESIGN_H, AW, AH
    DESIGN_W, DESIGN_H = int(w), int(h); AW, AH = max(2, DESIGN_W // 4 * 2), max(2, DESIGN_H // 4 * 2)
LW, LH = 90, 160           # cut-detection thumbnail
SAMPLE_FPS = 6.0           # face / grade / caption samples per second


# ======================================================================== helpers
def _lin(c): c = np.asarray(c, np.float64); return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
def _Y(rgb): return float(_lin(rgb) @ [.2126, .7152, .0722])                       # relative luminance of a display RGB 0..1
def _lab(rgb): return cv2.cvtColor(np.float32(rgb).reshape(1, 1, 3), cv2.COLOR_RGB2Lab).reshape(3)
def _hex(rgb): r = np.clip(np.round(np.asarray(rgb) * 255), 0, 255).astype(int); return "#%02X%02X%02X" % tuple(r)
def _pct(a, q): return float(np.percentile(a, q)) if len(a) else float("nan")
def _r(x, n=2): return round(float(x), n)
def _half(x): return math.ceil(x * 2) / 2


class Evidence:
    def __init__(self): self.keys, self.ev, self.conf = {}, {}, {}
    def put(self, key, value, how, n, conf):
        conf = float(np.clip(conf, 0, 1)); self.ev[key] = f"{how}; n={n}; confidence {conf:.2f}"; self.conf[key] = conf; self.keys[key] = value
    def note(self, key, how): self.ev.setdefault(key, how); self.conf.setdefault(key, 0.0)


def _yunet(w, h):
    from . import config as C
    p = C.get("yunet")
    if not p or not os.path.exists(p): raise SystemExit(f"YuNet face model not found ({p}): run `cves doctor` or set CVES_YUNET")
    return cv2.FaceDetectorYN.create(p, "", (w, h), 0.7, 0.3, 5000)


def _faces(det, rgb):
    _, f = det.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if f is None or not len(f): return None
    f = max(f, key=lambda r: r[2] * r[3])
    return f if f[3] >= .04 * rgb.shape[0] else None          # a presenter, not a face in a picture-in-picture or crowd


# ======================================================================== per-frame measurements
def cheeks(rgb, f):
    """per-cheek median RGB (0..1), averaged"""
    lm = np.array(f[4:14], float).reshape(5, 2); k = max(3, int(f[2] * .05)); out = []
    for eye, mouth in ((lm[0], lm[3]), (lm[1], lm[4])):
        cx, cy = eye * .55 + mouth * .45; x0, y0 = int(cx) - k, int(cy) - k
        if x0 < 0 or y0 < 0 or x0 + 2 * k > rgb.shape[1] or y0 + 2 * k > rgb.shape[0]: return None
        out.append(np.median(rgb[y0:y0 + 2 * k, x0:x0 + 2 * k].reshape(-1, 3), 0))
    return np.mean(out, 0) / 255


def grade_stats(rgb, f):
    """skin, wall (beside / above the head, away from the body), top corners, black level of one A-roll frame"""
    h, w, _ = rgb.shape; x, y, fw, fh = [float(v) for v in f[:4]]
    sk = cheeks(rgb, f)
    if sk is None: return None
    body = np.zeros((h, w), bool)
    body[max(0, int(y - .45 * fh)):, max(0, int(x - .55 * fw)):min(w, int(x + 1.55 * fw))] = True            # head + hair
    body[int(min(h - 1, y + 1.1 * fh)):, max(0, int(x - 1.4 * fw)):min(w, int(x + 2.4 * fw))] = True         # shoulders down
    near = np.zeros((h, w), bool)
    near[max(0, int(y - .6 * fh)):int(min(h, y + 1.0 * fh)), max(0, int(x - 1.6 * fw)):min(w, int(x + 2.6 * fw))] = True
    near &= ~body; near[:int(.06 * h)] = False
    if near.sum() < 400: return None
    px = rgb[near].reshape(-1, 3) / 255
    hsv = cv2.cvtColor(rgb[near].reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    keep = ~((hsv[:, 2] > 235) & (hsv[:, 1] < 40))           # drop white text over the wall
    if keep.sum() < 200: return None
    wall = np.median(px[keep], 0)
    cs = int(.07 * min(w, h)); corners = [rgb[int(.05 * h):int(.05 * h) + cs, :cs], rgb[int(.05 * h):int(.05 * h) + cs, w - cs:]]
    corner = float(np.mean([_Y(np.median(c.reshape(-1, 3), 0) / 255) for c in corners]))
    # look._vignette geometry (centre = face centre): k = clip(r - .35, 0, 1) ** 1.6 at the corner patches and at the near wall
    fcx, fcy = x + fw / 2, y + fh / 2
    kf = lambda px_, py_: float(np.clip(np.hypot((px_ - fcx) / (w * .75), (py_ - fcy) / (h * .62)) - .35, 0, 1) ** 1.6)
    yy, xx = np.nonzero(near); kn = kf(float(xx.mean()), float(yy.mean()))
    kc = float(np.mean([kf(cs / 2, .05 * h + cs / 2), kf(w - cs / 2, .05 * h + cs / 2)]))
    lum = rgb.reshape(-1, 3)[::7] / 255
    return dict(skin=sk.tolist(), wall=wall.tolist(), corner=corner, kc=kc, kn=kn, black=np.percentile(lum, .5, axis=0).tolist(),
                Ymed=float(np.median(lum @ [.2126, .7152, .0722])), Yp99=float(np.percentile(lum @ [.2126, .7152, .0722], 99.5)))


def caption_lines(rgb, face):
    """burned-in text lines: bright (or saturated) top-hat glyph components grouped on a baseline.
    -> [dict(box=(x0,y0,x1,y1), comps=[(x,y,w,h)], fill=rgb, hi=rgb|None, words=n, boxed=bool, box_rgb)]"""
    h, w, _ = rgb.shape; g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    th = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31)))
    m = ((th > 55) & (hsv[..., 2] > 170)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    comps = []
    for i in range(1, n):
        x, y, cw, ch, a = st[i]
        if 7 <= ch <= 90 and cw <= 2.2 * ch + 6 and a >= .12 * cw * ch and a >= 18: comps.append((x, y, cw, ch, i))
    if face is not None:
        fx, fy, fw, fh = face[:4]; comps = [c for c in comps if not (fx < c[0] + c[2] / 2 < fx + fw and fy < c[1] + c[3] / 2 < fy + fh)]
    comps.sort(key=lambda c: (c[1] + c[3] / 2, c[0])); used = [False] * len(comps); lines = []
    for a in range(len(comps)):
        if used[a]: continue
        L = [comps[a]]; used[a] = True; cy = comps[a][1] + comps[a][3] / 2; hh = comps[a][3]
        for b in range(a + 1, len(comps)):
            if used[b]: continue
            c = comps[b]
            if abs(c[1] + c[3] - (L[0][1] + L[0][3])) < .45 * hh + 3 and .45 < c[3] / hh < 2.2: L.append(c); used[b] = True
        L.sort(key=lambda c: c[0])
        # split on big horizontal gaps (two separate texts on one row)
        runs, cur = [], [L[0]]
        for c in L[1:]:
            if c[0] - (cur[-1][0] + cur[-1][2]) > 2.2 * np.median([q[3] for q in cur]): runs.append(cur); cur = [c]
            else: cur.append(c)
        runs.append(cur)
        for R in runs:
            if len(R) < 3: continue
            x0, y0 = min(c[0] for c in R), min(c[1] for c in R); x1, y1 = max(c[0] + c[2] for c in R), max(c[1] + c[3] for c in R)
            if x1 - x0 < .08 * w: continue
            hs = np.array([c[3] for c in R], float); hm = float(np.median(hs))
            gaps = [R[j + 1][0] - (R[j][0] + R[j][2]) for j in range(len(R) - 1)]
            words = 1 + sum(1 for gp in gaps if gp > .32 * hm)
            col = [np.median(rgb[cc == c[4]].reshape(-1, 3), 0) / 255 for c in R]
            lab = np.array([_lab(c_) for c_ in col]); main = np.median(lab, 0)
            far = [j for j in range(len(R)) if np.linalg.norm(lab[j] - main) > 25 and lab[j][0] > 35]
            body = [col[j] for j in range(len(R)) if j not in far]
            fill = np.median(body if body else col, 0)
            hi = np.median([col[j] for j in far], 0) if len(far) >= 2 else None
            # box: a flat surround inside 0.5 h of the glyphs that differs from the frame further out
            pad = int(.5 * hm) + 2; X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(w, x1 + pad), min(h, y1 + pad)
            ink = cv2.dilate(m[Y0:Y1, X0:X1], np.ones((5, 5), np.uint8)).astype(bool)
            inner = rgb[Y0:Y1, X0:X1][~ink].reshape(-1, 3).astype(float)
            P2 = int(1.6 * hm); oX0, oY0, oX1, oY1 = max(0, x0 - P2), max(0, y0 - P2), min(w, x1 + P2), min(h, y1 + P2)
            ring = np.ones((oY1 - oY0, oX1 - oX0), bool); ring[Y0 - oY0:Y1 - oY0, X0 - oX0:X1 - oX0] = False
            outer = rgb[oY0:oY1, oX0:oX1][ring].reshape(-1, 3).astype(float)
            boxed, box_rgb = False, None
            if len(inner) > 30 and len(outer) > 30:
                ist = inner.std(0).mean(); diff = np.abs(np.median(inner, 0) - np.median(outer, 0)).mean()
                boxed = ist < 16 and diff > 22; box_rgb = (np.median(inner, 0) / 255).tolist() if boxed else None
            lines.append(dict(box=(int(x0), int(y0), int(x1), int(y1)), h=hm, hs=hs.tolist(), n=len(R), words=words,
                              fill=fill.tolist(), hi=None if hi is None else hi.tolist(), boxed=boxed, box_rgb=box_rgb))
    return lines


def trans_feats(lo_rgb):
    """per thumbnail: sharpness (Laplacian var), mean luma, RGB-split (R vs B horizontal offset energy at edges)"""
    g = cv2.cvtColor(lo_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    sharp = float(cv2.Laplacian(g, cv2.CV_32F).var())
    R, B = lo_rgb[..., 0].astype(np.float32), lo_rgb[..., 2].astype(np.float32)
    ed = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) > 40
    split = float(np.abs(R - B)[ed].mean() / (np.abs(R - B).mean() + 1)) if ed.sum() > 30 else 0.0
    return sharp, float(g.mean()), split


# ======================================================================== one reference video
def analyse_video(path, max_s=90.0):
    import av
    out = dict(path=path, kind="video", samples=[], diffs=[], times=[], tf=[], palette=[], bg=[], bottom=[])
    with av.open(path) as c:
        vs = c.streams.video[0]; vs.thread_type = "AUTO"
        fps = float(vs.average_rate or vs.guessed_rate or 30); out["fps"] = fps
        W0, H0 = vs.codec_context.width, vs.codec_context.height
        rot = 0
        try: rot = int(float((vs.metadata or {}).get("rotate", 0)))
        except ValueError: pass
        step = max(1, int(round(fps / 30)))       # analyse at <= 30 fps for cuts
        det = _yunet(AW, AH); next_s = 0.0; prev = None; t0 = None
        for i, fr in enumerate(c.decode(vs)):
            t = float(fr.time if fr.time is not None else i / fps)
            if t0 is None: t0 = t
            t -= t0
            if t > max_s: break
            if i % step: continue
            lo = fr.reformat(width=LW, height=LH, format="rgb24").to_ndarray()
            if rot in (90, 270, -90): lo = np.ascontiguousarray(np.rot90(lo, -rot // 90))
            if prev is not None:
                d = np.abs(lo.astype(np.int16) - prev.astype(np.int16)).mean() / 255
                h1 = cv2.calcHist([lo], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3); h2 = cv2.calcHist([prev], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
                hd = 1 - cv2.compareHist(cv2.normalize(h1, h1).flatten(), cv2.normalize(h2, h2).flatten(), cv2.HISTCMP_CORREL)
                out["diffs"].append(.5 * d * 4 + .5 * hd)
            else: out["diffs"].append(0.0)
            out["times"].append(t); out["tf"].append(trans_feats(lo)); prev = lo
            if t + 1e-6 >= next_s:
                next_s += 1 / SAMPLE_FPS
                rgb = _fit(fr, rot)
                f = _faces(det, rgb)
                s = dict(t=t, face=None if f is None else [float(v) for v in f[:14]])
                if f is not None:
                    gs = grade_stats(rgb, f)
                    if gs: s["grade"] = gs
                s["caps"] = caption_lines(rgb, f)
                if f is None:
                    sm = cv2.resize(rgb, (135, 240), interpolation=cv2.INTER_AREA)
                    hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV).reshape(-1, 3); px = sm.reshape(-1, 3)
                    sat = (hsv[:, 1] > 110) & (hsv[:, 2] > 90)
                    if sat.any(): out["palette"].append(px[sat][::2].tolist())
                    out["bg"].append(px[::5].tolist()); out["bottom"].append(np.median(sm[int(.78 * 240):].reshape(-1, 3), 0).tolist())
                out["samples"].append(s)
        out["dur"] = out["times"][-1] if out["times"] else 0.0; out["size"] = [W0, H0]; out["rot"] = rot
    out["cuts"] = detect_cuts(out["times"], out["diffs"])
    out["audio"] = audio_stats(path, max_s)
    return out


def _fit(fr, rot=0):
    """decoded frame -> AW x AH RGB, letter-fitted (non-9:16 references are centred on black)"""
    w, h = fr.width, fr.height
    if rot in (90, 270, -90): w, h = h, w
    s = min(AW / w, AH / h); nw, nh = max(2, int(round(w * s / 2) * 2)), max(2, int(round(h * s / 2) * 2))
    im = fr.reformat(width=nw if rot not in (90, 270, -90) else nh, height=nh if rot not in (90, 270, -90) else nw, format="rgb24").to_ndarray()
    if rot in (90, 270, -90): im = np.ascontiguousarray(np.rot90(im, -rot // 90))
    if (nw, nh) == (AW, AH): return im
    can = np.zeros((AH, AW, 3), np.uint8); y0, x0 = (AH - im.shape[0]) // 2, (AW - im.shape[1]) // 2
    can[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im; return can


def analyse_image(path):
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None: return None
    rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; s = min(AW / w, AH / h)
    rgb = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    can = np.zeros((AH, AW, 3), np.uint8); y0, x0 = (AH - rgb.shape[0]) // 2, (AW - rgb.shape[1]) // 2; can[y0:y0 + rgb.shape[0], x0:x0 + rgb.shape[1]] = rgb
    f = _faces(_yunet(AW, AH), can); s_ = dict(t=0.0, face=None if f is None else [float(v) for v in f[:14]], caps=caption_lines(can, f))
    out = dict(path=path, kind="image", samples=[s_], palette=[], bg=[], bottom=[])
    if f is not None:
        gs = grade_stats(can, f)
        if gs: s_["grade"] = gs
    else:
        sm = cv2.resize(can, (135, 240), interpolation=cv2.INTER_AREA); hsv = cv2.cvtColor(sm, cv2.COLOR_RGB2HSV).reshape(-1, 3); px = sm.reshape(-1, 3)
        sat = (hsv[:, 1] > 110) & (hsv[:, 2] > 90)
        if sat.any(): out["palette"].append(px[sat][::2].tolist())
        out["bg"].append(px[::5].tolist()); out["bottom"].append(np.median(sm[int(.78 * 240):].reshape(-1, 3), 0).tolist())
    return out


def detect_cuts(times, diffs, min_gap=.2):
    """frame-difference peaks: above an absolute floor and well above the local median, local maximum within +-3 frames"""
    d = np.array(diffs); n = len(d); cuts = []
    if n < 5: return cuts
    for i in range(1, n):
        lo, hi = max(0, i - 15), min(n, i + 16); med = float(np.median(d[lo:hi]))
        if d[i] > max(.22, 4 * med + .05) and d[i] >= d[max(0, i - 3):i + 4].max():
            if not cuts or times[i] - cuts[-1] >= min_gap: cuts.append(times[i])
    return cuts


def audio_stats(path, max_s):
    from . import config as C
    try:
        r = subprocess.run([C.get("ffmpeg"), "-hide_banner", "-nostats", "-t", str(max_s), "-i", path, "-vn", "-af", "ebur128=framelog=verbose", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired): return None
    M = []
    for ln in r.stderr.splitlines():
        if " M:" in ln and "TARGET" not in ln:
            try: M.append(float(ln.split(" M:")[1].split()[0]))
            except (ValueError, IndexError): pass
    I = [ln for ln in r.stderr.splitlines() if ln.strip().startswith("I:")]
    integ = float(I[-1].split()[1]) if I else None
    return dict(M=M, I=integ) if M else None


# ======================================================================== this project's own footage (what grade() receives)
def source_stats(pr, max_frames=60):
    """grade stats of the project's ungraded footage: Edit/plate/*.mkv (conformed SDR, what look.grade gets), else Raw/"""
    import av
    paths = sorted(f for f in (os.listdir(pr.e("plate")) if os.path.isdir(pr.e("plate")) else []) if f.endswith(".mkv"))
    srcs = [pr.e("plate", f) for f in paths]
    if not srcs:
        try: srcs = [pr.raw]
        except (SystemExit, OSError): return None, "no Edit/plate and no Raw/ video"
    det = _yunet(AW, AH); got = []; per = max(4, max_frames // max(1, min(len(srcs), 12)))
    for p in srcs[::max(1, len(srcs) // 12)]:
        try:
            with av.open(p) as c:
                vs = c.streams.video[0]; vs.thread_type = "AUTO"; k = 0
                for i, fr in enumerate(c.decode(vs)):
                    if i % 6: continue
                    rgb = _fit(fr); f = _faces(det, rgb)
                    if f is not None:
                        gs = grade_stats(rgb, f)
                        if gs: got.append(gs); k += 1
                    if k >= per or i > 400: break
        except Exception as e:      # an unreadable plate is not fatal: the others still describe the footage
            print(f"  (source {os.path.basename(p)} skipped: {type(e).__name__})")
        if len(got) >= max_frames: break
    return (_pool_grade(got), f"{len(got)} frames of {'Edit/plate' if paths else 'Raw'}") if got else (None, "no face found in the project footage")


def _pool_grade(G):
    a = lambda k: np.median([g[k] for g in G], 0)
    return dict(skin=a("skin"), wall=a("wall"), corner=float(a("corner")), kc=float(a("kc")), kn=float(a("kn")), black=a("black"), Ymed=float(a("Ymed")), Yp99=float(a("Yp99")), n=len(G),
                near=float(np.median([_Y(g["wall"]) for g in G])))


# ======================================================================== pooling + derivation
def derive(R, src, ev):
    vids = [r for r in R if r["kind"] == "video"]
    # ---------------- shots / pacing
    shot_len, shots_all, per_share, cut_rate, first_face, runs, steps, levels, trans_in, trans_out, tdur = [], [], [], [], [], [], [], [], [], [], collections.defaultdict(list)
    for r in vids:
        T = r["dur"]
        if T < 3: continue
        b = [0.0] + r["cuts"] + [T]; S = r["samples"]
        shots = []
        for a_, b_ in zip(b[:-1], b[1:]):
            ss = [s for s in S if a_ <= s["t"] < b_]
            fs = [s for s in ss if s["face"]]
            face_frac = len(fs) / max(1, len(ss))
            fh = float(np.median([s["face"][3] / AH for s in fs])) if fs else 0.0
            shots.append(dict(t0=a_, t1=b_, aroll=face_frac >= .5 and fh >= .06, fh=fh, n=len(ss)))
        shot_len += [s["t1"] - s["t0"] for s in shots if s["t1"] - s["t0"] > .15]
        shots_all.append(shots)
        cut_rate.append(len(r["cuts"]) / T * 60)
        noface = sum(s["t1"] - s["t0"] for s in shots if not s["aroll"]); per_share.append(noface / T)
        run = 0.0
        for s in shots + [dict(aroll=True, t0=T, t1=T)]:
            if not s["aroll"]: run += s["t1"] - s["t0"]
            elif run: runs.append(run); run = 0.0
        first_face.append(bool(S and S[0]["face"]))
        A = [s for s in shots if s["aroll"]]
        mn = min((s["fh"] for s in A), default=0)
        for s in A:
            if mn: levels.append(s["fh"] / mn)
        for p, q in zip(shots[:-1], shots[1:]):
            if p["aroll"] and q["aroll"] and p["fh"] and q["fh"]: steps.append(max(p["fh"], q["fh"]) / min(p["fh"], q["fh"]))
        # transitions at A-roll <-> no-face boundaries
        tm = np.array(r["times"]); tf = np.array(r["tf"])
        for p, q in zip(shots[:-1], shots[1:]):
            if p["aroll"] == q["aroll"]: continue
            kind, dur = classify_transition(tm, tf, q["t0"])
            (trans_in if p["aroll"] else trans_out).append(kind)
            if dur: tdur[kind].append(dur)
    nv = len(shots_all)
    if shot_len:
        p90 = _pct(shot_len, 90)
        ev.put("grammar.max_shot_s", _half(p90), f"p90 of {len(shot_len)} shot lengths (frame-difference cuts) across {nv} refs; median {np.median(shot_len):.2f} s, max {max(shot_len):.2f} s; {np.mean(cut_rate):.1f} cuts/min",
               len(shot_len), min(1, len(shot_len) / 40))
    if per_share:
        lo, hi = min(per_share), max(per_share); pad = .05 if nv > 1 else .07
        ev.put("grammar.cutaway_share", [_r(max(0, lo - pad)), _r(min(1, hi + pad))], f"time without a presenter face (YuNet, {SAMPLE_FPS:g} fps) per ref: {', '.join(f'{x:.0%}' for x in per_share)}",
               nv, min(1, .45 + .15 * nv))
    if runs:
        ev.put("grammar.max_cutaway_s", _half(_pct(runs, 90)), f"p90 of {len(runs)} no-face runs across {nv} refs (longest {max(runs):.1f} s, often an end card)", len(runs), min(1, len(runs) / 10))
    if first_face:
        ok = sum(first_face) / len(first_face)
        ev.put("grammar.face_on_first_frame", ok >= .99, f"presenter face in the first sample of {sum(first_face)}/{len(first_face)} refs", len(first_face), .5 + .1 * len(first_face) if ok in (0, 1) else .3)
    if len(steps) >= 3:
        moved = [x for x in steps if x >= 1.06]
        if moved:
            ms = _pct(moved, 25)
            ev.put("framing.min_step", _r(max(1.05, ms)), f"face-height ratio across {len(steps)} direct A-roll cuts; {len(moved)} changed scale (p25 {ms:.2f}, median {np.median(moved):.2f})",
                   len(steps), min(1, len(steps) / 12) * (len(moved) / len(steps)) ** .5)
        if len(levels) >= 4:
            lv = _levels(levels, max(1.06, _pct(moved, 25) if moved else 1.15))
            ev.put("framing.zoom_levels", lv, f"A-roll face height per shot relative to each ref's widest shot, clustered ({len(levels)} shots)", len(levels), min(1, len(levels) / 15) * .8)
    for name, L in (("in", trans_in), ("out", trans_out)):
        if L:
            cnt = collections.Counter(L); k, c = cnt.most_common(1)[0]
            ev.put(f"transitions.{name}", k, f"{name.upper()} of cutaways: {dict(cnt)} (whip = blur spike, glitch = RGB split, fade = luma dip)", len(L), min(1, len(L) / 8) * (c / len(L)))
    for k, L in tdur.items():
        if k in ("whip", "glitch", "fade") and len(L) >= 2:
            ev.put(f"transitions.{k}_s", _r(np.median(L) / 2), f"half the median duration of {len(L)} {k} transitions (render applies it either side of the cut)", len(L), min(1, len(L) / 6))
    # ---------------- grade (relative to the project's footage)
    G = [s["grade"] for r in R for s in r["samples"] if s.get("grade")]
    if G and src:
        ref = _pool_grade(G); n = len(G); c0 = min(1, n / 40)
        sk_r, sk_s = _Y(ref["skin"]), _Y(src["skin"]); wl_r, wl_s = _Y(ref["wall"]), _Y(src["wall"])
        Ys_r, Ys_s = float(np.mean(ref["skin"])), float(np.mean(src["skin"]))
        g_raw = math.log(max(Ys_r, 1e-3)) / math.log(max(Ys_s, 1e-3)); gamma = float(np.clip(g_raw, .8, 1.3))
        ev.put("grade.gamma", _r(gamma), f"skin display level ref {Ys_r:.3f} vs footage {Ys_s:.3f} (cheek patches; raw {g_raw:.2f}"
               f"{', clamped' if gamma != g_raw else ''}; depends on the references' own lighting)", n, c0 * (.4 if gamma != g_raw else .6))
        sk_after = _Y(np.clip(np.array(src["skin"]) ** gamma, 0, 1))
        stops = math.log2(max(wl_r / sk_r, 1e-4) / max(wl_s / sk_after, 1e-4)) / 2.2      # look.grade scales display RGB: linear = display ** 2.2
        how = f"wall/skin luminance ref {wl_r / sk_r:.2f} vs footage {wl_s / sk_s:.2f} (wall beside/above the head)"
        ev.put("grade.relight", stops < -.2, how, n, c0 * .85)
        if stops < -.2: ev.put("grade.background_stops", _r(max(-3, stops)), how, n, c0 * .8)
        cr = lambda c: float(np.linalg.norm(np.array(c) - np.mean(c)) / (np.mean(c) + 1e-3))
        bs = cr(ref["wall"]) / max(cr(src["wall"]), 1e-3)
        ev.put("grade.background_saturation", _r(np.clip(bs, .3, 1.4)), f"wall chroma/level ref {cr(ref['wall']):.3f} vs footage {cr(src['wall']):.3f} (depends on the wall itself: scene-dependent)", n, c0 * .45)
        def tint(a, b):
            t = (np.array(a) / max(np.mean(a), 1e-3)) / (np.array(b) / max(np.mean(b), 1e-3)); t = t / t.mean(); return [_r(x, 3) for x in np.clip(t, .9, 1.1)]
        ev.put("grade.subject_tint", tint(ref["skin"], src["skin"]), f"skin RGB balance ref {_hex(ref['skin'])} vs footage {_hex(src['skin'])} (depends on the presenter and the light: kept below confidence unless the tint is small)",
               n, c0 * (.6 if max(abs(x - 1) for x in tint(ref["skin"], src["skin"])) <= .03 else .45))
        ev.put("grade.background_tint", tint(ref["wall"], src["wall"]), f"wall RGB balance ref {_hex(ref['wall'])} vs footage {_hex(src['wall'])} (depends on the wall paint: scene-dependent)", n, c0 * .45)
        vr, vs_ = ref["corner"] / max(ref["near"], 1e-4), src["corner"] / max(src["near"], 1e-4)
        q = (vr / max(vs_, 1e-4)) ** (1 / 2.2)                 # display-referred corner/near ratio change
        vig = float(np.clip((1 - q) / max(ref["kc"] - q * ref["kn"], 1e-3), 0, .8))
        ev.put("grade.vignette", _r(vig), f"top-corner / near-wall luminance ref {vr:.2f} vs footage {vs_:.2f}", n, c0 * .55)
        lift = np.clip(np.array(ref["black"]) - np.array(src["black"]), 0, .06)
        ev.put("grade.black_lift", [_r(x, 3) for x in lift], f"p0.5 per channel ref {np.round(ref['black'], 3).tolist()} vs footage {np.round(src['black'], 3).tolist()}", n, c0 * .6)
    elif G:
        ev.note("grade.*", f"{len(G)} reference A-roll frames measured, but no project footage to compare against ({src}): grade keys not written")
    # ---------------- palette
    pal = [p for r in R for fr in r["palette"] for p in fr]; bgp = [p for r in R for fr in r["bg"] for p in fr]; nfr = sum(len(r["bg"]) * (5 if r["kind"] == "image" else 1) for r in R)   # a screenshot is a chosen frame: worth 5 samples
    if bgp:
        c, w_ = _kmeans(np.array(bgp, np.float32) / 255, 5); big = c[int(np.argmax(w_))]
        ev.put("stage.background", _hex(big), f"largest k-means colour cluster ({w_.max():.0%} of pixels) of {nfr} graphics (no-face) frames", nfr, min(1, nfr / 30) * min(1, w_.max() / .35))
        bot = np.median(np.array([b for r in R for b in r["bottom"]]) / 255, 0)
        dE = float(np.linalg.norm(_lab(bot) - _lab(big)))
        if dE > 6: ev.put("stage.glow_bottom", _hex(bot), f"bottom-band median vs background dE {dE:.1f}", nfr, min(1, nfr / 30) * .7)
        ev.put("stage.glow", dE > 6, f"bottom band differs from the background by dE {dE:.1f}", nfr, min(1, nfr / 30) * .6)
    if len(pal) > 200:
        P = np.array(pal, np.float32) / 255; c, w_ = _kmeans(P, 4)
        hsv = cv2.cvtColor(np.float32(c).reshape(-1, 1, 3), cv2.COLOR_RGB2HSV).reshape(-1, 3)
        score = w_ * (hsv[:, 1] ** 1.5)
        j = int(np.argmax(score)); acc = c[j]
        hv = hsv[j].copy(); hv[2] *= .55
        dark = cv2.cvtColor(np.float32(hv).reshape(1, 1, 3), cv2.COLOR_HSV2RGB).reshape(3)
        ev.put("colors.accent", _hex(acc), f"dominant saturated cluster ({w_[j]:.0%} of {len(pal)} saturated graphics pixels; clusters {', '.join(_hex(x) for x in c)})",
               len(pal), min(1, len(pal) / 3000 + nfr / 30) * min(1, w_[j] / .3 + .3))
        ev.put("colors.accent_dark", _hex(dark), "accent at 55% value (same hue)", len(pal), min(1, len(pal) / 3000) * .6)
    # ---------------- captions
    caption_style(R, ev)
    # ---------------- sound: integrated loudness is a note; the bed / duck / rhythm keys come from HEAR (inspire_audio)
    A = [r["audio"] for r in vids if r.get("audio")]
    Is = [a["I"] for a in A if a.get("I") is not None]
    if Is: ev.note("sound.master_lufs", f"references measure {', '.join(f'{x:.1f}' for x in Is)} LUFS integrated (platform-normalised downloads: not written)")
    from . import inspire_audio, inspire_feel
    inspire_audio.derive(vids, ev); inspire_feel.derive(vids, ev)


def _levels(levels, step):
    v = sorted(levels); out = [1.0]
    for x in v:
        if x / out[-1] >= step: out.append(x)
    out = [round(min(1.6, x), 2) for x in out][:3]
    return out if len(out) > 1 else [1.0, round(step, 2)]


def _kmeans(X, k):
    k = min(k, len(X)); crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    lab = cv2.cvtColor(X.reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(-1, 3)
    cv2.setRNGSeed(7)
    _, lbl, C = cv2.kmeans(lab.astype(np.float32), k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    w = np.bincount(lbl.ravel(), minlength=k) / len(lbl)
    rgb = np.array([np.median(X[lbl.ravel() == i], 0) if (lbl.ravel() == i).any() else [0, 0, 0] for i in range(k)])
    return rgb, w


def classify_transition(tm, tf, tc, win=.25):
    """around a cut at tc: whip = sharpness collapses (motion / zoom blur), glitch = RGB split spike, fade = luma dip below
    both sides; else cut. Returns (kind, duration_s)"""
    if not len(tm): return "cut", 0
    near = np.abs(tm - tc) <= win; base = (np.abs(tm - tc) > win) & (np.abs(tm - tc) <= 1.0)
    if near.sum() < 2 or base.sum() < 4: return "cut", 0
    sh, lu, sp = tf[:, 0], tf[:, 1], tf[:, 2]
    sb, lb, pb = np.median(sh[base]), np.median(lu[base]), np.median(sp[base])
    dt = float(np.median(np.diff(tm))) if len(tm) > 1 else .033
    if pb > 0 and sp[near].max() > max(1.8 * pb, pb + .6): return "glitch", float((sp[near] > 1.5 * pb).sum() * dt)
    if lb > 8 and lu[near].min() < .55 * min(np.median(lu[base & (tm < tc)]) if (base & (tm < tc)).any() else lb,
                                            np.median(lu[base & (tm > tc)]) if (base & (tm > tc)).any() else lb):
        return "fade", float((lu[near] < .8 * lb).sum() * dt)
    if sb > 0 and sh[near].min() < .3 * sb: return "whip", float((sh[near] < .5 * sb).sum() * dt)
    return "cut", 0


def caption_style(R, ev):
    """captions.* from the burned-in text lines of A-roll samples"""
    seq, rel, ab, hts, ratio_tall, fills, his, boxes, nlines, words = [], [], [], [], [], [], [], [], [], []
    def cand(s):     # caption candidates: below the mouth, glyphs >= 10 px at analysis size (shelf / keyboard texture is smaller)
        f = s["face"]
        return [c for c in s.get("caps", []) if c["box"][1] > f[1] + .75 * f[3] and c["h"] >= 10] if f else []
    allh = [c["h"] for r in R for s in r["samples"] for c in cand(s)]
    if len(allh) < 8:
        ev.note("captions.*", f"burned-in captions found on {len(allh)} A-roll text lines: too few to describe a caption style"); return
    lh = np.log(np.array(allh, float)); hist, edges = np.histogram(lh, bins=np.arange(lh.min(), lh.max() + .2, .18))
    j = int(np.argmax(hist)); sel = (lh >= edges[j]) & (lh <= edges[j + 1])
    hmed = float(np.exp(np.median(lh[sel])))   # the caption is the most frequent text size on A-roll frames; titles / graphics differ
    for r in R:
        for s in r["samples"]:
            if not s["face"]: continue
            caps = [c for c in cand(s) if .65 * hmed <= c["h"] <= 1.5 * hmed]
            if not caps: seq.append((r["path"], s["t"], 0)); continue
            fy, fh = s["face"][1], s["face"][3]; chin = fy + fh
            top = min(c["box"][1] for c in caps)
            # one caption block = lines stacked within 2 line heights of the top one
            blk = [c for c in caps if c["box"][1] - top < 2.6 * max(c["h"] for c in caps)]
            rel.append((top - chin) / AH); ab.append(top / AH)
            hmax = [_pct(c["hs"], 85) for c in blk]; hts.append(float(np.median(hmax)))
            for c in blk:
                hs = np.array(c["hs"]); ratio_tall.append(float((hs >= .88 * _pct(hs, 85)).mean()))
                fills.append(c["fill"]); boxes.append(c["boxed"])
                if c["hi"] is not None: his.append(c["hi"])
            nlines.append(len(blk)); wsum = sum(c["words"] for c in blk); words.append(wsum); seq.append((r["path"], s["t"], wsum))
    n = len(rel)
    if n < 8:
        ev.note("captions.*", f"burned-in captions found on {n} A-roll samples: too few to describe a caption style"); return
    share = n / max(1, len(seq)); c0 = min(1, n / 60) * min(1, share / .4 + .2)
    rs, as_ = np.std(rel), np.std(ab); mrel, mab = float(np.median(rel)), float(np.median(ab))
    if rs < .8 * as_ and -.03 <= mrel <= .22: pos, how = "chin", f"caption top sits {mrel * DESIGN_H:.0f} px under the chin (std {rs * DESIGN_H:.0f} px vs {as_ * DESIGN_H:.0f} px absolute)"
    elif abs(mab - .47) < .06: pos, how = "center", f"caption top at {mab:.0%} of the height"
    elif .58 <= mab <= .8 and as_ < .05: pos, how = "lower_third", f"caption top at {mab:.0%} of the height (std {as_:.0%})"
    else: pos, how = f"y:{int(round(mab * DESIGN_H))}", f"caption top at {mab * DESIGN_H:.0f} px (std {as_ * DESIGN_H:.0f} px)"
    ev.put("captions.position", pos, how, n, c0 * (.9 if pos == "chin" else .75))
    if pos == "lower_third": ev.put("captions.lower_third_y", _r(mab), "median caption top / frame height", n, c0 * .7)
    u = min(DESIGN_W, DESIGN_H) / 1080          # caption px keys are at a 1080 short side (scaled by gfx.U on the canvas)
    if pos == "chin": ev.put("captions.chin_gap", int(round(max(10, mrel * DESIGN_H / u))), "median gap chin -> caption top (design px)", n, c0 * .6)
    cap_h = float(np.median(hts)) * DESIGN_H / AH / u
    ev.put("captions.size", int(round(cap_h / .72)), f"median cap height {cap_h:.0f} px (design space) / 0.72 cap-height ratio", n, c0 * .7)
    tall = float(np.median(ratio_tall))
    ev.put("captions.case", "upper" if tall > .8 else "sentence", f"{tall:.0%} of glyphs reach cap height (upper case > 80%)", n, c0 * .6)
    fill = np.median(np.array(fills), 0); ev.put("captions.color", _hex(fill), "median glyph colour", n, c0 * .8)
    if len(his) >= max(5, .15 * n):
        ev.put("captions.highlight_color", _hex(np.median(np.array(his), 0)), f"glyph runs of a second colour on {len(his)} samples", len(his), c0 * .7)
    bshare = float(np.mean(boxes))
    if bshare > .5:
        bx = [c["box_rgb"] for r in R for s in r["samples"] for c in s.get("caps", []) if c.get("box_rgb")]
        if bx: ev.put("captions.box_color", _hex(np.median(np.array(bx), 0)) + "E6", f"flat surround behind {bshare:.0%} of caption lines", n, c0 * .6)
    ml = int(round(_pct(nlines, 80))); ev.put("captions.max_lines", max(1, ml), f"p80 stacked lines per caption ({collections.Counter(nlines).most_common(3)})", n, c0 * .6)
    # words per caption and how they change from sample to sample
    w = np.array([x for x in words if x > 0]); inc = dec = same = 0
    for (pa, ta, wa), (pb, tb, wb) in zip(seq[:-1], seq[1:]):
        if pa != pb or tb - ta > 1.5 / SAMPLE_FPS or wa == 0 or wb == 0: continue
        if wb > wa: inc += 1
        elif wb < wa: dec += 1
        else: same += 1
    ch = inc + dec
    if _pct(w, 50) <= 1.3 and _pct(w, 90) <= 2: style, how = "one_word", f"median {np.median(w):.1f} words on screen"
    elif ch and inc / ch >= .6: style, how = "word_reveal", f"word count grows within a caption ({inc} increments vs {dec} resets)"
    elif len(his) >= max(5, .15 * n): style, how = "highlight", f"whole phrase shown, one word in a second colour ({inc} increments vs {dec} resets)"
    elif bshare > .5: style, how = "box", f"whole phrase on a box ({inc} increments vs {dec} resets)"
    else: style, how = "pop", f"whole phrase appears at once, no box or highlight ({inc} increments vs {dec} resets; median {np.median(w):.0f} words)"
    ev.put("captions.style", style, how, n, c0 * (.75 if style != "pop" else .5))
    if style != "one_word":
        mc = int(round(_pct(w, 90) * 6.2)); ev.put("captions.max_chars", int(np.clip(mc, 8, 40)), f"p90 {(_pct(w, 90)):.0f} words per caption x 6.2 chars", n, c0 * .45)


# ======================================================================== CLI entry
def _collect(d):
    if not d or not os.path.isdir(d): return [], []
    vids, ims = [], []
    for root, _, fs in os.walk(d):
        for f in sorted(fs):
            if f.startswith("."): continue
            p = os.path.join(root, f); e = os.path.splitext(f)[1].lower()
            if e in VIDEO_EXT: vids.append(p)
            elif e in IMAGE_EXT and "frames" not in root.lower(): ims.append(p)
    return vids, ims


V2 = 1      # bump when an Edit/inspire/cache entry must be re-measured


def _job(a):
    path, max_s, sheet, frame = a
    set_frame(*frame)                       # spawn: this worker re-imported the module with the default canvas
    try: r = analyse_video(path, max_s)
    except SystemExit: raise
    except Exception as e: return dict(path=path, kind="error", error=f"{type(e).__name__}: {e}")
    from . import inspire_audio, inspire_feel, inspire_see
    for name, fn in (("hear", lambda: inspire_audio.analyse(path, max_s)), ("seam", lambda: inspire_feel.seam(path, rot=r.get("rot", 0))),
                     ("feel", lambda: inspire_feel.analyse(r, r.get("hear"))), ("see", lambda: inspire_see.analyse(path, r, sheet))):
        try: r[name] = fn()
        except SystemExit: raise
        except Exception as e:     # one failed measurement must not lose the others
            r[name] = None; r.setdefault("warnings", []).append(f"{name}: {type(e).__name__}: {e}")
    return r


def _set(d, dotted, v):
    ks = dotted.split("."); cur = d
    for k in ks[:-1]: cur = cur.setdefault(k, {})
    cur[ks[-1]] = v


def _labels(paths, d):
    """short unique names per reference: the file stem, else the relative path without extension"""
    stems = [os.path.splitext(os.path.basename(p))[0] for p in paths]
    out = []
    for p, st in zip(paths, stems):
        lab = st if stems.count(st) == 1 else os.path.splitext(os.path.relpath(p, d))[0].replace(os.sep, "_")
        out.append(lab)
    return out


def _cache_key(path, max_s):
    st = os.stat(path); return f"{V2}|{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}|{float(max_s):g}"


def _cache_get(cdir, lab, key):
    import pickle
    p = os.path.join(cdir, lab + ".pkl")
    if not os.path.exists(p): return None
    try:
        with open(p, "rb") as f: k, r = pickle.load(f)
    except Exception: return None
    if k != key or not os.path.exists(((r.get("see") or {}).get("sheet")) or ""): return None
    return r


def _cache_put(cdir, lab, key, r):
    import pickle
    os.makedirs(cdir, exist_ok=True)
    with open(os.path.join(cdir, lab + ".pkl"), "wb") as f: pickle.dump((key, r), f)


def run(pr, refs=None, dry_run=False, max_s=90.0, min_conf=.5, workers=None, mix=None, refresh=False):
    """measure every reference (cached in Edit/inspire/cache), derive per reference and pooled, choose a source per
    dimension (inspire_mix), write Edit/inspire/REPORT.md + contact sheets always and Edit/style.yaml unless dry_run"""
    from . import inspire_mix as MX, inspire_report as RP, inspire_see, style as STY
    d = os.path.abspath(os.path.expanduser(refs)) if refs else pr.p("Inspirations")
    from . import gfx as G, style as STY
    set_frame(*G.canvas_of(STY.load(pr), pr))
    vids, ims = _collect(d)
    if not vids and not ims:
        raise SystemExit(f"no reference videos or images in {d}: put the client's reference edits there (or pass --refs DIR)")
    print(f"inspire: {len(vids)} video(s), {len(ims)} image(s) from {d}")
    idir = pr.e("inspire"); cdir = os.path.join(idir, "cache"); os.makedirs(idir, exist_ok=True)
    paths = vids + ims; labs = dict(zip(paths, _labels(paths, d)))
    meta_raw, ry = MX.load_refs_yaml(d)
    rel = {labs[p]: os.path.relpath(p, d) for p in paths}
    meta = {}
    for k, v in meta_raw.items():
        lab = MX.match_ref(k, rel)
        if not lab: print(f"  refs.yaml: '{k}' matches no reference (refs: {', '.join(rel)})"); continue
        meta[lab] = v
    forced = MX.parse_mix(mix, rel) if mix else {}
    if ry: print(f"  refs.yaml: {len(meta)} entr{'y' if len(meta) == 1 else 'ies'} from {ry}")
    got = {}; todo = []
    for v in vids:
        key = _cache_key(v, max_s); r = None if refresh else _cache_get(cdir, labs[v], key)
        if r: got[v] = r
        else: todo.append(v)
    if todo:
        import multiprocessing as _mp
        from concurrent.futures import ProcessPoolExecutor
        nw = workers or int(os.environ.get("CVES_INSPIRE_WORKERS", "0") or 0) or max(1, min(len(todo), (os.cpu_count() or 4) // 2))
        args = [(v, max_s, os.path.join(idir, labs[v] + "-sheet.jpg"), (DESIGN_W, DESIGN_H)) for v in todo]
        # a worker that dies (out of memory on a small machine) raises BrokenProcessPool here; multiprocessing.Pool waited forever
        ex = ProcessPoolExecutor(nw, mp_context=_mp.get_context("spawn")) if nw > 1 else None   # no fork: see render.py
        try:
            for r in (ex.map(_job, args) if ex else map(_job, args)):
                if r.get("kind") == "error": print(f"  skipped {os.path.basename(r['path'])}: {r['error']}"); continue
                for w in r.get("warnings", []): print(f"  ({os.path.basename(r['path'])}: {w})")
                _cache_put(cdir, labs[r["path"]], _cache_key(r["path"], max_s), r); got[r["path"]] = r
        finally:
            if ex: ex.shutdown(cancel_futures=True)
    R, labels = [], []
    for v in vids:
        if v not in got: continue
        r = got[v]; nf = sum(1 for s in r["samples"] if s["face"])
        print(f"  {os.path.basename(v)[:44]:44s} {r['dur']:5.1f} s  {len(r['cuts']):3d} cuts  face {nf}/{len(r['samples'])}"
              f"{'  (cached)' if v not in todo else ''}")
        R.append(r); labels.append(labs[v])
    for p in ims:
        r = analyse_image(p)
        if r:
            r["see"] = inspire_see.analyse_image(p, os.path.join(idir, labs[p] + "-sheet.jpg")); R.append(r); labels.append(labs[p])
    src, src_how = source_stats(pr)
    print(f"  project footage for the grade comparison: {src_how}")
    # ---- per reference, pooled, then one source per dimension
    per_ref = {}
    for r, lab in zip(R, labels):
        e = Evidence(); derive([r], src, e); per_ref[lab] = e
    pool_R = [r for r, lab in zip(R, labels) if float(meta.get(lab, {}).get("weight", 1.0)) > 0] or R
    pooled = Evidence(); derive(pool_R, src, pooled)
    ev, plan, rows = MX.decide(per_ref, pooled, meta, STY.load(), forced, min_conf)
    keep = {k: v for k, v in ev.keys.items() if ev.conf.get(k, 0) >= min_conf}
    out = {}
    for k, v in sorted(keep.items()): _set(out, k, v)
    out["_evidence"] = {k: ev.ev[k] for k in sorted(ev.ev)}
    dropped = sorted(k for k in ev.keys if k not in keep)
    out["_inspire"] = {"refs": [os.path.relpath(r["path"], d) for r in R], "refs_dir": d, "date": datetime.date.today().isoformat(),
                       "source": src_how, "min_confidence": min_conf, "dropped": dropped,
                       "mix": {dim: {"source": p["source"], "rule": p["rule"], "consistency": p["consistency"]} for dim, p in plan.items()},
                       "ranking": {lab: {k: v for k, v in m.items() if k in ("rank", "weight", "kind", "use", "notes")} for lab, m in meta.items()},
                       "aesthetics": {lab: _aesthetic_note(r.get("see")) for r, lab in zip(R, labels)},
                       "report": os.path.join(idir, "REPORT.md")}
    print("\n" + summary(ev, keep))
    print("\n" + MX.table(plan, rows, labels))
    rp, rv = RP.write(idir, R, labels, meta, plan, keep, dropped, d, written=not dry_run)
    print(f"\nreport: {rp}\nlook at the contact sheets and fill: {rv}")
    if dry_run: print("\n--dry-run: Edit/style.yaml not written"); return out
    p = pr.e("style.yaml")
    if os.path.exists(p): shutil.copy2(p, p + ".bak")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Written by `cves inspire` on {datetime.date.today()} from {len(R)} reference(s) in {d}.\n"
                "# Merged over the preset, under Brand/style.yaml and edit.yaml `style:` (docs/STYLE.md). Edit freely; re-running overwrites (a .bak is kept).\n"
                "# Which reference each dimension came from: _inspire.mix; the full read: Edit/inspire/REPORT.md.\n")
        yaml.safe_dump(_plain(out), f, sort_keys=False, allow_unicode=True, width=160, default_flow_style=None)
    print(f"\nwrote {p} ({len(keep)} keys)")
    return out


def _aesthetic_note(s):
    if not s or "contrast" not in s: return None
    keep = ("size", "orientation", "display_aspect", "content_aspect", "letterbox", "contrast", "saturation", "temperature", "grain", "vignette", "motion_blur")
    return {k: s[k] for k in keep if k in s}


def _plain(x):
    """numpy scalars / tuples -> plain YAML types"""
    if isinstance(x, dict): return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [_plain(v) for v in x]
    if isinstance(x, np.generic): return x.item()
    return x


def summary(ev, keep):
    rows = []
    for k in sorted(ev.ev):
        v = ev.keys.get(k, "-"); mark = "  " if k in keep else "x "
        vs = json.dumps(v) if not isinstance(v, str) else v
        rows.append(f"{mark}{k:32s} {vs:22s} {ev.ev[k]}")
    return "measured style (x = below confidence, not written):\n" + "\n".join(rows)
