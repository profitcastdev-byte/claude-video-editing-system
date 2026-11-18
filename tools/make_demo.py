#!/usr/bin/env python3
"""Build the synthetic demo project: no real person, no client, no licensed media.

    python tools/make_demo.py OUT_DIR [--fps 30] [--seconds 9]

It writes a complete CVES project in the state ingest leaves it in, so render, mix, QC, deliver and export can run on any
machine without whisper, RVM or DeepFilterNet (CI uses it; teammates can use it to try the engine):

  Raw/demo.mp4                  a drawn "presenter" (head, eyes, a mouth that moves with the voice) on a lit wall
  Edit/plate/<seg>.mkv          lossless plates (ffv1, the same format ingest writes)
  Edit/matte/<seg>.mkv          subject mattes (gray ffv1)
  Edit/faces.json               per-frame face box + 5 landmarks (the geometry is known, so it is exact)
  Edit/words.json, edl.json, selects.yaml, ingest.json, voice_chain.json
  Edit/voice_final.wav, voice_raw.wav   a voiced, speech-like synth following the word timings
  Music/demo_bed.wav            a 100 BPM synth bed (kick, chord pad) with a drop, so `cves beats` has something to find
  Edit/edit.yaml                an edit that uses generic templates, captions, a roto moment and an end card

The presenter is drawn, so YuNet will not see a face in the final video. Face-dependent QC gates read faces.json for the
A-roll; the few that re-detect faces on the delivered file (RET-13, RET-22) are expected to WARN/FAIL on the demo.
"""
import argparse, json, math, os, shutil, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))
from cves import config as C   # noqa: E402

W, H = 1080, 1920
SR = 48000
SCRIPT = [   # (clip id, beat, sentence)
    ("01_hook", "H", "Most videos lose people in two seconds."),
    ("02_problem", "P", "Long intros, slow cuts and tiny text."),
    ("03_proof", "PR", "Tight edits keep ninety percent watching."),
    ("04_offer", "O", "This engine edits it for you."),
    ("05_cta", "C", "Try the demo today."),
]

def word_times(sentences, start=0.12, wps=2.9, gap=0.16):
    out, t = [], start
    for sid, (cid, beat, text) in enumerate(sentences):
        ws = text.split(); t0 = t
        for w in ws:
            d = max(.16, .085 * len(w.strip(".,")) + .05) * 2.9 / wps
            out.append([round(t, 3), round(t + d, 3), w, cid]); t += d + .03
        t += gap
    return out

def voice(words, dur):
    """speech-like voiced synth: f0 120 Hz with jitter, 3 formant bands per vowel, syllable envelope"""
    n = int(dur * SR); y = np.zeros(n, np.float32); rng = np.random.default_rng(7)
    for t0, t1, w, _ in words:
        i0, i1 = int(t0 * SR), min(n, int(t1 * SR)); L = i1 - i0
        if L <= 0: continue
        tt = np.arange(L) / SR; f0 = 118 + 10 * np.sin(2 * np.pi * 3 * tt) + rng.normal(0, 1)
        ph = 2 * np.pi * np.cumsum(f0) / SR; src = sum(np.sin(k * ph) / k for k in range(1, 30))
        F = [(700, 1200, 2500), (400, 2000, 2700), (300, 900, 2300)][len(w) % 3]
        spec = np.fft.rfft(src); fr = np.fft.rfftfreq(L, 1 / SR)
        gain = sum(np.exp(-((fr - f) / (80 + f * .08)) ** 2) for f in F) + .02
        s = np.fft.irfft(spec * gain, L)
        syl = max(1, sum(ch in "aeiouy" for ch in w.lower()))
        env = np.clip(np.sin(np.pi * np.minimum(1, (tt * syl / (L / SR)) % 1)) ** .6, 0, 1) * np.minimum(1, tt / .015) * np.minimum(1, (L / SR - tt) / .02)
        s = s / (np.abs(s).max() + 1e-9) * env * .55
        y[i0:i1] += s.astype(np.float32)
    y += rng.normal(0, 10 ** (-72 / 20), n).astype(np.float32)        # room floor ~ -72 dBFS
    return y

def music(dur, bpm=100, drop=None):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n, np.float32); beat = 60 / bpm
    chords = [(220, 277.2, 329.6), (196, 246.9, 293.7), (174.6, 220, 261.6), (196, 246.9, 311.1)]
    for b in range(int(dur / beat) + 1):
        i = int(b * beat * SR); bar = b // 4
        loud = 1.0 if drop is None or b * beat >= drop else .35
        k = np.arange(min(int(.25 * SR), n - i)) / SR
        if len(k) and (drop is None or b * beat >= drop or b % 4 == 0):
            y[i:i + len(k)] += (np.sin(2 * np.pi * (55 + 60 * np.exp(-k * 30)) * k) * np.exp(-k * 9) * .7 * loud).astype(np.float32)
        if b % 4 == 0:
            L = min(int(4 * beat * SR), n - i); kk = np.arange(L) / SR
            pad = sum(np.sin(2 * np.pi * f * kk) for f in chords[bar % 4]) / 3 * np.minimum(1, kk / .3) * np.exp(-kk * .25) * .22 * loud
            y[i:i + L] += pad.astype(np.float32)
    st = np.stack([y, np.roll(y, 240)], 1)
    return st / (np.abs(st).max() + 1e-9) * .8

_G = {}
def _grid():
    if not _G:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _G["g"] = (yy, xx, np.stack([150 + 40 * (1 - yy / H) - 25 * ((xx - W * .7) / W) ** 2] * 3, -1) * np.array([1.0, .93, .84], np.float32))
    return _G["g"]

def draw(k, fps, mouth_open, sway_seed=0, look=0.0):
    """one presenter frame (RGB uint8) + matte (uint8) + face box/landmarks in plate pixels"""
    t = k / fps
    yy, xx, wall = _grid()
    cx = W / 2 + 22 * math.sin(2 * np.pi * .23 * t + sway_seed) + look; cy = 760 + 10 * math.sin(2 * np.pi * .31 * t + sway_seed)
    hw, hh = 190, 250
    head = ((xx - cx) / hw) ** 2 + ((yy - cy) / hh) ** 2 <= 1
    neck = (np.abs(xx - cx) < 85) & (yy > cy + hh * .7) & (yy < cy + hh + 120)
    tors = ((xx - cx) / 470) ** 2 + ((yy - (cy + hh + 640)) / 620) ** 2 <= 1
    hair = (((xx - cx) / (hw * 1.05)) ** 2 + ((yy - (cy - hh * .35)) / (hh * .78)) ** 2 <= 1) & (yy < cy - hh * .25)
    img = wall.copy()
    img[tors] = (64, 78, 52); img[neck | head] = (196, 142, 112); img[hair] = (32, 26, 24)
    shade = np.clip(1 - .25 * ((xx - cx) / hw), .7, 1.15)[..., None]
    img = np.where((head | neck)[..., None], img * shade, img)
    le, re = (cx - 70, cy - 30), (cx + 70, cy - 30); nose = (cx, cy + 40); ml, mr = (cx - 62, cy + 120), (cx + 62, cy + 120)
    for ex, ey in (le, re):
        img[((xx - ex) / 24) ** 2 + ((yy - ey) / 12) ** 2 <= 1] = (245, 240, 235)
        img[((xx - ex) / 10) ** 2 + ((yy - ey) / 10) ** 2 <= 1] = (40, 28, 22)
    mh = 6 + 34 * mouth_open
    img[((xx - cx) / 64) ** 2 + ((yy - (cy + 120)) / mh) ** 2 <= 1] = (110, 40, 40)
    matte = (head | neck | tors | hair).astype(np.uint8) * 255
    face = [cx - hw * .82, cy - hh * .72, hw * 1.64, hh * 1.62, *le, *re, *nose, *ml, *mr]
    return np.clip(img, 0, 255).astype(np.uint8), matte, [round(float(v), 1) for v in face]

def ff(args):
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", *args], check=True)

def pipe_writer(out, fps, pix_in, pix_out, codec_args, size=(W, H)):
    return subprocess.Popen([C.get("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_in, "-s", f"{size[0]}x{size[1]}",
                             "-r", str(fps), "-i", "-", *codec_args, "-pix_fmt", pix_out, out], stdin=subprocess.PIPE)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--small", action="store_true", help="fewer words (CI speed)")
    a = ap.parse_args(); fps = a.fps; out = os.path.abspath(a.out)
    import soundfile as sf
    if os.path.exists(out): shutil.rmtree(out)
    for d in ("Raw", "Inspirations", "Brand", "Music", "Edit/plate", "Edit/matte", "Moodboard", "Export", "Assets"): os.makedirs(os.path.join(out, d), exist_ok=True)
    script = SCRIPT[:3] + SCRIPT[-1:] if a.small else SCRIPT
    words = word_times(script); dur = words[-1][1] + .35
    vo = voice(words, dur)
    sf.write(os.path.join(out, "Edit", "voice_final.wav"), vo, SR); sf.write(os.path.join(out, "Edit", "voice_raw.wav"), vo, SR)
    sf.write(os.path.join(out, "Music", "demo_bed.wav"), music(dur + 12, drop=4 * 2.4), SR)
    env = np.convolve(np.abs(vo), np.ones(int(.04 * SR)) / int(.04 * SR), "same")
    # one clip per sentence = one segment; cut time = source time (nothing tightened)
    clips, segs, faces = [], [], {}
    for cid, beat, text in script:
        ws = [w for w in words if w[3] == cid]; t0 = max(0, ws[0][0] - .1); t1 = ws[-1][1] + .1
        clips.append({"id": cid, "in": round(t0, 3), "out": round(t1, 3), "beat": beat})
    # continuous cut times: segment k runs from clip k start (or previous end) to clip k+1 start
    bounds = [0.0] + [c["in"] for c in clips[1:]] + [round(dur, 3)]
    fr = lambda t: int(round(t * fps))
    raw = pipe_writer(os.path.join(out, "Edit", "_raw_video.mkv"), fps, "rgb24", "yuv420p", ["-c:v", "ffv1"])
    for k, (cid, beat, _) in enumerate(script):
        sid = f"{cid}_0"; f0, f1 = fr(bounds[k]), fr(bounds[k + 1]); n = f1 - f0
        segs.append({"id": sid, "clip": cid, "in": round(f0 / fps, 5), "out": round(f1 / fps, 5), "src": "Raw/demo.mp4"})
        pw = pipe_writer(os.path.join(out, "Edit", "plate", f"{sid}.mkv"), fps, "rgb24", "yuv420p10le", ["-c:v", "ffv1", "-level", "3"])
        mw = pipe_writer(os.path.join(out, "Edit", "matte", f"{sid}.mkv"), fps, "gray", "gray", ["-c:v", "ffv1"])
        faces[sid] = []
        for j in range(n):
            g = f0 + j; m = float(np.clip(env[min(len(env) - 1, int(g / fps * SR))] * 6, 0, 1))
            img, mat, face = draw(g, fps, m, sway_seed=k * 1.7, look=(-30 if k % 2 else 30))
            pw.stdin.write(img.tobytes()); mw.stdin.write(mat.tobytes()); raw.stdin.write(img.tobytes()); faces[sid].append(face)
        pw.stdin.close(); mw.stdin.close(); pw.wait(); mw.wait()
    raw.stdin.close(); raw.wait()
    ff(["-i", os.path.join(out, "Edit", "_raw_video.mkv"), "-i", os.path.join(out, "Edit", "voice_raw.wav"), "-c:v", "libx264", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", os.path.join(out, "Raw", "demo.mp4")])
    os.remove(os.path.join(out, "Edit", "_raw_video.mkv"))
    from fractions import Fraction
    E = os.path.join(out, "Edit"); dump = lambda name, d: json.dump(d, open(os.path.join(E, name), "w", encoding="utf-8"), indent=1)
    dump("edl.json", {"source": "Raw/demo.mp4", "clips": clips, "segments": segs, "fps": float(fps), "fps_rational": [fps, 1], "size": [W, H]})
    dump("words.json", [w[:3] for w in words]); dump("raw_words.json", [w[:3] for w in words]); dump("faces.json", faces)
    dump("ingest.json", {"version": 2, "canvas": [W, H], "fps_rational": [fps, 1], "plate_scale": 1.0, "language": "en", "language_detected": "en",
                         "probes": {"Raw/demo.mp4": {"w": W, "h": H, "fps": fps}}, "sources": {}})
    dump("voice_chain.json", {"steps": [{"name": "synthetic demo voice", "generative": False, "params": {"tool": "tools/make_demo.py"}}]})
    import yaml
    yaml.safe_dump({"clips": clips}, open(os.path.join(E, "selects.yaml"), "w", encoding="utf-8"), sort_keys=False)
    st = lambda cid: bounds[[c[0] for c in script].index(cid)]
    en = lambda cid: bounds[[c[0] for c in script].index(cid) + 1]
    edit = {
        "project": {"client": "Demo", "title": "CVES demo", "raw": "Raw/demo.mp4", "language": "en"},
        "style": {},
        "captions": {"auto": True},
        "music": {"file": "Music/demo_bed.wav", "drop_track": 9.6, "drop_cut": round(st(script[2][0]), 2)},
        "qc": {"topic_keywords": ["videos"], "brand_tail": [], "duration": [5, 60]},
    }
    with open(os.path.join(HERE, "demo_edit.yaml"), encoding="utf-8") as fh: tmpl = yaml.safe_load(fh)
    edit = merge_demo(edit, tmpl, st, en)
    yaml.safe_dump(edit, open(os.path.join(E, "edit.yaml"), "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
    print(f"demo project: {out}  ({dur:.1f} s, {sum(len(v) for v in faces.values())} frames at {fps} fps, {len(segs)} segments)")

def merge_demo(edit, tmpl, st, en):
    """tools/demo_edit.yaml holds the template choices + params; {start:clip}/{end:clip} placeholders resolve to cut times"""
    def res(v):
        if isinstance(v, str) and v.startswith("{") and v.endswith("}") and ":" in v:
            kind, rest = v[1:-1].split(":", 1); cid, _, off = rest.partition("+")
            return round((st if kind == "start" else en)(cid) + float(off or 0), 2)
        if isinstance(v, dict): return {k: res(x) for k, x in v.items()}
        if isinstance(v, list): return [res(x) for x in v]
        return v
    t = res(tmpl)
    for k, v in t.items(): edit[k] = v
    return edit

if __name__ == "__main__":
    main()
