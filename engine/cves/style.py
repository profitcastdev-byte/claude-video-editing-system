"""The style profile: the ONLY place a look lives. Nothing about a client, brand or look is hard-coded in the engine.

Merge order (later wins):
  1. styles/default.yaml            neutral, safe defaults (no brand, no house look)
  1b. styles/viral.yaml             only when edit.yaml `goal: viral` (retention-first defaults; docs/VIRAL.md)
  2. styles/<preset>.yaml           optional named preset (edit.yaml: style.preset)
  3. PROJECT/Edit/style.yaml        written by `cves inspire` from the client's reference edits
  4. PROJECT/Brand/style.yaml       brand tokens (logo colours, fonts) the client supplies
  5. edit.yaml `style:` keys        per-video overrides
Every module reads values with `S.get("section.key", default)`. See docs/STYLE.md for the schema.
After the merge, `platform.target` (styles/platforms.yaml) fills platform.safe_zone / sound.master_lufs / sound.true_peak
unless a layer above default.yaml set them (cves.platforms.apply)."""
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

NOT_PRESETS = {"default", "platforms"}     # files in styles/ that are not presets
GOALS = ("ad", "viral")

def goal(pr):
    """edit.yaml `goal:` (ad | viral; default ad). Switches the goal layer, the QC profile and the music-slot rules."""
    g = (pr.edit.get("goal") if pr is not None else None) or "ad"
    return str(g).strip().lower()

def load(pr=None, preset=None, extra=None):
    d = _read(os.path.join(HERE, "default.yaml")); sources = ["default"]; layers = []
    E = pr.edit if pr is not None else {}
    st = (E.get("style") or {}) if isinstance(E.get("style"), dict) else {}
    preset = preset or st.get("preset")
    if pr is not None and goal(pr) == "viral" and preset != "viral":      # the goal layer sits under any named preset
        L = _read(os.path.join(HERE, "viral.yaml")); d = _merge(d, L); layers.append(L); sources.append("goal:viral")
    if preset:
        p = os.path.join(HERE, f"{preset}.yaml")
        if preset in NOT_PRESETS or not os.path.exists(p): raise SystemExit(f"style preset '{preset}' not found in {HERE}")
        L = _read(p); d = _merge(d, L); layers.append(L); sources.append(f"preset:{preset}")
    if pr is not None:
        for name, p in (("inspire", pr.e("style.yaml")), ("brand", pr.p("Brand", "style.yaml"))):
            if os.path.exists(p): L = _read(p); d = _merge(d, L); layers.append(L); sources.append(name)
        inline = {k: v for k, v in st.items() if k != "preset"}
        if inline: d = _merge(d, inline); layers.append(inline); sources.append("edit.yaml")
    if extra: d = _merge(d, extra); layers.append(extra)
    from . import platforms
    d = platforms.apply(d, layers)
    s = Style(d); s["_sources"] = sources
    return s

def rgb(v):
    if isinstance(v, (list, tuple)): return tuple(int(x) for x in v[:3])
    v = str(v).lstrip("#"); return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
