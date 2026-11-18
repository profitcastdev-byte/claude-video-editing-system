"""Motion pieces as templates (docs/MOTION.md): every piece folder (engine/cves/motion/pieces/, ~/.cves/motion/,
PROJECT/Brand/motion/) becomes a template `m_<piece>`. The frames are HTML/CSS compositions rendered once by headless
Chromium and cached under PROJECT/Edit/motion/<hash>/ (render.render() pre-renders them before its worker pool starts);
render() here only reads the cached PNG for frame round((t - start) * fps).

Where a piece sits decides how it behaves:
- in `cutaways:` it is a full-screen moment on the stage (role `cutaway`; it cuts out with the cutaway's transition);
- in `chest:` it is an overlay over the A-roll (role `chest`, so every chest / text-over-video gate applies) and it plays
  its exit animation before the segment ends;
- `<name>_roto` (pieces whose meta lists `roto`) sits behind the presenter (role `roto`);
- `<name>_end` (pieces whose meta lists `end`) is an end card.

Params common to every motion template: `at` (when the piece's clock starts; default the slot's start), `duration`
(default: to the slot's end), `exit` (play the exit animation; default on for overlays). Every other `at` / `*_at`
param is a cut-time second, passed to the page piece-relative. Colours, fonts and motion all come from the style."""
import json, os
import numpy as np
from PIL import Image
from .. import gfx as G
from .. import motion as MO

KIND = "overlay"
KINDS, PARAMS, T = {}, {}, {}
_JOBS = {}


def _slot(name, ctx):
    k = KINDS.get(name)
    if k in ("roto", "end"): return k
    return "chest" if "chin" in ctx or "chin_hold" in ctx else "cutaway"


def _cache_root(ctx):
    """PROJECT/Edit/motion when the timeline is known (ctx resolve is Timeline.resolve), else $CVES_MOTION_CACHE / ~/.cves"""
    tl = getattr(ctx.get("resolve"), "__self__", None); pr = getattr(tl, "pr", None)
    return pr.e("motion") if pr is not None and hasattr(pr, "e") else MO.default_cache_root()


def job_for(name, piece, p, ctx, exit=None):
    """the motion Job for this template call (memoised: frames of one piece share it)"""
    p = p or {}; fps = G.fps_of(ctx) or 30; slot = _slot(name, ctx)
    start = float(p.get("at", ctx["start"]))
    dur = float(p.get("duration") or (ctx.get("end", start + piece.duration) - start))
    ex = bool(p.get("exit", slot != "cutaway")) if exit is None else exit
    S = ctx.get("S") or G.STYLE; root = _cache_root(ctx)
    key = json.dumps([name, p, start, dur, ex, G.W, G.H, fps, str(root), id(S)], sort_keys=True, default=str)
    j = _JOBS.get(key)
    if j is None:
        if len(_JOBS) > 256: _JOBS.clear()
        j = _JOBS[key] = MO.Job(piece, p, S, (G.W, G.H), fps, start, dur, exit=ex, resolve=ctx.get("resolve"), root=root)
    return j


def _make(name, piece):
    def render(t, p, ctx):
        from . import El
        job = job_for(name, piece, p, ctx)
        if t < job.start - 1e-6 or t >= job.end - 1e-6: return []
        if not job.done: MO.render(job)
        k = job.frame_index(t)
        im = Image.open(job.frame_path(k)).convert("RGBA")
        if im.size != (G.W, G.H): im = im.resize((G.W, G.H), Image.LANCZOS)
        man = getattr(job, "_man", None) or job.manifest(); job._man = man
        text = (man.get("text") or [""] * job.n)[k] or None
        return [El(im, name, _slot(name, ctx), text=text, t_key=G.q(job.start, G.fps_of(ctx)), asset=piece.name)]

    def cues(p, ctx):
        jobs = [job_for(name, piece, p, ctx, exit=e) for e in (False, True)]
        job = next((j for j in jobs if j.done), jobs[0])
        out = [(job.start + float(c[0]), c[1], float(c[2]), dict(c[3]) if len(c) > 3 and isinstance(c[3], dict) else {})
               for c in MO.cues_for(job) if job.start + float(c[0]) < job.end]
        return G.cues_out(out, ctx)

    render.__doc__ = f"[motion] {piece.title}: {piece.description}"
    render.motion_job = lambda p, ctx: job_for(name, piece, p, ctx)
    return render, cues


def _primary_kind(kinds):
    if "overlay" in kinds: return "overlay"            # usable in cutaways AND chest (schema)
    if "cutaway" in kinds: return "cutaway"
    return kinds[0] if kinds else "overlay"


def register(pieces, registry=None, kinds=None, source=None):
    """add motion pieces to the template registry: m_<piece> (+ m_<piece>_roto / _end when the meta lists them)"""
    from . import REGISTRY, KIND as TKIND, SOURCE
    got = []
    for pc in pieces.values():
        MO.PIECES[pc.name] = pc
        names = [(pc.name, _primary_kind(pc.kinds))] + [(f"{pc.name}_{k}", k) for k in ("roto", "end") if k in pc.kinds]
        for n, k in names:
            T[n] = _make(n, pc); KINDS[n] = k; PARAMS[n] = pc.schema_types()
            REGISTRY[n] = T[n]; TKIND[n] = k; SOURCE[n] = f"motion:{pc.origin}"; got.append(n)
    return got


def _load_hook(d, origin=None):
    """templates.load_dir hook: a `templates` folder's sibling `motion` folder holds motion pieces
    (~/.cves/templates -> ~/.cves/motion, PROJECT/Brand/templates -> PROJECT/Brand/motion)"""
    d = os.path.expanduser(d or "")
    if not d or os.path.basename(os.path.normpath(d)) != "templates": return []
    return register(MO.scan(os.path.join(os.path.dirname(os.path.normpath(d)), "motion"), origin or "user"))


# built-in pieces (+ $CVES_MOTION) at import; user / project folders come through load_dir
for _d, _o in MO.piece_dirs():
    if _o in ("builtin", "env"):
        for _pc in MO.scan(_d, _o).values():
            MO.PIECES[_pc.name] = _pc
            for _n, _k in [(_pc.name, _primary_kind(_pc.kinds))] + [(f"{_pc.name}_{k}", k) for k in ("roto", "end") if k in _pc.kinds]:
                T[_n] = _make(_n, _pc); KINDS[_n] = _k; PARAMS[_n] = _pc.schema_types()

from . import LOAD_HOOKS   # noqa: E402  (defined before the package imports its modules)
LOAD_HOOKS.append(_load_hook)
