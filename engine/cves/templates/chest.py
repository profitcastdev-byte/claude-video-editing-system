"""Chest-level elements that replace captions for their duration (client wordmark, price, brand lockup).
Kept above the safe-zone bottom where possible (platform UI); never over the face (FRAME-01). Small text over video gets an
auto-darkened bed when its colour misses the WCAG target (gfx.legible_bed, GFX-15). The vertical anchor is
`ctx["chin_hold"]` (a segment-stable chin, when the renderer provides it) else `ctx["chin"]`."""
import numpy as np
from PIL import Image, ImageFilter
from .. import gfx as G
from ..gfx import ease_out, back

KIND = "chest"
def _el(): from . import El, faded; return El, faded
def _t(ctx): F = G.fps_of(ctx); return F, (lambda v: G.q(v, F))
def _chin(ctx): return ctx.get("chin_hold", ctx.get("chin", G.H * .45))

def _sh(im, El, id_, r, a, dy, **kw):
    """[shadow (decor), element]: the shadow is its own element so the logged bbox is the ink (GFX-08)"""
    return [El(G.shadow_only(im, r=r, alpha=a, dy=dy), id_ + ".sh.bed", "chest", asset=kw.get("asset")), El(im, id_, "chest", **kw)]

def _with_bed(im, fg, size_px, El, id_, **kw):
    """[bed, text] elements: the bed only when the text needs it"""
    bed = G.legible_bed(im, fg, size_px)
    return ([El(bed, id_ + ".bed", "chest")] if bed is not None else []) + [El(im, id_, "chest", **kw)]

def wordmark(t, p, ctx):
    """a name set as a display-serif wordmark with a soft gradient + dark bed, wiping in from its first letter.
    p: lines, sub, at, sub_at, out_at, y, size (104), color (gold), sub_color, line_gap (100)"""
    El, faded = _el(); F, Q = _t(ctx); at = p["at"]; pp = G.enter(t, at, .6, F); out = G.enter(t, p.get("out_at", ctx["end"] - .2), .18, F)
    y0 = p.get("y") or _chin(ctx) + 150; res = []; lines = [G.tidy(x) for x in p.get("lines", [])]; gap = p.get("line_gap", 100)
    c = G.col(p.get("color"), G.GOLD)
    if pp > 0 and lines:
        f = G.font("serif", p.get("size", 104))
        def mark(d):
            for k, ln in enumerate(lines): G.draw_text(d, (G.W / 2, y0 + k * gap), ln, f, c, anchor="ms")
        im = G.layer(mark); a = np.asarray(im).copy()
        xs = np.where(a[..., 3].max(0) > 0)[0]; xl, xr = (xs.min(), xs.max()) if len(xs) else (0, G.W)
        x = np.arange(G.W)[None, :]; edge = xl + ease_out(pp) * (xr - xl + 120)          # the wipe starts at the first letter: visible on its word's frame
        a[..., 3] = (a[..., 3] * np.clip((edge - x) / 120, 0, 1) * (1 - out)).astype(np.uint8)
        g = np.linspace(1.30, .95, G.H)[:, None, None]; a[..., :3] = np.clip(a[..., :3] * g, 0, 255).astype(np.uint8)
        bed = Image.fromarray(a[..., 3]).filter(ImageFilter.GaussianBlur(34)).point(lambda v: min(255, int(v * 1.6)))
        dk = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0)); dk.putalpha(bed.point(lambda v: int(v * G.sget("legibility.wordmark_bed", .72))))   # >= 3:1 over a light shirt (GFX-15)
        res += [El(dk, "chest.wordmark.bed", "chest"), *_sh(Image.fromarray(a), El, "chest.wordmark", 6, .75, 3, text=" ".join(lines), t_key=Q(at), font="CormorantGaramond")]
    sub = G.tidy(p.get("sub", "")); sa = p.get("sub_at", 1e9); ps = ease_out(G.enter(t, sa, .4, F))
    if ps > 0 and sub:
        ys = y0 + len(lines) * gap - 30; sc = G.col(p.get("sub_color"), G.mix(c, G.WHITE, .55)); fs = 26
        im = faded(lambda d: G.label(d, G.W / 2, ys + 12 * (1 - ps), sub, fs, col=sc, tracking=6), ps * (1 - out))
        bed = G.legible_bed(im, sc, fs)                                   # 26 px type needs 4.5:1 over the video (GFX-15)
        if bed is not None: res.append(El(bed, "chest.wordmark.sub.bed", "chest"))
        res += _sh(im, El, "chest.wordmark.sub", 6, .8, 2, text=sub, t_key=Q(sa))
    return res

def price_card(t, p, ctx):
    """a price line. p: label (e.g. a word above the price), price, unit, at, y, color"""
    El, faded = _el(); F, Q = _t(ctx); pp = G.enter(t, p["at"], .25, F)
    y = p.get("y") or max(_chin(ctx) + 170, min(_chin(ctx) + 250, G.safe()[3] - 26))   # baseline inside the safe zone, label never on the chin
    if pp <= 0: return []
    lab, price, unit = G.tidy(p.get("label", "")), G.tidy(p.get("price", "")), G.tidy(p.get("unit", ""))
    c = G.col(p.get("color"), G.MINT)
    def draw(d):
        f = G.font("xb", 112); f2 = G.font("sb", 42); w1 = G.text_w(price, f); spc = G.text_w(" ", f2)
        il = G.ink(price, f)[0]; ir = (w1 + spc + G.ink(unit, f2)[1]) if unit else G.ink(price, f)[1]
        x = G.W / 2 - (il + ir) / 2
        dy = 30 * (1 - back(pp))   # price and unit move together (linked text never separates)
        G.draw_text(d, (x, y + dy), price, f, c)
        if unit: G.draw_text(d, (x + w1 + spc, y + dy), unit, f2, G.WHITE)
    im = faded(draw, min(1, pp * 2)); bed = G.legible_bed(im, G.WHITE if unit else c, 42 if unit else 112)
    res = ([El(bed, "chest.price.bed", "chest")] if bed is not None else []) + _sh(im, El, "chest.price", 12, .6, 4, text=G.tidy(f"{price} {unit}"), t_key=Q(p["at"]))
    if lab:
        im = faded(lambda d: G.label(d, G.W / 2, y - 118 + 20 * (1 - ease_out(pp)), lab, 26, col=G.MUTED), min(1, pp * 2))
        res = _with_bed(im, G.MUTED, 26, El, "chest.price.label", text=lab, t_key=Q(p["at"])) + res
    return res

def logo_lockup(t, p, ctx):
    """brand logo on the brand word, tagline on its words. p: logo (path), at, tagline, tagline_at, y, width (520)"""
    El, faded = _el(); F, Q = _t(ctx); res = []; pp = ease_out(G.enter(t, p["at"], .3, F)); y = p.get("y") or _chin(ctx) + 60
    wpx = p.get("width", 520); lg = None
    if pp > 0:
        from .generic import asset
        lg = G.image(asset(ctx, p["logo"]))
        res += _sh(G.layer(lambda d: d.paste(lg, (G.W - wpx) / 2, y + 30 * (1 - pp), wpx, opacity=pp)), El, "chest.logo", 12, .6, 4, text="logo", t_key=Q(p["at"]), asset=p["logo"])
    tg = G.tidy(p.get("tagline", "")); ta = p.get("tagline_at", 1e9); pm = ease_out(G.enter(t, ta, .3, F))
    if pm > 0 and tg:
        from .generic import asset
        lg = lg or G.image(asset(ctx, p["logo"])); ty = y + wpx * lg.height / lg.width + 70
        im = faded(lambda d: G.draw_text(d, (G.W / 2, ty + 16 * (1 - pm)), tg, G.fit_font("sb", 40, tg, min(900, G.safe()[2] - G.safe()[0]), 12), G.WHITE, tracking=12, anchor="ms"), pm)
        bed = G.legible_bed(im, G.WHITE, 40)
        res += ([El(bed, "chest.tagline.bed", "chest")] if bed is not None else []) + _sh(im, El, "chest.tagline", 10, .7, 3, text=tg, t_key=Q(ta))
    return res

def wordmark_cues(p, ctx):
    c = [(p["at"], "ding", -25, {})]
    if p.get("sub") and p.get("sub_at") is not None: c.append((p["sub_at"], "swipe", -24, {"trim": (0, .25)}))
    return G.cues_out(c, ctx)
def price_cues(p, ctx): return G.cues_out([(p["at"], "button", -17, {}), (p["at"], "ding", -22, {})], ctx)
def lockup_cues(p, ctx):
    c = [(p["at"], "whoosh", -20, {"trim": (0, .35)}), (p["at"], "lowhit", -15, {})]
    if p.get("tagline") and p.get("tagline_at") is not None: c.append((p["tagline_at"], "pop", -20, {"pitch": -2}))
    return G.cues_out(c, ctx)

T = {"wordmark": (wordmark, wordmark_cues), "price_card": (price_card, price_cues), "logo_lockup": (logo_lockup, lockup_cues)}
