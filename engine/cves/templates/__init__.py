"""Template registry. A template = render(t, p, ctx) -> list[El] and cues(p) -> list[(t, sfx, gain_db, kw)].
All times are cut-time seconds. Add a template: write the function, register it here, document it in docs/TEMPLATES.md."""
import numpy as np
from PIL import Image
from .. import gfx as G

class El:
    """one drawn element: an RGBA layer + what it is (for the element log and QC)"""
    __slots__ = ("im", "id", "role", "text", "t_key", "asset", "font")
    def __init__(self, im, id, role, text=None, t_key=None, asset=None, font=None):
        self.im, self.id, self.role, self.text, self.t_key, self.asset, self.font = im, id, role, text, t_key, asset, font

def faded(fn, alpha):
    im = G.layer(fn)
    if alpha < 1:
        a = np.asarray(im).copy(); a[..., 3] = (a[..., 3] * max(0, alpha)).astype(np.uint8); im = Image.fromarray(a)
    return im

# ---- registry: auto-discovered. Every module in this package (and every *.py in $CVES_TEMPLATES / ~/.cves/templates /
# PROJECT/Brand/templates) that defines `T = {name: (render, cues)}` is registered. Its kind comes from module-level
# `KIND = "cutaway" | "roto" | "chest" | "end" | "media" | "overlay"`, else from the module name. No list to edit by hand.
import os, sys, pkgutil, importlib, importlib.util   # noqa: E402

REGISTRY, KIND, SOURCE = {}, {}, {}
LOAD_HOOKS = []      # fn(folder, origin) called by load_dir (motion.py: a `templates` folder's sibling `motion` pieces)

def _register(mod, origin):
    T = getattr(mod, "T", None)
    if not isinstance(T, dict): return
    kind = getattr(mod, "KIND", None) or {"cutaways": "cutaway"}.get(mod.__name__.rsplit(".", 1)[-1], mod.__name__.rsplit(".", 1)[-1])
    for name, fns in T.items():
        REGISTRY[name] = fns; KIND[name] = (getattr(mod, "KINDS", {}) or {}).get(name, kind); SOURCE[name] = origin

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
    if name not in REGISTRY: raise SystemExit(f"unknown template '{name}'. Available: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[name]
