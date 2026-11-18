"""The style profile: the ONLY place a look lives. Nothing about a client, brand or look is hard-coded in the engine.

Merge order (later wins):
  1. styles/default.yaml            neutral, safe defaults (no brand, no house look)
  2. styles/<preset>.yaml           optional named preset (edit.yaml: style.preset)
  3. PROJECT/Edit/style.yaml        written by `cves inspire` from the client's reference edits
  4. PROJECT/Brand/style.yaml       brand tokens (logo colours, fonts) the client supplies
  5. edit.yaml `style:` keys        per-video overrides
Every module reads values with `S.get("section.key", default)`. See docs/STYLE.md for the schema."""
import os, copy, yaml

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")

def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out

def _read(p):
    if p and os.path.exists(p):
        with open(p, encoding="utf-8") as f: return yaml.safe_load(f) or {}
    return {}

class Style(dict):
    def get(self, path, default=None):
        cur = self
        for k in path.split("."):
            if not isinstance(cur, dict) or k not in cur: return default
            cur = cur[k]
        return cur

def load(pr=None, preset=None, extra=None):
    d = _read(os.path.join(HERE, "default.yaml")); sources = ["default"]
    E = pr.edit if pr is not None else {}
    st = (E.get("style") or {}) if isinstance(E.get("style"), dict) else {}
    preset = preset or st.get("preset")
    if preset:
        p = os.path.join(HERE, f"{preset}.yaml")
        if not os.path.exists(p): raise SystemExit(f"style preset '{preset}' not found in {HERE}")
        d = _merge(d, _read(p)); sources.append(f"preset:{preset}")
    if pr is not None:
        for name, p in (("inspire", pr.e("style.yaml")), ("brand", pr.p("Brand", "style.yaml"))):
            if os.path.exists(p): d = _merge(d, _read(p)); sources.append(name)
        inline = {k: v for k, v in st.items() if k != "preset"}
        if inline: d = _merge(d, inline); sources.append("edit.yaml")
    if extra: d = _merge(d, extra)
    s = Style(d); s["_sources"] = sources
    return s

def rgb(v):
    if isinstance(v, (list, tuple)): return tuple(int(x) for x in v[:3])
    v = str(v).lstrip("#"); return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
