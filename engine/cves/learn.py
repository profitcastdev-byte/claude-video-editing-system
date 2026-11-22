"""Self-learning (docs/LEARNING.md): journal -> mined candidate patterns -> human-approved promotion into a learned style layer.

  cves learn note "text" [--version vNNN]                 the user's words, verbatim
  cves learn rate vNNN 1-10 [--why ".."] [--by owner|client|claude] [--scores hook=7,story=6,..]
  cves learn approve|reject vNNN [--why ".."] [--by ..]   the version was approved / rejected
  cves learn results vNNN [--platform meta] [--hook-rate 0.31 --hold 0.18 ..] [key=value ..]
  cves learn journal [--tail 20]                          print this project's journal
  cves learn mine [--root DIR] [--json]                   every project journal -> ~/.cves/taste/candidates.jsonl
  cves learn list [--all] | show ID
  cves learn promote ID [--scope ..] [--share|--team]     personal learned.yaml; --team: the shared team folder; --share: the public repo (anonymised)
  cves learn reject ID --why ".."                         never propose it again
  cves learn forget ID                                    revert a promotion
  cves learn study FOLDER [--max-s 60]                    measure great videos (notes.txt: file | ad|viral | why)

Automatic events (build, deliver, import-edits) are written by `cves` itself into PROJECT/Edit/journal.jsonl. Journaling
never breaks a command: every hook catches its own errors. Nothing learned changes the look until a person promotes it."""
import argparse, copy, datetime, glob, hashlib, json, math, os, re, statistics, sys
import yaml

from . import style as STY
from . import __version__

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VERSION_RX = re.compile(r"^(v\d{2,}|master)$")
MIN_N = 3                       # outcome correlations and study patterns need at least this many samples
MISSING = object()
SKIP_WALK = {"Raw", "Export", "Assets", "Music", "Inspirations", "Moodboard", "Brand", "frames", "plate", "matte", "stems", "node_modules"}
IGNORE_EDIT = ("project.", "qc.", "captions.events", "captions.hide", "captions.fixes", "edl", "assets", "variants", "delivery.cover")


# ======================================================================== paths
def taste_dir():
    return os.path.dirname(STY.learned_path("personal"))

def kb_dir():
    return os.path.dirname(os.path.dirname(STY.learned_path("repo")))

def _tp(*p):
    d = taste_dir(); os.makedirs(d, exist_ok=True); return os.path.join(d, *p)

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
def _today(): return datetime.date.today().isoformat()

def _read_jsonl(p):
    out = []
    if p and os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln: continue
                try: out.append(json.loads(ln))
                except json.JSONDecodeError: pass
    return out

def _append_jsonl(p, rec):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f: f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

def _write_jsonl(p, recs):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


# ======================================================================== style keys
_DEFAULT = None
def default_style():
    global _DEFAULT
    if _DEFAULT is None:
        with open(os.path.join(STY.HERE, "default.yaml"), encoding="utf-8") as f: _DEFAULT = yaml.safe_load(f) or {}
    return _DEFAULT

def style_value(key, d=None):
    cur = default_style() if d is None else d
    for k in key.split("."):
        if not isinstance(cur, dict) or k not in cur: return MISSING
        cur = cur[k]
    return cur

def is_style_key(key):
    """only keys that exist in default.yaml can be learned (leaves or whole lists; not whole sections)"""
    v = style_value(key)
    return v is not MISSING and key != "name" and not (isinstance(v, dict) and v)

def _dset(d, key, v):
    ks = key.split("."); cur = d
    for k in ks[:-1]:
        if not isinstance(cur.get(k), dict): cur[k] = {}
        cur = cur[k]
    cur[ks[-1]] = v

def _ddel(d, key):
    ks = key.split("."); stack = [d]; cur = d
    for k in ks[:-1]:
        if not isinstance(cur.get(k), dict): return
        cur = cur[k]; stack.append(cur)
    cur.pop(ks[-1], None)
    for i in range(len(ks) - 1, 0, -1):      # drop sections left empty
        if not stack[i]: stack[i - 1].pop(ks[i - 1], None)


# ======================================================================== journal (per project)
def journal_path(pr): return pr.e("journal.jsonl")

def _style_hash(S):
    return hashlib.sha1(json.dumps({k: v for k, v in S.items() if k != "_sources"}, sort_keys=True, default=str).encode()).hexdigest()[:12]

def append(pr, event, **data):
    rec = {"t": _now(), "event": event, "cves": __version__}
    try: rec["style_hash"] = _style_hash(STY.load(pr))
    except BaseException: pass
    rec.update({k: v for k, v in data.items() if v is not None})
    _append_jsonl(journal_path(pr), rec)
    return rec

def read_journal(pr_or_path):
    return _read_jsonl(pr_or_path if isinstance(pr_or_path, str) else journal_path(pr_or_path))

def _safe(fn):
    """journaling must never break a command"""
    def run(*a, **k):
        try: return fn(*a, **k)
        except BaseException as e:      # noqa: BLE001  (SystemExit included: a hook never ends the command)
            try: sys.stderr.write(f"cves learn: journal skipped ({type(e).__name__}: {e})\n")
            except BaseException: pass
            return None
    run.__name__ = fn.__name__; run.__doc__ = fn.__doc__
    return run

FACT_KEYS = ("captions.style", "captions.size", "captions.position", "captions.case", "transitions.in", "transitions.out",
             "sound.bed_lu", "sound.sfx_offset_db", "grammar.max_shot_s", "framing.creep", "motion.entry_s", "music.sync")

def facts(pr):
    """the decisions taken in this edit: style values that shape it + what edit.yaml uses"""
    E = pr.edit or {}; S = STY.load(pr); ctx = STY.scope_context(E)
    tlx = E.get("timeline") if isinstance(E.get("timeline"), dict) else {}
    f = {"goal": ctx["goal"], "platform": ctx["platform"], "spine": E.get("spine") or tlx.get("spine")}
    for k in FACT_KEYS: f[k] = S.get(k)
    mus = E.get("music") if isinstance(E.get("music"), dict) else {}
    if mus.get("bed_lu") is not None: f["sound.bed_lu"] = mus["bed_lu"]
    f["music.bed"] = bool(mus.get("file"))
    tpl = []
    for k in ("cutaways", "roto", "chest"):
        for c in E.get(k) or []:
            if isinstance(c, dict) and c.get("template"): tpl.append(c["template"])
    if isinstance(E.get("end_card"), dict) and E["end_card"].get("template"): tpl.append(E["end_card"]["template"])
    f["templates"] = sorted(set(tpl))
    f["n_cutaways"] = len(E.get("cutaways") or []); f["n_roto"] = len(E.get("roto") or []); f["n_chest"] = len(E.get("chest") or [])
    mot = E.get("motion") if isinstance(E.get("motion"), list) else []
    f["motion"] = sorted({str(m.get("piece") or m.get("template") or m.get("id")) for m in mot if isinstance(m, dict)})
    tr = E.get("transitions") if isinstance(E.get("transitions"), list) else []
    f["transition_kinds"] = sorted({str(t.get("kind")) for t in tr if isinstance(t, dict) and t.get("kind")})
    tl = pr.json("timeline.json") or {}
    if tl.get("frames") and tl.get("fps"): f["duration_s"] = round(tl["frames"] / tl["fps"], 2)
    f["treatment"] = E.get("treatment")          # `cves treatments pick` (docs/TREATMENTS.md)
    f["style_sources"] = S.get("_sources")
    return f

def flatten(o, p=""):
    """edit.yaml -> {dotted path: scalar}; lists of {id: ..} dicts are keyed by id (cutaways[c3].start), other dict lists by index"""
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            if str(k).startswith("_"): continue
            out.update(flatten(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list) and o and all(isinstance(x, dict) for x in o):
        for i, x in enumerate(o):
            key = x.get("id", i)
            out.update(flatten({k: v for k, v in x.items() if k != "id"}, f"{p}[{key}]"))
    else: out[p] = o
    return out

def diff(a, b, cap=300):
    fa, fb = flatten(a or {}), flatten(b or {})
    ch = []
    for k in sorted(set(fa) | set(fb)):
        o, n = fa.get(k), fb.get(k)
        if json.dumps(o, sort_keys=True, default=str) != json.dumps(n, sort_keys=True, default=str):
            ch.append({"path": k, "old": o, "new": n})
    return ch[:cap]

def _snap_path(pr): return pr.e("journal.last_edit.yaml")

@_safe
def on_build(pr, video=None):
    """a new master was built: journal a revision (edit.yaml diff since the last build) + the build facts"""
    E = pr.edit or {}; ev = read_journal(pr)
    snap = _snap_path(pr)
    if os.path.exists(snap):
        with open(snap, encoding="utf-8") as f: E0 = yaml.safe_load(f) or {}
        ch = diff(E0, E)
        if ch:
            last_build = max((i for i, e in enumerate(ev) if e.get("event") == "build"), default=-1)
            after_notes = any(e.get("event") == "note" for e in ev[last_build + 1:])
            append(pr, "revision", changes=ch, after_notes=after_notes)
    with open(snap, "w", encoding="utf-8") as f: yaml.safe_dump(E, f, sort_keys=False, allow_unicode=True, width=140)
    append(pr, "build", video=os.path.basename(video) if video else None, facts=facts(pr))

@_safe
def on_deliver(pr, man):
    append(pr, "deliver", version=man.get("version"),
           variants=[{"id": v.get("id"), "status": v.get("status")} for v in man.get("variants") or []], facts=facts(pr))

@_safe
def on_import(pr, E0, rep, dry_run=False):
    if dry_run: return
    append(pr, "import-edits", changes=diff(E0, rep.get("edit") or {}), applied=rep.get("applied"), not_mapped=len(rep.get("not_mapped") or []))

@_safe
def on_treatment_pick(pr, name, **data):
    """`cves treatments pick`: which treatment won, out of which, for which goal / client (mined into treatments.prefer)"""
    append(pr, "treatment-pick", treatment=name, **data)


# ======================================================================== mining
def project_roots(root):
    """Edit/journal.jsonl files under a projects root (client/project/Edit, any depth <= 4)"""
    root = os.path.abspath(os.path.expanduser(root)); out = []
    if not os.path.isdir(root): return out
    base = root.rstrip(os.sep).count(os.sep)
    for d, dirs, files in os.walk(root):
        if os.path.basename(d) == "Edit":
            if "journal.jsonl" in files: out.append(os.path.dirname(d))
            dirs[:] = []; continue
        dirs[:] = [x for x in dirs if x not in SKIP_WALK and not x.startswith((".", "_")) and d.count(os.sep) - base < 4]
    return sorted(out)

def _project_info(pdir):
    E = {}
    p = os.path.join(pdir, "Edit", "edit.yaml")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f: E = yaml.safe_load(f) or {}
        except yaml.YAMLError: E = {}
    ctx = STY.scope_context(E)
    client = ctx["client"] or os.path.basename(os.path.dirname(pdir))
    return {"dir": pdir, "name": os.path.basename(pdir), "client": str(client), "goal": ctx["goal"], "platform": ctx["platform"],
            "ref": f"{client}/{os.path.basename(pdir)}"}

def _norm_path(path):
    p = re.sub(r"\[[^\]]*\]", "[]", path)
    if p.startswith("style."): p = p[6:]
    return {"music.bed_lu": "sound.bed_lu", "aroll.creep": "framing.creep"}.get(p, p)

def _num(x): return isinstance(x, (int, float)) and not isinstance(x, bool)

def classify(ch):
    """one edit.yaml change -> (key, kind, value) or None. kind: up | down | set | remove"""
    path = ch["path"]
    if path.startswith(IGNORE_EDIT) or ".params." in path and not path.endswith((".at", ".start", ".end")): return None
    key = _norm_path(path); o, n = ch["old"], ch["new"]
    if _num(o) and _num(n) and o != n: return key, ("up" if n > o else "down"), n
    if key.endswith("[].template") and o is not None and n is None: return key, "remove", o
    if (is_style_key(key) or key.endswith(("[].kind", "[].template"))) and n is not None and o is not None and not isinstance(n, (dict, list)):
        return key, "set", n
    return None

def _scope_of(projects, versions=None):
    cl = {p["client"] for p in projects}; go = {p["goal"] for p in projects}; pl = {p["platform"] for p in projects}
    if len(cl) == 1: return f"client:{next(iter(cl))}"
    if len(go) == 1 and None not in go: return f"goal:{next(iter(go))}"
    if len(pl) == 1 and None not in pl: return f"platform:{next(iter(pl))}"
    return "global"

def _cid(*parts):
    return "L" + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:7]

def _round(v):
    if isinstance(v, float): return int(v) if abs(v - round(v)) < 1e-9 else round(v, 2)
    return v

def fit_type(key, v):
    """a learned value keeps the type of its default (an int key stays an int)"""
    d = style_value(key)
    if isinstance(d, int) and not isinstance(d, bool) and _num(v): return int(round(v))
    return v

def _median(xs):
    xs = [x for x in xs if _num(x)]
    return _round(statistics.median(xs)) if xs else None

def load_all(root):
    """[(project info, events)] for every journal under root"""
    return [(_project_info(d), _read_jsonl(os.path.join(d, "Edit", "journal.jsonl"))) for d in project_roots(root)]

def corrections(data):
    """(a) the same kind of change made by people (import-edits, or edit.yaml revisions after notes) >= 2 times"""
    groups = {}
    for info, events in data:
        for i, e in enumerate(events):
            if e.get("event") == "import-edits": src = "editor"
            elif e.get("event") == "revision" and e.get("after_notes"): src = "notes"
            else: continue
            seen = set()
            for ch in e.get("changes") or []:
                c = classify(ch)
                if not c: continue
                key, kind, val = c
                gk = (key, kind, val if kind in ("set", "remove") else None)
                if gk in seen: continue
                seen.add(gk)
                groups.setdefault(gk, []).append({"info": info, "ref": f"{info['ref']}#{i}", "src": src, "old": ch["old"], "new": ch["new"]})
    out = []
    for (key, kind, val), occ in groups.items():
        if len(occ) < 2: continue
        n = len(occ); projects = [o["info"] for o in occ]
        opp = len(groups.get((key, {"up": "down", "down": "up"}.get(kind, kind), val), [])) if kind in ("up", "down") else 0
        conf = round(min(.95, .35 + .15 * n) * n / (n + opp), 2)
        style = is_style_key(key)
        if kind in ("up", "down"):
            value = _median([o["new"] for o in occ])
            deltas = [o["new"] - o["old"] for o in occ if _num(o["old"]) and _num(o["new"])]
            what = f"`{key}` {'raised' if kind == 'up' else 'lowered'} by people {n} times (median change {_round(statistics.median(deltas)):+g})"
        elif kind == "remove":
            value = None; what = f"`{val}` graphics deleted by people {n} times"
        else:
            value = val; what = f"`{key}` set to `{val}` by people {n} times"
        c = {"id": _cid("correction", key, kind, val if kind != "up" and kind != "down" else ""), "kind": "correction",
             "type": "style" if style and kind != "remove" else "rule", "statement": what + f" across {len({p['dir'] for p in projects})} edit(s)",
             "scope": _scope_of(projects), "evidence": [o["ref"] + f" ({o['src']}: {o['old']} -> {o['new']})" for o in occ],
             "n": n, "effect": None, "confidence": conf}
        if c["type"] == "style": c["change"] = {"key": key, "value": fit_type(key, value)}
        else:
            c["rule"] = (f"Plan `{key}` {'later/larger' if kind == 'up' else 'earlier/smaller'} from the start: people corrected it that way {n} times."
                         if kind in ("up", "down") else f"Use `{val}` less: people deleted it {n} times." if kind == "remove"
                         else f"Prefer `{val}` for `{key}`: people switched to it {n} times.")
        c["public"] = c["statement"]
        out.append(c)
    return out

def versions_table(data):
    """one row per (project, version): facts at delivery (or the last build) + outcomes"""
    rows = []
    for info, events in data:
        V = {}; cur = None; last_v = None
        def row(v):
            if v not in V: V[v] = {"info": info, "version": v, "facts": cur, "ratings": [], "claude": [], "approved": None, "results": {}, "notes": []}
            elif V[v]["facts"] is None: V[v]["facts"] = cur
            return V[v]
        for e in events:
            k = e.get("event")
            if k == "build": cur = e.get("facts") or cur
            elif k == "deliver":
                cur = e.get("facts") or cur; last_v = e.get("version") or last_v
                if last_v: row(last_v)["facts"] = cur
            elif k in ("rate", "approve", "reject-version", "results", "note"):
                v = e.get("version") or last_v or "master"; r = row(v)
                if k == "rate":
                    (r["claude"] if str(e.get("by", "")).lower() == "claude" else r["ratings"]).append(float(e["score"]))
                elif k == "approve": r["approved"] = True
                elif k == "reject-version": r["approved"] = False
                elif k == "results":
                    for m, x in (e.get("metrics") or {}).items():
                        if _num(x): r["results"][m] = float(x)
                elif k == "note": r["notes"].append(e.get("text", ""))
        rows += [r for r in V.values() if r["facts"]]
    for r in rows:
        r["outcome"] = {}
        if r["ratings"]: r["outcome"]["rating"] = statistics.mean(r["ratings"])
        elif r["approved"] is not None: r["outcome"]["rating"] = 8.0 if r["approved"] else 3.0
        r["outcome"].update(r["results"])
    return rows

def _features(f):
    out = {}
    for k, v in (f or {}).items():
        if k in ("style_sources", "duration_s", "goal", "platform", "spine"): continue
        if isinstance(v, list):
            for x in v: out[f"uses:{k}:{x}"] = True
        elif v is None or isinstance(v, dict): continue
        else: out[k] = v
    return out

def correlations(rows, report):
    """(b) decisions that go with better outcomes (ratings, approvals, results). n < 3 -> nothing proposed, and the report says so"""
    out = []
    metrics = sorted({m for r in rows for m in r["outcome"]})
    if not rows: report.append("no built or delivered versions in the journals yet: no correlations"); return out
    if not metrics: report.append("outcomes: no ratings, approvals or results yet: no correlations (log them with `cves learn rate|approve|results`)")
    for m in metrics:
        R = [r for r in rows if m in r["outcome"]]
        if len(R) < MIN_N:
            report.append(f"outcome `{m}`: n={len(R)} version(s) (< {MIN_N}): no correlation proposed until there are {MIN_N}"); continue
        report.append(f"outcome `{m}`: n={len(R)} version(s)")
        feats = {}
        for r in R:
            for k, v in _features(r["facts"]).items(): feats.setdefault(k, {})
        best = {}
        for k in feats:
            vals = [(_features(r["facts"]).get(k), r["outcome"][m], r) for r in R]
            if k.startswith("uses:"): vals = [(bool(v), y, r) for v, y, r in vals]
            present = [x for x in vals if x[0] is not None]
            if len(present) < MIN_N: continue
            if all(_num(v) for v, _, _ in present) and len({v for v, _, _ in present}) > 2:
                med = statistics.median(v for v, _, _ in present)
                hi = [x for x in present if x[0] > med]; lo = [x for x in present if x[0] <= med]
                if not hi or not lo: continue
                for grp, rest, side in ((hi, lo, "high"), (lo, hi, "low")):
                    eff = statistics.mean(y for _, y, _ in grp) - statistics.mean(y for _, y, _ in rest)
                    cand = (eff, k, _median([v for v, _, _ in grp]), grp, rest, side)
                    if eff > 0 and (k not in best or eff > best[k][0]): best[k] = cand
            else:
                for val in {v for v, _, _ in present}:
                    grp = [x for x in present if x[0] == val]; rest = [x for x in present if x[0] != val]
                    if len(grp) < 2 or not rest: continue
                    eff = statistics.mean(y for _, y, _ in grp) - statistics.mean(y for _, y, _ in rest)
                    if eff > 0 and (k not in best or eff > best[k][0]): best[k] = (eff, k, val, grp, rest, "value")
        for eff, k, val, grp, rest, side in best.values():
            base = statistics.mean(y for _, y, _ in rest)
            big = eff >= 1.0 if m == "rating" else (base > 0 and eff / base >= .15) or (base <= 0 and eff > 0)
            if not big: continue
            n = len(grp) + len(rest); projects = [x[2]["info"] for x in grp + rest]
            unit = "rating points" if m == "rating" else f"{m}" + (f" (+{eff / base:.0%})" if base > 0 else "")
            if k.startswith("uses:"):
                _, kind, name = k.split(":", 2)
                if val is not True: continue
                stmt = f"edits using {kind} `{name}` scored higher on {m}: {eff:+.2f} {unit} (n={n}: {len(grp)} with, {len(rest)} without)"
                c = {"type": "rule", "rule": f"Consider {kind} `{name}`: it went with better {m} ({eff:+.2f}, n={n})."}
            else:
                stmt = f"`{k}` = {val} ({side}) went with better {m}: {eff:+.2f} {unit} (n={n}: {len(grp)} vs {len(rest)})"
                c = {"type": "style", "change": {"key": k, "value": fit_type(k, val)}} if is_style_key(k) else {"type": "rule", "rule": f"Prefer `{k}` = {val}: it went with better {m} ({eff:+.2f}, n={n})."}
            conf = round(min(.9, .2 + .08 * n) * min(1.0, (eff / 2.0) if m == "rating" else (eff / base if base > 0 else 1)), 2)
            c.update({"id": _cid("correlation", m, k, val if not _num(val) else side), "kind": "correlation", "statement": stmt, "public": stmt,
                      "scope": _scope_of(projects), "evidence": [f"{x[2]['info']['ref']}@{x[2]['version']} ({m} {x[1]:g}, {k}={x[0]})" for x in grp + rest],
                      "n": n, "effect": round(eff, 3), "metric": m, "confidence": conf})
            out.append(c)
    return out

TOPICS = {
    "captions": r"caption|subtitle|subs\b|text|font|typo",
    "music": r"music|bgm|song|track|\bbed\b|beat",
    "sfx": r"\bsfx\b|sound effect|whoosh|swoosh|ding|click",
    "pace": r"pac(e|ing)|tempo|faster|slower|quick|snappy|tight|drag|breathe|rhythm",
    "transitions": r"transition|whip|glitch|fade|wipe",
    "colour": r"colou?r|grade|grading|\bdark|bright|warm|cool|saturat",
    "zoom": r"zoom|punch",
    "hook": r"hook|opening|intro|first second|start",
    "brand": r"logo|brand",
    "motion": r"animation|animate|motion|graphic",
}
UP = r"bigger|larger|louder|more|increase|higher|boost|raise|turn up|stronger"
DOWN = r"smaller|quieter|softer|less|lower|reduce|turn down|subtle|weaker"
FAST = r"faster|quicker|snappier|tighter|punchier|speed up"
SLOW = r"slower|calmer|breathe|let it|longer hold|slow down"
NOTE_STYLE = {("captions", "up"): ("captions.size", 1.1), ("captions", "down"): ("captions.size", 0.9),
              ("music", "up"): ("sound.bed_lu", 2), ("music", "down"): ("sound.bed_lu", -2),
              ("pace", "faster"): ("grammar.max_shot_s", -0.5), ("pace", "slower"): ("grammar.max_shot_s", 0.5)}

def note_direction(t):
    t = t.lower()
    if re.search(r"too (big|large|loud|much|bright|busy|long)", t): return "down" if not re.search(r"too long", t) else "faster"
    if re.search(r"too (small|tiny|quiet|soft|little|dark)", t): return "up"
    if re.search(r"too (fast|quick|rushed)", t): return "slower"
    if re.search(r"too slow|drags?", t): return "faster"
    for d, rx in (("faster", FAST), ("slower", SLOW), ("up", UP), ("down", DOWN)):
        if re.search(rx, t): return d
    return None

def note_clusters(data):
    """(c) notes clustered by topic keyword (+ direction): the same ask >= 2 times"""
    groups = {}
    for info, events in data:
        for i, e in enumerate(events):
            if e.get("event") != "note": continue
            txt = str(e.get("text", "")); d = note_direction(txt)
            for topic, rx in TOPICS.items():
                if re.search(rx, txt, re.I):
                    dd = d if (topic == "pace") == (d in ("faster", "slower")) else None
                    groups.setdefault((topic, dd), []).append({"info": info, "ref": f"{info['ref']}#{i}", "text": txt})
    out = []
    for (topic, d), occ in groups.items():
        if len(occ) < 2: continue
        n = len(occ); projects = [o["info"] for o in occ]
        ask = {None: "mention", "up": "ask for more / bigger", "down": "ask for less / smaller", "faster": "ask for a faster pace", "slower": "ask for a slower pace"}[d]
        stmt = f"notes {ask} on {topic} {n} times across {len({p['dir'] for p in projects})} edit(s)"
        c = {"id": _cid("notes", topic, d), "kind": "notes", "statement": stmt, "public": stmt, "scope": _scope_of(projects),
             "evidence": [f"{o['ref']}: \"{o['text']}\"" for o in occ], "n": n, "effect": None, "confidence": round(min(.8, .2 + .15 * n) * (1 if d else .6), 2)}
        ms = NOTE_STYLE.get((topic, d))
        if ms:
            key, step = ms; base = style_value(key)
            if _num(base):
                val = _round(base * step) if isinstance(step, float) else _round(base + step)
                c.update({"type": "style", "change": {"key": key, "value": fit_type(key, val)}})
        if "change" not in c:
            c.update({"type": "rule", "rule": f"Check {topic} first on every edit: notes {ask} on it repeatedly (n={n})."})
        out.append(c)
    return out

def treatment_picks(data):
    """(d) the treatment people pick (`cves treatments pick`), per client and per goal: the same treatment chosen >= 2 times
    and in >= 60 % of that scope's picks -> a `treatments.prefer` style candidate for that scope"""
    groups = {}
    for info, events in data:
        for i, e in enumerate(events):
            if e.get("event") != "treatment-pick" or not e.get("treatment"): continue
            for dim in ("client", "goal"):
                val = e.get(dim) if e.get(dim) is not None else info.get(dim)
                if val is None or (dim == "goal" and not val): continue
                groups.setdefault((dim, str(val)), []).append({"info": info, "ref": f"{info['ref']}#{i}", "t": e["treatment"], "of": e.get("offered") or []})
    out = []
    for (dim, val), picks in groups.items():
        counts = {}
        for p in picks: counts[p["t"]] = counts.get(p["t"], 0) + 1
        best, n = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
        share = n / len(picks)
        if n < 2 or share < .6: continue
        scope = f"{dim}:{val}"; dirs = {p["info"]["dir"] for p in picks}
        stmt = f"treatment `{best}` picked {n} of {len(picks)} times for {scope} across {len(dirs)} edit(s)"
        public = f"treatment `{best}` picked {n} of {len(picks)} times for {'a client' if dim == 'client' else scope}"
        out.append({"id": _cid("treatment", dim, val, best), "kind": "treatment", "type": "style", "statement": stmt, "public": public,
                    "scope": scope, "evidence": [f"{p['ref']} ({p['t']} of {', '.join(p['of'])})" for p in picks],
                    "n": len(picks), "effect": None, "confidence": round(min(.9, .3 + .15 * n) * share, 2),
                    "change": {"key": "treatments.prefer", "value": best}})
    return out

def _status_maps():
    rej = {r["id"] for r in _read_jsonl(_tp("rejected.jsonl"))}
    prom = {}
    for r in _read_jsonl(_tp("promotions.jsonl")):
        if r.get("forgotten"): prom.pop(r["id"], None)
        else: prom[r["id"]] = r
    return rej, prom

def read_candidates(): return _read_jsonl(_tp("candidates.jsonl"))

def _save_candidates(cands):
    rej, prom = _status_maps()
    for c in cands: c["status"] = "rejected" if c["id"] in rej else "promoted" if c["id"] in prom else "new"
    _write_jsonl(_tp("candidates.jsonl"), [c for c in cands if c["status"] != "rejected"])

def mine(root=None, quiet=False):
    from .project import clients_root
    root = os.path.abspath(os.path.expanduser(root or clients_root()))
    data = load_all(root); report = [f"mined {len(data)} project journal(s) under {root}"]
    rows = versions_table(data)
    report.append(f"{len(rows)} version(s) with decisions; {sum(1 for r in rows if r['outcome'])} with outcomes")
    cands = corrections(data) + correlations(rows, report) + note_clusters(data) + treatment_picks(data)
    st = _read_json(_tp("study.json"))
    if st: cands += study_candidates(st, report)
    cal = [(statistics.mean(r["claude"]), r["outcome"]["rating"]) for r in rows if r["claude"] and r["ratings"]]
    if cal: report.append(f"Claude self-ratings vs human ratings: mean difference {statistics.mean(a - b for a, b in cal):+.2f} over n={len(cal)}")
    rej, prom = _status_maps()
    skipped = [c for c in cands if c["id"] in rej]
    cands = [c for c in cands if c["id"] not in rej]
    now = _now()
    for c in cands:
        c["created"] = now; c["status"] = "promoted" if c["id"] in prom else "new"
    cands.sort(key=lambda c: (c["status"] != "new", -c["confidence"]))
    _write_jsonl(_tp("candidates.jsonl"), cands)
    if skipped: report.append(f"{len(skipped)} candidate(s) skipped: rejected before")
    report.append(f"{sum(c['status'] == 'new' for c in cands)} new candidate(s) -> {_tp('candidates.jsonl')}")
    return cands, report


# ======================================================================== promotion (always by a person)
def find(cid):
    for c in read_candidates():
        if c["id"] == cid: return c
    raise SystemExit(f"no candidate {cid}: run `cves learn mine`, then `cves learn list`")

def _read_yaml(p):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return yaml.safe_load(f) or {}
    return {}

def _read_json(p):
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)
    return None

LEARNED_HEAD = ("# Learned taste layer (docs/LEARNING.md). Written by `cves learn promote`; every entry was approved by a person.\n"
                "# scopes: {global | goal:<ad|viral> | platform:<name> | client:<name> (personal file only): {style keys}}\n")

def _write_learned(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(LEARNED_HEAD); yaml.safe_dump(d, f, sort_keys=False, allow_unicode=True, width=140)

def known_names(extra=()):
    """client names seen in project journals / folders: never written into shared files"""
    from .project import clients_root
    names = set(x for x in extra if x)
    try:
        for info, _ in load_all(clients_root()): names.add(info["client"])
    except Exception: pass
    for c in read_candidates():
        for k, v in STY.scope_parts(c.get("scope", "global")):
            if k == "client": names.add(v)
        for e in c.get("evidence") or []: names.add(str(e).split("/")[0])
    return {n for n in names if n and len(n) > 1}

PATHISH = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][^\s`|]+){2,}|~[\\/][^\s`|]*")

def anonymise(text, names):
    t = PATHISH.sub("<path>", str(text))
    for n in sorted(names, key=len, reverse=True):
        t = re.sub(re.escape(n), "a client", t, flags=re.I)
    return t

def _public(c, scope, names):
    t = anonymise(c.get("public") or c["statement"], names)
    for n in names: assert n.lower() not in t.lower(), "client name in shared text"
    return t

def promote(cid, scope=None, share=False, team=False):
    c = find(cid); scope = scope or c["scope"]
    try: parts = STY.scope_parts(scope)
    except ValueError as e: raise SystemExit(str(e))
    if share and team: raise SystemExit("--share (public repo) and --team (shared folder): pick one")
    if team and not STY.team_dir():
        raise SystemExit("no team layer: set `team_taste: <shared folder>` in ~/.cves/config.yaml (or $CVES_TEAM_TASTE), e.g. a Google Drive folder every editor syncs")
    if share and any(k == "client" for k, _ in parts):
        raise SystemExit(f"{cid} is scoped to a client: client taste stays local. Promote without --share, or pass --scope global|goal:<..>|platform:<..> with --share")
    rej, prom = _status_maps()
    if cid in prom: raise SystemExit(f"{cid} is already promoted ({prom[cid]['scope']}{', shared' if prom[cid].get('share') else ''}); `cves learn forget {cid}` first")
    names = known_names([v for k, v in parts if k == "client"])
    import getpass
    rec = {"id": cid, "t": _now(), "scope": scope, "share": bool(share), "team": bool(team), "by": getpass.getuser(), "type": c["type"]}
    msgs = []
    if c["type"] == "style":
        key, val = c["change"]["key"], c["change"]["value"]
        if not is_style_key(key): raise SystemExit(f"`{key}` is not a key of engine/cves/styles/default.yaml: only existing style keys can be learned")
        path = STY.learned_path("repo" if share else "team" if team else "personal")
        L = _read_yaml(path); L.setdefault("scopes", {}); L["scopes"].setdefault(scope, {})
        prev = style_value(key, L["scopes"][scope])
        _dset(L["scopes"][scope], key, val)
        info = {"scope": scope, "key": key, "value": val, "date": _today(), "n": c.get("n"), "effect": c.get("effect")}
        if not share: info["statement"] = c["statement"]
        if team: info["by"] = rec["by"]
        L.setdefault("_promoted", {})[cid] = info
        _write_learned(path, L)
        rec.update({"key": key, "value": val, "path": path, "prev": None if prev is MISSING else prev, "had_prev": prev is not MISSING})
        msgs.append(f"{key} = {val} for {scope} -> {path}")
    else:
        text = c.get("rule") or c["statement"]
        if not share:
            rp = os.path.join(STY.team_dir(), "rules.md") if team else _tp("rules.md")
            os.makedirs(os.path.dirname(rp), exist_ok=True); new = not os.path.exists(rp)
            with open(rp, "a", encoding="utf-8") as f:
                if new: f.write("# Team learned rules (`cves learn promote --team`; shared folder)\n\n" if team else "# Personal learned rules (`cves learn promote`; local only)\n\n")
                f.write(f"- [{cid}] ({scope}, {_today()}{', ' + rec['by'] if team else ''}) {text}\n")
            rec["path"] = rp; msgs.append(f"rule -> {rp}")
    if share:
        tp = os.path.join(kb_dir(), "TASTE.md")
        what = f"`{c['change']['key']}` → `{c['change']['value']}`" if c["type"] == "style" else anonymise(c.get("rule") or "", names)
        eff = f" · effect {c['effect']:+g} {c.get('metric', '')}".rstrip() if _num(c.get("effect")) else ""
        line = f"- {_today()} [{cid}] **{c['type']}** {what} · scope {scope} · n={c.get('n')}{eff} · {_public(c, scope, names)}\n"
        for n in names: assert n.lower() not in line.lower()
        _taste_add(tp, line); msgs.append(f"shared entry -> {tp}")
        rec["taste"] = tp
    _append_jsonl(_tp("promotions.jsonl"), rec)
    cands = read_candidates()
    for x in cands:
        if x["id"] == cid: x["status"] = "promoted"
    _write_jsonl(_tp("candidates.jsonl"), cands)
    return msgs

TASTE_HEAD = ("# Shared taste (learned, anonymised)\n\n"
              "Patterns the team approved with `cves learn promote --share` (docs/LEARNING.md). No client names, no paths: only the\n"
              "pattern, its scope, the sample size and the effect. Style changes live in `knowledge-base/taste/learned.yaml`.\n\n")

def _taste_add(p, line):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    s = open(p, encoding="utf-8").read() if os.path.exists(p) else TASTE_HEAD
    s = s.rstrip("\n") + "\n"
    if not s.splitlines()[-1].startswith("- "): s += "\n"
    with open(p, "w", encoding="utf-8") as f: f.write(s + line)

def _drop_lines(p, cid):
    if not p or not os.path.exists(p): return
    with open(p, encoding="utf-8") as f: lines = f.readlines()
    with open(p, "w", encoding="utf-8") as f: f.writelines(l for l in lines if f"[{cid}]" not in l)

def forget(cid):
    rej, prom = _status_maps()
    if cid not in prom: raise SystemExit(f"{cid} is not promoted (nothing to forget)")
    r = prom[cid]; msgs = []
    if r["type"] == "style":
        L = _read_yaml(r["path"]); sec = (L.get("scopes") or {}).get(r["scope"], {})
        if r.get("had_prev"): _dset(sec, r["key"], r["prev"])
        else: _ddel(sec, r["key"])
        if not sec: (L.get("scopes") or {}).pop(r["scope"], None)
        (L.get("_promoted") or {}).pop(cid, None)
        _write_learned(r["path"], L); msgs.append(f"{r['key']} reverted in {r['path']}")
    else:
        _drop_lines(r.get("path"), cid); msgs.append(f"rule removed from {r.get('path')}")
    if r.get("taste"): _drop_lines(r["taste"], cid); msgs.append(f"shared entry removed from {r['taste']}")
    _append_jsonl(_tp("promotions.jsonl"), {"id": cid, "t": _now(), "forgotten": True})
    cands = read_candidates()
    for x in cands:
        if x["id"] == cid: x["status"] = "new"
    _write_jsonl(_tp("candidates.jsonl"), cands)
    return msgs

def reject_candidate(cid, why):
    c = find(cid)
    _append_jsonl(_tp("rejected.jsonl"), {"id": cid, "t": _now(), "why": why, "statement": c["statement"]})
    _write_jsonl(_tp("candidates.jsonl"), [x for x in read_candidates() if x["id"] != cid])
    return f"{cid} rejected: it will not be proposed again"


# ======================================================================== taste study (great videos -> measurements only)
def parse_notes(folder):
    """notes.txt lines `file | ad|viral | why it's great`; without it, every video (kind from an ad/ viral/ sub-folder)"""
    from .inspire import VIDEO_EXT
    p = os.path.join(folder, "notes.txt"); out = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                if not ln.strip() or ln.lstrip().startswith("#"): continue
                parts = [x.strip() for x in ln.split("|")]
                kind = (parts[1].lower() if len(parts) > 1 and parts[1] else "unknown")
                out.append({"file": parts[0], "kind": kind, "why": parts[2] if len(parts) > 2 else ""})
        return out
    for d, _, fs in os.walk(folder):
        for f in sorted(fs):
            if f.lower().endswith(VIDEO_EXT):
                rel = os.path.relpath(os.path.join(d, f), folder); top = rel.split(os.sep)[0].lower()
                out.append({"file": rel, "kind": top if top in ("ad", "viral") else "unknown", "why": ""})
    return out

def _ceil_half(x): return math.ceil(x * 2) / 2

def measure(path, max_s=60.0):
    """pacing / face / loudness of one video through inspire's analysis (degrades to a plain frame-difference pass)"""
    r, how = None, "inspire.analyse_video"
    try:
        from . import inspire
        r = inspire.analyse_video(path, max_s)
    except Exception as e:      # noqa: BLE001  inspire is being rewritten by another workstream: never depend on its internals
        how = f"fallback ({type(e).__name__})"; r = _fallback_analyse(path, max_s)
    dur = float(r.get("dur") or 0.0); cuts = sorted(float(c) for c in r.get("cuts") or [])
    edges = [0.0] + [c for c in cuts if 0 < c < dur] + [dur]
    shots = [b - a for a, b in zip(edges, edges[1:]) if b - a > 1e-3]
    m = {"duration_s": round(dur, 2), "cuts": len(cuts), "cuts_per_min": round(len(cuts) / dur * 60, 1) if dur else None,
         "median_shot_s": round(statistics.median(shots), 2) if shots else None,
         "p90_shot_s": round(sorted(shots)[min(len(shots) - 1, int(.9 * len(shots)))], 2) if shots else None,
         "first_cut_s": round(cuts[0], 2) if cuts else None, "how": how}
    smp = r.get("samples") or []
    if smp: m["face_share"] = round(sum(1 for s in smp if s.get("face")) / len(smp), 2)
    a = r.get("audio") or {}
    if a.get("I") is not None: m["loudness_lufs"] = round(a["I"], 1)
    M = [x for x in a.get("M") or [] if x > -70]
    if len(M) > 10: m["loudness_range_lu"] = round(float(sorted(M)[int(.9 * len(M))] - sorted(M)[int(.1 * len(M))]), 1)
    style = {}
    if m["p90_shot_s"]: style["grammar.max_shot_s"] = max(1.0, _ceil_half(m["p90_shot_s"]))
    return m, style

def _fallback_analyse(path, max_s):
    import cv2, numpy as np
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    prev, times, diffs, i = None, [], [], 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        t = i / fps; i += 1
        if t > max_s: break
        lo = cv2.resize(fr, (96, 170), interpolation=cv2.INTER_AREA).astype(np.int16)
        diffs.append(0.0 if prev is None else float(np.abs(lo - prev).mean() / 255 * 2)); times.append(t); prev = lo
    cap.release()
    try: from .inspire import detect_cuts
    except Exception:      # noqa: BLE001
        def detect_cuts(ts, ds): return [t for t, d in zip(ts, ds) if d > .25]
    return {"dur": times[-1] if times else 0.0, "cuts": detect_cuts(times, diffs), "samples": [], "audio": None}

def study(folder, max_s=60.0):
    folder = os.path.abspath(os.path.expanduser(folder))
    if not os.path.isdir(folder): raise SystemExit(f"no folder {folder}")
    items = parse_notes(folder)
    if not items: raise SystemExit(f"no videos in {folder} (and no notes.txt: lines `file | ad|viral | why it's great`)")
    files, lines = [], []
    for it in items:
        p = os.path.join(folder, it["file"])
        if not os.path.exists(p): lines.append(f"  missing {it['file']}: skipped"); continue
        try: m, st = measure(p, max_s)
        except Exception as e:      # noqa: BLE001
            lines.append(f"  {it['file']}: not measured ({type(e).__name__}: {e})"); continue
        files.append({"name": os.path.basename(it["file"]), "kind": it["kind"], "why": it["why"], "metrics": m, "style": st})
        lines.append(f"  {os.path.basename(it['file'])[:40]:40s} {it['kind']:7s} {m['duration_s']:6.1f} s  {m['cuts']:3d} cuts  median shot {m['median_shot_s']} s")
    kinds = {}
    for f in files:
        k = kinds.setdefault(f["kind"], {"n": 0, "metrics": {}, "style": {}, "why": []})
        k["n"] += 1; k["why"].append(f["why"])
    for kind, k in kinds.items():
        F = [f for f in files if f["kind"] == kind]
        for key in sorted({x for f in F for x in f["metrics"] if x != "how"}):
            k["metrics"][key] = _median([f["metrics"].get(key) for f in F])
        for key in sorted({x for f in F for x in f["style"]}):
            vals = [f["style"][key] for f in F if key in f["style"]]
            k["style"][key] = {"value": _median(vals) if all(_num(v) for v in vals) else max(set(vals), key=vals.count), "n": len(vals)}
    st = {"folder_name": os.path.basename(folder), "date": _today(), "kinds": kinds, "files": files}
    with open(_tp("study.json"), "w", encoding="utf-8") as f: json.dump(st, f, indent=1, ensure_ascii=False)
    report = []
    new = study_candidates(st, report)
    old = [c for c in read_candidates() if c.get("kind") != "study"]
    rej, _ = _status_maps()
    _save_candidates(old + [c for c in new if c["id"] not in rej])
    return lines + report + [f"measurements -> {_tp('study.json')} (no media copied)"], new

def study_candidates(st, report):
    out = []
    for kind, k in (st.get("kinds") or {}).items():
        if kind not in ("ad", "viral"): report.append(f"study `{kind}`: kind is not ad|viral: measured, no candidates"); continue
        if k["n"] < MIN_N: report.append(f"study `{kind}`: n={k['n']} video(s) (< {MIN_N}): measured, no candidates yet"); continue
        for key, sv in (k.get("style") or {}).items():
            if sv["n"] < MIN_N or not is_style_key(key) or sv["value"] == style_value(key): continue
            stmt = f"great {kind} videos you studied use `{key}` = {sv['value']} (n={sv['n']}; default {style_value(key)})"
            out.append({"id": _cid("study", kind, key), "kind": "study", "type": "style", "change": {"key": key, "value": fit_type(key, sv["value"])},
                        "statement": stmt, "public": stmt, "scope": f"goal:{kind}", "evidence": [f"study.json kinds.{kind}"],
                        "n": sv["n"], "effect": None, "confidence": round(min(.8, .3 + .1 * sv["n"]), 2), "status": "new", "created": _now()})
        m = k.get("metrics") or {}
        if m.get("first_cut_s") is not None:
            stmt = f"great {kind} videos you studied make their first cut at {m['first_cut_s']} s (median, n={k['n']}); {m.get('cuts_per_min')} cuts/min"
            out.append({"id": _cid("study", kind, "pacing"), "kind": "study", "type": "rule", "statement": stmt, "public": stmt,
                        "rule": f"For {kind} edits: first change by about {m['first_cut_s']} s and about {m.get('cuts_per_min')} cuts per minute (studied, n={k['n']}).",
                        "scope": f"goal:{kind}", "evidence": [f"study.json kinds.{kind}"], "n": k["n"], "effect": None,
                        "confidence": round(min(.7, .2 + .1 * k["n"]), 2), "status": "new", "created": _now()})
    return out


# ======================================================================== CLI
def _kv(tokens):
    """--hook-rate 0.31 / --hold=0.18 / ctr=0.02 -> {hook_rate: 0.31, ...}"""
    out, i = {}, 0
    while i < len(tokens):
        t = tokens[i]
        if t.startswith("--"):
            k = t[2:]
            if "=" in k: k, v = k.split("=", 1)
            elif i + 1 < len(tokens) and not tokens[i + 1].startswith("--") and "=" not in tokens[i + 1]: v = tokens[i + 1]; i += 1
            else: v = True
        elif "=" in t: k, v = t.split("=", 1)
        else: raise SystemExit(f"results: cannot read `{t}` (use --metric value or metric=value)")
        try: v = float(v) if not isinstance(v, bool) else v
        except ValueError: pass
        out[k.strip().lower().replace("-", "_")] = v; i += 1
    return out

def _version(v):
    if not VERSION_RX.match(v or ""): raise SystemExit(f"`{v}` is not a version: use vNNN (a folder in Export/) or master")
    return v

def _pop_project(argv, project):
    out, i = [], 0
    while i < len(argv):
        if argv[i] == "--project" and i + 1 < len(argv): project = argv[i + 1]; i += 2; continue
        if argv[i].startswith("--project="): project = argv[i].split("=", 1)[1]; i += 1; continue
        out.append(argv[i]); i += 1
    return out, project

def main(argv, project=None):
    argv, project = _pop_project(list(argv), project)
    if argv and argv[0] == "results":      # free-form metrics: parsed by hand (argparse splits unknown --flags from their values)
        if len(argv) < 2 or argv[1] in ("-h", "--help"): print("cves learn results vNNN [--platform meta] [--hook-rate 0.31 --hold 0.18 ..] [key=value ..]"); return 0
        from .project import Project
        mt = _kv(argv[2:]); plat = mt.pop("platform", None)
        if not mt: raise SystemExit("give at least one metric, e.g. --hook-rate 0.31 --hold 0.18 or ctr=0.012")
        append(Project(project or os.getcwd()), "results", version=_version(argv[1]), platform=plat, metrics=mt)
        print(f"{argv[1]}: {len(mt)} result metric(s) journaled" + (f" ({plat})" if plat else "")); return 0
    ap = argparse.ArgumentParser(prog="cves learn", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="sub", required=True)
    n = sp.add_parser("note"); n.add_argument("text"); n.add_argument("--version"); n.add_argument("--by", default="owner")
    r = sp.add_parser("rate"); r.add_argument("version"); r.add_argument("score", type=float); r.add_argument("--why", default=""); r.add_argument("--by", default="owner")
    r.add_argument("--scores", help="rubric scores: hook=7,story=6,...")
    for k in ("approve", "reject"):
        x = sp.add_parser(k); x.add_argument("target", help="vNNN | master (reject also takes a candidate id)"); x.add_argument("--why", default=""); x.add_argument("--by", default="owner")
    j = sp.add_parser("journal"); j.add_argument("--tail", type=int, default=20)
    m = sp.add_parser("mine"); m.add_argument("--root"); m.add_argument("--json", action="store_true")
    ls = sp.add_parser("list"); ls.add_argument("--all", action="store_true")
    sh = sp.add_parser("show"); sh.add_argument("id")
    pm = sp.add_parser("promote"); pm.add_argument("id"); pm.add_argument("--scope"); pm.add_argument("--share", action="store_true"); pm.add_argument("--team", action="store_true")
    fg = sp.add_parser("forget"); fg.add_argument("id")
    sd = sp.add_parser("study"); sd.add_argument("folder"); sd.add_argument("--max-s", type=float, default=60.0)
    a = ap.parse_args(argv)

    def proj():
        from .project import Project
        return Project(project or os.getcwd())

    if a.sub == "note":
        append(proj(), "note", text=a.text, version=_version(a.version) if a.version else None, by=a.by); print("note journaled (verbatim)"); return 0
    if a.sub == "rate":
        if not 1 <= a.score <= 10: raise SystemExit("score must be 1-10")
        sc = None
        if a.scores:
            sc = {}
            for kv in a.scores.split(","):
                k, _, v = kv.partition("=")
                try: sc[k.strip()] = float(v)
                except ValueError: raise SystemExit(f"--scores: `{kv}` is not name=number")
        append(proj(), "rate", version=_version(a.version), score=a.score, why=a.why or None, by=a.by.lower(), scores=sc)
        print(f"{a.version} rated {a.score:g}/10 by {a.by}"); return 0
    if a.sub in ("approve", "reject"):
        if a.sub == "reject" and not VERSION_RX.match(a.target):
            if not a.why: raise SystemExit("say why: cves learn reject <id> --why \"...\"")
            print(reject_candidate(a.target, a.why)); return 0
        append(proj(), "approve" if a.sub == "approve" else "reject-version", version=_version(a.target), why=a.why or None, by=a.by.lower())
        print(f"{a.target} {a.sub}d by {a.by}"); return 0
    if a.sub == "journal":
        for e in read_journal(proj())[-a.tail:]:
            print(f"{e.get('t', '')[:19]}  {e.get('event', ''):13s} " + json.dumps({k: v for k, v in e.items() if k not in ('t', 'event', 'cves', 'style_hash', 'facts', 'changes')}, ensure_ascii=False, default=str)[:160])
        return 0
    if a.sub == "mine":
        cands, rep = mine(a.root)
        if a.json: print(json.dumps(cands, indent=1, ensure_ascii=False, default=str)); return 0
        print("\n".join(rep))
        for c in cands:
            if c["status"] == "new": print(f"  {c['id']}  {c['confidence']:.2f}  {c['type']:5s} {c['scope']:22s} {c['statement']}")
        print("review: cves learn show <id>; then promote <id> [--share] or reject <id> --why \"...\"")
        return 0
    if a.sub == "list":
        cs = read_candidates()
        if not cs: print("no candidates: run `cves learn mine`"); return 0
        for c in cs:
            if a.all or c.get("status") == "new":
                print(f"{c['id']}  {c.get('status', 'new'):8s} {c['confidence']:.2f}  {c['type']:5s} {c['scope']:22s} {c['statement']}")
        return 0
    if a.sub == "show":
        print(yaml.safe_dump(find(a.id), sort_keys=False, allow_unicode=True, width=140)); return 0
    if a.sub == "promote":
        for x in promote(a.id, a.scope, a.share, a.team): print(x)
        return 0
    if a.sub == "forget":
        for x in forget(a.id): print(x)
        return 0
    if a.sub == "study":
        lines, new = study(a.folder, a.max_s)
        print("\n".join(lines))
        for c in new: print(f"  {c['id']}  {c['confidence']:.2f}  {c['type']:5s} {c['scope']:14s} {c['statement']}")
        return 0
    return 1
