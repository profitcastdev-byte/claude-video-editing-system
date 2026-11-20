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
from . import gfx as G, templates as TPL, style as STY, captions as CAP, spines as SP, craft as CR, shotmatch as SM
from .gfx import prog, clamp          # the canvas is G.W / G.H, read at call time (set per process by Timeline)
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
    def __init__(self, pr, proxy=None):
        """proxy: a fraction of the canvas (treatment proxies, docs/TREATMENTS.md): the timeline is planned and the exposure
        solved at full size, then the canvas and the face tracks are scaled; plates and mattes are resized as they decode"""
        self.pr = pr; E = pr.edit; self.E = E; self.proxy = None
        self.S = STY.load(pr); self.style = self.S
        G.apply_style(self.S, canvas=G.canvas_of(self.S, pr))              # the ONLY source of look (docs/STYLE.md) + the canvas (docs/FORMATS.md)
        TPL.load_dir(pr.p("Brand", "templates"), "project")                  # per-client templates, if any
        refresh_needs_aroll()
        self.spine = SP.spine_of(E); self.aroll = SP.has_aroll(self.spine)          # what drives the timeline (docs/FORMATS.md)
        edl = pr.json("edl.json")
        if not self.aroll and (not edl or edl.get("spine") != self.spine): edl = SP.sync_edl(pr, self.S)
        if not edl: raise SystemExit("Edit/edl.json missing: run `cves select` (A-roll) or `cves ingest` (voiceover / music / broll spines)")
        self.FPS = edl["fps"]; self.faces = pr.json("faces.json", {}) if self.aroll else {}
        G.FPS = self.FPS                                                     # cue / animation quantisation in templates (MOT-07)
        self.size = (G.W, G.H)                                                  # the frame canvas the renderer writes
        if edl.get("size") and tuple(edl["size"]) != self.size and edl.get("segments"):
            raise SystemExit(f"the canvas is {self.size[0]}x{self.size[1]} (style canvas.size) but the plates were made at {edl['size'][0]}x{edl['size'][1]}: "
                             "re-run `cves select` + `cves prep` (or set canvas.size back)")
        fr = edl.get("fps_rational"); self.fps_rational = tuple(fr) if fr else (Fraction(self.FPS).limit_denominator(1001).numerator, Fraction(self.FPS).limit_denominator(1001).denominator)
        self.broll = SP.shots(E, self.FPS, self.S, pr)                       # the broll: track, frame-snapped
        self.segs = []; f0 = 0
        if self.aroll:
            for s in edl["segments"]:
                n = round((s["out"] - s["in"]) * self.FPS); self.segs.append(dict(s, f0=f0, n=n, t0=f0 / self.FPS, t1=(f0 + n) / self.FPS, kind="aroll")); f0 += n
        else:                                                                # picture segments = the broll shots (+ gaps)
            self.segs = SP.tiles(self.broll, SP.duration(pr, self.spine, E), self.FPS, self.S); f0 = sum(s["n"] for s in self.segs)
        self.A_FRAMES = f0; self.T_END = f0 / self.FPS
        end = E.get("end_card") or {}; self.END = end.get("duration", 0)
        self.N = self.A_FRAMES + round(self.END * self.FPS)
        snapb = [s["t0"] for s in self.segs] + [self.T_END]
        self.snap_t = lambda t: min(snapb, key=lambda x: abs(x - t))
        self.cuts = []
        for c in E.get("cutaways", []):
            sn = c.get("snap", True)    # snap to segment boundaries (hides jump cuts); snap:false for a beat that starts mid-shot
            self.cuts.append(dict(c, start=self.snap_t(c["start"]) if sn else c["start"], end=self.snap_t(c["end"]) if sn else c["end"]))
        for c in SP.cutaways(self.broll, self.aroll):                       # after the drawn cutaways: those win where they overlap
            sn = c["snap"]
            self.cuts.append(dict(c, start=self.snap_t(c["start"]) if sn else c["start"], end=self.snap_t(c["end"]) if sn else c["end"]))
        self.trans = []
        for c in self.cuts:
            self.trans.append((c["start"], c.get("in", self.S.get("transitions.in", "cut")))); self.trans.append((c["end"], c.get("out", self.S.get("transitions.out", "cut"))))
        if self.END: self.trans.append((self.T_END, end.get("in", self.S.get("transitions.in", "cut"))))
        for tr in E.get("transitions", []): self.trans.append((self.snap_t(tr["t"]), tr["kind"]))
        self.craft_notes = CR.limit_transitions(self)                       # restraint: rate-limited transitions (docs/MOTION.md "Craft")
        self.roto = {r["segment"]: r for r in E.get("roto", [])} if self.aroll else {}     # roto / chest need a presenter
        self.matte_ok = {s["id"]: os.path.exists(pr.e("matte", f"{s['id']}.mkv")) for s in self.segs} if self.aroll else {}
        self.chest = {}
        for c in (E.get("chest", []) if self.aroll else []):
            for sid in ([c["segment"]] if isinstance(c["segment"], str) else c["segment"]): self.chest.setdefault(sid, []).append(c)
        ar = E.get("aroll", {}); self.creep = ar.get("creep", self.S.get("framing.creep", 0.0))
        sn = ar.get("snap"); self.snap = (sn["start"], sn["end"], sn["zoom"]) if sn else None
        self.zoom = self._auto_zoom(ar.get("zoom", {})) if self.aroll else {}
        if not self.aroll: self.lift = set()
        self.match = SM.solve(self) if self.aroll else {}          # per-shot colour match to a reference shot (COL-06/07)
        # the colour match includes exposure: the older skin-gain balance only runs when it is off
        self.gain = self._exposure() if self.aroll and not self.match and ar.get("exposure_match", self.S.get("grade.exposure_match", True)) else {}
        self.caps = self._captions()
        self.root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if proxy and float(proxy) != 1.0: self._to_proxy(float(proxy))

    def _to_proxy(self, k):
        """scale this timeline's canvas by k (even-rounded) for a fast proxy render. Called after the exposure solve, which
        measures the full-size plates. Every module reads G.W / G.H / G.U at call time, so templates follow."""
        w, h = self.size; pw, ph = max(16, int(round(w * k / 2)) * 2), max(16, int(round(h * k / 2)) * 2)
        G.set_canvas(pw, ph); self.size = (G.W, G.H); self.proxy = (pw / w, ph / h)
        sx, sy = self.proxy
        def sc(f):
            if not f: return f
            f = list(f)
            for j in range(min(len(f), 14)): f[j] = f[j] * (sx if j % 2 == 0 else sy)
            return f
        self.faces = {sid: [sc(f) for f in F] for sid, F in (self.faces or {}).items()}

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
        if cfg.get("events"): ev = [(e["start"], e["end"], [tuple(w) for w in e["words"]]) for e in cfg["events"]]
        elif not SP.has_voice(self.spine): return []                         # music / broll spines: text cards are cutaways
        else: ev = CAP.build(self.pr.json("words.json", []), cfg, self.T_END)
        self.cap_log = []                                                    # no fragment flashes round a cover (PLAT-06 / 07)
        return CAP.schedule(ev, self.cap_hidden, self.FPS, cfg, self.cap_log)

    def cap_hidden(self, f):
        """True where compose() surely draws no caption on frame f: a drawn cutaway (B-roll shots keep them), the snap over a
        roto segment, a captions.hide window, the end card. Chest graphics are not counted: they hide captions only on the
        frames they draw on, which only the render knows (a fragment there is left as it is)."""
        t = f / self.FPS
        if t >= self.T_END or any(a <= t < b for a, b in self.cap_hide): return True
        c = self.in_cut(t)
        if c and not c.get("broll"): return True
        if not (self.snap and self.snap[0] <= t < self.snap[1]): return False
        s = self.seg_at(f)
        return bool(s is not None and s["id"] in self.roto)

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
    if clamp_cover: tx = min(0, max(G.W - s * G.W, tx)); ty = min(0, max(G.H - s * G.H, ty))
    return np.float32([[s, 0, tx], [0, s, ty]])

def warp(img, M, interp=cv2.INTER_LINEAR):
    if abs(M[0, 0] - 1) < 1e-4 and abs(M[0, 2]) < .01 and abs(M[1, 2]) < .01: return img
    return cv2.warpAffine(img, M, (G.W, G.H), flags=interp, borderMode=cv2.BORDER_REPLICATE)

def zoom_blur(img, e, cx=None, cy=None, n=6):
    """radial (zoom) blur for whips: average of progressively scaled copies (the house spec calls for zoom-blur)"""
    if e <= .02: return img
    cx = G.W / 2 if cx is None else cx; cy = G.H * .4 if cy is None else cy
    acc = img.copy()
    for k in range(1, n):
        acc += warp(img, affine(1 + .06 * e * k, cx, cy, False))
    return acc / n

def glitch(img, e, seed):
    if e <= 0: return img
    rng = random.Random(seed); out = img.copy()
    for _ in range(int(6 + 14 * e)):
        y0 = rng.randrange(0, G.H - 10); hh = rng.randrange(6, int((20 + 120 * e) * G.U) or 7); dx = int(rng.uniform(-1, 1) * 160 * e * G.U)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], dx, axis=1)
    sh = int(14 * e) + 1
    out[..., 0] = np.roll(out[..., 0], sh, axis=1); out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    lines = (np.arange(G.H) % 4 < 1)[:, None, None].astype(np.float32)
    return np.clip(out * (1 - .25 * e * lines) + np.array([.1, .9, .6], np.float32) * .12 * e * lines, 0, 1)

def caption_el(TL, t, chin, frame=None):
    if any(a <= t < b for a, b in getattr(TL, "cap_hide", [])): return None
    S = STY.Style({**TL.S, "captions": TL.cap_cfg})
    return CAP.element(TL, t, chin, TL.caps, S, frame=frame)

# ------------------------------------------------------------------ frame composition
def compose(TL, i, P=None, A=None, k=0, mode="final"):
    """mode: final (everything) | aroll (graded A-roll + roto, no captions/chest) | overlay (chest + captions on transparent) | chest (chest graphics only, transparent)"""
    t = i / TL.FPS; s = TL.seg_at(i); cut = TL.in_cut(t); els = []; M = np.float32([[1, 0, 0], [0, 1, 0]])
    if t >= TL.T_END:
        e = TL.E["end_card"]; fn = TPL.get(e["template"])[0]
        els = fn(t, e.get("params", {}), TL.ctx(TL.T_END, TL.T_END + TL.END))
        img = G.stage().copy()
        for el in els: img = G.over(img, el.im, inplace=True)
        sc = 1 + TL.S.get('motion.drift', .025) * clamp((t - TL.T_END) / 6); M = affine(sc, G.W / 2, G.H * .46875, False); img = warp(img, M)
    elif cut and mode != "aroll":
        fn = TPL.get(cut["template"])[0]; cx_ = TL.ctx(cut["start"], cut["end"])
        if cut["template"] in NEEDS_AROLL and P is not None and s is not None:     # media templates (pip, split)
            cx_["aroll"] = aroll_frame(TL, s, k, t, P, A)
        els = fn(t, cut.get("params", {}), cx_)
        img = G.stage().copy()
        for el in els: img = G.over(img, el.im, inplace=True)
        if not cut.get("broll"):          # B-roll shots frame themselves (fill / fit / ken burns): no stage drift
            sc = 1 + TL.S.get('motion.drift', .025) * clamp((t - cut["start"]) / 6); M = affine(sc, G.W / 2, G.H * .46875, False); img = warp(img, M)
        if mode in ("overlay", "chest"): img = None
        if cut.get("broll") and mode in ("final", "overlay"): img, els = _caption_front(TL, t, img, els)
    elif s is not None and s.get("kind") in ("broll", "gap"):              # non-aroll timeline: a frame no shot covers, or the
        img = G.stage().copy() if mode not in ("overlay", "chest") else None    # V1 picture pass (mode aroll) of a B-roll shot
        sh = next((c for c in TL.cuts if c.get("broll") and c["id"] == s["id"]), None) if mode == "aroll" and s.get("kind") == "broll" else None
        if sh is not None:
            els = TPL.get(sh["template"])[0](t, sh.get("params", {}), TL.ctx(sh["start"], sh["end"]))
            for el in els: img = G.over(img, el.im, inplace=True)
        if mode in ("final", "overlay"): img, els = _caption_front(TL, t, img, els)
    else:
        sid = s["id"]; f = TL.faces[sid][min(k, len(TL.faces[sid]) - 1)]
        sm = smooth_face(TL, sid, k)
        cx, cy, fh = sm
        z = TL.zoom.get(sid, 1.0) * (1 + TL.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
        if TL.snap and TL.snap[0] <= t < TL.snap[1]: z = TL.snap[2]
        M = affine(z, cx, G.H if sid in TL.lift else cy - fh * .05, True)    # lift: anchor at the frame bottom raises the face
        z0 = TL.zoom.get(sid, 1.0) * (1 + TL.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
        M0 = M if z0 == z else affine(z0, cx, G.H if sid in TL.lift else cy - fh * .05, True)    # the shot's framing without a snap
        if TL.snap and TL.snap[0] < s["t1"] and s["t0"] < TL.snap[1]:     # a snap punch-in in this shot: roto type fits the tighter view
            Ms = affine(max(z0, TL.snap[2]), cx, G.H if sid in TL.lift else cy - fh * .05, True); M0 = Ms if Ms[0, 0] > M0[0, 0] else M0
        if mode in ("overlay", "chest"): img = None
        else:
            img = grade(_matched(TL, sid, k, P, A), A, (cx, cy), TL.S.get("grade"))
            r = TL.roto.get(sid)
            if r:
                rels = TPL.get(r["template"])[0](t, r.get("params", {}), TL.ctx(s["t0"], s["t1"], view=M, seg_view=M0, plate_lum=lambda ks, s=s: plate_lum(TL, s, ks), **CR.roto_ctx(TL, s, k)))
                if rels:
                    a = cv2.GaussianBlur(cv2.erode(A.astype(np.float32) / 255, np.ones((3, 3), np.uint8)), (0, 0), 1.2)[..., None]
                    person = img.copy()
                    for el in rels: img = G.over(img, el.im, inplace=True)
                    img = img * (1 - a) + person * a; els += rels
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
            snapped = TL.snap and TL.snap[0] <= t < TL.snap[1] and sid in TL.roto   # the snap's roto type replaces the captions; a bare punch-in keeps them
            if not front and not snapped and mode != "chest":     # chest mode: graphics only, captions go to subtitles
                ce = caption_el(TL, t, cap_chin, frame=img)
                if ce: front.append(ce)
            if img is None: img = np.zeros((G.H, G.W, 4), np.float32); ov = True
            else: ov = False
            for el in front:
                if ov:
                    a = np.asarray(el.im, np.float32) / 255; al = a[..., 3:4]
                    img[..., :3] = img[..., :3] * (1 - al) + a[..., :3] * al; img[..., 3:4] = img[..., 3:4] * (1 - al) + al
                else: img = G.over(img, el.im, inplace=True)
            els += [(el, "post") for el in front]
    if mode == "final" and img is not None:
        kind, e, after = trans_strength(TL, t)
        if kind == "whip":
            z = 1 + (.22 if after else .35) * e ** 1.5; img = zoom_blur(warp(img, affine(z, G.W / 2, G.H * .4, False)), e ** 1.2)
        elif kind == "glitch": img = glitch(img, e, i)
        elif kind == "fade": img = img * (1 - e)          # dip through black
        elif kind in CR.TRANSITIONS:                         # the craft library (style craft.transitions.*)
            mt = None
            if kind == "mask_wipe" and A is not None and cut is None and s is not None and s.get("kind", "aroll") == "aroll" and TL.S.get("craft.transitions.wipe_shape") == "matte":
                mt = warp(A.astype(np.float32) / 255, M)
            img = CR.transition(kind, img, e, after, CR.seed_of(kind, round(CR.boundary(TL, t), 4)), TL.S, mt)
    return img, log_records(i, els, M)

def _caption_front(TL, t, img, els):
    """captions over a frame with no presenter (B-roll, gaps): low in the safe zone; img None = a transparent overlay"""
    ce = caption_el(TL, t, None, frame=img)
    if ce is None: return img, els
    if img is None:
        img = np.zeros((G.H, G.W, 4), np.float32); a = np.asarray(ce.im, np.float32) / 255; al = a[..., 3:4]
        img[..., :3] = a[..., :3] * al; img[..., 3:4] = al
    else: img = G.over(img, ce.im, inplace=True)
    return img, els + [(ce, "post")]

def _matched(TL, sid, k, P, A=None):
    """the plate as the grade receives it: colour-matched to the reference shot (grade.shot_match), else exposure-balanced"""
    if TL.match: return SM.apply(TL.match, sid, k, P, A)
    g = np.asarray(TL.gain.get(sid, 1.0), np.float32)
    return np.clip(P * g, 0, 1) if np.any(g != 1) else P

def aroll_frame(TL, s, k, t, P, A):
    """the graded, framed A-roll frame of segment s at plate frame k (what the A-roll branch shows, without roto,
    chest or captions) + its matte (float 0..1, framed the same way). Only computed for NEEDS_AROLL templates."""
    sid = s["id"]; cx, cy, fh = smooth_face(TL, sid, k)
    img = grade(_matched(TL, sid, k, P, A), A, (cx, cy), TL.S.get("grade"))
    z = TL.zoom.get(sid, 1.0) * (1 + TL.creep * clamp((t - s["t0"]) / max(.5, s["t1"] - s["t0"])))
    if TL.snap and TL.snap[0] <= t < TL.snap[1]: z = TL.snap[2]
    M = affine(z, cx, G.H if sid in TL.lift else cy - fh * .05, True)
    return warp(img, M, cv2.INTER_CUBIC), warp(A.astype(np.float32) / 255, M)

def plate_lum(TL, s, ks):
    """[(k, relative luminance HxW float32, subject matte HxW float 0..1)] of segment s at plate frames ks: the graded plate
    as the A-roll branch shows it before the frame transform (plate px). Roto templates measure the wall behind them with it
    (text_behind color: auto) and find free space beside the head (roto card placement). Decoded on demand; callers cache
    what they decide from it, so every worker decides the same."""
    import av
    sid = s["id"]; n = max(1, int(s["n"])); ks = sorted(set(min(max(0, int(k)), n - 1) for k in ks))
    if not ks: return []
    def grab(path, fmt):
        got = {}
        with av.open(path) as c:
            for j, fr in enumerate(c.decode(video=0)):
                if j > ks[-1]: break
                if j in ks: got[j] = fr.to_ndarray(format=fmt)
        return got
    P = grab(TL.pr.e("plate", f"{sid}.mkv"), "rgb48le")
    A = grab(TL.pr.e("matte", f"{sid}.mkv"), "gray") if TL.matte_ok.get(sid, True) else {}
    out = []
    for k in ks:
        if k not in P: continue
        p_ = P[k].astype(np.float32) / 65535; a_ = A.get(k)
        if a_ is None: a_ = np.zeros(p_.shape[:2], np.uint8)
        if TL.proxy: p_ = cv2.resize(p_, TL.size, interpolation=cv2.INTER_AREA); a_ = cv2.resize(a_, TL.size, interpolation=cv2.INTER_AREA)
        cx, cy, _ = smooth_face(TL, sid, k)
        g = np.asarray(TL.gain.get(sid, 1.0), np.float32)
        img = np.clip(grade(np.clip(p_ * g, 0, 1) if np.any(g != 1) else p_, a_, (cx, cy), TL.S.get("grade")), 0, 1)
        lin = np.where(img <= .04045, img / 12.92, ((img + .055) / 1.055) ** 2.4)
        out.append((k, (lin @ np.float32([.2126, .7152, .0722])).astype(np.float32), a_.astype(np.float32) / 255))
    return out

def smooth_face(TL, sid, k, r=6):
    """face centre smoothed over +-r frames (no punch-in shake, MOT-03)"""
    F = TL.faces[sid]; lo, hi = max(0, k - r), min(len(F), k + r + 1)
    xs = [F[j][0] + F[j][2] / 2 for j in range(lo, hi)]; ys = [F[j][1] + F[j][3] / 2 for j in range(lo, hi)]; hs = [F[j][3] for j in range(lo, hi)]
    return float(np.mean(xs)), float(np.mean(ys)), float(np.mean(hs))

def trans_strength(TL, t):
    for tb, kind in TL.trans:
        d = CR.trans_dur(TL.S, kind)
        if d and abs(t - tb) < d: return kind, 1 - abs(t - tb) / d, t >= tb
    return None, 0, False

_GT20 = [0] * 21 + [255] * 235

def _alpha_box(im):
    """(box of alpha > 20 as inclusive (x0, y0, x1, y1), max alpha 0..255) or (None, max): PIL in C, else numpy"""
    if isinstance(im, Image.Image) and im.mode == "RGBA":
        b0 = im.getbbox()                                         # alpha > 0: everything else is on the clear canvas
        if b0 is None: return None, 0.0
        al = im.crop(b0).getchannel("A"); mx = al.getextrema()[1]
        bb = al.point(_GT20).getbbox() if mx > 20 else None
        return (None if bb is None else (float(b0[0] + bb[0]), float(b0[1] + bb[1]), float(b0[0] + bb[2] - 1), float(b0[1] + bb[3] - 1))), float(mx)
    a = np.asarray(im)[..., 3]; ys, xs = np.where(a > 20)
    if not len(xs): return None, float(a.max())
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())), float(a.max())

def log_records(i, els, M):
    out = []
    for el in els:
        post = isinstance(el, tuple); el = el[0] if post else el
        box, amax = _alpha_box(el.im)
        if box is None: continue
        x0, y0, x1, y1 = box
        if not post:     # element was drawn before the frame transform (roto / cutaway drift)
            x0, y0 = M[0, 0] * x0 + M[0, 2], M[1, 1] * y0 + M[1, 2]; x1, y1 = M[0, 0] * x1 + M[0, 2], M[1, 1] * y1 + M[1, 2]
        out.append({"f": i, "id": el.id, "role": el.role, "bbox": [round(x0), round(y0), round(x1), round(y1)], "alpha": round(amax / 255, 2),
                    "text": el.text, "t_key": el.t_key, "asset": el.asset, "font": el.font, **({"size": el.size} if getattr(el, "size", None) else {})})
    return out

# ------------------------------------------------------------------ jobs
def _decode(path, fmt, start=0):
    """plate / matte frames from frame `start` on, converted to ndarrays. FFV1 plates are GOP-coded (keyframe every
    12 frames): the decoder seeks to the keyframe at or before `start` and decodes forward, so a chunk of a segment
    costs its own frames, not the whole segment before it; a container that cannot seek is decoded from frame 0."""
    for f in _frames_from(path, start): yield f.to_ndarray(format=fmt)

def _frames_from(path, start=0):
    """av.VideoFrame objects from frame index `start` on (frame index from the pts and the stream rate)"""
    import av
    c = av.open(path); vs = c.streams.video[0]
    if start > 0:
        rate = float(vs.average_rate or vs.guessed_rate or 0); tb = vs.time_base; st = vs.start_time or 0
        idx = lambda f: round(float((f.pts - st) * tb) * rate)
        ok, it, first = False, None, None
        if rate > 0 and tb:
            try:
                c.seek(int(st + start / rate / tb), stream=vs, backward=True)      # the keyframe at or before `start`
                it = c.decode(vs); first = next(it, None)
                ok = first is not None and first.pts is not None and idx(first) <= start
            except (av.error.FFmpegError, ValueError, TypeError):
                ok = False
        if ok:
            if idx(first) == start: yield first
            for f in it:
                if idx(f) >= start: yield f
            return
        c.close(); c = av.open(path); vs = c.streams.video[0]          # cannot seek: decode from the start, skip to `start`
        for j, f in enumerate(c.decode(vs)):
            if j >= start: yield f
        return
    yield from c.decode(vs)

def _write(TL, out_dir, i, img, logf):
    t = i / TL.FPS
    if img.shape[2] == 4: _put(f"{out_dir}/{i:05d}.png", img, True, None); return
    c = TL.in_cut(t); s = TL.seg_at(i)
    dith = (c and not c.get("broll")) or t >= TL.T_END or (not c and s is not None and s.get("kind") == "gap")   # dither the gradient stage only
    _put(f"{out_dir}/{i:05d}.png", img, False, i if dith else None)

def _png(path, img, rgba, seed):
    """float frame -> 8-bit PNG (runs on the writer thread: numpy, cv2 and the file write release the GIL)"""
    if seed is not None: img = img + np.random.default_rng(seed).uniform(-.5, .5, img.shape) / 255
    out = np.clip(img * 255 + .5, 0, 255).astype(np.uint8)
    if not cv2.imwrite(path, cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA if rgba else cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 1]):
        raise OSError(f"could not write {path} (disk full?)")

_WRITER, _PENDING = None, []

def _put(path, img, rgba, seed):
    """quantise + PNG-encode + write a frame on a background thread while the next frame composes (same bytes as writing
    it inline; at most 3 frames in flight). _flush() waits for them: a job returns only once its frames are on disk."""
    global _WRITER
    if _WRITER is None:
        from concurrent.futures import ThreadPoolExecutor
        _WRITER = ThreadPoolExecutor(1, thread_name_prefix="cves-png")
    _PENDING.append(_WRITER.submit(_png, path, img, rgba, seed))
    while len(_PENDING) > 3: _PENDING.pop(0).result()

def _flush():
    while _PENDING: _PENDING.pop(0).result()

_TL = None
def _init(root, work=None, proxy=None):
    """worker initializer. spawn re-imports every module, so the canvas (gfx.set_canvas) and the style are re-applied here
    by Timeline: never rely on the parent's module state. work: a Variant's folder (treatments); proxy: canvas fraction"""
    global _TL
    from .project import reopen
    _TL = Timeline(reopen(root, work), proxy=proxy)

def canvas_of_worker():
    """(G.W, G.H) as this process sees it (tests: the canvas is re-set inside spawned workers)"""
    return (G.W, G.H)

def job_seg(sid, only, out_dir, mode):
    """one segment (or a chunk of it), streamed: plate/matte decoded a frame at a time from the chunk's first frame,
    converted only for frames that show the A-roll, element records written as they come (O(1) RAM in length)"""
    TL = _TL; s = next(x for x in TL.segs if x["id"] == sid)
    frames = set(range(s["f0"], s["f0"] + s["n"])) if only is None else {f for f in only if s["f0"] <= f < s["f0"] + s["n"]}
    if not frames: return 0
    uses = lambda f: mode == "aroll" or not TL.in_cut(f / TL.FPS) or (TL.in_cut(f / TL.FPS) or {}).get("template") in NEEDS_AROLL
    need = s.get("kind", "aroll") == "aroll" and any(uses(f) for f in frames)
    first, last = min(frames) - s["f0"], max(frames) - s["f0"]
    Pg = _frames_from(TL.pr.e("plate", f"{sid}.mkv"), first) if need else None
    Ag = (_frames_from(TL.pr.e("matte", f"{sid}.mkv"), first) if TL.matte_ok.get(sid, True) else None) if need else None   # no matte: degrade (roto in front)
    def arr(fr, fmt):
        if fr is None: return np.zeros((G.H, G.W), np.uint8)
        x = fr.to_ndarray(format=fmt)
        return cv2.resize(x, TL.size, interpolation=cv2.INTER_AREA) if TL.proxy else x   # proxy: the full-size plate / matte, resized as it decodes
    with open(os.path.join(out_dir, f"_log_{min(frames):07d}_{sid}.jsonl"), "w", encoding="utf-8") as fh:
        for k in range(first, last + 1):
            pf, af = (next(Pg), next(Ag) if Ag is not None else None) if need else (None, None); i = s["f0"] + k
            if i not in frames: continue
            P, A = (arr(pf, "rgb48le"), arr(af, "gray")) if need and uses(i) else (None, None)
            img, r = compose(TL, i, P.astype(np.float32) / 65535 if P is not None else None, A, k, mode)
            if img is not None: _write(TL, out_dir, i, img, None)
            for x in r: fh.write(json.dumps(x) + "\n")
    _flush()
    return len(frames)

def job_tail(only, out_dir, mode):
    TL = _TL; fr = range(TL.A_FRAMES, TL.N) if only is None else [f for f in only if f >= TL.A_FRAMES]
    if not fr: return 0
    with open(os.path.join(out_dir, f"_log_{min(fr):07d}_tail.jsonl"), "w", encoding="utf-8") as fh:
        for i in fr:
            img, r = compose(TL, i, mode=mode)
            if img is not None: _write(TL, out_dir, i, img, None)
            for x in r: fh.write(json.dumps(x) + "\n")
    _flush()
    return len(fr)

def media_refs(TL):
    """every asset reference (id or path) the timeline's templates decode: `asset:` keys anywhere in their params"""
    out = []
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "asset" and isinstance(v, str): out.append(v)
                else: walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    for c in TL.cuts: walk(c.get("params") or {})
    for k in ("chest", "roto"):
        for r in (TL.E.get(k) or []) if hasattr(TL, "E") else []: walk(r.get("params") or {})
    return sorted(set(out))

def prepare_media(pr, TL):
    """tonemap HDR video assets to SDR (ingest.sdr_source, the A-roll chain) before the workers start"""
    from . import assets as AS, ingest as ING
    from .templates.media import _is_still
    for ref in media_refs(TL):
        try: p = AS.resolve(pr, ref, strict=False) or (ref if os.path.isabs(ref) else pr.p(ref))
        except SystemExit: continue
        if p and os.path.isfile(p) and not _is_still(p): ING.sdr_source(p, TL.S, pr.e("conform"))

def _chunks(TL, want, workers):
    """[(segment id | None for the end card, [frames])]: every segment's wanted frames in contiguous chunks of about
    1/4 of a worker's share (>= render.chunk_min frames), longest first. A whole segment per job left the pool waiting on
    the longest shot; plates seek to a chunk's first frame (_frames_from), so a chunk costs only its own frames."""
    per = max(int(TL.S.get("render.chunk_min", 24) or 24), -(-len(want) // max(1, workers * 4)))
    out = []
    for sid, lo, hi in [(s["id"], s["f0"], s["f0"] + s["n"]) for s in TL.segs] + [(None, TL.A_FRAMES, TL.N)]:
        fr = sorted(f for f in want if lo <= f < hi)
        runs, cur = [], []
        for f in fr:
            if cur and (f - cur[-1] > 12 or len(cur) >= per): runs.append(cur); cur = []      # a short gap is decoded through (GOP)
            cur.append(f)
        if cur: runs.append(cur)
        out += [(sid, r) for r in runs]
    return sorted(out, key=lambda j: -len(j[1]))

LAST = {}          # what the last render() did: {"frames": rendered, "of": N, "cached": kept from the frame cache} (cves build prints it)

def render(pr, only=None, out_dir=None, mode="final", workers=None, proxy=None, cache=None, draft=False):
    """only: None (everything), a frame list, or an `--only` spec string (ids / ranges, see Timeline.frames_for).
    proxy: a canvas fraction (e.g. 0.5) for a fast preview render (treatments); timeline.json then records `proxy`.
    cache: incremental render (rcache, default style `render.cache`): a full final render re-renders only the frames whose
    inputs changed and rebuilds the element log from the kept frames' records; the result equals a full render.
    draft: timeline.json records `draft: true` (`cves build --draft`; delivery refuses it).
    Streams: each worker decodes one segment a frame at a time and writes frames + element records straight to disk;
    nothing holds the timeline's frames or logs in RAM, so memory does not grow with the video's length."""
    from . import rcache as RC
    out_dir = out_dir or pr.e("frames"); os.makedirs(out_dir, exist_ok=True)
    TL = Timeline(pr, proxy=proxy)    # also computes + caches exposure gains before forking
    if isinstance(only, str): only = TL.frames_for(only)
    for n in TL.craft_notes: print(f"craft: {n}")
    used, allowed = CR.budget(TL.E, TL.S, TL.N / TL.FPS)
    if used > allowed: print(f"craft: {used} craft moves (ramps, camera moves, match cuts, text behind) > creative.craft_per_30s budget {allowed}: restraint")
    full = only is None and mode == "final"
    index = full and (cache is True or RC.enabled(TL.S))          # keep a frame cache index for this frames folder
    use_cache = index and cache is not False                       # ... and reuse the frames it vouches for (--no-cache: refresh only)
    log_path = pr.e("elements.jsonl"); keys = kept = None
    if index: keys = RC.frame_keys(TL, mode)
    if use_cache:
        have = RC.load(out_dir, log_path)
        kept = {i for i in range(TL.N) if have.get(i) == keys[i]}
        only = [i for i in range(TL.N) if i not in kept]
        RC.save(out_dir, {i: keys[i] for i in kept}, log_path)      # invalidate first: a crash mid-render never leaves a stale key
    elif full:
        RC.save(out_dir, None, log_path)                             # every frame is rendered again: no key may outlive it
    elif os.path.abspath(out_dir) == os.path.abspath(pr.e("frames")) and only is not None:
        RC.drop(out_dir, only)                                       # --only rewrote these PNGs but not the element log
    elif os.path.abspath(out_dir) == os.path.abspath(pr.e("frames")) and mode != "final":
        RC.save(out_dir, None, log_path)
    if only is None or only:
        from . import motion as MOT; MOT.prerender(pr, TL)     # motion pieces (HTML) render their frames ONCE here, before the spawn pool: workers only read the cache
        prepare_media(pr, TL)                                   # HDR B-roll / clips tonemapped to SDR once here, not raced by the workers
    for f in glob.glob(os.path.join(out_dir, "_log_*.jsonl")): os.remove(f)
    want = set(range(TL.N)) if only is None else set(only)
    nw = max(1, workers or int(os.environ.get("CVES_RENDER_WORKERS", "0") or 0) or max(2, (os.cpu_count() or 4) - 1))   # env cap: parallel test runs on small CI runners
    jobs = _chunks(TL, want, nw)
    n = 0
    if jobs:
        with Pool(max(1, min(nw, len(jobs))), initializer=_init, initargs=(pr.root, getattr(pr, "work", None), proxy)) as pool:
            res = [pool.apply_async(job_tail if sid is None else job_seg, ((fr,) if sid is None else (sid, fr)) + (out_dir, mode)) for sid, fr in jobs]
            n = sum(r.get() for r in res)
    logs = sorted(glob.glob(os.path.join(out_dir, "_log_*.jsonl")))     # named by first frame: concatenation is in frame order
    LAST.clear(); LAST.update(frames=n, of=TL.N, cached=len(kept or ()))
    if full:
        for f in os.listdir(out_dir):                        # a shorter timeline: no stale frames past the end for the encoder
            if f.endswith(".png") and f[:-4].isdigit() and int(f[:-4]) >= TL.N: os.remove(os.path.join(out_dir, f))
        if use_cache:
            old = RC.old_records(log_path, kept)
            new = {}
            for f in logs:
                with open(f, encoding="utf-8") as fh:
                    for line in fh: new.setdefault(json.loads(line)["f"], []).append(line)
            body = "".join(l for i in range(TL.N) for l in (old.get(i) if i in kept else new.get(i, [])))
            _write_if_changed(log_path, body, force=n > 0)
        else:
            with open(log_path, "w", encoding="utf-8") as out:
                for f in logs:
                    with open(f, encoding="utf-8") as fh:
                        for line in fh: out.write(line)
        tl = {"spine": TL.spine, "fps": TL.FPS, "fps_rational": list(TL.fps_rational), "size": list(TL.size), "frames": TL.N, "a_frames": TL.A_FRAMES, "zoom": TL.zoom, "lift": sorted(TL.lift), "snap": TL.snap, "creep": TL.creep,
              "cutaways": [dict({"id": c["id"], "start": c["start"], "end": c["end"], "template": c["template"]}, **({"broll": True} if c.get("broll") else {})) for c in TL.cuts],
              "transitions": TL.trans, "exposure_gain": TL.gain,
              "shot_match": {"reference": (TL.pr.json("shot_match.json", {}) or {}).get("reference"), "shots": sorted(TL.match)} if TL.match else None, **({"proxy": list(TL.proxy)} if TL.proxy else {}),
              **({"draft": True} if draft else {}),
              "segments": [{k: s.get(k) for k in ("id", "in", "out", "f0", "n", "t0", "t1", "kind")} for s in TL.segs]}
        _write_if_changed(pr.e("timeline.json"), json.dumps(tl, indent=1), force=n > 0 or not use_cache)
        if index: RC.save(out_dir, {i: keys[i] for i in range(TL.N)}, log_path)
    for f in logs: os.remove(f)
    return n, TL.N

def _write_if_changed(path, text, force=False):
    """rewrite only when the content changed (or force): an untouched element log / timeline keeps its mtime, so caches
    keyed on it (mix cue_sync) stay valid when nothing was re-rendered"""
    if not force and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == text: return False
    with open(path, "w", encoding="utf-8") as fh: fh.write(text)
    return True
