"""Edit plan review (docs/PLAN-REVIEW.md): the editor approves shots and leaves notes on EDIT-PLAN.html; quick actions become
exact edit.yaml edits; Claude reads one small file (Edit/plan_notes.pending.md) instead of the page or its images.

  cves review-plan [--port N] [--no-open] [--keep]   build the plan if stale, serve Moodboard/ on 127.0.0.1, wait for Send
  cves plan apply-notes [--force]                    Edit/plan_notes.json -> edit.yaml edits (backup kept) + plan_notes.pending.md

Files:
  Edit/plan_notes.json          what the page sends: per shot the edit.yaml entries it came from (refs), approve / unlock,
                                quick actions and the free-text note; `applied_at` once applied
  Edit/plan_notes.pending.md    the free-text notes and the actions that need Claude, per shot (the only file Claude reads)
  Edit/plan_lock.json           approved shots: {shots: {key: {entries: {ref: entry hash}, approved_at, n}}}
  Moodboard/plan_state.json     per shot hash + frames of the last plan round (changed badges, frame reuse)

A shot's refs point at edit.yaml entries: {slot: cutaways|broll|roto|chest|end_card|zoom|captions, index, id | segment}.
Entries are found by id (cutaways, broll) or segment (roto, chest), so a ref stays exact when the list moves."""
import ast, copy, datetime, hashlib, html, http.server, inspect, json, os, re, shutil, socketserver, tempfile, textwrap, threading
import yaml

NOTES_VERSION = 1
OPS = ("bigger", "smaller", "earlier", "later", "swap", "remove", "fix_caption")
STEP_S = .25                    # Earlier / Later (s)
SIZE_K = 1.1                    # Bigger / Smaller factor on a template's size / scale param
ZOOM_STEP = .05                 # Bigger / Smaller on an A-roll shot (its aroll.zoom)
SLOT_KINDS = {"cutaways": ("cutaway", "media", "overlay"), "roto": ("roto",), "chest": ("chest", "overlay"), "end_card": ("end",)}
NOT_SWAPPABLE = {"broll_shot", "overlay_render"}      # engine plumbing, not a look to pick
PORT = 8765


def today(): return datetime.date.today().isoformat()


def _now(): return datetime.datetime.now().isoformat(timespec="seconds")


def entry_hash(x):
    return hashlib.sha1(json.dumps(x, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ refs: shot -> edit.yaml entry
def broll_id(x, j): return str(x.get("id") or f"b{j + 1:02d}")


def _seg_of(x):
    s = x.get("segment"); return ",".join(s) if isinstance(s, list) else s


def ref_for(E, slot, i=None, **kw):
    """the ref of edit.yaml entry slot[i] (cutaways / broll / roto / chest), end_card, zoom (segment=, zoom=) or captions"""
    if slot in ("cutaways", "broll", "roto", "chest"):
        x = (E.get(slot) or [])[i]; r = {"slot": slot, "index": i}
        if slot == "cutaways": r["id"] = str(x.get("id"))
        elif slot == "broll": r["id"] = broll_id(x, i)
        else: r["segment"] = _seg_of(x)
        if x.get("template"): r["template"] = x["template"]
    elif slot == "end_card": r = {"slot": "end_card", "template": (E.get("end_card") or {}).get("template")}
    elif slot == "zoom": r = {"slot": "zoom", "segment": kw["segment"], "zoom": float(kw.get("zoom", 1.0))}
    elif slot == "captions": r = {"slot": "captions"}
    else: raise ValueError(f"unknown slot {slot}")
    x = find_entry(E, r)
    if slot not in ("captions",) and x is not None: r["hash"] = entry_hash(x)
    return r


def _locate(E, r):
    """(container, key) holding the entry a ref points at, or None"""
    s = r.get("slot")
    if s in ("cutaways", "broll", "roto", "chest"):
        L = E.get(s)
        if not isinstance(L, list): return None
        if s == "cutaways": m = [j for j, x in enumerate(L) if isinstance(x, dict) and str(x.get("id")) == r.get("id")]
        elif s == "broll": m = [j for j, x in enumerate(L) if isinstance(x, dict) and broll_id(x, j) == r.get("id")]
        else: m = [j for j, x in enumerate(L) if isinstance(x, dict) and _seg_of(x) == r.get("segment")]
        if len(m) > 1 and r.get("template"): m = [j for j in m if L[j].get("template") == r["template"]] or m
        if not m: return None
        j = r.get("index") if r.get("index") in m else m[0]
        return L, j
    if s == "end_card": return (E, "end_card") if E.get("end_card") else None
    return None


def find_entry(E, r):
    """the edit.yaml entry of a ref (zoom: {segment, zoom}; captions: the captions mapping), or None"""
    s = r.get("slot")
    if s == "zoom":
        z = ((E.get("aroll") or {}).get("zoom") or {}).get(r["segment"])
        return {"segment": r["segment"], "zoom": float(z) if z is not None else float(r.get("zoom", 1.0))}
    if s == "captions": return E.get("captions") or {}
    loc = _locate(E, r)
    return loc[0][loc[1]] if loc else None


def ref_key(r): return f"{r['slot']}:{r.get('id') or r.get('segment') or ''}".rstrip(":")


def ref_label(r):
    s = r["slot"]
    if s == "zoom": return f"A-roll framing ({r['segment']})"
    if s == "captions": return "captions"
    if s == "end_card": return f"end card `{r.get('template')}`"
    return f"{s} {r.get('id') or r.get('segment')} `{r.get('template', '')}`".replace(" ``", "")


# ------------------------------------------------------------------ templates: what a slot accepts, which param sizes it
def valid_templates(slot):
    """templates `cves validate` accepts without a warning in that slot (schema._template), engine plumbing left out"""
    from . import templates as T
    want = SLOT_KINDS.get(slot)
    if not want: return []
    return sorted(k for k in T.REGISTRY if T.KIND.get(k) in want and k not in NOT_SWAPPABLE)


def _num_default(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): return float(node.value)
    if isinstance(node, ast.Call):            # p.get("size", B("size", 300)): the inner literal
        for a in reversed(node.args):
            v = _num_default(a)
            if v is not None: return v
    return None


def _param_default(name, key):
    from . import templates as T
    fns = T.REGISTRY.get(name)
    if not fns: return None
    try: tree = ast.parse(textwrap.dedent(inspect.getsource(fns[0])))
    except (OSError, TypeError, SyntaxError): return None
    vals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and len(node.args) == 2 \
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == key:
            v = _num_default(node.args[1])
            if v is not None: vals.add(v)
    return max(vals) if vals else None


def size_param(name):
    """(param, default) that Bigger / Smaller scale for a template ("scale" first, then "size"), or None"""
    from . import schema
    if not name: return None
    spec, _ = schema.template_params(name)
    for key in ("scale", "size"):
        if key in spec and spec[key][0] in ("number", "any", "int"):
            d = _param_default(name, key)
            if d is None and key == "scale": d = 1.0
            if d is not None: return key, d
    return None


# ------------------------------------------------------------------ quick actions (pure: edit dict in place)
_PH = re.compile(r"^\{(start|end):([^}+]+?)([+-]\d+(?:\.\d+)?)?\}$")


def _fmt(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _shift_t(v, d):
    if isinstance(v, (int, float)) and not isinstance(v, bool): return round(max(0.0, float(v) + d), 3)
    m = _PH.match(v) if isinstance(v, str) else None
    if not m: return v
    off = round(float(m.group(3) or 0) + d, 3)
    return "{%s:%s%s}" % (m.group(1), m.group(2), "" if off == 0 else ("+" if off > 0 else "-") + _fmt(abs(off)))


def _is_time(v): return (isinstance(v, (int, float)) and not isinstance(v, bool)) or (isinstance(v, str) and bool(_PH.match(v)))


def _shift_params(p, d, path, out):
    """every entry time in a params tree: `at`, `*_at`, `enter`, and `count: [t, dur]`"""
    if isinstance(p, dict):
        for k, v in p.items():
            if (k == "at" or k.endswith("_at") or k == "enter") and _is_time(v):
                nv = _shift_t(v, d); out.append((path + (k,), v, nv)); p[k] = nv
            elif k == "count" and isinstance(v, list) and len(v) == 2 and _is_time(v[0]):
                nv = [_shift_t(v[0], d), v[1]]; out.append((path + (k,), list(v), nv)); p[k] = nv
            elif isinstance(v, (dict, list)): _shift_params(v, d, path + (k,), out)
    elif isinstance(p, list):
        for j, v in enumerate(p):
            if isinstance(v, (dict, list)): _shift_params(v, d, path + (j,), out)


OP_LABEL = {"bigger": "Bigger", "smaller": "Smaller", "earlier": "Earlier", "later": "Later", "swap": "Swap template", "remove": "Remove", "fix_caption": "Fix caption"}


def action_label(a):
    op = a.get("op"); s = OP_LABEL.get(op, str(op))
    if op in ("earlier", "later"): s += f" {float(a.get('step', STEP_S)):.2f} s"
    if op == "swap": s += f" -> `{a.get('template')}`"
    if op == "fix_caption": s += f" \"{a.get('from')}\" -> \"{a.get('to')}\""
    return s


def apply_action(E, ref, action):
    """one quick action on the edit dict E (in place). Returns {changed, changes: [(path, old, new)]} plus `note` (it goes to
    Claude as a note: the engine has no exact edit for it) or `error` (invalid, nothing changed)."""
    op = action.get("op"); res = {"changed": False, "changes": []}; slot = ref.get("slot")
    if op == "fix_caption":
        a, b = str(action.get("from") or "").strip(), str(action.get("to") or "").strip()
        if not a or not b: return {**res, "error": "fix caption needs a word and its replacement"}
        cap = E.get("captions")
        if not isinstance(cap, dict): cap = E["captions"] = {}
        fx = cap.get("fixes")
        if not isinstance(fx, dict): fx = cap["fixes"] = {}
        old = fx.get(a); fx[a] = b
        return {"changed": old != b, "changes": [(("captions", "fixes", a), old, b)]}
    if slot == "captions": return {**res, "note": f"{action_label(action)} needs a target graphic or framing"}
    if slot == "zoom":
        seg = ref["segment"]
        if op in ("bigger", "smaller"):
            ar = E.get("aroll")
            if not isinstance(ar, dict): ar = E["aroll"] = {}
            zm = ar.get("zoom")
            if not isinstance(zm, dict): zm = ar["zoom"] = {}
            cur = float(zm.get(seg, ref.get("zoom", 1.0))); new = round(max(1.0, cur + (ZOOM_STEP if op == "bigger" else -ZOOM_STEP)) if op == "bigger" else max(.5, cur - ZOOM_STEP), 3)
            old = zm.get(seg); zm[seg] = new
            return {"changed": old != new, "changes": [(("aroll", "zoom", seg), old, new)]}
        if op == "remove": return {**res, "note": "Remove on an A-roll shot cuts speech: change Edit/selects.yaml (step 3), not edit.yaml"}
        return {**res, "note": f"{action_label(action)} on an A-roll shot: its cuts are the segment boundaries (selects.yaml), not an edit.yaml time"}
    loc = _locate(E, ref)
    if loc is None: return {**res, "error": f"{ref_label(ref)} is no longer in edit.yaml"}
    cont, key = loc; x = cont[key]; base = (slot,) if slot == "end_card" else (slot, key)
    if op == "remove":
        del cont[key]; return {"changed": True, "changes": [(base, x, None)]}
    if op in ("bigger", "smaller"):
        if slot == "broll": return {**res, "note": f"{action_label(action)} on a B-roll shot: it fills the frame; say how (framing fit, ken burns, a crop)"}
        sp = size_param(x.get("template"))
        if not sp: return {**res, "note": f"{action_label(action)}: `{x.get('template')}` has no scale or size param, so this is a note for Claude"}
        k, d = sp; p = x.get("params")
        if not isinstance(p, dict): p = x["params"] = {}
        cur = p.get(k, d)
        try: cur = float(cur)
        except (TypeError, ValueError): return {**res, "note": f"{action_label(action)}: `{x.get('template')}` {k} is {cur!r}, not a number"}
        new = cur * SIZE_K if op == "bigger" else cur / SIZE_K
        new = round(new, 3) if k == "scale" else round(new, 1)
        old = p.get(k); p[k] = new
        return {"changed": True, "changes": [(base + ("params", k), old, new)]}
    if op in ("earlier", "later"):
        if slot == "end_card": return {**res, "note": f"{action_label(action)} on the end card: it starts where the A-roll ends; change its duration or the cut"}
        d = abs(float(action.get("step", STEP_S))) * (-1 if op == "earlier" else 1); ch = []
        for k in ("start", "end", "at"):
            if k in x and _is_time(x[k]):
                nv = _shift_t(x[k], d); ch.append((base + (k,), x[k], nv)); x[k] = nv
        _shift_params(x.get("params"), d, base + ("params",), ch)
        if slot in ("cutaways", "broll") and any(c[0][-1] in ("start", "end") for c in ch) and x.get("snap") is not False:
            ch.append((base + ("snap",), x.get("snap"), False)); x["snap"] = False     # exact: the boundary snap would undo the move
        if not ch: return {**res, "note": f"{action_label(action)}: {ref_label(ref)} has no start / end / at time"}
        return {"changed": True, "changes": ch}
    if op == "swap":
        new = action.get("template")
        if slot not in SLOT_KINDS: return {**res, "error": f"a {slot} shot has no template to swap"}
        if new not in valid_templates(slot): return {**res, "error": f"`{new}` is not a {slot} template (`cves templates`)"}
        from . import schema
        spec, open_ = schema.template_params(new); old = x.get("template"); x["template"] = new; ch = [(base + ("template",), old, new)]
        p = x.get("params")
        if isinstance(p, dict) and not open_:
            for k in [k for k in p if k not in spec]: ch.append((base + ("params", k), p[k], None)); del p[k]
        return {"changed": old != new, "changes": ch}
    return {**res, "error": f"unknown quick action {op!r}"}


# ------------------------------------------------------------------ notes file
def _check_notes(d):
    if not isinstance(d, dict) or not isinstance(d.get("shots"), list): raise ValueError("plan notes: expected {shots: [...]}")
    for s in d["shots"]:
        if not isinstance(s, dict): raise ValueError("plan notes: every shot is a mapping")
        if not isinstance(s.get("refs", []), list) or not isinstance(s.get("actions", []), list): raise ValueError("plan notes: refs / actions are lists")
        if not isinstance(s.get("note", ""), str): raise ValueError("plan notes: note is text")
        for a in s.get("actions", []):
            if not isinstance(a, dict) or a.get("op") not in OPS: raise ValueError(f"plan notes: unknown quick action {a!r}")
    if not isinstance(d.get("overall", ""), str): raise ValueError("plan notes: overall is text")


def _atomic_write(path, text):
    d = os.path.dirname(path); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp): os.remove(tmp)
        raise


def write_notes(pr, d):
    """validate + write Edit/plan_notes.json atomically (temp file + rename); Approve all also records approval 2"""
    _check_notes(d)
    _atomic_write(pr.e("plan_notes.json"), json.dumps(d, indent=1, ensure_ascii=False))
    if d.get("approve_all"): record_approval(pr)
    return pr.e("plan_notes.json")


def read_notes(pr):
    p = pr.e("plan_notes.json")
    if not os.path.exists(p): raise SystemExit("no Edit/plan_notes.json: run `cves review-plan` and press Send (or save the copied notes there)")
    with open(p, encoding="utf-8") as f: return json.load(f)


def record_approval(pr):
    """approval 2 (the edit plan) with today's date in Edit/NOTES.md, once a day"""
    p = pr.e("NOTES.md"); line = f"- {today()}: Approval 2 (edit plan): approved in the plan review page (`cves review-plan`)."
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else "# Notes\n"
    if any("Approval 2" in l and today() in l for l in old.splitlines()): return p
    _atomic_write(p, old.rstrip("\n") + "\n" + line + "\n"); return p


# ------------------------------------------------------------------ locks
def load_lock(pr):
    p = pr.e("plan_lock.json")
    if not os.path.exists(p): return {"version": 1, "shots": {}}
    with open(p, encoding="utf-8") as f: d = json.load(f)
    d.setdefault("shots", {}); return d


def _locked_hashes(lock): return {h: k for k, v in lock["shots"].items() for h in (v.get("entries") or {}).values()}


def lock_shot(lock, E, shot):
    ents = {}
    for r in shot.get("refs", []):
        if r.get("slot") == "captions": continue
        x = find_entry(E, r)
        if x is not None: ents[ref_key(r)] = entry_hash(x)
    if ents: lock["shots"][shot["key"]] = {"entries": ents, "approved_at": today(), "n": shot.get("n")}
    return bool(ents)


def unlock_shot(lock, E, shot):
    hs = {entry_hash(x) for r in shot.get("refs", []) if r.get("slot") != "captions" for x in [find_entry(E, r)] if x is not None}
    for k in [k for k, v in lock["shots"].items() if k == shot.get("key") or hs & set((v.get("entries") or {}).values())]: del lock["shots"][k]


def is_unlock(shot): return bool(shot.get("unlock")) or (shot.get("note") or "").strip().lower().startswith("unlock")


# ------------------------------------------------------------------ edit.yaml text patch (comments kept where possible)
def _ind(l): return len(l) - len(l.lstrip(" "))


def _blank(l): s = l.strip(); return not s or s.startswith("#")


def _kind(l):
    """(indent of the key, key, inline value text) of a mapping line; a leading '- ' counts as indentation"""
    m = re.match(r"^(\s*(?:-\s+)*)([^\s#'\"{\[][^:#]*?|\"[^\"]*\"|'[^']*'):(\s|$)(.*)$", l)
    if not m: return None
    return len(m.group(1)), m.group(2).strip().strip("'\""), m.group(4)


def _trim(lines, i0, i1):
    while i1 > i0 + 1 and _blank(lines[i1 - 1]): i1 -= 1
    return i0, i1


def _children(lines, i0, i1, ind):
    """direct child key lines of a mapping whose keys sit at indent `ind` in [i0, i1): {key: (line, range end)}"""
    out = {}; keys = []
    for i in range(i0, i1):
        if _blank(lines[i]): continue
        k = _kind(lines[i])
        if k and k[0] == ind: keys.append((i, k[1]))
    for n, (i, k) in enumerate(keys):
        end = keys[n + 1][0] if n + 1 < len(keys) else i1
        out[k] = _trim(lines, i, end)
    return out


def _child_indent(lines, i0, i1):
    for i in range(i0, i1):
        if not _blank(lines[i]): return _ind(lines[i]) + (len(re.match(r"\s*((?:-\s+)*)", lines[i]).group(1)))
    return None


def _items(lines, i0, i1):
    """list item ranges of a block list in [i0, i1)"""
    starts = []; dash = None
    for i in range(i0, i1):
        if _blank(lines[i]): continue
        m = re.match(r"^(\s*)-(\s|$)", lines[i])
        if dash is None:
            if not m: return None
            dash = len(m.group(1))
        if m and len(m.group(1)) == dash: starts.append(i)
        elif _ind(lines[i]) <= dash: break
    return [_trim(lines, s, starts[n + 1] if n + 1 < len(starts) else i1) for n, s in enumerate(starts)]


def _flow(v):
    s = yaml.safe_dump([v], default_flow_style=True, width=10 ** 9, allow_unicode=True, sort_keys=False).strip()
    return s[1:-1].strip()


def _inline_span(line, start):
    """[a, b) of an inline value starting at or after column start (a scalar, quoted string or one-line flow collection)"""
    a = start
    while a < len(line) and line[a] in " \t": a += 1
    if a >= len(line) or line[a] == "#": return None
    if line[a] in "[{":
        depth, q, j = 0, None, a
        while j < len(line):
            ch = line[j]
            if q:
                if ch == q: q = None
            elif ch in "'\"": q = ch
            elif ch in "[{": depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0: return a, j + 1
            j += 1
        return None
    if line[a] in "'\"":
        j = line.find(line[a], a + 1); return (a, j + 1) if j > 0 else None
    m = re.search(r"\s+#", line[a:]); b = a + m.start() if m else len(line.rstrip())
    return a, b


def _set_inline(lines, i, value):
    l = lines[i]; m = re.match(r"^(\s*(?:-\s+)*)(.*?):", l)
    sp = _inline_span(l, m.end()) if m else None
    if not sp: return False
    lines[i] = l[:sp[0]] + _flow(value) + l[sp[1]:]; return True


def _patch_node(lines, i0, i1, ind, path, new_root, has_new):
    """apply new_root[path] (or delete it when has_new is False) inside the mapping at indent ind in [i0, i1)"""
    ch = _children(lines, i0, i1, ind); k = path[0]
    if k not in ch:
        if len(path) > 1: return False
        if not has_new: return True
        j = i1                                                           # add: after the last child line
        lines.insert(j, " " * ind + f"{_flow(k)}: {_flow(new_root[k])}"); return True
    a, b = ch[k]
    if len(path) == 1:
        if not has_new: del lines[a:b]; return True
        if _inline_span(lines[a], lines[a].index(":", _kind(lines[a])[0]) + 1): return _set_inline(lines, a, new_root[k])
        v = new_root[k]                                          # a block value: re-dump just this key, block style
        if not isinstance(v, (dict, list)) or not v: del lines[a + 1:b]; return _set_inline_after(lines, a, v)
        pre = lines[a][:ind] if re.match(r"^\s*-\s", lines[a]) else " " * ind
        body = yaml.safe_dump({k: v}, sort_keys=False, allow_unicode=True, width=140).rstrip("\n").split("\n")
        lines[a:b] = [pre + body[0]] + [" " * ind + x for x in body[1:]]; return True
    if _inline_span(lines[a], lines[a].index(":", _kind(lines[a])[0]) + 1): return _set_inline(lines, a, new_root[k])   # a flow value: rewrite it whole
    sub = new_root.get(k) if isinstance(new_root, dict) else None
    if isinstance(sub, (dict, list)) and not sub: del lines[a + 1:b]; return _set_inline_after(lines, a, sub)   # emptied: `key: {}`
    if isinstance(path[1], int):
        its = _items(lines, a + 1, b)
        if its is None or path[1] >= len(its) or not isinstance(sub, list): return False
        c0, c1 = its[path[1]]; item = sub[path[1]] if path[1] < len(sub) else None
        if len(path) == 2:
            if not has_new: del lines[c0:c1]; return True
            return _patch_item(lines, c0, c1, item)
        return _patch_in_item(lines, c0, c1, path[2:], item, has_new)
    ci = _child_indent(lines, a + 1, b)
    if ci is None or not isinstance(sub, dict): return False
    return _patch_node(lines, a + 1, b, ci, path[1:], sub, has_new)


def _set_inline_after(lines, a, v):
    l = lines[a]; m = re.match(r"^(.*?:)(\s*)(#.*)?$", l)
    if not m: return False
    lines[a] = m.group(1) + " " + _flow(v) + ("  " + m.group(3) if m.group(3) else ""); return True


def _patch_item(lines, c0, c1, item):
    """rewrite a whole list item (flow items in place, block items re-dumped at their indent)"""
    m = re.match(r"^(\s*-\s+)", lines[c0])
    if m and _inline_span(lines[c0], m.end()) and c1 == c0 + 1: lines[c0] = m.group(1) + _flow(item) + lines[c0][_inline_span(lines[c0], m.end())[1]:]; return True
    dash = len(re.match(r"^(\s*)", lines[c0]).group(1))
    body = yaml.safe_dump([item], sort_keys=False, allow_unicode=True, width=140).rstrip("\n").split("\n")
    lines[c0:c1] = [" " * dash + x for x in body]; return True


def _patch_in_item(lines, c0, c1, path, item, has_new):
    m = re.match(r"^(\s*-\s+)", lines[c0])
    if not m or not isinstance(item, dict): return False
    if _inline_span(lines[c0], m.end()) and lines[c0][m.end():].lstrip().startswith("{"): return _patch_item(lines, c0, c1, item)
    return _patch_node(lines, c0, c1, len(m.group(1)), path, item, has_new)


def _diff(a, b, path=()):
    """minimal changed paths a -> b: [(path, has_new)]; lists of mappings compare per item when the length holds"""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in list(a) + [k for k in b if k not in a]:
            if k not in b: out.append((path + (k,), False))
            elif k not in a: out.append((path + (k,), True))
            elif a[k] != b[k]: out += _diff(a[k], b[k], path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(isinstance(x, dict) for x in a + b):
        out = []
        for j, (x, y) in enumerate(zip(a, b)):
            if x != y: out += _diff(x, y, path + (j,))
        return out
    return [(path, True)]


def _item_key(x):
    if not isinstance(x, dict): return None
    k = x.get("id") if x.get("id") is not None else x.get("segment")
    return json.dumps(k, sort_keys=True) if k is not None else None


def _match_items(a, b):
    """(removed old indexes, [(old i, new i)]) when list b is list a with items removed and / or changed in place, matched by
    id / segment (else by equality); None when items were added or reordered"""
    if not (isinstance(a, list) and isinstance(b, list)) or len(b) > len(a): return None
    ka, kb = [_item_key(x) for x in a], [_item_key(x) for x in b]
    if None not in ka + kb and len(set(ka)) == len(ka) and len(set(kb)) == len(kb):
        pos = {k: i for i, k in enumerate(ka)}
        if not all(k in pos for k in kb): return None
        oi = [pos[k] for k in kb]
        if oi != sorted(oi): return None
        return [i for i in range(len(a)) if i not in set(oi)], list(zip(oi, range(len(b))))
    if len(a) == len(b): return [], [(i, i) for i in range(len(a))]
    out, pairs, j = [], [], 0
    for i, x in enumerate(a):
        if j < len(b) and x == b[j]: pairs.append((i, j)); j += 1
        else: out.append(i)
    return (out, pairs) if j == len(b) else None


def patch_text(text, E_old, E_new):
    """edit.yaml text for E_new that keeps the comments and layout of `text` (E_old) where it can; None if it cannot verify"""
    lines = text.split("\n")
    top = _children(lines, 0, len(lines), 0)
    for k in reversed(list(E_old) + [k for k in E_new if k not in E_old]):
        if k in E_old and k in E_new and E_old[k] == E_new[k]: continue
        if k not in E_new:
            if k not in top: return None
            a, b = top[k]; del lines[a:b]; continue
        if k not in E_old:
            body = yaml.safe_dump({k: E_new[k]}, sort_keys=False, allow_unicode=True, width=140).rstrip("\n")
            while lines and not lines[-1].strip(): lines.pop()
            lines += body.split("\n") + [""]; continue
        if k not in top: return None
        a, b = top[k]; old, new = E_old[k], E_new[k]
        m = _match_items(old, new) if isinstance(old, list) else None
        if m is not None:                                        # a list: items removed and / or changed in place
            its = _items(lines, a + 1, b)
            if its is None or len(its) != len(old): return None
            removed, pairs = m
            if not new: del lines[a + 1:b]; _set_inline_after(lines, a, []); top = _children(lines, 0, len(lines), 0); continue
            ops = sorted([(i, None) for i in removed] + [(oi, ni) for oi, ni in pairs if old[oi] != new[ni]], key=lambda o: -o[0])
            for oi, ni in ops:                                   # last item first: earlier ranges stay valid
                c0, c1 = its[oi]
                if ni is None: del lines[c0:c1]; continue
                for path, has_new in reversed(_diff(old[oi], new[ni])):
                    n0 = len(lines)
                    if not _patch_in_item(lines, c0, c1, path, new[ni], has_new): return None
                    c1 += len(lines) - n0
            top = _children(lines, 0, len(lines), 0)
            continue
        for path, has_new in reversed(_diff(old, new)):
            if not _patch_node(lines, a, b, 0, (k,) + path, E_new, has_new): return None
            top = _children(lines, 0, len(lines), 0); a, b = top[k]
        top = _children(lines, 0, len(lines), 0)
    out = "\n".join(lines)
    try: ok = yaml.safe_load(out) == E_new
    except yaml.YAMLError: ok = False
    return out if ok else None


def write_edit(pr, E_old, E_new, text):
    """backup, then the comment-keeping text patch when it verifies, else a re-dump. Returns (backup, how)"""
    src = pr.e("edit.yaml"); stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); bak = pr.e(f"edit.yaml.bak-{stamp}")
    n = 1
    while os.path.exists(bak): bak = pr.e(f"edit.yaml.bak-{stamp}-{n}"); n += 1
    shutil.copy2(src, bak)
    out = patch_text(text, E_old, E_new); how = "text patch (comments kept)"
    if out is None:
        out = yaml.safe_dump(E_new, sort_keys=False, allow_unicode=True, width=140); how = "re-dumped (comments lost; see the backup)"
    _atomic_write(src, out)
    return bak, how


# ------------------------------------------------------------------ apply-notes
def apply_notes(pr, force=False, dry_run=False):
    """Edit/plan_notes.json -> exact edit.yaml edits + Edit/plan_notes.pending.md (what Claude reads) + Edit/plan_lock.json"""
    d = read_notes(pr); _check_notes(d)
    if d.get("applied_at") and not force:
        raise SystemExit(f"Edit/plan_notes.json was applied at {d['applied_at']}: re-run `cves review-plan` for a new round (or --force)")
    src = pr.e("edit.yaml"); text = open(src, encoding="utf-8").read(); E = yaml.safe_load(text) or {}; En = copy.deepcopy(E)
    lock = load_lock(pr); unlocked = []
    for s in d["shots"]:
        if is_unlock(s) and (s.get("key") in lock["shots"] or _shot_locked(lock, E, s)):
            unlock_shot(lock, E, s); unlocked.append(s.get("key"))
    held = _locked_hashes(lock)
    applied, refused, for_claude, errors = [], [], [], []
    for s in d["shots"]:
        refs = s.get("refs") or []
        for a in s.get("actions") or []:
            if a["op"] == "fix_caption": r = {"slot": "captions"}
            else:
                ti = a.get("target", s.get("target", 0))
                r = refs[ti] if isinstance(ti, int) and 0 <= ti < len(refs) else None
                if r is None: errors.append((s, a, "no edit.yaml entry for this shot")); continue
                x0 = find_entry(E, r)
                if x0 is not None and r.get("slot") != "captions" and entry_hash(x0) in held:
                    refused.append((s, a, f"shot is locked (approved as {held[entry_hash(x0)]}): tick it off (unlock) to change it")); continue
            res = apply_action(En, r, a)
            if res.get("error"): errors.append((s, a, res["error"]))
            elif res.get("note"): for_claude.append((s, a, res["note"]))
            elif res["changed"]: applied.append((s, a, res["changes"]))
    locked = []
    for s in d["shots"]:
        if (s.get("approved") or d.get("approve_all")) and s.get("refs"):
            if lock_shot(lock, En, s): locked.append(s.get("key"))
    res = {"applied": [_row(s, a) for s, a, _ in applied], "refused": [_row(s, a, w) for s, a, w in refused],
           "for_claude": [_row(s, a, w) for s, a, w in for_claude], "errors": [_row(s, a, w) for s, a, w in errors],
           "locked": locked, "unlocked": unlocked, "backup": None, "how": None, "dry_run": dry_run}
    if dry_run: return res
    if En != E: res["backup"], res["how"] = write_edit(pr, E, En, text)
    lock["updated"] = _now(); _atomic_write(pr.e("plan_lock.json"), json.dumps(lock, indent=1, ensure_ascii=False))
    if d.get("approve_all"): record_approval(pr)
    res["pending"] = write_pending(pr, d, res)
    d["applied_at"] = _now(); _atomic_write(pr.e("plan_notes.json"), json.dumps(d, indent=1, ensure_ascii=False))
    return res


def _shot_locked(lock, E, s):
    held = _locked_hashes(lock)
    return [r for r in s.get("refs") or [] if r.get("slot") != "captions" and (lambda x: x is not None and entry_hash(x) in held)(find_entry(E, r))]


def _row(s, a, why=None):
    r = {"n": s.get("n"), "key": s.get("key"), "action": action_label(a)}
    if why: r["why"] = why
    return r


def write_pending(pr, d, res):
    """the free-text notes and the actions that need Claude, per shot (Claude reads only this)"""
    by = {}
    for kind in ("for_claude", "refused", "errors"):
        for r in res[kind]: by.setdefault(r["key"], []).append((kind, r))
    L = [f"# Plan notes for Claude ({today()})", "",
         f"Applied {len(res['applied'])} quick action(s) to Edit/edit.yaml" + (f" ({res['how']}; backup {os.path.basename(res['backup'])})" if res.get("backup") else "")
         + f"; {len(res['locked'])} shot(s) approved and locked" + (f"; unlocked: {', '.join(res['unlocked'])}" if res["unlocked"] else "") + "."]
    if d.get("approve_all"): L += ["", "**The editor approved the whole plan (approval 2, recorded in Edit/NOTES.md).**"]
    if (d.get("overall") or "").strip(): L += ["", "## Overall", "", d["overall"].strip()]
    rows = [s for s in d["shots"] if (s.get("note") or "").strip() or s.get("key") in by]
    L += ["", "## Shots", ""]
    if not rows: L.append("No free-text notes and nothing left for you: rebuild the plan (`cves moodboard`) and show it again.")
    tag = {"for_claude": "needs you", "refused": "refused (locked)", "errors": "not applied"}
    for s in rows:
        refs = ", ".join(ref_label(r) for r in s.get("refs") or [] if r.get("slot") != "captions") or "no edit.yaml entry"
        L.append(f"### #{s.get('n')} `{s.get('key')}` {float(s.get('start', 0)):.2f}-{float(s.get('end', 0)):.2f} s: {refs}")
        if s.get("label"): L.append(f"- on screen: {s['label']}")
        if (s.get("note") or "").strip(): L.append(f"- note: {s['note'].strip()}")
        for kind, r in by.get(s.get("key"), []): L.append(f"- {tag[kind]}: {r['action']}: {r['why']}")
        if s.get("frames") and (s.get("note") or "").strip(): L.append("- frames (open only if the note is visual): " + ", ".join(f"Moodboard/frames/{f:05d}.jpg" for f in s["frames"]))
        L.append("")
    L += ["Next: make the changes these notes ask for in edit.yaml (never touch a locked shot), then `cves moodboard` and `cves review-plan` again."]
    p = pr.e("plan_notes.pending.md"); _atomic_write(p, "\n".join(L).rstrip("\n") + "\n"); return p


# ------------------------------------------------------------------ plan data (built by moodboard from the timeline)
GLOBAL_SKIP = ("cutaways", "broll", "roto", "chest", "end_card", "music", "sfx", "transitions", "variants", "assets")


def global_sig(pr, TL):
    """what every frame depends on beyond its own shot: the look, canvas, plates, engine and the non-shot edit keys"""
    E = TL.E; g = {k: v for k, v in E.items() if k not in GLOBAL_SKIP}
    cap = dict(g.get("captions") or {}); cap.pop("fixes", None); g["captions"] = cap
    ar = dict(g.get("aroll") or {}); ar.pop("zoom", None); g["aroll"] = ar
    from . import __version__
    tdirs = [os.path.join(os.path.dirname(__file__), "templates"), os.path.join(os.path.dirname(__file__), "motion"), pr.p("Brand", "templates")]
    mt = max([os.path.getmtime(os.path.join(dd, f)) for dd in tdirs if os.path.isdir(dd) for f in os.listdir(dd)] + [0])
    S = {k: v for k, v in (TL.S or {}).items() if not str(k).startswith("_")}
    return entry_hash({"edit": g, "style": S, "edl": pr.json("edl.json", {}), "size": list(TL.size), "v": __version__, "t": mt,
                       "assets": pr.json("assets.json", {})})


def shot_hash(E, sh):
    ents = [find_entry(E, r) for r in sh.get("refs", []) if r.get("slot") != "captions"]
    return entry_hash({"kind": sh.get("kind"), "t": [round(float(sh.get("start", 0)), 3), round(float(sh.get("end", 0)), 3)], "entries": ents,
                       "captions": sh.get("captions", []), "trans": sh.get("trans"), "snap": sh.get("snap")})


def shot_refs(E, TL, sh):
    """the edit.yaml entries a moodboard shot came from: [refs], targets (indexes Bigger / Swap / ... act on)"""
    refs = []; k = sh["kind"]
    if k == "cutaway":
        cid = str(sh["cut"].get("id")); L = E.get("cutaways") or []
        j = next((j for j, x in enumerate(L) if str(x.get("id")) == cid), None)
        if j is not None: refs.append(ref_for(E, "cutaways", j))
    elif k == "broll":
        bid = str(sh["cut"].get("id")); L = E.get("broll") or []
        j = next((j for j, x in enumerate(L) if broll_id(x, j) == bid), None)
        if j is not None: refs.append(ref_for(E, "broll", j))
    elif k == "aroll":
        sid = sh["seg"]["id"]
        for slot in ("roto", "chest"):
            for j, x in enumerate(E.get(slot) or []):
                segs = [x.get("segment")] if isinstance(x.get("segment"), str) else (x.get("segment") or [])
                if sid in segs: refs.append(ref_for(E, slot, j))
        refs.append(ref_for(E, "zoom", segment=sid, zoom=sh.get("zoom", 1.0)))
    elif k == "end" and E.get("end_card"): refs.append(ref_for(E, "end_card"))
    if k in ("aroll", "broll", "gap") and sh.get("captions"): refs.append(ref_for(E, "captions"))
    return refs


def shot_key(sh, refs, seen):
    k = sh["kind"]
    base = {"cutaway": f"cutaways:{sh.get('cut', {}).get('id')}", "broll": f"broll:{sh.get('cut', {}).get('id')}", "end": "end_card",
            "aroll": f"aroll:{(sh.get('seg') or {}).get('id')}", "gap": f"gap:{(sh.get('seg') or {}).get('id')}"}.get(k, k)
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base}#{seen[base]}"


def plan_data(pr, TL, S, describe):
    """per shot: key, refs (edit.yaml), quick-action options, hash, frames. moodboard adds changed / locked"""
    E = TL.E; seen = {}; out = []; lock = load_lock(pr); held = _locked_hashes(lock)
    for n, sh in enumerate(S, 1):
        refs = shot_refs(E, TL, sh); key = shot_key(sh, refs, seen)
        targets = [i for i, r in enumerate(refs) if r["slot"] != "captions"]
        swap, sizable, shiftable, removable = {}, {}, {}, {}
        for i in targets:
            r = refs[i]; x = find_entry(E, r) or {}
            swap[str(i)] = [t for t in valid_templates(r["slot"]) if t != x.get("template")] if r["slot"] in SLOT_KINDS else []
            sizable[str(i)] = r["slot"] == "zoom" or (r["slot"] != "broll" and bool(size_param(x.get("template"))))
            shiftable[str(i)] = r["slot"] in ("cutaways", "broll", "roto", "chest")
            removable[str(i)] = r["slot"] not in ("zoom",)
        d = {"n": n, "key": key, "kind": sh["kind"], "start": round(sh["start"], 3), "end": round(sh["end"], 3), "label": describe(sh).replace("`", ""),
             "refs": refs, "targets": targets, "target": targets[0] if targets else 0, "swap": swap, "sizable": sizable, "shiftable": shiftable,
             "removable": removable, "captions": sh.get("captions", []), "frames": sh.get("frames", []), "trans": [sh.get("trans_in"), sh.get("trans_out")],
             "snap": list(sh["snap"]) if sh.get("snap") else None}
        d["hash"] = shot_hash(E, d)
        lk = lock["shots"].get(key)
        d["locked"] = any(r.get("hash") in held for r in refs if r.get("slot") != "captions")
        d["lock_broken"] = bool(lk) and not d["locked"]          # approved, then its entry changed without an unlock note
        out.append(d)
    return out


def changed_shots(prev, cur, gsig, have):
    """(keys whose shot changed since the last round, frames whose jpg can be reused). prev: the last plan_state.json;
    cur: {key: {hash, frames}}; have: frame numbers with a jpg on disk. A new global signature reuses nothing."""
    if not prev: return set(), set()
    ps = prev.get("shots") or {}
    changed = {k for k, v in cur.items() if k not in ps or ps[k].get("hash") != v["hash"]}
    if prev.get("sig") != gsig: return changed, set()
    reuse = set()
    for k, v in cur.items():
        if k in changed or ps[k].get("frames") != v["frames"]: continue
        reuse |= {f for f in v["frames"] if f in have}
    return changed, reuse


# ------------------------------------------------------------------ page (added to EDIT-PLAN.html by moodboard)
CSS = """
.rv{border-top:1px solid var(--line);margin-top:8px;padding-top:8px;display:grid;gap:6px}
.rv .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.rv button,.bar button{background:#1d2622;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 10px;font:inherit;cursor:pointer}
.rv button:hover,.bar button:hover{border-color:var(--acc)} .rv button[disabled],.bar button[disabled]{opacity:.45;cursor:not-allowed}
.rv button.note{border-style:dashed} .rv select,.rv input,.rv textarea,.bar textarea{background:#0b0f0d;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 8px;font:inherit}
.rv textarea,.bar textarea{width:100%;box-sizing:border-box;min-height:42px;resize:vertical} .rv input{width:120px}
.rv label.ok{font-weight:600} .rv .acts{color:var(--acc);font-size:12px} .rv .acts span{background:#15302a;border-radius:10px;padding:1px 8px;margin-right:4px;cursor:pointer}
.badge{border-radius:10px;padding:1px 8px;font-size:12px;margin-left:6px} .badge.chg{background:#5a3b12;color:#ffd38a} .badge.lck{background:#173f30;color:#8ff0c8}
.badge.brk{background:#5a1a22;color:#ffb3bd} .shot.approved{border-left-color:var(--acc);opacity:.92}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;margin:14px 0;display:grid;gap:8px}
.bar .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center} .bar .st{color:var(--mut);font-size:12px} .bar button.pri{background:var(--acc);color:#0b0f0d;border-color:var(--acc);font-weight:600}
"""


def _e(s): return html.escape(str(s), quote=True)


def badges(shot):
    b = ""
    if shot.get("changed"): b += '<span class="badge chg">changed since last round</span>'
    if shot.get("locked"): b += '<span class="badge lck">locked (approved)</span>'
    if shot.get("lock_broken"): b += '<span class="badge brk">approved, then changed without an unlock note</span>'
    return b


def card_controls(shot):
    """the per-shot review controls: Approve, quick actions, Fix caption, note"""
    n = shot["n"]; refs = shot.get("refs") or []; targets = shot.get("targets", [i for i, r in enumerate(refs) if r.get("slot") != "captions"])
    t0 = str(targets[0]) if targets else None
    def flag(name, default):
        return bool((shot.get(name) or {}).get(t0, default)) if t0 is not None else False
    sl = refs[int(t0)]["slot"] if t0 is not None else None
    can_size = flag("sizable", False); can_shift = flag("shiftable", sl in ("cutaways", "broll", "roto", "chest")); can_rm = flag("removable", sl != "zoom")
    swaps = (shot.get("swap") or {}).get(t0, []) if t0 is not None else []
    tsel = ""
    if len(targets) > 1:
        tsel = f'<select class="tgt" id="target-{n}" aria-label="what the actions change">' + "".join(
            f'<option value="{i}">{_e(ref_label(refs[i]))}</option>' for i in targets) + "</select>"
    dis = lambda ok: "" if ok else " disabled"
    size_cls = "" if can_size else " note"
    size_tip = "scales its size param" if can_size else "no size param: goes to Claude as a note"
    btn = lambda op, label, ok, cls="", tip="": f'<button type="button" data-op="{op}" data-n="{n}" class="{cls.strip()}" title="{_e(tip)}"{dis(ok)}>{label}</button>'
    acts = (btn("bigger", "Bigger", t0 is not None, size_cls, size_tip) + btn("smaller", "Smaller", t0 is not None, size_cls, size_tip)
            + btn("earlier", f"Earlier {STEP_S:.2f} s", can_shift) + btn("later", f"Later {STEP_S:.2f} s", can_shift) + btn("remove", "Remove", can_rm))
    sw = (f'<select id="swap-{n}" data-n="{n}" aria-label="swap template"{dis(bool(swaps))}><option value="">Swap template…</option>'
          + "".join(f'<option value="{_e(t)}">{_e(t)}</option>' for t in swaps) + "</select>") if t0 is not None else ""
    fix = (f'<input id="fixfrom-{n}" placeholder="caption word"> → <input id="fixto-{n}" placeholder="should read">'
           f'<button type="button" data-op="fix_caption" data-n="{n}">Fix caption</button>') if any(r.get("slot") == "captions" for r in refs) else ""
    chk = " checked" if shot.get("locked") else ""
    return (f'<div class="rv" data-n="{n}"><div class="row"><label class="ok"><input type="checkbox" id="approve-{n}" data-n="{n}"{chk}> Approve</label>{badges(shot)}'
            f'{tsel}{acts}{sw}</div>' + (f'<div class="row">{fix}</div>' if fix else "")
            + f'<div class="acts" id="acts-{n}"></div><textarea id="note-{n}" data-n="{n}" placeholder="Note for Claude on shot #{n}"></textarea></div>')


def page_controls(P):
    return ('<div class="bar" id="review"><div class="row"><b>Review</b><span class="st" id="status"></span></div>'
            '<textarea id="overall" placeholder="Overall note for Claude (pacing, look, anything not tied to one shot)"></textarea>'
            '<div class="row"><button type="button" class="pri" id="send">Send to Claude</button><button type="button" id="approve-all">Approve all</button>'
            '<button type="button" id="copy">Copy notes</button><span class="st" id="counts"></span></div></div>')


def embed(P):
    s = json.dumps(P, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/json" id="plan-data">{s}</script>'


SCRIPT = r"""
(function () {
  const P = JSON.parse(document.getElementById('plan-data').textContent);
  const served = location.protocol === 'http:' && /^(127\.0\.0\.1|localhost)$/.test(location.hostname);
  const st = document.getElementById('status'), counts = document.getElementById('counts');
  const send = document.getElementById('send'), copy = document.getElementById('copy'), all = document.getElementById('approve-all');
  const acts = {}; let approveAll = false;
  P.shots.forEach(s => acts[s.n] = []);
  const byN = {}; P.shots.forEach(s => byN[s.n] = s);
  const $ = id => document.getElementById(id);
  const label = a => ({bigger: 'Bigger', smaller: 'Smaller', earlier: 'Earlier', later: 'Later', remove: 'Remove'})[a.op]
    || (a.op === 'swap' ? 'Swap → ' + a.template : a.op === 'fix_caption' ? 'Fix "' + a.from + '" → "' + a.to + '"' : a.op);
  function target(n) { const t = $('target-' + n); return t ? parseInt(t.value, 10) : byN[n].target; }
  function draw(n) {
    const el = $('acts-' + n); el.textContent = '';
    acts[n].forEach((a, i) => { const s = document.createElement('span'); s.textContent = label(a) + ' ×'; s.title = 'remove this action';
      s.onclick = () => { acts[n].splice(i, 1); draw(n); tally(); }; el.appendChild(s); });
  }
  function add(n, a) { a.target = target(n); acts[n].push(a); draw(n); tally(); }
  function notes() {
    return {version: P.version, title: P.title, round: P.round, plan_sig: P.sig, created: new Date().toISOString(),
      overall: $('overall').value, approve_all: approveAll,
      shots: P.shots.map(s => ({n: s.n, key: s.key, kind: s.kind, start: s.start, end: s.end, label: s.label, refs: s.refs,
        target: target(s.n), frames: s.frames, approved: $('approve-' + s.n).checked,
        unlock: !!s.locked && !$('approve-' + s.n).checked, note: $('note-' + s.n).value, actions: acts[s.n]}))};
  }
  function tally() {
    const d = notes(); const a = d.shots.filter(s => s.approved).length, q = d.shots.reduce((k, s) => k + s.actions.length, 0),
      t = d.shots.filter(s => s.note.trim()).length;
    counts.textContent = a + '/' + d.shots.length + ' approved · ' + q + ' quick action(s) · ' + t + ' note(s)';
    P.shots.forEach(s => { const c = $('approve-' + s.n).closest('.shot'); if (c) c.classList.toggle('approved', $('approve-' + s.n).checked); });
  }
  document.querySelectorAll('button[data-op]').forEach(b => b.addEventListener('click', () => {
    const n = parseInt(b.dataset.n, 10), op = b.dataset.op;
    if (op === 'fix_caption') {
      const f = $('fixfrom-' + n).value.trim(), t = $('fixto-' + n).value.trim();
      if (!f || !t) { st.textContent = 'Fix caption needs the word and what it should read'; return; }
      add(n, {op: op, from: f, to: t}); $('fixfrom-' + n).value = ''; $('fixto-' + n).value = ''; return;
    }
    add(n, (op === 'earlier' || op === 'later') ? {op: op, step: 0.25} : {op: op});
  }));
  document.querySelectorAll('select[id^="swap-"]').forEach(s => s.addEventListener('change', () => {
    if (s.value) { add(parseInt(s.dataset.n, 10), {op: 'swap', template: s.value}); s.value = ''; }
  }));
  document.querySelectorAll('select.tgt').forEach(s => s.addEventListener('change', () => {
    const n = parseInt(s.id.split('-')[1], 10), sh = byN[n], t = String(s.value);
    const box = s.closest('.rv');
    box.querySelectorAll('button[data-op="bigger"],button[data-op="smaller"]').forEach(b => b.classList.toggle('note', !(sh.sizable || {})[t]));
    box.querySelectorAll('button[data-op="earlier"],button[data-op="later"]').forEach(b => b.disabled = !(sh.shiftable || {})[t]);
    box.querySelectorAll('button[data-op="remove"]').forEach(b => b.disabled = !(sh.removable || {})[t]);
    const sw = $('swap-' + n); if (sw) { sw.length = 1; ((sh.swap || {})[t] || []).forEach(v => sw.add(new Option(v, v))); sw.disabled = sw.length < 2; }
  }));
  document.querySelectorAll('input[id^="approve-"], textarea').forEach(e => e.addEventListener('input', tally));
  function post() {
    if (!served) return;
    send.disabled = true; st.textContent = 'Sending…';
    fetch('/notes', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(notes())})
      .then(r => r.ok ? r.json() : r.text().then(t => Promise.reject(t)))
      .then(() => { st.textContent = 'Saved to Edit/plan_notes.json. Tell Claude, or close this tab: Claude applies the notes next.'; })
      .catch(e => { st.textContent = 'Not saved: ' + e + ' (use Copy notes)'; send.disabled = false; });
  }
  send.addEventListener('click', post);
  all.addEventListener('click', () => { approveAll = true; P.shots.forEach(s => $('approve-' + s.n).checked = true); tally();
    if (served) post(); else st.textContent = 'All shots approved: use Copy notes and give the text to Claude.'; });
  copy.addEventListener('click', () => {
    const t = JSON.stringify(notes(), null, 1);
    const done = () => st.textContent = 'Notes copied: paste them to Claude (it saves them as Edit/plan_notes.json).';
    if (navigator.clipboard && window.isSecureContext !== false) navigator.clipboard.writeText(t).then(done, () => fallback(t, done));
    else fallback(t, done);
  });
  function fallback(t, done) { const a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select();
    try { document.execCommand('copy'); done(); } catch (e) { st.textContent = 'Copy failed: select the notes by hand'; } a.remove(); }
  if (!served) { send.disabled = true; send.title = 'Opened as a file: run `cves review-plan` to send, or use Copy notes';
    st.textContent = 'Read-only (opened as a file): Send needs `cves review-plan`; Copy notes still works.'; }
  else st.textContent = 'Connected to cves review-plan: Send saves your notes on this Mac only.';
  tally();
})();
"""


def review_block(P):
    """(css, top bar, per-shot controls by n, tail = data + script) for EDIT-PLAN.html"""
    return CSS, page_controls(P), {s["n"]: card_controls(s) for s in P["shots"]}, embed(P) + "<script>" + SCRIPT + "</script>"


# ------------------------------------------------------------------ server (stdlib only, 127.0.0.1 only)
LOCAL_HOSTS = ("127.0.0.1", "localhost")
MAX_BODY = 4 * 1024 * 1024


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(pr, port=0, host="127.0.0.1"):
    """an HTTP server on 127.0.0.1 that serves Moodboard/ and accepts POST /notes -> Edit/plan_notes.json"""
    if host not in LOCAL_HOSTS: raise ValueError(f"the plan review server binds to 127.0.0.1 only, not {host!r}")
    root = pr.p("Moodboard"); os.makedirs(root, exist_ok=True)

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw): super().__init__(*a, directory=root, **kw)

        def log_message(self, *a): pass

        def _host_ok(self):
            h = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            return h in LOCAL_HOSTS

        def _origin_ok(self):
            o = self.headers.get("Origin")
            if o is None: return True                    # a non-browser local client (curl, Python)
            port_ = self.server.server_address[1]
            return o in (f"http://127.0.0.1:{port_}", f"http://localhost:{port_}")

        def _json(self, code, d):
            b = json.dumps(d, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            if not self._host_ok(): return self._json(403, {"error": "host not allowed"})
            if self.path.split("?")[0] == "/notes":
                p = pr.e("plan_notes.json")
                return self._json(200, json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {})
            if self.path.split("?")[0] == "/": self.path = "/EDIT-PLAN.html"
            return super().do_GET()

        def do_HEAD(self):
            if not self._host_ok(): return self._json(403, {"error": "host not allowed"})
            return super().do_HEAD()

        def do_POST(self):
            if not self._host_ok() or not self._origin_ok(): return self._json(403, {"error": "only this Mac's own page may send notes"})
            if self.path.split("?")[0] != "/notes": return self._json(404, {"error": "not found"})
            if "json" not in (self.headers.get("Content-Type") or ""): return self._json(415, {"error": "send application/json"})
            try: n = int(self.headers.get("Content-Length") or 0)
            except ValueError: n = -1
            if n <= 0 or n > MAX_BODY: return self._json(413, {"error": "empty or too large"})
            try: d = json.loads(self.rfile.read(n).decode("utf-8")); write_notes(pr, d)
            except (ValueError, UnicodeDecodeError) as e: return self._json(400, {"error": str(e)})
            self.server.notes_saved.set()
            return self._json(200, {"saved": True, "path": pr.e("plan_notes.json")})

        def do_PUT(self): self._json(405, {"error": "method not allowed"})
        do_DELETE = do_PUT

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff"); super().end_headers()

    srv = _Server(("127.0.0.1", port), H); srv.notes_saved = threading.Event()
    return srv


def stale(pr):
    """True when EDIT-PLAN.html is missing, predates the review controls, or is older than what it is built from"""
    h = pr.p("Moodboard", "EDIT-PLAN.html")
    if not os.path.exists(h): return True
    with open(h, encoding="utf-8") as f:
        if 'id="plan-data"' not in f.read(): return True
    t = os.path.getmtime(h)
    srcs = [pr.e(x) for x in ("edit.yaml", "edl.json", "words.json", "style.yaml", "treatment.yaml", "selects.yaml")] + [pr.p("Brand", "style.yaml")]
    return any(os.path.exists(s) and os.path.getmtime(s) > t for s in srcs)


def serve(pr, port=PORT, open_browser=True, keep=False, build=True):
    """`cves review-plan`: build the plan if stale, serve it on 127.0.0.1, stop after the first Send unless keep"""
    if build and stale(pr):
        from .moodboard import moodboard
        s, k = moodboard(pr); print(f"edit plan rebuilt: {s} shots, {k} keyframes")
    try: srv = make_server(pr, port)
    except OSError:
        if port == PORT: srv = make_server(pr, 0)        # the default port is taken: any free one
        else: raise SystemExit(f"port {port} is in use: pick another with --port")
    url = f"http://127.0.0.1:{srv.server_address[1]}/EDIT-PLAN.html"
    print(f"plan review: {url}  (127.0.0.1 only; Ctrl-C stops)" + ("" if keep else "; stops after the editor presses Send"), flush=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    saved = 0
    try:
        while th.is_alive():
            if srv.notes_saved.wait(.5):
                saved += 1; srv.notes_saved.clear()
                print(f"notes saved -> {pr.e('plan_notes.json')}", flush=True)
                if not keep: break
    except KeyboardInterrupt: pass
    finally:
        srv.shutdown(); srv.server_close()
    if saved: print("  next: `cves plan apply-notes`, then read Edit/plan_notes.pending.md only")
    else: print("stopped before Send: no notes saved")
    return 0


def print_apply(r):
    for x in r["applied"]: print(f"  applied   #{x['n']} {x['key']}: {x['action']}")
    for x in r["refused"]: print(f"  REFUSED   #{x['n']} {x['key']}: {x['action']} ({x['why']})")
    for x in r["errors"]: print(f"  invalid   #{x['n']} {x['key']}: {x['action']} ({x['why']})")
    for x in r["for_claude"]: print(f"  for you   #{x['n']} {x['key']}: {x['action']} ({x['why']})")
    if r["locked"]: print(f"  locked {len(r['locked'])} approved shot(s); unlocked {len(r['unlocked'])}")
    if r.get("backup"): print(f"  edit.yaml: {r['how']}; backup {r['backup']}")
    if r.get("pending"): print(f"  read {r['pending']} (only this), then `cves moodboard` + `cves review-plan`")
