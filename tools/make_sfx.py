#!/usr/bin/env python3
"""Synthesize the CVES house SFX (CC0, synthesized by CVES) into assets/sfx/ and (re)write assets/sfx/manifest.yaml.

    python tools/make_sfx.py [--out assets/sfx] [--only riser_air,impact_sub] [--no-manifest]

Every sound is made from numpy noise and tones (no samples, no downloads), deterministic (fixed seeds), 48 kHz mono
16-bit WAV, peak -1 dBFS:
  risers       filtered-noise sweeps rising in pitch and level, with rising tones; the PEAK is the last ~20 ms, so a
               riser placed by its peak resolves exactly on its target (SND-32);
  impacts      pitched decays (sub drops, a thud, a hard hit with a noise body and a short room tail);
  whooshes     band-pass noise swept up then down under a bell envelope, with a little Doppler tilt;
  ui / pop     short clicks, ticks and bubble pops;
  ambience     a soft, loopable room tone.
The 13 recordings already in assets/sfx (Freesound CC0, see CREDITS.md) are catalogued in the manifest too.
Listen before committing a change: `earshot describe` / `earshot realness` on each file (docs/SOUND.md)."""
import argparse, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))
SR = 48000

# the recordings already in the repo (Freesound CC0, 2026-11-17): id -> (category, intensity, title, source)
RECORDED = {
    "lowhit": ("impact", "medium", "LowHit 01", "https://cdn.freesound.org/previews/336/336495_5866833-hq.mp3"),
    "boom": ("impact", "hard", "Bass Boom", "https://cdn.freesound.org/previews/268/268084_3812550-hq.mp3"),
    "whoosh": ("whoosh", "medium", "Swosh swoosh whoosh", "https://cdn.freesound.org/previews/60/60026_71257-hq.mp3"),
    "swipe": ("transition", "soft", "Swipe Whoosh", "https://cdn.freesound.org/previews/60/60007_71257-hq.mp3"),
    "riser": ("riser", "medium", "Riser", "https://cdn.freesound.org/previews/561/561207_10825267-hq.mp3"),
    "pop": ("pop", "soft", "Pop 2", "https://cdn.freesound.org/previews/244/244654_3624044-hq.mp3"),
    "ding": ("ui", "soft", "glass ding", "https://cdn.freesound.org/previews/66/66876_874154-hq.mp3"),
    "button": ("ui", "soft", "Button Pressed", "https://cdn.freesound.org/previews/367/367852_6512973-hq.mp3"),
    "switch": ("ui", "medium", "Light Switch Turn Off", "https://cdn.freesound.org/previews/440/440499_4629347-hq.mp3"),
    "card": ("ui", "soft", "card.wav", "https://cdn.freesound.org/previews/147/147532_2641011-hq.mp3"),
    "keyboard": ("ui", "medium", "Keyboard Typing", "https://cdn.freesound.org/previews/379/379418_6207707-hq.mp3"),
    "scribble": ("ui", "soft", "scribble", "https://cdn.freesound.org/previews/82/82610_1316563-hq.mp3"),
    "ring": ("ui", "medium", "Phone Ringing Sound", "https://cdn.freesound.org/previews/528/528111_11684955-hq.mp3"),
}


# ------------------------------------------------------------------ building blocks
def t_of(d): return np.arange(int(d * SR)) / SR

def noise(n, seed, color="white"):
    r = np.random.default_rng(seed); x = r.standard_normal(n)
    if color == "pink":
        X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1 / SR); X[1:] /= np.sqrt(f[1:]); X[0] = 0; x = np.fft.irfft(X, n)
    return x / (np.abs(x).max() + 1e-12)

def swept_band(x, fc, q=1.4, nfft=1024):
    """time-varying band-pass of x: centre fc[t] (Hz, one value per sample), bandwidth fc/q (STFT domain)"""
    from scipy.signal import stft, istft
    f, tt, Z = stft(x, SR, nperseg=nfft, noverlap=nfft * 3 // 4)
    idx = np.clip((tt * SR).astype(int), 0, len(fc) - 1); c = fc[idx][None, :]; bw = c / q
    Z = Z * np.exp(-.5 * ((f[:, None] - c) / (bw / 2.355 + 1e-9)) ** 2)
    _, y = istft(Z, SR, nperseg=nfft, noverlap=nfft * 3 // 4)
    y = np.real(y)[:len(x)]
    return np.pad(y, (0, len(x) - len(y)))

def lowpass(x, fc, order=4):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)

def highpass(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)

def tone(f, phase0=0.0):
    """sine with a per-sample frequency array f (Hz)"""
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase0)

def fades(y, a=.003, b=.008):
    na, nb = int(a * SR), int(b * SR)
    if na: y[:na] *= np.linspace(0, 1, na)
    if nb: y[-nb:] *= np.linspace(1, 0, nb)
    return y

def room(y, seed, decay=.25, mix=.12):
    """a short diffuse tail: the signal convolved with exponentially decaying low-passed noise"""
    n = int(decay * 3 * SR); ir = lowpass(noise(n, seed + 99), 5000) * np.exp(-np.arange(n) / SR / decay * 3)
    ir /= np.sqrt((ir ** 2).sum()) + 1e-12
    wet = np.convolve(y, ir)[:len(y) + n]; wet = np.pad(wet, (0, len(y) + n - len(wet)))
    out = np.pad(y, (0, n)) * (1 - mix) + wet * mix * 1.5
    return out

def norm(y, peak_db=-1.0):
    return y / (np.abs(y).max() + 1e-12) * 10 ** (peak_db / 20)


# ------------------------------------------------------------------ the sounds
def riser(d, seed, f0=300, f1=7000, tone0=110, tone1=440, grit=.0, curve=2.2, tail=.012):
    """noise swept f0 -> f1 + two detuned tones gliding tone0 -> tone1; level rises as (t/d)^curve and peaks at the end"""
    t = t_of(d); u = t / d
    fc = f0 * (f1 / f0) ** (u ** 1.3)
    nz = swept_band(noise(len(t), seed), fc, q=2.0)
    nz = nz / (np.abs(nz).max() + 1e-9)
    ft = tone0 * (tone1 / tone0) ** (u ** 1.6)
    tn = .55 * tone(ft) + .35 * tone(ft * 1.007, 1.3) + .2 * tone(ft * 2.003, .4)
    trem = 1 - .25 * (1 - u ** 8) * (.5 + .5 * np.sin(2 * np.pi * np.cumsum(3 + 14 * u ** 2) / SR))       # accelerating flutter, gone at the peak
    y = (nz * (1 + grit) + .3 * tn * trem) * (u ** curve)
    nc = int(.05 * SR); y[-nc:] *= 1 + .6 * np.linspace(0, 1, nc) ** 2        # a crest in the last 50 ms: the peak IS the resolve point
    nt = int(tail * SR); y[-nt:] *= np.linspace(1, .85, nt)        # the peak is ~tail before the end; no click
    return fades(y, .01, .004)

def impact(d, seed, f0=70, f1=38, body=.0, click=.4, decay=.35, tail=.0, lp=9000):
    t = t_of(d)
    f = f1 + (f0 - f1) * np.exp(-t / .06)
    sub = tone(f) * np.exp(-t / decay)
    ck = lowpass(noise(len(t), seed), lp) * np.exp(-t / .004) * click
    bd = lowpass(noise(len(t), seed + 1), 900) * np.exp(-t / (decay * .45)) * body
    y = sub + ck + bd
    if tail: y = room(y, seed, decay=tail)[:len(t)]
    return fades(y, .0005, .05)

def whoosh(d, seed, f_lo=500, f_hi=3500, peak=.55, q=1.6):
    """bell-shaped pass-by: centre frequency rises to f_hi at the peak and falls (Doppler), level peaks at `peak`"""
    t = t_of(d); u = t / d
    bell = np.exp(-.5 * ((u - peak) / (.22 if u.size else 1)) ** 2) * np.where(u < peak, 1, np.exp(-(u - peak) * 2.5))
    fc = f_lo + (f_hi - f_lo) * np.exp(-.5 * ((u - peak) / .25) ** 2)
    y = swept_band(noise(len(t), seed, "pink"), fc, q=q) * bell
    return fades(y, .004, .02)

def pop(d, seed, f0=1100, f1=380, decay=.03):
    t = t_of(d); f = f1 + (f0 - f1) * np.exp(-t / .012)
    y = tone(f) * np.exp(-t / decay) + .15 * lowpass(noise(len(t), seed), 6000) * np.exp(-t / .002)
    return fades(y, .0005, .01)

def tick(d, seed, f=3200):
    t = t_of(d)
    y = tone(np.full(len(t), f)) * np.exp(-t / .006) * .6 + highpass(noise(len(t), seed), 1500) * np.exp(-t / .0015)
    return fades(y, .0002, .005)

def ambience(d, seed):
    """pink room tone, low-passed, with a slow drift; the ends crossfade so it loops"""
    t = t_of(d + .5); x = lowpass(noise(len(t), seed, "pink"), 1800) * (1 + .1 * np.sin(2 * np.pi * .13 * t))
    n = int(d * SR); xf = int(.5 * SR); y = x[:n].copy()
    y[:xf] = y[:xf] * np.sin(np.linspace(0, np.pi / 2, xf)) + x[n:n + xf] * np.cos(np.linspace(0, np.pi / 2, xf))
    return y

SOUNDS = {   # id: (category, intensity, title, builder, peak dBFS)
    "riser_air":        ("riser", "soft", "Air riser, 1.0 s", lambda: riser(1.0, 11, f0=600, f1=9000, tone0=220, tone1=660, curve=2.6), -1),
    "riser_sweep":      ("riser", "medium", "Noise sweep riser, 2.0 s", lambda: riser(2.0, 12, f0=250, f1=8000, tone0=98, tone1=392, curve=2.2), -1),
    "riser_long":       ("riser", "hard", "Long tension riser, 3.2 s", lambda: riser(3.2, 13, f0=150, f1=10000, tone0=55, tone1=440, grit=.3, curve=2.0), -1),
    "impact_sub":       ("impact", "hard", "Sub drop downbeat hit", lambda: impact(1.4, 21, f0=95, f1=36, click=.5, decay=.45, body=.15), -1),
    "impact_thud":      ("impact", "medium", "Low thud", lambda: impact(.7, 22, f0=120, f1=55, click=.25, decay=.16, body=.5), -1),
    "impact_hit":       ("impact", "hard", "Hard hit with room tail", lambda: impact(1.6, 23, f0=80, f1=42, click=.9, decay=.3, body=.9, tail=.35, lp=7000), -1),
    "impact_soft":      ("impact", "soft", "Soft felt hit", lambda: impact(.5, 24, f0=160, f1=80, click=.08, decay=.1, body=.3, lp=3000), -1),
    "whoosh_soft":      ("whoosh", "soft", "Soft air whoosh, 0.6 s", lambda: whoosh(.6, 31, 400, 2500, .55), -1),
    "whoosh_fast":      ("whoosh", "medium", "Fast whoosh, 0.35 s", lambda: whoosh(.35, 32, 700, 5000, .6, q=1.3), -1),
    "whoosh_heavy":     ("whoosh", "hard", "Heavy pass-by whoosh, 0.9 s", lambda: whoosh(.9, 33, 250, 3000, .5, q=1.1), -1),
    "transition_swish": ("transition", "soft", "Short swish, 0.25 s", lambda: whoosh(.25, 41, 1500, 7000, .5, q=1.2), -1),
    "pop_bubble":       ("pop", "soft", "Bubble pop", lambda: pop(.12, 51), -1),
    "pop_bright":       ("pop", "medium", "Bright pop", lambda: pop(.1, 52, 1800, 700, .022), -1),
    "ui_tick":          ("ui", "soft", "UI tick", lambda: tick(.05, 61), -1),
    "ambience_room":    ("ambience", "soft", "Room tone loop, 4 s", lambda: ambience(4.0, 71), -18),
}


def main():
    import soundfile as sf
    from cves import sfx as SFX
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(ROOT, "assets", "sfx"))
    ap.add_argument("--only"); ap.add_argument("--no-manifest", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    for sid, (cat, inten, title, fn, pk) in SOUNDS.items():
        if only and sid not in only: continue
        y = norm(fn(), pk).astype(np.float32)
        sf.write(os.path.join(a.out, sid + ".wav"), y, SR, subtype="PCM_16"); print(f"{sid:18s} {len(y) / SR:5.2f} s")
    if a.no_manifest: return 0
    snd = []
    for sid, (cat, inten, title, src) in RECORDED.items():
        f = sid + ".mp3"
        if not os.path.exists(os.path.join(a.out, f)): continue
        m = SFX.measure(os.path.join(a.out, f))
        snd.append({"id": sid, "file": f, "category": cat, "intensity": inten, **m,
                    "licence": "CC0 1.0", "source": src, "title": title, "creator": "Freesound (via Openverse)"})
    for sid, (cat, inten, title, fn, pk) in SOUNDS.items():
        f = sid + ".wav"
        if not os.path.exists(os.path.join(a.out, f)): continue
        m = SFX.measure(os.path.join(a.out, f))
        snd.append({"id": sid, "file": f, "category": cat, "intensity": inten, **m,
                    "licence": "CC0, synthesized by CVES", "source": "tools/make_sfx.py (procedural, numpy)", "title": title, "creator": "CVES"})
    SFX.write_manifest(a.out, {"sounds": snd}); print(f"manifest: {len(snd)} sounds -> {os.path.join(a.out, 'manifest.yaml')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
