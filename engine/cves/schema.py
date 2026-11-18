"""Lightweight validation of Edit/edit.yaml, Edit/selects.yaml and every style layer, before anything renders.

    errors, warnings = schema.validate(pr)          # lists of "yaml.path: message" strings

`cves validate` prints them; `cves render` / `cves build` stop on errors. No extra dependency: the checks are plain Python.
Every message starts with the YAML path of the offending value, e.g. `cutaways[3].params.price: expected number, got 'abc'`.

What is checked
- types and required keys of every edit.yaml section (`EDIT` below) and of selects.yaml clips;
- template names exist in `cves.templates.REGISTRY` (project Brand/templates included) and suit the slot (a roto template
  in `cutaways:` is a warning);
- template params: required params (read as `p["x"]` by the template), types inferred from the template's own defaults
  (`p.get("size", 200)` -> number), time params (`at`, `*_at`, `start`/`end`, `[t, dur]` pairs) inside the timeline; a
  module may declare `PARAMS = {template: {param: type}}` to be exact (types: number, int, str, bool, list, dict, time,
  path, color, asset, any; `?` suffix = optional, `!` suffix = required);
- times inside the timeline (edl.json + end card), cutaways not overlapping (before and after segment snapping);
- roto / chest / aroll.zoom segment ids exist in edl.json, one roto per segment;
- asset paths and asset ids resolve (project folder, repo, edit.yaml `assets:`, Edit/assets.json);
- style keys (edit.yaml `style:`, Edit/style.yaml, Brand/style.yaml, the preset) are known to styles/default.yaml:
  unknown keys are warnings with a did-you-mean suggestion; a wrong type against the default is a warning."""
import os, ast, difflib, inspect, json, textwrap
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TRANSITIONS = ("cut", "whip", "glitch", "fade")
MEDIA_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".tif", ".tiff", ".bmp", ".mp4", ".mov", ".mkv", ".webm", ".m4v",
             ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aif", ".aiff", ".ttf", ".otf", ".woff", ".woff2", ".json", ".lottie")
# style maps whose keys are data (any name is fine), not schema
OPEN_STYLE = {"colors", "font_files", "font_files.script_fallback", "captions.per_style", "sound.transition_sfx", "media.device_box",
              "_evidence", "_inspire"}
STYLE_META = {"name", "preset", "_evidence", "_inspire", "_sources", "description", "extends"}

# ------------------------------------------------------------------ edit.yaml spec
# type strings: number int str bool list dict time path color asset any; "a|b" = either; "?" = optional (default), "!" = required
CUT = {"id!": "str|int", "template!": "str", "start!": "time", "end!": "time", "in": "transition", "out": "transition",
       "snap": "bool", "params": "dict", "sfx": "any", "note": "str", "beat": "str"}
SEGREF = {"segment!": "segref", "template!": "str", "params": "dict", "note": "str"}
EDIT = {
    "project": {"client": "str", "title": "str", "fps": "number|list|str", "size": "list", "raw": "path|null", "sources": "list", "language": "str"},
    "style": "style",
    "edl": "str",
    "aroll": {"zoom": "zoommap", "creep": "number", "snap": {"start!": "time", "end!": "time", "zoom!": "number"},
              "exposure_match": "bool", "lift": "bool"},
    "captions": "captions",
    "cutaways": [CUT],
    "roto": [SEGREF],
    "chest": [dict(SEGREF, **{"segment!": "segref|segreflist"})],
    "end_card": {"template!": "str", "duration!": "number", "params": "dict", "in": "transition"},
    "music": "music",
    "sfx": {"auto": "bool", "extra": [{"t!": "time", "name!": "str", "gain": "number", "pitch": "number", "kw": "dict"}]},
    "transitions": [{"t!": "time", "kind!": "transition"}],
    "qc": {"topic_keywords": "list", "brand_tail": "list", "duration": "list|null", "skip": "list", "waive": "any"},
    "assets": "assets",
    "variants": "any",
    "delivery": "dict",
    "notes": "any",
}


class V:
    def __init__(self, pr):
        self.pr = pr; self.errors, self.warnings = [], []
        self.segs, self.fps, self.T_END, self.T_ALL = [], None, None, None
        self.declared_assets, self.registry_assets = {}, {}

    def err(self, path, msg): self.errors.append(f"{path}: {msg}")
    def warn(self, path, msg): self.warnings.append(f"{path}: {msg}")


def _did_you_mean(k, options):
    m = difflib.get_close_matches(str(k), [str(o) for o in options], n=1, cutoff=.6)
    return f" (did you mean '{m[0]}'?)" if m else ""


def _num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)


def _tname(v):
    return {bool: "bool", int: "int", float: "number", str: "string", list: "list", dict: "mapping", type(None): "null"}.get(type(v), type(v).__name__)


def _show(v):
    s = repr(v); return s if len(s) <= 40 else s[:37] + "..."


# ------------------------------------------------------------------ helpers: time, paths, assets
def _time(v, path, val, lo=0.0, hi=None, what="timeline"):
    if not _num(val): v.err(path, f"expected a time in seconds, got {_tname(val)} {_show(val)}"); return False
    hi = v.T_ALL if hi is None else hi
    if val < lo - 1e-6 or (hi is not None and val > hi + 1e-6):
        v.err(path, f"{val:g} s is outside the {what} (0-{hi:.2f} s)" if hi is not None else f"{val:g} s is negative"); return False
    return True


def _resolves(v, ref):
    """True if ref is a usable asset id or an existing path (project, repo); None if it is a declared asset with no file yet"""
    if not isinstance(ref, str) or not ref: return False
    if ref in v.registry_assets:
        return os.path.exists(v.pr.p(v.registry_assets[ref].get("path", ""))) or None
    if ref in v.declared_assets:
        d = v.declared_assets[ref] or {}
        p = d.get("path") if isinstance(d, dict) else None
        if p: return os.path.exists(p if os.path.isabs(p) else v.pr.p(p)) or None
        return None
    p = os.path.expanduser(ref)
    if os.path.isabs(p): return os.path.exists(p)
    return any(os.path.exists(os.path.join(b, p)) for b in (v.pr.root, REPO, os.path.join(REPO, "assets")))


def _looks_like_path(s):
    return isinstance(s, str) and s.lower().endswith(MEDIA_EXT) and len(s) < 400 and "\n" not in s


def _check_path(v, path, val, required=False):
    if val is None:
        if required: v.err(path, "a file is required")
        return
    if not isinstance(val, str): v.err(path, f"expected a file path or asset id, got {_tname(val)}"); return
    ok = _resolves(v, val)
    if ok is None: v.warn(path, f"asset '{val}' is declared but has no file yet (`cves assets todo`)")
    elif not ok: v.err(path, f"file not found: {val} (paths are relative to the project folder, or an asset id from `assets:`)")


# ------------------------------------------------------------------ generic typed walk
def _check(v, path, val, spec):
    if isinstance(spec, dict):
        if not isinstance(val, dict): v.err(path, f"expected a mapping, got {_tname(val)} {_show(val)}"); return
        keys = {k.rstrip("!?"): k for k in spec}
        for k, sk in keys.items():
            if sk.endswith("!") and k not in val: v.err(f"{path}.{k}" if path else k, "required key missing")
        for k, x in val.items():
            p = f"{path}.{k}" if path else str(k)
            if k not in keys: v.warn(p, f"unknown key{_did_you_mean(k, keys)}"); continue
            if x is None and not keys[k].endswith("!"): continue
            _check(v, p, x, spec[keys[k]])
        return
    if isinstance(spec, list):
        if not isinstance(val, list): v.err(path, f"expected a list, got {_tname(val)} {_show(val)}"); return
        for j, x in enumerate(val): _check(v, f"{path}[{j}]", x, spec[0])
        return
    alts = spec.split("|")
    if any(_is(v, path, val, a) for a in alts): return
    if len(alts) == 1 and alts[0] in SPECIAL: SPECIAL[alts[0]](v, path, val); return
    v.err(path, f"expected {' or '.join(a.replace('segreflist', 'list of segment ids').replace('segref', 'segment id') for a in alts)}, got {_tname(val)} {_show(val)}")


def _is(v, path, val, t):
    """type test only (no side-effects) for the simple types; special types run their own checker and return True"""
    if t == "any": return True
    if t == "null": return val is None
    if t == "number": return _num(val)
    if t == "int": return isinstance(val, int) and not isinstance(val, bool)
    if t == "str": return isinstance(val, str)
    if t == "bool": return isinstance(val, bool)
    if t == "list": return isinstance(val, list)
    if t == "dict": return isinstance(val, dict)
    if t == "time": return _num(val) and (_time(v, path, val) or True)
    if t == "transition":
        if isinstance(val, str) and val in TRANSITIONS: return True
        if isinstance(val, str): v.err(path, f"unknown transition '{val}' (one of {', '.join(TRANSITIONS)}){_did_you_mean(val, TRANSITIONS)}"); return True
        return False
    if t == "path": return isinstance(val, str) and (_check_path(v, path, val) or True)
    if t == "segref": return isinstance(val, str) and (_segref(v, path, val) or True)
    if t == "segreflist":
        if isinstance(val, list) and val and all(isinstance(x, str) for x in val):
            for j, x in enumerate(val): _segref(v, f"{path}[{j}]", x)
            return True
        return False
    if t in SPECIAL: return False
    return False


def _segref(v, path, sid):
    if not v.segs: return
    ids = [s["id"] for s in v.segs]
    if sid not in ids: v.err(path, f"segment '{sid}' not in edl.json{_did_you_mean(sid, ids)}")


# ------------------------------------------------------------------ special sections
def _zoommap(v, path, val):
    if not isinstance(val, dict): v.err(path, f"expected a mapping segment id -> zoom, got {_tname(val)}"); return
    for k, z in val.items():
        _segref(v, f"{path}.{k}", k)
        if not _num(z) or z <= 0: v.err(f"{path}.{k}", f"expected a zoom factor > 0, got {_show(z)}")


def _captions(v, path, val):
    if not isinstance(val, dict): v.err(path, f"expected a mapping, got {_tname(val)}"); return
    own = {"auto": "bool", "hide": "list", "fixes": "dict", "events": "list", "words": "list"}
    sty = (_default_style().get("captions") or {})
    for k, x in val.items():
        p = f"{path}.{k}"
        if k in own:
            if not _is(v, p, x, own[k]): v.err(p, f"expected {own[k]}, got {_tname(x)} {_show(x)}"); continue
        elif k in sty:
            _style_type(v, p, x, sty[k])
        else:
            v.warn(p, f"unknown key{_did_you_mean(k, list(own) + list(sty))}")
    for j, h in enumerate(val.get("hide") or []):
        p = f"{path}.hide[{j}]"
        if not (isinstance(h, list) and len(h) == 2 and all(_num(x) for x in h)): v.err(p, f"expected [start, end] seconds, got {_show(h)}"); continue
        if h[1] <= h[0]: v.err(p, f"end {h[1]} is not after start {h[0]}")
        for q, x in enumerate(h): _time(v, f"{p}[{q}]", x, hi=v.T_END)
    for k, x in (val.get("fixes") or {}).items():
        if not isinstance(x, str): v.err(f"{path}.fixes.{k}", f"expected the replacement text, got {_tname(x)}")
    for j, e in enumerate(val.get("events") or []):
        p = f"{path}.events[{j}]"
        if not isinstance(e, dict): v.err(p, "expected {start, end, words}"); continue
        for k in ("start", "end", "words"):
            if k not in e: v.err(f"{p}.{k}", "required key missing")
        for k in ("start", "end"):
            if k in e: _time(v, f"{p}.{k}", e[k], hi=v.T_END)


def _music(v, path, val):
    if not isinstance(val, dict): v.err(path, f"expected a mapping, got {_tname(val)}"); return
    own = {"file": "path|null", "drop_track": "number", "drop_cut": "number", "bed_lu": "number", "credits": "str", "offset": "number",
           "gain_db": "number", "fade_out": "number", "start": "number", "licence": "str", "license": "str", "url": "str", "beats": "any"}
    sty = (_default_style().get("music") or {})
    for k, x in val.items():
        p = f"{path}.{k}"
        if k in own:
            if x is None and own[k].endswith("null"): continue
            if not any(_is(v, p, x, t) for t in own[k].split("|")): v.err(p, f"expected {own[k].replace('|null', '')}, got {_tname(x)} {_show(x)}")
        elif k in sty: _style_type(v, p, x, sty[k])
        else: v.warn(p, f"unknown key{_did_you_mean(k, list(own) + list(sty))}")
    if _num(val.get("drop_cut")) and val["drop_cut"] > 0: _time(v, f"{path}.drop_cut", val["drop_cut"])


def _assets(v, path, val):
    if not isinstance(val, dict): v.err(path, f"expected a mapping asset id -> {{path | url | generate}}, got {_tname(val)}"); return
    for k, d in val.items():
        p = f"{path}.{k}"
        if not isinstance(d, dict): v.err(p, "expected {path: ...} or {url: ...} or {generate: {...}}"); continue
        if not any(x in d for x in ("path", "url", "generate", "stock")): v.err(p, "needs one of path, url, generate")
        if d.get("path"):
            q = d["path"]
            if not os.path.exists(q if os.path.isabs(q) else v.pr.p(q)): v.warn(f"{p}.path", f"file not found yet: {q} (`cves assets add --id {k} --file ...`)")


def _style_section(v, path, val):
    if not isinstance(val, dict): v.err(path, f"expected a mapping ({{preset: name}} and/or style keys), got {_tname(val)}"); return
    pre = val.get("preset")
    if pre is not None:
        if not isinstance(pre, str): v.err(f"{path}.preset", f"expected a preset name, got {_tname(pre)}")
        elif not os.path.exists(os.path.join(HERE, "styles", f"{pre}.yaml")):
            names = [f[:-5] for f in os.listdir(os.path.join(HERE, "styles")) if f.endswith(".yaml")]
            v.err(f"{path}.preset", f"style preset '{pre}' not found in engine/cves/styles{_did_you_mean(pre, names)}")
    check_style(v, {k: x for k, x in val.items() if k != "preset"}, path)


SPECIAL = {"zoommap": _zoommap, "captions": _captions, "music": _music, "assets": _assets, "style": _style_section}


# ------------------------------------------------------------------ style keys vs default.yaml
_DEF = {}
def _default_style():
    p = os.path.join(HERE, "styles", "default.yaml"); m = os.path.getmtime(p)
    if _DEF.get("m") != m:
        with open(p, encoding="utf-8") as f: _DEF.update(m=m, d=yaml.safe_load(f) or {})
    return _DEF["d"]


def _style_type(v, path, val, dflt):
    """warn when a style value's type clearly differs from its default (number vs string, list vs scalar)"""
    if dflt is None or val is None: return
    if _num(dflt) and not _num(val) and not isinstance(val, (list, str)): v.warn(path, f"expected a number like the default {_show(dflt)}, got {_tname(val)}")
    elif _num(dflt) and isinstance(val, str): v.warn(path, f"expected a number like the default {_show(dflt)}, got string {_show(val)}")
    elif isinstance(dflt, bool) and not isinstance(val, bool): v.warn(path, f"expected true/false, got {_tname(val)} {_show(val)}")
    elif isinstance(dflt, dict) and not isinstance(val, dict): v.warn(path, f"expected a mapping like the default, got {_tname(val)} {_show(val)}")


def check_style(v, d, path, base=None, dotted=""):
    """unknown style keys -> warnings (did-you-mean), obvious type mismatches -> warnings"""
    base = _default_style() if base is None else base
    for k, x in (d or {}).items():
        p = f"{path}.{k}" if path else str(k); dk = f"{dotted}.{k}" if dotted else str(k)
        if not dotted and k in STYLE_META: continue
        if dotted in OPEN_STYLE: continue
        if k not in base:
            v.warn(p, f"unknown style key{_did_you_mean(k, base)} (known keys: styles/default.yaml, docs/STYLE.md)"); continue
        if isinstance(base[k], dict) and isinstance(x, dict) and dk not in OPEN_STYLE: check_style(v, x, p, base[k], dk)
        else: _style_type(v, p, x, base[k])


# ------------------------------------------------------------------ templates: registry + params
_PSPEC = {}
def template_params(name):
    """{param: (type, required)} for a template, from its module's PARAMS declaration or inferred from its source
    (p["x"] = required; p.get("x", <literal>) = optional, typed by the literal). Returns (spec, open) where open=True means
    the template passes `p` on to other code, so unknown params cannot be judged."""
    from . import templates as T
    if name in _PSPEC: return _PSPEC[name]
    fns = T.REGISTRY.get(name); spec, open_ = {}, False
    if not fns: _PSPEC[name] = ({}, True); return _PSPEC[name]
    import sys
    mod = sys.modules.get(getattr(fns[0], "__module__", ""), None)
    decl = (getattr(mod, "PARAMS", None) or {}).get(name) if mod else None
    if decl:
        for k, t in decl.items():
            spec[k.rstrip("!?")] = (t.rstrip("!?"), k.endswith("!") or t.endswith("!"))
        _PSPEC[name] = (spec, False); return _PSPEC[name]
    for j, fn in enumerate(fns[:2]):
        try: src = textwrap.dedent(inspect.getsource(fn)); tree = ast.parse(src)
        except (OSError, TypeError, SyntaxError): open_ = True; continue
        f = tree.body[0] if tree.body and isinstance(tree.body[0], (ast.FunctionDef, ast.Lambda)) else None
        if not isinstance(f, ast.FunctionDef) or len(f.args.args) < 2: open_ = True; continue
        pn = f.args.args[1].arg if j == 0 else f.args.args[0].arg         # render(t, p, ctx) / cues(p, ctx)
        for node in ast.walk(f):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == pn:
                key = node.slice.value if isinstance(node.slice, ast.Constant) else None
                if isinstance(key, str): spec.setdefault(key, ("any", j == 0))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == pn and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value; t = "any"
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    c = node.args[1].value
                    t = "bool" if isinstance(c, bool) else "number" if isinstance(c, (int, float)) else "str" if isinstance(c, str) else "any"
                elif len(node.args) > 1 and isinstance(node.args[1], (ast.List, ast.Tuple)): t = "list"
                elif len(node.args) > 1 and isinstance(node.args[1], ast.Dict): t = "dict"
                if isinstance(key, str):
                    old = spec.get(key); spec[key] = (t if not old or old[0] == "any" else old[0], False)
            elif isinstance(node, ast.Name) and node.id == pn and not isinstance(getattr(node, "_parent", None), ast.Subscript):
                pass
        # p used other than p[...] / p.get(...): passed on (e.g. helper(p), **p, p.items()) -> unknown keys not judged
        for node in ast.walk(f):
            for ch in ast.iter_child_nodes(node): ch._parent = node
        for node in ast.walk(f):
            if isinstance(node, ast.Name) and node.id == pn:
                par = getattr(node, "_parent", None)
                ok = isinstance(par, ast.Subscript) and par.value is node
                ok = ok or (isinstance(par, ast.Attribute) and par.attr == "get")
                ok = ok or isinstance(par, ast.arguments) or isinstance(par, ast.arg)
                if not ok: open_ = True
    _PSPEC[name] = (spec, open_)
    return _PSPEC[name]


def _time_like(k): return k in ("at", "start", "end", "t", "time") or k.endswith("_at") or k.endswith("_t")


def _check_params(v, path, params, name, win):
    """params of one template use; win = (t0, t1) of the element on the cut timeline (for lead/lag warnings)"""
    if params is None: params = {}
    if not isinstance(params, dict): v.err(path, f"expected a mapping of template params, got {_tname(params)}"); return
    spec, open_ = template_params(name)
    for k, (t, req) in spec.items():
        if req and k not in params: v.err(f"{path}.{k}", f"required by template '{name}'")
    for k, x in params.items():
        p = f"{path}.{k}"
        if k not in spec and not open_ and spec:
            v.warn(p, f"template '{name}' does not read this param{_did_you_mean(k, spec)}")
        t = spec.get(k, ("any", False))[0]
        if x is None: continue
        if t in ("number", "int") and not _num(x): v.err(p, f"expected number, got {_tname(x)} {_show(x)}"); continue
        if t == "str" and not isinstance(x, (str, int, float)): v.err(p, f"expected text, got {_tname(x)} {_show(x)}"); continue
        if t == "bool" and not isinstance(x, bool): v.err(p, f"expected true/false, got {_tname(x)} {_show(x)}"); continue
        if t == "list" and not isinstance(x, list): v.err(p, f"expected a list, got {_tname(x)} {_show(x)}"); continue
        if t in ("path", "asset"): _check_path(v, p, x, required=False); continue
        if t == "time" or _time_like(k):
            if _num(x): _ptime(v, p, x, win)
            elif isinstance(x, list) and x and _num(x[0]) and _time_like(k): _ptime(v, f"{p}[0]", x[0], win)
            elif t == "time" or k in ("at", "start", "end"): v.err(p, f"expected a time in seconds, got {_tname(x)} {_show(x)}")
            continue
        _walk_param_values(v, p, x, win, k)


def _walk_param_values(v, path, x, win, key):
    """nested param values: file-like strings must resolve; [text, t] / {at: t} times must sit on the timeline"""
    if isinstance(x, str):
        if _looks_like_path(x) or key in ("logo", "asset", "image", "video", "file", "src", "icon_file"):
            if key in ("asset",) or _looks_like_path(x): _check_path(v, path, x)
    elif isinstance(x, dict):
        for k, y in x.items():
            p = f"{path}.{k}"
            if _time_like(str(k)) and _num(y): _ptime(v, p, y, win)
            elif _time_like(str(k)) and isinstance(y, list) and y and _num(y[0]): _ptime(v, f"{p}[0]", y[0], win)
            else: _walk_param_values(v, p, y, win, str(k))
    elif isinstance(x, list):
        for j, y in enumerate(x):
            # [text, t] / [text, t, accent] word lists (big_words, browser head)
            if j == 1 and isinstance(x[0], str) and _num(y) and len(x) <= 3: _ptime(v, f"{path}[1]", y, win)
            else: _walk_param_values(v, f"{path}[{j}]", y, win, key)


def _ptime(v, path, t, win):
    if v.T_ALL is None: return
    if not _time(v, path, t): return
    if win and (t < win[0] - 1.0 or t > win[1] + 1.0):
        v.warn(path, f"{t:g} s is outside this element's window {win[0]:.2f}-{win[1]:.2f} s (more than 1 s off: not shown?)")


def _template(v, path, name, slot):
    from . import templates as T
    if not isinstance(name, str): v.err(path, f"expected a template name, got {_tname(name)}"); return False
    if name not in T.REGISTRY:
        v.err(path, f"unknown template '{name}'{_did_you_mean(name, T.REGISTRY)} (`cves templates` lists them)"); return False
    kind = T.KIND.get(name)
    want = {"cutaways": ("cutaway", "media", "overlay"), "roto": ("roto",), "chest": ("chest", "overlay"), "end_card": ("end",)}.get(slot)
    if want and kind not in want: v.warn(path, f"template '{name}' is a {kind} template, used in `{slot}:`")
    return True


# ------------------------------------------------------------------ timeline context
def _load_timeline(v, E):
    edl = v.pr.json("edl.json") if os.path.exists(v.pr.e("edl.json")) else None
    if not edl:
        v.warn("edl", "Edit/edl.json missing: time and segment checks skipped (run `cves select`)"); return
    v.fps = float(edl.get("fps") or 0) or None
    if not v.fps: v.err("edl.json.fps", "missing"); return
    f0 = 0
    for s in edl.get("segments", []):
        n = round((s["out"] - s["in"]) * v.fps); v.segs.append(dict(s, f0=f0, n=n, t0=f0 / v.fps, t1=(f0 + n) / v.fps)); f0 += n
    v.T_END = f0 / v.fps
    end = E.get("end_card") if isinstance(E.get("end_card"), dict) else {}
    v.T_ALL = v.T_END + (end.get("duration") or 0 if _num(end.get("duration") or 0) else 0)


def _snap(v, t):
    b = [s["t0"] for s in v.segs] + [v.T_END]
    return min(b, key=lambda x: abs(x - t))


def _edit_specific(v, E):
    from . import templates as T
    seg_by = {s["id"]: s for s in v.segs}
    # ---- cutaways: template, params, order, overlap (raw and snapped)
    cuts = E.get("cutaways") or []
    if isinstance(cuts, list):
        ids, spans = {}, []
        for j, c in enumerate(cuts):
            p = f"cutaways[{j}]"
            if not isinstance(c, dict): continue
            if "id" in c:
                if c["id"] in ids: v.err(f"{p}.id", f"duplicate id '{c['id']}' (also cutaways[{ids[c['id']]}])")
                ids.setdefault(c["id"], j)
            ok_t = "template" in c and _template(v, f"{p}.template", c["template"], "cutaways")
            st, en = c.get("start"), c.get("end")
            if _num(st) and _num(en):
                if en <= st: v.err(f"{p}.end", f"{en:g} s is not after start {st:g} s")
                if v.T_END is not None and (st > v.T_END + 1e-6 or en > v.T_END + 1e-6):
                    v.err(f"{p}.end" if en > v.T_END else f"{p}.start", f"outside the A-roll timeline (0-{v.T_END:.2f} s; the end card follows it)")
                spans.append((st, en, j, c.get("snap", True)))
            if ok_t: _check_params(v, f"{p}.params", c.get("params"), c["template"], (st, en) if _num(st) and _num(en) else None)
        spans.sort()
        for (a0, a1, ja, sa), (b0, b1, jb, sb) in zip(spans[:-1], spans[1:]):
            tol = .5 / v.fps if v.fps else 1e-3
            if b0 < a1 - tol: v.err(f"cutaways[{jb}].start", f"{b0:g} s overlaps cutaways[{ja}] ({a0:g}-{a1:g} s)")
        if v.segs:
            snapped = []
            for st, en, j, sn in spans:
                s0, s1 = (_snap(v, st), _snap(v, en)) if sn else (st, en)
                if s1 <= s0: v.err(f"cutaways[{j}]", f"{st:g}-{en:g} s snaps to an empty span at {s0:.2f} s (segment boundaries); move it or set snap: false")
                snapped.append((s0, s1, j))
            snapped.sort()
            for (a0, a1, ja), (b0, b1, jb) in zip(snapped[:-1], snapped[1:]):
                if b0 < a1 - 1e-6 and b1 > b0 and a1 > a0:
                    v.err(f"cutaways[{jb}]", f"after snapping to segment boundaries it overlaps cutaways[{ja}] ({a0:.2f}-{a1:.2f} s); set snap: false on one")
    # ---- roto / chest
    seen = {}
    for slot in ("roto", "chest"):
        for j, c in enumerate(E.get(slot) or [] if isinstance(E.get(slot), list) else []):
            p = f"{slot}[{j}]"
            if not isinstance(c, dict): continue
            sids = [c.get("segment")] if isinstance(c.get("segment"), str) else (c.get("segment") or [])
            if slot == "roto" and isinstance(c.get("segment"), list): v.err(f"{p}.segment", "roto takes one segment id (a list is only allowed for chest)")
            if slot == "roto" and isinstance(c.get("segment"), str):
                if c["segment"] in seen: v.err(f"{p}.segment", f"segment '{c['segment']}' already has roto[{seen[c['segment']]}]: only one roto per segment renders")
                seen.setdefault(c["segment"], j)
            win = None
            ss = [seg_by[s] for s in sids if isinstance(s, str) and s in seg_by]
            if ss: win = (min(s["t0"] for s in ss), max(s["t1"] for s in ss))
            if "template" in c and _template(v, f"{p}.template", c["template"], slot): _check_params(v, f"{p}.params", c.get("params"), c["template"], win)
    # ---- end card
    e = E.get("end_card")
    if isinstance(e, dict) and "template" in e and _template(v, "end_card.template", e["template"], "end_card"):
        if _num(e.get("duration")) and e["duration"] <= 0: v.err("end_card.duration", "must be > 0")
        _check_params(v, "end_card.params", e.get("params"), e["template"], (v.T_END, v.T_ALL) if v.T_END is not None else None)
    # ---- aroll snap
    sn = (E.get("aroll") or {}).get("snap") if isinstance(E.get("aroll"), dict) else None
    if isinstance(sn, dict) and _num(sn.get("start")) and _num(sn.get("end")) and sn["end"] <= sn["start"]:
        v.err("aroll.snap.end", f"{sn['end']:g} s is not after start {sn['start']:g} s")
    # ---- sfx names exist
    sfx = E.get("sfx") if isinstance(E.get("sfx"), dict) else {}
    lib = os.path.join(REPO, "assets", "sfx")
    if os.path.isdir(lib):
        names = {os.path.splitext(f)[0] for f in os.listdir(lib)}
        for j, x in enumerate(sfx.get("extra") or []):
            if isinstance(x, dict) and isinstance(x.get("name"), str) and x["name"] not in names and not _resolves(v, x["name"]):
                v.warn(f"sfx.extra[{j}].name", f"no sound '{x['name']}' in assets/sfx{_did_you_mean(x['name'], names)}")


# ------------------------------------------------------------------ selects.yaml
SELECT_CLIP = {"id!": "str|int", "in!": "number", "out!": "number", "beat": "str", "src": "str", "note": "str", "text": "str", "keep": "any"}

def _selects(v):
    p = v.pr.e("selects.yaml")
    if not os.path.exists(p): return
    try:
        with open(p, encoding="utf-8") as f: sel = yaml.safe_load(f) or []
    except yaml.YAMLError as e:
        v.err("selects.yaml", f"YAML syntax error: {_yerr(e)}"); return
    clips = sel.get("clips") if isinstance(sel, dict) else sel
    if not isinstance(clips, list): v.err("selects.yaml", "expected a list of clips (or {clips: [...]})"); return
    beats = _default_style().get("grammar", {}).get("beats") or []
    ids = {}
    for j, c in enumerate(clips):
        path = f"selects.yaml clips[{j}]"
        if not isinstance(c, dict): v.err(path, f"expected {{id, in, out}}, got {_tname(c)}"); continue
        _check(v, path, c, SELECT_CLIP)
        if "id" in c:
            if c["id"] in ids: v.err(f"{path}.id", f"duplicate id '{c['id']}' (also clips[{ids[c['id']]}])")
            ids.setdefault(c["id"], j)
        if _num(c.get("in")) and _num(c.get("out")) and c["out"] <= c["in"]: v.err(f"{path}.out", f"{c['out']:g} s is not after in {c['in']:g} s")
        if isinstance(c.get("beat"), str) and beats and c["beat"] not in beats + ["X"]:
            v.warn(f"{path}.beat", f"'{c['beat']}' is not a story beat ({', '.join(beats)}, X){_did_you_mean(c['beat'], beats)}")
        if isinstance(c.get("src"), str):
            q = c["src"] if os.path.isabs(c["src"]) else v.pr.p(c["src"])
            if not os.path.exists(q): v.err(f"{path}.src", f"source not found: {c['src']} (relative to the project folder, e.g. Raw/<file>)")


def _yerr(e):
    m = getattr(e, "problem_mark", None)
    return f"line {m.line + 1}, column {m.column + 1}: {getattr(e, 'problem', e)}" if m else str(e)


# ------------------------------------------------------------------ entry points
def validate(pr, edit=None):
    """-> (errors, warnings): lists of 'yaml.path: message'. Reads Edit/edit.yaml (or the given dict), Edit/selects.yaml,
    Edit/edl.json, Edit/style.yaml, Brand/style.yaml and the templates registry. Never raises on bad content."""
    v = V(pr)
    from . import templates as T
    T.load_dir(pr.p("Brand", "templates"), "project")
    if edit is None:
        f = pr.e("edit.yaml")
        if not os.path.exists(f): v.err("edit.yaml", "Edit/edit.yaml missing (run `cves plan`)"); _selects(v); return v.errors, v.warnings
        try:
            with open(f, encoding="utf-8") as fh: edit = yaml.safe_load(fh) or {}
        except yaml.YAMLError as e:
            v.err("edit.yaml", f"YAML syntax error: {_yerr(e)}"); return v.errors, v.warnings
    if not isinstance(edit, dict): v.err("edit.yaml", f"expected a mapping at the top level, got {_tname(edit)}"); return v.errors, v.warnings
    v.declared_assets = edit.get("assets") if isinstance(edit.get("assets"), dict) else {}
    try:
        reg = pr.json("assets.json") or {}; v.registry_assets = reg.get("assets", {}) if isinstance(reg, dict) else {}
    except (ValueError, OSError): v.warn("Edit/assets.json", "unreadable")
    _load_timeline(v, edit)
    _check(v, "", edit, EDIT)
    _edit_specific(v, edit)
    for name, p in (("Edit/style.yaml", pr.e("style.yaml")), ("Brand/style.yaml", pr.p("Brand", "style.yaml"))):
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as fh: d = yaml.safe_load(fh) or {}
                if isinstance(d, dict): check_style(v, d, name)
                else: v.err(name, "expected a mapping of style keys")
            except yaml.YAMLError as e: v.err(name, f"YAML syntax error: {_yerr(e)}")
    pre = (edit.get("style") or {}).get("preset") if isinstance(edit.get("style"), dict) else None
    pp = os.path.join(HERE, "styles", f"{pre}.yaml") if isinstance(pre, str) else None
    if pp and os.path.exists(pp):
        with open(pp, encoding="utf-8") as fh: check_style(v, yaml.safe_load(fh) or {}, f"styles/{pre}.yaml")
    _selects(v)
    return v.errors, v.warnings


def report(errors, warnings):
    out = [f"ERROR   {e}" for e in errors] + [f"warning {w}" for w in warnings]
    out.append(f"{len(errors)} error(s), {len(warnings)} warning(s)" if (errors or warnings) else "edit.yaml, selects.yaml and style OK")
    return "\n".join(out)


def require_valid(pr):
    """for render / build: print warnings, stop with one actionable line on errors"""
    errors, warnings = validate(pr)
    for w in warnings[:20]: print(f"warning {w}")
    if len(warnings) > 20: print(f"... {len(warnings) - 20} more warnings (`cves validate`)")
    if errors:
        for e in errors[:20]: print(f"ERROR   {e}")
        raise SystemExit(f"{len(errors)} error(s) in the edit: fix them (see above, or run `cves validate`) and run again")
    return warnings


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="cves validate", description="check edit.yaml, selects.yaml and the style layers")
    ap.add_argument("project", nargs="?"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    from .project import Project
    pr = Project(a.project or os.getcwd())
    errors, warnings = validate(pr)
    print(json.dumps({"errors": errors, "warnings": warnings}, indent=1) if a.json else report(errors, warnings))
    return 1 if errors else 0
