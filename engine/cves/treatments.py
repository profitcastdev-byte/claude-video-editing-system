"""Creative treatments (docs/TREATMENTS.md): 2-3 distinct takes on one edit plan, rendered as fast proxies, compared side by
side, and one of them promoted to the real plan.

  cves treatments list                                     built-in + project treatments, the preferred one first
  cves treatments make [NAMES]                             Edit/treatments/<name>/{edit.yaml, treatment.yaml, plan.json}
  cves treatments render [NAMES] [--full]                  proxies: half size, fast x264, plates + mattes reused
  cves treatments compare [NAMES] [--sequential]           Edit/treatments/compare/{sheet.jpg, compare.mp4, compare.json}
  cves treatments pick NAME                                promote to Edit/edit.yaml (backup kept) + Edit/treatment.yaml, journal it

A treatment is a YAML file: `name`, `label`, `summary`, a `style:` overlay (keys of styles/default.yaml only; it becomes the
treatment layer of the style merge, after inspire and before Brand and edit.yaml, docs/CONTRACTS.md §1) and `structure:`
hints that `make` applies to a copy of the edit plan (pace / cut density, punch-ins, transition family, roto, music bed,
motion piece swaps, B-roll moves). Built-ins live in engine/cves/styles/treatments/; PROJECT/treatments/*.yaml add or
override them by name. The engine never calls a model: Claude looks at the comparison sheet and the user picks."""
import argparse, copy, datetime, json, os, re, shutil, subprocess, sys
import yaml

from . import style as STY, project as PRJ

BUILTIN = os.path.join(STY.HERE, "treatments")
STRUCT = {"pace": ("fast", "medium", "slow"), "punch_ins": ("add", "keep", "gentle"),
          "transitions": ("whip", "glitch", "fade", "cut", "keep"), "roto": ("keep", "drop")}
STRUCT_KEYS = set(STRUCT) | {"max_shot_s", "min_shot_s", "cutaways_per_30s", "music", "motion", "broll_move"}
# per-video caption keys that are content, not look: a treatment never touches them
CAPTION_CONTENT = {"auto", "hide", "fixes", "events", "words"}
NUMBER_WORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "twenty",
                "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion", "percent", "half", "double"}


# ======================================================================== catalogue
def _yaml(p):
    with open(p, encoding="utf-8") as f: return yaml.safe_load(f) or {}

def catalogue(pr=None):
    """{name: path}: built-ins, then PROJECT/treatments/*.yaml (same name = override)"""
    out = {}
    dirs = [BUILTIN] + ([pr.p("treatments")] if pr is not None else [])
    for d in dirs:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if f.endswith((".yaml", ".yml")) and not f.startswith((".", "_")):
                out[os.path.splitext(f)[0]] = os.path.join(d, f)
    return out

def check(T, where):
    """-> list of problems of a treatment definition (style keys must exist in default.yaml; structure values known)"""
    from . import learn
    errs = []
    if not isinstance(T, dict): return [f"{where}: expected a mapping"]
    st = T.get("style") or {}
    if not isinstance(st, dict): errs.append(f"{where}: style: expected a mapping of style keys")
    else:
        for k, v in learn.flatten(st).items():
            if not learn.is_style_key(k) and not _open_key(k): errs.append(f"{where}: style.{k} is not a key of styles/default.yaml")
    S_ = T.get("structure") or {}
    if not isinstance(S_, dict): return errs + [f"{where}: structure: expected a mapping"]
    for k, v in S_.items():
        if k not in STRUCT_KEYS: errs.append(f"{where}: structure.{k} is not a treatment hint ({', '.join(sorted(STRUCT_KEYS))})")
        elif k in STRUCT and v is not None and v not in STRUCT[k]: errs.append(f"{where}: structure.{k}: '{v}' is not one of {', '.join(STRUCT[k])}")
    return errs

def _open_key(k):
    """keys under the open style maps (sound.transition_sfx.<kind>, colors.<name>, ...) are data, not schema"""
    from .schema import OPEN_STYLE
    return any(k.startswith(o + ".") for o in OPEN_STYLE)

def load(pr, name):
    cat = catalogue(pr)
    if name not in cat: raise SystemExit(f"no treatment '{name}': have {', '.join(sorted(cat))} (add PROJECT/treatments/{name}.yaml)")
    T = _yaml(cat[name]); T.setdefault("name", name); T["name"] = name
    errs = check(T, os.path.relpath(cat[name], pr.root) if pr is not None and cat[name].startswith(pr.root) else f"treatments/{name}.yaml")
    if errs: raise SystemExit("bad treatment: " + "; ".join(errs[:6]))
    T["_source"] = "project" if pr is not None and cat[name].startswith(pr.root) else "builtin"
    return T

def ordered(pr, names=None):
    """the names to work on: given, else style treatments.offer (+ the project's own); the preferred one first"""
    S = STY.load(pr); cat = catalogue(pr)
    if names: out = [n.strip() for n in (names.split(",") if isinstance(names, str) else names) if n.strip()]
    else:
        out = [n for n in (S.get("treatments.offer") or []) if n in cat]
        out += [n for n in cat if catalogue_is_project(pr, cat[n]) and n not in out]
    pref = S.get("treatments.prefer")
    if pref in out: out = [pref] + [n for n in out if n != pref]
    for n in out:
        if n not in cat: raise SystemExit(f"no treatment '{n}': have {', '.join(sorted(cat))}")
    return out

def catalogue_is_project(pr, path): return pr is not None and os.path.abspath(path).startswith(os.path.abspath(pr.p("treatments")) + os.sep)

def tdir(pr, name): return pr.e("treatments", name)

def variant(pr, name):
    d = tdir(pr, name)
    if not os.path.exists(os.path.join(d, "edit.yaml")): raise SystemExit(f"no treatment '{name}' made yet: run `cves treatments make {name}`")
    return PRJ.Variant(pr.root, d)


# ======================================================================== timeline facts (no render needed)
def _fps(pr):
    edl = pr.json("edl.json", {}) or {}
    return float(edl.get("fps") or 30.0)

def aroll_segments(pr):
    """[(id, t0, t1)] in cut time, the way render.Timeline lays them out (frame-snapped)"""
    edl = pr.json("edl.json", {}) or {}; F = _fps(pr); out = []; f0 = 0
    for s in edl.get("segments") or []:
        n = round((s["out"] - s["in"]) * F); out.append((s["id"], f0 / F, (f0 + n) / F)); f0 += n
    return out

def duration(pr, E):
    from . import spines as SP
    sp = SP.spine_of(E)
    if SP.has_aroll(sp):
        segs = aroll_segments(pr); return segs[-1][2] if segs else 0.0
    try: return float(SP.duration(pr, sp, E))
    except SystemExit: return max([float(x.get("end", 0)) for x in E.get("broll") or [] if isinstance(x, dict)] or [0.0])

def _num(x): return isinstance(x, (int, float)) and not isinstance(x, bool)


# ======================================================================== plan metrics
def metrics(pr, E=None, S=None):
    """measurable facts of a plan: cut count (picture changes), caption style, transition kinds, punch-ins, graphics,
    music bed. Used by `make` (plan.json), `compare` and the tests."""
    from . import spines as SP
    E = pr.edit if E is None else E; S = STY.load(pr) if S is None else S
    sp = SP.spine_of(E); T = duration(pr, E); F = _fps(pr)
    q = lambda t: round(round(float(t) * F) / F, 3)
    ch = set()
    if SP.has_aroll(sp):
        for _, t0, _ in aroll_segments(pr)[1:]: ch.add(q(t0))
    for x in E.get("broll") or []:
        if isinstance(x, dict): ch.add(q(x["start"])); ch.add(q(x["end"]))
    for c in E.get("cutaways") or []:
        if _num(c.get("start")) and _num(c.get("end")): ch.add(q(c["start"])); ch.add(q(c["end"]))
    sn = (E.get("aroll") or {}).get("snap") if isinstance(E.get("aroll"), dict) else None
    if isinstance(sn, dict) and _num(sn.get("start")): ch.add(q(sn["start"])); ch.add(q(sn["end"]))
    if E.get("end_card"): ch.add(q(T))
    ch = sorted(t for t in ch if 0 < t <= q(T) + 1e-6)
    capcfg = {**(S.get("captions") or {}), **(E.get("captions") or {})}
    kinds = []
    for c in E.get("cutaways") or []:
        kinds += [c.get("in", S.get("transitions.in", "cut")), c.get("out", S.get("transitions.out", "cut"))]
    kinds += [x.get("transition", "cut") for x in E.get("broll") or [] if isinstance(x, dict)]
    kinds += [t.get("kind") for t in E.get("transitions") or [] if isinstance(t, dict)]
    if isinstance(E.get("end_card"), dict): kinds.append(E["end_card"].get("in", S.get("transitions.in", "cut")))
    tr = {}
    for k in kinds:
        if k and k != "cut": tr[k] = tr.get(k, 0) + 1
    punch = (1 if isinstance(sn, dict) else 0) + sum(1 for x in E.get("broll") or [] if _punched(x))
    tpl = [c.get("template") for k in ("cutaways", "chest", "roto") for c in E.get(k) or [] if isinstance(c, dict)]
    mus = E.get("music") if isinstance(E.get("music"), dict) else {}
    return {"spine": sp, "duration_s": round(T, 2), "cuts": len(ch), "cut_times": ch,
            "mean_shot_s": round(T / (len(ch) + 1), 2) if T else None,
            "caption_style": capcfg.get("style"), "caption_position": capcfg.get("position"),
            "transitions": tr, "punch_ins": punch, "zoom_levels": S.get("framing.zoom_levels"), "creep": (E.get("aroll") or {}).get("creep", S.get("framing.creep")),
            "cutaways": len(E.get("cutaways") or []), "roto": len(E.get("roto") or []), "broll_shots": len(E.get("broll") or []),
            "motion_pieces": sorted({t for t in tpl if str(t).startswith("m_")}),
            "bed_lu": mus.get("bed_lu", S.get("sound.bed_lu")), "music_sync": mus.get("sync", S.get("music.sync")),
            "motion_energy": S.get("motion.energy"), "grade": {k: S.get(f"grade.{k}") for k in ("relight", "vignette", "shoulder")}}


# ======================================================================== adapting the plan
def _punched(x):
    """a broll shot framed as a punch-in (the second half of a split): kenburns starting at >= 1.15x"""
    kb = x.get("kenburns") if isinstance(x, dict) else None
    z = kb.get("zoom") if isinstance(kb, dict) else None
    return isinstance(z, (list, tuple)) and len(z) == 2 and _num(z[0]) and z[0] >= 1.15

def _sentence_starts(pr, gap=0.2):
    """cut times where a new sentence or phrase starts (after a full stop or a pause >= gap): where a transition may go"""
    W = [w for w in pr.json("words.json", []) or [] if len(w) >= 3]
    out = [float(W[0][0])] if W else []
    for a, b in zip(W, W[1:]):
        if str(a[2]).rstrip().endswith((".", "!", "?")) or float(b[0]) - float(a[1]) >= gap: out.append(float(b[0]))
    return out

def _near(t, ts, tol): return any(abs(t - x) <= tol for x in ts)

def _strong_word(pr, t0, t1):
    """the word in [t0, t1] to punch in on: a number first, then the longest word"""
    W = [w for w in pr.json("words.json", []) or [] if len(w) >= 3 and t0 <= float(w[0]) <= t1]
    if not W: return None
    def score(w):
        s = re.sub(r"[^\w%$]", "", str(w[2]).lower())
        return (2 if (any(c.isdigit() for c in s) or s in NUMBER_WORDS) else 0, len(s))
    return max(W, key=score)

def _zooms(pr, E, S):
    """{segment id: scale} as render.Timeline._auto_zoom will choose it (cutaways snapped to segment boundaries), plus
    in_cut(t). Kept in step with Timeline._auto_zoom: every direct A-roll cut changes scale by framing.min_step."""
    segs = aroll_segments(pr); F = _fps(pr); bnd = [t0 for _, t0, _ in segs] + ([segs[-1][2]] if segs else [])
    snap = lambda t: min(bnd, key=lambda x: abs(x - t)) if bnd else t
    cuts = [((snap(c["start"]), snap(c["end"])) if c.get("snap", True) else (c["start"], c["end"])) for c in E.get("cutaways") or [] if _num(c.get("start")) and _num(c.get("end"))]
    in_cut = lambda t: any(a <= t < b for a, b in cuts)
    lv = sorted(S.get("framing.zoom_levels") or [1.0, 1.18, 1.38]); step = float(S.get("framing.min_step", 1.15))
    cr = float((E.get("aroll") or {}).get("creep", S.get("framing.creep", 0)) or 0); given = (E.get("aroll") or {}).get("zoom") or {}
    z, prev = {}, None
    for sid, t0, t1 in segs:
        if not any(not in_cut(t0 + k / F) for k in range(0, max(1, round((t1 - t0) * F)), 3)): prev = None; continue
        direct = prev is not None and not in_cut(t0 - .5 / F)
        if sid in given: z[sid] = given[sid]
        else:
            pz = z.get(prev, lv[0]) * (1 + cr) if direct else None
            z[sid] = next((c for c in lv if pz is None or max(c, pz) / min(c, pz) >= step), lv[-1] if (pz or 0) < lv[-1] else lv[0])
        prev = sid
    return z, in_cut, cr, lv, step

def _snap_level(z0, z_next, cr, lv, step):
    """a punch-in level that is a real step up from the shot's own scale (with creep) and still differs from the next
    direct shot's scale by min_step (CUT-05); never extreme (FRAME-09: < 1.4x). None if no level works."""
    for c in sorted(lv, reverse=True):
        if c >= 1.4 or c <= z0: continue
        if c / (z0 * (1 + cr)) >= step and (z_next is None or max(c, z_next) / min(c, z_next) >= step): return c
    return None

def _hook_punch(pr, E, S, notes):
    """punch_ins: add on the aroll spine: a snap punch-in from the strongest word of the first clean A-roll shot (the hook
    unless a cutaway or a chest graphic sits on it) to the end of that shot"""
    if "aroll" in E and not isinstance(E.get("aroll"), dict): return
    ar = E.setdefault("aroll", {})
    if ar.get("snap"): return
    segs = aroll_segments(pr); F = _fps(pr)
    z, in_cut, cr, lv, step = _zooms(pr, E, S)
    chest = {x for c in E.get("chest") or [] for x in ([c.get("segment")] if isinstance(c.get("segment"), str) else c.get("segment") or [])}
    order = [k for k, s_ in enumerate(segs) if s_[0] not in chest] + [k for k, s_ in enumerate(segs) if s_[0] in chest]
    for k in order:                                     # the first shot seen whole; shots under a chest graphic only as a fallback
        sid, t0, t1 = segs[k]
        if sid not in z or any(in_cut(t0 + j / F) for j in range(0, max(1, round((t1 - t0) * F)))): continue
        w = _strong_word(pr, t0 + .8, t1 - .9)
        if not w: continue
        nxt = segs[k + 1][0] if k + 1 < len(segs) else None
        z_next = z.get(nxt) if nxt and not in_cut(t1 + .5 / F) else None
        lvl = _snap_level(z[sid], z_next, cr, lv, step)
        if lvl is None: continue
        ar["snap"] = {"start": round(float(w[0]), 3), "end": round(t1, 3), "zoom": lvl}
        notes.append(f"punch-in x{lvl} on the word '{str(w[2]).strip('.,!?')}' at {float(w[0]):.2f} s (shot {sid})")
        return

def _cut_rank(c):
    p = c.get("params") or {}
    info = 2 if any(k in p for k in ("value", "number", "price", "count", "stat")) or c.get("template") in ("stat", "m_stat_counter", "m_chart_bars") else \
        1 if isinstance(p.get("items"), list) else 0
    return (info, float(c.get("end", 0)) - float(c.get("start", 0)))

def _map_params(src, dst, p):
    """params of a drawn template -> the HTML motion piece that replaces it (None = no known mapping)"""
    p = copy.deepcopy(p or {})
    if src == "stat" and dst == "m_stat_counter":
        out = {k: p[k] for k in ("value", "prefix", "suffix", "decimals") if k in p}
        if "value" not in out: return None
        if p.get("label"): out["caption"] = p["label"]
        cnt = p.get("count")
        if isinstance(cnt, (list, tuple)) and len(cnt) == 2 and _num(cnt[0]): out["at"] = cnt[0]; out["count_s"] = float(cnt[1])
        return out
    if src in ("checklist", "list") and dst == "m_list_build":
        items = p.get("items")
        if not isinstance(items, list) or not items: return None
        mark = p.get("mark", "check"); out = {"items": []}
        for it in items:
            it = dict(it) if isinstance(it, dict) else {"text": str(it)}
            if mark in ("check", "cross"): it.setdefault("state", mark)
            out["items"].append(it)
        if p.get("title"): out["title"] = p["title"]
        if _num(p.get("at")): out["at"] = p["at"]
        return out
    return None

def _swap_motion(E, swap, notes):
    if not swap: return
    from . import templates as TPL
    for k in ("cutaways", "chest"):
        for c in E.get(k) or []:
            dst = swap.get(c.get("template"))
            if not dst or dst not in TPL.REGISTRY: continue
            mp = _map_params(c["template"], dst, c.get("params"))
            if mp is None: continue
            notes.append(f"{c.get('id', c.get('segment'))}: {c['template']} -> {dst}"); c["template"] = dst; c["params"] = mp

def _lbl(x): return str(x.get("id") or f"{x.get('asset') or os.path.basename(str(x.get('src', '?')))}@{float(x['start']):.2f}s")

def _clip_len(pr, ref):
    from . import spines as SP, assets as AS
    p = SP._path(pr, ref)
    if not p or str(p).lower().endswith(SP.STILL_EXT): return None       # a still holds forever
    try: return float(AS.probe(p).get("duration") or 0) or None
    except (SystemExit, OSError, ValueError): return None

def _broll_pace(pr, E, S, st, notes):
    """broll: track pace. max_shot_s splits long video shots (fill or fit) into a wide + punched-in pair (cut on a word);
    min_shot_s merges short shots into longer holds (never past grammar.max_shot_s, never past the clip's end, never the
    opening cut inside the first second, RET-09)."""
    B = [dict(x) for x in E.get("broll") or [] if isinstance(x, dict)]
    if not B: return
    B.sort(key=lambda x: float(x["start"]))
    W = [w for w in pr.json("words.json", []) or [] if len(w) >= 3]
    lo = st.get("min_shot_s"); hi = st.get("max_shot_s"); cap = float(S.get("grammar.max_shot_s") or 4)
    if _num(lo):
        out = []
        for x in B:
            if out:
                p = out[-1]; d = float(p["end"]) - float(p["start"]); nd = float(x["end"]) - float(p["start"])
                L = _clip_len(pr, p.get("asset") or p.get("src")); room = None if L is None else (L - float(p.get("in", 0) or 0)) / float(p.get("speed", 1) or 1)
                opening = float(p["start"]) < .05 and float(p["end"]) <= 1.0           # the first cut stays inside 1 s (RET-09)
                if d < lo and not opening and nd <= cap and abs(float(x["start"]) - float(p["end"])) < .05 and (room is None or room >= nd) and p.get("framing") != "fit":
                    p["end"] = x["end"]; notes.append(f"broll {_lbl(p)}: held to {float(p['end']):.2f} s (absorbs {_lbl(x)})"); continue
            out.append(x)
        B = out
    if _num(hi):
        out = []
        for x in B:
            a, b = float(x["start"]), float(x["end"]); d = b - a
            ref = str(x.get("asset") or x.get("src") or "")
            under = any(_num(c.get("start")) and c["start"] <= a + .05 and c["end"] >= b - .05 for c in E.get("cutaways") or [])
            if d > hi and not under and x.get("framing", "fill") in ("fill", "fit") and not x.get("kenburns") and _clip_len(pr, ref) is not None:
                mids = [float(w[0]) for w in W if a + .7 <= float(w[0]) <= b - .7]
                m = min(mids, key=lambda t: abs(t - (a + b) / 2)) if mids else (a + b) / 2
                if not mids and d < 1.4: out.append(x); continue
                one = dict(x, end=round(m, 3)); two = dict(x, start=round(m, 3), transition="cut", kenburns={"zoom": [1.22, 1.26]},
                                                           **{"in": round(float(x.get("in", 0) or 0) + (m - a) * float(x.get("speed", 1) or 1), 3)})
                if x.get("id"): two["id"] = f"{x['id']}p"
                out += [one, two]; notes.append(f"broll {_lbl(x)}: split at {m:.2f} s into a wide + punch-in"); continue
            out.append(x)
        B = out
    mv = st.get("broll_move")
    if isinstance(mv, list) and len(mv) == 2:
        n = 0
        for x in B:
            ref = str(x.get("asset") or x.get("src") or "")
            if x.get("framing", "fill") == "fill" and not x.get("kenburns") and _clip_len(pr, ref) is not None: x["kenburns"] = {"zoom": list(mv)}; n += 1
        if n: notes.append(f"broll: slow push {mv[0]}->{mv[1]} on {n} shot(s)")
    E["broll"] = B

def _family(E, pr, fam, notes):
    """the transition family: cutaway in/out, broll shot entries at sentence starts, explicit transitions, the end card"""
    if fam in (None, "keep"): return
    n = 0; nb = 0; where = []
    for c in E.get("cutaways") or []: c["in"] = fam; c["out"] = fam; n += 1
    if n: where.append(f"{n} cutaway(s) in + out")
    starts = _sentence_starts(pr)
    for x in E.get("broll") or []:
        if not isinstance(x, dict): continue
        t = float(x["start"])
        x["transition"] = fam if fam != "cut" and t > .05 and _near(t, starts, .35) and not _punched(x) else "cut"
        nb += x["transition"] != "cut"
    if nb: where.append(f"{nb} broll shot(s) at sentence starts")
    if fam == "cut": E.pop("transitions", None)
    elif E.get("transitions"): E["transitions"] = [dict(t, kind=fam) for t in E["transitions"] if isinstance(t, dict)]; where.append("explicit transitions")
    if isinstance(E.get("end_card"), dict): E["end_card"]["in"] = fam; where.append("end card")
    notes.append(f"transitions: {fam}" + (f" ({', '.join(where)})" if where else ""))

def adapt(pr, E, T, S):
    """a copy of the base plan E adapted to treatment T (S = the style with the treatment layer). -> (E, notes)"""
    from . import spines as SP
    E = copy.deepcopy(E); st = T.get("structure") or {}; ts = T.get("style") or {}; notes = []
    E["treatment"] = T["name"]
    # captions: the treatment's caption preset replaces the per-video look keys (content keys stay)
    capst = ts.get("captions") or {}
    if isinstance(E.get("captions"), dict) and capst:
        gone = [k for k in list(E["captions"]) if k in capst and k not in CAPTION_CONTENT]
        for k in gone: E["captions"].pop(k)
        if gone: notes.append(f"captions: per-video {', '.join(gone)} -> the treatment's preset")
    if capst.get("style"): notes.append(f"captions: {capst['style']}")
    # framing creep set per video gives way to the treatment's
    if isinstance(E.get("aroll"), dict) and "creep" in E["aroll"] and _num((ts.get("framing") or {}).get("creep")):
        E["aroll"]["creep"] = ts["framing"]["creep"]
    # cut density: graphics cap, roto, B-roll pace
    cap = st.get("cutaways_per_30s")
    if _num(cap) and E.get("cutaways"):
        keep = max(1, int(round(cap * max(duration(pr, E), 1) / 30)))
        cuts = E["cutaways"]
        if len(cuts) > keep:
            best = set(id(c) for c in sorted(cuts, key=_cut_rank, reverse=True)[:keep])
            drop = [c.get("id") for c in cuts if id(c) not in best]
            E["cutaways"] = [c for c in cuts if id(c) in best]; notes.append(f"cutaways: kept {keep}, dropped {', '.join(map(str, drop))}")
    if st.get("roto") == "drop" and E.get("roto"): notes.append(f"roto: dropped {len(E['roto'])}"); E["roto"] = []
    if E.get("broll"): _broll_pace(pr, E, S, st, notes)
    # punch-ins
    pi = st.get("punch_ins")
    if SP.has_aroll(SP.spine_of(E)):
        if pi == "add": _hook_punch(pr, E, S, notes)
        elif pi == "gentle" and isinstance(E.get("aroll"), dict) and E["aroll"].pop("snap", None): notes.append("punch-in snap removed")
    _family(E, pr, st.get("transitions"), notes)
    _swap_motion(E, (st.get("motion") or {}).get("swap") or {}, notes)
    mus = E.get("music") if isinstance(E.get("music"), dict) else None
    off = (st.get("music") or {}).get("bed_lu_offset")
    if mus is not None and _num(mus.get("bed_lu")) and _num(off):
        mus["bed_lu"] = round(mus["bed_lu"] + off, 2); notes.append(f"music bed {mus['bed_lu']} LU")
    return E, notes


# ======================================================================== commands
def _journal(pr, event, **kw):
    from . import learn
    try: learn.append(pr, event, **kw)
    except BaseException as e: sys.stderr.write(f"cves treatments: journal skipped ({e})\n")

def make(pr, names=None):
    base = pr.edit
    if not any(base.get(k) for k in ("cutaways", "broll", "end_card", "roto", "chest")):
        raise SystemExit("no edit plan yet: fill Edit/edit.yaml (`cves plan`) before making treatments")
    base = {k: v for k, v in base.items() if k != "treatment"}
    out = []
    for name in ordered(pr, names):
        T = load(pr, name); d = tdir(pr, name); os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "treatment.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump({k: v for k, v in T.items() if not k.startswith("_")}, f, sort_keys=False, allow_unicode=True, width=140)
        v = PRJ.Variant(pr.root, d); v.save_edit(dict(base, treatment=name))       # provisional: S with the treatment layer
        if os.path.exists(pr.e("beats.json")) and not os.path.exists(v.e("beats.json")): shutil.copy2(pr.e("beats.json"), v.e("beats.json"))   # seed: no re-analysis
        S = STY.load(v)
        E, notes = adapt(pr, base, T, S); v.save_edit(E)
        for f in ("proxy.mp4", "full.mp4"):                                     # renders of an older plan are stale now
            if os.path.exists(os.path.join(d, f)): os.remove(os.path.join(d, f))
        m = metrics(v, E, STY.load(v))
        with open(os.path.join(d, "plan.json"), "w", encoding="utf-8") as f:
            json.dump({"treatment": name, "label": T.get("label", name), "summary": T.get("summary", ""), "source": T["_source"], "changes": notes, "metrics": m}, f, indent=1)
        out.append({"name": name, "label": T.get("label", name), "dir": d, "changes": notes, "metrics": m})
    _journal(pr, "treatments-make", treatments=[o["name"] for o in out], metrics={o["name"]: _short(o["metrics"]) for o in out})
    return out

def _short(m):
    return {k: m.get(k) for k in ("cuts", "mean_shot_s", "caption_style", "transitions", "punch_ins", "cutaways", "roto", "motion_pieces", "bed_lu", "motion_energy")}

def made(pr, names=None):
    """names of treatments made in Edit/treatments/ (in offer order), or the given ones"""
    if names: return ordered(pr, names)
    root = pr.e("treatments"); have = [n for n in sorted(os.listdir(root)) if os.path.exists(os.path.join(root, n, "edit.yaml"))] if os.path.isdir(root) else []
    if not have: raise SystemExit("no treatments made yet: run `cves treatments make`")
    try: order = ordered(pr)
    except SystemExit: order = []
    return [n for n in order if n in have] + [n for n in have if n not in order]

def render(pr, names=None, full=False, workers=None):
    """proxy (default) or full renders of each treatment -> Edit/treatments/<name>/proxy.mp4 (or full.mp4)"""
    from . import render as R, mix as MX, encode as EN, schema
    k = 1.0 if full else float(STY.load(pr).get("treatments.proxy_scale", .5) or .5)
    out = []
    for name in made(pr, names):
        v = variant(pr, name); schema.require_valid(v)
        shutil.rmtree(v.e("frames"), ignore_errors=True)            # stale frames of another size would end up in the encode
        R.render(v, workers=workers, proxy=None if full else k); MX.mix(v)
        f = EN.encode(v, out=os.path.join(v.work, "full.mp4" if full else "proxy.mp4"), proxy=not full)
        shutil.rmtree(v.e("frames"), ignore_errors=True)            # proxies keep only the mp4 (frames are cheap to remake)
        out.append((name, f)); print(f"{name}: {f}")
    _journal(pr, "treatments-render", treatments=[n for n, _ in out], proxy=not full)
    return out

def _probe_size(path):
    r = subprocess.run([_ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout); s = j["streams"][0]
    return int(s["width"]), int(s["height"]), float(j["format"]["duration"])

def _ffprobe():
    from . import config as C
    try: return C.get("ffprobe")
    except (KeyError, SystemExit):
        ff = C.get("ffmpeg"); d, b = os.path.split(ff)
        return os.path.join(d, b.replace("ffmpeg", "ffprobe")) if d else "ffprobe"

def _font(size, bold=True):
    from PIL import ImageFont
    from . import gfx as G
    for f in ("Poppins-SemiBold.ttf" if bold else "Poppins-Medium.ttf", "Poppins-Medium.ttf"):
        p = os.path.join(G.ROOT, "assets", "fonts", f)
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def _label_png(path, w, h, title, sub):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (w, h), (0, 0, 0, 170)); d = ImageDraw.Draw(im)
    fs = max(12, int(h * .42)); d.text((int(h * .35), int(h * .1)), title, font=_font(fs), fill=(255, 255, 255, 255))
    if sub: d.text((int(h * .35), int(h * .1) + fs + 2), sub, font=_font(max(9, int(fs * .55)), False), fill=(210, 210, 215, 255))
    im.save(path)

def _desc(m):
    tr = "/".join(sorted(m.get("transitions") or {})) or "cuts"
    return f"{m.get('cuts')} cuts · {m.get('caption_style')} captions · {tr}"

def timecodes(cut_lists, D, k):
    """k timecodes that are settled in EVERY treatment: the middles of the k longest stretches between any treatment's
    picture changes (so no column lands on a transition or a graphic still entering), in time order; even spacing fills up"""
    b = sorted({0.0, float(D)} | {float(t) for L in cut_lists for t in L if 0 < float(t) < D})
    gaps = sorted(((y - x, (x + y) / 2) for x, y in zip(b, b[1:]) if y - x > .3), reverse=True)[:k]
    ts = sorted(round(m, 2) for _, m in gaps)
    j = 0
    while len(ts) < k and j < 4 * k:                                         # few changes: add evenly spaced points
        t = round(D * (j + .5) / k, 2); j += 1
        if all(abs(t - x) > .5 for x in ts): ts.append(t)
    return sorted(ts)[:k]

def compare(pr, names=None, sequential=False):
    """same timecodes across treatments -> Edit/treatments/compare/sheet.jpg (+ compare.json) and compare.mp4"""
    from PIL import Image, ImageDraw
    from . import config as C
    S = STY.load(pr); names = made(pr, names)
    vids = []
    for n in names:
        f = os.path.join(tdir(pr, n), "proxy.mp4")
        if not os.path.exists(f): f = os.path.join(tdir(pr, n), "full.mp4")
        if not os.path.exists(f): raise SystemExit(f"treatment '{n}' has no render: run `cves treatments render {n}`")
        pj = os.path.join(tdir(pr, n), "plan.json"); P = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {}
        w, h, dur = _probe_size(f); vids.append({"name": n, "label": P.get("label", n), "file": f, "w": w, "h": h, "dur": dur, "metrics": P.get("metrics") or {}})
    od = pr.e("treatments", "compare"); os.makedirs(od, exist_ok=True)
    D = min(v["dur"] for v in vids); k = int(S.get("treatments.compare_points", 6) or 6)
    ts = timecodes([v["metrics"].get("cut_times") or [] for v in vids], D, k)
    # ---- sheet: rows = treatments, columns = timecodes
    portrait = vids[0]["h"] >= vids[0]["w"]
    th = int(S.get("treatments.compare_thumb", 360) or 360)                  # thumbnail height (portrait) or width (landscape)
    tw, tht = (int(round(th * vids[0]["w"] / vids[0]["h"])), th) if portrait else (th, int(round(th * vids[0]["h"] / vids[0]["w"])))
    pad, lw, hh = 12, 300, 44
    sheet = Image.new("RGB", (lw + k * (tw + pad) + pad, hh + len(vids) * (tht + pad) + pad), (18, 18, 22)); dr = ImageDraw.Draw(sheet)
    for j, t in enumerate(ts): dr.text((lw + pad + j * (tw + pad), 12), f"{int(t // 60)}:{t % 60:05.2f}", font=_font(20), fill=(230, 230, 235))
    tmp = os.path.join(od, "_frames"); os.makedirs(tmp, exist_ok=True)
    for i, v in enumerate(vids):
        y = hh + i * (tht + pad)
        dr.text((pad, y + 6), v["label"], font=_font(30), fill=(255, 255, 255))
        m = v["metrics"]; lines = [f"{m.get('cuts', '?')} cuts, shot {m.get('mean_shot_s', '?')} s", f"captions: {m.get('caption_style')}",
                                   "transitions: " + (", ".join(f"{a} x{b}" for a, b in sorted((m.get('transitions') or {}).items())) or "cuts"),
                                   f"punch-ins {m.get('punch_ins', 0)}, graphics {m.get('cutaways', 0)}", f"bed {m.get('bed_lu')} LU, energy {m.get('motion_energy')}"]
        for li, s in enumerate(lines): dr.text((pad, y + 48 + li * 24), s, font=_font(17, False), fill=(190, 190, 200))
        for j, t in enumerate(ts):
            fp = os.path.join(tmp, f"{v['name']}_{j}.png")
            subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", v["file"], "-frames:v", "1", fp], check=True)
            with Image.open(fp) as im: sheet.paste(im.convert("RGB").resize((tw, tht), Image.LANCZOS), (lw + pad + j * (tw + pad), y))
    shutil.rmtree(tmp, ignore_errors=True)
    sp = os.path.join(od, "sheet.jpg"); sheet.save(sp, quality=90)
    # ---- comparison mp4: stacked (one picture per treatment, audio of the first) or sequential (each with its own sound)
    mx = float(S.get("treatments.compare_max_s", 12) or 12); layout = "sequential" if sequential else str(S.get("treatments.compare_layout", "stacked"))
    mp = os.path.join(od, "compare.mp4"); _compare_mp4(vids, mp, mx, layout, portrait, od, S)
    rec = {"treatments": [{k: v[k] for k in ("name", "label", "file", "metrics")} for v in vids], "timecodes": ts, "sheet": sp, "video": mp, "layout": layout}
    with open(os.path.join(od, "compare.json"), "w", encoding="utf-8") as f: json.dump(rec, f, indent=1)
    _journal(pr, "treatments-compare", treatments=names, timecodes=ts)
    return rec

def _compare_mp4(vids, out, mx, layout, portrait, od, S):
    from . import config as C, encode as EN
    w0, h0 = vids[0]["w"], vids[0]["h"]
    # every picture at the first proxy's size (even), a label strip on top
    lh = max(28, int(min(w0, h0) * .07)) // 2 * 2
    args = [C.get("ffmpeg"), "-v", "error", "-y"]; fc = []
    for i, v in enumerate(vids):
        lp = os.path.join(od, f"_label_{i}.png"); _label_png(lp, w0, lh, v["label"], _desc(v["metrics"]) + (" · audio" if layout != "sequential" and i == 0 else ""))
        args += ["-t", f"{min(mx, v['dur']):.3f}", "-i", v["file"]]
    for i in range(len(vids)): args += ["-i", os.path.join(od, f"_label_{i}.png")]
    n = len(vids)
    for i in range(n):
        fc.append(f"[{i}:v]scale={w0}:{h0},setsar=1,fps=30[s{i}];[s{i}][{n + i}:v]overlay=0:0[v{i}]")
    if layout == "sequential":
        fc.append("".join(f"[v{i}][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
        amap = "[a]"
    else:
        fc.append("".join(f"[v{i}]" for i in range(n)) + (f"hstack=inputs={n}" if portrait else f"vstack=inputs={n}") + "[v]")
        amap = "0:a"
    va = EN.proxy_video_args(S); j = va.index("-vf"); va = va[:j] + va[j + 2:]          # the complex graph ends in yuv420p itself
    fc[-1] = fc[-1].replace("[v]", ",format=yuv420p[v]") if layout != "sequential" else fc[-1]
    if layout == "sequential": fc.append("[v]format=yuv420p[vo]")
    args += ["-filter_complex", ";".join(fc), "-map", "[vo]" if layout == "sequential" else "[v]", "-map", amap] + va + EN.audio_args(S) + [out]
    subprocess.run(args, check=True)
    for i in range(n):
        try: os.remove(os.path.join(od, f"_label_{i}.png"))
        except OSError: pass

def pick(pr, name):
    """promote a treatment: its edit.yaml -> Edit/edit.yaml (old one backed up), treatment.yaml -> Edit/treatment.yaml
    (the treatment layer of the style merge), and journal the choice for `cves learn mine`"""
    d = tdir(pr, name)
    for f in ("edit.yaml", "treatment.yaml"):
        if not os.path.exists(os.path.join(d, f)): raise SystemExit(f"no treatment '{name}' made yet: run `cves treatments make {name}`")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); baks = []
    for f in ("edit.yaml", "treatment.yaml"):
        src = pr.e(f)
        if os.path.exists(src): b = pr.e(f"{f}.bak-{stamp}"); shutil.copy2(src, b); baks.append(b)
    E0 = pr.edit
    shutil.copy2(os.path.join(d, "edit.yaml"), pr.e("edit.yaml")); shutil.copy2(os.path.join(d, "treatment.yaml"), pr.e("treatment.yaml"))
    P = {}
    pj = os.path.join(d, "plan.json")
    if os.path.exists(pj):
        with open(pj, encoding="utf-8") as f: P = json.load(f)
    offered = [n for n in sorted(os.listdir(pr.e("treatments"))) if os.path.exists(os.path.join(pr.e("treatments"), n, "edit.yaml"))]
    ctx = STY.scope_context(pr.edit)
    from . import learn
    learn.on_treatment_pick(pr, name, offered=offered, goal=ctx["goal"], client=ctx["client"], platform=ctx["platform"],
                            metrics=_short(P.get("metrics") or {}), changes=learn.diff(E0, pr.edit)[:60])
    return {"name": name, "backups": baks, "edit": pr.e("edit.yaml"), "layer": pr.e("treatment.yaml")}


# ======================================================================== CLI
def _table(rows):
    for r in rows:
        m = r["metrics"]
        print(f"  {r['name']:11s} {m['cuts']:3d} cuts  shot {m['mean_shot_s']} s  captions {m['caption_style']:<11s} "
              f"transitions {('/'.join(sorted(m['transitions'])) or 'cut'):<6s} punch-ins {m['punch_ins']}  graphics {m['cutaways']}  bed {m['bed_lu']} LU")

def main(argv, project=None):
    ap = argparse.ArgumentParser(prog="cves treatments", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="sub", required=True)
    sp.add_parser("list")
    mk = sp.add_parser("make"); mk.add_argument("names", nargs="?", help="comma list (default: style treatments.offer + the project's own)")
    rd = sp.add_parser("render"); rd.add_argument("names", nargs="?"); rd.add_argument("--proxy", action="store_true", help="the default: half size, fast encode")
    rd.add_argument("--full", action="store_true", help="full size and delivery encode settings instead of a proxy"); rd.add_argument("--workers", type=int)
    cp = sp.add_parser("compare"); cp.add_argument("names", nargs="?"); cp.add_argument("--sequential", action="store_true", help="one after another, each with its own sound")
    pk = sp.add_parser("pick"); pk.add_argument("name")
    a = ap.parse_args(argv)
    pr = PRJ.Project(project or os.getcwd())
    if a.sub == "list":
        S = STY.load(pr); pref = S.get("treatments.prefer"); cat = catalogue(pr)
        for n in ordered(pr) + [n for n in cat if n not in ordered(pr)]:
            T = load(pr, n)
            mark = " (preferred)" if n == pref else ""
            made_ = " [made]" if os.path.exists(os.path.join(tdir(pr, n), "edit.yaml")) else ""
            print(f"{n:11s} {T['_source']:8s}{made_}{mark}  {T.get('summary', '')}")
        return 0
    if a.sub == "make":
        rows = make(pr, a.names)
        for r in rows:
            print(f"{r['name']}: {r['dir']}")
            for c in r["changes"]: print(f"    {c}")
        _table(rows); print("next: `cves treatments render` (proxies), then `cves treatments compare`")
        return 0
    if a.sub == "render":
        render(pr, a.names, full=a.full, workers=a.workers); print("next: `cves treatments compare`"); return 0
    if a.sub == "compare":
        r = compare(pr, a.names, a.sequential)
        print(f"sheet -> {r['sheet']}\nvideo -> {r['video']} ({r['layout']})\npick one: `cves treatments pick <name>`"); return 0
    if a.sub == "pick":
        r = pick(pr, a.name)
        print(f"picked {r['name']}: {r['edit']} (treatment layer {r['layer']})")
        for b in r["backups"]: print(f"  backup {b}")
        print("next: `cves build` (the full render of the picked plan)"); return 0
    return 1
