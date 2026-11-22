"""`cves status [--json]`: one screen that tells Claude where a project is, without reading several files.

The stage is read from what is on disk (docs/ARCHITECTURE.md §3): transcript, selects, edl, words / plate, edit.yaml,
the moodboard, the master in Export/ and the delivered Export/vNNN/ folders. It prints approvals noted in Edit/NOTES.md
and the next command to run. Read-only: it never runs a step."""
import glob, hashlib, json, os, re

def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def _load(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def _mt(p): return os.path.getmtime(p) if os.path.exists(p) else 0.0

def _master(pr):
    d = pr.p("Export")
    if not os.path.isdir(d): return None
    v = sorted((os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".mp4")), key=os.path.getmtime)
    return v[-1] if v else None

def collect(pr):
    """facts + stage + next command (a dict; `report` formats it)"""
    from . import spines as SP
    E = pr.edit or {}
    spine = SP.spine_of(E); aroll = spine == "aroll"
    ex = lambda *a: os.path.exists(pr.e(*a))
    st = {"project": pr.root, "spine": spine, "title": E.get("title") or os.path.basename(pr.root.rstrip(os.sep)), "done": [], "todo": []}
    planned = any(E.get(k) for k in ("cutaways", "roto", "chest", "broll")) or isinstance(E.get("end_card"), dict) and bool(E["end_card"].get("template"))
    steps = [("ingest", ex("raw_transcript.txt") or (not aroll and ex("edl.json")), "cves ingest"),
             ("story", ex("selects.yaml") or not aroll, "cves story  (then write Edit/selects.yaml, `text:` on every clip)"),
             ("select", ex("edl.json") and (ex("voice_final.wav") or not aroll), "cves select"),
             ("prep", (ex("words.json") and os.path.isdir(pr.e("plate"))) or not aroll, "cves prep"),
             ("plan", planned, "cves plan  (fill edit.yaml from `cves templates`, then `cves plan`)"),
             ("moodboard", os.path.exists(pr.p("Moodboard", "EDIT-PLAN.html")), "cves moodboard")]
    nxt = None
    last = len(steps) if _master(pr) else max((i for i, (_, ok, _) in enumerate(steps) if ok), default=-1)   # later work implies earlier steps
    steps = [(n, ok or i < last, c) for i, (n, ok, c) in enumerate(steps)]
    for name, ok, cmd in steps:
        if ok: st["done"].append(name)
        elif nxt is None: nxt = cmd; st["stage"] = name
    # approvals the skill records in NOTES.md
    notes = pr.e("NOTES.md"); st["approvals"] = []
    if os.path.exists(notes):
        with open(notes, encoding="utf-8", errors="replace") as f:
            st["approvals"] = [l.strip()[:110] for l in f if re.search(r"approv", l, re.I)][-3:]
    m = _master(pr); st["master"] = m and os.path.relpath(m, pr.root)
    vers = sorted(d for d in glob.glob(pr.p("Export", "v[0-9][0-9][0-9]*")) if os.path.isdir(d))
    st["delivered"] = [os.path.basename(v) for v in vers][-3:]
    if nxt is None:
        st["stage"] = "render"
        msha = _sha(m) if m else None
        man = _load(os.path.join(vers[-1], "manifest.json")) if vers else None
        if not m or (os.path.exists(pr.e("edit.yaml")) and _mt(pr.e("edit.yaml")) > _mt(m)):
            nxt = "cves build" + ("  (edit.yaml changed since the last master)" if m else "")
        elif not man or man.get("master_sha256") != msha:
            st["stage"] = "deliver"; nxt = "cves deliver"
        else:
            st["stage"] = "delivered"; nxt = f"delivered {os.path.basename(vers[-1])}"
    st["next"] = nxt
    return st

def report(st):
    L = [f"{st['title']}  [{st['spine']}]  stage: {st['stage']}", f"  done: {', '.join(st['done']) or '-'}"]
    if st.get("approvals"): L.append("  approvals (NOTES.md): " + " | ".join(st["approvals"]))
    if st.get("master"): L.append(f"  master: {st['master']}")
    if st.get("delivered"): L.append(f"  delivered: {', '.join(st['delivered'])}")
    L.append(f"next: {st['next']}")
    return "\n".join(L)
