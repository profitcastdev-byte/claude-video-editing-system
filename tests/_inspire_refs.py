"""Synthetic reference edits for the Inspire v2 tests (no real media): numpy frames + audio piped through ffmpeg.

    python tests/_inspire_refs.py OUT_DIR      writes the four references below into OUT_DIR

  onbeat.mp4     120 BPM click track (kick + click + pad, no voice); a cut on every 2nd beat (exactly on the frame);
                 the last shot repeats the first, so the end frame equals the opening frame (a loop)
  offbeat.mp4    the same music; cuts half a beat late; ends on a different shot (no loop)
  voice.mp4      speech-like synth (tools/make_demo.voice) over a quiet bed; slow cuts, off the grid
"""
import os, sys, subprocess, tempfile, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine")); sys.path.insert(0, os.path.join(ROOT, "tools"))
SR, FPS, W, H = 48000, 30, 360, 640
BPM = 120.0


def _ffmpeg():
    from cves import config as C
    return C.get("ffmpeg")


def click_track(dur, bpm=BPM, pad=True):
    n = int(dur * SR); y = np.zeros(n, np.float32); beat = 60 / bpm; rng = np.random.default_rng(3)
    for b in range(int(dur / beat) + 1):
        i = int(round(b * beat * SR)); k = np.arange(min(int(.2 * SR), n - i)) / SR
        if not len(k): continue
        y[i:i + len(k)] += (np.sin(2 * np.pi * (50 + 90 * np.exp(-k * 35)) * k) * np.exp(-k * 14) * .8).astype(np.float32)
        m = min(len(k), int(.012 * SR)); y[i:i + m] += (rng.normal(0, .35, m) * np.exp(-np.arange(m) / (.003 * SR))).astype(np.float32)
    if pad:
        t = np.arange(n) / SR
        y += (sum(np.sin(2 * np.pi * f * t) for f in (220, 277.2, 329.6)) / 3 * .12).astype(np.float32)
    return y


def speech(dur):
    import make_demo as MD
    words, t = [], .3
    toks = ("most videos lose people in two seconds long intros slow cuts and tiny text tight edits keep ninety percent "
            "watching this engine edits it for you try the demo today").split()
    j = 0
    while t < dur - .8:
        w = toks[j % len(toks)]; d = max(.16, .085 * len(w) + .05); words.append([t, t + d, w, "c"]); t += d + .05; j += 1
        if j % 7 == 0: t += .35
    return MD.voice(words, dur)


def _wav(y, p):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y / (np.abs(y).max() + 1e-9) * .8, -1, 1) * 32767).astype(np.int16).tobytes())


COLORS = [(200, 40, 40), (30, 140, 220), (40, 170, 70), (230, 190, 30), (150, 60, 190), (240, 120, 30), (20, 20, 20), (230, 230, 230)]


def shot_frame(k, f):
    """shot k, frame f within the shot: flat colour + a block pattern drifting 1 px per frame"""
    rng = np.random.default_rng(k + 11); im = np.empty((H, W, 3), np.uint8); im[:] = COLORS[k % len(COLORS)]
    for _ in range(6):
        x, y, s = int(rng.integers(0, W - 80)), int(rng.integers(0, H - 80)), int(rng.integers(30, 80))
        c = rng.integers(0, 255, 3); x = (x + f) % (W - s); im[y:y + s, x:x + s] = c
    return im


def write_clip(path, cut_frames, n_frames, audio, shots=None):
    """cut_frames: frame indices where a new shot starts; shots: shot id per shot (default 0, 1, 2, ...)"""
    bounds = [0] + list(cut_frames) + [n_frames]; shots = shots or list(range(len(bounds) - 1))
    d = tempfile.mkdtemp(prefix="cves_ref_"); wp = os.path.join(d, "a.wav"); _wav(audio, wp)
    p = subprocess.Popen([_ffmpeg(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-i", wp, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                          "-shortest", path], stdin=subprocess.PIPE)
    for s, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        for f in range(b - a):
            # the loop shot (same id as shot 0) is drawn so its LAST frame is shot 0's first frame
            ff = (f - (b - a - 1)) if s and shots[s] == shots[0] else f
            p.stdin.write(shot_frame(shots[s], ff).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError(f"ffmpeg failed for {path}")
    return path


def make_onbeat(path, dur=12.0):
    n = int(dur * FPS); beat_f = int(60 / BPM * FPS)          # 15 frames
    cuts = list(range(2 * beat_f, n - beat_f, 2 * beat_f))
    shots = list(range(len(cuts))) + [0]
    return write_clip(path, cuts, n, click_track(dur), shots)


def make_offbeat(path, dur=12.0):
    n = int(dur * FPS); beat_f = int(60 / BPM * FPS)
    cuts = list(range(2 * beat_f + beat_f // 2, n - beat_f, 2 * beat_f))
    return write_clip(path, cuts, n, click_track(dur))


def make_voice(path, dur=12.0):
    n = int(dur * FPS); cuts = [int(x * FPS) for x in (2.3, 4.9, 7.7, 10.1)]
    y = speech(dur); bed = click_track(dur, 96) * .3
    return write_clip(path, cuts, n, y + bed, shots=[3, 4, 5, 6, 7])


def make_all(out):
    os.makedirs(out, exist_ok=True)
    return [make_onbeat(os.path.join(out, "onbeat.mp4")), make_offbeat(os.path.join(out, "offbeat.mp4")), make_voice(os.path.join(out, "voice.mp4"))]


if __name__ == "__main__":
    print("\n".join(make_all(sys.argv[1])))
