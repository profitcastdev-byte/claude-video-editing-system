"""CVES QC guard (Claude Code hook). Standard library only; runs under python3 or python, on Mac and Windows.

PreToolUse (Bash): BLOCKS
  - copying, moving or uploading anything out of a project's Export/ folder (cp, mv, rsync, scp, rclone, ditto, robocopy,
    copy/move/xcopy, gh release create|upload, curl -T / --upload-file / -F @file, aws s3 cp/sync, gsutil cp) unless the file
    is QC-clean: Edit/qc.json exists, has fail == 0 and its sha256 matches the master; files inside a delivered Export/vNNN/
    are fine when that folder's manifest.json says qc_verified and the master still matches it;
  - `cves deliver --force-unchecked` while Edit/qc.json is missing, failing or stale.
  It answers {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": ...}}.
PostToolUse (Bash): reminds Claude to run `cves qc` after render/mix/encode and surfaces a QC FAIL count (never blocks).
Any error inside the guard itself lets the command through (a broken guard must not wedge the session)."""
import hashlib, json, os, re, shlex, sys

COPY = re.compile(r"(^|[\s;&|(])(cp|mv|rsync|scp|rclone|ditto|robocopy|xcopy|copy|move|install|gsutil|aws\s+s3|gh\s+release\s+(create|upload)|curl|wget)\b", re.I)
UPLOAD_CURL = re.compile(r"\bcurl\b.*(\s-T\s|\s--upload-file\b|\s-F\s*\S*=@|\s--form\s*\S*=@|\s--data-binary\s+@)", re.I)


def out(event, **kw):
    print(json.dumps({"hookSpecificOutput": dict({"hookEventName": event}, **kw)})); sys.exit(0)


def deny(reason):
    out("PreToolUse", permissionDecision="deny", permissionDecisionReason="CVES QC guard: " + reason)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return None


def project_of(path):
    """the project root for a path inside <root>/Export/..., or a folder that has Edit/"""
    p = os.path.abspath(path)
    parts = p.split(os.sep)
    for i in range(len(parts) - 1, 0, -1):
        if parts[i] == "Export": return os.sep.join(parts[:i]) or os.sep
    return p if os.path.isdir(os.path.join(p, "Edit")) else None


def stamp_problem(root, video=None):
    """None if Edit/qc.json is clean for `video` (or for the master it names); else a one-line reason"""
    st = load(os.path.join(root, "Edit", "qc.json"))
    if st is None: return f"{root}/Edit/qc.json is missing: run `cves qc` and fix every FAIL first"
    if st.get("fail", 1) != 0: return f"QC has {st.get('fail')} FAIL (Edit/QC-REPORT.txt): fix them and re-run `cves qc`; deliver with `cves deliver`"
    v = video or st.get("video")
    if not v or not os.path.isfile(v): return "the master QC judged is gone: re-run `cves encode` + `cves qc`"
    if sha256(v) != st.get("sha256"):
        return f"{os.path.basename(v)} changed since QC (sha mismatch: re-encoded?). Re-run `cves qc`, then `cves deliver`"
    return None


def check_export_file(root, path):
    """None if this Export file may leave the project"""
    rel = os.path.relpath(os.path.abspath(path), os.path.join(root, "Export")).split(os.sep)
    if rel and re.fullmatch(r"v\d{3,}", rel[0]):            # a delivered version folder
        vdir = os.path.join(root, "Export", rel[0]); man = load(os.path.join(vdir, "manifest.json"))
        if man is None: return f"Export/{rel[0]} has no manifest.json (not made by `cves deliver`)"
        if not man.get("qc_verified") or man.get("forced_unchecked"):
            return f"Export/{rel[0]} was delivered with --force-unchecked (QC not passed): a human must review and ship it by hand"
        m = os.path.join(vdir, man.get("master", ""))
        if os.path.isfile(m) and sha256(m) != man.get("master_sha256"): return f"Export/{rel[0]}/{man.get('master')} was modified after delivery"
        return None
    if rel and rel[0].startswith(".staging-"): return "that is an unfinished `cves deliver` staging folder"
    vid = os.path.abspath(path) if len(rel) == 1 and path.lower().endswith((".mp4", ".mov", ".m4v")) and os.path.isfile(path) else None
    return stamp_problem(root, vid)       # a master in Export/ must be the exact file QC judged


def paths_in(cmd, cwd):
    try: toks = shlex.split(cmd, posix=os.name != "nt")
    except ValueError: toks = cmd.split()
    res = []
    for t in toks:
        if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'": t = t[1:-1]   # non-posix split (Windows) keeps the quotes
        t = t.split("=", 1)[1] if t.startswith("-") and "=" in t else t
        if "@" in t: t = re.sub(r"^[^@]*@", "", t)       # curl -F name=@file, --data-binary @file
        if not t or t.startswith("-"): continue
        if re.search(r"(^|[\\/])Export([\\/]|$)", t):
            p = os.path.expanduser(t)
            res.append(p if os.path.isabs(p) else os.path.join(cwd, p))
    return toks, res


def pre(d):
    cmd = (d.get("tool_input") or {}).get("command", "") or ""; cwd = d.get("cwd") or os.getcwd()
    if re.search(r"\bcves\b.*\bdeliver\b.*--force-unchecked", cmd):
        m = re.search(r"--project[ =](\"[^\"]+\"|'[^']+'|\S+)", cmd)
        root = project_of(os.path.join(cwd, os.path.expanduser(m.group(1).strip("\"'")))) if m else project_of(cwd)
        if root:
            p = stamp_problem(root)
            if p: deny(f"`cves deliver --force-unchecked` is blocked while QC is not clean ({p}). Fix the FAILs; only a human may force an unchecked delivery, from their own terminal.")
        return
    if not (COPY.search(cmd) or UPLOAD_CURL.search(cmd)): return
    if re.search(r"(^|\s)(curl|wget)\b", cmd) and not UPLOAD_CURL.search(cmd) and not COPY.search(re.sub(r"\b(curl|wget)\b", "", cmd)): return
    toks, paths = paths_in(cmd, cwd)
    if not paths: return
    last = toks[-1].lstrip("@") if toks else ""
    srcs = paths
    if len(paths) >= 2 and re.search(r"(^|[\\/])Export([\\/]|$)", last):   # the destination is itself inside an Export/ folder
        droot = project_of(paths[-1]); srcs = paths[:-1]
        if srcs and all(project_of(q) == droot for q in srcs): return   # Export -> Export of the same project: not a delivery
    for p in srcs:
        root = project_of(p)
        if not root or not os.path.isdir(os.path.join(root, "Edit")): continue
        if os.path.isdir(p): targets = [os.path.join(dp, f) for dp, _, fs in os.walk(p) for f in fs] or [p]
        else: targets = [p]
        for t in targets:
            why = check_export_file(root, t) if os.path.isfile(t) else stamp_problem(root)
            if why: deny(f"moving a file out of {root}/Export is blocked: {why}.")


def post(d):
    cmd = (d.get("tool_input") or {}).get("command", "") or ""
    o = str((d.get("tool_response") or {}).get("stdout", ""))[-4000:]
    msg = None
    if re.search(r"\bcves\s+(render|encode|mix)\b", cmd) and not re.search(r"\bcves\s+(qc|build)\b", cmd):
        msg = "CVES rule: the deliverable changed. Run `cves qc` and fix edit.yaml until QC-REPORT shows 0 FAIL before showing the user anything (objective faults must never reach the user). Deliver only with `cves deliver`."
    elif re.search(r"\bcves\s+(qc|build)\b", cmd):
        m = re.search(r"(\d+) FAIL", o)
        if m and int(m.group(1)) > 0:
            msg = f"CVES rule: QC has {m.group(1)} FAIL. Do not deliver. Fix each failing gate in edit.yaml (or the template), re-render, and re-run `cves qc`."
    if msg: out("PostToolUse", additionalContext=msg)


def main():
    try: d = json.load(sys.stdin)
    except Exception: return
    if d.get("tool_name") not in (None, "Bash"): return
    ev = d.get("hook_event_name") or ("PostToolUse" if "tool_response" in d else "PreToolUse")
    try:
        (pre if ev == "PreToolUse" else post)(d)
    except SystemExit: raise
    except Exception: return       # never wedge the session on a guard bug


if __name__ == "__main__":
    main()
