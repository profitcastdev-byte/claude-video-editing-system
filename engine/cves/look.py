"""A-roll grade, fully driven by the style profile (`grade:` section, see docs/STYLE.md). No look is hard-coded here.

Relight (optional): the subject matte lets the background be pulled down. The edge is composited by DECONTAMINATION, not by
a feather: every edge pixel of the plate is a mix `a*subject + (1-a)*wall`, so the wall behind it is estimated from the
nearby pure-background pixels, the subject colour is un-mixed, and the pixel is rebuilt as `a*graded subject +
(1-a)*darkened wall`. The old soft matte (1 px erode + 3 px blur) gave every wall pixel 2-7 px outside the edge a few
percent of the UN-darkened plate, which read as a bright ring (+11..+22 Y over the wall).
Widening a feather to hide an edge leaks the bright wall round the head and reads as an "aura"."""
import numpy as np, cv2

LUMA = np.array([.2126, .7152, .0722], np.float32)


def soft_matte(a):
    """legacy edge (1 px erode, 3 px blur). Kept for callers that only need a smooth mask; grade() no longer uses it."""
    a = a.astype(np.float32) / (255 if a.dtype == np.uint8 else 1)
    a = cv2.erode(a, np.ones((3, 3), np.uint8))
    return cv2.GaussianBlur(a, (0, 0), 3)


def edge_alpha(alpha, lo=0.2, hi=0.8):
    """the matte as a float 0..1 with its uncertain tails clipped: alpha <= lo is background, >= hi is solid subject, linear
    between. RVM leaves a soft alpha several px out into the wall (and on matte misses); a narrower [lo, hi] keeps the
    transition on the true edge (the 0.5 line) instead of spreading graded subject light over the darkened wall."""
    a = alpha.astype(np.float32) / (255 if alpha.dtype == np.uint8 else 1)
    if lo > 0 or hi < 1: a = np.clip((a - lo) / max(1e-6, hi - lo), 0, 1)
    return a


def _blur(x, sigma):
    """Gaussian blur; wide kernels run at half resolution (the result is smooth anyway, 4x cheaper)"""
    if sigma < 3 or min(x.shape[:2]) < 64: return cv2.GaussianBlur(x, (0, 0), sigma)
    h, w = x.shape[:2]
    small = cv2.resize(x, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(small, (0, 0), sigma / 2), (w, h), interpolation=cv2.INTER_LINEAR)


def decontaminate(rgb, a, sigma=6.0):
    """split rgb = a*F + (1-a)*B at the matte edge. Returns (F subject colour, B wall colour). B is the normalised blur of the
    pure-background pixels (a == 0) round each edge pixel; away from the edge F = B = rgb."""
    edge = (a > 0) & (a < 1)
    if not edge.any(): return rgb, rgb
    bgw = (a <= 0).astype(np.float32)
    num = _blur(rgb * bgw[..., None], sigma)
    den = _blur(bgw, sigma)[..., None]
    wall = num / np.maximum(den, 1e-4)
    has = (den[..., 0] > 1e-3) & edge             # an edge pixel deep in a subject hole has no wall to estimate from
    B = rgb.copy(); B[has] = wall[has]
    F = rgb.copy(); ae = np.maximum(a[has], .05)[:, None]
    F[has] = np.clip((rgb[has] - (1 - a[has])[:, None] * wall[has]) / ae, 0, 1)
    return F, B


def dehalo(B, a, px=10.0):
    """clamp the wall within `px` of the subject edge to the wall level `px`..3*px out (same neighbourhood). Phone cameras
    sharpen and bloom dark-on-bright edges: the plate already carries a bright band a few px wide round the silhouette, and
    once the wall is pulled down that band reads as a halo. Darker detail is kept; only brightness above the local wall is cut."""
    if px <= 0: return B
    d = cv2.distanceTransform((a < .5).astype(np.uint8), cv2.DIST_L2, 3)
    near = (d > 0) & (d < px)
    if not near.any(): return B
    far = ((d >= px) & (d <= 3 * px)).astype(np.float32)
    s = px * 1.2
    lum = B @ LUMA
    den = _blur(far, s)
    ref = _blur(lum * far, s) / np.maximum(den, 1e-4)
    ok = near & (den > 1e-3) & (lum > ref)
    if not ok.any(): return B
    w = np.clip((px - d[ok]) / (.4 * px), 0, 1)              # full clamp up to 0.6*px out, fading to none at px
    k = 1 - w * (1 - ref[ok] / np.maximum(lum[ok], 1e-6))
    out = B.copy(); out[ok] = B[ok] * k[:, None]
    return out


_VIG = {}
def _vignette(h, w, cx, cy, amount):
    key = (h, w, int(cx) // 8, int(cy) // 8, round(amount, 3))
    if key not in _VIG:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - cx) / (w * .75)) ** 2 + ((yy - cy) / (h * .62)) ** 2)
        _VIG.clear() if len(_VIG) > 64 else None
        _VIG[key] = (1 - amount * np.clip(r - .35, 0, 1) ** 1.6)[..., None].astype(np.float32)
    return _VIG[key]


def grade(rgb, alpha, face=None, g=None):
    """rgb float32 0..1 (display-referred BT.709), alpha = subject matte (or None), face = (cx, cy) vignette centre,
    g = the style's `grade` dict."""
    g = g or {}; h, w, _ = rgb.shape
    gamma, gain = g.get("gamma", 1.0), g.get("gain", 1.0)
    tint = np.array(g.get("subject_tint", [1, 1, 1]), np.float32)
    def sub_grade(x):
        x = np.clip(gain * x ** gamma, 0, 1) if (gamma != 1.0 or gain != 1.0) else x
        return x if np.all(tint == 1) else x * tint          # x * 1.0 == x exactly: skip the full-frame multiply
    if g.get("relight") and alpha is not None:
        a = edge_alpha(alpha, *g.get("edge_alpha_range", [0.2, 0.8]))
        if g.get("edge_decontaminate", True):
            F, B = decontaminate(rgb, a, g.get("edge_wall_sigma", 6.0))
        else:
            F = B = rgb
        B = dehalo(B, a, g.get("edge_dehalo_px", 10.0))
        lum = (B @ LUMA)[..., None]
        bg = (lum + (B - lum) * g.get("background_saturation", 1.0)) * (2.0 ** g.get("background_stops", 0.0))
        bg = bg * np.array(g.get("background_tint", [1, 1, 1]), np.float32)
        m = a[..., None]
        out = sub_grade(F) * m + bg * (1 - m)
    else:
        out = sub_grade(rgb)
    v = g.get("vignette", 0.0)
    if v:
        cx, cy = face if face else (w / 2, h * .32)
        out = out * _vignette(h, w, cx, cy, v)
    sh = g.get("shoulder", 0.0)
    if sh:
        out = out / (1 + sh * out) * (1 + sh) * g.get("shoulder_gain", 1.0)
    lift = np.array(g.get("black_lift", [0, 0, 0]), np.float32)
    if lift.any(): out = out + lift * (1 - out)
    return np.clip(out, 0, 1).astype(np.float32, copy=False)
