"""Inspire v2 HEAR: what a reference sounds like, measured from its soundtrack (no separation model, no new dependency).

analyse(path) -> dict, one reference:
  voice        speech present?  1 s windows whose voice-band (250-3500 Hz) harmonic envelope swings at the syllable
               rate (3-8 Hz modulation, std of the band-passed dB envelope >= VOICE_MOD_DB); the share of speech time
  music        bed level in the gaps between words (p15 of the frame level inside speech windows) vs the voice peaks (p90);
               outside speech: the level of non-silent windows. Presence share = 1 s windows holding music
  gap_lu       bed - voice while speaking (LU-like: dB of frame energy; both measured in the same reference)
  duck_db      music level between phrases (>= 1 s without speech) minus the bed under the words (positive = ducked)
  tempo        librosa via beats.analyse() on the soundtrack (only when music is present), beat salience = onset
               strength on the beat grid vs everywhere (confidence)
  sfx          percussive onsets that are not on a beat (+-60 ms) and, inside speech, stronger than p95 (plosives are
               not SFX); per 10 s
  silences     near-silent moments (>= 25 dB under the running 2 s median, >= 0.15 s, not the first/last 0.3 s); with
               music present they are drop-outs used as a device, without music they are pauses
  energy       music level per second (dB re median) and its shape (inspire_feel.arc_shape); full-mix level per second
               (for the FEEL energy arc)"""
import os, subprocess, tempfile, wave
import numpy as np

SR, HOP, NFFT = 22050, 512, 2048
VOICE_MOD_DB = 2.2          # syllable-rate modulation (std, dB) that marks a speech window (DECISIONS: Inspire v2)
SILENCE_DROP_DB = 25.0
ONBEAT_S = 0.06
BED_BIAS_DB = 6.0           # music mean minus its 0.5 s window minima, when the reference has no music-only stretch to measure it


def _decode(path, max_s):
    from . import config as C
    try:
        r = subprocess.run([C.get("ffmpeg"), "-hide_banner", "-nostats", "-v", "error", "-t", str(max_s), "-i", path, "-vn",
                            "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired): return None
    y = np.frombuffer(r.stdout, np.float32)
    return y if len(y) > SR // 2 else None


def _runs(mask):
    """[(i0, i1)] of True runs"""
    m = np.r_[False, np.asarray(mask, bool), False]; d = np.diff(m.astype(int))
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def _write_wav(y, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y / (np.abs(y).max() + 1e-9) * .9, -1, 1) * 32767).astype(np.int16).tobytes())


def modulation_db(env_db, fps, lo=3.0, hi=8.0):
    """std (dB) of the lo..hi Hz band of a dB envelope (syllable-rate modulation)"""
    x = env_db - env_db.mean(); n = len(x)
    if n < 8: return 0.0
    F = np.fft.rfft(x * np.hanning(n)); f = np.fft.rfftfreq(n, 1 / fps)
    F[(f < lo) | (f > hi)] = 0
    return float(np.fft.irfft(F, n).std() * 1.63)        # 1.63 undoes the Hann window's power loss


def analyse(path, max_s=90.0, tempo_range=(60, 150)):
    import librosa
    from .inspire_feel import arc_shape
    y = _decode(path, max_s)
    if y is None: return dict(has_audio=False)
    dur = len(y) / SR
    S = np.abs(librosa.stft(y, n_fft=NFFT, hop_length=HOP)) ** 2
    H, P = librosa.decompose.hpss(S, margin=1.0)
    f = librosa.fft_frequencies(sr=SR, n_fft=NFFT); fps = SR / HOP
    vb = (f >= 250) & (f <= 3500)
    rms = librosa.feature.rms(y=y, frame_length=HOP, hop_length=HOP)[0]     # 23 ms frames: the gaps between words show
    n = min(len(rms), S.shape[1])
    L = 20 * np.log10(rms[:n] + 1e-6)                        # full mix, dBFS per frame
    V = 10 * np.log10(H[vb].sum(0)[:n] + 1e-10)
    top = float(np.percentile(L, 95))
    floor = max(top - 50, -70.0)                             # below this a frame is silent
    audible = L > floor
    # ---------------- speech windows (1 s, step 0.25 s)
    win, stp = int(round(fps)), max(1, int(round(fps / 4)))
    speech = np.zeros(n, bool); mods = []
    for i0 in range(0, max(1, n - win + 1), stp):
        seg = V[i0:i0 + win]
        if len(seg) < win // 2 or audible[i0:i0 + win].mean() < .3: mods.append(0.0); continue
        m = modulation_db(np.maximum(seg, seg.max() - 40), fps); mods.append(m)
        if m >= VOICE_MOD_DB: speech[i0:i0 + win] = True
    # close tiny holes, drop tiny islands
    for a, b in _runs(~speech):
        if 0 < a and b < n and b - a < .4 * fps: speech[a:b] = True
    for a, b in _runs(speech):
        if b - a < .8 * fps: speech[a:b] = False
    aud_n = max(1, int(audible.sum()))
    voice_share = float((speech & audible).sum() / aud_n)
    has_voice = bool(speech.sum() / fps >= 1.5 and voice_share >= .15)
    # ---------------- levels
    out = dict(has_audio=True, dur=round(dur, 2), voice=dict(present=has_voice, share=round(voice_share, 3),
               mod_db_p75=round(float(np.percentile(mods, 75)) if mods else 0.0, 2)))
    half = max(2, int(round(fps / 2)))
    def pw(x): return float(np.mean(10 ** (np.asarray(x) / 10)))
    def bed_of(a, b):     # the bed shows through the gaps between words: median of the 0.5 s window minima (dB)
        return float(np.median([L[i:i + half].min() for i in range(a, max(a + 1, b - half + 1), max(1, half // 2))]))
    voice_lvl = bed = bias = None
    sp_runs = [(a, b) for a, b in _runs(speech) if b - a >= half]
    # music outside speech: runs >= 1 s that are audible and not speech; its real mean vs the gap estimator = the bias
    nonsp = [(a, b) for a, b in _runs(~speech & audible) if b - a >= fps]
    out_lvl = float(np.median([bed_of(a, b) for a, b in nonsp])) if nonsp else None
    if nonsp: bias = float(np.median([10 * np.log10(pw(L[a:b]) + 1e-12) - bed_of(a, b) for a, b in nonsp]))
    if has_voice and sp_runs:
        bed = float(np.median([bed_of(a, b) for a, b in sp_runs]))
        voice_lvl = 10 * np.log10(pw(L[speech]) + 1e-12)     # speech frames' energy mean (voice + the bed under it)
    bed_present = bed is not None and bed > floor + 6 and bed > voice_lvl - 35
    # presence per 1 s window
    pres = []
    for i0 in range(0, n, win):
        sl = slice(i0, min(n, i0 + win))
        if speech[sl].mean() > .5:
            pres.append(bool(bed_of(sl.start, sl.stop) > max(floor + 6, (voice_lvl or top) - 35)))
        else:
            pres.append(bool(audible[sl].mean() > .6 and np.median(L[sl]) > top - 40))
    music_share = float(np.mean(pres)) if pres else 0.0
    has_music = music_share >= .3 and (not has_voice or bed_present or out_lvl is not None and out_lvl > floor + 10)
    out["music"] = dict(present=bool(has_music), share=round(music_share, 3))
    if has_voice and has_music and bed_present:
        out["gap_lu"] = round(float(np.clip(bed + (bias if bias is not None else BED_BIAS_DB) - voice_lvl, -30, 0)), 1)
        out["gap_bias"] = "measured" if bias is not None else "default"
        if out_lvl is not None: out["duck_db"] = round(out_lvl - bed, 1)
    out["levels"] = dict(voice=None if voice_lvl is None else round(voice_lvl, 1), bed=None if bed is None else round(bed, 1),
                         between=None if out_lvl is None else round(out_lvl, 1))
    # ---------------- tempo + beat grid (music only)
    beats = []
    if has_music:
        from . import beats as BT
        fd, p = tempfile.mkstemp(suffix=".wav"); os.close(fd)
        try:
            _write_wav(y, p)
            B = BT.analyse(p, tempo_range=tempo_range)
            beats = [b for b in B["beats"] if b <= dur]
            oenv = librosa.onset.onset_strength(S=librosa.power_to_db(P), sr=SR, hop_length=HOP)[:n]
            bi = np.clip(np.round(np.array(beats) * fps).astype(int), 0, len(oenv) - 1)
            sal = float(np.mean([oenv[max(0, i - 1):i + 2].max() for i in bi]) / (oenv.mean() + 1e-9)) if len(bi) else 0.0
            out["tempo"] = dict(bpm=B["tempo"], salience=round(sal, 2), bar_s=B["bar_s"], conf=round(float(np.clip((sal - 1) / 2, 0, 1)), 2))
        except SystemExit as e:
            out["tempo"] = dict(bpm=None, note=str(e)[:120])
        finally:
            try: os.remove(p)
            except OSError: pass
    out["beats"] = [round(float(b), 4) for b in beats]
    # ---------------- SFX / transients: onsets off the beat and half-beat grid (music's own 8ths are not SFX), strong ones
    oenv = librosa.onset.onset_strength(S=librosa.power_to_db(P), sr=SR, hop_length=HOP)[:n]
    on = [i for i in librosa.onset.onset_detect(onset_envelope=oenv, sr=SR, hop_length=HOP, units="frames", backtrack=False) if i < n]
    strong = float(np.percentile(oenv, 95)) if len(oenv) else 0
    mid = float(np.percentile([oenv[i] for i in on], 75)) if on else 0
    grid = np.array(beats)
    if len(grid) >= 2: grid = np.sort(np.r_[grid, (grid[:-1] + grid[1:]) / 2])
    sfx = []
    for i in on:
        tt = i / fps
        if not audible[i]: continue
        if len(grid) and np.min(np.abs(grid - tt)) <= ONBEAT_S: continue
        if oenv[i] < (strong if speech[i] else mid): continue
        sfx.append(round(float(tt), 3))
    out["sfx"] = dict(times=sfx, per_10s=round(len(sfx) / max(dur, 1e-3) * 10, 2))
    # ---------------- silences / drop-outs
    k = int(2 * fps) | 1
    med = np.array([np.median(L[max(0, i - k // 2):i + k // 2 + 1]) for i in range(n)])
    low = (L < med - SILENCE_DROP_DB) | (L < floor)
    sil = []
    for a, b in _runs(low):
        if a / fps < .3 or b / fps > dur - .3 or (b - a) / fps < .15: continue
        sil.append([round(a / fps, 2), round((b - a) / fps, 2)])
    out["silences"] = dict(kind="dropout" if has_music else "pause", events=sil, per_30s=round(len(sil) / max(dur, 1e-3) * 30, 2))
    # ---------------- energy per second
    sec = [(int(i * fps), int(min(n, (i + 1) * fps))) for i in range(int(np.ceil(dur)))]
    mix_db = [round(float(10 * np.log10(np.mean(10 ** (L[a:b] / 10)) + 1e-10)), 1) if b > a else None for a, b in sec]
    mus = []
    for a, b in sec:
        if b <= a: mus.append(None); continue
        mus.append(bed_of(a, b) if speech[a:b].mean() > .5 else float(np.median(L[a:b])))
    mv = np.array([m for m in mus if m is not None]); md = float(np.median(mv)) if len(mv) else 0
    out["energy"] = dict(mix_db=mix_db, music_db=[None if m is None else round(m - md, 1) for m in mus])
    if has_music and len(mv) >= 4:
        out["energy"]["music_shape"] = arc_shape(np.array([10 ** ((m - md) / 20) for m in mv]))
    return out


def summary_line(a):
    if not a or not a.get("has_audio"): return "no audio"
    s = ["voice" if a["voice"]["present"] else "no voice", f"music {a['music']['share']:.0%}" if a["music"]["present"] else "no music"]
    if (a.get("tempo") or {}).get("bpm"): s.append(f"{a['tempo']['bpm']:.0f} BPM")
    if a.get("gap_lu") is not None: s.append(f"bed {a['gap_lu']:+.1f} LU under the voice")
    s.append(f"{a['sfx']['per_10s']:.1f} SFX / 10 s")
    return ", ".join(s)


def derive(R, ev):
    """sound.* / rhythm.* keys from the HEAR analysis of the references in R (median / mode across them)"""
    import collections
    H = [r["hear"] for r in R if (r.get("hear") or {}).get("has_audio")]
    if not H: return
    n = len(H); names = lambda xs: ", ".join(f"{x:g}" for x in xs)
    voiced = [h["voice"]["present"] for h in H]; k = sum(voiced)
    ev.put("rhythm.voice", k * 2 >= n, f"speech (syllable-rate modulation in the voice band) in {k}/{n} refs; voice share "
           f"{names([round(h['voice']['share'], 2) for h in H])}", n, (.55 + .1 * n) if k in (0, n) else .35)
    ms = [h["music"]["share"] for h in H]
    ev.put("rhythm.music_share", round(float(np.median(ms)), 2), f"share of 1 s windows holding music per ref: {names([round(x, 2) for x in ms])}", n, .5 + .05 * n)
    gaps = [h for h in H if h.get("gap_lu") is not None]
    if gaps:
        g = [h["gap_lu"] for h in gaps]; meas = all(h.get("gap_bias") == "measured" for h in gaps)
        ev.put("sound.bed_lu", round(float(np.clip(np.median(g), -20, -3)), 1),
               f"music bed under the words (0.5 s window minima + {'measured' if meas else 'default'} min-to-mean offset) vs the speech level, per ref {names(g)} LU",
               len(g), .55 if meas else .42)
    du = [h["duck_db"] for h in H if h.get("duck_db") is not None]
    if du:
        ev.put("sound.duck_other_db", round(float(np.clip(-np.median(du), -12, 0)), 1),
               f"music level between phrases minus under the words, per ref {names(du)} dB (whole spectrum; the voice-band duck is not separable)", len(du), .45)
    T = [h["tempo"] for h in H if (h.get("tempo") or {}).get("bpm")]
    if T:
        b = [t["bpm"] for t in T]; spread = (max(b) - min(b)) / max(np.median(b), 1)
        ev.put("rhythm.tempo_bpm", round(float(np.median(b)), 1), f"librosa beat tracker on each soundtrack: {names(b)} BPM (beat salience "
               f"{names([t['salience'] for t in T])})", len(T), float(np.mean([t['conf'] for t in T])) * (1 if spread < .08 else .6))
    sx = [h["sfx"]["per_10s"] for h in H]
    ev.put("rhythm.sfx_per_10s", round(float(np.median(sx)), 1), f"strong onsets off the beat / half-beat grid (speech plosives excluded) per 10 s: {names(sx)}", n, .5)
    dr = [h["silences"]["per_30s"] for h in H if h["silences"]["kind"] == "dropout"]
    if dr:
        ev.put("rhythm.dropouts_per_30s", round(float(np.median(dr)), 1), f"music drop-outs (>= 25 dB under the 2 s median, >= 0.15 s) per 30 s: {names(dr)}", len(dr), .5)
    sh = [h["energy"]["music_shape"] for h in H if (h.get("energy") or {}).get("music_shape")]
    if sh:
        c = collections.Counter(sh); m, cn = c.most_common(1)[0]
        ev.put("rhythm.music_energy", m, f"music level per second, shape per ref: {dict(c)}", len(sh), (.4 + .1 * len(sh)) * cn / len(sh))
