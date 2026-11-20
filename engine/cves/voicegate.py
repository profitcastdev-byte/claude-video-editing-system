"""Adaptive voice gate (the last step of the voice chain, docs/INGEST.md "Voice chain").

A fixed-threshold gate (the old `agate threshold=0.02`) only works in the room it was tuned for: in a real room the tone
between words sat just under or over it and left the voice floor at -50 dBFS (SND-19 wants p5 <= -60). This gate is
measured per take instead (style `voice.gate`):

  * the detector is a 10 ms RMS envelope of the voice band (`band_hz`, 150 Hz-6 kHz: rumble and hiss never open it);
  * per take, on the tightened voice itself (the room that is left between the words, which is what the viewer hears):
    the floor = a low percentile of that envelope (`floor_pct`), the speech level = a high one (`speech_pct`);
  * threshold = floor + `open_frac` x (speech - floor), kept `open_min_db`..`open_max_db` over the floor and 3 dB
    under the speech level;
  * depth = what takes the floor to `floor_target_db`, within `range_min_db`..`range_max_db`; a take whose speech sits
    closer than `min_snr_db` to its room gets only `range_min_db` (it cannot tell them apart);
  * it is a downward expander, not a switch: under the threshold the gain falls `ratio - 1` dB per dB down to the depth,
    so a word tail fades faster but continuously, never chopped; the room between words sits far under the threshold
    and gets the full depth;
  * timing: open `lookahead_ms` before a louder moment (consonant onsets are never clipped), held `hold_ms` after it,
    moving in dB with linear ramps (`attack_ms` up, `release_ms` down): no pumping inside words, no clicks.

No generative model: a level-dependent gain only (SND-30). DeepFilterNet stays the only denoiser."""
import numpy as np

DEFAULTS = {"enabled": True, "floor_pct": 10, "speech_pct": 90, "open_frac": 0.3, "open_min_db": 6.0, "open_max_db": 14.0,
            "floor_target_db": -72.0, "range_min_db": 10.0, "range_max_db": 40.0, "min_snr_db": 12.0,
            "ratio": 6.0, "attack_ms": 2.0, "lookahead_ms": 8.0, "hold_ms": 15.0, "release_ms": 40.0, "band_hz": [150, 6000]}


def cfg_of(S):
    g = dict(DEFAULTS)
    try: g.update({k: v for k, v in ((S.get("voice.gate") if S is not None else None) or {}).items() if v is not None})
    except AttributeError: pass
    return g


def envelope_db(y, sr, band=(150, 6000), win_s=.01, hop_s=.005):
    """(dB envelope per hop, hop in samples): RMS over win_s of the band-passed signal"""
    from scipy.signal import butter, sosfiltfilt
    y = np.asarray(y, np.float64)
    if len(y) < 32: return np.full(1, -120.0), max(1, int(hop_s * sr))
    lo, hi = float(band[0]), min(float(band[1]), sr / 2 * .95)
    b = sosfiltfilt(butter(2, [lo, hi], "band", fs=sr, output="sos"), y)
    win, hop = max(1, int(win_s * sr)), max(1, int(hop_s * sr))
    p = np.convolve(b ** 2, np.ones(win) / win, "same")[::hop]
    return 10 * np.log10(p + 1e-14), hop


def measure(y, sr, g=None, seams=()):
    """{floor_db, speech_db, snr_db, open_db, range_db} for one clip. `seams` (sample indices of segment joins,
    which carry 8 ms fades to silence) are left out of the floor estimate."""
    g = g or DEFAULTS; env, hop = envelope_db(y, sr, g["band_hz"])
    keep = np.ones(len(env), bool)
    for s in seams:
        k = int(s // hop); keep[max(0, k - 4):k + 5] = False
    e = env[keep] if keep.sum() > 20 else env
    e = e[e > -110] if (e > -110).sum() > 20 else e            # digital silence is not the room
    floor, speech = float(np.percentile(e, g["floor_pct"])), float(np.percentile(e, g["speech_pct"]))
    snr = speech - floor
    op = floor + float(np.clip(g["open_frac"] * snr, g["open_min_db"], g["open_max_db"]))
    op = min(op, speech - 3.0)                                 # never above quiet speech
    rng = float(np.clip(floor - g["floor_target_db"], g["range_min_db"], g["range_max_db"]))
    if snr < g["min_snr_db"]: rng = float(g["range_min_db"])
    return {"floor_db": round(floor, 1), "speech_db": round(speech, 1), "snr_db": round(snr, 1), "open_db": round(op, 1),
            "range_db": round(rng, 1)}


def gain_curve(y, sr, m, g=None):
    """per-sample linear gain for clip y with the measured params m: a downward expander, not a switch. Under the open
    threshold the gain falls `ratio - 1` dB per dB (a word tail fades faster but continuously, never chopped), down to the
    clip's range; the room between words sits well under the threshold and gets the full range. The curve is held open
    `hold_ms` after (and `lookahead_ms` before) every louder moment, and it moves in dB at most range / attack_ms when
    opening and range / release_ms when closing."""
    from scipy.ndimage import maximum_filter1d
    g = g or DEFAULTS; env, hop = envelope_db(y, sr, g["band_hz"]); n = len(env)
    depth = float(m["range_db"]); R = float(g.get("ratio", 4.0))
    tgt = -np.minimum(depth, np.maximum(0.0, (m["open_db"] - env) * (R - 1)))          # static curve (dB, <= 0)
    la, hold = int(round(g["lookahead_ms"] / 1000 * sr / hop)), int(round(g["hold_ms"] / 1000 * sr / hop))
    size = la + hold + 1                       # window [k - hold, k + la]: open early for onsets, late for tails
    org = int(np.clip(size // 2 - hold, -(size // 2), (size - 1) // 2))   # output k = max of input [k - hold, k + la]
    tgt = maximum_filter1d(tgt, size=size, origin=org, mode="nearest")
    up = depth / max(1.0, g["attack_ms"] / 1000 * sr / hop); dn = depth / max(1.0, g["release_ms"] / 1000 * sr / hop)
    gd = np.empty(n); cur = float(tgt[0])
    for k in range(n):
        x = tgt[k]; cur = min(x, cur + up) if x > cur else max(x, cur - dn); gd[k] = cur
    t = np.arange(len(y)) / hop
    return 10 ** (np.interp(t, np.arange(n), gd) / 20)


def apply(y, sr, clips, S=None, seams=()):
    """gate the assembled voice. clips = [(first sample, end sample, clip id)]: the segments of one take share one clip
    (one room). The room is measured on the tightened voice itself, not on the take's long pauses: DeepFilterNet pulls a
    long pause far down, the short gaps between words keep the room (and the reverb tail) the viewer actually hears.
    seams = sample indices of segment joins (their 8 ms fades are left out of the floor estimate).
    Returns (gated signal, {clip id: params})."""
    g = cfg_of(S); y = np.asarray(y, np.float64); out = y.copy(); info = {}
    if not g.get("enabled", True) or str(g.get("enabled")).lower() in ("false", "off", "0"): return y, {}
    by = {}
    for a, b, cid in clips: by.setdefault(cid, []).append((int(a), int(b)))
    for cid, spans in by.items():
        x = np.concatenate([y[a:b] for a, b in spans]); joins, acc = [], 0
        for a, b in spans[:-1]: acc += b - a; joins.append(acc)
        sm = [s - a for s in seams for a, b in spans if a <= s < b]
        m = measure(x, sr, g, seams=joins + sm); info[cid] = m
        gc = gain_curve(x, sr, m, g); acc = 0
        for a, b in spans: out[a:b] = y[a:b] * gc[acc:acc + b - a]; acc += b - a
    return out.astype(np.float32), info
