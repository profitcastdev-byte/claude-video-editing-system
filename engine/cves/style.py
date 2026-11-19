"""The style profile: the ONLY place a look lives. Nothing about a client, brand or look is hard-coded in the engine.

Merge order (later wins):
  1. styles/default.yaml                   neutral, safe defaults (no brand, no house look)
  1b. styles/viral.yaml                    only when edit.yaml `goal: viral` (retention-first defaults; docs/VIRAL.md)
  2. knowledge-base/taste/learned.yaml     repo learned taste: shared publicly through git (`cves learn promote --share`)
     <team_taste>/learned.yaml               team learned taste: a shared folder ($CVES_TEAM_TASTE; `cves learn promote --team`)
  3. ~/.cves/taste/learned.yaml            personal learned taste (`cves learn promote`); may hold client-scoped sections
  4. styles/<preset>.yaml                  optional named preset (edit.yaml: style.preset)
  5. PROJECT/Edit/style.yaml               written by `cves inspire` from the client's reference edits
  5b. PROJECT/Edit/treatment.yaml `style:`  the creative treatment (`cves treatments make` / `pick`, docs/TREATMENTS.md)
  6. PROJECT/Brand/style.yaml              brand tokens (logo colours, fonts) the client supplies
  7. edit.yaml `style:` keys               per-video overrides
The learned layers (2, 3) apply only their sections whose scope matches the project (goal / platform / client from
edit.yaml; docs/LEARNING.md). Every module reads values with `S.get("section.key", default)`. Schema: docs/STYLE.md.
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

# ---- learned taste layers (WS E self-learning, docs/LEARNING.md) ----
SCOPE_RANK = {"global": 0, "platform": 1, "goal": 2, "client": 3}

def learned_paths():
    """[(name, path)] of the learned layers in merge order: the repo's (shared), then the personal one.
    $CVES_KB_DIR moves the repo knowledge base, $CVES_TASTE the personal taste folder (default ~/.cves/taste)."""
    kb = os.environ.get("CVES_KB_DIR") or os.path.join(HERE, "..", "..", "..", "knowledge-base")
    taste = os.environ.get("CVES_TASTE") or os.path.join(os.path.expanduser("~"), ".cves", "taste")
    out = [("repo", os.path.abspath(os.path.join(kb, "taste", "learned.yaml")))]
    team = team_dir()
    if team: out.append(("team", os.path.abspath(os.path.join(team, "learned.yaml"))))
    return out + [("personal", os.path.abspath(os.path.join(taste, "learned.yaml")))]

def team_dir():
    """the team learned layer: a folder every editor's machine points at ($CVES_TEAM_TASTE or `team_taste:` in
    ~/.cves/config.yaml), e.g. a synced Google Drive / Dropbox folder. Empty = no team layer. Client-scoped taste is
    allowed here (it never goes to the public repo)."""
    from . import config as C
    try: d = C.get("team_taste")
    except Exception: d = ""
    return os.path.expanduser(d) if d else ""

def learned_path(name):
    """the learned.yaml of one layer: repo | team | personal (None when that layer is not configured)"""
    return dict(learned_paths()).get(name)

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

NOT_PRESETS = {"default", "platforms"}     # files in styles/ that are not presets
GOALS = ("ad", "viral")

def goal(pr):
    """edit.yaml `goal:` (ad | viral; default ad). Switches the goal layer, the QC profile and the music-slot rules."""
    g = (pr.edit.get("goal") if pr is not None else None) or "ad"
    return str(g).strip().lower()

def load(pr=None, preset=None, extra=None):
    d = _read(os.path.join(HERE, "default.yaml")); sources = ["default"]; layers = []
    E = pr.edit if pr is not None else {}
    ctx = scope_context(E)
    st = (E.get("style") or {}) if isinstance(E.get("style"), dict) else {}
    preset = preset or st.get("preset")
    if pr is not None and goal(pr) == "viral" and preset != "viral":      # the goal layer: under learned taste and any preset
        L = _read(os.path.join(HERE, "viral.yaml")); d = _merge(d, L); layers.append(L); sources.append("goal:viral")
    for name, p in learned_paths():
        layer, _used = learned_layer(p, ctx)
        if layer: d = _merge(d, layer); layers.append(layer); sources.append(f"learned:{name}")
    if preset:
        p = os.path.join(HERE, f"{preset}.yaml")
        if preset in NOT_PRESETS or not os.path.exists(p): raise SystemExit(f"style preset '{preset}' not found in {HERE}")
        L = _read(p); d = _merge(d, L); layers.append(L); sources.append(f"preset:{preset}")
    if pr is not None:
        for name, p in (("inspire", pr.e("style.yaml")), ("treatment", pr.e("treatment.yaml")), ("brand", pr.p("Brand", "style.yaml"))):
            if not os.path.exists(p): continue
            L = _read(p)
            if name == "treatment":          # after inspire, before Brand and edit.yaml: brand rules still win
                name = f"treatment:{L.get('name') or '?'}"; L = L.get("style") if isinstance(L.get("style"), dict) else {}
            d = _merge(d, L); layers.append(L); sources.append(name)
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
