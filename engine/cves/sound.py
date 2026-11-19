"""Senior sound: automatic accents (risers into the hook / payoff, impacts on reveals) and voice-envelope ducking.

Accents (`accents()`, called by mix.all_cues, so `cves mix` and the SND gates see the same cue list):
  * a riser whose PEAK lands on the payoff (the drop moment: music.drop_cut, else the first music.drop_beats clip,
    else the reveal) and one into the hook (music.hook_cut / the first music.hook_beats clip when there is room before
    it, else resolving where the hook hands over to the body);
  * an impact (a downbeat hit, layered with the music drop) on the payoff, and on reveals / big text slams whose own
    cues carry no low hit;
  * rate-limited by the restraint budget `creative.sound_accents_per_30s` (payoff riser, payoff impact, hook riser,
    then reveals in time order), never on a moment that already has a riser / impact of its own, and only on a target
    within one frame of a picture event (a cut, a cutaway edge, the end card, the punch-in), so SND-07 holds;
  * sounds are chosen from the SFX bank by category + intensity (cves.sfx), the riser by the room before its target and
    only among risers that resolve (peak within `sound.accents.riser_tail_max_s` of their end).
  Every accent is an ordinary cue (t, id, gain, kw) with kw {accent, target, why}: SND-32 checks the riser peaks.

Ducking (`duck_control()` + `apply_duck()`, `mix.duck_mode`):
  envelope  (default) the music gain follows the voice-band RMS envelope: 0 at `mix.duck_range_db` under the voice's
            loud level, full depth from 6 dB under it; attack `mix.duck_attack_ms`, release `mix.duck_release_ms`
            (`auto` = 1.25 x the measured syllable period, clamped to `mix.duck_release_range_ms`), look-ahead
            `sound.duck_lookahead_s`. Depth from the style: `sound.duck_voice_band_db` (250 Hz-5 kHz) and
            `sound.duck_other_db` (lows + highs), the same frequency split as before.
  gate      the v0.3 fixed dips: a near-binary speech gate (100 ms |voice| average), 30 ms attack, 400 ms release."""
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
    budget = int(np.floor(float(S.get("creative.sound_accents_per_30s", 3)) * max(1.0, T / 30.0) + 1e-9))
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
    out, used, taken = [], [], {}
    for pri, kind, tgt, why, inten in sorted(want, key=lambda w: (w[0], w[2])):
        rec = {"kind": kind, "target": round(tgt, 4), "why": why}; log.append(rec)
        e = _nearest(ev, tgt, fr)
        if e is None: rec["status"] = f"skipped: no picture event within 1 frame of {tgt:.3f} s (SND-07)"; continue
        tgt = e; rec["target"] = round(tgt, 4)
        if kind == "riser" and any("riser" in n and abs((kw.get("peak_at") if kw.get("peak_at") is not None else t) - tgt) <= .5 for t, n, _, kw in cues):
            rec["status"] = "skipped: the moment already has a riser"; continue
        if kind == "impact" and any(any(f in n for f in IMPACT_FAMILY) and abs(t - tgt) <= 2 * fr for t, n, _, kw in cues if not kw.get("accent")):
            rec["status"] = "skipped: the moment already has a low hit"; continue
        if len(out) >= budget: rec["status"] = f"skipped: restraint budget ({budget} accents for {T:.1f} s, creative.sound_accents_per_30s)"; continue
        if kind == "riser":
            prev = max([u for u in used if u < tgt - 1e-6] + [0.0])       # a riser starts after the accent before it
            room = tgt - prev - (gap if prev > 0 else 0.0)
            if room < r_min: rec["status"] = f"skipped: {room:.2f} s of room before the target (< sound.accents.riser_min_s {r_min})"; continue
            s = SFX.pick(risers, "riser", inten, exclude=[taken.get("riser")] if taken.get("riser") else (), max_s=min(r_max, room), min_s=r_min)
            if s is None or float(s["duration_s"]) > room + 1e-6: rec["status"] = "skipped: no resolving riser in the bank fits the room"; continue
            out.append((tgt - float(s["peak_at_s"]), s["id"], r_gain, {"peak_at": tgt, "accent": "riser", "target": tgt, "beat_snap": False, "why": why}))
        else:
            imx = float(A.get("impact_max_s", 2.0))
            s = SFX.pick(cands, "impact", inten, exclude=[taken.get("impact")] if taken.get("impact") else ())
            if s is None: rec["status"] = "skipped: no impact in the bank"; continue
            kw = {"accent": "impact", "target": tgt, "reveal": True, "beat_snap": False, "why": why}
            if float(s["duration_s"]) > imx: kw["trim"] = (0, imx)          # a long recorded boom: its first impact_max_s
            out.append((tgt, s["id"], i_gain, kw))
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
