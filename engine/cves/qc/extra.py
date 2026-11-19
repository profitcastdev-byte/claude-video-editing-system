"""Extra QC gates: the QC-GATES.md rows that were still TO BUILD and can be measured with the instruments the engine
already writes. Called once from qc.run(); every gate reports through the same gate(gid, ok, summary, details, status).

Instruments read: Edit/elements.jsonl (one record per element per frame), Edit/timeline.json, Edit/words.json,
Edit/faces.json (box + 10 YuNet landmark values, plate scale), Edit/matte/*.mkv + Edit/plate/*.mkv (one frame per shot),
Edit/stems/*.wav, Edit/mix_premaster.wav, Edit/mix.wav, the SFX cue list (mix.all_cues) and the delivered MP4
(decoded once with PyAV as 8-bit YCbCr, converted with the BT.709 matrix here; OpenCV's BGR decode uses BT.601).

Conventions: a CALIBRATE threshold never FAILs (WARN with the measured value). A gate whose inputs are missing or whose
measurement throws reports WARN "not measured" so it is visible in the report. The A-roll transform (punch-in, creep,
face-centre smoothing, snap) is re-derived from timeline.json + faces.json exactly as render.compose does it."""
import os, re, json, math, collections
import numpy as np, cv2

from ..gfx import DESIGN as _D
W, H = _D                  # the canvas of the video being judged: run_extra sets them from timeline.json (element bboxes are canvas px)
TRANS_DUR = {"whip": .15, "glitch": .10, "cut": 0}          # render.TRANS_DUR (unknown kinds use .12, as trans_strength)
DECOR = ("brackets", ".glow", ".bed")                        # frame decoration / glow / shadow beds: not type, not movers
DESCRIPTOR = {"map", "listing", "map pack", "logo"}          # `text` used as a label on graphic-only elements
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CAP_SIZE, CAP_MAXW, CAP_LH = 50, 780, 66                     # render.caption_el layout at a 1080 short side (scaled by U_)
U_ = 1.0                                                     # min(W, H) / 1080 of the video being judged
LOW = (270, 480)                                             # low-res analysis size (canvas aspect)
SFX_PEAK_NAMES = ("whoosh", "riser")                         # SND-08: transition whooshes / risers are judged at their peak


# ======================================================================== helpers
def clamp(x, a=0., b=1.): return max(a, min(b, x))

def rgb709(Y, Cb, Cr):
    """8-bit limited-range YCbCr planes -> R'G'B' float 0..1 (BT.709 matrix)"""
    y = (Y.astype(np.float32) - 16) / 219; cb = (Cb.astype(np.float32) - 128) / 224; cr = (Cr.astype(np.float32) - 128) / 224
    return np.clip(np.stack([y + 1.5748 * cr, y - .1873 * cb - .4681 * cr, y + 1.8556 * cb], -1), 0, 1)

def rel_lum(rgb):
    c = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    return c @ np.array([.2126, .7152, .0722], np.float32)

def lab_of(rgb):
    return cv2.cvtColor(rgb.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_RGB2Lab).reshape(-1, 3)

def runs_of(mask):
    """[(start, end_exclusive)] of True runs in a 1-D bool array"""
    m = np.concatenate([[0], mask.astype(np.int8), [0]]); d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))

def longest_run(mask):
    r = runs_of(mask); return max((b - a for a, b in r), default=0)

def bs1770(y, sr):
    """integrated loudness (LUFS) of a mono signal, ITU-R BS.1770-4 (K-weighting, 400 ms blocks, -70 / -10 gates)"""
    from scipy.signal import lfilter
    G, Q, fc = 4.0, 1 / np.sqrt(2), 1681.974450955533
    A = 10 ** (G / 40); w0 = 2 * np.pi * fc / sr; al = np.sin(w0) / (2 * Q); cs = np.cos(w0)
    b = [A * ((A + 1) + (A - 1) * cs + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cs), A * ((A + 1) + (A - 1) * cs - 2 * np.sqrt(A) * al)]
    a = [(A + 1) - (A - 1) * cs + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cs), (A + 1) - (A - 1) * cs - 2 * np.sqrt(A) * al]
    y = lfilter(np.array(b) / a[0], np.array(a) / a[0], y)
    fc, Q = 38.13547087602444, .5003270373238773; w0 = 2 * np.pi * fc / sr; al = np.sin(w0) / (2 * Q); cs = np.cos(w0)
    y = lfilter(np.array([(1 + cs) / 2, -(1 + cs), (1 + cs) / 2]) / (1 + al), np.array([1 + al, -2 * cs, 1 - al]) / (1 + al), y)
    blk, hop = int(.4 * sr), int(.1 * sr)
    if len(y) < blk: return float("nan")
    z = np.array([np.mean(y[i:i + blk] ** 2) for i in range(0, len(y) - blk + 1, hop)])
    l = -.691 + 10 * np.log10(z + 1e-12); z = z[l > -70]
    if not len(z): return float("nan")
    rel = -.691 + 10 * np.log10(z.mean()) - 10; z = z[-.691 + 10 * np.log10(z + 1e-12) > rel]
    return float(-.691 + 10 * np.log10(z.mean())) if len(z) else float("nan")


class Inst:
    """one element instance: a run of log records for one id (an id reused by a later cutaway is a new instance)"""
    def __init__(self, key, recs):
        self.key, self.recs = key, recs; r0 = recs[0]
        self.id, self.role, self.text, self.t_key, self.asset, self.font = r0["id"], r0["role"], r0.get("text"), r0.get("t_key"), r0.get("asset"), r0.get("font")
        self.f = np.array([r["f"] for r in recs]); self.bb = np.array([r["bbox"] for r in recs], float); self.al = np.array([r["alpha"] for r in recs], float)
        self.f0, self.f1 = int(self.f[0]), int(self.f[-1])
        self.cls = re.sub(r"\d+$", "", self.id.split("@")[0])          # list.item0 -> list.item ; caption@1.51 -> caption
    @property
    def decor(self): return any(d in self.id for d in DECOR)
    @property
    def is_text(self):
        return bool(self.text) and self.text.strip().lower() not in DESCRIPTOR and not self.decor


# ======================================================================== context
class Ctx:
    def __init__(self, pr, video):
        self.pr, self.video, self.E = pr, video, pr.edit
        from .. import style as STY
        self.S = STY.load(pr); self.CS = {**(self.S.get("captions") or {}), **(pr.edit.get("captions") or {})}
        TL = pr.json("timeline.json", {}) or {}; self.TLm = TL
        self.FPS = TL.get("fps") or (pr.json("edl.json", {}) or {}).get("fps") or 30.0; self.A = int(TL.get("a_frames", 0)); self.N = int(TL.get("frames", 0)); self.T_END = self.A / self.FPS
        self.segs = TL.get("segments", []); self.cuts = TL.get("cutaways", []); self.trans = [tuple(x) for x in TL.get("transitions", [])]
        self.zoom = TL.get("zoom", {}); self.creep = TL.get("creep", .015); self.snap = TL.get("snap"); self.lift = set(TL.get("lift", []))
        self.faces = pr.json("faces.json", {}) or {}; self.words = pr.json("words.json", []) or []
        self.spine = TL.get("spine") or "aroll"; self.cards = [c for c in self.cuts if not c.get("broll")]
        ef = pr.e("elements.jsonl")
        self.els = [json.loads(l) for l in open(ef, encoding="utf-8")] if os.path.exists(ef) else []
        self.by_f = collections.defaultdict(list)
        for e in self.els: self.by_f[e["f"]].append(e)
        runs = collections.OrderedDict()
        for e in sorted(self.els, key=lambda r: (r["id"], r["f"])):
            L = runs.setdefault(e["id"], [])
            if L and (e["role"] == "caption" or e["f"] - L[-1][-1]["f"] <= 6): L[-1].append(e)
            else: L.append([e])
        self.inst = []
        for k, L in runs.items():
            for j, r in enumerate(L): self.inst.append(Inst(k if len(L) == 1 else f"{k}#{j + 1}", r))
        self.inst.sort(key=lambda i: i.f0)
        self.caps = [i for i in self.inst if i.role == "caption"]
        self.seg_idx = np.full(max(self.N, self.A, 1), -1, int)
        for j, s in enumerate(self.segs): self.seg_idx[s["f0"]:s["f0"] + s["n"]] = j
        self.cap_hide = [tuple(x) for x in (self.E.get("captions", {}) or {}).get("hide", [])]
        self._results = collections.defaultdict(list)

    # ---- timeline queries
    def in_cut(self, t): return any(c["start"] <= t < c["end"] for c in self.cuts)
    def is_aroll(self, f): return self.spine == "aroll" and 0 <= f < self.A and not self.in_cut(f / self.FPS)
    def in_card(self, t): return any(c["start"] <= t < c["end"] for c in self.cards)           # a drawn cutaway (not a B-roll shot)
    def in_trans(self, f, pad=0.):
        t = f / self.FPS
        for tb, kind in self.trans:
            d = 0 if kind in (None, "cut") else float(self.S.get(f"transitions.{kind}_s", TRANS_DUR.get(kind, .12)))   # the window render drew (craft.trans_dur)
            if d and abs(t - tb) < d + pad: return (tb, kind)
        return None
    def in_snap(self, f): return bool(self.snap) and self.snap[0] <= f / self.FPS < self.snap[1]
    def snap_hides_captions(self, f):
        """render.compose: the snap hides captions only where its segment has roto type (which replaces them)"""
        if not self.in_snap(f): return False
        s = self.seg_of(f); roto = {r.get("segment") for r in (self.E.get("roto") or [])}
        return bool(s) and s["id"] in roto
    def seg_of(self, f): j = self.seg_idx[f] if 0 <= f < len(self.seg_idx) else -1; return self.segs[j] if j >= 0 else None

    def aroll_M(self, f):
        """the A-roll affine of render.compose for frame f: (M 2x3, segment, k, raw face row) or None"""
        if not self.is_aroll(f): return None
        s = self.seg_of(f); sid = s["id"]; k = f - s["f0"]; F = self.faces.get(sid)
        if not F: return None
        lo, hi = max(0, k - 6), min(len(F), k + 7)
        if hi <= lo: lo, hi = len(F) - 1, len(F)
        cx = float(np.mean([F[j][0] + F[j][2] / 2 for j in range(lo, hi)])); cy = float(np.mean([F[j][1] + F[j][3] / 2 for j in range(lo, hi)]))
        fh = float(np.mean([F[j][3] for j in range(lo, hi)])); t = f / self.FPS
        z = self.zoom.get(sid, 1.0) * (1 + self.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
        if self.in_snap(f): z = self.snap[2]
        ay = H if sid in self.lift else cy - fh * .05
        tx, ty = cx - z * cx, ay - z * ay; tx = min(0, max(W - z * W, tx)); ty = min(0, max(H - z * H, ty))
        return np.float32([[z, 0, tx], [0, z, ty]]), s, k, F[min(k, len(F) - 1)]

    def cap_allowed(self, f):
        """frames where the renderer may draw a caption: A-roll, no chest element, not the snap, not a hide window"""
        t = f / self.FPS                 # A-roll, B-roll shots and uncovered frames take captions; drawn cutaways do not
        if not 0 <= f < self.A or self.in_card(t) or self.snap_hides_captions(f): return False
        if any(a <= t < b for a, b in self.cap_hide): return False
        return not any(e["role"] == "chest" for e in self.by_f.get(f, []))

    def cap_words(self, ins):
        """word timings [(start, end, word)] of a caption event (log text is the full event; t_key is its first word)"""
        i = self.cap_word_index(ins); n = len((ins.text or "").split())
        return self.words[i:i + n] if i is not None else []

    def cap_word_index(self, ins):
        if ins.t_key is None: return None
        return next((j for j, w in enumerate(self.words) if abs(w[0] - ins.t_key) < 1e-3), None)


# ======================================================================== frame decoding (one pass)
def decode(cx, need, keep_low=True):
    """single decode of the delivered file. need: {frame: [callback(f, yuv444 (3,H,W) uint8)]}. Returns low-res luma per frame."""
    import av
    low = {}
    with av.open(cx.video) as c:
        for f, fr in enumerate(c.decode(video=0)):
            if keep_low: low[f] = fr.reformat(width=LOW[0], height=LOW[1], format="gray").to_ndarray()
            cbs = need.get(f)
            if cbs:
                yuv = fr.to_ndarray(format="yuv444p")
                for cb in cbs:
                    try: cb(f, yuv)
                    except Exception as e: cx._results["errors"].append(f"f{f}: {type(e).__name__}: {e}")
    return low

def decode_plate_frames(cx, path, ks, fmt="gray"):
    import av
    out, ks = {}, set(ks)
    if not ks or not os.path.exists(path): return out
    with av.open(path) as c:
        for k, fr in enumerate(c.decode(video=0)):
            if k in ks: out[k] = fr.to_ndarray(format=fmt)
            if k >= max(ks): break
    return out


# ======================================================================== measurements on one frame
def text_contrast(yuv, bbox, pad=6, person=None):
    """WCAG ratio per glyph-sized ink component vs its own 3-7 px surround, in the delivered frame.
    Ink polarity: the Otsu class that touches the bbox border less is the ink. Returns [(ratio, glyph_h)]"""
    x0, y0, x1, y1 = [int(round(v)) for v in bbox]
    x0, y0, x1, y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad + 1), min(H, y1 + pad + 1)
    if x1 - x0 < 6 or y1 - y0 < 6: return []
    Yc = yuv[0, y0:y1, x0:x1]
    rgb = rgb709(Yc, yuv[1, y0:y1, x0:x1], yuv[2, y0:y1, x0:x1]); L = rel_lum(rgb)
    thr, _ = cv2.threshold(Yc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); bright = Yc > thr
    border = np.concatenate([bright[0], bright[-1], bright[:, 0], bright[:, -1]])
    ink = ~bright if border.mean() > .5 else bright
    pm = cv2.dilate(person[y0:y1, x0:x1].astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) if person is not None else np.zeros_like(ink)
    ink = ink & ~pm
    n, cc, st, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    ink_d = cv2.dilate(ink.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(bool)
    k7, k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if h < 8 or a < 15 or h > 420 or w > 600: continue
        X0, Y0, X1, Y1 = max(0, x - 9), max(0, y - 9), min(ink.shape[1], x + w + 9), min(ink.shape[0], y + h + 9)
        comp = (cc[Y0:Y1, X0:X1] == i).astype(np.uint8)
        core = cv2.erode(comp, np.ones((3, 3), np.uint8)).astype(bool)
        if core.sum() < 4: core = comp.astype(bool)
        ring = cv2.dilate(comp, k15).astype(bool) & ~cv2.dilate(comp, k7).astype(bool) & ~ink_d[Y0:Y1, X0:X1] & ~pm[Y0:Y1, X0:X1]
        if ring.sum() < 10: continue
        lf, lb = float(np.median(L[Y0:Y1, X0:X1][core])), float(np.median(L[Y0:Y1, X0:X1][ring]))
        fill_lab = lab_of(np.median(rgb[Y0:Y1, X0:X1][core], 0)[None])[0]
        out.append(((max(lf, lb) + .05) / (min(lf, lb) + .05), int(h), fill_lab))
    # text = runs of same-coloured glyphs: keep colour clusters (dE < 15) with >= 3 components; drops stray blobs (skin, icons)
    keep, used = [], [False] * len(out)
    for a in range(len(out)):
        if used[a]: continue
        grp = [b for b in range(len(out)) if not used[b] and np.linalg.norm(out[a][2] - out[b][2]) < 15]
        for b in grp: used[b] = True
        if len(grp) >= 3: keep += [out[b][:2] for b in grp]
    return keep

def caption_measure(yuv, bbox):
    """white caption ink inside the logged bbox: line bands, widths, cap height, fill, shadow, plate margin"""
    x0, y0, x1, y1 = [int(round(v)) for v in bbox]
    X0, Y0, X1, Y1 = max(0, x0 - 4), max(0, y0 - 4), min(W, x1 + 5), min(H, y1 + 5)
    Y = yuv[0, Y0:Y1, X0:X1].astype(np.int16); Cb = yuv[1, Y0:Y1, X0:X1].astype(np.int16) - 128; Cr = yuv[2, Y0:Y1, X0:X1].astype(np.int16) - 128
    ink = (Y > 185) & (np.abs(Cb) < 16) & (np.abs(Cr) < 16)
    if ink.sum() < 30: return None
    rows = ink.sum(1); bands = []
    for a, b in runs_of(rows > 0):
        if bands and a - bands[-1][1] < 10: bands[-1] = (bands[-1][0], b)
        else: bands.append((a, b))
    bands = [(a, b) for a, b in bands if b - a >= 12]
    if not bands: return None
    widths, caps_, xs_ = [], [], []
    for a, b in bands:
        cols = np.where(ink[a:b].any(0))[0]; widths.append(int(cols[-1] - cols[0] + 1))
        r = rows[a:b]; base = a + int(np.where(r >= .25 * r.max())[0][-1]); caps_.append(base - a + 1)   # band top (cap / ascender) to baseline
        xs_.append(base - (a + int(np.where(r >= .5 * r.max())[0][0])) + 1)                            # x-height: most glyph tops
    core = cv2.erode(ink.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    if core.sum() < 10: core = ink
    fill = np.median(rgb709(Y[core].astype(np.uint8), (Cb[core] + 128).astype(np.uint8), (Cr[core] + 128).astype(np.uint8)), 0) * 255
    # shadow: luma 4-8 px under the bottom of each stroke of the last line vs 22-30 px under it (same columns, full frame)
    a, b = bands[-1]; near, far = [], []
    for x in np.where(ink[a:b].any(0))[0][::2]:
        yb = Y0 + a + int(np.where(ink[a:b, x])[0][-1]); X = X0 + x
        if yb + 30 < H: near.append(np.median(yuv[0, yb + 4:yb + 9, X])); far.append(np.median(yuv[0, yb + 22:yb + 31, X]))
    shadow = float(np.median(far) - np.median(near)) if near else None
    ys, xs = np.where(ink); margin = max(ys.min() + Y0 - y0, y1 - (ys.max() + Y0), xs.min() + X0 - x0, x1 - (xs.max() + X0))
    return dict(lines=len(bands), widths=widths, cap_h=int(max(caps_)), x_h=int(np.median(xs_)), fill=[float(v) for v in fill], shadow=shadow, margin=int(margin))

def cheek_patches(yuv, lm, fw):
    """YuNet landmarks (delivered-frame coords): the two cheek patches between eye and mouth corner (render.skin_lab)"""
    k = max(4, int(fw * .05)); out = []
    for eye, mouth in ((lm[0], lm[3]), (lm[1], lm[4])):
        cx, cy = eye * .55 + mouth * .45; x0, y0 = int(cx) - k, int(cy) - k
        if x0 < 0 or y0 < 0 or x0 + 2 * k > W or y0 + 2 * k > H: continue
        out.append(yuv[:, y0:y0 + 2 * k, x0:x0 + 2 * k].reshape(3, -1))
    return out


# ======================================================================== the A-roll pass (frame, matte, colour, framing)
def plan_aroll(cx):
    """sampled A-roll frames: every 6th visible frame + first, middle and last visible frame of every shot"""
    per = collections.OrderedDict()
    for s in cx.segs:     # whip / glitch frames are zoom-blurred or line-shifted: not a picture of the shot
        vis = [f for f in range(s["f0"], s["f0"] + s["n"]) if cx.is_aroll(f) and not cx.in_trans(f)]
        if not vis: continue
        pick = set(vis[::6]) | {vis[0], vis[len(vis) // 2], vis[-1]}
        per[s["id"]] = dict(seg=s, vis=vis, pick=sorted(pick), first=vis[0], last=vis[-1], mid=vis[len(vis) // 2])
    return per

def aroll_frame(cx, f, yuv, matte, plate):
    m = cx.aroll_M(f)
    if m is None or matte is None: return
    M, s, k, face = m; z, tx, ty = float(M[0, 0]), float(M[0, 2]), float(M[1, 2])
    Am = cv2.warpAffine(matte, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    inside = Am > 127
    fb = [face[0] * z + tx, face[1] * z + ty, face[2] * z, face[3] * z]
    lm = (np.array(face[4:14], float).reshape(5, 2) * z + [tx, ty]) if len(face) >= 14 and any(face[4:14]) else None
    chin = fb[1] + fb[3]; fcx, fcy = fb[0] + fb[2] / 2, fb[1] + fb[3] / 2
    els = cx.by_f.get(f, []); elmask = np.zeros((H, W), bool)
    for e in els:
        x0, y0, x1, y1 = e["bbox"]; elmask[max(0, int(y0) - 12):int(y1) + 13, max(0, int(x0) - 12):int(x1) + 13] = True
    r = dict(f=f, sid=s["id"], snap=cx.in_snap(f))
    # FRAME-02: body exits through frame edges (bottom), no straight in-frame matte cut
    r["bottom"] = float(inside[-1].mean()); r["top"] = int(inside[0].sum())
    hb = inside[2:-2] != inside[1:-3]; vb = inside[:, 2:-2] != inside[:, 1:-3]
    r["hcut"] = int(max(longest_run(row) for row in hb[::2])); r["vcut"] = int(max(longest_run(col) for col in vb.T[::2]))
    # FRAME-05 headroom: first row with matte > 0.5
    rows = np.where(inside.any(1))[0]; r["headroom"] = int(rows[0]) if len(rows) else None
    if lm is not None:
        r["eye_y"] = float(lm[:2, 1].mean()); r["eye_x"] = float(lm[:2, 0].mean())
    # FRAME-03 halo: luma 3-7 px outside the matte edge vs the wall 20-40 px out ALONG THE SAME NORMAL: every outside pixel is
    # binned by its nearest subject pixel (40 px cells of the edge); a cell is judged only where its wall band is uniform
    # (std <= 10 Y), so a background object edge near the silhouette is not read as a halo
    Y = yuv[0]
    dist, lab = cv2.distanceTransformWithLabels((~inside).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    reg = np.zeros((H, W), bool); reg[6:int(min(H - 6, chin + .6 * fb[3])), 6:W - 6] = True; reg &= ~elmask
    src = np.flatnonzero(inside.ravel())   # label i -> i-th zero pixel of the source (= subject pixel) in raster order
    band = reg & (((dist >= 3) & (dist <= 7)) | ((dist >= 20) & (dist <= 40)))
    by, bx = np.where(band); nl = lab[by, bx] - 1; ok = (nl >= 0) & (nl < len(src)); by, bx, nl = by[ok], bx[ok], nl[ok]
    cell = (src[nl] // W // 40) * 1000 + (src[nl] % W) // 40; isring = dist[by, bx] <= 7; yv = Y[by, bx].astype(float)
    worst = None
    for cid in np.unique(cell):
        m = cell == cid; a, b = yv[m & isring], yv[m & ~isring]
        if len(a) < 40 or len(b) < 80 or b.std() > 10: continue
        ex = float(np.median(a) - np.median(b))
        if worst is None or ex > worst[0]: worst = (ex, f"edge cell x{(cid % 1000) * 40} y{(cid // 1000) * 40}", float(np.median(a)), float(np.median(b)))
    r["halo"] = worst
    # colour: skin core (cheeks), wall patch, frame statistics with graphics masked
    if lm is not None:      # each cheek summarised on its own, then averaged: side light makes the two cheeks 40-80 Y apart,
        pcs = cheek_patches(yuv, lm, fb[2])   # so a pooled median flips between them as the head turns
        if pcs and all(p.shape[1] > 15 for p in pcs) and len(pcs) == 2:
            st = []
            for px in pcs:
                Cb, Cr = px[1].astype(float) - 128, px[2].astype(float) - 128
                st.append((np.median(px[0]), np.median(np.degrees(np.arctan2(Cr, Cb)) % 360), np.median(np.hypot(Cb, Cr)), np.median(lab_of(rgb709(px[0], px[1], px[2])), 0)))
            r["skin_Y"] = float(np.mean([s_[0] for s_ in st])); r["skin_hue"] = float(np.mean([s_[1] for s_ in st]))
            r["skin_chroma"] = float(np.mean([s_[2] for s_ in st])); r["skin_lab"] = np.mean([s_[3] for s_ in st], 0).tolist()
    # wall patch: background 60-160 px out from the silhouette, above the eye line (the same wall round the head in every framing)
    wm = (dist >= 60) & (dist <= 160) & (Am < 5) & ~elmask; wm[:int(.03 * H)] = False; wm[int(fb[1] + .4 * fb[3]):] = False; wm[:, :20] = False; wm[:, W - 20:] = False
    if wm[::3, ::3].sum() > 300:
        sel = (slice(None), slice(None, None, 3), slice(None, None, 3)); w3 = wm[::3, ::3]
        P = yuv[sel][:, w3]; r["wall_lab"] = lab_of(rgb709(P[0], P[1], P[2])).mean(0).tolist(); r["wall_Y"] = float(P[0].mean())
    nm = ~elmask[::2, ::2]; Yn = Y[::2, ::2][nm].astype(float)
    Cn = np.hypot(yuv[1, ::2, ::2][nm].astype(float) - 128, yuv[2, ::2, ::2][nm].astype(float) - 128)
    r["Y_mean"] = float(Yn.mean()); r["C_mean"] = float(Cn.mean()); r["Y_p01"] = float(np.percentile(Yn, .1)); r["Y_p999"] = float(np.percentile(Yn, 99.9))
    r["Y_p1"] = float(np.percentile(Yn, 1)); r["Y_p99"] = float(np.percentile(Yn, 99)); r["C_p99"] = float(np.percentile(Cn, 99))
    # FRAME-10: correlation with the warped plate vs the warped mirrored plate, and the similarity transform plate -> frame
    if plate is not None:
        g = lambda im: cv2.magnitude(*[cv2.Sobel(cv2.resize(im, LOW, interpolation=cv2.INTER_AREA).astype(np.float32), cv2.CV_32F, *d) for d in ((1, 0), (0, 1))])
        def zncc(a, b): a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))
        dv = g(Y); r["corr"] = zncc(dv, g(cv2.warpAffine(plate, M, (W, H), borderMode=cv2.BORDER_REPLICATE)))
        r["corr_flip"] = zncc(dv, g(cv2.warpAffine(cv2.flip(plate, 1), M, (W, H), borderMode=cv2.BORDER_REPLICATE)))
        orb = cv2.ORB_create(3000); k1, d1 = orb.detectAndCompute(plate, None); k2, d2_ = orb.detectAndCompute(Y, None)
        if d1 is not None and d2_ is not None:
            mt = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2_)
            if len(mt) >= 20:
                A_, inl = cv2.estimateAffinePartial2D(np.float32([k1[m.queryIdx].pt for m in mt]), np.float32([k2[m.trainIdx].pt for m in mt]), ransacReprojThreshold=3)
                if A_ is not None:
                    r["rot"] = float(np.degrees(np.arctan2(A_[1, 0], A_[0, 0]))); r["scale"] = float(np.hypot(A_[0, 0], A_[1, 0])); r["inliers"] = int(inl.sum()); r["z"] = z
    cx._results["aroll"].append(r)


# ======================================================================== gates: captions
def gates_captions(cx, gate):
    caps = cx.caps; FPS = cx.FPS
    if not caps:
        for g in ("PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07", "PLAT-08", "PLAT-09", "PLAT-10", "GFX-16"): gate(g, False, "no caption events in the element log", status="WARN")
        return
    from PIL import ImageFont
    size, maxw = CAP_SIZE, CAP_MAXW
    try:                                 # the caption wrap width on this canvas, in px at the 50 px design size
        from .. import captions as CAPM, gfx as G
        maxw = CAPM._avail(CAPM.resolve(cx.CS), cx.S)[0] / G.U
    except Exception: pass
    fonts = {}
    def wrap(ins):
        fn = (ins.font or "Poppins-SemiBold"); p = os.path.join(REPO, "assets", "fonts", fn + ".ttf")
        if fn not in fonts: fonts[fn] = ImageFont.truetype(p, size) if os.path.exists(p) else None
        f = fonts[fn]; ws = (ins.text or "").split(); lines, cur = [], []
        if f is None: return [ws]
        for w in ws:
            if cur and f.getlength(" ".join(cur + [w])) > maxw: lines.append(cur); cur = [w]
            else: cur.append(w)
        return lines + [cur]
    meas = {m["key"]: m for m in cx._results["capmeas"]}
    l4, l4w, l5, l6, l7, l8, l8r, g16, nw = [], [], [], [], [], [], 0, [], []
    for c in caps:
        lines = wrap(c); m = meas.get(c.key); nl = max(len(lines), m["lines"] if m else 0)
        if nl > 2: l4.append(f"{c.id} '{c.text}': {nl} lines")
        elif nl == 2: l4w.append(c.id)
        for j, ln in enumerate(lines):
            s = " ".join(ln); wpx = m["widths"][j] if m and j < len(m["widths"]) and m["lines"] == len(lines) else None
            if len(s) > 32 or (wpx and wpx > 950 * U_): l5.append(f"{c.id} line {j + 1}: {len(s)} chars{f', {wpx} px' if wpx else ''} '{s}'")
        if len(lines) >= 2 and len(lines[-1]) < 2: g16.append(f"{c.id}: last line '{' '.join(lines[-1])}'")
        dur = len(c.f) / FPS; cps = len(c.text or "") / max(dur, 1e-6)
        if cps > 20: l6.append(f"{c.id}: {cps:.0f} cps ({len(c.text)} chars in {dur:.2f} s)")
        if dur < .83: l7.append(f"{c.id}: {dur:.2f} s on screen ({len(c.f)} f, frames {c.f0}-{c.f1})")
        nw.append(len((c.text or "").split()))
        ws = cx.cap_words(c)
        if not ws: l8.append(f"{c.id}: first word not found in words.json"); continue
        wf = ws[0][0] * FPS
        if cx.cap_allowed(int(round(wf))) or cx.cap_allowed(int(math.ceil(wf))):
            d = c.f0 - wf
            if abs(d) > 2: l8.append(f"{c.id}: shown at f{c.f0}, first word '{ws[0][2]}' at f{wf:.1f} ({d:+.1f} f)")
        else:      # first word under a cutaway / chest element / hide window: the caption must resume on the first free frame
            g = int(math.floor(wf))
            while g < c.f1 and not cx.cap_allowed(g): g += 1
            l8r += 1
            if not 0 <= c.f0 - g <= 2: l8.append(f"{c.id}: resumes at f{c.f0}, first free frame f{g} ({c.f0 - g:+d} f)")
    gate("PLAT-04", not l4, f"{len(caps)} caption events: max {max(max(len(wrap(c)) for c in caps), max([m['lines'] for m in meas.values()] or [0]))} lines; {len(l4w)} two-line events (warn > 1)",
         "\n".join(l4 + ([f"two-line (warn): {', '.join(l4w[:12])}"] if l4w else [])), status=None if l4 else ("WARN" if l4w else "PASS"))
    gate("PLAT-05", not l5, f"caption lines <= 32 chars and <= 950 px: {len(l5)} over", "\n".join(l5[:12]), status=None if not l5 else "WARN")
    gate("PLAT-06", not l6, f"reading speed: worst {max(len(c.text or '') / max(len(c.f) / FPS, 1e-6) for c in caps):.0f} cps (<= 20); {len(l6)} events over",
         "\n".join(l6[:12]), status=None if not l6 else "WARN")
    gate("PLAT-07", not l7, f"{len(l7)} of {len(caps)} events shorter than 0.83 s on screen", "\n".join(l7[:12]), status=None if not l7 else "WARN")
    gate("PLAT-08", not l8, f"caption onset vs first word <= 2 f: {len(caps) - len(l8)}/{len(caps)} on time ({l8r} resume after a cutaway / chest / hide)", "\n".join(l8[:12]))
    one = sum(n == 1 for n in nw) / len(nw)
    if cx.CS.get("style") == "one_word": gate("PLAT-09", True, f"style one_word: {np.mean(nw):.1f} words per event by design"); nw = [3]
    else: gate("PLAT-09", np.mean(nw) >= 3 and one <= .10, f"mean {np.mean(nw):.1f} words per event; {one:.0%} one-word events", status=None if (np.mean(nw) >= 3 and one <= .10) else "WARN")
    gate("GFX-16", not g16, f"{len(g16)} widows in multi-line captions", "\n".join(g16), status=None if not g16 else "WARN")
    # PLAT-10 style (BLOCKING) + cap height (CALIBRATE)
    fonts_used = sorted(set(str(c.font) for c in caps)); bad = []
    for c in caps:
        t = (c.text or "").strip(); letters = [ch for ch in t if ch.isalpha()]
        if cx.CS.get("case", "sentence") in ("sentence", "lower", "as_spoken") and letters and sum(ch.isupper() for ch in letters) / len(letters) > .6 and len(letters) > 3: bad.append(f"{c.id}: ALL CAPS '{t}' (style case {cx.CS.get('case', 'sentence')})")
    for c in caps:
        if cx.CS.get("case", "sentence") != "sentence": break          # sentence case: an event whose first word starts a sentence (previous spoken word ends . ? !) is capitalised
        j = cx.cap_word_index(c)
        starts = j == 0 or (j is not None and cx.words[j - 1][2].rstrip().endswith((".", "?", "!")))
        ch0 = next((ch for ch in (c.text or "") if ch.isalpha()), "A")
        if starts and ch0.islower(): bad.append(f"{c.id}: sentence starts lower-case '{c.text}'")
    if len(fonts_used) > 1: bad.append(f"fonts: {fonts_used}")
    ms = list(meas.values())
    asc = re.compile(r"[A-Zbdfhklt0-9]")
    for m in ms: m["cap_ok"] = bool(asc.search(m.get("shown") or ""))
    from .. import style as STY
    want = np.array(STY.rgb(cx.CS.get("color", "#FFFFFF")), float); hi = cx.CS.get("highlight_color")
    want_hi = np.array(STY.rgb((cx.S.get("colors") or {}).get(hi, hi) if hi else cx.CS.get("color", "#FFFFFF")), float)
    off = lambda f: min(np.abs(np.array(f[:3], float) - want).max(), np.abs(np.array(f[:3], float) - want_hi).max()) > 40
    nonwhite = [f"{m['id']} fill {[round(v) for v in m['fill']]} vs style {cx.CS.get('color', '#FFFFFF')}" for m in ms if off(m["fill"])]
    noshadow = [f"{m['id']} shadow {m['shadow']:+.1f}" for m in ms if cx.CS.get("shadow", True) and m["shadow"] is not None and m["shadow"] < 2]
    plate = [f"{m['id']} layer extends {m['margin']} px past the ink" for m in ms if cx.CS.get("style") != "box" and m["margin"] > 26 * max(1., U_)]   # px at a 1080 short side (the caption shadow scales by U)
    bad += nonwhite + noshadow + plate
    caph = [m["cap_h"] for m in ms if m["cap_ok"]]
    if cx._results.get("cap_unmeasured"): bad_note = f" ({len(cx._results['cap_unmeasured'])} events only on transition frames: not measured)"
    else: bad_note = ""
    summ = (f"{', '.join(fonts_used)}{bad_note}; fill matches style ({len(ms) - len(nonwhite)}/{len(ms)} measured); shadow {len(ms) - len(noshadow)}/{len(ms)}; plate per style; "
            f"cap/ascender height {np.median(caph) if caph else float('nan'):.0f} px (>= {40 * U_:.0f} CALIBRATE)")
    if bad: gate("PLAT-10", False, summ, "\n".join(bad[:12]))
    else: gate("PLAT-10", True, summ, f"cap height {np.median(caph):.0f} px < {40 * U_:.0f} px (CALIBRATE)" if caph and np.median(caph) < 40 * U_ else "",
               status="WARN" if caph and np.median(caph) < 40 * U_ else "PASS")
    cx._results["cap_style"] = (fonts_used, [m["x_h"] for m in ms if len(m.get("shown", "")) >= 6], [m["fill"] for m in ms])


# ======================================================================== gates: motion
def entry_profile(bb):
    """analyse a bbox track from its first frame: (kind, steps along travel, travel px, window len) or None.
    kind: rigid (translate / uniform scale, judged) | content (non-rigid: typing, wipes, builds; not judged) | still"""
    if len(bb) < 3: return None
    d = np.diff(bb, axis=0); still = np.abs(d).max(1) <= 1; end = len(d)
    for k in range(len(d) - 1):
        if still[k] and still[k + 1]: end = k; break
    if end == 0: return ("still", None, 0, 0)
    win = d[:end]; tot = (bb[end] - bb[0]); travel = float(np.abs(tot).max())
    if travel < 6: return ("still", None, travel, end)
    for st, b in zip(win, bb[:end]):
        if np.abs(st).max() <= 1: continue
        dx0, dy0, dx1, dy1 = st; w, h = max(1, b[2] - b[0]), max(1, b[3] - b[1])
        trans = abs(dx0 - dx1) <= 1.5 and abs(dy0 - dy1) <= 1.5
        scale = abs((dx1 - dx0) * h - (dy1 - dy0) * w) <= 1.5 * (w + h)
        if not (trans or scale): return ("content", None, travel, end)
    u = tot / (np.linalg.norm(tot) + 1e-9)
    return ("rigid", win @ u, travel, end)

def gates_motion(cx, gate):
    FPS = cx.FPS; mov = [i for i in cx.inst if i.role != "caption"]
    if not mov:
        for g in ("MOT-01", "MOT-02", "MOT-03", "MOT-04", "MOT-05", "MOT-07", "MOT-12", "MOT-14"): gate(g, False, "no graphic elements in the element log", status="WARN")
        return
    # MOT-12 origin
    o_bad, o_ex, o_ok = [], [], 0
    for i in mov:
        if i.id.startswith("broll."): continue          # a B-roll shot is footage: it enters on a cut (or its transition), not as a graphic
        tr = cx.in_trans(i.f0)
        if tr: o_ex.append(f"{i.key}@f{i.f0} ({tr[1]})"); continue
        r = min(len(i.bb) - 1, 14); b0, br = i.bb[0], i.bb[r]
        w0, h0, wr, hr = b0[2] - b0[0], b0[3] - b0[1], max(1, br[2] - br[0]), max(1, br[3] - br[1])
        off = float(np.abs(b0 - br).max()); sc = min(w0 / wr, h0 / hr)
        if i.al[0] < .5 or sc < .5 or off > 2: o_ok += 1
        else: o_bad.append(f"{i.key} f{i.f0} ({i.f0 / FPS:.2f} s): alpha {i.al[0]:.2f}, scale {sc:.2f}, offset {off:.0f} px vs f{i.f[r]} - appears fully formed")
    gate("MOT-12", not o_bad, f"{o_ok} of {o_ok + len(o_bad)} element entries start unformed; {len(o_bad)} pop in fully formed ({len(o_ex)} entries under a whip/glitch exempt; captions exempt)",
         "\n".join(o_bad[:14]) + (f"\nexempt (under transition): {', '.join(o_ex[:10])}" if o_ex else ""))
    # MOT-07 start quantisation
    q_bad, q_n = [], 0
    for i in mov:
        if i.t_key is None or i.decor: continue
        q_n += 1; ph = i.t_key * FPS - round(i.t_key * FPS)
        if abs(ph) > .01: q_bad.append(f"{i.key}: start {i.t_key:.3f} s = frame {i.t_key * FPS:.2f}")
    gate("MOT-07", not q_bad, f"{q_n - len(q_bad)} of {q_n} keyed element starts on a whole frame (|phase| <= 0.01)", "\n".join(q_bad[:12]) + (f"\n... {len(q_bad) - 12} more" if len(q_bad) > 12 else ""))
    # MOT-03 shake on graphics: second difference of the bbox centre over the hold (after the entry settles, before the exit
    # starts; frames whose bbox size changes are content changes and skipped). Integer bboxes add up to 2 px/f^2 of rounding,
    # so the 0.5 px/f^2 limit is tested as 2.5. (A-roll punch-in shake is enforced by the engine's +-6 f face smoothing.)
    shaky, n3 = {}, 0
    for i in mov:
        if i.decor or len(i.bb) < 8: continue
        full = np.where(i.al >= .95 * i.al.max())[0]        # hold = fully faded in, 6 f after the entry and 6 f before the exit
        if not len(full): continue
        k0, k1 = int(full[0]) + 6, int(full[-1]) - 6
        if k1 - k0 < 6: continue
        n3 += 1; bb = i.bb[k0:k1 + 1]; c = np.stack([(bb[:, 0] + bb[:, 2]) / 2, (bb[:, 1] + bb[:, 3]) / 2], 1)
        sz = np.stack([bb[:, 2] - bb[:, 0], bb[:, 3] - bb[:, 1]], 1)
        a = np.abs(c[2:] - 2 * c[1:-1] + c[:-2]).max(1); same = (np.abs(np.diff(sz, axis=0)) <= 1).all(1); same = same[1:] & same[:-1]
        a = a[same]
        if (a > 2.5).sum() >= 2: shaky[i.key] = (float(a.max()), int((a > 2.5).sum()), len(a), int(i.f[k0]), int(i.f[k1]))
    gate("MOT-03", not shaky, f"{n3} graphic holds checked: {len(shaky)} shake (|centre second difference| > 2.5 px/f^2 on >= 2 frames)",
         "\n".join(f"{k}: up to {v[0]:.0f} px/f^2 on {v[1]} of {v[2]} hold frames (f{v[3]}-{v[4]})" for k, v in shaky.items()))
    # MOT-01 / 02 / 04 / 05 from the bbox track (entries and exits); shaking elements are left to MOT-03
    e1, e2, e4, e5, n_r, n_c = [], [], [], [], 0, 0
    for i in mov:
        if i.decor or i.key in shaky: continue
        for tag, bb in (("entry", i.bb), ("exit", i.bb[::-1])):
            p = entry_profile(bb)
            if not p or p[0] == "still": continue
            if p[0] == "content": n_c += 1; continue
            n_r += 1; v = p[1]; tol = 1.5
            fwd = [k for k in range(len(v)) if v[k] > 1]
            acc = [k for k in range(len(v) - 1) if v[k] > 1 and v[k + 1] > v[k] + tol]
            if acc: e1.append(f"{i.key} {tag}: steps {np.round(v, 1).tolist()} ({'accelerates' if tag == 'entry' else 'decelerates'} at step {acc[0] + 1})")
            if tag == "entry" and len(fwd) >= 3:
                r = v[fwd[0]] / max(1e-6, np.median(v[fwd]))
                if r < 1.5: e2.append(f"{i.key}: first step {v[fwd[0]]:.1f} px / median {np.median(v[fwd]):.1f} = {r:.2f}")
            if tag == "entry":
                pos = np.concatenate([[0], np.cumsum(v)]); fin = pos[-1]; over = (pos.max() - fin) / max(abs(fin), 1e-6)
                if over > .10: e4.append(f"{i.key}: overshoot {over:.0%} of {abs(fin):.0f} px travel")
                pk = int(np.argmax(pos))
                if over > .01:
                    tolp = max(1.0, .005 * max(1, i.bb[-1][2] - i.bb[-1][0])); st = next((k for k in range(pk, len(pos)) if abs(pos[k] - fin) <= tolp), len(pos))
                    if st - pk > 3: e5.append(f"{i.key}: {st - pk} f from overshoot peak to rest")
    gate("MOT-01", not e1, f"{n_r} rigid entries/exits checked (decelerate in, accelerate out; tolerance 0.5 px + 1 px bbox rounding); {n_c} content builds not judged", "\n".join(e1[:12]))
    gate("MOT-02", not e2, f"{len(e2)} entries start with a linear first step (< 1.5x median)", "\n".join(e2[:10]), status=None if not e2 else "WARN")
    gate("MOT-04", not e4, f"{len(e4)} entries overshoot > 10% of travel", "\n".join(e4[:10]), status=None if not e4 else "WARN")
    gate("MOT-05", not e5, f"{len(e5)} entries take > 3 f to settle from the overshoot peak", "\n".join(e5[:10]), status=None if not e5 else "WARN")
    # MOT-14 raster scale (max on-screen size x supersample / source px). Icon size is bounded by its element bbox (upper bound).
    from PIL import Image
    r_bad, r_ok, unk = [], [], []
    icons = os.path.join(REPO, "assets", "icons"); MAT = {"post": "event", "link": "link", "chat": "chat", "star": "star", "search": "search", "pin": "place", "phone": "call"}
    shots = {}
    try:
        from .. import spines as SP
        shots = {f"broll.{x['id']}": x for x in SP.shots(cx.E, cx.FPS, cx.S, cx.pr)}
    except (SystemExit, KeyError, ValueError, TypeError): pass
    b_warn, b_fail = [], []
    for i in mov:
        if not i.asset: continue
        if i.id in shots:    # a B-roll shot: the scale its framing applies to source pixels (like FRAME-11: soft above 1.0, FAIL above 1.5)
            sh = shots[i.id]
            try:
                from .. import assets as AS, spines as SP
                pv = AS.probe(SP._path(cx.pr, sh["ref"]))
                kb = (sh.get("kenburns") or {}).get("zoom", 1.0); zmax = max(kb) if isinstance(kb, (list, tuple)) else float(kb)
                sc = (min if sh["framing"] == "fit" else max)(W / pv["w"], H / pv["h"]) * zmax
            except Exception as e: unk.append(f"{i.key}: {e}"); continue
            msg = f"{i.key}: {os.path.basename(str(i.asset))} {pv['w']}x{pv['h']} {sh['framing']} x{zmax:.2f} on {W}x{H} = {sc:.2f}x source px"
            (b_fail if sc > 1.5 else b_warn if sc > 1.0 else r_ok).append(msg); continue
        a = str(i.asset); src, ss = None, 1
        for base in (cx.pr.root, REPO):
            if os.path.exists(os.path.join(base, a)) and os.path.isfile(os.path.join(base, a)): src = os.path.join(base, a); break
        if src is None:
            nm = MAT.get(os.path.splitext(a)[0], os.path.splitext(a)[0]); q = os.path.join(icons, nm + "_512.png"); ss = 2
            if os.path.exists(q): src = q
        if src is None: unk.append(f"{i.key}: {a}"); continue
        try: sw, sh = Image.open(src).size
        except Exception:                       # video / sequence asset: size from the asset probe
            pv = {}
            try:
                from .. import assets as AS; pv = (AS.record(cx.pr, a) or {}).get("probe") or {}
            except Exception: pass
            if not pv.get("w"):
                try:
                    import av
                    with av.open(src) as c: st = c.streams.video[0]; pv = {"w": st.width, "h": st.height}
                except Exception: unk.append(f"{i.key}: {a}"); continue
            sw, sh = pv["w"], pv["h"]
        bw = float((i.bb[:, 2] - i.bb[:, 0]).max() + 1); bh = float((i.bb[:, 3] - i.bb[:, 1]).max() + 1)
        ratio = (min(bw, bh) * ss / min(sw, sh)) if ss == 2 else (bw * ss / sw)
        (r_bad if ratio > 1.0 else r_ok).append(f"{i.key}: {os.path.basename(src)} {sw}x{sh} shown <= {bw:.0f}x{bh:.0f} px x{ss} = {ratio:.2f}{' (bbox bound)' if ss == 2 else ''}")
    worst = max([float(x.rsplit('= ', 1)[1].split()[0].rstrip("x")) for x in r_ok + r_bad + b_warn + b_fail] or [0])
    bad = r_bad + b_fail
    gate("MOT-14", not bad, f"{len(r_ok)} raster uses <= 1.0x source; {len(b_warn)} B-roll shots soft (1.0-1.5x); worst {worst:.2f}",
         "\n".join(bad + b_warn + ([f"unresolved assets: {', '.join(unk)}"] if unk else [])), status=None if bad else ("WARN" if (unk or b_warn) else "PASS"))


# ======================================================================== gates: graphics
def gates_graphics(cx, gate):
    FPS = cx.FPS; ins = cx.inst
    # GFX-05 font count + classes
    CLASS = {"poppins": "sans", "cormorantgaramond": "serif", "marcellus": "serif display", "inter": "sans", "playfair": "serif"}
    fam = sorted(set(re.split(r"[-_ ]", str(i.font))[0] for i in ins if i.font))
    cls = [CLASS.get(f.lower(), "?") for f in fam]; nolog = sorted(set(i.cls for i in ins if i.is_text and not i.font))
    ok5 = len(fam) <= 2 and len(set(cls)) == len(cls)
    gate("GFX-05", ok5, f"{len(fam)} font families logged: {', '.join(f'{f} ({c})' for f, c in zip(fam, cls))}",
         ("" if ok5 else "more than 2 families or two of one class\n") + (f"text elements that log no font (renderer gap, assumed Poppins via gfx.font): {', '.join(nolog)}" if nolog else ""))
    # GFX-17 typesetting hygiene: logged text + every string the templates draw from edit.yaml
    texts = [(i.key, i.text) for i in ins if i.text]
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("template", "icon", "logo", "state", "in", "out", "id"): continue
                yield from walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for j, v in enumerate(o): yield from walk(v, f"{path}[{j}]")
        elif isinstance(o, str) and not re.search(r"\.(png|jpe?g|svg|webp|mp4|wav|mp3)$", o, re.I): yield (path, o)
    for sect in ("cutaways", "chest", "roto"):
        for c in cx.E.get(sect, []) or []: texts += list(walk(c.get("params", {}), f"{sect}:{c.get('id', c.get('segment'))}"))
    if cx.E.get("end_card"): texts += list(walk(cx.E["end_card"].get("params", {}), "end_card"))
    hy = sorted(set(f"{k}: {t!r}" for k, t in texts if "  " in t or t != t.strip() or "\t" in t))
    gate("GFX-17", not hy, f"{len(set(t for _, t in texts))} strings checked for double / leading / trailing spaces (alignment never justified by the renderer)", "\n".join(hy[:12]))
    # GFX-24 real assets: client name / wordmark rendered from an asset or set in a real display face, never plain mono text
    wm = [i for i in ins if any(k in i.id for k in ("wordmark", "client_name")) and not i.decor and ".sub" not in i.id]
    lg = [i for i in ins if (i.text or "").lower() == "logo" or "logo" in i.id]
    bad = [f"{i.key}: plain text, no asset, font {i.font}" for i in wm if not i.asset and (not i.font or re.search(r"mono|courier|menlo|consol", str(i.font), re.I))]
    bad += [f"{i.key}: logo asset missing on disk ({i.asset})" for i in lg if not i.asset or not any(os.path.isfile(os.path.join(b, str(i.asset))) for b in (cx.pr.root, REPO))]
    gate("GFX-24", not bad, f"{len(wm)} client wordmark element(s) ({', '.join(sorted(set(f'{i.id} in {i.font or i.asset}' for i in wm))) or 'none'}); {len(lg)} logo element(s) from asset files", "\n".join(bad))
    # GFX-26 clutter on A-roll: simultaneous non-caption overlays (one template instance = one overlay)
    worst, where = 0, []
    for f in range(cx.A):
        if not cx.is_aroll(f): continue
        groups = set((e["role"], e["id"].split(".")[1] if "." in e["id"] else e["id"]) for e in cx.by_f.get(f, []) if e["role"] in ("roto", "chest") and not any(d in e["id"] for d in DECOR))
        tmpl = set()
        for role, g in groups: tmpl.add(role if role == "roto" else ("chest", "logo" if g in ("logo", "tagline") else g))
        if len(tmpl) > 1: where.append(f)
        worst = max(worst, len(tmpl))
    gate("GFX-26", not where, f"max {worst} non-caption overlay(s) on an A-roll frame", f"{len(where)} frames, first f{where[0]}" if where else "", status=None if not where else "WARN")
    # GFX-08 alignment axis: near-miss left edges / centres (2-12 px) between static elements on the same frame
    mis = collections.defaultdict(list); static = {}
    for i in ins:
        if i.role == "caption" or i.decor: continue
        for j in range(1, len(i.f) - 1):
            if np.abs(i.bb[j] - i.bb[j - 1]).max() <= 1 and np.abs(i.bb[j + 1] - i.bb[j]).max() <= 1 and i.al[j] >= .9 and not cx.in_trans(int(i.f[j])):
                static.setdefault(int(i.f[j]), []).append((i, i.bb[j]))
    for f in sorted(static)[::3]:
        L = static[f]
        for a in range(len(L)):
            for b in range(a + 1, len(L)):
                (ia, ba), (ib, bb) = L[a], L[b]
                if ia.role != ib.role: continue
                dl = abs(ba[0] - bb[0]); dc = abs((ba[0] + ba[2]) / 2 - (bb[0] + bb[2]) / 2)
                if min(dl, dc) <= 2: continue          # aligned on one axis: a near miss on the other is a coincidence
                for kind, dv in (("left", dl), ("centre", dc)):
                    if 2 * max(1, U_) < dv <= 12 * U_: mis[(ia.key, ib.key, kind)].append(dv)     # px at a 1080 short side
    pairs = [f"{a} / {b}: {kind} {'edges' if kind == 'left' else 'axes'} {np.median(v):.0f} px apart ({len(v)} frames)" for (a, b, kind), v in mis.items()]
    gate("GFX-08", not pairs, f"{len(static)} frames with static graphics; {len(pairs)} near-aligned pairs ({2 * max(1, U_):.0f}-{12 * U_:.0f} px off one axis)", "\n".join(sorted(pairs)[:12]))
    # GFX-15 text contrast (WCAG, worst case over the shot) on the delivered frames
    cm = cx._results["contrast"]; per = collections.defaultdict(list)
    for key, f, res in cm:
        if res: per[key].append((f, res))
    low, n = [], 0
    kcls = {i.key: i.cls for i in ins}; clsh = collections.defaultdict(list)
    for key, L in per.items(): clsh[kcls[key]] += [h for _, res in L for _, h in res]
    for key, L in per.items():      # type size per element class (all captions share one size): p90 glyph height ~ ascender ~0.74 em
        hs = [h for _, res in L for _, h in res]; ch = clsh[kcls[key]]; fpx = np.percentile(ch, 90) / .74 if ch else 0; need = 3.0 if fpx >= 48 * U_ else 4.5
        worst_f, worst_c = None, 99
        for f, res in L:
            c = float(np.percentile([r for r, _ in res], 10))
            if c < worst_c: worst_c, worst_f = c, f
        n += 1
        cx._results["glyph_h"].append((key, float(np.median(hs)) if hs else 0))
        if worst_c < need: low.append(f"{key}: {worst_c:.2f}:1 at f{worst_f} (est. {fpx:.0f} px type, needs {need}:1)")
    allc = [float(np.percentile([r for r, _ in res], 10)) for _, _, res in cm if res]
    gate("GFX-15", not low, f"{n} text elements on {len(set(f for _, f, _ in cm))} decoded frames; worst {min(allc) if allc else float('nan'):.2f}:1", "\n".join(sorted(low)[:12]))
    # GFX-20 style repetition: one style per role. Captions measured (font, cap height, fill); repeated classes by font + glyph size
    st = cx._results.get("cap_style"); out = []
    if st:
        fonts_used, caph, fills = st
        hs = sorted(caph); cl = 1 + sum(1 for a, b in zip(hs[:-1], hs[1:]) if b - a > 3)          # x-heights; 3 px = AA + rounding
        fc = len(set("white" if min(f) >= 215 else tuple(int(v) // 24 for v in f) for f in fills))
        if len(fonts_used) > 1 or cl > 1 or fc > 1: out.append(f"captions: {len(fonts_used)} fonts, {cl} x-height clusters {hs}, {fc} fills")
    gh = collections.defaultdict(list)
    for key, h in cx._results["glyph_h"]:
        i = next(x for x in ins if x.key == key)
        if i.role != "caption" and h: gh[i.cls].append((key, h))
    for k, L in gh.items():
        insts = [x for x in ins if x.cls == k]
        fs = set(x.font for x in insts)
        if len(fs) > 1: out.append(f"{k}: fonts {fs}")
        if len(L) > 1 and max(h for _, h in L) / min(h for _, h in L) > 1.15 and len(set(x.id for x in insts)) == 1:
            out.append(f"{k}: glyph heights {', '.join(f'{a} {h:.0f}px' for a, h in L)}")
    gate("GFX-20", not out, f"captions one style ({'; '.join(st[0]) if st else '?'}); {len(gh)} repeated element classes compared by font and glyph size", "\n".join(out))


# ======================================================================== gates: frame + colour (from the A-roll pass)
def gates_frame_colour(cx, gate):
    R = sorted(cx._results["aroll"], key=lambda r: r["f"])
    if not R:
        for g in ("FRAME-02", "FRAME-03", "FRAME-04", "FRAME-05", "FRAME-06", "FRAME-10", "COL-03", "COL-04", "COL-05", "COL-06", "COL-07", "COL-08", "COL-09", "COL-10"):
            gate(g, False, "no A-roll frames measured (matte / faces missing?)", status="WARN")
        return
    # FRAME-02
    fl = [r for r in R if r["bottom"] < .05]; cut = [r for r in R if r["hcut"] > 200 or r["vcut"] > 200]; top = [r for r in R if r["top"] > 0 and not r["snap"]]
    det = [f"f{r['f']} {r['sid']}: matte reaches the bottom edge on {r['bottom']:.0%} of it" for r in fl] + [f"f{r['f']} {r['sid']}: straight in-frame matte edge {max(r['hcut'], r['vcut'])} px" for r in cut]
    det += [f"head touches the top edge (warn, FRAME-05): {', '.join(sorted(set(r['sid'] for r in top)))}"] if top else []
    gate("FRAME-02", not fl and not cut, f"{len(R)} A-roll frames: body exits the bottom edge in {len(R) - len(fl)}; {len(cut)} straight matte cuts; top-edge contact in {len(top)} (outside the snap)",
         "\n".join(det[:12]), status=None if (fl or cut) else ("WARN" if top else "PASS"))
    # FRAME-03 halo: ring luma <= wall luma (worst 30-degree sector); 1 code value allowed for encode noise
    hv = [(r["halo"][0], r) for r in R if r.get("halo")]
    bad = sorted([x for x in hv if x[0] > 1.0], key=lambda x: -x[0])
    by = collections.OrderedDict()
    for ex, r in bad: by.setdefault(r["sid"], (ex, r))
    gate("FRAME-03", not bad, f"edge ring 3-7 px vs wall 20-40 px out, {len(hv)} frames: worst ring - wall {max(x[0] for x in hv) if hv else float('nan'):+.1f} Y",
         "\n".join(f"{sid} f{r['f']}: ring {r['halo'][2]:.0f} vs wall {r['halo'][3]:.0f} ({ex:+.1f}) at {r['halo'][1]}" for sid, (ex, r) in list(by.items())[:12]))
    # FRAME-04 / 05 / 06 (CALIBRATE)
    def per_seg(key):
        d = collections.OrderedDict()
        for r in R:
            if r.get(key) is not None and not r["snap"]: d.setdefault(r["sid"], []).append(r[key])
        return {k: float(np.median(v)) for k, v in d.items()}
    ey, ex_, hr = per_seg("eye_y"), per_seg("eye_x"), per_seg("headroom")
    o4 = [f"{k}: eye line y {v:.0f}" for k, v in ey.items() if not 576 <= v <= 768]
    gate("FRAME-04", not o4, f"eye line y {min(ey.values()):.0f}-{max(ey.values()):.0f} px (576-768, CALIBRATE)" if ey else "no landmarks", "\n".join(o4), status="PASS" if not o4 and ey else "WARN")
    o5 = [f"{k}: headroom {v:.0f} px" for k, v in hr.items() if not 77 <= v <= 230]
    gate("FRAME-05", not o5, f"headroom {min(hr.values()):.0f}-{max(hr.values()):.0f} px (77-230, CALIBRATE; snap excluded)" if hr else "no matte", "\n".join(o5), status="PASS" if not o5 and hr else "WARN")
    o6 = [f"{k}: eye midpoint x {v:.0f}" for k, v in ex_.items() if not 486 <= v <= 594]
    gate("FRAME-06", not o6, f"eye midpoint x {min(ex_.values()):.0f}-{max(ex_.values()):.0f} px (486-594, CALIBRATE)" if ex_ else "no landmarks", "\n".join(o6), status="PASS" if not o6 and ex_ else "WARN")
    # FRAME-10 no roll / flip
    fr = [r for r in R if "corr" in r]
    rot = [r for r in fr if "rot" in r and r["inliers"] >= 40 and abs(r["scale"] / r["z"] - 1) < .1]   # a fit must also recover the known zoom
    b10 = [f"{r['sid']} f{r['f']}: plate corr {r['corr']:.2f} <= mirrored {r['corr_flip']:.2f}" for r in fr if r["corr"] <= r["corr_flip"]]
    b10 += [f"{r['sid']} f{r['f']}: rotation {r['rot']:+.2f} deg" for r in rot if abs(r["rot"]) > .3]
    gate("FRAME-10", not b10 and bool(fr), f"{len(fr)} shots: plate corr {min(r['corr'] for r in fr):.2f}-{max(r['corr'] for r in fr):.2f} vs mirrored <= {max(r['corr_flip'] for r in fr):.2f}; "
         f"rotation {max(abs(r['rot']) for r in rot) if rot else float('nan'):.2f} deg max ({len(rot)} ORB fits)" if fr else "no plate frames", "\n".join(b10), status=None if fr else "WARN")
    # colour per shot
    segs = collections.OrderedDict()
    for r in R: segs.setdefault(r["sid"], []).append(r)
    S = collections.OrderedDict()
    for sid, L in segs.items():
        sk = [r for r in L if "skin_hue" in r]
        if not sk: continue
        med = lambda k, LL=sk: float(np.median([r[k] for r in LL]))
        S[sid] = dict(hue=med("skin_hue"), chroma=med("skin_chroma"), Y=med("skin_Y"), lab=np.median([r["skin_lab"] for r in sk], 0),
                      wall=np.median([r["wall_lab"] for r in L if "wall_lab" in r], 0) if any("wall_lab" in r for r in L) else None,
                      Ym=float(np.mean([r["Y_mean"] for r in L])), Cm=float(np.mean([r["C_mean"] for r in L])), first=L[0], last=L[-1],
                      f0=L[0]["f"], f1=L[-1]["f"])
    if not S:
        for g in ("COL-03", "COL-04", "COL-05", "COL-06", "COL-07"): gate(g, False, "no skin patches measured", status="WARN")
    else:
        hues = {k: v["hue"] for k, v in S.items()}
        o3 = [f"{k}: {v:.1f} deg" for k, v in hues.items() if abs(v - 123) > 5]
        gate("COL-03", not o3, f"skin hue {min(hues.values()):.1f}-{max(hues.values()):.1f} deg (123 +-8, warn +-5)", "\n".join(o3), status="PASS" if not o3 else "WARN")
        ks = list(S); dh = [abs(S[b]["hue"] - S[a]["hue"]) for a, b in zip(ks[:-1], ks[1:])]; spread = max(hues.values()) - min(hues.values())
        gate("COL-04", spread <= 5 and max(dh or [0]) <= 3, f"skin hue spread {spread:.1f} deg (<= 5), max consecutive {max(dh or [0]):.1f} deg (<= 3) CALIBRATE",
             status="PASS" if spread <= 5 and max(dh or [0]) <= 3 else "WARN")
        ch = {k: v["chroma"] for k, v in S.items()}; ref = float(np.median(list(ch.values())))
        o5c = [f"{k}: chroma {v:.1f}" for k, v in ch.items() if not (18 <= v <= 40 and abs(v / ref - 1) <= .2)]
        gate("COL-05", not o5c, f"skin chroma {min(ch.values()):.1f}-{max(ch.values()):.1f} (18-40, +-20% of median {ref:.1f}) CALIBRATE", "\n".join(o5c), status="PASS" if not o5c else "WARN")
        # COL-06 / COL-07 between consecutive visible A-roll shots (direct cut vs across a cutaway)
        b6, b7, lines6 = [], [], []; worst6 = 0
        for a, b in zip(ks[:-1], ks[1:]):
            A_, B_ = S[a], S[b]; direct = A_["last"]["f"] + 1 == B_["first"]["f"] or not any(c for c in cx.cuts if A_["f1"] / cx.FPS <= c["start"] < B_["f0"] / cx.FPS)
            direct = direct and not any(not cx.is_aroll(f) for f in range(A_["f1"], B_["f0"]))
            lim = 3.0 if direct else 5.0
            dE = float(np.linalg.norm(A_["lab"] - B_["lab"]))
            dEc = float(np.linalg.norm(np.array(A_["last"].get("skin_lab", A_["lab"])) - np.array(B_["first"].get("skin_lab", B_["lab"]))))
            dW = float(np.linalg.norm(A_["wall"] - B_["wall"])) if A_["wall"] is not None and B_["wall"] is not None else float("nan")
            dWc = float(np.linalg.norm(np.array(A_["last"]["wall_lab"]) - np.array(B_["first"]["wall_lab"]))) if "wall_lab" in A_["last"] and "wall_lab" in B_["first"] else float("nan")
            sk_, wl_ = max(dE, dEc), np.nanmax([dW, dWc]) if not (math.isnan(dW) and math.isnan(dWc)) else float("nan")
            dY, dS = abs(A_["Ym"] - B_["Ym"]), abs(A_["Cm"] / max(B_["Cm"], 1e-6) - 1)
            worst6 = max(worst6, sk_, 0 if math.isnan(wl_) else wl_)
            msg = f"{a} -> {b} ({'direct' if direct else 'across cutaway'}): skin dE {sk_:.2f} (shot medians {dE:.2f}, cut frames f{A_['last']['f']}/f{B_['first']['f']} {dEc:.2f}), wall dE {wl_:.2f}" + (f", frame dY {dY:.1f}, dSat {dS:.0%}" if direct else "")
            lines6.append(msg)
            # frame dY / dSat (9.5 Q25) are reported, not judged: whole-frame means move with the punch-in framing, not the grade
            if sk_ > lim or (not math.isnan(wl_) and wl_ > lim) or max(sk_, 0 if math.isnan(wl_) else wl_) > 7: b6.append(msg)
            r7 = B_["Y"] / max(A_["Y"], 1e-6) - 1
            if abs(r7) > (.06 if direct else .10): b7.append(f"{a} -> {b} ({'direct' if direct else 'across cutaway'}): skin Y {A_['Y']:.0f} -> {B_['Y']:.0f} ({r7:+.1%})")
        gate("COL-06", not b6, f"{len(ks) - 1} shot pairs: worst skin/wall dE {worst6:.2f} (direct <= 3, across cutaway <= 5, hard 7)", "\n".join(b6[:12]))
        gate("COL-07", not b7, f"skin-core Y per shot {min(v['Y'] for v in S.values()):.0f}-{max(v['Y'] for v in S.values()):.0f} (+-6% direct, +-10% across cutaways)", "\n".join(b7[:12]))
    # COL-08 / 09 / 10 (CALIBRATE) on A-roll frames, graphics masked
    p01, p999 = [r["Y_p01"] for r in R], [r["Y_p999"] for r in R]; span = [r["Y_p99"] - r["Y_p1"] for r in R]
    ok8 = 16 <= min(p01) and max(p01) <= 24 and max(p999) <= 235
    gate("COL-08", ok8, f"A-roll black p0.1 {min(p01):.0f}-{max(p01):.0f} (16-24), white p99.9 <= {max(p999):.0f} (235) CALIBRATE", status="PASS" if ok8 else "WARN")
    wy = collections.defaultdict(list)
    for r in R:
        if "wall_Y" in r and "skin_Y" in r: wy[r["sid"]].append(r["skin_Y"] / max(r["wall_Y"], 1e-6))
    ratios = [float(np.median(v)) for v in wy.values()]
    ok9 = min(span) >= 130 and ratios and 2.0 <= min(ratios) and max(ratios) <= 3.5
    gate("COL-09", ok9, f"luma span p99-p1 {min(span):.0f}-{max(span):.0f} (>= 130); face/wall {min(ratios or [0]):.2f}-{max(ratios or [0]):.2f} (2.0-3.5) CALIBRATE", status="PASS" if ok9 else "WARN")
    c99 = [r["C_p99"] for r in R]
    gate("COL-10", max(c99) <= 45, f"A-roll chroma p99 max {max(c99):.1f} (<= 45, graphics masked) CALIBRATE", status="PASS" if max(c99) <= 45 else "WARN")


def gate_col12(cx, gate):
    from ..look import grade
    ramp = np.linspace(0, 1, 513, dtype=np.float32); bad = []
    for alpha in (255, 0):
        for name, ch in (("grey", None), ("R", 0), ("G", 1), ("B", 2)):
            outs = []
            for v in ramp:
                im = np.zeros((9, 9, 3), np.float32)
                if ch is None: im[:] = v
                else: im[..., ch] = v
                outs.append(grade(im, np.full((9, 9), alpha, np.uint8), (4, 4))[4, 4])
            o = np.array(outs); d = np.diff(o, axis=0)
            if (d < -1e-6).any(): k = int(np.argwhere(d < -1e-6)[0][0]); bad.append(f"{name} ramp, alpha {alpha}: output falls at input {ramp[k]:.3f} ({o[k].round(4).tolist()} -> {o[k + 1].round(4).tolist()})")
    gate("COL-12", not bad, "look.grade() grey and R/G/B ramps (subject and background) are non-decreasing on every channel", "\n".join(bad[:8]))


# ======================================================================== gates: timeline / retention
def gates_timeline(cx, gate):
    FPS = cx.FPS; bounds = [s["t0"] for s in cx.segs] + [cx.T_END]
    on = lambda t: min(abs(t - b) for b in bounds) * FPS
    bad, notes = [], []
    pts = [(c["start"], f"{c['id']} in") for c in cx.cuts] + [(c["end"], f"{c['id']} out") for c in cx.cuts] + [(tb, f"{k} at {tb:.2f}") for tb, k in cx.trans]
    for t, lab in sorted(set(pts)):
        d = on(t)
        if d < .5: continue
        if d <= 3: bad.append(f"{lab}: {d:.1f} f from the segment boundary (a frame of the other take shows)")
        else: notes.append(f"{lab}: mid-shot (nearest boundary {d:.0f} f; snap: false), no take change exposed")
    gate("CUT-04", not bad, f"{len(set(pts))} cutaway / transition edits: {len(set(pts)) - len(bad) - len(notes)} on segment boundaries, {len(notes)} deliberately mid-shot",
         "\n".join(bad + notes))
    kws = [k.lower() for k in (cx.E.get("qc", {}) or {}).get("topic_keywords", [])]
    first = None
    for i in cx.inst:
        if not i.text: continue
        if i.role == "caption":
            for (s, e, w) in cx.cap_words(i):
                if any(k in w.lower() for k in kws):     # the first frame the word is really drawn (not hidden by a chest / snap / card)
                    f = next((g for g in range(max(i.f0, int(math.ceil((s - .03) * FPS))), min(i.f1, int(e * FPS)) + 1) if cx.cap_allowed(g)), None)
                    if f is not None and (first is None or f < first[0]): first = (f, i.key, w)
        elif any(k in i.text.lower() for k in kws) and (first is None or i.f0 < first[0]): first = (i.f0, i.key, i.text)
    if not kws: gate("RET-12", False, "no qc.topic_keywords in edit.yaml", status="WARN")
    else: gate("RET-12", first is not None and first[0] / FPS <= 2.0, f"topic keyword on screen at {first[0] / FPS:.2f} s ({first[1]} '{first[2]}')" if first else "no text layer shows a topic keyword")


# ======================================================================== visual events (SND-07; mix's cue sync uses the same list)
def visual_events(cx, low=None):
    """[(t, label)] of the picture events a sound may sit on: element entries (first logged frame of every non-caption
    instance), cuts / transitions, the snap, logged bbox changes after a hold and, when `low` (frame -> quarter-res luma)
    is given, pixel-change onsets on graphic frames. One definition for the SND-07 gate and for mix's cue sync."""
    FPS = cx.FPS
    ev = [(i.f0 / FPS, f"{i.key} appears") for i in cx.inst if i.role != "caption"]
    ev += [(tb, f"{k} cut") for tb, k in cx.trans] + [(s["t0"], f"cut to {s['id']}") for s in cx.segs[1:]]
    if cx.snap: ev += [(cx.snap[0], "snap punch-in"), (cx.snap[1], "snap release")]
    for i in cx.inst:
        if i.role == "caption": continue
        for j in range(3, len(i.f)):
            if np.abs(np.diff(i.bb[j - 3:j], axis=0)).max() <= 1 and np.abs(i.bb[j] - i.bb[j - 1]).max() > 2: ev.append((i.f[j] / FPS, f"{i.key} changes"))
    if low: ev += [(f / FPS, f"pixel change on f{f}") for f in pixel_events(cx, low)]
    return ev

def pixel_events(cx, low, frames=None, min_px=12):
    """frames on which a region of a graphic frame starts changing (quarter-res luma differs by > 25 on >= min_px px that
    were still on the frame before). `low` maps frame -> luma; a frame needs itself and the one before; `frames` limits
    the frames reported (warm-up frames before a window are measured but not reported)."""
    out, prev = [], None
    for f in range(1, cx.N):
        if f in low and f - 1 in low and not cx.is_aroll(f) and not cx.is_aroll(f - 1) and not cx.in_trans(f, .05):
            ch = (np.abs(low[f].astype(np.int16) - low[f - 1].astype(np.int16)) > 25).astype(np.uint8)
            new = ch & (1 - cv2.dilate(prev, np.ones((5, 5), np.uint8))) if prev is not None else ch
            if new.sum() >= min_px and (frames is None or f in frames): out.append(f)
            prev = ch
        else: prev = None
    return out


# ======================================================================== gates: sound
def gates_sound(cx, gate):
    import soundfile as sf
    pr, FPS = cx.pr, cx.FPS
    try:
        from ..render import Timeline
        from ..mix import all_cues, sfx_bank, load_audio
        TL = Timeline(pr); cues = sorted(all_cues(TL), key=lambda c: c[0]); find = sfx_bank(TL)
    except Exception as e:
        for g in ("SND-07", "SND-08", "SND-09", "SND-11"): gate(g, False, f"cue list not rebuilt: {type(e).__name__}: {e}", status="WARN")
        cues = None
    if cues is not None:
        import librosa
        SR = 48000; cache = {}
        def clip(name, kw):
            key = (name, str(kw.get("trim")))
            if key not in cache:
                y = load_audio(find(name))
                if kw.get("trim"): y = y[int(kw["trim"][0] * SR):int(kw["trim"][1] * SR)]
                cache[key] = y
            return cache[key]
        ev = visual_events(cx, cx._results.get("low", {}))
        evt = np.array([e[0] for e in ev]); cut_t = np.array([tb for tb, _ in cx.trans] + [cx.T_END])     # transitions (whip / glitch / end card)
        ok_, off, unm, s8 = 0, [], [], []
        for t, name, gain, kw in cues:
            if t < 0 or t * FPS >= cx.N: continue
            y = clip(name, kw)
            if not len(y): continue
            env = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")); pk = env.max() + 1e-12
            on_t, pk_t = t + int(np.argmax(env >= .1 * pk)) / SR, t + int(np.argmax(env)) / SR
            dc = (pk_t - cut_t) * FPS; jc = int(np.argmin(np.abs(dc)))
            if any(n in name for n in SFX_PEAK_NAMES) and abs(dc[jc]) <= 12 and not kw.get("accent"):      # transition whoosh: SND-08 (peak on the cut); automatic risers: SND-32
                s8.append((name, t, on_t, pk_t, cut_t[jc], dc[jc])); continue
            at, how = (pk_t, "peak") if "riser" in name else (on_t, "onset")      # SND-07: risers at their peak, the rest at onset
            d = (at - evt) * FPS; j = int(np.argmin(np.abs(d)))
            if abs(d[j]) <= 1: ok_ += 1
            elif abs(d[j]) <= 6: off.append(f"{name} {how} {at:.3f} s vs {ev[j][1]} {evt[j]:.3f} s ({d[j]:+.1f} f)")
            else: unm.append(f"{name} {how} {at:.2f} s (nearest event {ev[j][1]} {d[j]:+.1f} f)")
        n = ok_ + len(off) + len(unm)
        gate("SND-07", not off, f"{n} SFX cues: {ok_} within 1 f of a visual event, {len(off)} off by 1-6 f, {len(unm)} with no logged visual event within 6 f",
             "\n".join(off[:14] + ([f"unmatched (check by eye): {len(unm)}"] + unm[:8] if unm else [])), status=None if off else ("WARN" if unm else "PASS"))
        b8 = [f"{n} at {t:.2f} s: peak {p:.3f} s vs cut {c:.3f} s ({d:+.1f} f){'' if o < c else ', onset after the cut'}" for n, t, o, p, c, d in s8 if abs(d) > 1 or o >= c]
        gate("SND-08", not b8, f"{len(s8)} transition whooshes: peak within 1 f of the cut in {len(s8) - len(b8)}", "\n".join(b8[:12]), status=None if not b8 else "WARN")
        # SND-09 identical consecutive cues
        rep = []
        for a, b in zip(cues[:-1], cues[1:]):
            same = a[1] == b[1] and a[3].get("pitch", 0) == b[3].get("pitch", 0)
            if not same: continue
            if str(a[3].get("trim")) == str(b[3].get("trim")): rep.append(f"{a[1]} at {a[0]:.2f} s and {b[0]:.2f} s identical (gap {b[0] - a[0]:.2f} s)")
            else:
                ya, yb = clip(a[1], a[3]), clip(b[1], b[3]); m = min(len(ya), len(yb))
                c = float(np.dot(ya[:m], yb[:m]) / (np.linalg.norm(ya[:m]) * np.linalg.norm(yb[:m]) + 1e-9))
                if c > .95: rep.append(f"{a[1]} at {a[0]:.2f} s and {b[0]:.2f} s: correlation {c:.2f} (gap {b[0] - a[0]:.2f} s)")
        gate("SND-09", not rep, f"{len(cues)} SFX cues: {len(rep)} identical consecutive repeats", "\n".join(rep[:12]))
        # SND-11 SFX level vs the voice peak; none above -2 dBFS on the stem (reveal cues are the tagged heroes)
        try:
            sx, sr = sf.read(pr.e("stems", "sfx.wav")); vo, _ = sf.read(pr.e("stems", "voice.wav"))
            sx = sx.mean(1) if sx.ndim > 1 else sx; vo = vo.mean(1) if vo.ndim > 1 else vo; vp = max(float(np.abs(vo).max()), 1e-9)
            hot = []
            for t, name, gain, kw in cues:
                i0 = int(max(0, t) * sr); seg = sx[i0:i0 + len(clip(name, kw))]
                if not len(seg): continue
                p = np.abs(seg).max()
                if (p > vp and not kw.get("reveal")) or p > 10 ** (-2 / 20): hot.append(f"{name} at {t:.2f} s: {20 * np.log10(p + 1e-12):.1f} dBFS (voice peak {20 * np.log10(vp):.1f})")
            gate("SND-11", not hot, f"SFX stem peak {20 * np.log10(np.abs(sx).max() + 1e-12):.1f} dBFS vs voice peak {20 * np.log10(vp):.1f} dBFS", "\n".join(hot[:10]), status=None if not hot else "WARN")
        except Exception as e: gate("SND-11", False, f"not measured: {e}", status="WARN")
    # SND-22 dialogue consistency per sentence (BS.1770 on the voice stem)
    try:
        vo, sr = sf.read(pr.e("stems", "voice.wav")); vo = vo.mean(1) if vo.ndim > 1 else vo
        sent, cur = [], []
        for w in cx.words:
            cur.append(w)
            if w[2].rstrip().endswith((".", "?", "!")): sent.append(cur); cur = []
        if cur: sent.append(cur)
        L = []
        for s in sent:
            a, b = s[0][0], s[-1][1]
            if b - a < .4: continue
            l = bs1770(vo[int(a * sr):int(b * sr)], sr)
            if not math.isnan(l): L.append((l, a, " ".join(w[2] for w in s)))
        if not L: raise ValueError("no sentences in words.json")
        med = float(np.median([x[0] for x in L])); f5 = [x for x in L if abs(x[0] - med) >= 5]; w3 = [x for x in L if 3 <= abs(x[0] - med) < 5]
        gate("SND-22", not f5, f"{len(L)} sentences: median {med:.1f} LUFS, range {min(x[0] for x in L) - med:+.1f}..{max(x[0] for x in L) - med:+.1f} LU",
             "\n".join(f"{x[1]:.2f} s {x[0] - med:+.1f} LU '{x[2][:40]}'" for x in sorted(f5 + w3, key=lambda x: -abs(x[0] - med))[:10]), status=None if f5 else ("WARN" if w3 else "PASS"))
    except Exception as e: gate("SND-22", False, f"not measured: {type(e).__name__}: {e}", status="WARN")
    # SND-23 pre-master headroom; SND-13 dead air
    try:
        pk = {}
        for nm, p in (("voice", pr.e("stems", "voice.wav")), ("music", pr.e("stems", "music.wav")), ("sfx", pr.e("stems", "sfx.wav")), ("premaster", pr.e("mix_premaster.wav"))):
            if os.path.exists(p):
                y, _ = sf.read(p)
                if np.abs(y).max() > 1e-6: pk[nm] = 20 * np.log10(np.abs(y).max() + 1e-12)      # a silent stem (no voice spine) is not reported
        hot = {k: v for k, v in pk.items() if v > -2}
        gate("SND-23", not hot, "sample peaks " + ", ".join(f"{k} {v:.1f}" for k, v in pk.items()) + " dBFS (<= -2; voice ~ -10 report)", status=None if not hot else "WARN")
    except Exception as e: gate("SND-23", False, f"not measured: {e}", status="WARN")
    try:
        y, sr = sf.read(pr.e("mix.wav")); y = y.mean(1) if y.ndim > 1 else y; h = int(.25 * sr)
        db = np.array([20 * np.log10(np.sqrt(np.mean(y[i:i + h] ** 2)) + 1e-12) for i in range(0, len(y) - h + 1, h)])
        dead = [f"{k * .25:.2f} s: {v:.1f} dBFS" for k, v in enumerate(db) if v < -50]
        gate("SND-13", not dead, f"quietest 250 ms window {db.min():.1f} dBFS (> -50)", "\n".join(dead[:8]), status=None if not dead else "WARN")
    except Exception as e: gate("SND-13", False, f"not measured: {e}", status="WARN")


# ======================================================================== entry point
def run_extra(pr, video, gate):
    global W, H, U_, LOW
    from .. import gfx as G, style as STY
    from . import small_size
    W, H = ((pr.json("timeline.json", {}) or {}).get("size") or G.canvas_of(STY.load(pr), pr)); U_ = min(W, H) / 1080; LOW = small_size(W, H)
    G.set_canvas(W, H)
    cx = Ctx(pr, video)
    def safe(fn, ids):
        try: fn(cx, gate)
        except Exception as e:
            import traceback; tb = traceback.format_exc().strip().splitlines()[-3:]
            for g in ids: gate(g, False, f"not measured: {type(e).__name__}: {e}", "\n".join(tb), status="WARN")
    if not cx.els or not cx.segs:
        gate("ELEMENT-LOG-X", False, "elements.jsonl / timeline.json missing: extra gates skipped (render with `cves render`)", status="WARN"); return
    # ---- plan the single decode
    need = collections.defaultdict(list)
    per = plan_aroll(cx); plates = {}
    text_fr = {}
    for i in cx.inst:       # text contrast: static, opaque, transition-free frames, every 6th, <= 8 per element
        if not i.is_text: continue
        fr = [int(i.f[j]) for j in range(len(i.f)) if i.al[j] >= .95 and not cx.in_trans(int(i.f[j]))
              and (i.role == "caption" or (0 < j < len(i.f) - 1 and np.abs(i.bb[j] - i.bb[j - 1]).max() <= 1
                                           and np.abs(i.bb[j + 1] - i.bb[j]).max() <= 1))]     # static on both sides (as GFX-08): not mid-entry
        text_fr[i.key] = (fr[::6] or fr[:1])[:8]
    roto_fr = sorted(set(f for i in cx.inst if i.role == "roto" and i.is_text for f in text_fr.get(i.key, [])))
    mattes = {}             # plate-space mattes for sampled A-roll frames and for roto text frames (person mask)
    for s in cx.segs:
        fs = set(per[s["id"]]["pick"] if s["id"] in per else []) | {f for f in roto_fr if s["f0"] <= f < s["f0"] + s["n"]}
        if not fs: continue
        for k, a in decode_plate_frames(cx, pr.e("matte", f"{s['id']}.mkv"), [f - s["f0"] for f in fs]).items(): mattes[s["f0"] + k] = a
        if s["id"] in per:
            p = per[s["id"]]
            for k, a in decode_plate_frames(cx, pr.e("plate", f"{s['id']}.mkv"), [p["first"] - s["f0"]]).items(): plates[s["f0"] + k] = a
            for f in p["pick"]: need[f].append(lambda f, yuv: aroll_frame(cx, f, yuv, mattes.get(f), plates.pop(f, None)))
    for c in cx.caps:       # caption style / lines: last transition-free frame showing every word (else the last transition-free frame)
        ws = cx.cap_words(c); ok = [int(f) for f in c.f if not cx.in_trans(int(f))]
        if not ok: cx._results["cap_unmeasured"].append(c.id); continue
        full = [f for f in ok if ws and ws[-1][0] <= f / cx.FPS + .03]; f = (full or ok)[-1]
        bb = next(r["bbox"] for r in c.recs if r["f"] == f)
        shown = " ".join(w[2] for w in ws if w[0] <= f / cx.FPS + .03) if ws else (c.text or "")
        def cap_cb(f, yuv, c=c, bb=bb, isfull=bool(full), shown=shown):
            m = caption_measure(yuv, bb)
            if m: cx._results["capmeas"].append(dict(key=c.key, id=c.id, f=f, full=isfull, shown=shown, **m))
        need[f].append(cap_cb)
    for i in cx.inst:
        for f in text_fr.get(i.key, []):
            bb = next(r["bbox"] for r in i.recs if r["f"] == f)
            def tc_cb(f, yuv, i=i, bb=bb):
                person = None
                if i.role == "roto" and f in mattes and cx.aroll_M(f):    # roto text sits behind the presenter: mask the person out
                    person = cv2.warpAffine(mattes[f], cx.aroll_M(f)[0], (W, H), borderMode=cv2.BORDER_REPLICATE) > 20
                cx._results["contrast"].append((i.key, f, text_contrast(yuv, bb, person=person)))
            need[f].append(tc_cb)
    cx._results["low"] = decode(cx, need)
    for k in ("errors",):
        if cx._results.get(k): gate("QC-EXTRA", False, f"{len(cx._results[k])} frame measurements failed", "\n".join(cx._results[k][:6]), status="WARN")
    safe(gates_captions, ["PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07", "PLAT-08", "PLAT-09", "PLAT-10", "GFX-16"])
    safe(gates_motion, ["MOT-01", "MOT-02", "MOT-03", "MOT-04", "MOT-05", "MOT-07", "MOT-12", "MOT-14"])
    safe(gates_graphics, ["GFX-05", "GFX-08", "GFX-15", "GFX-17", "GFX-20", "GFX-24", "GFX-26"])
    safe(gates_frame_colour, ["FRAME-02", "FRAME-03", "FRAME-04", "FRAME-05", "FRAME-06", "FRAME-10", "COL-03", "COL-04", "COL-05", "COL-06", "COL-07", "COL-08", "COL-09", "COL-10"])
    safe(gate_col12, ["COL-12"])
    safe(gates_timeline, ["CUT-04", "RET-12"])
    safe(gates_sound, ["SND-07", "SND-08", "SND-09", "SND-11", "SND-13", "SND-22", "SND-23"])
    from .sound_gates import gates_senior_sound            # v0.4 WS H: riser resolve + phrase alignment (WARN-only)
    safe(gates_senior_sound, ["SND-32", "SND-33"])
