"""Template registry. A template = render(t, p, ctx) -> list[El] and cues(p) -> list[(t, sfx, gain_db, kw)].
All times are cut-time seconds. Add a template: write the function, register it here, document it in docs/TEMPLATES.md."""
import numpy as np
from PIL import Image
from .. import gfx as G

class El:
    """one drawn element: an RGBA layer + what it is (for the element log)"""
    __slots__ = ("im", "id", "role", "text", "t_key", "asset", "font", "size")
    def __init__(self, im, id, role, text=None, t_key=None, asset=None, font=None, size=None):
        self.im, self.id, self.role, self.text, self.t_key, self.asset, self.font = im, id, role, text, t_key, asset, font
        self.size = size              # optional: the type size in canvas px (GFX-20 compares it when every instance logs it)

def faded(fn, alpha):
    im = G.layer(fn)
    if alpha < 1:
        bb = im.getbbox()                     # alpha * 0 stays 0: only the drawn box changes
        if bb is None: return im
        a = np.asarray(im.crop(bb)).copy(); a[..., 3] = (a[..., 3] * max(0, alpha)).astype(np.uint8)
        im = im.copy(); im.paste(Image.fromarray(a), bb[:2])
    return im

# ---- registry: auto-discovered. Every module in this package (and every *.py in $CVES_TEMPLATES / ~/.cves/templates /
# PROJECT/Brand/templates) that defines `T = {name: (render, cues)}` is registered. Its kind comes from module-level
# `KIND = "cutaway" | "roto" | "chest" | "end" | "media" | "overlay"`, else from the module name. No list to edit by hand.
import os, sys, pkgutil, importlib, importlib.util   # noqa: E402

REGISTRY, KIND, SOURCE, LAYOUT, RASTER = {}, {}, {}, {}, {}
LOAD_HOOKS = []      # fn(folder, origin) called by load_dir (motion.py: a `templates` folder's sibling `motion` pieces)

def _register(mod, origin):
    T = getattr(mod, "T", None)
    if not isinstance(T, dict): return
    kind = getattr(mod, "KIND", None) or {"cutaways": "cutaway"}.get(mod.__name__.rsplit(".", 1)[-1], mod.__name__.rsplit(".", 1)[-1])
    nat = getattr(mod, "NATIVE", None)
    for name, fns in T.items():
        lay = "native" if (nat is True or (isinstance(nat, (set, list, tuple, dict)) and name in nat)) else ("fixed" if getattr(mod, "DESIGN", False) else "relative")
        REGISTRY[name] = fns; KIND[name] = (getattr(mod, "KINDS", {}) or {}).get(name, kind); SOURCE[name] = origin; LAYOUT[name] = lay
        rs = getattr(mod, "RASTER", True)              # False / {names}: lay out AND rasterise at a 1080 short side, then scale
        RASTER[name] = not (rs is False or (isinstance(rs, (set, list, tuple, dict)) and name not in rs))

for _m in pkgutil.iter_modules(__path__):
    if not _m.name.startswith("_"): _register(importlib.import_module(f"{__name__}.{_m.name}"), "builtin")

def load_dir(d, origin=None):
    """register every template module in folder d (user / project templates); later folders override earlier ones"""
    d = os.path.expanduser(d or "")
    got = [n for h in LOAD_HOOKS for n in (h(d, origin) or [])]
    if not os.path.isdir(d): return got
    for f in sorted(os.listdir(d)):
        if f.endswith(".py") and not f.startswith("_"):
            spec = importlib.util.spec_from_file_location(f"cves_user_templates.{f[:-3]}", os.path.join(d, f))
            mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod; spec.loader.exec_module(mod)
            before = set(REGISTRY); _register(mod, origin or d); got += sorted(set(REGISTRY) - before) or list(getattr(mod, "T", {}))
    return got

for _d in (os.environ.get("CVES_TEMPLATES"), "~/.cves/templates"): load_dir(_d)

def get(name):
    """(render, cues) of a template. render is wrapped so it lays out on any canvas (see _canvas_render)."""
    if name not in REGISTRY: raise SystemExit(f"unknown template '{name}'. Available: {', '.join(sorted(REGISTRY))}")
    fn, cues = REGISTRY[name][0], REGISTRY[name][1]
    return (lambda t, p, ctx, _n=name, _f=fn: _canvas_render(_n, _f, t, p, ctx)), cues

# ---- any canvas (docs/FORMATS.md, docs/TEMPLATES.md "Layout on any canvas")
# Templates write px values designed for a frame whose short side is 1080 px. The canvas is G.W x G.H (style canvas.size).
#  * native templates (module-level NATIVE = True or {names}) draw on the canvas itself and scale their own px by G.U
#    (resolution-independent pictures such as broll_shot): no adapter;
#  * relative templates (the default) lay out from G.W / G.H / G.safe(): on a canvas whose short side is not 1080 they
#    lay out in a "design canvas" of the same aspect with a 1080 short side and are RASTERISED at the real canvas
#    (G.set_raster: coordinates, type, strokes and icons scale by G.U inside G.layer), so 4K graphics are drawn at 4K.
#    A module that touches layer pixels in ways the raster scale does not cover sets RASTER = False (or {names that are
#    raster-safe}): it is drawn at the design canvas and the layers are scaled by G.U (softer at 4K);
#  * fixed templates (module-level DESIGN = True: hard-coded 1080x1920 coordinates) draw in 1080x1920 and are fitted, per
#    instance, into the canvas safe zone: the union of what they draw over their span (sampled) is scaled (never up) and
#    centred. Kind chest / overlay / media are never fitted (they anchor to the presenter).
# At 1080x1920 both are the identity: the call goes straight through (golden frames unchanged).
_FIT = {}

def _design_size():
    u = G.U; return (int(round(G.W / u)), int(round(G.H / u)))

def _scaled_ctx(ctx, a, ox, oy, dsize):
    """ctx for a call laid out in another space: chin positions mapped; ctx["aroll"] resized to dsize (None: kept at the
    canvas resolution, for raster-scaled calls whose picture buffers are in layer px)"""
    if a == 1 and not ox and not oy: return ctx
    c = dict(ctx)
    for k in ("chin", "chin_hold"):
        if c.get(k) is not None: c[k] = (c[k] - oy) / a
    if dsize is not None and c.get("aroll") is not None and not callable(c["aroll"]):
        import cv2
        rgb, m = c["aroll"][0], c["aroll"][1]
        c["aroll"] = (cv2.resize(rgb, dsize, interpolation=cv2.INTER_AREA), cv2.resize(m, dsize, interpolation=cv2.INTER_AREA))
    return c

def _call_in(size, fn, t, p, ctx, raster=None):
    W0, H0 = G.W, G.H
    G.set_canvas(*size)
    if raster: G.set_raster(*raster)
    try: return fn(t, p, ctx)
    finally: G.set_canvas(W0, H0)

def _fit_for(name, fn, p, ctx):
    """(a, ox, oy) mapping a fixed-layout (G.DESIGN) template instance onto the canvas safe zone (cached per instance)"""
    import json
    try: key = (name, json.dumps(p, sort_keys=True, default=str), round(ctx.get("start", 0), 4), round(ctx.get("end", 0), 4), G.W, G.H)
    except (TypeError, ValueError): key = (name, id(p), G.W, G.H)
    if key in _FIT: return _FIT[key]
    a0, b0 = ctx.get("start", 0.), ctx.get("end", ctx.get("start", 0.) + 1)
    if b0 <= a0: b0 = a0 + 1
    box = None
    for f in (.12, .3, .5, .7, .88, .97):
        for el in _call_in(G.DESIGN, fn, a0 + (b0 - a0) * f, p, ctx) or []:
            im = el.im if isinstance(el.im, Image.Image) else Image.fromarray(np.clip(el.im * 255, 0, 255).astype(np.uint8))
            bb = im.getbbox()
            if bb: box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
    z = G.safe(); zw, zh = z[2] - z[0], z[3] - z[1]
    if box is None: box = (0, 0) + G.DESIGN
    bw, bh = max(1, box[2] - box[0]), max(1, box[3] - box[1])
    a = min(G.U, zw / bw, zh / bh)                      # never larger than the design size at this canvas scale
    ox = (z[0] + z[2]) / 2 - a * (box[0] + box[2]) / 2; oy = (z[1] + z[3]) / 2 - a * (box[1] + box[3]) / 2
    _FIT[key] = (a, ox, oy)
    if len(_FIT) > 512: _FIT.pop(next(iter(_FIT)))
    return _FIT[key]

def _canvas_render(name, fn, t, p, ctx):
    fixed = LAYOUT.get(name) == "fixed" and KIND.get(name) not in ("chest", "overlay", "media")
    if G.is_design() or LAYOUT.get(name) == "native" or (not fixed and G.U == 1): return fn(t, p, ctx)
    if fixed:
        a, ox, oy = _fit_for(name, fn, p, ctx); size = G.DESIGN
    else:
        a, ox, oy = G.U, 0., 0.; size = _design_size()
        if RASTER.get(name, True):                     # lay out at a 1080 short side, draw at the canvas's real resolution
            W, H = G.W, G.H
            els = _call_in(size, fn, t, p, _scaled_ctx(ctx, a, ox, oy, None), raster=(W, H)) or []
            for el in els:
                sz = el.im.size if isinstance(el.im, Image.Image) else (el.im.shape[1], el.im.shape[0])
                if sz != (W, H): el.im = G.place(el.im, W / sz[0], 0., 0.)        # a layer drawn at the layout size (raw pixels)
            return els
    els = _call_in(size, fn, t, p, _scaled_ctx(ctx, a, ox, oy, size)) or []
    for el in els: el.im = G.place(el.im, a, ox, oy)
    return els
