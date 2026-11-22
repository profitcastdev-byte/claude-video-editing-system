"""Senior sound: automatic accents (risers into the hook / payoff, impacts on reveals) and voice-envelope ducking.

Accents (`accents()`, called by mix.all_cues, so `cves mix` and the SND gates see the same cue list):
  * a riser whose PEAK lands on the payoff (the drop moment: music.drop_cut, else the first music.drop_beats clip,
    else the reveal) and one into the hook (music.hook_cut / the first music.hook_beats clip when there is room before
    it, else resolving where the hook hands over to the body). A riser needs a landing: a sound already on its target,
    the music drop, or an impact placed with it; otherwise it is skipped (a riser into nothing sounds unfinished);
  * an impact (a downbeat hit, layered with the music drop) on the payoff, and on reveals / big text slams whose own
    cues carry no low hit;
  * placed in order (payoff riser, payoff impact, hook riser, then reveals in time order), never on a moment that
    already has a riser / impact of its own, and only on a target within one frame of a picture event (a cut, a cutaway
    edge, the end card, the punch-in);
  * sounds are chosen from the SFX bank by category + intensity (cves.sfx), the riser by the room before its target and
    only among risers that resolve (peak within `sound.accents.riser_tail_max_s` of their end).
  Every accent is an ordinary cue (t, id, gain, kw) with kw {accent, target, why}.

Ducking (`duck_control()` + `apply_duck()`, `mix.duck_mode`):
  envelope  (default) the music gain follows the voice-band RMS envelope: 0 at `mix.duck_range_db` under the voice's
            loud level, full depth from 6 dB under it; attack `mix.duck_attack_ms`, release `mix.duck_release_ms`
            (`auto` = 1.25 x the measured syllable period, clamped to `mix.duck_release_range_ms`), look-ahead
            `sound.duck_lookahead_s`. Depth from the style: `sound.duck_voice_band_db` (250 Hz-5 kHz) and
            `sound.duck_other_db` (lows + highs), the same frequency split as before.
  gate      the v0.3 fixed dips: a near-binary speech gate (100 ms |voice| average), 30 ms attack, 400 ms release.

Cue sync (`sync_cues()`, from mix._finalize): after render, every cue's onset (a riser: its peak) lands exactly on its
logged picture event (at any frame rate). Vocal-to-music guard (`vmr_guard()`, from mix): the bed's speech band is
trimmed wherever a word would not clear the voice by `mix.vmr_min_db` (docs/SOUND.md §3, §5)."""
import numpy as np

IMPACT_FAMILY = ("lowhit", "boom", "impact", "hit")


# ------------------------------------------------------------------ helpers
def _on(v, dflt=True):
    if v is None: return dflt
    return v is True or str(v).strip().lower() in ("true", "on", "yes", "1")

def picture_events(TL):
    """cut times a sound may sit on (SND-07's picture events that are known before rendering)"""
    ev = [float(s["t0"]) for s in TL.segs[1:]]
    for cu in TL.cuts: ev += [float(cu["start"]), float(cu["end"])]
    if TL.END: ev.append(float(TL.T_END))
    if getattr(TL, "snap", None): ev += [float(TL.snap[0]), float(TL.snap[1])]
    ev += [float(t) for t, _ in getattr(TL, "trans", [])]
    return sorted(set(round(t, 6) for t in ev))

_ONSET = {}
def onset_offset(path, trim=None):
    """seconds from the start of a (trimmed) sound to its onset: the first 10 ms RMS window at 10% of the peak, the
    measure SND-07 uses. An impact is placed so this onset is on its target."""
    import os, librosa
    key = (os.path.abspath(path), int(os.path.getmtime(path)), str(trim))
    if key not in _ONSET:
        y, _ = librosa.load(path, sr=48000, mono=True)
        if trim: y = y[int(trim[0] * 48000):int(trim[1] * 48000)]
        env = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")) if len(y) else np.zeros(1)
        _ONSET[key] = float(np.argmax(env >= .1 * (env.max() + 1e-12))) / 48000
    return _ONSET[key]

# ------------------------------------------------------------------ cue sync (SND-07 at any frame rate)
def _sig(pr):
    """identity of the render the cue sync was measured on (element log + timeline)"""
    import os
    out = []
    for f in ("elements.jsonl", "timeline.json"):
        p = pr.e(f)
        if not os.path.exists(p): return None
        st = os.stat(p); out.append([f, st.st_size, st.st_mtime_ns])
    return out

def _file_sha(path):
    import hashlib, os
    if not os.path.exists(path): return None
    with open(path, "rb") as fh: return hashlib.sha256(fh.read()).hexdigest()

def _low_frames(pr, frames, size):
    """quarter-res full-range BT.709 luma of rendered frames (Edit/frames/NNNNN.png): what the SND-07 gate decodes from the master (PyAV gray).
    Read and reduced on a few threads (cv2 and numpy release the GIL): the same values, a fraction of the wait."""
    import os, cv2
    from concurrent.futures import ThreadPoolExecutor
    def one(f):
        p = pr.e("frames", f"{f:05d}.png")
        if not os.path.exists(p): return f, None
        im = cv2.imread(p, cv2.IMREAD_COLOR)
        if im is None: return f, None
        y = im[..., 2] * .2126 + im[..., 1] * .7152 + im[..., 0] * .0722
        return f, cv2.resize(y.astype(np.float32), size, interpolation=cv2.INTER_AREA).round().astype(np.uint8)
    frames = list(frames)
    with ThreadPoolExecutor(max(1, min(6, len(frames), (os.cpu_count() or 2) - 1))) as ex:
        return {f: y for f, y in ex.map(one, frames) if y is not None}

def sync_cues(TL, cues, log=None):
    """snap every cue's audible anchor onto the picture event it belongs to, exactly, at any frame rate.

    A template quantises a cue to the frame of its visual event, but the sound file starts there: its onset (or a riser's
    peak) comes 10-40 ms later, which is under a frame at 30 fps and 1-3 frames at 60 fps, and a few templates time a cue to
    a drawn state that the element log never records (a check that draws inside its row). After render, the picture
    events are known: the element log's entries, cuts / transitions / the snap, logged bbox changes and pixel-change onsets
    on graphic frames (cves.events.visual_events). Each cue moves so that its measured onset
    (risers: their peak) lands exactly on the nearest event within `sound.cue_sync_max_f` frames of the time the template
    asked for: a logged element entry / change or a cut first; a pixel onset only when none is that close and only a strong
    one (>= `sound.cue_sync_pixel_min` quarter-res px, so it survives the encode the gate decodes). A cue with no event
    that close keeps its time. Cues placed by their peak (`peak_at`: transition whooshes,
    automatic risers), media audio and `sync: false` cues are left alone. The pixel events are measured once on the
    rendered frames and cached in Edit/cue_sync.json with the render they belong to."""
    import os, json
    S = TL.S
    if not _on(S.get("sound.cue_sync", True)) or not cues: return cues
    pr = TL.pr; sig = _sig(pr)
    if sig is None: return cues                       # not rendered yet: nothing to sync to
    from . import events as X
    from .mix import sfx_bank, peak_offset
    cx = X.Ctx(pr, None); FPS = float(cx.FPS); mx = float(S.get("sound.cue_sync_max_f", 6)); find = sfx_bank(TL)
    ev = sorted(set((round(float(t), 6), lab) for t, lab in X.visual_events(cx)))
    cf = pr.e("cue_sync.json"); cache = {}
    if os.path.exists(cf):
        try: cache = json.load(open(cf, encoding="utf-8"))
        except ValueError: cache = {}
    pmin = int(S.get("sound.cue_sync_pixel_min", 40))
    # a pixel event at frame f is a function of the rendered frames f-2..f and of the timeline (which frames are A-roll /
    # in a transition): after an incremental render, the scan of every frame whose three frame-cache keys (cves.rcache) and
    # timeline are unchanged is still valid, so only the windows round re-rendered frames are scanned again
    from . import rcache as RC
    fk = RC.load(pr.e("frames"), pr.e("elements.jsonl")); tl_sha = _file_sha(pr.e("timeline.json"))
    if cache.get("sig") != sig or cache.get("min_px") != pmin:
        old = cache; cache = {"sig": sig, "min_px": pmin, "scanned": [], "pixel": [], "tl": tl_sha, "keys": {}}
        ok_keys = old.get("keys") or {}
        if fk and ok_keys and old.get("min_px") == pmin and old.get("tl") == tl_sha:
            same = lambda f: all(g < 0 or (fk.get(g) is not None and ok_keys.get(str(g)) == fk.get(g)) for g in (f - 2, f - 1, f))
            keep = {f for f in old.get("scanned", []) if same(f)}
            cache["scanned"] = sorted(keep); cache["pixel"] = [f for f in old.get("pixel", []) if f in keep]
    cache["tl"] = tl_sha
    todo = []
    for t, name, gain, kw in cues:
        if name.startswith("asset:") or kw.get("peak_at") is not None or kw.get("sync") is False: continue
        k = int(round(float(t) * FPS)); todo.append((k - int(mx) - 2, k + int(mx) + 2))
    scanned, px, dirty = set(cache["scanned"]), set(cache["pixel"]), False
    for lo, hi in todo:                                   # each window: 2 warm-up frames so a change carries its history
        rep = [f for f in range(max(1, lo), min(cx.N, hi + 1)) if f not in scanned]
        if not rep: continue
        low = _low_frames(pr, range(max(0, rep[0] - 2), rep[-1] + 1), X.LOW)
        if not low: continue
        px |= set(X.pixel_events(cx, low, frames=set(rep), min_px=pmin)); scanned |= {f for f in rep if f in low}; dirty = True
    if dirty or cache.get("keys") is None or (fk and not cache.get("keys")):
        dirty = True
        cache.update(scanned=sorted(scanned), pixel=sorted(px),
                     keys={str(g): fk[g] for f in scanned for g in (f - 2, f - 1, f) if g in fk})
        try:
            with open(cf, "w", encoding="utf-8") as fh: json.dump(cache, fh)
        except OSError: pass
    pev = [(f / FPS, f"pixel change on f{f}") for f in cache["pixel"]]
    def nearest(E, ref):
        if not E: return None
        j = min(range(len(E)), key=lambda i: abs(E[i][0] - ref))
        return E[j] if abs(E[j][0] - ref) * FPS <= mx + 1e-6 else None
    out = []
    for t, name, gain, kw in cues:
        if name.startswith("asset:") or kw.get("peak_at") is not None or kw.get("sync") is False:
            out.append((t, name, gain, kw)); continue
        path = find(name); riser = "riser" in name
        a = peak_offset(TL, name, kw) if riser else onset_offset(path, kw.get("trim"))
        ref = float(t) + (a if riser else 0.0)        # the time the template meant: the file start (a riser: its peak)
        e = nearest(ev, ref) or nearest(pev, ref)     # a logged element / cut first; a strong pixel onset only without one
        if e is None: out.append((t, name, gain, kw)); continue
        nt = float(e[0]) - a; kw = dict(kw, synced=e[1])
        if log is not None: log.append({"name": name, "from": round(float(t), 4), "to": round(nt, 4), "event": e[1], "anchor_ms": round(a * 1000, 1)})
        out.append((nt, name, gain, kw))
    return out

def _nearest(ev, t, tol):
    if not ev: return None
    e = min(ev, key=lambda x: abs(x - t))
    return e if abs(e - t) <= tol + 1e-9 else None


# ------------------------------------------------------------------ accents
def accents(TL, cues, log=None):
    """auto riser / impact cues for the story moments (see the module doc). `cues` = the cue list so far (pre-finalize):
    a moment that already carries a riser / impact gets none. `log` collects one dict per decision (mix.json accents)."""
    from . import beats as BT, sfx as SFX
    S = TL.S; A = S.get("sound.accents") or {}; log = log if log is not None else []
    if not _on(A.get("enabled", True)) or (TL.E.get("sfx") or {}).get("auto") is False:
        log.append({"status": "off", "why": "sound.accents.enabled: false" if not _on(A.get("enabled", True)) else "edit.yaml sfx.auto: false"}); return []
    c = BT.cfg(TL.pr, S); ms = BT.story_moments(TL, c); fr = 1.0 / TL.FPS; T = TL.N / TL.FPS
    ev = picture_events(TL); cands = SFX.entries(TL.pr)
    tail_max = float(A.get("riser_tail_max_s", 0.1))
    for s_ in cands:      # a riser resolves only if its peak is its end: older manifests without peak_at_s are measured once
        if s_.get("category") == "riser" and s_.get("peak_at_s") is None: s_["peak_at_s"] = SFX.measure(s_["path"])["peak_at_s"]
    risers = [s_ for s_ in cands if s_.get("category") != "riser" or float(s_["duration_s"]) - float(s_["peak_at_s"]) <= tail_max]
    r_gain, i_gain = float(A.get("riser_gain_db", -14)), float(A.get("impact_gain_db", -11))
    r_min, r_max = float(A.get("riser_min_s", 0.8)), float(A.get("riser_max_s", 2.2))
    gap = float(A.get("min_gap_s", 0.3))
    want = []          # (priority, kind, target, why, intensity)
    pay, why_p = ms["payoff"]
    if pay is not None and pay > 0:
        want += [(0, "riser", pay, f"payoff ({why_p})", A.get("payoff_riser", "medium")), (1, "impact", pay, f"payoff ({why_p})", A.get("payoff_impact", "hard"))]
    hook, why_h = ms["hook"]; he = ms["hook_end"][0]
    if hook is not None and hook >= r_min: want.append((2, "riser", hook, f"into the hook ({why_h})", A.get("hook_riser", "soft")))
    elif he is not None and (pay is None or he < pay - 1e-6): want.append((2, "riser", he, "out of the hook into the body (no room before the hook)", A.get("hook_riser", "soft")))
    if _on(A.get("reveals", True)):
        rev = sorted({round(float(t), 4) for t, n, g, kw in cues if kw.get("reveal") and not n.startswith("asset:")})
        for t in rev:
            if not any(any(f in n for f in IMPACT_FAMILY) and abs(t2 - t) <= 2 * fr for t2, n, _, _ in cues): want.append((3, "impact", t, "reveal without a low hit", A.get("reveal_impact", "medium")))
    has_drop = bool((TL.E.get("music") or {}).get("file")) and pay is not None
    def landing(t):          # a riser must resolve INTO something: a sound already on the target, the drop, or an impact we add
        if any(abs(t2 - t) <= 2 * fr and "riser" not in n for t2, n, _, kw in cues): return "a cue on the target"
        if has_drop and abs(t - pay) <= fr: return "the music drop"
        if any(k == "impact" and abs(x - t) <= fr for _, k, x, _, _ in want): return "the impact on the target"
        return None
    out, used, taken = [], [], {}
    for pri, kind, tgt, why, inten in sorted(want, key=lambda w: (w[0], w[2])):
        rec = {"kind": kind, "target": round(tgt, 4), "why": why}; log.append(rec)
        e = _nearest(ev, tgt, fr)
        if e is None: rec["status"] = f"skipped: no picture event within 1 frame of {tgt:.3f} s"; continue
        tgt = e; rec["target"] = round(tgt, 4)
        if kind == "riser" and any("riser" in n and abs((kw.get("peak_at") if kw.get("peak_at") is not None else t) - tgt) <= .5 for t, n, _, kw in cues):
            rec["status"] = "skipped: the moment already has a riser"; continue
        if kind == "impact" and any(any(f in n for f in IMPACT_FAMILY) and abs(t - tgt) <= 2 * fr for t, n, _, kw in cues if not kw.get("accent")):
            rec["status"] = "skipped: the moment already has a low hit"; continue
        if kind == "riser" and not landing(tgt): rec["status"] = "skipped: nothing lands on the target (a riser resolves into a hit, a drop or a cut sound)"; continue
        if kind == "riser":
            prev = max([u for u in used if u < tgt - 1e-6] + [0.0])       # a riser starts after the accent before it
            room = tgt - prev - (gap if prev > 0 else 0.0)
            if room < r_min: rec["status"] = f"skipped: {room:.2f} s of room before the target (< sound.accents.riser_min_s {r_min})"; continue
            s = SFX.pick(risers, "riser", inten, exclude=[taken.get("riser")] if taken.get("riser") else (), max_s=min(r_max, room), min_s=r_min)
            if s is None or float(s["duration_s"]) > room + 1e-6: rec["status"] = "skipped: no resolving riser in the bank fits the room"; continue
            st = tgt - float(s["peak_at_s"])
            if any(kw["accent"] == "riser" and t0 < tgt + gap and kw["target"] > st - gap for t0, _, _, kw in out):
                rec["status"] = "skipped: it would overlap another riser"; continue
            out.append((tgt - float(s["peak_at_s"]), s["id"], r_gain, {"peak_at": tgt, "accent": "riser", "target": tgt, "beat_snap": False, "why": why}))
        else:
            imx = float(A.get("impact_max_s", 2.0))
            att = float(A.get("impact_attack_max_s", 0.03))        # a hit, not a swell: onset to peak within this
            hits = [x for x in cands if x.get("category") == "impact" and x.get("peak_at_s") is not None and float(x["peak_at_s"]) - onset_offset(x["path"]) <= att]
            s = SFX.pick(hits, "impact", inten, exclude=[taken.get("impact")] if taken.get("impact") else ())
            if s is None: rec["status"] = "skipped: no impact in the bank"; continue
            kw = {"accent": "impact", "target": tgt, "reveal": True, "beat_snap": False, "why": why}
            if float(s["duration_s"]) > imx: kw["trim"] = (0, imx)          # a long recorded boom: its first impact_max_s
            out.append((tgt - onset_offset(s["path"], kw.get("trim")), s["id"], i_gain, kw))      # its onset on the target (SND-07)
        taken[kind] = s["id"]; used.append(tgt); rec.update(status="placed", id=s["id"], intensity=s.get("intensity"))
    return out


# ------------------------------------------------------------------ ducking
def _band(y, sr, lo=250, hi=5000):
    from scipy.signal import butter, sosfiltfilt
    return sosfiltfilt(butter(2, [lo, hi], "band", fs=sr, output="sos"), y)

def syllable_hz(env_db, hop_s, floor_db):
    """dominant 2-9 Hz modulation of a dB envelope while speaking (the syllable rate); None if too little speech"""
    on = np.convolve((env_db > floor_db).astype(float), np.ones(max(1, int(.3 / hop_s))), "same") > 0     # speaking spans (gaps < 0.3 s bridged)
    if on.sum() * hop_s < 1.0: return None
    x = np.where(on, env_db - np.median(env_db[on]), 0.0); x = x - x.mean()
    F = np.abs(np.fft.rfft(x * np.hanning(len(x)))); f = np.fft.rfftfreq(len(x), hop_s)
    m = (f >= 2) & (f <= 9)
    return float(f[m][np.argmax(F[m])]) if m.any() and F[m].max() > 0 else None

def duck_control(vo, sr, S, mode=None):
    """(control 0..1 per sample, info). 1 = full duck depth. mode: envelope | gate (default style mix.duck_mode)."""
    mode = str(mode or S.get("mix.duck_mode", "envelope")).strip().lower(); N = len(vo); info = {"mode": mode}
    if N == 0 or not np.abs(vo).max() > 0: return np.zeros(N), dict(info, note="no voice")
    if mode == "gate":            # v0.3: fixed dips from a near-binary speech gate
        env = np.convolve(np.abs(vo), np.ones(int(.1 * sr)) / int(.1 * sr), "same"); env /= env.max() + 1e-9
        speech = np.clip((env - .04) / .1, 0, 1); duck = np.zeros(N); lv = 0.
        aa, ar = 1 - np.exp(-48 / (.03 * sr)), 1 - np.exp(-48 / (.4 * sr))
        for k in range(0, N, 48):
            tg = speech[k]; lv += (tg - lv) * (aa if tg > lv else ar); duck[k:k + 48] = lv
        info.update(attack_ms=30, release_ms=400)
    elif mode == "envelope":
        hop = max(1, int(.005 * sr)); win = int(.02 * sr)
        b = _band(vo.astype(np.float64), sr)
        rms = np.sqrt(np.convolve(b ** 2, np.ones(win) / win, "same"))[::hop]
        edb = 20 * np.log10(rms + 1e-9); loud = float(np.percentile(edb[edb > edb.max() - 50], 95))
        rng = float(S.get("mix.duck_range_db", 30)); knee = 6.0
        tgt = np.clip((edb - (loud - rng)) / max(1.0, rng - knee), 0, 1)
        att = float(S.get("mix.duck_attack_ms", 40)) / 1000; rel = S.get("mix.duck_release_ms", "auto")
        lo_r, hi_r = (float(x) / 1000 for x in (S.get("mix.duck_release_range_ms") or [250, 400]))
        syl = syllable_hz(edb, hop / sr, loud - rng)
        if str(rel).strip().lower() == "auto": rel = float(np.clip(1.25 / syl, lo_r, hi_r)) if syl else (lo_r + hi_r) / 2
        else: rel = float(rel) / 1000
        aa, ar = 1 - np.exp(-hop / (att * sr)), 1 - np.exp(-hop / (rel * sr))
        lv = 0.0; d = np.zeros(len(tgt))
        for k, x in enumerate(tgt):
            lv += (x - lv) * (aa if x > lv else ar); d[k] = lv
        duck = np.repeat(d, hop)[:N]; duck = np.pad(duck, (0, N - len(duck)), mode="edge")
        info.update(attack_ms=round(att * 1000, 1), release_ms=round(rel * 1000, 1), syllable_hz=round(syl, 2) if syl else None,
                    voice_loud_db=round(loud, 1), range_db=rng)
    else:
        raise SystemExit(f"mix.duck_mode must be envelope | gate (got {mode!r})")
    la = int(float(S.get("sound.duck_lookahead_s", .12)) * sr)
    if la: duck = np.concatenate([duck[la:], np.full(min(la, N), duck[-1])])[:N]          # look-ahead
    info["lookahead_ms"] = round(la / sr * 1000, 1)
    return duck, info

def apply_duck(y, duck, S, sr):
    """frequency-split ducking of a (N, ch) bed: voice band by sound.duck_voice_band_db x control, the rest by
    sound.duck_other_db x control"""
    from scipy.signal import butter, sosfiltfilt
    lo = sosfiltfilt(butter(4, 250, "low", fs=sr, output="sos"), y, axis=0); hi = sosfiltfilt(butter(4, 5000, "high", fs=sr, output="sos"), y, axis=0)
    g_o = (10 ** (float(S.get("sound.duck_other_db", -3)) / 20)) ** duck; g_v = (10 ** (float(S.get("sound.duck_voice_band_db", -8)) / 20)) ** duck
    return (lo + hi) * g_o[:, None] + (y - lo - hi) * g_v[:, None]


# ------------------------------------------------------------------ vocal-to-music guarantee
def _band_power(x, sr, lo, hi, win_s, hop_s, rate=16000):
    """power of x (mono) in [lo, hi] Hz per hop: Hann-windowed FFT frames of win_s seconds centred every hop_s, at 16 kHz
    (the vocal-to-music ratio measure)"""
    from scipy.signal import resample_poly
    from math import gcd
    x = np.asarray(x, np.float64)
    if sr != rate: g = gcd(int(sr), rate); x = resample_poly(x, rate // g, int(sr) // g)
    win, hop = int(win_s * rate), max(1, int(hop_s * rate)); hann = np.hanning(win)
    fr = np.fft.rfftfreq(win, 1 / rate); band = (fr >= lo) & (fr <= hi)
    xp = np.pad(x, (win // 2, win // 2)); n = len(x) // hop + 1; out = np.empty(n)
    for a in range(0, n, 256):                     # chunks of frames: bounded memory on long videos
        ks = np.arange(a, min(n, a + 256)) * hop
        F = np.abs(np.fft.rfft(np.stack([xp[k:k + win] for k in ks]) * hann, axis=1)) ** 2
        out[a:a + len(ks)] = F[:, band].sum(1)
    return out


def _fit_len(x, n):
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)), mode="edge")

def vmr_guard(vo, mus, sr, S, words=None, log=None):
    """music bed (N, ch) -> the bed with its speech band trimmed wherever the voice would not clear it.

    Envelope ducking sets the depth from the voice's own level, so a quiet word over a busy, bright bar can still sit
    under the music in the 1-4 kHz band where consonants live. Here the voice and the ducked bed are
    measured in that band (`mix.vmr_band_hz`) over `mix.vmr_window_s` Hann windows while a word is spoken (words.json,
    else the voice envelope); wherever the ratio is under `mix.vmr_min_db` the bed's band is cut by the shortfall, at most `mix.vmr_max_cut_db`, held over the window and
    smoothed (`mix.vmr_attack_ms` / `mix.vmr_release_ms`). Only that band of the music moves, only when needed: a
    dynamic, band-aware bed trim. Two passes (the first cut changes the next measurement). Returns (bed, info)."""
    from scipy.signal import butter, sosfiltfilt
    from scipy.ndimage import maximum_filter1d
    if not _on(S.get("mix.vmr_guard", True)): return mus, {"vmr_guard": "off"}
    lo, hi = [float(x) for x in (S.get("mix.vmr_band_hz") or [1000, 4000])]
    target = float(S.get("mix.vmr_min_db") if S.get("mix.vmr_min_db") is not None else 8.0)
    mx = float(S.get("mix.vmr_max_cut_db", 12.0)); win = int(float(S.get("mix.vmr_window_s", 0.4)) * sr); hop = max(1, int(.01 * sr))
    dm = lambda x: x.sum(1) / np.sqrt(x.shape[1]) if x.ndim > 1 else x      # ffmpeg's -ac 1 downmix
    N = len(vo); mono = dm(mus)
    if N < win or not np.abs(mono).max() > 0: return mus, {"vmr_guard": "nothing to guard"}
    t = np.arange(0, N // hop + 1) * hop / sr
    if words:
        sp = np.zeros(len(t), bool)
        for w in words:
            a, b = float(w[0]) - .05, float(w[1]) + .05; sp[(t >= a) & (t <= b)] = True
    else:
        e = _fit_len(10 * np.log10(_band_power(vo, sr, 250, 5000, .02, hop / sr) + 1e-14), len(t)); sp = e > e.max() - 30
    ws = win / sr; vdb = _fit_len(10 * np.log10(_band_power(vo, sr, lo, hi, ws, hop / sr) + 1e-14), len(t))
    sp &= vdb > np.median(vdb[sp]) - 20 if sp.any() else sp                       # the gaps between words do not count
    bandsos = butter(4, [max(20.0, lo * .8), min(sr / 2 * .95, hi * 1.25)], "band", fs=sr, output="sos")
    y = np.asarray(mus, np.float64); cut_db = np.zeros(len(t)); info = {"target_db": round(target, 1), "band_hz": [lo, hi]}
    for it in range(2):
        m = dm(y)
        mdb = _fit_len(10 * np.log10(_band_power(m, sr, lo, hi, ws, hop / sr) + 1e-14), len(t))
        short = np.where(sp, np.clip(target - (vdb - mdb), 0, mx), 0.0)
        if it == 0: info["share_under_before"] = round(float((short[sp] > 2.0).mean()) if sp.any() else 0.0, 3)
        if not short.any(): break
        need = maximum_filter1d(short, size=max(1, win // hop), mode="nearest")      # the whole window clears, not its centre
        cut_db = np.minimum(mx, cut_db + need)
        att, rel = float(S.get("mix.vmr_attack_ms", 30)) / 1000, float(S.get("mix.vmr_release_ms", 250)) / 1000
        aa, ar = 1 - np.exp(-hop / (att * sr)), 1 - np.exp(-hop / (rel * sr))
        sm = np.zeros(len(cut_db)); lv = 0.0
        for k in range(len(cut_db) - 1, -1, -1):        # backwards first: the cut is in place before the word (look-ahead)
            x = cut_db[k]; lv += (x - lv) * (aa if x > lv else ar); sm[k] = lv
        lv = 0.0
        for k in range(len(sm)):
            x = sm[k]; lv += (x - lv) * (aa if x > lv else ar); sm[k] = max(sm[k], lv)
        g = 10 ** (-np.interp(np.arange(N) / hop, np.arange(len(sm)), sm) / 20)
        band = sosfiltfilt(bandsos, np.asarray(mus, np.float64), axis=0)
        y = np.asarray(mus, np.float64) - band * (1 - (g[:, None] if y.ndim > 1 else g))
    m = dm(y)
    mdb = _fit_len(10 * np.log10(_band_power(m, sr, lo, hi, ws, hop / sr) + 1e-14), len(t)); r = (vdb - mdb)[sp]
    info.update(share_under_after=round(float((r < target - 2.0).mean()) if len(r) else 0.0, 3), max_cut_db=round(float(cut_db.max()), 1),
                trimmed_s=round(float((cut_db > .5).sum() * hop / sr), 2))
    if log is not None: log.append(info)
    return y.astype(np.float32), info
