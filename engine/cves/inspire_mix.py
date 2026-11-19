"""Inspire v2 MIX AND MATCH: one source per dimension instead of a blind average of every reference.

Dimensions (which keys each one owns):
  grade      grade.*                         palette    stage.*, colors.*
  captions   captions.*                      motion     transitions.*, framing.*
  pacing     grammar.max_shot_s / cutaway_share / max_cutaway_s, rhythm.cut_* / cuts_per_s / interrupt_*, music.sync
  sound      sound.*, rhythm.tempo_bpm / voice / music_share / sfx_per_10s / dropouts_per_30s / music_energy
  structure  structure.*, grammar.face_on_first_frame

Every reference is measured on its own (one candidate value per key per ref) and all together (the pooled value, the
v0.2 behaviour). Per dimension, the source is chosen by the first rule that applies:
  1. --mix "dim=ref,..."                     forced by the person running inspire
  2. Inspirations/refs.yaml `use: [dim]`     that ref is the authority (best rank first, then weight)
  3. consistency >= AGREE (0.6), or only one ref measured the dimension: pooled across the refs (weight 0 = left out)
  4. the refs disagree: ONE ref, the highest  rank_w x weight x (0.5 + distinctiveness) x confidence, where rank_w = 1/rank
     (unranked refs rank after the ranked ones), distinctiveness = how far its values sit from the neutral defaults
     (a deliberate look beats a near-default one) and confidence = its mean key confidence. Never an average of two
     looks that disagree.
Consistency per key: numbers 1 - (max - min) / max(|median|, 0.5); colours 1 - max pairwise dE / 40; lists element-wise;
labels and booleans: share of refs agreeing with the most common value. A dimension's consistency is the mean of its keys.
When the chosen ref measured nothing in a dimension (an authority ref with no captions), the pooled value is used (said
so in its evidence); when it measured the dimension, keys it did not set stay at the default (its look is kept whole). Forced and authority picks
are written down to confidence 0.2 (the person chose the ref), otherwise `--min-conf` applies as before.

refs.yaml (optional, next to the references):
    refs:
      hook-reel.mp4: {rank: 1, weight: 1.0, kind: viral, use: [pacing, structure], notes: "the energy we want"}
      brand-ad.mov:  {rank: 2, kind: ad, use: [grade, captions]}
A plain mapping without `refs:` works too. Files match by name, relative path or stem."""
import os, collections
import numpy as np, cv2, yaml

DIMS = ["grade", "palette", "captions", "pacing", "sound", "motion", "structure"]
AGREE = 0.6
FORCED_MIN_CONF = 0.2
_EXACT = {"grammar.max_shot_s": "pacing", "grammar.cutaway_share": "pacing", "grammar.max_cutaway_s": "pacing", "music.sync": "pacing",
          "rhythm.cut_on_beat": "pacing", "rhythm.cuts_per_s": "pacing", "rhythm.cut_curve": "pacing", "rhythm.interrupt_max_s": "pacing",
          "rhythm.interrupt_median_s": "pacing", "grammar.face_on_first_frame": "structure"}
_PREFIX = [("grade.", "grade"), ("stage.", "palette"), ("colors.", "palette"), ("captions.", "captions"), ("transitions.", "motion"),
           ("framing.", "motion"), ("sound.", "sound"), ("rhythm.", "sound"), ("structure.", "structure"), ("music.", "sound")]


def dim_of(key):
    if key in _EXACT: return _EXACT[key]
    for p, d in _PREFIX:
        if key.startswith(p): return d
    return "other"


# ---------------------------------------------------------------- refs.yaml + --mix
def load_refs_yaml(d):
    for name in ("refs.yaml", "refs.yml"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f: y = yaml.safe_load(f) or {}
            y = y.get("refs", y) if isinstance(y, dict) else y
            if isinstance(y, list): y = {str(e.get("file")): e for e in y if isinstance(e, dict) and e.get("file")}
            if not isinstance(y, dict): raise SystemExit(f"{p}: expected a mapping of file -> {{rank, weight, kind, use, notes}}")
            for k, v in y.items():
                bad = [u for u in (v or {}).get("use", []) or [] if u not in DIMS]
                if bad: raise SystemExit(f"{p}: {k}: unknown dimension(s) {bad} in use: (one of {', '.join(DIMS)})")
            return {str(k): (v or {}) for k, v in y.items()}, p
    return {}, None


def match_ref(name, labels):
    """name (file, relative path, stem or unique prefix) -> label"""
    nm = name.strip().lower()
    for lab, rel in labels.items():
        if nm in (lab.lower(), rel.lower(), os.path.basename(rel).lower(), os.path.splitext(os.path.basename(rel))[0].lower()): return lab
    hits = [lab for lab, rel in labels.items() if os.path.basename(rel).lower().startswith(nm)]
    return hits[0] if len(hits) == 1 else None


def parse_mix(s, labels):
    out = {}
    for part in [p for p in (s or "").split(",") if p.strip()]:
        if "=" not in part: raise SystemExit(f"--mix: '{part}' is not dim=ref (dimensions: {', '.join(DIMS)})")
        d, r = (x.strip() for x in part.split("=", 1))
        if d not in DIMS: raise SystemExit(f"--mix: unknown dimension '{d}' (one of {', '.join(DIMS)})")
        lab = match_ref(r, labels)
        if not lab: raise SystemExit(f"--mix: no reference matches '{r}' (refs: {', '.join(labels)})")
        out[d] = lab
    return out


# ---------------------------------------------------------------- agreement
def _hexlab(v):
    s = str(v).lstrip("#")[:6]
    try: rgb = [int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError: return None
    return cv2.cvtColor(np.float32(rgb).reshape(1, 1, 3), cv2.COLOR_RGB2Lab).reshape(3)


def _num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)


def distance(a, b):
    """0 = same, 1 = clearly different (same metric as the consistency score)"""
    if _num(a) and _num(b): return float(min(1, abs(a - b) / max(abs((a + b) / 2), .5)))
    if isinstance(a, str) and isinstance(b, str) and a.startswith("#") and b.startswith("#"):
        la, lb = _hexlab(a), _hexlab(b)
        if la is not None and lb is not None: return float(min(1, np.linalg.norm(la - lb) / 40))
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(_num(x) for x in a + b):
        return max([distance(x, y) for x, y in zip(a, b)] or [0.0])
    return 0.0 if a == b else 1.0


def agreement(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2: return None
    if all(_num(v) for v in vals):
        med = float(np.median(vals)); return float(np.clip(1 - (max(vals) - min(vals)) / max(abs(med), .5), 0, 1))
    if all(isinstance(v, str) and v.startswith("#") for v in vals) or all(isinstance(v, list) for v in vals):
        return float(1 - max(distance(a, b) for i, a in enumerate(vals) for b in vals[i + 1:]))
    c = collections.Counter(str(v) for v in vals); return c.most_common(1)[0][1] / len(vals)


# ---------------------------------------------------------------- decide
def decide(per_ref, pooled, meta, defaults, forced=None, min_conf=.5):
    """per_ref: {label: Evidence}; pooled: Evidence; meta: {label: refs.yaml entry}; defaults: Style of default.yaml.
    -> (keys {key: value}, ev {key: how}, conf {key: c}, plan {dim: {...}}, table rows)"""
    from .inspire import Evidence
    forced = forced or {}; labels = list(per_ref)
    ranks = {l: meta.get(l, {}).get("rank") for l in labels}
    worst = max([r for r in ranks.values() if isinstance(r, (int, float))] or [0])
    rank_w = {l: 1 / (ranks[l] if isinstance(ranks[l], (int, float)) and ranks[l] > 0 else worst + 1) for l in labels}
    weight = {l: float(meta.get(l, {}).get("weight", 1.0)) for l in labels}
    all_keys = set(pooled.ev) | {k for e in per_ref.values() for k in e.ev}
    by_dim = collections.defaultdict(list)
    for k in sorted(all_keys): by_dim[dim_of(k)].append(k)
    out = Evidence(); plan = {}
    for dim in DIMS + ["other"]:
        keys = by_dim.get(dim, [])
        if not keys: continue
        cands = {l: {k: per_ref[l].keys[k] for k in keys if k in per_ref[l].keys} for l in labels}
        have = [l for l in labels if cands[l] and weight[l] > 0]
        ag = [a for a in (agreement([cands[l].get(k) for l in have]) for k in keys if k in pooled.keys or any(k in cands[l] for l in have)) if a is not None]
        cons = round(float(np.mean(ag)), 2) if ag else None
        src, rule = None, None
        auth = [l for l in labels if dim in (meta.get(l, {}).get("use") or [])]
        if dim in forced: src, rule = forced[dim], "forced by --mix"
        elif auth:
            src = sorted(auth, key=lambda l: (-rank_w[l], -weight[l]))[0]; rule = f"refs.yaml: {src} is the {dim} authority"
        elif dim == "other" or cons is None or cons >= AGREE or len(have) < 2:
            rule = ("not measured in any ref" if not have else "pooled: " + ("one ref measured it" if len(have) < 2 else f"refs agree (consistency {cons})" if cons is not None else "pooled"))
        else:
            def score(l):
                dist = [distance(cands[l][k], defaults.get(k)) for k in cands[l] if defaults.get(k) is not None]
                conf = np.mean([per_ref[l].conf.get(k, 0) for k in cands[l]]) if cands[l] else 0
                return rank_w[l] * weight[l] * (.5 + (float(np.mean(dist)) if dist else .5)) * float(conf)
            sc = {l: score(l) for l in have}; src = max(sc, key=sc.get)
            top = sorted(sc, key=sc.get, reverse=True)[:3]
            rule = f"refs disagree (consistency {cons}): strongest look x rank -> {src} (scores " + ", ".join(f"{l} {sc[l]:.2f}" for l in top) + (", ..." if len(sc) > 3 else "") + ")"
        plan[dim] = dict(source=src or ("pooled" if have else "-"), rule=rule, consistency=cons, keys=keys)
        for k in keys:
            if src and k in per_ref[src].keys:
                c = per_ref[src].conf[k]
                if rule.startswith(("forced", "refs.yaml")) and c >= FORCED_MIN_CONF: c = max(c, min_conf)
                out.keys[k] = per_ref[src].keys[k]; out.conf[k] = c; out.ev[k] = f"[{src}] {per_ref[src].ev[k]}"
            elif src and cands.get(src):    # the chosen ref measured this dimension and did not set this key: keep its look whole
                if k in per_ref[src].ev: out.ev[k] = f"[{src}] {per_ref[src].ev[k]}"; out.conf[k] = per_ref[src].conf.get(k, 0)
            elif k in pooled.ev:
                out.ev[k] = (f"[pooled; not measured in {src}] " if src else "[pooled] ") + pooled.ev[k]; out.conf[k] = pooled.conf.get(k, 0)
                if k in pooled.keys: out.keys[k] = pooled.keys[k]
    rows = []
    for dim, p in plan.items():
        for k in p["keys"]:
            rows.append(dict(dim=dim, key=k, cands={l: per_ref[l].keys.get(k) for l in labels}, chosen=out.keys.get(k),
                             source=p["source"], conf=round(out.conf.get(k, 0), 2), kept=out.conf.get(k, 0) >= min_conf and k in out.keys))
    return out, plan, rows


def _fmt(v, w=14):
    if v is None: return "-"
    if isinstance(v, float): s = f"{v:g}"
    elif isinstance(v, list): s = "[" + ",".join(f"{x:g}" if isinstance(x, float) else str(x) for x in v) + "]"
    else: s = str(v)
    return s if len(s) <= w else s[:w - 1] + "~"


def table(plan, rows, labels):
    """the --dry-run per-dimension table: candidates per ref, chosen value, source, confidence"""
    lw = max([len(l) for l in labels] + [8]); lw = min(lw, 16)
    out = []
    for dim, p in plan.items():
        cons = "-" if p["consistency"] is None else f"{p['consistency']:.2f}"
        out.append(f"\n{dim.upper()}  consistency {cons}  ->  {p['source']}   ({p['rule']})")
        out.append(f"  {'key':30s} " + " ".join(f"{l[:lw]:>{lw}s}" for l in labels) + f" {'chosen':>14s} {'source':>{lw}s} conf")
        for r in [r for r in rows if r["dim"] == dim]:
            mark = " " if r["kept"] else "x"
            out.append(f"{mark} {r['key']:30s} " + " ".join(f"{_fmt(r['cands'][l], lw):>{lw}s}" for l in labels) +
                       f" {_fmt(r['chosen']):>14s} {(r['source'] if r['source'] != 'pooled' else 'pooled')[:lw]:>{lw}s} {r['conf']:.2f}")
    return "per-dimension mix (x = below confidence, not written):" + "\n".join(out)
