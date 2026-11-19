"""`cves build` (render + mix + encode + qc) and its draft mode (docs/ARCHITECTURE.md §3 step 6, docs/CONTRACTS.md §6).

Final build: the full-quality master in Export/, rendered incrementally (cves.rcache: only frames whose inputs changed),
mixed, encoded with the style `delivery:` settings and QC'd (the fast gate set), as before.

Draft build (`cves build --draft`): a quick look while iterating. It is a project.Variant in `Edit/draft/` (its own
frames, frame cache, element log, timeline, mix, QC stamp), rendered at `render.draft_scale` of the canvas (the treatments
proxy path: plates and mattes resized as they decode), encoded with the proxy settings (`treatments.proxy_preset` /
`proxy_crf`) into `Edit/draft/<title>_draft.mp4`, tagged `comment=cves-draft`, and QC'd with the fast gate set. The
final build's frames, cache and stamp are never touched. Delivery refuses a draft (`deliver.is_draft`)."""
import os, shutil, time
from .project import Variant

DRAFT = "draft"
# the plan is the project's; the solved caches are reused while their signature matches (else solved again)
_PLAN = ("edit.yaml", "treatment.yaml")
_SOLVED = ("exposure.json", "shot_match.json", "beats.json")


def draft_project(pr):
    """the draft Variant (Edit/draft/), with the project's current plan and its solved caches"""
    d = pr.e(DRAFT); os.makedirs(d, exist_ok=True)
    for f in _PLAN:
        src, dst = pr.e(f), os.path.join(d, f)
        if os.path.exists(src):
            same = os.path.exists(dst) and open(src, "rb").read() == open(dst, "rb").read()
            if not same: shutil.copyfile(src, dst)
        elif os.path.exists(dst): os.remove(dst)
    for f in _SOLVED:
        src, dst = pr.e(f), os.path.join(d, f)
        if os.path.exists(src) and (not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst)): shutil.copy2(src, dst)
    return Variant(pr.root, d)


def build(pr, draft=False, cache=None, log=print):
    """-> (master path, QC fail count, QC report, {stage: seconds}). draft: see the module doc."""
    from . import render as R, mix as MX, encode as EN, qc, schema, style as STY
    schema.require_valid(pr); T = {}
    tgt = draft_project(pr) if draft else pr
    k = float(STY.load(pr).get("render.draft_scale", 0.5) or 0.5) if draft else None
    t = time.time(); R.render(tgt, proxy=k if k and k != 1.0 else None, cache=cache, draft=draft); T["render"] = time.time() - t
    L = R.LAST; log(f"render: {L.get('frames', 0)} of {L.get('of', 0)} frames rendered ({L.get('cached', 0)} from the frame cache)")
    t = time.time(); MX.mix(tgt); T["mix"] = time.time() - t
    t = time.time()
    if draft:
        title = (pr.edit.get("project", {}) or {}).get("title", "edit").replace(" ", "_")
        v = EN.encode(tgt, out=os.path.join(tgt.work, f"{title}_draft.mp4"), draft=True)
    else:
        v = EN.encode(pr)
    T["encode"] = time.time() - t
    t = time.time(); nf, rep = qc.run(tgt, v, fast=True); T["qc"] = time.time() - t
    if draft:                                     # the stamp says what it judged: a draft never passes for a master
        st = tgt.json("qc.json")
        if isinstance(st, dict): st["draft"] = True; tgt.save_json("qc.json", st)
    return v, nf, rep, T
