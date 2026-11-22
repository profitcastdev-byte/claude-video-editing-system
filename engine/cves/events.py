"""Picture events a sound can sit on, for the mix's SFX cue sync (sound.sync_cues), and BS.1770 loudness (sfx.measure).

Reads the render's own logs: Edit/elements.jsonl (one record per element per frame) and Edit/timeline.json (segments,
cutaways, transitions, snap). Pixel-change onsets are measured on quarter-res luma of the rendered frames."""
import os, re, json, collections
import numpy as np, cv2

TRANS_DUR = {"whip": .15, "glitch": .10, "cut": 0}          # render.TRANS_DUR (unknown kinds use .12, as trans_strength)
DECOR = ("brackets", ".glow", ".bed")                        # frame decoration / glow / shadow beds: not type, not movers
DESCRIPTOR = {"map", "listing", "map pack", "logo"}          # `text` used as a label on graphic-only elements
LOW = (270, 480)                                             # low-res analysis size (canvas aspect)


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
        self.f0, self.f1 = int(self.f[0]), int(self.f[-1]); self.size = r0.get("size")
        self.cls = re.sub(r"\d+$", "", self.id.split("@")[0])          # list.item0 -> list.item ; caption@1.51 -> caption
    @property
    def decor(self): return any(d in self.id for d in DECOR)
    @property
    def is_text(self):
        return bool(self.text) and self.text.strip().lower() not in DESCRIPTOR and not self.decor


class Ctx:
    """the rendered timeline and element instances of a project (what visual_events / pixel_events read)"""
    def __init__(self, pr, video=None):
        self.pr, self.video = pr, video
        from . import style as STY
        self.S = STY.load(pr)
        TL = pr.json("timeline.json", {}) or {}
        self.FPS = TL.get("fps") or (pr.json("edl.json", {}) or {}).get("fps") or 30.0; self.A = int(TL.get("a_frames", 0)); self.N = int(TL.get("frames", 0))
        self.segs = TL.get("segments", []); self.cuts = TL.get("cutaways", []); self.trans = [tuple(x) for x in TL.get("transitions", [])]
        self.snap = TL.get("snap"); self.spine = TL.get("spine") or "aroll"
        ef = pr.e("elements.jsonl")
        els = [json.loads(l) for l in open(ef, encoding="utf-8")] if os.path.exists(ef) else []
        runs = collections.OrderedDict()
        for e in sorted(els, key=lambda r: (r["id"], r["f"])):
            L = runs.setdefault(e["id"], [])
            if L and (e["role"] == "caption" or e["f"] - L[-1][-1]["f"] <= 6): L[-1].append(e)
            else: L.append([e])
        self.inst = []
        for k, L in runs.items():
            for j, r in enumerate(L): self.inst.append(Inst(k if len(L) == 1 else f"{k}#{j + 1}", r))
        self.inst.sort(key=lambda i: i.f0)

    def in_cut(self, t): return any(c["start"] <= t < c["end"] for c in self.cuts)
    def is_aroll(self, f): return self.spine == "aroll" and 0 <= f < self.A and not self.in_cut(f / self.FPS)
    def in_trans(self, f, pad=0.):
        t = f / self.FPS
        for tb, kind in self.trans:
            d = 0 if kind in (None, "cut") else float(self.S.get(f"transitions.{kind}_s", TRANS_DUR.get(kind, .12)))   # the window render drew (craft.trans_dur)
            if d and abs(t - tb) < d + pad: return (tb, kind)
        return None


def visual_events(cx, low=None, px=None):
    """[(t, label)] of the picture events a sound may sit on: element entries (first logged frame of every non-caption
    instance), cuts / transitions, the snap, logged bbox changes after a hold and, when `low` (frame -> quarter-res luma)
    is given, pixel-change onsets on graphic frames."""
    FPS = cx.FPS
    ev = [(i.f0 / FPS, f"{i.key} appears") for i in cx.inst if i.role != "caption"]
    ev += [(tb, f"{k} cut") for tb, k in cx.trans] + [(s["t0"], f"cut to {s['id']}") for s in cx.segs[1:]]
    if cx.snap: ev += [(cx.snap[0], "snap punch-in"), (cx.snap[1], "snap release")]
    for i in cx.inst:
        if i.role == "caption": continue
        for j in range(3, len(i.f)):
            if np.abs(np.diff(i.bb[j - 3:j], axis=0)).max() <= 1 and np.abs(i.bb[j] - i.bb[j - 1]).max() > 2: ev.append((i.f[j] / FPS, f"{i.key} changes"))
    if px is None and low: px = pixel_events(cx, low)
    if px: ev += [(f / FPS, f"pixel change on f{f}") for f in px]
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
