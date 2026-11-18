"""Inspire v2 SEE: a contact sheet per reference (for Claude to look at) + the aesthetics that can be measured.

analyse(path, r, sheet_path) -> dict, from up to 12 frames at shot middles (decoded at <= 720 px):
  canvas       stored size, rotation, display aspect, orientation; letterbox / pillarbox bars (rows / columns that stay
               near black on every frame) and the content aspect inside them (2.39:1 = scope)
  grain        noise sigma (8-bit levels) of the high-pass residual in flat areas; compression erases fine grain, so this
               reads "clean / fine / visible", not a film stock
  contrast     luma percentiles p2 / p25 / p50 / p75 / p98 (display 0..1) = the tone curve the reference lands on
  saturation   HSV saturation p50 / p90 of non-dark pixels
  temperature  median Lab a* / b* of the mid-tones -> warm / neutral / cool (+ a magenta / green note)
  vignette     corner / centre luminance ratio (inside the bars)
  motion_blur  share of analysed thumbnails much softer than the reference's median (whips, smears, handheld blur)
These are notes (`_inspire.aesthetics`): the engine has no grain or curve keys to fill (DECISIONS: no added grain).
The sheet is PROJECT/Edit/inspire/<ref>-sheet.jpg, each frame labelled with its time; aesthetic-review.md holds the
rubric Claude fills from it."""
import os
import numpy as np, cv2

N_FRAMES = 12


def sheet_times(cuts, dur, n=N_FRAMES):
    """middles of shots; more shots than n -> n spread evenly over the shot list; fewer -> long shots get more frames"""
    b = [0.0] + [c for c in cuts if 0 < c < dur] + [dur]; shots = [(a, c) for a, c in zip(b[:-1], b[1:]) if c - a > .05]
    if not shots: return []
    if len(shots) >= n:
        idx = np.linspace(0, len(shots) - 1, n).round().astype(int); return [round((shots[i][0] + shots[i][1]) / 2, 2) for i in idx]
    per = np.ones(len(shots), int); L = np.array([c - a for a, c in shots])
    while per.sum() < n: per[int(np.argmax(L / (per + 1)))] += 1
    out = []
    for (a, c), k in zip(shots, per): out += [round(a + (c - a) * (j + 1) / (k + 1), 2) for j in range(k)]
    return sorted(out)


def grab(path, times, rot=0, max_w=720):
    import av
    got = []
    with av.open(path) as c:
        vs = c.streams.video[0]; vs.thread_type = "AUTO"; t0 = None
        for fr in c.decode(vs): t0 = float(fr.time or 0); break
        for t in times:
            try: c.seek(int(max(0, t + t0 - .5) / vs.time_base), stream=vs, backward=True)
            except Exception: continue      # unseekable stream: skip this time
            for fr in c.decode(vs):
                ft = float(fr.time or 0) - t0
                if ft + 1e-3 < t: continue
                w, h = fr.width, fr.height; s = min(1, max_w / max(w, h))
                im = fr.reformat(width=max(2, int(w * s) // 2 * 2), height=max(2, int(h * s) // 2 * 2), format="rgb24").to_ndarray()
                if rot in (90, 270, -90): im = np.ascontiguousarray(np.rot90(im, -rot // 90))
                got.append((round(ft, 2), im)); break
    return got


def _bars(frames):
    """rows / cols that are near black on every frame -> (top, bottom, left, right) in px of the first frame's size"""
    g = np.stack([cv2.cvtColor(cv2.resize(f, frames[0].shape[1::-1]), cv2.COLOR_RGB2GRAY) for f in frames]).astype(np.float32)
    dark_r = (g.max(0).mean(1) < 20) & (g.std(0).mean(1) < 4); dark_c = (g.max(0).mean(0) < 20) & (g.std(0).mean(0) < 4)
    def run(m):
        k = 0
        while k < len(m) and m[k]: k += 1
        return k
    return run(dark_r), run(dark_r[::-1]), run(dark_c), run(dark_c[::-1])


def measure(frames, r=None):
    h, w = frames[0].shape[:2]
    top, bot, left, right = _bars(frames) if len(frames) >= 3 else (0, 0, 0, 0)
    if top + bot > .45 * h: top = bot = 0
    if left + right > .45 * w: left = right = 0
    ch, cw = h - top - bot, w - left - right
    content = [cv2.resize(f, (w, h))[top:h - bot, left:w - right] for f in frames]
    out = dict(display_aspect=round(w / h, 3), orientation="vertical" if h > w * 1.05 else "horizontal" if w > h * 1.05 else "square",
               bars=dict(top=round(top / h, 3), bottom=round(bot / h, 3), left=round(left / w, 3), right=round(right / w, 3)),
               content_aspect=round(cw / max(1, ch), 3))
    ca = out["content_aspect"]
    out["letterbox"] = ("scope 2.39:1" if 2.2 <= ca <= 2.5 else f"{ca:.2f}:1") if top + bot > .04 * h else ("pillarbox" if left + right > .04 * w else None)
    lum, sat, a_, b_, noise, vig = [], [], [], [], [], []
    for im in content:
        f = im.astype(np.float32) / 255; Y = f @ np.float32([.2126, .7152, .0722])
        lum.append(Y[::3, ::3].ravel())
        hsv = cv2.cvtColor(im, cv2.COLOR_RGB2HSV); m = hsv[..., 2] > 40; sat.append(hsv[..., 1][m][::3] / 255)
        lab = cv2.cvtColor(im, cv2.COLOR_RGB2Lab).astype(np.float32); mid = (Y > .25) & (Y < .75)
        if mid.sum() > 100: a_.append(np.median(lab[..., 1][mid]) - 128); b_.append(np.median(lab[..., 2][mid]) - 128)
        g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)
        res = g - cv2.GaussianBlur(g, (0, 0), 1.2); grad = cv2.GaussianBlur(np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)), (0, 0), 2)
        flat = grad < np.percentile(grad, 30)
        if flat.sum() > 200: noise.append(float(np.median(np.abs(res[flat])) * 1.4826))
        hh, ww = Y.shape; k = max(4, int(.12 * min(hh, ww)))
        cor = np.mean([Y[:k, :k].mean(), Y[:k, -k:].mean(), Y[-k:, :k].mean(), Y[-k:, -k:].mean()])
        cen = Y[hh // 2 - hh // 6:hh // 2 + hh // 6, ww // 2 - ww // 6:ww // 2 + ww // 6].mean()
        if cen > .05: vig.append(float(cor / cen))
    L = np.concatenate(lum); Sx = np.concatenate(sat) if sat else np.zeros(1)
    out["contrast"] = {f"p{q}": round(float(np.percentile(L, q)), 3) for q in (2, 25, 50, 75, 98)}
    sp = out["contrast"]; out["contrast"]["range"] = round(sp["p98"] - sp["p2"], 3)
    out["contrast"]["read"] = ("crushed blacks" if sp["p2"] < .01 else "lifted blacks" if sp["p2"] > .08 else "clean blacks") + ", " + \
        ("high contrast" if sp["p75"] - sp["p25"] > .45 else "low contrast" if sp["p75"] - sp["p25"] < .2 else "medium contrast")
    out["saturation"] = dict(p50=round(float(np.percentile(Sx, 50)), 3), p90=round(float(np.percentile(Sx, 90)), 3))
    out["saturation"]["read"] = "muted" if out["saturation"]["p50"] < .2 else "vivid" if out["saturation"]["p50"] > .45 else "natural"
    if a_:
        A, B = float(np.median(a_)), float(np.median(b_))
        out["temperature"] = dict(a=round(A, 1), b=round(B, 1), read=("warm" if B > 6 else "cool" if B < -4 else "neutral") +
                                  (", magenta" if A > 6 else ", green" if A < -4 else ""))
    if noise:
        n = float(np.median(noise)); out["grain"] = dict(sigma=round(n, 2), read="clean" if n < 1.2 else "fine grain / noise" if n < 3 else "visible grain / noise")
    if vig:
        v = float(np.median(vig)); out["vignette"] = dict(corner_ratio=round(v, 3), read="strong vignette" if v < .6 else "soft vignette" if v < .85 else "no vignette")
    if r and r.get("tf"):
        sh = np.array([x[0] for x in r["tf"]], float); med = float(np.median(sh)) if len(sh) else 0
        if med > 0: out["motion_blur"] = dict(soft_share=round(float((sh < .35 * med).mean()), 3))
    return out


def contact_sheet(frames, path, cols=None):
    """tile labelled frames (t, rgb) -> jpg"""
    if not frames: return None
    h, w = frames[0][1].shape[:2]; vertical = h >= w
    cols = cols or (4 if vertical else 3); rows = int(np.ceil(len(frames) / cols))
    tw = 270 if vertical else 480; th = int(round(tw * h / w))
    pad, lab = 6, 26
    can = np.full((rows * (th + lab + pad) + pad, cols * (tw + pad) + pad, 3), 24, np.uint8)
    for i, (t, im) in enumerate(frames):
        r_, c_ = divmod(i, cols); x, y = pad + c_ * (tw + pad), pad + r_ * (th + lab + pad)
        can[y:y + th, x:x + tw] = cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)
        cv2.putText(can, f"{int(t // 60)}:{t % 60:05.2f}", (x + 4, y + th + 19), cv2.FONT_HERSHEY_SIMPLEX, .55, (235, 235, 235), 1, cv2.LINE_AA)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cv2.imwrite(path, cv2.cvtColor(can, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    return path


def analyse(path, r, sheet_path):
    rot = int(r.get("rot") or 0)
    times = sheet_times(r.get("cuts") or [], float(r.get("dur") or 0))
    frames = grab(path, times, rot) if times else []
    if not frames: return dict(note="no frames decoded")
    out = measure([f for _, f in frames], r)
    W0, H0 = r.get("size") or frames[0][1].shape[1::-1]
    if rot in (90, 270, -90): W0, H0 = H0, W0
    out["size"] = [int(W0), int(H0)]
    out["sheet"] = contact_sheet(frames, sheet_path); out["sheet_times"] = [t for t, _ in frames]
    return out


def analyse_image(path, sheet_path):
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    if im is None: return dict(note="unreadable")
    rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB); s = min(1, 720 / max(rgb.shape[:2]))
    rgb = cv2.resize(rgb, (int(rgb.shape[1] * s), int(rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)
    out = measure([rgb]); out["size"] = [int(im.shape[1]), int(im.shape[0])]
    out["sheet"] = contact_sheet([(0.0, rgb)], sheet_path, cols=1); out["sheet_times"] = [0.0]
    return out


def summary_line(s):
    if not s or "contrast" not in s: return "no frames"
    bits = [f"{s['orientation']} {s['display_aspect']:.2f}"]
    if s.get("letterbox"): bits.append(s["letterbox"])
    bits += [s["contrast"]["read"], f"{s['saturation']['read']} colour"]
    if s.get("temperature"): bits.append(s["temperature"]["read"])
    if s.get("grain"): bits.append(s["grain"]["read"])
    if s.get("vignette") and s["vignette"]["read"] != "no vignette": bits.append(s["vignette"]["read"])
    return ", ".join(bits)
