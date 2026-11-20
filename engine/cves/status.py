"""`cves status [--json]`: one screen that tells Claude where a project is, without reading several files.

The stage is read from what is on disk (docs/ARCHITECTURE.md §3): transcript, selects, edl, words / plate, edit.yaml,
the moodboard, the master in Export/, Edit/qc.json (and whether it judged this master), the critique pack, the review
rounds and sign-off, and the delivered Export/vNNN/ folders. It prints the last QC counts, the open FAILs, approvals noted
in Edit/NOTES.md, and the next command to run. Read-only: it never runs a step."""
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
             ("select", ex("edl.json") and (ex("voice_final.wav") or not aroll), "cves select  (then `cves qc --stage story`; show the cut list: approval 1)"),
             ("prep", (ex("words.json") and os.path.isdir(pr.e("plate"))) or not aroll, "cves prep"),
             ("plan", planned, "cves plan  (fill edit.yaml from `cves templates`, then `cves plan` + `cves qc --stage plan`)"),
             ("moodboard", os.path.exists(pr.p("Moodboard", "EDIT-PLAN.html")), "cves moodboard  (show EDIT-PLAN.html: approval 2)")]
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
    q = _load(pr.e("qc.json")); qc_ok_for_master = False
    if q:
        st["qc"] = {k: q.get(k) for k in ("fail", "warn", "pass", "na", "fast", "created")}
        st["qc"]["video"] = os.path.basename(q.get("video") or "")
        st["open_fails"] = [{"id": g["id"], "summary": g.get("summary", "")} for g in q.get("gates") or [] if g.get("status") == "FAIL"]
        if m and os.path.abspath(q.get("video") or "") == os.path.abspath(m):
            qc_ok_for_master = q.get("size") == os.path.getsize(m) and q.get("sha256") == _sha(m)
        st["qc"]["current"] = qc_ok_for_master
    rv = _load(pr.e("review", "state.json")) or {}
    rounds = rv.get("rounds") or []
    last_hist = (rv.get("history") or [None])[-1]
    if rounds: r = rounds[-1]; st["review"] = {"round": r["n"], "dir": r["dir"], "counts": r.get("counts"), "high": r.get("high"), "signed": None}
    elif last_hist and last_hist.get("rounds"):
        r = last_hist["rounds"][-1]; st["review"] = {"round": r["n"], "dir": r["dir"], "counts": r.get("counts"), "high": r.get("high"), "signed": last_hist.get("verdict")}
    else: r = None
    rv_sha = r and r.get("sha256")
    cq = pr.e("critique", "critique.json")
    vers = sorted(d for d in glob.glob(pr.p("Export", "v[0-9][0-9][0-9]*")) if os.path.isdir(d))
    st["delivered"] = [os.path.basename(v) for v in vers][-3:]
    if nxt is None:
        st["stage"] = "render"
        msha = _sha(m) if m else None
        man = _load(os.path.join(vers[-1], "manifest.json")) if vers else None
        if not m or (os.path.exists(pr.e("edit.yaml")) and _mt(pr.e("edit.yaml")) > _mt(m)):
            nxt = "cves build" + ("  (edit.yaml changed since the last master)" if m else "")
        elif not q or not qc_ok_for_master or q.get("fast"):
            st["stage"] = "qc"; nxt = "cves qc" + ("  (the last QC judged another file, or was --fast)" if q else "")
        elif q.get("fail"):
            st["stage"] = "qc"; nxt = f"fix the {q['fail']} FAIL(s) in edit.yaml, re-render what changed, `cves qc`"
        elif _mt(cq) < _mt(m):
            st["stage"] = "critique"; nxt = "cves critique  (fill CRITIQUE.md, log scores with `cves learn rate ... --by claude`)"
        elif not r or rv_sha != msha:
            st["stage"] = "review"; nxt = "cves review build  (then read REVIEW.md and the images it lists)"
        elif rounds and (r.get("counts") or {}).get("high"):
            st["stage"] = "review"; nxt = f"fix the high finding(s) {', '.join(r.get('high') or [])} (`cves review apply` for safe patches), rebuild, `cves review build`"
        elif rounds:
            st["stage"] = "review"; nxt = "cves review signoff --verdict ship|revise --notes \"...\""
        elif not man or man.get("master_sha256") != msha:
            st["stage"] = "deliver"; nxt = "cves deliver"
        else:
            st["stage"] = "delivered"; nxt = f"delivered {os.path.basename(vers[-1])}: ask for a rating (`cves learn rate`), take notes (/cves:notes)"
    st["next"] = nxt
    return st

def report(st):
    L = [f"{st['title']}  [{st['spine']}]  stage: {st['stage']}", f"  done: {', '.join(st['done']) or '-'}"]
    if st.get("approvals"): L.append("  approvals (NOTES.md): " + " | ".join(st["approvals"]))
    if st.get("master"): L.append(f"  master: {st['master']}")
    q = st.get("qc")
    if q:
        L.append(f"  last QC: {q['fail']} FAIL  {q['warn']} WARN  {q['pass']} PASS  {q.get('na') or 0} N/A  on {q['video']}"
                 + ("" if q.get("current") else "  (not this master)") + ("  [fast]" if q.get("fast") else ""))
        for g in (st.get("open_fails") or [])[:8]: L.append(f"    FAIL {g['id']}: {' '.join(g['summary'].split())[:120]}")
        if len(st.get("open_fails") or []) > 8: L.append(f"    (+{len(st['open_fails']) - 8} more: `cves qc --json`)")
    rv = st.get("review")
    if rv:
        c = rv.get("counts") or {}
        L.append(f"  review: round {rv['round']} ({rv['dir']}) {c.get('high', 0)} high {c.get('med', 0)} med {c.get('low', 0)} low"
                 + (f"; signed off: {rv['signed']}" if rv.get("signed") else ""))
    if st.get("delivered"): L.append(f"  delivered: {', '.join(st['delivered'])}")
    L.append(f"next: {st['next']}")
    return "\n".join(L)
