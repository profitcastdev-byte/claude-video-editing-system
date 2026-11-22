"""Per-shot colour match (style `grade.shot_match`, docs/STYLE.md "grade"): every A-roll shot is matched to a reference
shot in linear light before the look is applied, so a cut between takes recorded minutes apart under drifting room
light does not jump (skin / wall dE, skin Y).

`grade.exposure_match` balanced skin exposure only (one gain per shot, plus a 6 % per-channel trim). It cannot fix a wall
that changed colour while the skin did not, nor light that drifts inside a shot. This module measures two things on the
plate, the same two measures on the master:

  * skin: the two cheek patches between eye and mouth corner (YuNet landmarks, faces.json), each summarised by its own
    median and then averaged (side light puts the cheeks 40-80 Y apart; a pooled median flips between them);
  * wall: background pixels (matte alpha ~ 0) 50-130 px out from the silhouette and above the eye line, borders excluded:
    the same wall round the head in every take.

For every sampled frame (every `grade.shot_match_step_f` frames, plus the first / last visible frames of the shot) the
correction is a per-channel gain in linear light for the SUBJECT (its skin onto the reference's skin) and one for the
BACKGROUND (its wall onto the reference's wall), applied through the matte. Between takes the face and the wall do not
drift together (the presenter moves through the window light while the wall stays put, or the other way round): one
gain for the frame matched one and broke the other, and a gain + offset fit on two anchors at about the same level (a
pale wall behind the face) is ill-conditioned and lifts or crushes the blacks. The two gains never differ by more than
`shot_match_split_max` (log) per channel, so the subject never looks cut out of its room, and both are clamped to
`shot_match_gain_range`. Each shot gets its median correction onto the reference plus `shot_match_drift` x the
correction of each sample onto the shot's own median, median-filtered (landmark glitches) and smoothed with a Gaussian of
`shot_match_smooth_s` seconds: a slow drift of the room light is followed, a head turn is not chased (that would pump
the exposure). `shot_match_strength` blends toward identity. The reference is `grade.shot_match_reference`: `median`
(the visible shot closest to the median of all shots: the least correction overall), `hook` (the first A-roll shot on
screen) or a segment id.

Cached in Edit/shot_match.json with the signature of what it was solved for. `apply()` is two per-channel LUTs blended by the matte."""
import os, json, math
import numpy as np, cv2

VERSION = 2


def eotf(x):
    """sRGB / BT.709 display value -> linear light (the transfer cv2's Lab assumes)"""
    x = np.asarray(x, np.float64)
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)

def oetf(y):
    y = np.clip(np.asarray(y, np.float64), 0, 1)
    return np.where(y <= .0031308, y * 12.92, 1.055 * y ** (1 / 2.4) - .055)


def cfg_of(S):
    g = S.get("grade") or {}
    return {"on": _on(g.get("shot_match", True)), "strength": float(g.get("shot_match_strength", 1.0)),
            "reference": str(g.get("shot_match_reference", "hook")), "smooth_s": float(g.get("shot_match_smooth_s", 0.8)),
            "drift": float(g.get("shot_match_drift", 0.5)), "step_f": max(1, int(g.get("shot_match_step_f", 4))),
            "gain_range": [float(v) for v in (g.get("shot_match_gain_range") or [0.7, 1.45])],
            "split_max": float(g.get("shot_match_split_max", 0.18))}

def _on(v):
    return v is True or str(v).strip().lower() in ("true", "on", "yes", "1")


# ------------------------------------------------------------------ measurement
def skin_rgb(rgb, f):
    """mean of the two cheek patches' median display RGB (0..1), or None"""
    if f is None or len(f) < 14 or not any(f[4:14]): return None
    lm = np.array(f[4:14], float).reshape(5, 2); k = max(4, int(f[2] * .05)); h, w = rgb.shape[:2]; out = []
    for eye, mouth in ((lm[0], lm[3]), (lm[1], lm[4])):
        cx, cy = eye * .55 + mouth * .45; x0, y0 = int(cx) - k, int(cy) - k
        if x0 < 0 or y0 < 0 or x0 + 2 * k > w or y0 + 2 * k > h: return None
        out.append(np.median(rgb[y0:y0 + 2 * k, x0:x0 + 2 * k].reshape(-1, 3), 0))
    return np.mean(out, 0)

def wall_rgb(rgb, alpha, f, near=50, far=130):
    """mean display RGB (0..1) of the wall round the head, or None. alpha: matte uint8 (or float 0..1). The patch,
    on the plate: background 50-130 px out from the silhouette (60-160 px on the master at the usual
    1.2x framing), above the eye line, frame borders excluded."""
    a = alpha.astype(np.float32) / (255 if alpha.dtype == np.uint8 else 1)
    h, w = a.shape[:2]; s = 2                                         # half resolution: plenty for a median
    sub = (a[::s, ::s] > .5).astype(np.uint8)
    d = cv2.distanceTransform(1 - sub, cv2.DIST_L2, 3) * s
    m = (d >= near) & (d <= far) & (a[::s, ::s] < .02)
    if f is not None and len(f) >= 4: m[int((f[1] + .4 * f[3]) / s):] = False         # above the eye line: the wall behind the head
    b = int(20 / s) + 1; m[:max(b, int(.03 * h / s))] = False; m[:, :b] = False; m[:, -b:] = False
    if m.sum() < 300: return None
    return rgb[::s, ::s][m].mean(0)


def gains(src, ref, gain_range=(0.7, 1.45), split_max=0.18):
    """(subject gain (3,), background gain (3,)) in linear light mapping src {skin, wall} onto ref {skin, wall}: the
    subject is matched by its skin, the background by its wall. Values are LINEAR rgb (3,) or None (a missing wall
    borrows the skin gain). Clamped to gain_range; the two never differ by more than split_max (log units) per channel,
    so the subject never looks cut out of its room."""
    lo, hi = np.log(gain_range[0]), np.log(gain_range[1])
    ls = np.clip(np.log(np.maximum(ref["skin"], 1e-6) / np.maximum(src["skin"], 1e-6)), lo, hi)
    lw = ls if src.get("wall") is None or ref.get("wall") is None else np.clip(np.log(np.maximum(ref["wall"], 1e-6) / np.maximum(src["wall"], 1e-6)), lo, hi)
    m = (ls + lw) / 2; d = np.clip((ls - lw) / 2, -split_max / 2, split_max / 2)
    return np.exp(m + d), np.exp(m - d)


def _smooth(ts, V, sigma):
    """median-of-3 then Gaussian (sigma seconds) along time; V (n, d)"""
    V = np.asarray(V, float)
    if len(V) >= 3:
        M = V.copy()
        for j in range(1, len(V) - 1): M[j] = np.median(V[j - 1:j + 2], 0)
        V = M
    if sigma <= 0 or len(V) < 2: return V
    ts = np.asarray(ts, float); W = np.exp(-.5 * ((ts[:, None] - ts[None, :]) / sigma) ** 2)
    return (W @ V) / W.sum(1, keepdims=True)


# ------------------------------------------------------------------ the solve
def solve(TL):
    """{seg id: {"k": [frame...], "g": [[3]...], "o": [[3]...]}} (+ "_ref", "_stats") for the timeline; {} when off"""
    S = TL.S; c = cfg_of(S); pr = TL.pr
    ar = TL.E.get("aroll", {}) or {}
    if not c["on"] or not _on(ar.get("shot_match", True)): return {}
    segs = [s for s in TL.segs if s.get("kind", "aroll") == "aroll" and os.path.exists(pr.e("plate", f"{s['id']}.mkv"))]
    if len(segs) < 2: return {}                       # one take: nothing to match
    from .render import trans_strength
    vis = {}
    for s in segs:
        v = [k for k in range(s["n"]) if not TL.in_cut((s["f0"] + k) / TL.FPS) and trans_strength(TL, (s["f0"] + k) / TL.FPS)[0] is None]
        if v: vis[s["id"]] = v
    mt = {s["id"]: [int(os.path.getmtime(pr.e(x, f"{s['id']}.mkv"))) if os.path.exists(pr.e(x, f"{s['id']}.mkv")) else 0 for x in ("plate", "matte")] for s in segs}
    sig = {"v": VERSION, "cfg": c, "segs": [[s["id"], s["n"]] for s in segs], "vis": {k: [v[0], v[-1], len(v)] for k, v in vis.items()}, "mtime": mt}
    cache = pr.e("shot_match.json")
    if os.path.exists(cache):
        try:
            d = json.load(open(cache, encoding="utf-8"))
            if d.get("_sig") == sig: return d["shots"]
        except (ValueError, KeyError): pass
    import av
    from concurrent.futures import ThreadPoolExecutor
    def measure_shot(s):
        sid = s["id"]; F = TL.faces.get(sid) or []; v = vis.get(sid, [])
        want = set(range(0, s["n"], c["step_f"])) | set(v[:3]) | set(v[-3:]) | {s["n"] - 1}
        mp = pr.e("matte", f"{sid}.mkv"); rows = []
        with av.open(pr.e("plate", f"{sid}.mkv")) as cp:
            cp.streams.video[0].thread_type = "AUTO"
            cm = av.open(mp) if os.path.exists(mp) else None
            try:
                mg = cm.decode(video=0) if cm is not None else None
                for k, fr in enumerate(cp.decode(video=0)):
                    mf = next(mg, None) if mg is not None else None
                    if k not in want: continue
                    rgb = fr.to_ndarray(format="rgb24").astype(np.float32) / 255
                    f = F[min(k, len(F) - 1)] if F else None
                    sk = skin_rgb(rgb, f)
                    wl = wall_rgb(rgb, mf.to_ndarray(format="gray"), f) if mf is not None else None
                    rows.append((k, None if sk is None else eotf(sk), None if wl is None else eotf(wl)))
            finally:
                if cm is not None: cm.close()
        return sid, rows
    with ThreadPoolExecutor(max(1, min(6, (os.cpu_count() or 2) - 1))) as ex: meas = dict(ex.map(measure_shot, segs))     # decode-bound (FFV1)
    def med(rows, j, only=None):
        x = [r[j] for r in rows if r[j] is not None and (only is None or r[0] in only)]
        return np.median(x, 0) if x else None
    stats = {sid: {"skin": med(r, 1, set(vis.get(sid, []))), "wall": med(r, 2, set(vis.get(sid, [])))} for sid, r in meas.items()}
    for sid, r in meas.items():                                # a shot never visible still gets stats from all its frames
        if stats[sid]["skin"] is None: stats[sid]["skin"] = med(r, 1)
        if stats[sid]["wall"] is None: stats[sid]["wall"] = med(r, 2)
    ok = [sid for sid in stats if stats[sid]["skin"] is not None]
    if not ok: return _save(cache, sig, {}, None, stats)
    ref = _reference(TL, c["reference"], ok, stats, vis)
    out = corrections(meas, stats, ref, c, TL.FPS)
    samples = {sid: [[int(k), None if a is None else np.round(oetf(a), 5).tolist(), None if b is None else np.round(oetf(b), 5).tolist()] for k, a, b in r] for sid, r in meas.items()}
    return _save(cache, sig, out, ref, stats, samples, vis)

def corrections(meas, stats, ref, c, fps):
    """{sid: {"k": [frame], "gs": [[3]], "gb": [[3]]}}: per sample, the shot's median correction onto the reference times
    `shot_match_drift` x the drift correction onto the shot's own median (smoothed over `shot_match_smooth_s`), in log
    gain, all scaled by `shot_match_strength`."""
    R = stats[ref]; out = {}; st, dr = c["strength"], c["drift"]; lo, hi = np.log(c["gain_range"][0]), np.log(c["gain_range"][1])
    for sid, rows in meas.items():
        M = stats.get(sid)
        if not rows or M is None or M["skin"] is None: continue
        s0, b0 = gains(M, R, c["gain_range"], c["split_max"])
        ks, V = [], []
        for k, sk, wl in rows:          # a sample missing one anchor borrows the shot median for it
            src = {"skin": sk if sk is not None else M["skin"], "wall": wl if wl is not None else M["wall"]}
            gs, gb = gains(src, M, c["gain_range"], c["split_max"])
            ks.append(k); V.append(np.r_[np.log(gs), np.log(gb)])
        V = _smooth(np.array(ks) / fps, V, c["smooth_s"]) * dr
        L = (np.r_[np.log(s0), np.log(b0)][None, :] + V) * st
        L[:, :3] = np.clip(L[:, :3], lo, hi); L[:, 3:] = np.clip(L[:, 3:], lo, hi)
        out[sid] = {"k": [int(k) for k in ks], "gs": np.round(np.exp(L[:, :3]), 5).tolist(), "gb": np.round(np.exp(L[:, 3:]), 5).tolist()}
    return out

def _reference(TL, how, ok, stats, vis):
    """the shot every other one is matched to: a segment id, `hook` (the first A-roll shot on screen) or `median` (the
    visible shot whose skin and wall are closest, in log linear RGB, to the median of the visible shots)"""
    if how in ok: return how
    order = [s["id"] for s in TL.segs if s["id"] in ok]
    shown = [s for s in order if vis.get(s)] or order        # shots the viewer never sees are not a reference
    if how == "median":
        vec = lambda s: np.log(np.r_[stats[s]["skin"], stats[s]["wall"] if stats[s]["wall"] is not None else stats[s]["skin"]] + 1e-6)
        M = np.median([vec(s) for s in shown], 0)
        return min(shown, key=lambda s: float(np.linalg.norm(vec(s) - M)))
    return shown[0]

def _save(cache, sig, shots, ref, stats, samples=None, vis=None):
    st = {k: {kk: (None if vv is None else np.round(oetf(vv) * 255, 1).tolist()) for kk, vv in v.items()} for k, v in stats.items()}
    try:
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump({"_sig": sig, "reference": ref, "stats_display_rgb": st, "shots": shots, "samples_display": samples or {},
                       "visible": {k: [v[0], v[-1]] for k, v in (vis or {}).items()}}, fh, indent=1)
    except OSError: pass
    return shots


# ------------------------------------------------------------------ apply
_LUT_N = 4096
_GRID = np.linspace(0, 1, _LUT_N)
_LIN = eotf(_GRID)

def params_at(M, sid, k):
    """(subject gain (3,), background gain (3,)) for plate frame k of shot sid, interpolated between samples; None = identity"""
    m = M.get(sid) if M else None
    if not m: return None
    ks = np.array(m["k"], float); GS = np.array(m["gs"]); GB = np.array(m["gb"])
    return (np.array([np.interp(k, ks, GS[:, c]) for c in range(3)]), np.array([np.interp(k, ks, GB[:, c]) for c in range(3)]))

def _idx(P):
    """LUT index of every value (intp: the gathers below then use it without converting it again)"""
    return np.clip(P * (_LUT_N - 1) + .5, 0, _LUT_N - 1).astype(np.intp)

def _table(g, c, dtype):
    return oetf(_LIN * g[c]).astype(dtype)

def _chan_idx(P):
    """per-channel contiguous intp index arrays (a gather from a contiguous intp index is numpy's fast path; one set is
    shared by the subject and wall passes of a frame)"""
    return [_idx(P[..., c]) for c in range(3)]

def _lut(P, g, idx=None):
    """per-channel LUT lookup; idx = _chan_idx(P) (shared by the subject and wall passes of one frame)"""
    ix = _chan_idx(P) if idx is None else idx; out = np.empty_like(P)
    for c in range(3): out[..., c] = _table(g, c, P.dtype)[ix[c]]
    return out

def apply(M, sid, k, P, A=None):
    """P (H, W, 3) display RGB float 0..1 (the plate), A its matte (uint8 / float, or None) -> the matched plate. The
    subject (matte) takes the skin gain, the wall the wall gain, blended through a softened matte (no edge line)."""
    p = params_at(M, sid, k)
    if p is None: return P
    gs, gb = p
    if A is None or np.allclose(gs, gb, atol=1e-3):
        g = (gs + gb) / 2 if A is None else gs
        return P if np.allclose(g, 1, atol=1e-4) else _lut(P, g)
    a = A.astype(np.float32) / (255 if A.dtype == np.uint8 else 1)
    a = cv2.resize(a, (a.shape[1] // 2, a.shape[0] // 2), interpolation=cv2.INTER_AREA)
    # erode before softening: the gain blend happens INSIDE the silhouette, so no subject gain spills onto the wall next to
    # it (a lifted 3-7 px band outside the shoulder, FRAME-03 on the first real job). Semi-transparent hair and edge pixels
    # take the wall gain, which is what shows through them anyway
    a = cv2.GaussianBlur(cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))), (0, 0), 1.5)   # ~3 px soft, ~7 px inside
    a = cv2.resize(a, (P.shape[1], P.shape[0]), interpolation=cv2.INTER_LINEAR)[..., None]
    idx = _chan_idx(P)
    out = _lut(P, gs, idx); out *= a                       # = lut(gs) * a + lut(gb) * (1 - a), without temporaries
    wall = _lut(P, gb, idx); wall *= (1 - a); out += wall
    return out
