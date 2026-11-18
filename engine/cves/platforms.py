"""Platform profiles (styles/platforms.yaml): UI safe zones, caption line, duration band and loudness per platform.

    S.get("platform.target")        reels | tiktok | shorts | youtube | meta_feed | meta_stories | null
    platforms.safe_zone(S, w, h)    -> (x0, y0, x1, y1) px on a w x h frame

Boxes in the table are fractions of the frame, so they scale with the canvas: never assume a frame size. With no target the
legacy pixel box `platform.safe_zone` applies; it is in the `platform.size` design space and is scaled to the frame the
same way. See docs/VIRAL.md."""
import os, copy, yaml

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")
_T = {}


def table():
    """{name: profile} from styles/platforms.yaml (cached by mtime)"""
    p = os.path.join(HERE, "platforms.yaml"); m = os.path.getmtime(p)
    if _T.get("m") != m:
        with open(p, encoding="utf-8") as f: _T.update(m=m, d=yaml.safe_load(f) or {})
    return copy.deepcopy(_T["d"])


def names(): return sorted(table())


def target(S):
    t = S.get("platform.target") if S is not None else None
    if t in (None, "", "none", "null"): return None
    t = str(t).strip().lower()
    if t not in table(): raise SystemExit(f"platform.target '{t}' is not a platform profile (one of {', '.join(names())}; styles/platforms.yaml)")
    return t


def profile(S):
    """the active profile dict (with `name`) or None when no platform.target is set"""
    t = target(S)
    return dict(table()[t], name=t) if t else None


def _design_size(S):
    sz = S.get("canvas.size") or S.get("platform.size") or None
    return (float(sz[0]), float(sz[1])) if sz else None


def box_px(frac, w, h):
    x0, y0, x1, y1 = frac
    return (int(round(x0 * w)), int(round(y0 * h)), int(round(x1 * w)), int(round(y1 * h)))


def safe_zone(S, w, h):
    """text safe zone in px on a w x h frame: the active platform's `safe` box, else the style's `platform.safe_zone`
    (pixels in the platform.size design space, scaled to w x h), else None (no zone)."""
    pf = profile(S)
    if pf: return box_px(pf["safe"], w, h)
    z = S.get("platform.safe_zone")
    if not z: return None
    ds = _design_size(S) or (w, h)
    kx, ky = w / ds[0], h / ds[1]
    return (int(round(z[0] * kx)), int(round(z[1] * ky)), int(round(z[2] * kx)), int(round(z[3] * ky)))


def caption_bottom(S, h):
    """px line burned-in captions end above (None when no platform profile is active)"""
    pf = profile(S)
    return int(round(pf["caption_bottom"] * h)) if pf and pf.get("caption_bottom") is not None else None


def duration(S):
    """(ideal_lo, ideal_hi, max) seconds of the active platform, or None"""
    pf = profile(S)
    if not pf: return None
    d = pf.get("duration") or {}; lo, hi = d.get("ideal") or [0, 1e9]
    return float(lo), float(hi), float(d.get("max") or 1e9)


def apply(d, layers):
    """style.load hook: with a platform.target, fill platform.safe_zone (px of the design canvas), sound.master_lufs and
    sound.true_peak from the profile unless a style layer above default.yaml set them itself. `layers` = those layers."""
    pl = d.get("platform") or {}
    t = pl.get("target")
    if t in (None, "", "none", "null"): return d
    t = str(t).strip().lower(); T = table()
    if t not in T: raise SystemExit(f"platform.target '{t}' is not a platform profile (one of {', '.join(sorted(T))}; styles/platforms.yaml)")
    pf = T[t]
    def set_by_layer(sec, key): return any(isinstance(L.get(sec), dict) and key in L[sec] for L in layers)
    sz = (d.get("canvas") or {}).get("size") or pl.get("size")
    if sz and not set_by_layer("platform", "safe_zone"):
        d.setdefault("platform", {})["safe_zone"] = list(box_px(pf["safe"], sz[0], sz[1]))
    snd = d.setdefault("sound", {})
    if pf.get("lufs") is not None and not set_by_layer("sound", "master_lufs"): snd["master_lufs"] = pf["lufs"]
    if pf.get("true_peak") is not None and not set_by_layer("sound", "true_peak"): snd["true_peak"] = pf["true_peak"]
    return d
