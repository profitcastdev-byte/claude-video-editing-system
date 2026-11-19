"""Inspire v2 FEEL: how a reference moves. Reads the per-frame analysis of inspire.analyse_video() and the soundtrack
analysis of inspire_audio.analyse(); decodes nothing except the loop seam (first / last 0.5 s).

analyse(r, hear) -> dict:
  cut_on_beat    share of detected cuts within +-2 frames of a beat of the reference's own music (+ the chance level
                 for that tempo, so 0.3 at 120 BPM is "random", 0.9 is "cut on the beat")
  cut_rate       cuts per second, a 3 s smoothed curve and its shape (arc_shape: rising = builds up, flat, wave, ...)
  hook           time to the first cut, to the first strong visual change (cut, zoom jump or graphic in) and to the first
                 on-screen text (any burned-in text line, 6 samples / s)
  interrupts     every strong visual change (cuts, frame-difference peaks that are not cuts, face-scale jumps >= 8%);
                 the gaps between them (median, max) = the pattern-interrupt rhythm
  loop           seam score: the last frame vs the first, measured like a cut, against the reference's normal frame step
  energy_arc     per second: visual change (mean frame difference) + mix level, each over its mean; arc_shape()
  duration       container duration (not capped by --max-s)
Thresholds: knowledge-base/DECISIONS.md "Inspire v2"."""
import numpy as np, cv2

BEAT_TOL_F = 2              # cut-on-beat tolerance, frames
LOOP_MAX_D = 0.15           # seam frame difference above this is never a loop (a cut is > 0.22)
LOOP_STEP_X = 3.0           # ... and it must look like a normal frame step: <= 3x the median step (floor LOOP_FLOOR)
LOOP_FLOOR = 0.03
SCALE_JUMP = 1.08           # face-height change between samples that counts as a zoom jump
SYNC_CUTS_MIN = 0.6         # cut_on_beat at or above this (and >= 2x chance) -> music.sync: cuts


def frame_diff(a, b):
    """the cut detector's distance between two thumbnails (pixel + colour histogram)"""
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).mean() / 255
    h1 = cv2.calcHist([a], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3); h2 = cv2.calcHist([b], [0, 1, 2], None, [8, 8, 8], [0, 256] * 3)
    hd = 1 - cv2.compareHist(cv2.normalize(h1, h1).flatten(), cv2.normalize(h2, h2).flatten(), cv2.HISTCMP_CORREL)
    return float(.5 * d * 4 + .5 * hd)


def _smooth(x, k=3):
    x = np.asarray(x, float)
    if len(x) < k: return x
    p = np.pad(x, k // 2, mode="edge"); return np.convolve(p, np.ones(k) / k, mode="valid")


def arc_shape(e):
    """rising | peak_end | wave | falling | flat for a positive per-second curve"""
    e = _smooth(np.asarray(e, float)); n = len(e)
    if n < 4: return "flat"
    m, sd = float(e.mean()), float(e.std())
    if sd / (abs(m) + 1e-9) < .12: return "flat"
    third = max(1, n // 3); a, c = float(e[:third].mean()), float(e[-third:].mean())
    rho = float(np.corrcoef(np.arange(n), np.argsort(np.argsort(e)))[0, 1])
    j = int(np.argmax(e))
    if rho >= .6 and c > 1.15 * a: return "rising"
    if j >= .8 * (n - 1) and e[j] >= m + 1.2 * sd: return "peak_end"
    from scipy.signal import find_peaks
    if len(find_peaks(e, prominence=.6 * sd)[0]) >= 2: return "wave"
    if rho <= -.6 and a > 1.15 * c: return "falling"
    return "flat" if sd / (abs(m) + 1e-9) < .25 else "wave"


def seam(path, head_s=.5, rot=0):
    """thumbnails of the first and last head_s seconds -> loop seam measurement"""
    import av
    from .inspire import LW, LH
    def thumb(fr):
        lo = fr.reformat(width=LW, height=LH, format="rgb24").to_ndarray()
        return np.ascontiguousarray(np.rot90(lo, -rot // 90)) if rot in (90, 270, -90) else lo
    head, tail = [], []
    with av.open(path) as c:
        vs = c.streams.video[0]
        dur = float(vs.duration * vs.time_base) if vs.duration else float(c.duration or 0) / 1e6
        t0 = None
        for fr in c.decode(vs):
            t = float(fr.time or 0); t0 = t if t0 is None else t0
            if t - t0 > head_s: break
            head.append(thumb(fr))
        if dur > 2 * head_s + .1:
            c.seek(int(max(0, dur - head_s - .6) / vs.time_base), stream=vs, backward=True)
            for fr in c.decode(vs): tail.append((float(fr.time or 0), thumb(fr)))
            last = tail[-1][0] if tail else 0
            tail = [im for t, im in tail if t >= last - head_s]
    if len(head) < 2 or len(tail) < 2: return dict(score=None, loop=None, note="too short for a seam")
    steps = [frame_diff(a, b) for a, b in zip(head[:-1], head[1:])] + [frame_diff(a, b) for a, b in zip(tail[:-1], tail[1:])]
    typ = float(np.median(steps))
    d = min(frame_diff(a, b) for a in tail[-3:] for b in head[:3])
    loop = bool(d <= LOOP_MAX_D and d <= max(LOOP_STEP_X * typ, LOOP_FLOOR))
    return dict(seam_d=round(d, 4), step_d=round(typ, 4), score=round(float(np.clip(1 - d / .22, 0, 1)), 3), loop=loop, duration=round(dur, 2))


def _peaks(times, diffs, cuts):
    """strong visual changes that are not cuts (graphic in, flash, zoom jump), >= 0.25 s apart"""
    d = np.asarray(diffs); n = len(d); out = []
    for i in range(1, n):
        lo, hi = max(0, i - 15), min(n, i + 16); med = float(np.median(d[lo:hi]))
        if d[i] > max(.08, 3 * med + .02) and d[i] >= d[max(0, i - 3):i + 4].max():
            t = times[i]
            if any(abs(t - c) < .15 for c in cuts): continue
            if not out or t - out[-1] >= .25: out.append(t)
    return out


def analyse(r, hear=None):
    fps = float(r.get("fps") or 30); step = max(1, int(round(fps / 30))); afps = fps / step
    T = float(r.get("dur") or 0); cuts = list(r.get("cuts") or []); times, diffs = r.get("times") or [], r.get("diffs") or []
    out = dict(cuts=len(cuts), analysed_s=round(T, 2))
    sm = r.get("seam") or {}
    out["duration"] = sm.get("duration") or round(T, 2)
    # ---------------- cut on beat
    beats = np.array((hear or {}).get("beats") or [])
    tol = BEAT_TOL_F / afps
    if len(beats) >= 4 and cuts:
        inside = [c for c in cuts if beats[0] - tol <= c <= beats[-1] + tol]
        if inside:
            hit = [c for c in inside if np.min(np.abs(beats - c)) <= tol]
            per = float(np.median(np.diff(beats)))
            out["cut_on_beat"] = dict(ratio=round(len(hit) / len(inside), 3), n=len(inside), tol_s=round(tol, 3),
                                      chance=round(min(1.0, 2 * tol / per), 3), beat_s=round(per, 3))
    # ---------------- cut-rate curve
    if T >= 3:
        nb = int(np.ceil(T)); cnt = np.zeros(nb)
        for c in cuts: cnt[min(nb - 1, int(c))] += 1
        curve = _smooth(cnt, 3)
        out["cut_rate"] = dict(mean=round(len(cuts) / T, 3), curve=[round(float(x), 2) for x in curve],
                               shape=arc_shape((curve[1:-1] if len(curve) >= 6 else curve) + .05) if len(cuts) >= 3 else "flat")   # the edge bins are partial windows
    # ---------------- interrupts + hook
    peaks = _peaks(times, diffs, cuts)
    S = r.get("samples") or []; jumps = []
    for p, q in zip(S[:-1], S[1:]):
        if p.get("face") and q.get("face") and q["t"] - p["t"] < .4:
            a, b = p["face"][3], q["face"][3]
            if max(a, b) / max(1e-6, min(a, b)) >= SCALE_JUMP and not any(abs(q["t"] - c) < .3 for c in cuts): jumps.append(q["t"])
    ev = sorted(set([round(x, 3) for x in cuts + peaks + jumps]))
    merged = []
    for x in ev:
        if not merged or x - merged[-1] >= .2: merged.append(x)
    gaps = np.diff([0.0] + merged + [T]) if T else np.array([])
    out["interrupts"] = dict(n=len(merged), cuts=len(cuts), changes=len(peaks), zoom_jumps=len(jumps),
                             median_s=round(float(np.median(gaps)), 2) if len(gaps) else None,
                             max_s=round(float(gaps.max()), 2) if len(gaps) else None,
                             per_10s=round(len(merged) / max(T, 1e-3) * 10, 2))
    text_t = next((s["t"] for s in S if s.get("caps")), None)
    out["hook"] = dict(first_cut_s=round(cuts[0], 2) if cuts else None, first_change_s=round(merged[0], 2) if merged else None,
                       first_text_s=None if text_t is None else round(text_t, 2))
    # ---------------- loop
    out["loop"] = dict(score=sm.get("score"), loop=sm.get("loop"), seam_d=sm.get("seam_d"), step_d=sm.get("step_d"))
    # ---------------- energy arc (visual change + mix level per second)
    if T >= 4 and times:
        nb = int(np.ceil(T)); vis = np.zeros(nb); k = np.zeros(nb)
        for t, d in zip(times, diffs): j = min(nb - 1, int(t)); vis[j] += d; k[j] += 1
        vis = vis / np.maximum(k, 1)
        comb = vis / (vis.mean() + 1e-9)
        mix = [m for m in ((hear or {}).get("energy") or {}).get("mix_db") or []][:nb]
        if len(mix) == nb and all(m is not None for m in mix):
            a = 10 ** (np.array(mix) / 20); comb = .5 * comb + .5 * a / (a.mean() + 1e-9)
        out["energy_arc"] = dict(shape=arc_shape(comb), curve=[round(float(x), 2) for x in comb])
    return out


def summary_line(f):
    s = [f"{f.get('duration', 0):.1f} s", f"{f['cuts']} cuts"]
    if f.get("cut_rate"): s.append(f"{f['cut_rate']['mean'] * 60:.0f} cuts/min ({f['cut_rate']['shape']})")
    if f.get("cut_on_beat"): s.append(f"{f['cut_on_beat']['ratio']:.0%} on the beat (chance {f['cut_on_beat']['chance']:.0%})")
    h = f.get("hook") or {}
    if h.get("first_change_s") is not None: s.append(f"first change {h['first_change_s']:.2f} s")
    if (f.get("loop") or {}).get("loop"): s.append("loops")
    if f.get("energy_arc"): s.append(f"arc {f['energy_arc']['shape']}")
    return ", ".join(s)


def derive(R, ev):
    """rhythm.* / structure.* (and music.sync) from the FEEL analysis of the references in R"""
    import collections, math
    F = [r["feel"] for r in R if r.get("feel")]
    if not F: return
    n = len(F); fmt = lambda xs: ", ".join(f"{x:g}" for x in xs)
    half = lambda x: math.ceil(x * 2) / 2
    cb = [f["cut_on_beat"] for f in F if f.get("cut_on_beat")]
    if cb:
        ratio = float(np.median([c["ratio"] for c in cb])); chance = float(np.median([c["chance"] for c in cb])); ncut = sum(c["n"] for c in cb)
        sep = abs(ratio - chance) / max(chance, .05)
        conf = min(1, ncut / 12) * (.85 if sep >= 1 else .5)
        ev.put("rhythm.cut_on_beat", round(ratio, 2), f"cuts within +-{BEAT_TOL_F} frames of a beat of the ref's own music: {fmt([c['ratio'] for c in cb])} "
               f"(chance at that tempo {chance:.0%}); {ncut} cuts", ncut, conf)
        if ratio >= SYNC_CUTS_MIN and ratio >= 2 * chance:
            ev.put("music.sync", "cuts", f"references cut on the beat ({ratio:.0%} vs chance {chance:.0%}): cut points and graphic entries go on the beat", ncut, conf)
    cr = [f["cut_rate"] for f in F if f.get("cut_rate")]
    if cr:
        ev.put("rhythm.cuts_per_s", round(float(np.median([c["mean"] for c in cr])), 2), f"cuts per second per ref: {fmt([c['mean'] for c in cr])}",
               len(cr), min(1, sum(f["cuts"] for f in F) / 20))
        c = collections.Counter(x["shape"] for x in cr); m, k = c.most_common(1)[0]
        ev.put("rhythm.cut_curve", m, f"shape of the 3 s smoothed cut-rate curve per ref: {dict(c)}", len(cr), (.4 + .1 * len(cr)) * k / len(cr))
    it = [f["interrupts"] for f in F if (f.get("interrupts") or {}).get("max_s") is not None]
    if it:
        mx = [i["max_s"] for i in it]; md = [i["median_s"] for i in it]
        ev.put("rhythm.interrupt_max_s", half(float(np.median(mx))), f"longest gap between pattern interrupts (cut, visual-change peak, zoom jump) per ref: {fmt(mx)} s",
               len(it), min(1, .45 + .1 * len(it)))
        ev.put("rhythm.interrupt_median_s", round(float(np.median(md)), 2), f"median gap between pattern interrupts per ref: {fmt(md)} s", len(it), min(1, .45 + .1 * len(it)))
    hk = [f["hook"] for f in F if f.get("hook")]
    for key, name, how in (("first_change_s", "structure.hook_change_s", "first strong visual change (cut, zoom jump, graphic in)"),
                           ("first_cut_s", "structure.first_cut_s", "first cut"), ("first_text_s", "structure.first_text_s", "first burned-in text")):
        v = [h[key] for h in hk if h.get(key) is not None]
        if v: ev.put(name, round(float(np.median(v)), 2), f"{how} per ref: {fmt(v)} s", len(v), min(1, .45 + .1 * len(v)))
    lp = [f["loop"] for f in F if (f.get("loop") or {}).get("loop") is not None]
    if lp:
        k = sum(1 for x in lp if x["loop"])
        ev.put("structure.loop", k * 2 > len(lp), f"last frame vs first measured like a cut (seam score per ref {fmt([x['score'] for x in lp])}); loops in {k}/{len(lp)}",
               len(lp), (.55 + .1 * len(lp)) if k in (0, len(lp)) else .35)
    ar = [f["energy_arc"]["shape"] for f in F if f.get("energy_arc")]
    if ar:
        c = collections.Counter(ar); m, k = c.most_common(1)[0]
        ev.put("structure.energy_arc", m, f"visual change + mix level per second, shape per ref: {dict(c)}", len(ar), (.4 + .1 * len(ar)) * k / len(ar))
    du = [f["duration"] for f in F if f.get("duration")]
    if du: ev.put("structure.duration_s", round(float(np.median(du)), 1), f"reference durations {fmt(du)} s", len(du), .6)
