"""edit.yaml + the style profile -> frames (+ element log). Shared by vibe mode (final frames) and control mode (layered clips).
No look is hard-coded: grade, captions, transitions, framing levels, pacing and motion all come from `style.load()`
(docs/STYLE.md). Engine invariants (not style): edits snap to segment boundaries, every direct A-roll cut changes scale by
the style's min_step, per-shot exposure balance, face-smoothed punch-ins, a single lossless source path."""
import os, sys, json, math, random, glob
import numpy as np, cv2
import multiprocessing as _mp
Pool = _mp.get_context("spawn").Pool   # same on every OS; fork deadlocks once torch/OpenCV threads exist (Linux)
from PIL import Image, ImageFilter
from fractions import Fraction
from . import gfx as G, templates as TPL, style as STY, captions as CAP
from .gfx import W, H, prog, clamp
from .look import grade

# Templates that need the graded A-roll frame under them (media templates such as `pip` and `split`): they get
# ctx["aroll"] = (graded RGB float HxWx3, matte float HxW, both framed like the A-roll shot). Filled by
# refresh_needs_aroll() from cves.templates: every template whose kind is "media", plus any template module that
# declares `NEEDS_AROLL = {names}` (or `NEEDS_AROLL = True` for all its templates). Every other template costs nothing.
NEEDS_AROLL = set()

def refresh_needs_aroll():
    NEEDS_AROLL.clear()
    for name, fns in TPL.REGISTRY.items():
        mod = sys.modules.get(getattr(fns[0], "__module__", ""), None)
        decl = getattr(mod, "NEEDS_AROLL", None)
        if TPL.KIND.get(name) == "media" or decl is True or (isinstance(decl, (set, list, tuple, dict)) and name in decl):
            NEEDS_AROLL.add(name)
    return NEEDS_AROLL


# ------------------------------------------------------------------ timeline
class Timeline:
    def __init__(self, pr):
        self.pr = pr; E = pr.edit; self.E = E
        self.S = STY.load(pr); self.style = self.S; G.apply_style(self.S)     # the ONLY source of look (docs/STYLE.md)
        TPL.load_dir(pr.p("Brand", "templates"), "project")                  # per-client templates, if any
        refresh_needs_aroll()
        edl = pr.json("edl.json"); self.FPS = edl["fps"]; self.faces = pr.json("faces.json", {})
        G.FPS = self.FPS                                                     # cue / animation quantisation in templates (MOT-07)
        self.size = (W, H)                                                      # the frame canvas the renderer writes
        fr = edl.get("fps_rational"); self.fps_rational = tuple(fr) if fr else (Fraction(self.FPS).limit_denominator(1001).numerator, Fraction(self.FPS).limit_denominator(1001).denominator)
        self.segs = []; f0 = 0
        for s in edl["segments"]:
            n = round((s["out"] - s["in"]) * self.FPS); self.segs.append(dict(s, f0=f0, n=n, t0=f0 / self.FPS, t1=(f0 + n) / self.FPS)); f0 += n
        self.A_FRAMES = f0; self.T_END = f0 / self.FPS
        end = E.get("end_card") or {}; self.END = end.get("duration", 0)
        self.N = self.A_FRAMES + round(self.END * self.FPS)
        snapb = [s["t0"] for s in self.segs] + [self.T_END]
        self.snap_t = lambda t: min(snapb, key=lambda x: abs(x - t))
        self.cuts = []
        for c in E.get("cutaways", []):
            sn = c.get("snap", True)    # snap to segment boundaries (hides jump cuts); snap:false for a beat that starts mid-shot
            self.cuts.append(dict(c, start=self.snap_t(c["start"]) if sn else c["start"], end=self.snap_t(c["end"]) if sn else c["end"]))
        self.trans = []
        for c in self.cuts:
            self.trans.append((c["start"], c.get("in", self.S.get("transitions.in", "cut")))); self.trans.append((c["end"], c.get("out", self.S.get("transitions.out", "cut"))))
        if self.END: self.trans.append((self.T_END, end.get("in", self.S.get("transitions.in", "cut"))))
        for tr in E.get("transitions", []): self.trans.append((self.snap_t(tr["t"]), tr["kind"]))
        self.roto = {r["segment"]: r for r in E.get("roto", [])}
        self.chest = {}
        for c in E.get("chest", []):
            for sid in ([c["segment"]] if isinstance(c["segment"], str) else c["segment"]): self.chest.setdefault(sid, []).append(c)
        ar = E.get("aroll", {}); self.creep = ar.get("creep", self.S.get("framing.creep", 0.0))
        sn = ar.get("snap"); self.snap = (sn["start"], sn["end"], sn["zoom"]) if sn else None
        self.zoom = self._auto_zoom(ar.get("zoom", {}))
        self.gain = self._exposure() if ar.get("exposure_match", self.S.get("grade.exposure_match", True)) else {}
        self.caps = self._captions()
        self.root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def resolve(self, p):
        """asset id (edit.yaml `assets:` / Edit/assets.json) -> path; else a path relative to the project or the repo"""
        if isinstance(p, str) and p:
            try:
                from . import assets as AS                 # lazy: optional module (asset registry)
                q = AS.resolve(self.pr, p, strict=False)
                if q: return q
            except (ImportError, AttributeError, TypeError):
                pass
        for base in (self.pr.root, self.root):
            q = os.path.join(base, p)
            if os.path.exists(q): return q
        return p

    def ctx(self, start, end, **kw):
        """the ctx dict every template call gets: start/end (cut-time s), resolve, fps (quantise starts with
        round(t * fps) / fps, MOT-07) and S (the style profile)"""
        return {"start": start, "end": end, "resolve": self.resolve, "fps": self.FPS, "S": self.S, **kw}

    # ---- --only: ids / ranges -> frames
    def only_targets(self):
        """every id `--only` accepts -> (first frame, end frame exclusive, layer kind)"""
        F = self.FPS; out = {}
        for s in self.segs: out[s["id"]] = (s["f0"], s["f0"] + s["n"], "aroll"); out["a_" + s["id"]] = out[s["id"]]
        for c in self.cuts: out[str(c["id"])] = (round(c["start"] * F), round(c["end"] * F), "cutaway")
        for k, r in enumerate(self.E.get("roto", []) or []):
            s = next((x for x in self.segs if x["id"] == r["segment"]), None)
            if s: out[f"roto.{k}"] = out[f"roto:{s['id']}"] = (s["f0"], s["f0"] + s["n"], "aroll")
        for k, (lo, hi) in enumerate(self.chest_spans()):
            if hi > lo: out[f"chest.{k}"] = out[f"chest_{k}"] = (lo, hi, "chest")
        if self.END: out["end_card"] = out["end"] = (self.A_FRAMES, self.N, "end")
        return out

    def chest_spans(self):
        """per edit.yaml chest entry: (first frame, end frame) of the segments it sits on"""
        spans = []
        for c in self.E.get("chest", []) or []:
            sids = [c["segment"]] if isinstance(c["segment"], str) else list(c["segment"])
            fr = [(s["f0"], s["f0"] + s["n"]) for s in self.segs if s["id"] in sids]
            spans.append((min(a for a, _ in fr), max(b for _, b in fr)) if fr else (0, 0))
        return spans

    def frames_for(self, spec):
        """`--only` spec -> sorted frame list. Items (comma list): a cutaway / segment / layer id (c3, 01_hook_0,
        a_01_hook_0, roto.0, roto:<segment>, chest.0, chest_0, end_card), a time range in seconds (12.5-14.0, or
        12s-14s), a frame range (300-420, inclusive), one frame (300) or one time (12.5)."""
        import re
        if spec is None: return None
        items = [x.strip() for x in (spec.split(",") if isinstance(spec, str) else spec) if str(x).strip()]
        tg = self.only_targets(); fr = set(); bad = []
        num = r"\d+(?:\.\d*)?s?"
        for it in items:
            it = str(it)
            if it in tg: a, b, _ = tg[it]; fr.update(range(a, b)); continue
            m = re.fullmatch(rf"({num})\s*-\s*({num})", it)
            if m:
                x, y = m.groups()
                if "." in it or it.endswith("s") or "s-" in it.replace(" ", ""):
                    a, b = round(float(x.rstrip("s")) * self.FPS), round(float(y.rstrip("s")) * self.FPS)
                else: a, b = int(x), int(y) + 1
                fr.update(range(max(0, a), min(self.N, b))); continue
            if re.fullmatch(r"\d+", it): fr.add(int(it)); continue
            if re.fullmatch(r"\d+\.\d*s?|\d+s", it): fr.add(round(float(it.rstrip("s")) * self.FPS)); continue
            bad.append(it)
        if bad:
            raise SystemExit(f"--only: unknown id or range {', '.join(bad)}; ids: {', '.join(sorted(k for k in tg if not k.startswith(('a_', 'roto:'))))}")
        out = sorted(f for f in fr if 0 <= f < self.N)
        if not out: raise SystemExit(f"--only {spec}: no frames in 0-{self.N - 1}")
        return out

    def in_cut(self, t):
        for c in self.cuts:
            if c["start"] <= t < c["end"]: return c
        return None

    def seg_at(self, i):
        for s in self.segs:
            if s["f0"] <= i < s["f0"] + s["n"]: return s

    def is_aroll(self, s): return not self.in_cut(s["t0"] + .5 / self.FPS) or not self.in_cut(s["t1"] - .5 / self.FPS)

    def _auto_zoom(self, given):
        """framing per A-roll segment:
        - every DIRECT A-roll cut changes scale by >= 1.15x with creep counted (CUT-05)
        - optional `aroll.lift`: shots carrying a chest element are punched in and anchored at the frame bottom to make room
          under the chin. OFF by default: on close selfies it crops the head. Put key info (prices) in a cutaway instead.
        - levels 1.0 / 1.18 / 1.38: every pair >= 1.15x with creep, all below the 1.4x "extreme" line (FRAME-09); 1.38 is 0.87 of native on 3072-px sources"""
        z, prev, self.lift = {}, None, set()
        for s in self.segs:
            visible = any(not self.in_cut((s["f0"] + k) / self.FPS) for k in range(0, s["n"], 3))
            if not visible: prev = None; continue
            direct = prev is not None and not self.in_cut(s["t0"] - .5 / self.FPS)
            needs_lift = self.E.get("aroll", {}).get("lift", self.S.get("framing.lift", False)) and s["id"] in self.chest   # opt-in: lifting crops the head on close selfies
            if needs_lift: self.lift.add(s["id"])
            if s["id"] in given: z[s["id"]] = given[s["id"]]
            else:
                levels = sorted(self.S.get("framing.zoom_levels", [1.0, 1.18, 1.38])); step = self.S.get("framing.min_step", 1.15)
                lo = levels[1] if needs_lift and len(levels) > 1 else levels[0]
                pz = z.get(prev, levels[0]) * (1 + self.creep) if direct else None
                z[s["id"]] = next((c for c in levels if c >= lo and (pz is None or max(c, pz) / min(c, pz) >= step)), levels[-1] if (pz or 0) < levels[-1] else levels[0])
            prev = s["id"]
        return z

    def _exposure(self):
        """per-shot skin balance (COL-06/07), one gain per shot. Cheek-patch L* is measured on the plate every 2nd visible
        frame and on the first / last 3 VISIBLE frames of each shot (cutaway and transition frames excluded: that is what
        the viewer sees either side of a cut). Skin drifts inside a shot as the head moves through the light, so gaining
        shot medians together still left the cut frames 5-9 dE apart. The gains are a weighted least-squares fit in log
        luminance: consecutive shots meet at their boundary frames (direct cuts weight 1, across a cutaway 0.5) and every
        pair of consecutive shots also meets at its shot medians (COL-07), and every shot median is weakly anchored to the
        common median (weight `grade.exposure_anchor_weight`) so the video does not drift. Clamped to
        `grade.exposure_gain_range`. Cached in Edit/exposure.json with the timeline signature it was solved for."""
        cache = self.pr.e("exposure.json")
        lo_g, hi_g = self.S.get("grade.exposure_gain_range", [.85, 1.18]); w_med = float(self.S.get("grade.exposure_anchor_weight", .15))
        vis = {}
        for s in self.segs:     # visible A-roll frames: not under a cutaway, not inside a transition window
            v = [k for k in range(s["n"]) if not self.in_cut((s["f0"] + k) / self.FPS) and trans_strength(self, (s["f0"] + k) / self.FPS)[0] is None]
            if v: vis[s["id"]] = v
        sig = {"method": "boundary-lsq-5", "mode": self.S.get("grade.exposure_mode", "rgb"), "segs": [[s["id"], s["n"]] for s in self.segs], "vis": {k: [v[0], v[-1], len(v)] for k, v in vis.items()},
               "range": [lo_g, hi_g], "w_med": w_med}
        if os.path.exists(cache):
            c = json.load(open(cache, encoding="utf-8"))
            if isinstance(c, dict) and c.get("_sig") == sig: return c["gain"]
        import av
        def cheeks_L(rgb, f):
            """L* of the two cheek patches, each summarised on its own and then averaged (as QC COL-06 measures it):
            under side light the cheeks sit 40-80 Y apart, so a pooled median flips between them as the head turns"""
            if f is None or len(f) < 14 or not any(f[4:14]): return None
            lm = np.array(f[4:14], float).reshape(5, 2); kk = max(4, int(f[2] * .05)); out = []; rgbs = []
            for eye, mouth in ((lm[0], lm[3]), (lm[1], lm[4])):
                cx, cy = eye * .55 + mouth * .45; x0, y0 = int(cx) - kk, int(cy) - kk
                p = rgb[max(0, y0):y0 + 2 * kk, max(0, x0):x0 + 2 * kk]
                if p.size < 48: return None
                out.append(float(np.median(cv2.cvtColor(p.astype(np.float32) / 255, cv2.COLOR_RGB2Lab)[..., 0])))
                rgbs.append(np.median(p.reshape(-1, 3).astype(np.float32), 0))
            return float(np.mean(out)), np.mean(rgbs, 0)
        meas = {}
        for s in self.segs:
            sid = s["id"]; v = vis.get(sid)
            if not v: continue
            F = self.faces.get(sid) or []
            if not F: continue
            want = set(v[::max(2, len(v) // 30)]) | set(v[:3]) | set(v[-3:]); L = {}; RGB = {}     # <= ~30 samples per shot: long videos stay cheap
            with av.open(self.pr.e("plate", f"{sid}.mkv")) as cin:
              for k, f in enumerate(cin.decode(video=0)):
                if k > v[-1]: break
                if k not in want: continue
                l_ = cheeks_L(f.to_ndarray(format="rgb24"), F[min(k, len(F) - 1)])
                if l_ is not None: L[k] = l_[0]; RGB[k] = l_[1]
            if not L: continue
            head = [L[k] for k in v[:3] if k in L] or [L[min(L)]]; tail = [L[k] for k in v[-3:] if k in L] or [L[max(L)]]
            # the cut frame itself (what the viewer compares) blended with its 3-frame median (landmark noise)
            st = .5 * (L.get(v[0], np.median(head)) + np.median(head)); en = .5 * (L.get(v[-1], np.median(tail)) + np.median(tail))
            meas[sid] = dict(med=float(np.median(list(L.values()))), start=float(st), end=float(en), first=v[0], last=v[-1])
            hr = [RGB[k] for k in v[:3] if k in RGB] or [RGB[min(RGB)]]; tr = [RGB[k] for k in v[-3:] if k in RGB] or [RGB[max(RGB)]]
            meas[sid]["rgb"] = dict(med=np.median(list(RGB.values()), 0).tolist(), start=np.median(hr, 0).tolist(), end=np.median(tr, 0).tolist())
        if not meas:
            json.dump({"_sig": sig, "gain": {}}, open(cache, "w", encoding="utf-8"), indent=1); return {}
        u = lambda L: math.log(((L + 16) / 116) ** 3)          # log relative luminance of an L* value
        ids = [s["id"] for s in self.segs if s["id"] in meas]; ix = {k: j for j, k in enumerate(ids)}
        t = float(np.median([u(meas[k]["med"]) for k in ids]))
        rows, rhs, wts = [], [], []
        for k in ids:          # weak anchor: shot median -> common median (gain g scales luminance by g**2.2: x = 2.2 * ln g)
            r = np.zeros(len(ids)); r[ix[k]] = 1; rows.append(r); rhs.append(t - u(meas[k]["med"])); wts.append(w_med)
        for a, b in zip(ids[:-1], ids[1:]):     # consecutive visible shots: cut frames meet AND shot medians meet
            A_, B_ = meas[a], meas[b]
            fa = next(s["f0"] for s in self.segs if s["id"] == a) + A_["last"]; fb = next(s["f0"] for s in self.segs if s["id"] == b) + B_["first"]
            w = 1.0 if not any(self.in_cut(f / self.FPS) for f in range(fa + 1, fb)) else .5       # direct cut / across a cutaway
            for da, db in ((A_["end"], B_["start"]), (A_["med"], B_["med"])):
                r = np.zeros(len(ids)); r[ix[a]] = 1; r[ix[b]] = -1; rows.append(r); rhs.append(u(db) - u(da)); wts.append(w)
        Wt = np.sqrt(np.array(wts))[:, None]
        x = np.linalg.lstsq(np.array(rows) * Wt, np.array(rhs) * Wt[:, 0], rcond=None)[0]
        g = {k: float(np.clip(math.exp(x[ix[k]] / 2.2), lo_g, hi_g)) for k in ids}
        if self.S.get("grade.exposure_mode", "rgb") == "rgb":
            # skin hue/chroma also jumps at cuts (white balance drift, COL-06 a/b): solve the same system on log(channel / mean)
            # per channel and apply it as a small per-channel trim around the luminance gain, capped at grade.exposure_chroma_max
            cmax = float(self.S.get("grade.exposure_chroma_max", .06))
            def rel(v3): v3 = np.maximum(np.array(v3, float), 1.0); return np.log(v3 / v3.mean())
            trims = {k: np.zeros(3) for k in ids}
            ref = np.median([rel(meas[k]["rgb"]["med"]) for k in ids], 0)      # anchor: the video's typical skin colour, not grey
            for c in range(3):
                rr, hh = [], []
                for k in ids:
                    r = np.zeros(len(ids)); r[ix[k]] = 1; rr.append(r * math.sqrt(w_med)); hh.append((ref[c] - rel(meas[k]["rgb"]["med"])[c]) * math.sqrt(w_med))
                for a, b in zip(ids[:-1], ids[1:]):
                    for da, db in (("end", "start"), ("med", "med")):
                        r = np.zeros(len(ids)); r[ix[a]] = 1; r[ix[b]] = -1
                        rr.append(r); hh.append(rel(meas[b]["rgb"][db])[c] - rel(meas[a]["rgb"][da])[c])
                xc = np.linalg.lstsq(np.array(rr), np.array(hh), rcond=None)[0]
                for k in ids: trims[k][c] = xc[ix[k]]
            g = {k: [float(np.clip(g[k] * math.exp(np.clip(trims[k][c] - trims[k].mean(), -cmax, cmax)), lo_g, hi_g)) for c in range(3)] for k in ids}
        json.dump({"_sig": sig, "gain": g, "skin_L": meas}, open(cache, "w", encoding="utf-8"), indent=1); return g

    def _captions(self):
        cfg = {**(self.S.get("captions") or {}), **(self.E.get("captions") or {})}     # style defaults + per-video (fixes, hide)
        self.cap_cfg = cfg; self.cap_hide = [tuple(x) for x in cfg.get("hide", [])]
        if cfg.get("events"): return [(e["start"], e["end"], [tuple(w) for w in e["words"]]) for e in cfg["events"]]
        return CAP.build(self.pr.json("words.json", []), cfg, self.T_END)

# ------------------------------------------------------------------ helpers
def skin_lab(bgr, f):
    """median Lab of two cheek patches from YuNet landmarks (stable under beard / mouth / zoom)"""
    if f is None or len(f) < 14 or not any(f[4:14]): return None
    lm = np.array(f[4:14]).reshape(5, 2); w = f[2]; pts = []
    for eye, mouth in ((lm[0], lm[3]), (lm[1], lm[4])):
        cx, cy = eye * .55 + mouth * .45; k = max(4, int(w * .05))
        pts.append(bgr[int(cy) - k:int(cy) + k, int(cx) - k:int(cx) + k])
    lab = np.concatenate([cv2.cvtColor(p, cv2.COLOR_BGR2LAB).reshape(-1, 3) for p in pts if p.size]).astype(float)
    return np.median(lab, 0) * [100 / 255, 1, 1] - [0, 128, 128]

def affine(s, cx, cy, clamp_cover):
    tx, ty = cx - s * cx, cy - s * cy
    if clamp_cover: tx = min(0, max(W - s * W, tx)); ty = min(0, max(H - s * H, ty))
    return np.float32([[s, 0, tx], [0, s, ty]])

def warp(img, M, interp=cv2.INTER_LINEAR):
    if abs(M[0, 0] - 1) < 1e-4 and abs(M[0, 2]) < .01 and abs(M[1, 2]) < .01: return img
    return cv2.warpAffine(img, M, (W, H), flags=interp, borderMode=cv2.BORDER_REPLICATE)

def zoom_blur(img, e, cx=W / 2, cy=H * .4, n=6):
    """radial (zoom) blur for whips: average of progressively scaled copies (the house spec calls for zoom-blur)"""
    if e <= .02: return img
    acc = img.copy()
    for k in range(1, n):
        acc += warp(img, affine(1 + .06 * e * k, cx, cy, False))
    return acc / n

def glitch(img, e, seed):
    if e <= 0: return img
    rng = random.Random(seed); out = img.copy()
    for _ in range(int(6 + 14 * e)):
        y0 = rng.randrange(0, H - 10); hh = rng.randrange(6, int(20 + 120 * e)); dx = int(rng.uniform(-1, 1) * 160 * e)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], dx, axis=1)
    sh = int(14 * e) + 1
    out[..., 0] = np.roll(out[..., 0], sh, axis=1); out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    lines = (np.arange(H) % 4 < 1)[:, None, None].astype(np.float32)
    return np.clip(out * (1 - .25 * e * lines) + np.array([.1, .9, .6], np.float32) * .12 * e * lines, 0, 1)

def caption_el(TL, t, chin):
    if any(a <= t < b for a, b in getattr(TL, "cap_hide", [])): return None
    S = STY.Style({**TL.S, "captions": TL.cap_cfg})
    return CAP.element(TL, t, chin, TL.caps, S)

# ------------------------------------------------------------------ frame composition
def compose(TL, i, P=None, A=None, k=0, mode="final"):
    """mode: final (everything) | aroll (graded A-roll + roto, no captions/chest) | overlay (chest + captions on transparent) | chest (chest graphics only, transparent)"""
    t = i / TL.FPS; s = TL.seg_at(i); cut = TL.in_cut(t); els = []; M = np.float32([[1, 0, 0], [0, 1, 0]])
    if t >= TL.T_END:
        e = TL.E["end_card"]; fn = TPL.get(e["template"])[0]
        els = fn(t, e.get("params", {}), TL.ctx(TL.T_END, TL.T_END + TL.END))
        img = G.stage().copy()
        for el in els: img = G.over(img, el.im)
        sc = 1 + TL.S.get('motion.drift', .025) * clamp((t - TL.T_END) / 6); M = affine(sc, W / 2, 900, False); img = warp(img, M)
    elif cut and mode != "aroll":
        fn = TPL.get(cut["template"])[0]; cx_ = TL.ctx(cut["start"], cut["end"])
        if cut["template"] in NEEDS_AROLL and P is not None and s is not None:     # media templates (pip, split)
            cx_["aroll"] = aroll_frame(TL, s, k, t, P, A)
        els = fn(t, cut.get("params", {}), cx_)
        img = G.stage().copy()
        for el in els: img = G.over(img, el.im)
        sc = 1 + TL.S.get('motion.drift', .025) * clamp((t - cut["start"]) / 6); M = affine(sc, W / 2, 900, False); img = warp(img, M)
        if mode in ("overlay", "chest"): img = None
    else:
        sid = s["id"]; f = TL.faces[sid][min(k, len(TL.faces[sid]) - 1)]
        sm = smooth_face(TL, sid, k)
        cx, cy, fh = sm
        if mode in ("overlay", "chest"): img = None
        else:
            g = np.asarray(TL.gain.get(sid, 1.0), np.float32)
            img = grade(np.clip(P * g, 0, 1) if np.any(g != 1) else P, A, (cx, cy), TL.S.get("grade"))
            r = TL.roto.get(sid)
            if r:
                rels = TPL.get(r["template"])[0](t, r.get("params", {}), TL.ctx(s["t0"], s["t1"]))
                if rels:
                    a = cv2.GaussianBlur(cv2.erode(A.astype(np.float32) / 255, np.ones((3, 3), np.uint8)), (0, 0), 1.2)[..., None]
                    person = img.copy()
                    for el in rels: img = G.over(img, el.im)
                    img = img * (1 - a) + person * a; els += rels
        z = TL.zoom.get(sid, 1.0) * (1 + TL.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
        if TL.snap and TL.snap[0] <= t < TL.snap[1]: z = TL.snap[2]
        M = affine(z, cx, H if sid in TL.lift else cy - fh * .05, True)    # lift: anchor at the frame bottom raises the face
        if img is not None: img = warp(img, M, cv2.INTER_CUBIC)
        _, scy, sfh = smooth_face(TL, sid, k, r=12)                         # smoothed: raw boxes made chest graphics shake (MOT-03)
        chin = (scy + sfh / 2) * M[1, 1] + M[1, 2]
        # captions must clear the face on THIS frame (FRAME-01): never above the raw chin, even when the head drops fast
        cap_chin = max(chin, (f[1] + f[3]) * M[1, 1] + M[1, 2]) if f is not None and len(f) >= 4 else chin
        # chest graphics hold still over the shot (MOT-03): the lowest chin of the segment, under the current framing
        Fs = TL.faces.get(sid) or []
        chin_hold = (max(x[1] + x[3] for x in Fs) * M[1, 1] + M[1, 2]) if Fs else chin
        if mode != "aroll":
            front = []
            for c in TL.chest.get(sid, []):
                front += TPL.get(c["template"])[0](t, c.get("params", {}), TL.ctx(s["t0"], s["t1"], chin=chin, chin_hold=chin_hold))
            snapped = TL.snap and TL.snap[0] <= t < TL.snap[1]
            if not front and not snapped and mode != "chest":     # chest mode: graphics only, captions go to subtitles
                ce = caption_el(TL, t, cap_chin)
                if ce: front.append(ce)
            if img is None: img = np.zeros((H, W, 4), np.float32); ov = True
            else: ov = False
            for el in front:
                if ov:
                    a = np.asarray(el.im, np.float32) / 255; al = a[..., 3:4]
                    img[..., :3] = img[..., :3] * (1 - al) + a[..., :3] * al; img[..., 3:4] = img[..., 3:4] * (1 - al) + al
                else: img = G.over(img, el.im)
            els += [(el, "post") for el in front]
    if mode == "final" and img is not None:
        kind, e, after = trans_strength(TL, t)
        if kind == "whip":
            z = 1 + (.22 if after else .35) * e ** 1.5; img = zoom_blur(warp(img, affine(z, W / 2, H * .4, False)), e ** 1.2)
        elif kind == "glitch": img = glitch(img, e, i)
        elif kind == "fade": img = img * (1 - e)          # dip through black
    return img, log_records(i, els, M)

def aroll_frame(TL, s, k, t, P, A):
    """the graded, framed A-roll frame of segment s at plate frame k (what the A-roll branch shows, without roto,
    chest or captions) + its matte (float 0..1, framed the same way). Only computed for NEEDS_AROLL templates."""
    sid = s["id"]; cx, cy, fh = smooth_face(TL, sid, k)
    g = np.asarray(TL.gain.get(sid, 1.0), np.float32)
    img = grade(np.clip(P * g, 0, 1) if np.any(g != 1) else P, A, (cx, cy), TL.S.get("grade"))
    z = TL.zoom.get(sid, 1.0) * (1 + TL.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
    if TL.snap and TL.snap[0] <= t < TL.snap[1]: z = TL.snap[2]
    M = affine(z, cx, H if sid in TL.lift else cy - fh * .05, True)
    return warp(img, M, cv2.INTER_CUBIC), warp(A.astype(np.float32) / 255, M)

def smooth_face(TL, sid, k, r=6):
    """face centre smoothed over +-r frames (no punch-in shake, MOT-03)"""
    F = TL.faces[sid]; lo, hi = max(0, k - r), min(len(F), k + r + 1)
    xs = [F[j][0] + F[j][2] / 2 for j in range(lo, hi)]; ys = [F[j][1] + F[j][3] / 2 for j in range(lo, hi)]; hs = [F[j][3] for j in range(lo, hi)]
    return float(np.mean(xs)), float(np.mean(ys)), float(np.mean(hs))

def trans_strength(TL, t):
    for tb, kind in TL.trans:
        d = 0 if kind == "cut" else TL.S.get(f"transitions.{kind}_s", .12)
        if d and abs(t - tb) < d: return kind, 1 - abs(t - tb) / d, t >= tb
    return None, 0, False

def log_records(i, els, M):
    out = []
    for el in els:
        post = isinstance(el, tuple); el = el[0] if post else el
        a = np.asarray(el.im)[..., 3]; ys, xs = np.where(a > 20)
        if not len(xs): continue
        x0, y0, x1, y1 = float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())
        if not post:     # element was drawn before the frame transform (roto / cutaway drift)
            x0, y0 = M[0, 0] * x0 + M[0, 2], M[1, 1] * y0 + M[1, 2]; x1, y1 = M[0, 0] * x1 + M[0, 2], M[1, 1] * y1 + M[1, 2]
        out.append({"f": i, "id": el.id, "role": el.role, "bbox": [round(x0), round(y0), round(x1), round(y1)], "alpha": round(float(a.max()) / 255, 2),
                    "text": el.text, "t_key": el.t_key, "asset": el.asset, "font": el.font})
    return out

# ------------------------------------------------------------------ jobs
def _decode(path, fmt):
    import av
    for f in av.open(path).decode(video=0): yield f.to_ndarray(format=fmt)

def _write(TL, out_dir, i, img, logf):
    t = i / TL.FPS
    if img.shape[2] == 4:
        out = np.clip(img * 255 + .5, 0, 255).astype(np.uint8); cv2.imwrite(f"{out_dir}/{i:05d}.png", cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA), [cv2.IMWRITE_PNG_COMPRESSION, 1]); return
    if TL.in_cut(t) or t >= TL.T_END: img = img + np.random.default_rng(i).uniform(-.5, .5, img.shape) / 255   # dither the gradient stage only
    out = np.clip(img * 255 + .5, 0, 255).astype(np.uint8)
    cv2.imwrite(f"{out_dir}/{i:05d}.png", cv2.cvtColor(out, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 1])

_TL = None
def _init(root):
    global _TL
    from .project import Project
    _TL = Timeline(Project(root))

def job_seg(sid, only, out_dir, mode):
    """one segment, streamed: plate/matte decoded a frame at a time, element records written as they come (O(1) RAM in length)"""
    TL = _TL; s = next(x for x in TL.segs if x["id"] == sid)
    frames = set(range(s["f0"], s["f0"] + s["n"])) if only is None else {f for f in only if s["f0"] <= f < s["f0"] + s["n"]}
    if not frames: return 0
    need = mode == "aroll" or any(not TL.in_cut(f / TL.FPS) or (TL.in_cut(f / TL.FPS) or {}).get("template") in NEEDS_AROLL for f in frames)
    Pg = _decode(TL.pr.e("plate", f"{sid}.mkv"), "rgb48le") if need else None
    Ag = _decode(TL.pr.e("matte", f"{sid}.mkv"), "gray") if need else None
    last = max(frames) - s["f0"]
    with open(os.path.join(out_dir, f"_log_{s['f0']:07d}_{sid}.jsonl"), "w", encoding="utf-8") as fh:
        for k in range(last + 1):
            P, A = (next(Pg), next(Ag)) if need else (None, None); i = s["f0"] + k
            if i not in frames: continue
            img, r = compose(TL, i, P.astype(np.float32) / 65535 if P is not None else None, A, k, mode)
            if img is not None: _write(TL, out_dir, i, img, None)
            for x in r: fh.write(json.dumps(x) + "\n")
    return len(frames)

def job_tail(only, out_dir, mode):
    TL = _TL; fr = range(TL.A_FRAMES, TL.N) if only is None else [f for f in only if f >= TL.A_FRAMES]
    with open(os.path.join(out_dir, f"_log_{TL.A_FRAMES:07d}_tail.jsonl"), "w", encoding="utf-8") as fh:
        for i in fr:
            img, r = compose(TL, i, mode=mode)
            if img is not None: _write(TL, out_dir, i, img, None)
            for x in r: fh.write(json.dumps(x) + "\n")
    return len(fr)

def render(pr, only=None, out_dir=None, mode="final", workers=None):
    """only: None (everything), a frame list, or an `--only` spec string (ids / ranges, see Timeline.frames_for).
    Streams: each worker decodes one segment a frame at a time and writes frames + element records straight to disk;
    nothing holds the timeline's frames or logs in RAM, so memory does not grow with the video's length."""
    out_dir = out_dir or pr.e("frames"); os.makedirs(out_dir, exist_ok=True)
    TL = Timeline(pr)    # also computes + caches exposure gains before forking
    if isinstance(only, str): only = TL.frames_for(only)
    from . import motion as MOT; MOT.prerender(pr, TL)     # motion pieces (HTML) render their frames ONCE here, before the spawn pool: workers only read the cache
    for f in glob.glob(os.path.join(out_dir, "_log_*.jsonl")): os.remove(f)
    want = None if only is None else set(only)
    jobs = [(s["id"], None if want is None else sorted(f for f in range(s["f0"], s["f0"] + s["n"]) if f in want))
            for s in sorted(TL.segs, key=lambda s: -s["n"])]
    jobs = [(sid, fr) for sid, fr in jobs if fr is None or fr]
    tail = None if want is None else sorted(f for f in want if f >= TL.A_FRAMES)
    with Pool(max(1, min(workers or max(2, (os.cpu_count() or 4) - 1), len(jobs) + 1)), initializer=_init, initargs=(pr.root,)) as pool:
        res = [pool.apply_async(job_seg, (sid, fr, out_dir, mode)) for sid, fr in jobs]
        if tail is None or tail: res.append(pool.apply_async(job_tail, (tail, out_dir, mode)))
        n = sum(r.get() for r in res)
    logs = sorted(glob.glob(os.path.join(out_dir, "_log_*.jsonl")))     # named by first frame: concatenation is in frame order
    if only is None and mode == "final":
        with open(pr.e("elements.jsonl"), "w", encoding="utf-8") as out:
            for f in logs:
                with open(f, encoding="utf-8") as fh:
                    for line in fh: out.write(line)
        pr.save_json("timeline.json", {"fps": TL.FPS, "fps_rational": list(TL.fps_rational), "size": list(TL.size), "frames": TL.N, "a_frames": TL.A_FRAMES, "zoom": TL.zoom, "lift": sorted(TL.lift), "snap": TL.snap, "creep": TL.creep,
                                       "cutaways": [{"id": c["id"], "start": c["start"], "end": c["end"], "template": c["template"]} for c in TL.cuts],
                                       "transitions": TL.trans, "exposure_gain": TL.gain,
                                       "segments": [{k: s[k] for k in ("id", "in", "out", "f0", "n", "t0", "t1")} for s in TL.segs]})
    for f in logs: os.remove(f)
    return n, TL.N
