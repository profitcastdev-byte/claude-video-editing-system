"""Roto templates: drawn BEHIND the presenter (person matte composited on top). House rule: <= 4 moments, each <= 3 s.
Cards sit high so their top edge stays visible above the head. Pins, rows and badges are their own elements, so their
cues have a logged visual event (SND-07). Colours come from the palette (gfx); no copy lives here."""
from .. import gfx as G
from ..gfx import ease_out, ease_in, back, clamp

KIND = "roto"
DESIGN = True             # fixed 1080x1920 layout: fitted into the canvas safe zone on other canvases (templates._canvas_render)
def _el(): from . import El, faded; return El, faded
def _t(ctx): F = G.fps_of(ctx); return F, (lambda v: G.q(v, F))
def _deep(a=235): return G.mix(G.CARD, (0, 0, 0), .35) + (a,)          # roto card body: a darker card, slightly see-through

def map_card(t, p, ctx):
    """a map card: search bar + roads drawing in + pins popping. p: at (card in), draw_at (roads), pins_at, pins (count, <= 6), pin_stagger"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F))
    pm = G.enter(t, p.get("draw_at", at + .6), .9, F); res = []
    if pp <= 0: return res
    y = 200 + 40 * (1 - pp)
    def card(d):
        G.rrect(d, (170, y, 910, y + 880), 44, fill=_deep(), outline=G.CARD_B, width=4)
        G.brackets(d, (140, y - 30, 940, y + 910), L=60)
        G.rrect(d, (220, y + 44, 860, y + 104), 30, fill=G.SURFACE); G.icon(d, "search", 262, y + 74, 30, col=G.MUTED)
        roads = [((170, y + 330), (910, y + 250)), ((350, y + 120), (420, y + 880)), ((170, y + 600), (910, y + 700)), ((700, y + 120), (640, y + 880)), ((170, y + 460), (520, y + 880))]
        for k, (a, b) in enumerate(roads):
            qv = clamp(pm * 1.6 - k * .15)
            if qv > 0: d.line((a, (a[0] + (b[0] - a[0]) * qv, a[1] + (b[1] - a[1]) * qv)), fill=G.mix(G.CARD_B, G.MINT_D, .6), width=10)
    res.append(El(faded(card, pp), "roto.map", "roto", text="map", t_key=Q(at)))
    pins = ((300, 250), (780, 200), (250, 520), (820, 560), (560, 400), (420, 700))[:int(p.get("pins", 4))]
    for k, (px, py) in enumerate(pins):
        pa = p.get("pins_at", at + 1.0) + k * p.get("pin_stagger", .1); qv = G.enter(t, pa, .2, F)
        if qv > 0: res.append(El(G.layer(lambda d, px=px, py=py, qv=qv: G.icon(d, "pin", px, y + py, 54 * max(0, back(qv)))), f"roto.map.pin{k}", "roto", t_key=Q(pa), asset="pin"))
    return res

def big_words(t, p, ctx):
    """huge words slam in behind the head. p: words [[WORD, at, accent?]], out_at, ys?, size (200), accent_size (270), color, accent_color"""
    El, faded = _el(); F, Q = _t(ctx); out_p = ease_in(G.enter(t, p.get("out_at", ctx["end"] - .3), .2, F)); res = []
    ys = p.get("ys", [400, 610, 860]); sz = G.safe(); maxw = sz[2] - sz[0]
    for k, (wd, at, *acc) in enumerate(p.get("words", [])):
        qv = G.enter(t, at, .14, F); acc = bool(acc and acc[0])
        if qv <= 0: continue
        sc = 1 + .35 * (1 - ease_out(qv)); base = p.get("accent_size", 270) if acc else p.get("size", 200); y = ys[min(k, len(ys) - 1)]
        wd = G.tidy(wd); f = G.fit_font("xb", int(base * sc), wd, maxw * sc, 4)
        c = G.col(p.get("accent_color"), G.MINT) if acc else G.col(p.get("color"), G.WHITE)
        def word(d, wd=wd, y=y, f=f, c=c, sc=sc):
            G.draw_text(d, (540, y + 60 * (sc - 1) - 120 * out_p), wd, f, c, tracking=4, anchor="ms")    # ink-centred: every line on one axis (GFX-08)
        res.append(El(faded(word, min(1, qv * 2) * (1 - out_p)), f"roto.word{k}", "roto", text=wd, t_key=Q(at)))
    return res

def listing_card(t, p, ctx):
    """a listing / profile card rising behind the head (map strip, pin, rating). p: at, stars (0-5), stars_at"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F))
    if pp <= 0: return []
    y = 180 + 120 * (1 - pp); res = []
    def listing(d):
        G.rrect(d, (150, y, 930, y + 900), 44, fill=_deep(240), outline=G.CARD_B, width=4)
        G.brackets(d, (120, y - 30, 960, y + 930), L=60)
        G.rrect(d, (200, y + 44, 880, y + 104), 30, fill=G.SURFACE); G.icon(d, "search", 242, y + 74, 30, col=G.MUTED)
        G.rrect(d, (200, y + 130, 880, y + 330), 24, fill=G.SURFACE)
        for a, b in (((200, y + 210), (880, y + 170)), ((480, y + 130), (540, y + 330))): d.line((a, b), fill=G.mix(G.CARD_B, G.MINT_D, .6), width=9)
        G.icon(d, "pin", 700, y + 220, 60)
    res.append(El(faded(listing, pp), "roto.listing", "roto", text="listing", t_key=Q(at)))
    sa = p.get("stars_at", at + .2); ps = G.enter(t, sa, .35, F); n = int(p.get("stars", 5))
    if ps > 0 and n:
        def stars(d):
            for j in range(n):
                qv = clamp(ps * n * 1.3 - j)
                if qv > 0: G.icon(d, "star", 230 + j * 34, y + 380, 24 * back(qv), col=G.STAR)
        res.append(El(G.layer(stars), "roto.listing.stars", "roto", t_key=Q(sa), asset="star"))
    return res

def top3_card(t, p, ctx):
    """a ranked-results card + a badge (e.g. a 'top N' badge). p: at, badge (text), badge_at, rows (count), rows_at"""
    El, faded = _el(); F, Q = _t(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F)); res = []
    y = 260 + 100 * (1 - pp); n = int(p.get("rows", 3)); ra = p.get("rows_at", at + 1.0); stg = p.get("row_stagger", .12)
    def pack(d):
        G.rrect(d, (150, y, 930, y + 860), 44, fill=_deep(240), outline=G.CARD_B, width=4)
        G.brackets(d, (120, y - 30, 960, y + 890), L=60)
        for k in range(n):
            yy = y + 120 + k * 150
            G.rrect(d, (190, yy, 890, yy + 120), 24, fill=G.SURFACE, outline=G.CARD_B, width=3)
            G.icon(d, "pin", 240, yy + 60, 46, col=G.MUTED)
    if pp > 0: res.append(El(faded(pack, pp), "roto.pack", "roto", text="map pack", t_key=Q(at)))
    for k in range(n):                       # each row lights up as its own element (a visual event for its cue)
        qv = ease_out(G.enter(t, ra + k * stg, .18, F))
        if qv <= 0 or pp <= 0: continue
        def hi(d, k=k):
            yy = y + 120 + k * 150
            G.rrect(d, (190, yy, 890, yy + 120), 24, fill=G.mix(G.SURFACE, G.MINT_D, .35), outline=G.MINT_D, width=3)
            G.icon(d, "pin", 240, yy + 60, 46, col=G.MINT)
        res.append(El(faded(hi, qv), f"roto.pack.row{k}", "roto", t_key=Q(ra + k * stg)))
    pb = G.enter(t, p.get("badge_at", at + .7), .25, F); txt = G.tidy(p.get("badge", ""))
    if pb > 0 and txt:
        res.append(El(G.layer(lambda d: G.pill(d, 540, 300, txt, G.font("xb", 52), pad=(35, 18), sc=back(pb), text_p=pb)), "roto.badge", "roto", text=txt, t_key=Q(p.get("badge_at", at + .7))))
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
