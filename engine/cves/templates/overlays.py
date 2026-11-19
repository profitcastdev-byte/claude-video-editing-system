"""Overlays on A-roll: lower_third (name + role, chest-style, under the chin; replaces captions while visible) and
kinetic_caption_emphasis (one emphasised word, big; roto-capable: behind the presenter in `roto:`, in front in `chest:`).
Text over video gets the auto-darkened bed when its colour misses the WCAG target (gfx.legible_bed)."""
from .. import gfx as G
from ..gfx import ease_out, ease_in, back, clamp

KIND = "chest"
KINDS = {"kinetic_caption_emphasis": "roto", "emphasis_word": "roto"}
def _el(): from . import El, faded; return El, faded

def lower_third(t, p, ctx):
    """name + role. p: name, role, at, role_at, out_at (default: 0.25 s before the shot ends), align (left|center), style (bar|card),
    color (accent bar / card edge), y (top; default just under the chin, inside the safe zone)"""
    El, faded = _el(); F = G.fps_of(ctx); Q = lambda v: G.q(v, F); res = []
    name, role = G.tidy(p.get("name", "")), G.tidy(p.get("role", ""))
    if not name: return res
    at = p.get("at", ctx["start"]); pa = G.enter(t, at, .35, F)
    if pa <= 0: return res
    oa = p.get("out_at", ctx.get("end", 1e9) - .25); po = ease_in(G.enter(t, oa, .22, F)); vis = 1 - po
    z = G.safe(); pad = p.get("pad", 50); chin = ctx.get("chin_hold", ctx.get("chin", G.H * .45))
    fn = G.fit_font("b", p.get("size", 54), name, (z[2] - z[0]) - 2 * pad - 60, 1); fr = G.fit_font("sb", int(fn.size * .6), role, (z[2] - z[0]) - 2 * pad - 60, 2) if role else None
    h = fn.size * 1.25 + (fr.size * 1.45 if fr else 0) + 36
    top = p.get("y") or min(max(chin + 60, z[3] - 40 - h - 140), z[3] - 20 - h)
    centre = p.get("align", "left") == "center"; style = p.get("style", "bar"); c = G.col(p.get("color"), G.MINT)
    tw = max(G.ink(name, fn, 1)[1], G.ink(role, fr, 2)[1] if fr else 0)
    x0 = (G.W / 2 - (tw + 60) / 2) if centre else z[0] + pad; tx = x0 + 34
    e = ease_out(pa); slide = G.mo("slide_px", 50) * .6
    if style == "card":
        res.append(El(G.alpha(G.layer(lambda d: G.rrect(d, (x0, top, x0 + (tw + 68) * e, top + h), 18, fill=G.CARD + (235,), outline=G.CARD_B, width=2)), vis),
                      "lower.plate", "chest", t_key=Q(at)))
    res.append(El(G.alpha(G.layer(lambda d: G.rrect(d, (x0, top + h / 2 - h / 2 * e, x0 + 8, top + h / 2 + h / 2 * e), 4, fill=c)), vis), "lower.bar", "chest", t_key=Q(at)))
    na = at + .06; pn = ease_out(G.enter(t, na, .3, F))
    if pn > 0:
        im = faded(lambda d: G.draw_text(d, (tx - slide * (1 - pn) - slide * po, top + 18 + fn.size * .95), name, fn, G.WHITE, tracking=1, anchor="li"), pn * vis)
        bed = G.legible_bed(im, G.WHITE, fn.size) if style != "card" else None
        if bed is not None: res.append(El(bed, "lower.name.bed", "chest"))
        res.append(El(im, "lower.name", "chest", text=name, t_key=Q(na)))
    ra = p.get("role_at", at + .2); pr = ease_out(G.enter(t, ra, .3, F))
    if fr and pr > 0:
        rc = G.col(p.get("role_color"), G.mix(G.WHITE, c, .35))
        im = faded(lambda d: G.draw_text(d, (tx - slide * po, top + 18 + fn.size * 1.25 + fr.size * 1.0 + 10 * (1 - pr)), role, fr, rc, tracking=2, anchor="li"), pr * vis)
        bed = G.legible_bed(im, rc, fr.size) if style != "card" else None
        if bed is not None: res.append(El(bed, "lower.role.bed", "chest"))
        res.append(El(im, "lower.role", "chest", text=role, t_key=Q(ra)))
    return res

def lower_third_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = [(at, "swipe", -20, {"trim": (0, .3)})]
    if p.get("role"): c.append((p.get("role_at", at + .2), "pop", -26, {"pitch": 2}))
    return G.cues_out(c, ctx)

def kinetic_caption_emphasis(t, p, ctx):
    """one big emphasised word. p: word, at, out_at (default 0.2 s before the shot ends), size (260), color (accent), y (baseline, 560),
    scale_from (1.35), tracking (4)"""
    El, faded = _el(); F = G.fps_of(ctx); Q = lambda v: G.q(v, F)
    wd = G.tidy(p.get("word", p.get("text", "")))
    at = p.get("at", ctx["start"]); qv = G.enter(t, at, .16, F)
    if not wd or qv <= 0: return []
    oa = p.get("out_at", ctx.get("end", 1e9) - .2); po = ease_in(G.enter(t, oa, .2, F))
    z = G.safe(); sf = p.get("scale_from", 1.35); hold = clamp((t - G.q(at, F)) / 3) * .04
    sc = 1 + (sf - 1) * (1 - ease_out(qv)) + hold
    tr = p.get("tracking", 4); base = G.fit_font("xb", int(p.get("size", 260)), wd, (z[2] - z[0]) / 1.04, tr)   # fit at rest, room for the hold
    f = G.fit_font("xb", int(base.size * sc), wd, 1e9, tr)          # the entry scales from there (a fitted word never ends past the safe zone)
    c = G.col(p.get("color"), G.MINT); y = p.get("y", 560 if G.is_design() else G.safe()[1] + .3 * (G.safe()[3] - G.safe()[1]))
    im = faded(lambda d: G.draw_text(d, (G.W / 2, y - 80 * po), wd, f, c, tracking=tr, anchor="ms"), min(1, qv * 2) * (1 - po))
    return [El(im, "emph.word", "roto", text=wd, t_key=Q(at))]

def kinetic_cues(p, ctx): return G.cues_out([(p.get("at", ctx["start"]), "lowhit", -10, {"reveal": True})], ctx)

T = {"lower_third": (lower_third, lower_third_cues), "kinetic_caption_emphasis": (kinetic_caption_emphasis, kinetic_cues),
     "emphasis_word": (kinetic_caption_emphasis, kinetic_cues)}
