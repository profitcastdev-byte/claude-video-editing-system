"""The style profile: the ONLY place a look lives. Nothing about a client, brand or look is hard-coded in the engine.

Merge order (later wins):
  1. styles/default.yaml                   neutral, safe defaults (no brand, no house look)
  2. knowledge-base/taste/learned.yaml     repo learned taste: team-shared through git (`cves learn promote --share`)
  3. ~/.cves/taste/learned.yaml            personal learned taste (`cves learn promote`); may hold client-scoped sections
  4. styles/<preset>.yaml                  optional named preset (edit.yaml: style.preset)
  5. PROJECT/Edit/style.yaml               written by `cves inspire` from the client's reference edits
  6. PROJECT/Brand/style.yaml              brand tokens (logo colours, fonts) the client supplies
  7. edit.yaml `style:` keys               per-video overrides
The learned layers (2, 3) apply only their sections whose scope matches the project (goal / platform / client from
edit.yaml; docs/LEARNING.md). Every module reads values with `S.get("section.key", default)`. Schema: docs/STYLE.md."""
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

# ---- learned taste layers (WS E self-learning, docs/LEARNING.md) ----
SCOPE_RANK = {"global": 0, "platform": 1, "goal": 2, "client": 3}

def learned_paths():
    """[(name, path)] of the learned layers in merge order: the repo's (shared), then the personal one.
    $CVES_KB_DIR moves the repo knowledge base, $CVES_TASTE the personal taste folder (default ~/.cves/taste)."""
    kb = os.environ.get("CVES_KB_DIR") or os.path.join(HERE, "..", "..", "..", "knowledge-base")
    taste = os.environ.get("CVES_TASTE") or os.path.join(os.path.expanduser("~"), ".cves", "taste")
    return [("repo", os.path.abspath(os.path.join(kb, "taste", "learned.yaml"))),
            ("personal", os.path.abspath(os.path.join(taste, "learned.yaml")))]

def scope_context(E):
    """goal / platform / client of an edit.yaml; every one is optional (absent = only unscoped sections match it)"""
    E = E or {}
    plat = E.get("platform"); plat = plat.get("target") if isinstance(plat, dict) else plat
    proj = E.get("project") if isinstance(E.get("project"), dict) else {}
    return {"goal": E.get("goal"), "platform": plat, "client": proj.get("client")}

def scope_parts(scope):
    """'goal:viral+platform:tiktok' -> [('goal', 'viral'), ('platform', 'tiktok')]; 'global' -> [('global', '')]"""
    out = []
    for part in str(scope or "global").split("+"):
        k, _, v = part.strip().partition(":")
        if k not in SCOPE_RANK or (k != "global" and not v.strip()):
            raise ValueError(f"bad scope '{scope}': use global | goal:<ad|viral> | platform:<name> | client:<name> (join with +)")
        out.append((k, v.strip()))
    return out

def scope_matches(scope, ctx):
    try: parts = scope_parts(scope)
    except ValueError: return False
    for k, v in parts:
        if k == "global": continue
        have = (ctx or {}).get(k)
        if have is None or str(have).strip().casefold() != v.casefold(): return False
    return True

def _specificity(scope):
    parts = scope_parts(scope)
    return (sum(k != "global" for k, _ in parts), max(SCOPE_RANK[k] for k, _ in parts), scope)

def learned_layer(path, ctx):
    """merged style of the sections of a learned.yaml whose scope matches ctx (general first, most specific last) + their scopes"""
    data = _read(path); scopes = data.get("scopes") if isinstance(data.get("scopes"), dict) else {}
    out, used = {}, []
    for sc in sorted((s for s in scopes if scope_matches(s, ctx)), key=_specificity):
        if isinstance(scopes[sc], dict) and scopes[sc]: out = _merge(out, scopes[sc]); used.append(sc)
    return out, used

def load(pr=None, preset=None, extra=None):
    d = _read(os.path.join(HERE, "default.yaml")); sources = ["default"]
    E = pr.edit if pr is not None else {}
    ctx = scope_context(E)
    for name, p in learned_paths():
        layer, _used = learned_layer(p, ctx)
        if layer: d = _merge(d, layer); sources.append(f"learned:{name}")
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
