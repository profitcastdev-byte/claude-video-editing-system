"""End cards (after the last spoken word; <= 3 s, hard cut, no black - PLAT-11/12).
logo_end: logo + label + pill. end_card: the generic call-to-action card (headline, button, handle / URL, optional QR,
optional logo), the same layout as the `cta` cutaway. Every element enters from its own centre / with a fade."""
from .. import gfx as G
from ..gfx import ease_out, back

KIND = "end"
def _el(): from . import El, faded; return El, faded

def logo_end(t, p, ctx):
    """p: logo, label, pill, width (640), y (700). Defaults are design px (G.DESIGN); on other canvases the block is centred in the safe zone"""
    El, faded = _el(); F = G.fps_of(ctx); Q = lambda v: G.q(v, F); t0 = ctx["start"]; res = []
    pp = ease_out(G.enter(t, t0 - .15, .45, F)); wpx = p.get("width", 640)
    z = G.safe(); dy = 0 if G.is_design() else ((z[1] + z[3]) / 2 - 950)        # the 700-1230 px block, centred in the safe zone
    y = p.get("y", 700 + dy)
    if pp > 0 and p.get("logo"):
        from .generic import asset
        lg = G.image(asset(ctx, p["logo"])); sc = .92 + .08 * pp
        res.append(El(G.layer(lambda d: d.paste(lg, (G.W - wpx * sc) / 2, y + 30 * (1 - pp), wpx * sc, opacity=pp)), "end.logo", "end", text="logo", asset=p["logo"], t_key=Q(t0)))
    lab = G.tidy(p.get("label", "")); la = t0 + .25; pl = ease_out(G.enter(t, la, .35, F))
    if pl > 0 and lab: res.append(El(faded(lambda d: G.label(d, G.W / 2, 1100 + dy + 14 * (1 - pl), lab, 28), pl), "end.label", "end", text=lab, t_key=Q(la)))
    pil = G.tidy(p.get("pill", "")); pa = t0 + .45; pq = G.enter(t, pa, .3, F)
    if pq > 0 and pil:      # pops from its own centre (MOT-12), label once it is big enough to read
        res.append(El(G.layer(lambda d: G.pill(d, G.W / 2, 1200 + dy, pil, G.font("b", 34), pad=(38, 18), sc=back(pq), text_p=pq)), "end.pill", "end", text=pil, t_key=Q(pa)))
    return res

def logo_end_cues(p, ctx):
    c = [(ctx["start"], "lowhit", -12, {})]
    if p.get("label"): c.append((ctx["start"] + .25, "swipe", -24, {"trim": (0, .25)}))
    if p.get("pill"): c.append((ctx["start"] + .45, "pop", -17, {}))
    return G.cues_out(c, ctx)

def end_card(t, p, ctx):
    """generic CTA end card. p: headline, button, handle, icon, qr, logo, at / *_at times (default: a short cascade from the card start), press_at"""
    from .generic import cta_render
    return cta_render(t, {**p, "at": p.get("at", ctx["start"])}, ctx, "end", "end")

def end_card_cues(p, ctx):
    from .generic import cta_cues
    return cta_cues({**p, "at": p.get("at", ctx["start"])}, ctx)

T = {"logo_end": (logo_end, logo_end_cues), "end_card": (end_card, end_card_cues)}
