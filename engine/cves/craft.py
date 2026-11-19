"""Motion craft (docs/MOTION.md, "Craft"): the editor's moves between and inside shots. Pure functions of their inputs, so
every frame is deterministic and the same in every worker process. Everything is read from the style (`craft.*`,
`transitions.*`), and every move counts against the `creative.*` restraint budget (`usage()`; `cves critique` reports it).

  speed ramps      ramp_src / ramp_frame: time remap of a clip along an eased speed curve (keys or a style preset),
                   normalised so the shot's source range lands exactly on its in / out; frame blending (crossfade between
                   neighbours on slow sections, a shutter-length average on fast ones) or nearest frame; audio muted or
                   varispeed-pitched (varispeed) per style.
  camera moves     camera(): push, pull, pan_*, handheld drift (seeded smooth noise: same seed, same wobble) on eased
                   curves; parallax_layers / parallax_view: a 2-plane 2.5D move for stills with a depth map or matte.
  match cuts       blob / match_transform: the salient shape of the outgoing frame (spectral-residual saliency, or a
                   bright-shape centroid) and the scale + offset that put the incoming frame's shape on it; find_in
                   searches a clip for the in-point whose shape lines up best.
  transitions      transition(): whip_pan, zoom_through, mask_wipe (bar / circle / matte), luma_fade, glitch_lite,
                   light_leak (procedural), dip (to a style colour). limit_transitions() rate-limits them on a timeline.
  text behind      face_track / roto_ctx feed the `text_behind` template (templates/craft.py): type composited between the
                   plate and the subject matte, placed from smoothed face landmarks."""
import math, zlib, json, functools
import numpy as np, cv2
from . import gfx as G

# ------------------------------------------------------------------ easing (same names as the motion runtime)
def _io(p, k): return 2 ** (k - 1) * p ** k if p < .5 else 1 - (-2 * p + 2) ** k / 2

EASE = {
    "linear": lambda p: p,
    "inSine": lambda p: 1 - math.cos(p * math.pi / 2), "outSine": lambda p: math.sin(p * math.pi / 2),
    "inOutSine": lambda p: -(math.cos(math.pi * p) - 1) / 2,
    "inQuad": lambda p: p * p, "outQuad": lambda p: 1 - (1 - p) ** 2, "inOutQuad": lambda p: _io(p, 2),
    "inCubic": lambda p: p ** 3, "outCubic": lambda p: 1 - (1 - p) ** 3, "inOutCubic": lambda p: _io(p, 3),
    "inQuint": lambda p: p ** 5, "outQuint": lambda p: 1 - (1 - p) ** 5, "inOutQuint": lambda p: _io(p, 5),
    "outExpo": lambda p: 1.0 if p >= 1 else 1 - 2 ** (-10 * p),
    "inExpo": lambda p: 0.0 if p <= 0 else 2 ** (10 * p - 10),
    "inOutExpo": lambda p: 0.0 if p <= 0 else 1.0 if p >= 1 else (2 ** (20 * p - 10) / 2 if p < .5 else (2 - 2 ** (-20 * p + 10)) / 2),
}

def ease(name, p):
    """eased progress: p clamped to 0..1, name from EASE (unknown names are an error, not a silent linear)"""
    if name not in EASE: raise SystemExit(f"unknown ease '{name}': one of {', '.join(sorted(EASE))}")
    return float(EASE[name](min(1.0, max(0.0, float(p)))))

def _S(S, key, default=None):
    v = S.get(key, default) if S is not None and hasattr(S, "get") else default
    return default if v is None else v

def seed_of(*parts):
    """a stable 32-bit seed from any values (crc32 of their JSON): the same shot always gets the same wobble / leak"""
    return zlib.crc32(json.dumps(parts, sort_keys=True, default=str).encode()) & 0xFFFFFFFF


# ================================================================== speed ramps
def ramp_keys(spec, S=None):
    """the [[shot fraction 0..1, speed multiplier], ...] keys of a ramp spec: {keys: [...]} or {preset: name}
    (style craft.ramp.presets) or a bare preset name. Sorted, clamped, padded to cover 0 and 1."""
    if isinstance(spec, str): spec = {"preset": spec}
    keys = (spec or {}).get("keys")
    if keys is None:
        name = (spec or {}).get("preset") or _S(S, "craft.ramp.default", "slam")
        presets = _S(S, "craft.ramp.presets", {}) or {}
        if name not in presets: raise SystemExit(f"ramp preset '{name}' is not in style craft.ramp.presets ({', '.join(sorted(presets)) or 'none'})")
        keys = presets[name]
    try: ks = sorted([float(a), float(b)] for a, b in keys)
    except (TypeError, ValueError): raise SystemExit(f"ramp keys must be [[fraction, speed], ...], got {keys!r}")
    if not ks: raise SystemExit("ramp: no keys")
    ks = [[min(1.0, max(0.0, a)), b] for a, b in ks]
    if ks[0][0] > 0: ks.insert(0, [0.0, ks[0][1]])
    if ks[-1][0] < 1: ks.append([1.0, ks[-1][1]])
    return ks

@functools.lru_cache(256)
def _ramp_table(keys_t, ease_name, min_speed, n=2048):
    """speed and its running integral on a fine grid of the shot fraction (trapezoid rule): monotonic by construction"""
    ks = [list(k) for k in keys_t]; f = np.linspace(0, 1, n + 1); v = np.empty_like(f)
    for i, x in enumerate(f):
        j = max(0, min(len(ks) - 2, next((m for m in range(len(ks) - 1) if ks[m][0] <= x <= ks[m + 1][0]), len(ks) - 2)))
        a, b = ks[j], ks[j + 1]; span = b[0] - a[0]
        p = 1.0 if span <= 1e-9 else (x - a[0]) / span
        v[i] = max(min_speed, a[1] + (b[1] - a[1]) * ease(ease_name, p))
    cum = np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(f))])
    return f, v, cum

def ramp_table(spec, S=None):
    sp = spec if isinstance(spec, dict) else {"preset": spec}
    keys = ramp_keys(sp, S)
    return _ramp_table(tuple(tuple(k) for k in keys), sp.get("ease") or _S(S, "craft.ramp.ease", "inOutCubic"),
                       float(sp.get("min_speed", _S(S, "craft.ramp.min_speed", .08))))

def ramp_src(local, dur, spec, S=None, sin=0.0, base_speed=1.0, sout=None):
    """(source seconds, instantaneous speed in source s per cut s) at `local` cut seconds into a ramped shot of `dur` s.
    With sout the curve is normalised so local 0 -> sin and local dur -> sout exactly (the shot keeps its in / out);
    without it the shot consumes base_speed x dur x (mean ramp speed) seconds of source."""
    f, v, cum = ramp_table(spec, S); dur = max(1e-6, float(dur)); x = min(1.0, max(0.0, float(local) / dur))
    I = float(np.interp(x, f, cum)); total = float(cum[-1]); vi = float(np.interp(x, f, v))
    if sout is not None:
        span = float(sout) - float(sin)
        return float(sin) + span * (I / total), span / total / dur * vi
    return float(sin) + float(base_speed) * dur * I, float(base_speed) * vi

def ramp_span(dur, spec, S=None, base_speed=1.0):
    """source seconds a ramped shot of `dur` cut seconds consumes (without an explicit out)"""
    return float(base_speed) * float(dur) * float(ramp_table(spec, S)[2][-1])

def ramp_frame(clip, st, speed, out_fps, mode="auto", shutter=0.5):
    """an RGBA uint8 frame of `clip` at source time st, blended for its speed. mode: nearest | blend | auto (= blend).
    Slow (< 1 source frame per output frame): crossfade the two neighbouring frames by the fractional position (no
    stutter). Fast: average the frames a `shutter` (fraction of an output frame) would see, up to 8 (motion blur)."""
    x = st * clip.fps; i0 = int(math.floor(x + 1e-6))
    if mode == "nearest": return clip.frame(int(round(x)))
    window = abs(speed) * clip.fps / max(1e-6, out_fps) * shutter          # source frames under one shutter
    if window <= 1.0:
        a = x - i0
        if a < 1e-3 or i0 + 1 >= clip.n: return clip.frame(i0)
        f0, f1 = clip.frame(i0).astype(np.float32), clip.frame(i0 + 1).astype(np.float32)
        return np.clip(f0 * (1 - a) + f1 * a + .5, 0, 255).astype(np.uint8)
    k = min(8, int(math.ceil(window))); ids = sorted({min(clip.n - 1, max(0, int(round(x - window / 2 + window * (j + .5) / k)))) for j in range(k)})
    acc = np.zeros(clip.frame(ids[0]).shape, np.float32)
    for j in ids: acc += clip.frame(j)
    return np.clip(acc / len(ids) + .5, 0, 255).astype(np.uint8)

def varispeed(y, sr, ramp):
    """tape-style varispeed audio for a ramped shot: output sample n plays source position src(n / sr) (pitch follows
    speed). ramp: {spec, dur, sin (0 = the start of y), sout, base, S-free keys}. Returns the shot-length signal."""
    dur = float(ramp["dur"]); n = max(1, int(round(dur * sr))); t = np.arange(n) / sr
    f, v, cum = _ramp_table(tuple(tuple(k) for k in ramp["keys"]), ramp.get("ease", "inOutCubic"), float(ramp.get("min_speed", .08)))
    I = np.interp(np.clip(t / dur, 0, 1), f, cum)
    span = (float(ramp["sout"]) - float(ramp["sin"])) if ramp.get("sout") is not None else float(ramp.get("base", 1)) * dur * float(cum[-1])
    pos = I / float(cum[-1]) * span * sr
    return np.interp(pos, np.arange(len(y)), y, right=0.0).astype(np.float32)

def ramp_audio_kw(spec, S, dur, sin, base, sout=None):
    """the kw a ramped shot's audio cue carries for mix (keys resolved here, so mix needs no style)"""
    sp = spec if isinstance(spec, dict) else {"preset": spec}
    return {"keys": ramp_keys(sp, S), "ease": sp.get("ease") or _S(S, "craft.ramp.ease", "inOutCubic"),
            "min_speed": float(sp.get("min_speed", _S(S, "craft.ramp.min_speed", .08))), "dur": round(float(dur), 5),
            "sin": float(sin), "sout": sout, "base": float(base)}

def ramp_audio_mode(spec, S):
    sp = spec if isinstance(spec, dict) else {}
    m = str(sp.get("audio") or _S(S, "craft.ramp.audio", "mute"))
    if m not in ("mute", "pitch"): raise SystemExit(f"ramp audio: '{m}' is not mute | pitch")
    return m


# ================================================================== camera moves
MOVES = ("none", "push", "pull", "pan_left", "pan_right", "pan_up", "pan_down", "drift")

def _noise(t, seed, hz):
    """smooth deterministic noise in -1..1: three seeded sines at incommensurate frequencies around hz"""
    r = np.random.default_rng(seed); out = 0.0; norm = 0.0
    for k, mul in enumerate((1.0, 2.13, 3.71)):
        ph = r.uniform(0, 2 * math.pi); a = 1 / (1 + k)
        out += a * math.sin(2 * math.pi * hz * mul * t + ph); norm += a
    return out / norm

def camera(f, spec, S=None, seed=0, dur=1.0):
    """the camera at shot fraction f: {z (zoom >= 1), px, py (pan, -1..1 of the free margin), ox, oy (handheld offset,
    canvas px), rot (deg)}. spec: {move, amount, ease, handheld, drift_u, drift_hz, drift_rot}; amount is the zoom change
    (push / pull) or the travel (pans); pans and drift zoom in just enough to never show an edge."""
    sp = spec if isinstance(spec, dict) else {"move": spec}
    mv = sp.get("move", _S(S, "craft.camera.move", "none")) or "none"
    if mv not in MOVES: raise SystemExit(f"camera.move: '{mv}' is not one of {', '.join(MOVES)}")
    a = float(sp.get("amount", _S(S, "craft.camera.amount", .08))); e = ease(sp.get("ease") or _S(S, "craft.camera.ease", "inOutSine"), f)
    z, px, py = 1.0, 0.0, 0.0
    if mv == "push": z = 1 + a * e
    elif mv == "pull": z = 1 + a * (1 - e)
    elif mv.startswith("pan_"):
        z = 1 + a; d = (2 * e - 1) * .9
        if mv == "pan_left": px = -d
        elif mv == "pan_right": px = d
        elif mv == "pan_up": py = -d
        else: py = d
    ox = oy = rot = 0.0
    if mv == "drift" or sp.get("handheld", False):
        amp = float(sp.get("drift_u", _S(S, "craft.camera.drift_u", .5))) * min(G.W, G.H) / 100
        hz = float(sp.get("drift_hz", _S(S, "craft.camera.drift_hz", .3))); t = f * float(dur)
        ox, oy = amp * _noise(t, seed, hz), amp * _noise(t, seed + 1, hz * .87)
        rot = float(sp.get("drift_rot", _S(S, "craft.camera.drift_rot", .25))) * _noise(t, seed + 2, hz * .61)
        diag = math.hypot(G.W, G.H) / 2
        z *= 1 + 2.2 * amp / min(G.W, G.H) + abs(math.radians(float(sp.get("drift_rot", _S(S, "craft.camera.drift_rot", .25))))) * diag / min(G.W, G.H)
    return {"z": z, "px": px, "py": py, "ox": ox, "oy": oy, "rot": rot, "move": mv}

def rotate(pic, deg):
    """rotate an RGBA canvas picture about its centre (handheld roll); edges reflect, the camera zoom hides them"""
    if abs(deg) < 1e-3: return pic
    h, w = pic.shape[:2]; M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(pic, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

@functools.lru_cache(8)
def parallax_layers(path, depth_path, split=.5):
    """(foreground RGBA, background RGBA) of a still for a 2-plane 2.5D move. depth_path: a grayscale depth map (white =
    near) or an image whose alpha is the subject matte; pixels nearer than `split` are the foreground (soft edge). The
    background has the foreground area filled (OpenCV Telea inpaint at <= 1024 px, so it costs one call per still)."""
    from PIL import Image, ImageOps
    with Image.open(path) as im: rgb = np.asarray(ImageOps.exif_transpose(im).convert("RGB"))
    with Image.open(depth_path) as dm:
        dm = ImageOps.exif_transpose(dm)
        d = np.asarray(dm.convert("RGBA"))[..., 3] if dm.mode in ("RGBA", "LA") else np.asarray(dm.convert("L"))
    h, w = rgb.shape[:2]
    if d.shape != (h, w): d = cv2.resize(d, (w, h), interpolation=cv2.INTER_LINEAR)
    m = np.clip((d.astype(np.float32) / 255 - split) / .08 + .5, 0, 1)
    m = cv2.GaussianBlur(m, (0, 0), max(1.0, min(w, h) / 500))
    fg = np.dstack([rgb, (m * 255 + .5).astype(np.uint8)])
    k = min(1.0, 1024 / max(w, h)); small = cv2.resize(rgb, (max(2, int(w * k)), max(2, int(h * k))), interpolation=cv2.INTER_AREA)
    hole = cv2.resize((m > .02).astype(np.uint8) * 255, small.shape[1::-1], interpolation=cv2.INTER_NEAREST)
    hole = cv2.dilate(hole, np.ones((5, 5), np.uint8), iterations=2)
    fill = cv2.inpaint(small, hole, 7, cv2.INPAINT_TELEA)
    fill = cv2.GaussianBlur(fill, (0, 0), 2.0)
    big = cv2.resize(fill, (w, h), interpolation=cv2.INTER_CUBIC)
    hm = cv2.resize(hole, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)[..., None] / 255
    bg = (rgb * (1 - hm) + big * hm).astype(np.uint8)
    return fg, np.dstack([bg, np.full((h, w), 255, np.uint8)])

def parallax_view(layers, view_fn, s0, c0, s, c, parallax):
    """composite the 2.5D layers: the background moves with the camera (scale s, centre c), the foreground moves
    (1 + parallax) times as much from the rest view (s0, c0). view_fn(img, scale, centre) -> canvas RGBA uint8."""
    fg, bg = layers; k = 1 + float(parallax)
    s_fg = s0 * (s / s0) ** k; c_fg = (c0[0] + (c[0] - c0[0]) * k, c0[1] + (c[1] - c0[1]) * k)
    B = view_fn(bg, s, c, False).astype(np.float32); F = view_fn(fg, s_fg, c_fg, True).astype(np.float32)
    a = F[..., 3:4] / 255
    return np.dstack([np.clip(F[..., :3] * a + B[..., :3] * (1 - a) + .5, 0, 255).astype(np.uint8), np.full(B.shape[:2], 255, np.uint8)])


# ================================================================== match cuts
def saliency(rgb, size=96):
    """spectral-residual saliency (Hou & Zhang 2007) of an RGB(A) frame on a `size`-px long side: float 0..1 map"""
    g = cv2.cvtColor(np.ascontiguousarray(rgb[..., :3]), cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = g.shape; k = size / max(h, w); g = cv2.resize(g, (max(8, int(w * k)), max(8, int(h * k))), interpolation=cv2.INTER_AREA)
    F = np.fft.fft2(g); amp = np.log(np.abs(F) + 1e-6); ph = np.angle(F)
    res = amp - cv2.blur(amp, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(res + 1j * ph))) ** 2
    sal = cv2.GaussianBlur(sal.astype(np.float32), (0, 0), 2.5)
    sal -= sal.min(); return sal / (sal.max() + 1e-9)

def blob(rgb, mode="saliency"):
    """the salient shape of a frame: (cx, cy, spread) as fractions of the frame (spread = RMS radius / short side).
    mode saliency: spectral residual; centroid: the brightest / highest-contrast shape (a sun, a lamp, a white product)."""
    if mode == "centroid":
        g = cv2.cvtColor(np.ascontiguousarray(rgb[..., :3]), cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = g.shape; k = 96 / max(h, w); g = cv2.resize(g, (max(8, int(w * k)), max(8, int(h * k))), interpolation=cv2.INTER_AREA)
        lift = np.clip(g - cv2.GaussianBlur(g, (0, 0), 14), 0, None)       # brighter than its surroundings (not a lit gradient)
        con = np.abs(g - cv2.GaussianBlur(g, (0, 0), 4)); m = lift / (lift.max() + 1e-6) * .75 + con / (con.max() + 1e-6) * .25
        q = .97
    elif mode == "saliency": m = saliency(rgb); q = .9
    else: raise SystemExit(f"match mode '{mode}' is not saliency | centroid")
    thr = np.quantile(m, q); wgt = np.clip(m - thr, 0, None)
    if wgt.sum() <= 1e-9: wgt = np.ones_like(m)
    hh, ww = m.shape; ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32); W_ = wgt.sum()
    cx, cy = (wgt * xs).sum() / W_, (wgt * ys).sum() / W_
    spread = math.sqrt(float((wgt * ((xs - cx) ** 2 + (ys - cy) ** 2)).sum() / W_)) / min(hh, ww)
    return (cx + .5) / ww, (cy + .5) / hh, max(spread, 1e-3)

def match_transform(a_rgb, b_rgb, mode="saliency", scale_range=(1.0, 1.6)):
    """how to move the incoming frame b so its salient shape sits on the outgoing frame a's: {scale, ax, ay, bx, by,
    cost} (fractions of the frame; scale about b's shape, clamped to scale_range so the fill crop never shows an edge)"""
    ax, ay, sa = blob(a_rgb, mode); bx, by, sb = blob(b_rgb, mode)
    # the smallest scale that lets the shape move onto (ax, ay) without the fill crop running out of picture:
    # x' = r (x - b) + a must still cover the frame, so r >= a / b and r >= (1 - a) / (1 - b) on each axis
    need = max(ax / max(bx, 1e-3), (1 - ax) / max(1 - bx, 1e-3), ay / max(by, 1e-3), (1 - ay) / max(1 - by, 1e-3), 1.0)
    r = float(min(max(sa / sb, need, scale_range[0]), scale_range[1]))
    return {"scale": round(r, 4), "ax": round(ax, 4), "ay": round(ay, 4), "bx": round(bx, 4), "by": round(by, 4),
            "cost": round(math.hypot(ax - bx, ay - by) + abs(math.log(sa / sb)) * .5, 4)}

def match_view_shift(m, w, h):
    """(scale multiplier, dX, dY) for a view: scaling the incoming picture by m.scale about its shape (bx, by) and moving
    the shape onto (ax, ay) shows, at the canvas centre, the canvas point centre + (dX, dY) of the untransformed view"""
    r = m["scale"]; C = (w / 2, h / 2)
    q = (m["bx"] * w + (C[0] - m["ax"] * w) / r, m["by"] * h + (C[1] - m["ay"] * h) / r)
    return r, q[0] - C[0], q[1] - C[1]

def find_in(a_rgb, frame_at, t0, t1, step=.25, mode="saliency"):
    """search source times t0..t1 (step s) of a clip for the in-point whose salient shape best continues a_rgb.
    frame_at(t) -> RGB(A) frame. Returns [(cost, t, transform)] best first."""
    out = []; t = float(t0)
    while t <= float(t1) + 1e-9:
        m = match_transform(a_rgb, frame_at(t), mode); out.append((m["cost"], round(t, 3), m)); t += step
    return sorted(out, key=lambda x: x[0])


# ================================================================== transitions
TRANSITIONS = ("whip_pan", "zoom_through", "mask_wipe", "luma_fade", "glitch_lite", "light_leak", "dip")
LEGACY = ("whip", "glitch", "fade")

def _colour(v, S, default="stage"):
    v = v or default
    if v == "stage": return np.array(G.STAGE["background"], np.float32) / 255
    if v == "black": return np.zeros(3, np.float32)
    if v == "white": return np.ones(3, np.float32)
    return np.array(G.col(v, G.MINT), np.float32) / 255

def _shift(img, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]]); h, w = img.shape[:2]
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

def _dir_blur(img, length, horizontal=True):
    """directional (motion) blur of `length` px: a box kernel along one axis, done at reduced size for long smears"""
    if length < 1.5: return img
    h, w = img.shape[:2]; k = 1.0 if length < 24 else max(.2, 24 / length)
    small = cv2.resize(img, (max(2, int(w * k)), max(2, int(h * k))), interpolation=cv2.INTER_AREA) if k < 1 else img
    n = max(3, int(length * k) | 1)
    ker = np.ones((1, n), np.float32) / n if horizontal else np.ones((n, 1), np.float32) / n
    out = cv2.filter2D(small, -1, ker, borderType=cv2.BORDER_REFLECT101)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR) if k < 1 else out

def _zoom(img, z, cx, cy):
    h, w = img.shape[:2]; M = np.float32([[z, 0, cx - z * cx], [0, z, cy - z * cy]])
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)

def _radial_blur(img, amt, cx, cy, n=7):
    if amt <= .01: return img
    acc = img.copy()
    for k in range(1, n): acc += _zoom(img, 1 + amt * k / n, cx, cy)
    return acc / n

@functools.lru_cache(16)
def _leak_field(w, h, seed):
    """a soft procedural light-leak field (0..1) at 1/8 size: three warm blobs and a streak, from the seed"""
    sw, sh = max(8, w // 8), max(8, h // 8); r = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:sh, 0:sw].astype(np.float32); ys /= sh; xs /= sw; f = np.zeros((sh, sw), np.float32)
    side = r.choice([-1, 1])
    for k in range(3):
        cx = .5 + side * r.uniform(.25, .7); cy = r.uniform(.1, .9); rad = r.uniform(.25, .55)
        f += np.exp(-(((xs - cx) * (h / w if w < h else 1)) ** 2 + ((ys - cy) * (w / h if w > h else 1)) ** 2) / (rad * rad)) * r.uniform(.5, 1)
    ang = r.uniform(-.6, .6); streak = np.exp(-((ys - .5 - ang * (xs - .5)) ** 2) / .01) * .35
    f = f + streak
    return f / (f.max() + 1e-6)

def transition(kind, img, e, after, seed, S=None, matte=None):
    """one frame of a transition. img: RGB float 0..1 (the shot on this side of the cut); e: strength, 1 on the cut,
    0 at the window edge; after: True on the incoming side. Every kind reads its look from style craft.transitions.*."""
    if e <= 0 or img is None: return img
    h, w = img.shape[:2]; x = float(min(1.0, e)); u = min(w, h) / 100
    T = lambda k, d=None: _S(S, f"craft.transitions.{k}", d)
    if kind == "whip_pan":
        d = str(T("whip_dir", "left")); horiz = d in ("left", "right"); sgn = -1 if d in ("left", "up") else 1
        span = (w if horiz else h) * .55; off = sgn * span * x ** 2 * (-1 if after else 1)
        out = _shift(img, off if horiz else 0, 0 if horiz else off)
        return _dir_blur(out, (w if horiz else h) * .32 * x ** 1.4, horiz)
    if kind == "zoom_through":
        cx, cy = w / 2, h / 2
        z = 1 + (2.2 if not after else .7) * x ** 2.2
        out = _radial_blur(_zoom(img, z, cx, cy), .18 * x ** 1.5, cx, cy)
        return np.clip(out + .12 * x ** 3, 0, 1)
    if kind == "mask_wipe":
        shape = str(T("wipe_shape", "bar")); col = _colour(T("wipe_color", "accent"), S, "accent")
        P = .5 * x if not after else .5 + .5 * (1 - x)                # 0 -> 1 across the whole window, .5 on the cut
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        if shape == "circle": coord = np.hypot(xs - w / 2, ys - h / 2) / (math.hypot(w, h) / 2)
        elif shape == "matte" and matte is not None:
            coord = .55 * (1 - cv2.GaussianBlur(matte.astype(np.float32), (0, 0), 3 * u)) + .45 * (xs / w)   # background first, the subject last
        else: coord = (xs + .28 * ys) / (w + .28 * h)
        feather = 1.2 * u / max(w, h)
        if not after: cover = np.clip((ease("inCubic", P * 2) * (1 + feather) - coord) / feather, 0, 1)
        else: cover = np.clip((coord - ease("outCubic", P * 2 - 1) * (1 + feather) + feather) / feather, 0, 1)
        edge = np.clip(1 - np.abs(cover - .5) * 2, 0, 1) ** 2 * .35        # a lit leading edge
        return np.clip(img * (1 - cover[..., None]) + col * cover[..., None] + edge[..., None], 0, 1)
    if kind == "luma_fade":
        col = _colour(T("dip_color", "stage"), S); Y = (img * np.array([.2126, .7152, .0722], np.float32)).sum(-1)
        soft = .18; thr = x * (1 + soft) - soft / 2                # shadows go first (out), highlights come first (in)
        a = np.clip((thr - (Y if not after else 1 - Y)) / soft + .5, 0, 1)
        return img * (1 - a[..., None]) + col * a[..., None]
    if kind == "glitch_lite":
        rng = np.random.default_rng(seed + (1 if after else 0)); out = img.copy(); sh = int(round(1.2 * u * x)) + 1
        out[..., 0] = np.roll(img[..., 0], sh, axis=1); out[..., 2] = np.roll(img[..., 2], -sh, axis=1)
        for _ in range(int(1 + 3 * x)):
            y0 = int(rng.integers(0, max(1, h - 4))); hh = int(rng.integers(max(2, int(u)), max(3, int(6 * u))))
            out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], int(rng.uniform(-1, 1) * 9 * u * x), axis=1)
        return np.clip(out * (1 + .06 * x * (1 if rng.random() > .5 else -1)), 0, 1)
    if kind == "light_leak":
        f = _leak_field(w, h, seed & 0xFFFF)
        drift = int((1 - x if not after else x - 1) * f.shape[1] * .25)
        f = cv2.resize(np.roll(f, drift, axis=1), (w, h), interpolation=cv2.INTER_CUBIC)
        c = np.array(G.col(T("leak_color", "gold"), G.GOLD), np.float32) / 255
        c = c * .7 + .3; k = float(T("leak_strength", .55)) * x ** 1.3
        add = f[..., None] * c * k
        return np.clip(1 - (1 - img) * (1 - add) + .08 * x ** 2, 0, 1)          # screen blend + a touch of exposure
    if kind == "dip":
        col = _colour(T("dip_color", "stage"), S); a = ease("inOutSine", x)
        return img * (1 - a) + col * a
    raise SystemExit(f"unknown transition '{kind}': cut | {' | '.join(LEGACY + TRANSITIONS)}")

def boundary(TL, t):
    """the cut time of the transition window t sits in (its seed: every frame of one transition shares it)"""
    best = None
    for tb, kind in TL.trans:
        d = trans_dur(TL.S, kind)
        if d and abs(t - tb) < d and (best is None or abs(t - tb) < abs(t - best)): best = tb
    return t if best is None else best

def trans_dur(S, kind):
    return 0.0 if kind in (None, "cut") else float(_S(S, f"transitions.{kind}_s", .12))

def limit_transitions(TL):
    """rate-limit a timeline's transitions (restraint): a non-cut transition within craft.transitions.min_gap_s of the
    previous kept one becomes a cut, and kinds beyond creative.transition_kinds_max (first come, first kept) become cuts.
    Patches TL.trans and the cutaways' in / out (so mix gives a downgraded transition no whoosh). Returns notes."""
    S = TL.S; gap = float(_S(S, "craft.transitions.min_gap_s", 0) or 0); kmax = _S(S, "creative.transition_kinds_max", None)
    if not _S(S, "craft.transitions.enforce", True): return []
    notes, kept, kinds, drop = [], [], [], set()
    for k, (tb, kind) in sorted(enumerate(TL.trans), key=lambda x: x[1][0]):
        if kind in (None, "cut"): continue
        if kmax is not None and kind not in kinds and len(kinds) >= int(kmax):
            drop.add(k); notes.append(f"{kind} at {tb:.2f}s -> cut (creative.transition_kinds_max {kmax}: {', '.join(kinds)} already used)"); continue
        if gap and kept and tb - kept[-1] < gap - 1e-6 and tb != kept[-1]:
            drop.add(k); notes.append(f"{kind} at {tb:.2f}s -> cut ({tb - kept[-1]:.2f}s after the last transition < craft.transitions.min_gap_s {gap:g})"); continue
        if kind not in kinds: kinds.append(kind)
        kept.append(tb)
    if drop:
        gone = {(round(TL.trans[k][0], 6), TL.trans[k][1]) for k in drop}
        TL.trans = [(tb, "cut" if k in drop else kind) for k, (tb, kind) in enumerate(TL.trans)]
        for c in TL.cuts:
            for side, key in (("start", "in"), ("end", "out")):
                if (round(c[side], 6), c.get(key)) in gone: c[key] = "cut"
    return notes


# ================================================================== text behind the speaker: the face track
def _gauss(x, sigma):
    """zero-phase Gaussian smoothing of a 1-D series (edges held: reflect would invent motion past the segment ends)"""
    if sigma <= 0 or len(x) < 2: return np.asarray(x, np.float64)
    r = int(math.ceil(3 * sigma)); k = np.exp(-.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    return np.convolve(np.pad(np.asarray(x, np.float64), r, mode="edge"), k, mode="valid")

def smooth_s(S, fps):
    """the face-track smoothing of text_behind as a Gaussian sigma in frames: style craft.behind.smooth_s is in seconds,
    so the follow is equally calm at 24, 30 and 60 fps"""
    return max(0.0, float(_S(S, "craft.behind.smooth_s", .2))) * float(fps or 30)

def _face_rows(F):
    """per-frame (cx, eye_y, top, chin, w, h) of the raw face rows; missing rows are filled from their neighbours"""
    def eyes(f):
        if len(f) >= 14 and any(f[4:8]): return (f[4] + f[6]) / 2, (f[5] + f[7]) / 2
        return f[0] + f[2] / 2, f[1] + f[3] * .4
    R = np.full((len(F), 6), np.nan)
    for j, f in enumerate(F):
        if f is None or len(f) < 4: continue
        ex, ey = eyes(f); R[j] = (ex, ey, f[1] - .32 * f[3], f[1] + f[3], f[2], f[3])
    ok = ~np.isnan(R[:, 0])
    if not ok.any(): return None
    idx = np.arange(len(F))
    for c in range(6): R[:, c] = np.interp(idx, idx[ok], R[ok, c])
    return R

def face_track(TL, sid, k, sigma=None):
    """the presenter's face at plate frame k of segment sid: {cx (eye midpoint x), eye_y, top (head top: hair line
    estimate), chin, w, h} in plate px, or None without faces. Smoothed with a zero-phase Gaussian whose sigma is in
    SECONDS (style craft.behind.smooth_s), over the whole segment track (computed once per segment and process): raw face
    boxes jump 10-20 px between detections, and a window counted in frames was twice as nervous at 60 fps as at 30 (MOT-03)."""
    F = TL.faces.get(sid) or []
    if not F: return None
    sg = smooth_s(TL.S, TL.FPS) if sigma is None else float(sigma)
    cache = TL.__dict__.setdefault("_face_tracks", {})
    key = (sid, round(sg, 4), len(F))
    if key not in cache:
        R = _face_rows(F)
        cache[key] = None if R is None else np.stack([_gauss(R[:, c], sg) for c in range(6)], 1)
    T = cache[key]
    if T is None: return None
    r = T[min(max(int(k), 0), len(T) - 1)]
    return {"cx": float(r[0]), "eye_y": float(r[1]), "top": float(r[2]), "chin": float(r[3]), "w": float(r[4]), "h": float(r[5])}

def seg_scale(TL, sid):
    """the tightest zoom a segment is shown at (its zoom with the full creep, or a snap punch-in inside it): text_behind
    fits its type to that view once, so it never re-fits mid-shot"""
    s = next((x for x in TL.segs if x["id"] == sid), None)
    z = float((getattr(TL, "zoom", {}) or {}).get(sid, 1.0)) * (1 + float(getattr(TL, "creep", 0.0) or 0.0))
    sn = getattr(TL, "snap", None)
    if sn and s is not None and sn[0] < s["t1"] and s["t0"] < sn[1]: z = max(z, float(sn[2]))
    return z

def behind_size(TL):
    """one type size for every `text_behind` in the video (GFX-20): the smallest size any instance fits at, in canvas px.
    Instances with an explicit `size` keep their own fit and are left out. None when no instance needs harmonising."""
    if "_behind_size" in TL.__dict__: return TL.__dict__["_behind_size"]
    from .templates import craft as TC
    got = []
    for r in (getattr(TL, "E", {}) or {}).get("roto", []) or []:
        if (r or {}).get("template") != "text_behind" or "size" in (r.get("params") or {}): continue
        got.append(TC.fitted_size(r.get("params") or {}, TL.S, seg_scale(TL, r.get("segment"))))
    TL.__dict__["_behind_size"] = min(got) if len(got) > 1 else None
    return TL.__dict__["_behind_size"]

def roto_ctx(TL, s, k):
    """extra ctx a roto template gets on an A-roll frame: k (plate frame), face (smoothed, now), face_at(t) (smoothed,
    at cut time t in this segment), frame_of(t) (plate frame of cut time t), matte_ok (the segment has a subject matte),
    seg_scale (the segment's tightest zoom) and behind_size (the video's harmonised text_behind size, or None)"""
    sid = s["id"]
    def frame_of(tt): return int(round((tt - s["t0"]) * TL.FPS))
    def face_at(tt): return face_track(TL, sid, frame_of(tt))
    return {"k": k, "face": face_track(TL, sid, k), "face_at": face_at, "frame_of": frame_of,
            "matte_ok": bool(getattr(TL, "matte_ok", {}).get(sid, True)), "seg_scale": seg_scale(TL, sid), "behind_size": behind_size(TL)}


# ================================================================== restraint
CRAFT_TEMPLATES = ("text_behind",)

def usage(E):
    """craft moves an edit.yaml asks for: [(kind, where)] (ramps, camera moves, match cuts, text behind). Non-cut
    transitions are counted by the existing transition-kinds budget."""
    out = []
    for j, x in enumerate((E or {}).get("broll") or []):
        if not isinstance(x, dict): continue
        if x.get("ramp"): out.append(("ramp", f"broll[{j}]"))
        cam = x.get("camera")
        if cam and (cam if isinstance(cam, str) else (cam.get("move") or "none")) != "none": out.append(("camera", f"broll[{j}]"))
        if x.get("match"): out.append(("match", f"broll[{j}]"))
    for c in (E or {}).get("cutaways") or []:
        p = (c or {}).get("params") or {}
        if p.get("ramp"): out.append(("ramp", f"cutaway {c.get('id')}"))
        if p.get("camera"): out.append(("camera", f"cutaway {c.get('id')}"))
    for r in (E or {}).get("roto") or []:
        if (r or {}).get("template") in CRAFT_TEMPLATES: out.append(("text_behind", f"roto {r.get('segment')}"))
    return out

def budget(E, S, dur):
    """(used, allowed) craft moves for a timeline of `dur` s: creative.craft_per_30s, one 30 s allowance minimum"""
    per = float(_S(S, "creative.craft_per_30s", 4)); return len(usage(E)), round(per * max(1.0, dur / 30.0), 1)
