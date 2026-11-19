"""Roto templates: drawn BEHIND the presenter (person matte composited on top). House rule: <= 4 moments, each <= 3 s.
Cards sit high so their top edge stays visible above the head. Pins, rows and badges are their own elements, so their
cues have a logged visual event (SND-07). Colours come from the palette (gfx); no copy lives here.
Relative templates: each card is laid out in fractions of its own box, and the box comes from the canvas shape
(templates/_layout.py): the original 1080x1920 box on 9:16, a box filling the safe zone on square and wide canvases."""
import functools, math
from .. import gfx as G
from ..gfx import ease_out, ease_in, back, clamp
from . import _layout as LY

KIND = "roto"
def _el(): from . import El, faded; return El, faded
def _t(ctx): F = G.fps_of(ctx); return F, (lambda v: G.q(v, F))
def _deep(a=235): return G.mix(G.CARD, (0, 0, 0), .35) + (a,)          # roto card body: a darker card, slightly see-through

def _card_box(tall_box, rise, place=None):
    """(x0, y_top, w, h, s, rise px) of a roto card. tall_box = (x0, y, x1, h) as designed on 1080x1920; rise = the entry
    travel (px at s = 1). place = (outer x0, outer y0, s) from _place (free space beside / above the head) wins.
    Square / wide: the card fills the safe zone height (its top edge stays high, above the head) and is wider on wide
    canvases; s = the scale of its inner px (icons, strokes, radii)."""
    x0, y, x1, h = tall_box; w = x1 - x0
    if place is not None:
        ox, oy, s = place; return ox + _BR * s, oy + _BR * s, w * s, h * s, s, rise * s
    if LY.mode() == "tall": return x0, y + LY.tall_dy(), w, h, 1.0, rise
    z = LY.zone(); ch = z[5] / (1 + 68 / h); s = ch / h                     # the corner brackets (30 px out) stay inside the zone
    cw = min(z[4] - 68 * s, ch * (1.35 if LY.mode() == "wide" else w / h * 1.08))
    return z[6] - cw / 2, z[1] + 34 * s, cw, ch, s, rise * s

_BR = 34                    # px (at s = 1) the corner brackets + their stroke reach outside a card
_PLACED = {}

@functools.lru_cache(256)
def _rise_steps(R, n_f):
    """whole-raster-px offsets of an ease-out rise of R px over n_f frames (frame j shows offset[j]); the per-frame steps
    are the rounded steps of the curve SORTED largest first, so they never grow (same total, same shape within 1 px)"""
    N = max(1, int(math.ceil(n_f - .5)))
    o = [R * (1 - ease_out(min(1.0, (i + .5) / n_f))) for i in range(N + 1)]
    c = [round(o[0] - v) for v in o]; st = sorted((c[i + 1] - c[i] for i in range(N)), reverse=True)
    off, cur = [], round(o[0])
    for d in [0] + st: cur -= d; off.append(cur)
    return tuple(off)

def _rise(t, at, dur, F, rise):
    """offset (layout px) of a card rising `rise` px over `dur` s with an ease-out. The card moves by whole raster px and
    its per-frame steps never grow, so its logged bbox decelerates monotonically at any frame rate (MOT-01: at 60 fps
    rounded half-pixel steps went 2, 3, 1, 2 and read as an acceleration)"""
    if not F: return rise * (1 - ease_out(G.enter(t, at, dur, F)))
    j = int(round((t - G.q(at, F)) * F))
    off = _rise_steps(round(rise * G.R, 3), dur * F)
    return (off[0] if j < 0 else off[min(j, len(off) - 1)]) / G.R

def _place(name, tall_box, p, ctx):
    """free-space placement of a roto card (style roto.place: auto): the largest scale (<= 1, >= roto.min_scale) at which
    the card sits where the subject matte, unioned over the card's slot, covers <= roto.max_cover of it; positions inside
    the shot's safe zone, the side with more room wins by construction (more room = a larger card). Returns
    (outer x0, outer y0, s) in layout px, or None (no matte / no fit: the designed position, and QC GFX-27 judges it)."""
    S = ctx.get("S") or G.STYLE; R_ = lambda k, d: (S.get(f"roto.{k}", d) if hasattr(S, "get") else d)
    if str(p.get("place", R_("place", "auto"))) != "auto": return None
    pl, fo = ctx.get("plate_lum"), ctx.get("frame_of")
    if pl is None or fo is None or not ctx.get("matte_ok", True): return None
    import json, numpy as np, cv2
    at = float(p.get("at", ctx["start"])); end = float(ctx.get("end", at + 2))
    try: key = (name, json.dumps(p, sort_keys=True, default=str), round(ctx["start"], 4), G.W, G.H, G.R)
    except (TypeError, ValueError): key = (name, id(p), G.W, G.H)
    if key in _PLACED: return _PLACED[key]
    res = None
    try: frames = pl([fo(at + (end - at) * (j + .5) / 8) for j in range(8)])
    except (OSError, ValueError) as e: print(f"cves: roto placement: matte not readable ({e}); designed position"); frames = []
    if frames:
        cell = 6.0                                                          # layout px per search cell
        gw, gh = int(G.W / cell), int(G.H / cell)
        occ = np.zeros((gh, gw), np.float32); lum = np.zeros((gh, gw), np.float32)
        for _, L, A in frames:
            occ = np.maximum(occ, cv2.resize((A > .5).astype(np.float32), (gw, gh), interpolation=cv2.INTER_AREA))
            lum += cv2.resize(L, (gw, gh), interpolation=cv2.INTER_AREA) / len(frames)
        II = np.pad(occ.cumsum(0).cumsum(1), ((1, 0), (1, 0))); IL = np.pad(lum.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        box = lambda I, ch, cw: I[ch:, cw:] - I[:-ch, cw:] - I[ch:, :-cw] + I[:-ch, :-cw]          # [top cell, left cell] sums
        z = G.safe(); sc = float(ctx.get("seg_scale") or 1.0)               # the zone that stays on screen at the shot's tightest zoom
        ix, iy = G.W * (1 - 1 / sc) / 2, G.H * (1 - 1 / sc) / 2
        zx0, zy0, zx1, zy1 = max(z[0], ix), max(z[1], iy), min(z[2], G.W - ix), min(z[3], G.H - iy)
        x0, y, x1, h = tall_box; w = x1 - x0
        mx = float(R_("max_cover", .2)); mn = float(R_("min_scale", .25)); s = 1.0
        while s >= mn - 1e-9 and res is None:
            ow, oh = (w + 2 * _BR) * s, (h + 2 * _BR) * s; cw, ch = int(np.ceil(ow / cell)), int(np.ceil(oh / cell))
            a0, b0 = int(np.ceil(zx0 / cell)), int(np.ceil(zy0 / cell)); a1, b1 = int((zx1 - ow) / cell), int((zy1 - oh) / cell)
            if a1 >= a0 and b1 >= b0:
                cov = box(II, ch, cw)[b0:b1 + 1, a0:a1 + 1] / (cw * ch)
                if cov.size and cov.min() <= mx:
                    # among the spots that fit: the brightest wall (the dark card reads on it), less covered, higher
                    bright = box(IL, ch, cw)[b0:b1 + 1, a0:a1 + 1] / (cw * ch)
                    score = np.where(cov <= mx, bright - .5 * cov - 1e-4 * np.arange(cov.shape[0])[:, None], -1e9)
                    yy, xx = np.unravel_index(int(np.argmax(score)), score.shape)
                    res = (float((a0 + xx) * cell), float((b0 + yy) * cell), s)
            s = round(s - .02, 4)
    _PLACED[key] = res
    if len(_PLACED) > 128: _PLACED.pop(next(iter(_PLACED)))
    return res

def map_card(t, p, ctx):
    """a map card: search bar + roads drawing in + pins popping. p: at (card in), draw_at (roads), pins_at, pins (count, <= 6), pin_stagger"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F))
    pm = G.enter(t, p.get("draw_at", at + .6), .9, F); res = []
    if pp <= 0: return res
    tb = (170, 200, 910, 880); bx, by, bw, bh, s, rise = _card_box(tb, 40, _place("map_card", tb, p, ctx))
    y = by + _rise(t, at, .35, F, rise)
    X = lambda fx: bx + bw * fx; Yc = lambda fy: y + bh * fy                 # card fractions (tall: x = 170 + 740 fx, y + 880 fy)
    def card(d):
        G.rrect(d, (bx, y, bx + bw, y + bh), 44 * s, fill=_deep(), outline=G.CARD_B, width=4 * s)
        G.brackets(d, (bx - 30 * s, y - 30 * s, bx + bw + 30 * s, y + bh + 30 * s), L=60 * s, w=3 * s)
        G.rrect(d, (bx + 50 * s, y + 44 * s, bx + bw - 50 * s, y + 104 * s), 30 * s, fill=G.SURFACE); G.icon(d, "search", bx + 92 * s, y + 74 * s, 30 * s, col=G.MUTED)
        roads = [((0, 330), (740, 250)), ((180, 120), (250, 880)), ((0, 600), (740, 700)), ((530, 120), (470, 880)), ((0, 460), (350, 880))]
        for k, (a, b) in enumerate(roads):
            qv = clamp(pm * 1.6 - k * .15)
            a_, b_ = (X(a[0] / 740), Yc(a[1] / 880)), (X(b[0] / 740), Yc(b[1] / 880))
            if qv > 0: d.line((a_, (a_[0] + (b_[0] - a_[0]) * qv, a_[1] + (b_[1] - a_[1]) * qv)), fill=G.mix(G.CARD_B, G.MINT_D, .6), width=10 * s)
    res.append(El(faded(card, pp), "roto.map", "roto", text="map", t_key=Q(at)))
    pins = ((130, 250), (610, 200), (80, 520), (650, 560), (390, 400), (250, 700))[:int(p.get("pins", 4))]
    cols = []                       # a scaled-down card brings designed pin columns within a few px: share one axis (GFX-08)
    for px_, py_ in pins:
        c = next((c for c in cols if abs(X(c / 740) - X(px_ / 740)) <= 14), None)
        if c is None: cols.append(px_)
    pins = [(next(c for c in cols if abs(X(c / 740) - X(px_ / 740)) <= 14), py_) for px_, py_ in pins]
    for k, (px_, py_) in enumerate(pins):
        pa = p.get("pins_at", at + 1.0) + k * p.get("pin_stagger", .1); qv = G.enter(t, pa, .2, F)
        if qv > 0: res.append(El(G.layer(lambda d, px_=px_, py_=py_, qv=qv: G.icon(d, "pin", X(px_ / 740), Yc(py_ / 880), 54 * max(0, back(qv)) * s)), f"roto.map.pin{k}", "roto", t_key=Q(pa), asset="pin"))
    return res

def big_words(t, p, ctx):
    """huge words slam in behind the head. p: words [[WORD, at, accent?]], out_at, ys? (baselines, 1080x1920 px; tall canvases
    only), size (200), accent_size (270), color, accent_color. Square / wide: the lines are spread down the safe zone."""
    El, faded = _el(); F, Q = _t(ctx); out_p = ease_in(G.enter(t, p.get("out_at", ctx["end"] - .3), .2, F)); res = []
    words = p.get("words", []); sz = G.safe(); maxw = sz[2] - sz[0]
    if LY.mode() == "tall":
        dy = LY.tall_dy(); ys = [v + dy for v in p.get("ys", [400, 610, 860])]; s = 1.0
    else:
        z = LY.zone(); n = max(1, len(words)); big = max(p.get("accent_size", 270), p.get("size", 200))
        s = max(.4, min(1.25, z[5] * .92 / (n * big * 1.02))); pitch = big * s * 1.02
        top = z[7] - pitch * n / 2; ys = [top + pitch * (k + .5) + big * s * .36 for k in range(n)]
    for k, (wd, at, *acc) in enumerate(words):
        qv = G.enter(t, at, .14, F); acc = bool(acc and acc[0])
        if qv <= 0: continue
        sc = 1 + .35 * (1 - ease_out(qv)); base = (p.get("accent_size", 270) if acc else p.get("size", 200)) * s; y = ys[min(k, len(ys) - 1)]
        wd = G.tidy(wd); f = G.fit_font("xb", int(base * sc), wd, maxw * sc, 4)
        c = G.col(p.get("accent_color"), G.MINT) if acc else G.col(p.get("color"), G.WHITE)
        def word(d, wd=wd, y=y, f=f, c=c, sc=sc):
            G.draw_text(d, (G.W / 2, y + 60 * (sc - 1) * s - 120 * out_p * s), wd, f, c, tracking=4, anchor="ms")    # ink-centred: every line on one axis (GFX-08)
        res.append(El(faded(word, min(1, qv * 2) * (1 - out_p)), f"roto.word{k}", "roto", text=wd, t_key=Q(at)))
    return res

def listing_card(t, p, ctx):
    """a listing / profile card rising behind the head (map strip, pin, rating). p: at, stars (0-5), stars_at"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F))
    if pp <= 0: return []
    tb = (150, 180, 930, 900); bx, by, bw, bh, s, rise = _card_box(tb, 120, _place("listing_card", tb, p, ctx))
    y = by + _rise(t, at, .35, F, rise); res = []
    X = lambda fx: bx + bw * fx; Yc = lambda fy: y + bh * fy
    def listing(d):
        G.rrect(d, (bx, y, bx + bw, y + bh), 44 * s, fill=_deep(240), outline=G.CARD_B, width=4 * s)
        G.brackets(d, (bx - 30 * s, y - 30 * s, bx + bw + 30 * s, y + bh + 30 * s), L=60 * s, w=3 * s)
        G.rrect(d, (bx + 50 * s, y + 44 * s, bx + bw - 50 * s, y + 104 * s), 30 * s, fill=G.SURFACE); G.icon(d, "search", bx + 92 * s, y + 74 * s, 30 * s, col=G.MUTED)
        G.rrect(d, (bx + 50 * s, y + 130 * s, bx + bw - 50 * s, y + 330 * s), 24 * s, fill=G.SURFACE)
        for a, b in (((50, 210), (730, 170)), ((330, 130), (390, 330))):
            d.line(((X(a[0] / 780), y + a[1] * s), (X(b[0] / 780), y + b[1] * s)), fill=G.mix(G.CARD_B, G.MINT_D, .6), width=9 * s)
        G.icon(d, "pin", X(550 / 780), y + 220 * s, 60 * s)
    res.append(El(faded(listing, pp), "roto.listing", "roto", text="listing", t_key=Q(at)))
    sa = p.get("stars_at", at + .2); ps = G.enter(t, sa, .35, F); n = int(p.get("stars", 5))
    if ps > 0 and n:
        def stars(d):
            for j in range(n):
                qv = clamp(ps * n * 1.3 - j)
                if qv > 0: G.icon(d, "star", bx + (80 + j * 34) * s, y + 380 * s, 24 * back(qv) * s, col=G.STAR)
        res.append(El(G.layer(stars), "roto.listing.stars", "roto", t_key=Q(sa), asset="star"))
    return res

def top3_card(t, p, ctx):
    """a ranked-results card + a badge (e.g. a 'top N' badge). p: at, badge (text), badge_at, rows (count), rows_at"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F)); res = []
    tb = (150, 260, 930, 860); bx, by, bw, bh, s, rise = _card_box(tb, 100, _place("top3_card", tb, p, ctx))
    y = by + _rise(t, at, .35, F, rise); n = int(p.get("rows", 3)); ra = p.get("rows_at", at + 1.0); stg = p.get("row_stagger", .12)
    pitch = 150 * s if n <= 4 or LY.mode() == "tall" else (bh - 160 * s) / n; rh = min(120 * s, pitch - 20 * s)
    def pack(d):
        G.rrect(d, (bx, y, bx + bw, y + bh), 44 * s, fill=_deep(240), outline=G.CARD_B, width=4 * s)
        G.brackets(d, (bx - 30 * s, y - 30 * s, bx + bw + 30 * s, y + bh + 30 * s), L=60 * s, w=3 * s)
        for k in range(n):
            yy = y + 120 * s + k * pitch
            G.rrect(d, (bx + 40 * s, yy, bx + bw - 40 * s, yy + rh), 24 * s, fill=G.SURFACE, outline=G.CARD_B, width=3 * s)
            G.icon(d, "pin", bx + 90 * s, yy + rh / 2, 46 * s, col=G.MUTED)
    if pp > 0: res.append(El(faded(pack, pp), "roto.pack", "roto", text="map pack", t_key=Q(at)))
    for k in range(n):                       # each row lights up as its own element (a visual event for its cue)
        qv = ease_out(G.enter(t, ra + k * stg, .18, F))
        if qv <= 0 or pp <= 0: continue
        def hi(d, k=k):
            yy = y + 120 * s + k * pitch
            G.rrect(d, (bx + 40 * s, yy, bx + bw - 40 * s, yy + rh), 24 * s, fill=G.mix(G.SURFACE, G.MINT_D, .35), outline=G.MINT_D, width=3 * s)
            G.icon(d, "pin", bx + 90 * s, yy + rh / 2, 46 * s, col=G.MINT)
        res.append(El(faded(hi, qv), f"roto.pack.row{k}", "roto", t_key=Q(ra + k * stg)))
    pb = G.enter(t, p.get("badge_at", at + .7), .25, F); txt = G.tidy(p.get("badge", ""))
    if pb > 0 and txt:
        res.append(El(G.layer(lambda d: G.pill(d, bx + bw / 2, by + 40 * s, txt, G.font("xb", 52 * s), pad=(35 * s, 18 * s), sc=back(pb), text_p=pb)), "roto.badge", "roto", text=txt, t_key=Q(p.get("badge_at", at + .7))))
    return res

def _cues_simple(p, ctx): return G.cues_out([(p.get("at", ctx["start"]), "swipe", -19, {})], ctx)
def listing_cues(p, ctx):
    at = p.get("at", ctx["start"]); return G.cues_out([(at, "swipe", -19, {})] + ([(p.get("stars_at", at + .2), "pop", -24, {"pitch": 3})] if int(p.get("stars", 5)) else []), ctx)
def big_words_cues(p, ctx): return G.cues_out([(w[1], "lowhit", -9 if len(w) > 2 and w[2] else -12, {"reveal": True, "pitch": [0, -1, 1, -2][k % 4]}) for k, w in enumerate(p.get("words", []))], ctx)
def map_card_cues(p, ctx):
    at = p.get("at", ctx["start"]); n = int(p.get("pins", 4)); st = p.get("pin_stagger", .1)
    return G.cues_out([(at, "swipe", -20, {})] + [(p.get("pins_at", at + 1) + k * st, "pop", -24, {"pitch": 4 + k}) for k in range(min(n, 2))], ctx)
def top3_cues(p, ctx):
    at = p.get("at", ctx["start"]); ba = p.get("badge_at", at + .7); ra = p.get("rows_at", at + 1); stg = p.get("row_stagger", .12)
    c = [(at, "swipe", -20, {})] + [(ra + k * stg, "pop", -22, {"pitch": k}) for k in range(int(p.get("rows", 3)))]
    if p.get("badge"): c += [(ba, "lowhit", -12, {"reveal": True}), (ba, "ding", -23, {})]
    return G.cues_out(c, ctx)

T = {"map_card": (map_card, map_card_cues), "big_words": (big_words, big_words_cues),
     "listing_card": (listing_card, listing_cues), "top3_card": (top3_card, top3_cues)}
