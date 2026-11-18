#!/usr/bin/env python3
"""Build the synthetic demo project: no real person, no client, no licensed media.

    python tools/make_demo.py OUT_DIR [--fps 30] [--small] [--kind aroll|voiceover|music|broll] [--size WxH]

It writes a complete CVES project in the state ingest leaves it in, so render, mix, QC, deliver and export can run on any
machine without whisper, RVM or DeepFilterNet (CI uses it; teammates can use it to try the engine).

--kind picks the timeline spine (docs/FORMATS.md); --size the canvas (style canvas.size, written to edit.yaml style:).
  aroll      (default) the drawn presenter below
  voiceover  a synthetic VO as the spine (Assets/vo.wav, registered) + a broll: track of drawn clips cut on the words
  music      no voice: a synthetic 100 BPM track drives the cut; the broll: track comes from `cves autocut` (on the bars)
  broll      a shot-led edit: drawn clips with their own (synthetic ambient) sound + a music bed
The drawn B-roll clips (Assets/broll_*) cover what real footage throws at the engine: landscape, portrait, a phone clip
stored landscape with a 90 degree rotation flag, 25 fps next to 30 fps, and a still for ken burns.

The aroll kind writes:

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

W, H = 1080, 1920      # the canvas (--size); the presenter geometry scales by K = min(W / 1080, H / 1920)
K = 1.0
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
    cx = W / 2 + K * (22 * math.sin(2 * np.pi * .23 * t + sway_seed) + look); cy = H * (760 / 1920) + K * 10 * math.sin(2 * np.pi * .31 * t + sway_seed)
    hw, hh = 190 * K, 250 * K
    head = ((xx - cx) / hw) ** 2 + ((yy - cy) / hh) ** 2 <= 1
    neck = (np.abs(xx - cx) < 85 * K) & (yy > cy + hh * .7) & (yy < cy + hh + 120 * K)
    tors = ((xx - cx) / (470 * K)) ** 2 + ((yy - (cy + hh + 640 * K)) / (620 * K)) ** 2 <= 1
    hair = (((xx - cx) / (hw * 1.05)) ** 2 + ((yy - (cy - hh * .35)) / (hh * .78)) ** 2 <= 1) & (yy < cy - hh * .25)
    img = wall.copy()
    img[tors] = (64, 78, 52); img[neck | head] = (196, 142, 112); img[hair] = (32, 26, 24)
    shade = np.clip(1 - .25 * ((xx - cx) / hw), .7, 1.15)[..., None]
    img = np.where((head | neck)[..., None], img * shade, img)
    le, re = (cx - 70 * K, cy - 30 * K), (cx + 70 * K, cy - 30 * K); nose = (cx, cy + 40 * K); ml, mr = (cx - 62 * K, cy + 120 * K), (cx + 62 * K, cy + 120 * K)
    for ex, ey in (le, re):
        img[((xx - ex) / (24 * K)) ** 2 + ((yy - ey) / (12 * K)) ** 2 <= 1] = (245, 240, 235)
        img[((xx - ex) / (10 * K)) ** 2 + ((yy - ey) / (10 * K)) ** 2 <= 1] = (40, 28, 22)
    mh = (6 + 34 * mouth_open) * K
    img[((xx - cx) / (64 * K)) ** 2 + ((yy - (cy + 120 * K)) / mh) ** 2 <= 1] = (110, 40, 40)
    matte = (head | neck | tors | hair).astype(np.uint8) * 255
    face = [cx - hw * .82, cy - hh * .72, hw * 1.64, hh * 1.62, *le, *re, *nose, *ml, *mr]
    return np.clip(img, 0, 255).astype(np.uint8), matte, [round(float(v), 1) for v in face]

def ff(args):
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", *args], check=True)

def pipe_writer(out, fps, pix_in, pix_out, codec_args, size=None):
    size = size or (W, H)                     # the canvas at call time (--size)
    return subprocess.Popen([C.get("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_in, "-s", f"{size[0]}x{size[1]}",
                             "-r", str(fps), "-i", "-", *codec_args, "-pix_fmt", pix_out, out], stdin=subprocess.PIPE)

def main():
    global W, H, K
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--small", action="store_true", help="fewer words (CI speed)")
    ap.add_argument("--kind", choices=("aroll", "voiceover", "music", "broll"), default="aroll", help="the timeline spine (docs/FORMATS.md)")
    ap.add_argument("--size", default=None, help="canvas WxH (even numbers), e.g. 1920x1080; default 1080x1920")
    a = ap.parse_args(); fps = a.fps; out = os.path.abspath(a.out)
    if a.size:
        try: W, H = (int(v) for v in a.size.lower().split("x"))
        except ValueError: raise SystemExit("--size WxH, e.g. 1920x1080")
        if W % 2 or H % 2: raise SystemExit("--size: width and height must be even")
        K = min(W / 1080, H / 1920)
    if a.kind != "aroll": return build_spine(a, out, fps)
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
        "style": {} if (W, H) == (1080, 1920) else {"canvas": {"size": [W, H]}},
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

# ------------------------------------------------------------------ the other spines (voiceover / music / broll)
def _rotate_flag(src, dst, deg):
    """copy src to dst with a display-rotation flag (a phone clip stored landscape, shown portrait). deg: counter-clockwise,
    as ffprobe reports it (an upright phone clip stored on its side is -90); old ffmpeg: the legacy clockwise `rotate` tag"""
    try: ff(["-display_rotation:v:0", str(deg), "-i", src, "-c", "copy", dst])
    except subprocess.CalledProcessError: ff(["-i", src, "-c", "copy", "-metadata:s:v:0", f"rotate={(-deg) % 360}", dst])

def drawn_clip(path, w, h, fps, seconds, seed, audio=None):
    """a drawn, moving B-roll clip (no real media): a lit gradient, drifting discs and a sweeping bar, mid-tone colours
    (nothing near black or white). audio: optional mono float array muxed as AAC (the clip's own sound)."""
    rng = np.random.default_rng(seed); n = int(round(seconds * fps))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); u = min(w, h)
    base = np.array(rng.uniform(70, 150, 3), np.float32); tint = np.array(rng.uniform(40, 90, 3), np.float32)
    discs = [(rng.uniform(.1, .9), rng.uniform(.1, .9), rng.uniform(.06, .16), rng.uniform(-.25, .25), rng.uniform(-.2, .2), rng.uniform(90, 200, 3)) for _ in range(4)]
    tmp = path + ".v.mkv"; pw = pipe_writer(tmp, fps, "rgb24", "yuv420p", ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast"], size=(w, h))
    for k in range(n):
        t = k / fps
        img = base + tint * (yy / h)[..., None] + 18 * np.sin(2 * np.pi * (xx / w * 1.3 + t * .4))[..., None]
        for (dx, dy, r, vx, vy, col) in discs:
            cx, cy = ((dx + vx * t) % 1) * w, ((dy + vy * t) % 1) * h
            m = ((xx - cx) ** 2 + (yy - cy) ** 2) <= (r * u) ** 2
            img[m] = img[m] * .35 + np.array(col, np.float32) * .65
        bx = ((.15 + .3 * t + seed * .1) % 1.2 - .1) * w
        img[:, max(0, int(bx)):max(0, int(bx + .05 * w))] *= 1.18
        pw.stdin.write(np.clip(img, 24, 226).astype(np.uint8).tobytes())
    pw.stdin.close(); pw.wait()
    if audio is not None:
        import soundfile as sf
        wav = path + ".a.wav"; sf.write(wav, audio, SR)
        ff(["-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-shortest", path]); os.remove(wav)
    else: ff(["-i", tmp, "-c", "copy", path])
    os.remove(tmp)

def drawn_still(path, w, h, seed):
    from PIL import Image
    rng = np.random.default_rng(seed); yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.stack([90 + 60 * (xx / w), 80 + 70 * (yy / h), 120 + 40 * np.sin(xx / w * 6 + yy / h * 3)], -1)
    for _ in range(6):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(.05, .18) * min(w, h)
        img[((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r] = rng.uniform(80, 210, 3)
    Image.fromarray(np.clip(img, 24, 226).astype(np.uint8)).save(path)

def ambience(seconds, seed):
    """a quiet room-tone / street bed for a clip's own sound"""
    rng = np.random.default_rng(seed); n = int(seconds * SR); t = np.arange(n) / SR
    y = rng.normal(0, .05, n) * (1 + .3 * np.sin(2 * np.pi * .3 * t)) + .08 * np.sin(2 * np.pi * (180 + 40 * seed) * t) * np.exp(-((t % 1.7) * 3))
    return (y / (np.abs(y).max() + 1e-9) * .4).astype(np.float32)

def _even(x): return max(2, int(math.ceil(x / 2)) * 2)

def broll_set(out, fps, seconds, audio=False):
    """drawn clips sized to cover the canvas without upscaling (a fill crop never goes above 1.0x source pixels):
    16:9 landscape, 9:16 portrait, a phone clip stored landscape with a -90 degree rotation flag, a 25 fps clip, a 3:2 still"""
    A = os.path.join(out, "Assets")
    lh = _even(max(H, W * 9 / 16)); land = (_even(lh * 16 / 9), lh)
    pw = _even(max(W, H * 9 / 16)); port = (pw, _even(pw * 16 / 9))
    sh = _even(max(H, W / 1.5) * 1.1); still = (_even(sh * 1.5), sh)          # 10% headroom for the ken burns zoom
    specs = [("broll_city", land, fps, 1), ("broll_portrait", port, fps, 2), ("broll_phone_raw", (port[1], port[0]), fps, 3), ("broll_pal", land, 25, 4)]
    files = {}
    for name, (w, h), r, seed in specs:
        p = os.path.join(A, name + ".mp4")
        if name == "broll_phone_raw":       # drawn upright, stored on its side (as phones store portrait video; transpose=2 = 90 deg CCW)
            tmp = os.path.join(A, "_upright.mp4"); drawn_clip(tmp, port[0], port[1], r, seconds, seed, ambience(seconds, seed) if audio else None)
            ff(["-i", tmp, "-vf", "transpose=2", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "copy", p]); os.remove(tmp)
        else: drawn_clip(p, w, h, r, seconds, seed, ambience(seconds, seed) if audio else None)
        files[name] = p
    _rotate_flag(files["broll_phone_raw"], os.path.join(A, "broll_phone.mp4"), -90); os.remove(files.pop("broll_phone_raw"))
    files["broll_phone"] = os.path.join(A, "broll_phone.mp4")
    drawn_still(os.path.join(A, "broll_still.png"), still[0], still[1], 5); files["broll_still"] = os.path.join(A, "broll_still.png")
    return files

def build_spine(a, out, fps):
    import soundfile as sf, yaml
    if os.path.exists(out): shutil.rmtree(out)
    for d in ("Raw", "Inspirations", "Brand", "Music", "Edit", "Moodboard", "Export", "Assets"): os.makedirs(os.path.join(out, d), exist_ok=True)
    E = os.path.join(out, "Edit"); dump = lambda name, d: json.dump(d, open(os.path.join(E, name), "w", encoding="utf-8"), indent=1)
    kind = a.kind; script = SCRIPT[:3] + SCRIPT[-1:] if a.small else SCRIPT
    edit = {"project": {"client": "Demo", "title": f"CVES {kind} demo", "language": "en"}, "spine": kind,
            "style": {} if (W, H) == (1080, 1920) else {"canvas": {"size": [W, H]}}, "captions": {"auto": True}}
    if kind == "voiceover":
        words = word_times(script); dur = words[-1][1] + .35
        vo = voice(words, dur)
        sf.write(os.path.join(out, "Assets", "vo.wav"), vo, SR)
        sf.write(os.path.join(E, "voice_final.wav"), vo, SR); sf.write(os.path.join(E, "voice_raw.wav"), vo, SR)
        dump("words.json", [w[:3] for w in words])
        dump("voice_chain.json", {"steps": [{"name": "synthetic demo voice", "generative": False, "params": {"tool": "tools/make_demo.py"}}]})
        files = broll_set(out, fps, 5.0)
        starts = [w[0] for w in words]; sent = [next(w[0] for w in words if w[3] == cid) for cid, _, _ in script]
        cuts = sorted(set([0.0, .9] + [round(t - .05, 2) for t in sent[1:]] + [round((x + y) / 2, 2) for x, y in zip(sent[1:-1], sent[2:])]))
        cuts = [c for c in cuts if c < dur - .6] + [round(dur, 3)]
        order = ["broll_city", "broll_portrait", "broll_still", "broll_phone", "broll_pal"]
        frame = {"broll_portrait": "fit"}
        track = []
        for k, (x, y) in enumerate(zip(cuts[:-1], cuts[1:])):
            nm = order[k % len(order)]; sh = {"asset": nm, "start": round(x, 3), "end": round(y, 3)}
            if not nm.endswith("still"): sh["in"] = round(.3 * (k % 4), 2)
            if nm in frame: sh["framing"] = frame[nm]
            if nm == "broll_pal": sh["speed"] = 0.75
            track.append(sh)
        edit.update(voiceover={"asset": "vo"}, broll=track,
                    cutaways=[{"id": "t1", "template": "title_card", "start": round(sent[2] - .05, 2), "end": round(sent[3] - .05, 2) if len(sent) > 3 else round(dur, 2),
                               "snap": False, "params": {"lines": ["Ninety percent", "keep watching"], "accent": ["ninety"], "at": round(sent[2], 2)}}],
                    music={"file": "Music/demo_bed.wav", "drop_track": 9.6, "drop_cut": round(sent[2], 2)},
                    qc={"topic_keywords": ["videos"], "brand_tail": [], "duration": [5, 60]})
        sf.write(os.path.join(out, "Music", "demo_bed.wav"), music(dur + 12, drop=4 * 2.4), SR)
        assets = {"vo": ("Assets/vo.wav", "elevenlabs", "Most videos lose people in two seconds.")}
    else:
        dur = 8.0 if a.small else 12.0
        files = broll_set(out, fps, 5.0, audio=(kind == "broll"))
        sf.write(os.path.join(out, "Music", "demo_bed.wav"), music(dur + 6), SR)
        edit.update(music={"file": "Music/demo_bed.wav"}, qc={"topic_keywords": [], "brand_tail": [], "duration": [5, 60]}, duration=dur)
        assets = {}
        if kind == "broll":
            seq = [("broll_city", 0, 2.2, {"audio": True}), ("broll_phone", 2.2, 3.9, {}), ("broll_still", 3.9, 5.4, {}),
                   ("broll_portrait", 5.4, 6.8, {"framing": "fit", "audio": True}), ("broll_pal", 6.8, dur, {"speed": 1.5})]
            edit["broll"] = [dict({"asset": n, "start": x, "end": y, **({"in": .3} if not n.endswith("still") else {})}, **kw) for n, x, y, kw in seq]
            edit["cutaways"] = [{"id": "t1", "template": "title_card", "start": 0.0, "end": 0.9, "snap": False, "params": {"lines": ["Shot-led edit"], "at": 0.0, "reveal": "none"}}]
            edit["music"]["bed_lu"] = -10
    for nm, p in files.items(): assets[nm] = (os.path.relpath(p, out).replace(os.sep, "/"), "render", None)
    edit["assets"] = {k: {"path": v[0], "licence": "synthetic (tools/make_demo.py)"} for k, v in assets.items()}
    yaml.safe_dump(edit, open(os.path.join(E, "edit.yaml"), "w", encoding="utf-8"), sort_keys=False, allow_unicode=True)
    sys.path.insert(0, os.path.join(ROOT, "engine"))
    from cves import project, assets as AS, spines as SP
    pr = project.Project(out)
    for k, (path, src, prompt) in assets.items():
        AS.add(pr, k, os.path.join(out, path), source=src, prompt=prompt, licence="synthetic (tools/make_demo.py)")
    SP.sync_edl(pr, force=True)
    if kind == "music":       # the cut comes from the music: autocut on the bars, cycling through the drawn clips
        track, info = SP.autocut(pr, every="downbeats", min_shot=1.0, folder="Assets")
        E_ = pr.edit; E_["broll"] = track; pr.save_edit(E_)
        E_["cutaways"] = [{"id": "t1", "template": "title_card", "start": 0.0, "end": 0.9, "snap": False,       # a text card, then the cut
                            "params": {"lines": ["On the beat"], "at": 0.0, "reveal": "none"}}]
        pr.save_edit(E_)
    print(f"demo project ({kind}, {W}x{H}): {out}  ({SP.duration(pr, kind):.1f} s at {fps} fps, {len(pr.edit.get('broll') or [])} B-roll shots)")


if __name__ == "__main__":
    main()
