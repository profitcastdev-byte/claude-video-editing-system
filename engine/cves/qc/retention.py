"""Retention gates RET-24..RET-32 (knowledge-base/QC-GATES.md, docs/VIRAL.md): hook timing, pattern-interrupt rhythm, loop
seam, payoff, platform duration band, dead air and the guide-track alignment of the platform sound slot.

Signals: the rendered master (luma decoded once at 96 px wide, mono audio at 16 kHz), Edit/timeline.json (cuts, cutaways,
transitions, snap), Edit/elements.jsonl (graphic entries, on-screen text), Edit/faces.json, Edit/stems/guide.wav and the
guide grid (cves.guide). Every threshold is a style key (`structure.*`, `rhythm.*`, `retention.*`, `platform.target`).

Goal profile (edit.yaml `goal:`): RET-25 / RET-28 / RET-29 apply to `goal: viral` only (an ad is judged by its story gates);
RET-31 dead air FAILs for viral and WARNs for ads (SND-13 is the ad's dead-air gate); RET-30 runs when platform.target is set;
RET-32 runs with `music.slot: platform` or `rhythm.cut_on_beat` + a music file. New gates WARN unless clearly objective
(dead air, duration over the platform maximum, a missing guide, music in a slot master): DECISIONS.md records each threshold."""
import os, json, subprocess
import numpy as np
from .. import config as C

IDS = ["RET-24", "RET-25", "RET-26", "RET-27", "RET-28", "RET-29", "RET-30", "RET-31", "RET-32"]


# ======================================================================== decoding
def probe(video):
    r = subprocess.run([C.get("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", video], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def decode_gray(video, width=96):
    """-> (frames uint8 (n, h, w), fps). One pass, area-scaled to `width` px wide (aspect kept, even height)."""
    from fractions import Fraction
    p = probe(video); v = next(s for s in p["streams"] if s["codec_type"] == "video")
    fps = float(Fraction(v.get("r_frame_rate", "30/1"))); W0, H0 = int(v["width"]), int(v["height"])
    w = width; h = max(2, int(round(width * H0 / W0 / 2)) * 2)
    out = subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", video, "-vf", f"scale={w}:{h}:flags=area,format=gray",
                          "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True).stdout
    n = len(out) // (w * h)
    return np.frombuffer(out[:n * w * h], np.uint8).reshape(n, h, w), fps


def decode_audio(video, sr=16000):
    """-> mono float32 at sr (empty when the file has no audio)"""
    out = subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "pipe:1"],
                         capture_output=True).stdout
    return np.frombuffer(out, np.float32).copy()


# ======================================================================== measurements (pure functions, unit-tested)
def frame_diffs(frames):
    """mean abs luma step per frame (index 0 = 0)"""
    if len(frames) < 2: return np.zeros(len(frames))
    f = frames.astype(np.int16)
    return np.r_[0.0, np.abs(f[1:] - f[:-1]).mean(axis=(1, 2))]


def scene_events(diffs, fps, thr):
    """times of picture changes: local maxima of the frame step at or above thr"""
    out = []
    for i in range(1, len(diffs)):
        d = diffs[i]
        if d >= thr and d >= diffs[i - 1] and (i + 1 >= len(diffs) or d >= diffs[i + 1]): out.append(i / fps)
    return out


def element_entries(els, fps):
    """[(t, label)] first visible frame of every non-caption element instance (an id reappearing after > 6 frames is a new entry)"""
    last, out = {}, []
    for e in sorted(els, key=lambda r: (r["f"], r["id"])):
        if e.get("role") == "caption" or float(e.get("alpha", 1)) <= 0.05: continue
        k = e["id"]
        if k not in last or e["f"] - last[k] > 6: out.append((e["f"] / fps, f"{e.get('role', '?')} {k} in"))
        last[k] = e["f"]
    return out


def timeline_events(tl):
    """[(t, label)] edits from timeline.json: A-roll cuts (with their zoom step), cutaway in / out, transitions, the snap"""
    ev = [(s["t0"], f"cut to {s['id']}") for s in (tl.get("segments") or [])[1:]]
    for c in tl.get("cutaways") or []: ev += [(c["start"], f"{c.get('id')} in"), (c["end"], f"{c.get('id')} out")]
    ev += [(float(t), f"{k} transition") for t, k in (tl.get("transitions") or [])]
    if tl.get("snap"): ev += [(tl["snap"][0], "snap punch-in"), (tl["snap"][1], "snap release")]
    return ev


def merge_events(ev, merge_s):
    """sort and merge events closer than merge_s into one interrupt: [(t, label)]"""
    out = []
    for t, lab in sorted(ev):
        if out and t - out[-1][0] < merge_s: out[-1] = (out[-1][0], out[-1][1] if lab in out[-1][1] else out[-1][1] + " + " + lab)
        else: out.append((float(t), lab))
    return out


def interrupt_gaps(times, T):
    """[(gap_s, from_t, to_t)] between consecutive interrupts, from 0 to the first and from the last to the end"""
    pts = [0.0] + [t for t in sorted(times) if 0 < t < T] + [T]
    return [(b - a, a, b) for a, b in zip(pts[:-1], pts[1:]) if b - a > 1e-6]


def soup_runs(times, min_s, window_s):
    """runs of consecutive interrupt gaps all shorter than min_s that last >= window_s: [(t0, t1, n_events)]"""
    ts = sorted(times); runs, i = [], 0
    while i < len(ts) - 1:
        j = i
        while j + 1 < len(ts) and ts[j + 1] - ts[j] < min_s: j += 1
        if j > i and ts[j] - ts[i] >= window_s: runs.append((ts[i], ts[j], j - i + 1))
        i = max(j, i + 1)
    return runs


def ssim(a, b):
    """mean SSIM of two grey images (7x7 box windows)"""
    import cv2
    a = a.astype(np.float32); b = b.astype(np.float32); C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2; k = (7, 7)
    ma, mb = cv2.blur(a, k), cv2.blur(b, k)
    va, vb, cab = cv2.blur(a * a, k) - ma * ma, cv2.blur(b * b, k) - mb * mb, cv2.blur(a * b, k) - ma * mb
    return float((((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))).mean())


def loop_similarity(frames, fps, span_s):
    """(span similarity, seam similarity): SSIM of the mean of the last span_s vs the first span_s, and last vs first frame"""
    n = max(1, min(len(frames) // 2, int(round(span_s * fps))))
    A, B = frames[-n:].astype(np.float32).mean(0), frames[:n].astype(np.float32).mean(0)
    return ssim(A, B), ssim(frames[-1], frames[0])


def short_term_db(y, sr, win_s=0.4, hop_s=0.1):
    if not len(y): return np.zeros(0)
    w, h = max(1, int(win_s * sr)), max(1, int(hop_s * sr))
    return np.array([20 * np.log10(np.sqrt(np.mean(y[i:i + w] ** 2)) + 1e-9) for i in range(0, max(1, len(y) - w + 1), h)])


def silent_runs(y, sr, thr_db, guide=None, win_s=0.05):
    """[(t0, t1)] spans where every 50 ms window of y (and of the guide, when given) is below thr_db"""
    w = max(1, int(win_s * sr)); n = len(y) // w
    if n == 0: return []
    def dbs(x):
        x = np.pad(x[:n * w], (0, max(0, n * w - len(x))))
        return 20 * np.log10(np.sqrt((x.reshape(n, w) ** 2).mean(1)) + 1e-12)
    quiet = dbs(y) < thr_db
    if guide is not None and len(guide): quiet &= dbs(guide) < thr_db
    m = np.concatenate([[0], quiet.astype(np.int8), [0]]); d = np.diff(m)
    return [(a * win_s, b * win_s) for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0])]


def on_beat_share(cuts, beats, tol):
    """share of cut times within tol of a beat, and the [(cut, nearest beat, offset)] misses"""
    if not cuts: return 1.0, []
    if not len(beats): return 0.0, [(c, None, None) for c in cuts]
    b = np.asarray(beats, float); miss = []
    for c in cuts:
        j = int(np.argmin(np.abs(b - c)))
        if abs(b[j] - c) > tol: miss.append((c, float(b[j]), c - float(b[j])))
    return 1 - len(miss) / len(cuts), miss


def centre_subject(frame):
    """a strong subject heuristic: the centre half holds clearly more detail than the frame border, with contrast"""
    import cv2
    f = frame.astype(np.float32); lap = np.abs(cv2.Laplacian(f, cv2.CV_32F)); h, w = f.shape
    c = (slice(h // 4, 3 * h // 4), slice(w // 4, 3 * w // 4)); mask = np.ones_like(f, bool); mask[c] = False
    ctr, ring = float(lap[c].mean()), float(lap[mask].mean()) + 1e-3
    return ctr / ring >= 1.5 and float(f[c].std()) >= 20, ctr / ring


# ======================================================================== the gates
def measure(pr, video, S=None):
    """every retention measurement as a dict (the gates and the tests read it)"""
    from .. import style as STY
    S = S or STY.load(pr); R = S.get("retention") or {}
    frames, fps = decode_gray(video); n = len(frames); T = n / fps if fps else 0.0
    tl = pr.json("timeline.json", {}) or {}
    ef = pr.e("elements.jsonl"); els = []
    if os.path.exists(ef):
        with open(ef, encoding="utf-8") as f: els = [json.loads(l) for l in f if l.strip()]
    diffs = frame_diffs(frames); thr = float(R.get("scene_diff", 12.0))
    scenes = scene_events(diffs, fps, thr)
    ev = timeline_events(tl) + element_entries(els, fps) + [(t, "picture change") for t in scenes]
    ev = [(t, l) for t, l in ev if 0 <= t < T]
    inter = merge_events(ev, float(R.get("merge_s", 0.05)))
    first = next(((t, l) for t, l in inter if t >= 0.5 / fps), None)
    audio = decode_audio(video); sr = 16000
    return {"S": S, "fps": fps, "T": T, "frames": frames, "diffs": diffs, "scenes": scenes, "interrupts": inter, "first_change": first,
            "els": els, "tl": tl, "audio": audio, "sr": sr}


def run_retention(pr, video, gate, S=None):
    from .. import style as STY, guide as GD, platforms as PF
    M = measure(pr, video, S); S = M["S"]; R = S.get("retention") or {}
    viral = STY.goal(pr) == "viral"; fps, T = M["fps"], M["T"]; inter = M["interrupts"]; times = [t for t, _ in inter]
    goal_s = "goal viral" if viral else "goal ad"

    # RET-24 first visual change (pattern interrupt) by structure.hook_change_s
    hc = float(S.get("structure.hook_change_s", 1.5)); fc = M["first_change"]
    gate("RET-24", bool(fc) and fc[0] <= hc + 1e-6, (f"first visual change at {fc[0]:.2f} s ({fc[1]})" if fc else "no visual change found") + f" (<= {hc:g} s, {goal_s})",
         status=None if fc and fc[0] <= hc + 1e-6 else "WARN")

    # RET-25 viral: on-screen text or a strong subject by retention.hook_subject_s
    if viral:
        hs = float(R.get("hook_subject_s", 1.0)); why = None
        txt = [e for e in M["els"] if e.get("text") and str(e["text"]).strip() and float(e.get("alpha", 1)) >= .5 and e["f"] / fps <= hs
               and not any(d in e["id"] for d in (".glow", ".bed", "brackets"))]
        if txt: e = min(txt, key=lambda r: r["f"]); why = f"text '{str(e['text'])[:24]}' ({e['id']}) at {e['f'] / fps:.2f} s"
        segs = M["tl"].get("segments") or []; faces = pr.json("faces.json", {}) or {}
        if not why and segs and segs[0].get("t0", 0) <= 0 and faces.get(segs[0]["id"]):
            covered = any(c["start"] <= 0 and c["end"] >= hs for c in M["tl"].get("cutaways") or [])
            if not covered: why = f"presenter face on the A-roll from 0 s ({segs[0]['id']})"
        if not why:
            k = min(len(M["frames"]) - 1, int(hs * fps))
            for i in range(0, k + 1, max(1, int(fps // 6))):
                ok, ratio = centre_subject(M["frames"][i])
                if ok: why = f"strong centre subject at {i / fps:.2f} s (centre/border detail {ratio:.1f}x)"; break
        gate("RET-25", bool(why), (why or "no on-screen text and no strong subject") + f" by {hs:g} s", status=None if why else "WARN")

    # RET-26 / RET-27 pattern-interrupt rhythm: max gap, and no sustained effect soup
    mx = float(S.get("rhythm.interrupt_max_s", 4.0)); gp = interrupt_gaps(times, T); long_ = [g for g in gp if g[0] > mx + 1e-6]
    worst = max(gp, default=(0.0, 0.0, 0.0))
    gate("RET-26", not long_, f"{len(inter)} interrupts; longest gap {worst[0]:.2f} s at {worst[1]:.2f}-{worst[2]:.2f} s (<= {mx:g} s)",
         "\n".join(f"{g:.2f} s without an interrupt: {a:.2f}-{b:.2f} s" for g, a, b in sorted(long_, reverse=True)[:8]), status=None if not long_ else "WARN")
    mn = float(S.get("rhythm.interrupt_min_s", 0.3)); win = float(R.get("soup_window_s", 1.5)); soup = soup_runs(times, mn, win)
    rate = len(inter) / T if T else 0.0
    gate("RET-27", not soup, f"{rate:.2f} interrupts/s overall; {len(soup)} sustained run(s) with gaps < {mn:g} s for >= {win:g} s (effect soup)",
         "\n".join(f"{a:.2f}-{b:.2f} s: {k} interrupts" for a, b, k in soup[:8]), status=None if not soup else "WARN")

    # RET-28 loop seam (viral, structure.loop)
    if viral and S.get("structure.loop"):
        span = float(R.get("loop_seam_s", 0.3)); lim = float(R.get("loop_min_similarity", 0.6))
        a, b = loop_similarity(M["frames"], fps, span); sim = min(a, b)
        gate("RET-28", sim >= lim, f"loop seam: last {span:g} s vs first {span:g} s similarity {a:.2f}, last vs first frame {b:.2f} (>= {lim:g})",
             status=None if sim >= lim else "WARN")

    # RET-29 payoff in the last structure.payoff_window of the runtime (viral)
    if viral:
        pw = float(S.get("structure.payoff_window", 0.2)); w0 = T * (1 - pw); dfs = M["diffs"]; i0 = int(w0 * fps); found = []
        body = dfs[1:i0] if i0 > 2 else dfs[1:]
        if len(dfs) > i0 + 1 and len(body):
            vth = max(float(R.get("scene_diff", 12.0)), float(np.percentile(body, 90)))
            j = i0 + int(np.argmax(dfs[i0:]))
            if dfs[j] >= vth: found.append(f"picture peak {dfs[j]:.1f} at {j / fps:.2f} s (body p90 {np.percentile(body, 90):.1f})")
        en = [(t, l) for t, l in element_entries(M["els"], fps) if t >= w0]
        if en: found.append(f"graphic entry at {en[0][0]:.2f} s ({en[0][1]})")
        st = short_term_db(M["audio"], M["sr"]); k0 = int(w0 / 0.1)
        if len(st) > k0 + 1 and k0 > 2:
            med = float(np.median(st[:k0])); pk = float(st[k0:].max()); rise = float(R.get("payoff_rise_db", 3.0))
            if pk >= med + rise: found.append(f"audio peak {pk - med:+.1f} dB vs body median at {(k0 + int(np.argmax(st[k0:]))) * .1:.2f} s")
        gate("RET-29", bool(found), f"payoff in the last {pw:.0%} ({w0:.2f}-{T:.2f} s): " + ("; ".join(found) if found else "no visual or audio peak"),
             status=None if found else "WARN")

    # RET-30 duration within the platform band
    band = PF.duration(S)
    if band:
        lo, hi, top = band; pf = PF.profile(S)
        st_ = "FAIL" if T > top + 1e-3 else ("PASS" if lo - 1e-3 <= T <= hi + 1e-3 else "WARN")
        gate("RET-30", st_ == "PASS", f"{T:.2f} s on {pf['label']}: ideal {lo:g}-{hi:g} s, max {top:g} s", status=st_)

    # RET-31 dead air: no speech, music or SFX (with music.slot: platform the guide counts: the sound plays there)
    thr = float(R.get("dead_air_db", -45)); lim = float(R.get("dead_air_s", 0.6)); guide = None
    gw = pr.e("stems", "guide.wav")
    if GD.is_slot(pr) and os.path.exists(gw):
        import soundfile as sf, librosa
        gy, gsr = sf.read(gw); gy = gy.mean(1) if gy.ndim > 1 else gy
        guide = librosa.resample(gy.astype(np.float32), orig_sr=gsr, target_sr=M["sr"])
    runs = silent_runs(M["audio"], M["sr"], thr, guide)
    if not len(M["audio"]): runs = [(0.0, T)]
    lr = max(runs, key=lambda r: r[1] - r[0], default=(0.0, 0.0)); dead = [r for r in runs if r[1] - r[0] > lim + 1e-6]
    gate("RET-31", not dead, f"longest silence {lr[1] - lr[0]:.2f} s at {lr[0]:.2f} s (<= {lim:g} s below {thr:g} dBFS"
         + (", guide counted" if guide is not None else "") + f"; {goal_s})",
         "\n".join(f"{a:.2f}-{b:.2f} s silent ({b - a:.2f} s)" for a, b in dead[:8]), status=None if not dead else ("FAIL" if viral else "WARN"))

    # RET-32 cuts vs the guide beat (music.slot: platform), or vs the music beat (rhythm.cut_on_beat)
    tl = M["tl"]; cuts = sorted(set([round(s["t0"], 4) for s in (tl.get("segments") or [])[1:]] + [round(c[k], 4) for c in tl.get("cutaways") or [] for k in ("start", "end")]))
    cuts = [c for c in cuts if 0 < c < T]
    from .. import beats as BT
    tol = float(BT.cfg(pr, S).get("snap_tolerance_s", 0.12)); need = float(R.get("guide_on_beat_min", 0.6)); grid = None; what = None
    if GD.is_slot(pr):
        probs = GD.problems(pr)
        if probs: gate("RET-32", False, "music.slot: platform: " + "; ".join(probs)); return
        if not os.path.exists(gw): gate("RET-32", False, "music.slot: platform but Edit/stems/guide.wav is missing: run `cves mix`"); return
        g = GD.grid(pr, T, S); grid, what = (g["beats"] if g else []), f"guide ({g['kind']}, {g['tempo'] or 0:.1f} BPM)" if g else "guide"
    elif S.get("rhythm.cut_on_beat") and (pr.edit.get("music") or {}).get("file"):
        try:
            P = BT.plan(pr, S=S, need_beats=True); grid, what = (P or {}).get("beats") or [], "music"
        except SystemExit as e: gate("RET-32", False, f"music beat grid not measured: {e}", status="WARN"); return
    if grid is not None:
        share, miss = on_beat_share(cuts, grid, tol)
        gate("RET-32", share >= need, f"{len(cuts) - len(miss)} of {len(cuts)} cuts within {tol * 1000:.0f} ms of a {what} beat ({share:.0%}, >= {need:.0%})",
             "\n".join(f"cut {c:.3f} s: nearest beat {b:.3f} s ({o * 1000:+.0f} ms)" if b is not None else f"cut {c:.3f} s: no beats" for c, b, o in miss[:10]),
             status=None if share >= need else "WARN")
