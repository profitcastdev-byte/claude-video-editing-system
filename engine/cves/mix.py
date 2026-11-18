"""Mix: voice_final + music (placed and fitted by beats.plan, frequency-split ducking with look-ahead) + SFX (template cues + extras)
-> Edit/mix_premaster.wav, Edit/mix.wav (style sound.master_lufs / sound.true_peak; default -14 LUFS, <= -1 dBTP) and stems (Edit/stems/voice|music|sfx.wav).
Levels come from the style (`sound.*`); music placement / fit / beat sync from `music.*` (docs/MUSIC.md).
Cue post-pass (all_cues): transition whooshes are placed by their measured PEAK on the cut (SND-08), identical back-to-back
repeats get a deterministic pitch / gain variation (SND-09), and in `music.sync: full` transition-type cues are nudged so
their peak lands on the beat (never more than `music.sfx_snap_max_f` frames, so they stay on their picture event)."""
import os, re, json, subprocess, tempfile, shutil
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfiltfilt
from . import config as C, templates as TPL, beats as BT
from .render import Timeline

SR = 48000
def db(x): return 10 ** (x / 20)
def lufs(path):
    r = subprocess.run([C.get("ffmpeg"), "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])

def sfx_bank(TL):
    roots = [TL.pr.p("Music", "sfx"), os.path.join(TL.root, "assets", "sfx")]
    def find(name):
        if name.startswith("asset:"):         # media templates' own audio (video_broll audio: true): an asset id
            from . import assets
            p = assets.resolve(TL.pr, name[6:])
            if p is None: raise SystemExit(f"audio cue '{name}': no such asset; add it with `cves assets add`")
            return p
        for r in roots:
            for ext in (".mp3", ".wav"):
                if os.path.exists(os.path.join(r, name + ext)): return os.path.join(r, name + ext)
        raise SystemExit(f"sfx '{name}' not found in {roots}")
    return find

# ------------------------------------------------------------------ SFX peak offsets (measured, cached)
_PEAKS = {}
def peak_offset(TL, name, kw):
    """seconds from the start of the (trimmed) SFX to its loudness peak: 10 ms RMS envelope argmax, the same
    measure the SND-08 gate uses. Cached in memory and in Edit/sfx_peaks.json (keyed by file, mtime and trim)."""
    path = sfx_bank(TL)(name); tr = kw.get("trim"); key = f"{os.path.abspath(path)}|{int(os.path.getmtime(path))}|{tr}"
    if key in _PEAKS: return _PEAKS[key]
    cf = TL.pr.e("sfx_peaks.json"); disk = {}
    if os.path.exists(cf):
        try: disk = json.load(open(cf, encoding="utf-8"))
        except ValueError: disk = {}
    if key not in disk:
        y, _ = librosa.load(path, sr=SR, mono=True)
        if tr: y = y[int(tr[0] * SR):int(tr[1] * SR)]
        env = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")) if len(y) else np.zeros(1)
        disk[key] = round(int(np.argmax(env)) / SR, 5)
        try:
            with open(cf, "w", encoding="utf-8") as f: json.dump(disk, f, indent=1)
        except OSError: pass
    _PEAKS[key] = disk[key]; return disk[key]

def _trans_cue(TL, t_cut, kind, side):
    """the SFX for a transition at t_cut. style sound.transition_sfx maps kind -> sound (null = none)."""
    m = TL.S.get("sound.transition_sfx") or {}
    name = m.get(kind, m.get("default"))
    if not name: return []
    if name == "whoosh": return [(t_cut - .30, "whoosh", -15, {"trim": (0, .45), "peak_at": t_cut})]     # placed by peak below
    return [(t_cut - .04, name, -19, {"trim": (0, .18)})]

def all_cues(TL, plan=None, log=None, finalize=True):
    cues = []
    din, dout = TL.S.get("transitions.in", "cut"), TL.S.get("transitions.out", "cut")
    for c in TL.cuts:
        cues += TPL.get(c["template"])[1](c.get("params", {}), TL.ctx(c["start"], c["end"]))
        cues += _trans_cue(TL, c["start"], c.get("in", din), "in") + _trans_cue(TL, c["end"], c.get("out", dout), "out")
    for sid, r in TL.roto.items():
        s = next(x for x in TL.segs if x["id"] == sid); cues += TPL.get(r["template"])[1](r.get("params", {}), TL.ctx(s["t0"], s["t1"]))
    seen = set()
    for sid, cs in TL.chest.items():
        for c in cs:
            if id(c) in seen: continue           # a chest graphic spanning several segments cues once
            seen.add(id(c)); s = next(x for x in TL.segs if x["id"] == sid)
            cues += TPL.get(c["template"])[1](c.get("params", {}), TL.ctx(s["t0"], s["t1"]))
    if TL.END:
        e = TL.E["end_card"]; cues += _trans_cue(TL, TL.T_END, e.get("in", din), "in")
        cues += TPL.get(e["template"])[1](e.get("params", {}), TL.ctx(TL.T_END, TL.T_END + TL.END))
    if TL.snap: cues += [(TL.snap[0] - .01, "lowhit", -9, {"reveal": True}), (TL.snap[0] - .01, "boom", -16, {"trim": (0, 1.2), "reveal": True})]
    for x in (TL.E.get("sfx", {}) or {}).get("extra", []): cues.append((x["t"], x["name"], x.get("gain", -18), {k: v for k, v in x.items() if k in ("trim", "pitch", "beat_snap", "speed", "raw")}))
    return _finalize(TL, cues, plan, log) if finalize else cues

def _finalize(TL, cues, plan=None, log=None):
    """peak placement (SND-08) -> beat nudge (music.sync full) -> repeat variation (SND-09). Deterministic."""
    out = []
    for t, name, gain, kw in cues:
        if kw.get("peak_at") is not None: t = kw["peak_at"] - peak_offset(TL, name, kw)
        out.append((t, name, gain, dict(kw)))
    c = BT.cfg(TL.pr, TL.S)
    if BT.mode_of(c) == "full" and (TL.E.get("music") or {}).get("file"):
        P = plan or BT.plan(TL.pr, TL)
        grid = np.asarray(P.get("beats") or []); tol = P["tolerance"]
        mx = float(c.get("sfx_snap_max_f", 1)) / TL.FPS; kinds = [str(k) for k in (c.get("sfx_snap") or [])]
        if len(grid):
            for k, (t, name, gain, kw) in enumerate(out):
                if name.startswith("asset:") or not kw.get("beat_snap", True) or not any(s in name for s in kinds): continue
                pk = t + peak_offset(TL, name, kw); j = int(np.argmin(np.abs(grid - pk))); d = float(grid[j] - pk)
                if 1e-4 < abs(d) <= min(tol, mx):
                    out[k] = (t + d, name, gain, kw)
                    if log is not None: log.append((name, pk, pk + d))
    out.sort(key=lambda x: x[0])
    st = float(TL.S.get("sound.repeat_pitch_st", 1)); gd = float(TL.S.get("sound.repeat_gain_db", 1.5))
    prev, nvar = None, {}
    for k, (t, name, gain, kw) in enumerate(out):          # SND-09: never the same sound twice in a row
        base, p = name, kw.get("pitch", 0)          # by name, like the SND-09 gate (a different trim of one file still sounds the same)
        if name.startswith("asset:"): prev = None; continue            # media audio is never varied
        if prev == (base, p) and (st or gd):
            n = nvar.get(base, 0); nvar[base] = n + 1; sgn = 1 if n % 2 == 0 else -1
            kw["pitch"] = p + sgn * st; out[k] = (t, name, gain - sgn * gd, kw); p = kw["pitch"]
        prev = (base, p)
    return out

# ------------------------------------------------------------------ music bed
def _music(pr, TL, P, N, T):
    """(N, 2) music bed before ducking, laid out by beats.plan (bar-aware fit) or the legacy offset + 0.9 s fade."""
    if P["fit"] == "bars" and P.get("lay"):
        y, _ = librosa.load(P["file"], sr=SR, mono=False)
        y = y if y.ndim == 2 else np.stack([y, y])
        return BT.render(y[:2], SR, P["lay"], N), False
    y, _ = librosa.load(P["file"], sr=SR, mono=False, offset=max(0, P["offset"]), duration=T + 1)
    y = y if y.ndim == 2 else np.stack([y, y]); y = np.pad(y, ((0, 0), (0, max(0, N - y.shape[1]))))[:, :N].T
    return y, True

def mix(pr):
    TL = Timeline(pr); T = TL.N / TL.FPS; N = int(T * SR); find = sfx_bank(TL)
    vo, _ = librosa.load(pr.e("voice_final.wav"), sr=SR, mono=True); vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
    M = TL.E.get("music") or {}; mus = np.zeros((N, 2), np.float32); SND = TL.S.get("sound") or {}
    bed_lu = M.get("bed_lu", SND.get("bed_lu", -10)); tmp = tempfile.mkdtemp(prefix="cves_mix_")
    TV, TM, TB = (os.path.join(tmp, f"{k}.wav") for k in "vmb")
    P = BT.plan(pr, TL) if M.get("file") else None
    if P:
        y, legacy_fade = _music(pr, TL, P, N, T)
        sf.write(TV, vo, SR); sf.write(TM, y, SR)
        y *= db(lufs(TV) - lufs(TM) + bed_lu + 3)   # +3: ducking takes ~3 LU back off
        env = np.convolve(np.abs(vo), np.ones(int(.1 * SR)) / int(.1 * SR), "same"); env /= env.max() + 1e-9
        speech = np.clip((env - .04) / .1, 0, 1); duck = np.zeros(N); lv = 0.
        aa, ar = 1 - np.exp(-48 / (.03 * SR)), 1 - np.exp(-48 / (.4 * SR))
        for k in range(0, N, 48):
            tg = speech[k]; lv += (tg - lv) * (aa if tg > lv else ar); duck[k:k + 48] = lv
        la = int(SND.get("duck_lookahead_s", .12) * SR); duck = np.concatenate([duck[la:], np.full(la, duck[-1])])         # look-ahead
        lo = sosfiltfilt(butter(4, 250, "low", fs=SR, output="sos"), y, axis=0); hi = sosfiltfilt(butter(4, 5000, "high", fs=SR, output="sos"), y, axis=0)
        y = (lo + hi) * (db(SND.get("duck_other_db", -3)) ** duck)[:, None] + (y - lo - hi) * (db(SND.get("duck_voice_band_db", -8)) ** duck)[:, None]
        if legacy_fade: fo = int(.9 * SR); y[N - fo:] *= (np.linspace(1, 0, fo) ** 1.5)[:, None]
        mus = y.astype(np.float32); music_target = bed_lu
    sfx = np.zeros(N, np.float32); cache = {}; snaps = []; cues = all_cues(TL, plan=P, log=snaps)
    for t, name, gain, kw in cues:
        sp = float(kw.get("speed", 1) or 1); key = (name, str(kw.get("trim")), kw.get("pitch", 0), sp, bool(kw.get("raw")))
        if key not in cache:
            y, _ = librosa.load(find(name), sr=SR, mono=True)
            if kw.get("trim"): y = y[int(kw["trim"][0] * SR):int(kw["trim"][1] * SR)]
            if sp != 1 and len(y) > 2048: y = librosa.effects.time_stretch(y, rate=sp)      # media clip played at speed
            if kw.get("pitch"): y = librosa.effects.pitch_shift(y, sr=SR, n_steps=kw["pitch"])
            f = min(int(.006 * SR), len(y) // 4)
            if f: y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
            cache[key] = y if kw.get("raw") else y / (np.abs(y).max() + 1e-9)      # raw: media audio keeps its own level
        y = cache[key]; g = gain if kw.get("reveal") else gain + SND.get("sfx_offset_db", -3); i = int(round(t * SR)); j = min(N, i + len(y))
        if i < 0: y, i = y[-i:], 0                      # a cue placed before 0 keeps its peak where it belongs
        if i < N: sfx[i:j] += y[:j - i] * db(g)
    if M.get("file"):     # measure the real bed (music + SFX) vs voice and correct the music gain: no guessed compensation
        sf.write(TV, vo, SR)
        for _ in range(3):
            sf.write(TB, mus.mean(1) + sfx, SR); err = music_target - (lufs(TB) - lufs(TV))
            if abs(err) < .3: break
            mus *= db(err)
    os.makedirs(pr.e("stems"), exist_ok=True)
    sf.write(pr.e("stems", "voice.wav"), vo, SR); sf.write(pr.e("stems", "music.wav"), mus, SR); sf.write(pr.e("stems", "sfx.wav"), sfx, SR)
    mixd = (vo + sfx)[:, None] + mus
    pk = max(1., np.abs(mixd).max() * 1.05); sf.write(pr.e("mix_premaster.wav"), mixd / pk, SR)
    for st in ("voice", "music", "sfx"):     # stems at the same scale as the premaster (for control-mode faders)
        y, _ = sf.read(pr.e("stems", f"{st}.wav")); sf.write(pr.e("stems", f"{st}.wav"), y / pk, SR)
    shutil.rmtree(tmp, ignore_errors=True)
    target = SND.get("master_lufs", -14); lim = SND.get("true_peak", -1.0) - 1.0      # limiter ceiling 1 dB under the TP target (inter-sample headroom)
    g = target - lufs(pr.e("mix_premaster.wav"))
    for _ in range(4):
        subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-i", pr.e("mix_premaster.wav"), "-af",
                        f"volume={g:.2f}dB,alimiter=limit={db(lim):.4f}:attack=3:release=60:level=false", "-ar", str(SR), pr.e("mix.wav")], check=True)
        err = target - lufs(pr.e("mix.wav"))
        if abs(err) < .2: break
        g += err
    info = {"master_gain_db": round(g, 2), "cues": len(cues), "peak_placed": sum(1 for c in cues if c[3].get("peak_at") is not None),
            "beat_nudged": len(snaps)}
    if P:
        lay = P.get("lay") or {}
        info["music"] = {"sync": P["mode"], "fit": P["fit"], "offset_s": round(P["offset"], 3), "drop": P["drop"],
                         "loops": lay.get("loops", 0), "end": lay.get("end"), "notes": P["notes"]}
    pr.save_json("mix.json", info)
    return T
