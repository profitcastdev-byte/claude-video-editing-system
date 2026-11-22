"""House templates: one ad look, drawn (PIL). The same moves as HTML motion pieces: motion/pieces/<name>/ (m_<name>).
Roto (behind the head): calendar_card, bars_card, rupee_drift, guarantee_dial, radar.
Cutaway (full-screen stage): month_rows, report_card, contact_form. End: contact_form_end. Chest: big_stat.
Drawn at 1080x1920. Colours come from the style palette (G.MINT = accent). No copy lives here: every word is a param.
ponytail: tall 9:16 layout only; square / wide canvases need the _layout.py treatment the v0.2 templates have."""
import math
from .. import gfx as G
from ..gfx import ease_out, ease_in, back, clamp
from . import El, faded
from .generic import asset

KIND = "roto"
KINDS = {"month_rows": "cutaway", "report_card": "cutaway", "contact_form": "cutaway",
         "contact_form_end": "end", "big_stat": "chest"}

def _F(ctx): return G.fps_of(ctx)
def _Q(ctx): F = _F(ctx); return lambda v: G.q(v, F)
def _deep(a=235): return G.mix(G.CARD, (0, 0, 0), .35) + (a,)
def _out(t, p, ctx, d=.2): return ease_in(G.enter(t, p.get("out_at", ctx["end"] - .25), d, _F(ctx)))
def _cx(ctx, t):
    f = ctx.get("face")
    return (f["cx"], f["eye_y"], f["h"]) if f else (G.W / 2, 620, 420)

# ================================================================== roto: calendar_card (hook: "every single month")
def calendar_card(t, p, ctx):
    """a month grid rises behind the head; booked days tick on a stagger. p: at, eyebrow, fill_at, booked (count), stagger, out_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .35, F)); po = _out(t, p, ctx)
    if pp <= 0 or po >= 1: return []
    x0, x1, top, rows = 50, 1030, 300 + 70 * (1 - pp), 5; pit = (x1 - x0 - 60) / 7; cell = pit - 14
    y1 = top + 40 + rows * pit + 10; a = pp * (1 - po); res = []
    def card(d):
        G.rrect(d, (x0, top, x1, y1), 40, fill=_deep(), outline=G.CARD_B, width=4)
        for r in range(rows):
            for c in range(7):
                cx_, cy_ = x0 + 30 + c * pit + 7, top + 40 + r * pit
                G.rrect(d, (cx_, cy_, cx_ + cell, cy_ + cell), 18, fill=G.SURFACE)
                G.draw_text(d, (cx_ + cell - 16, cy_ + cell - 16), str(r * 7 + c + 1), G.font("sb", 26), G.MUTED, anchor="rs")
    res.append(El(faded(card, a), "roto.cal", "roto", text="calendar", t_key=Q(at)))
    eb = G.tidy(p.get("eyebrow", ""))
    ea = p.get("eyebrow_at", at); pe = ease_out(G.enter(t, ea, .3, F)) * (1 - po)
    if eb and pe > 0: res.append(El(faded(lambda d: G.label(d, G.W / 2, top - 46, eb, 30, col=G.WHITE, tracking=9), pe), "roto.cal.eyebrow", "roto", text=eb, t_key=Q(ea)))
    n = int(p.get("booked", 16)); fa = p.get("fill_at", at + .4); st = p.get("stagger", .05)
    order = sorted(range(rows * 7), key=lambda i: (i * 37) % 35)[:n]          # a fixed scatter of booked days
    def booked(d):
        for j, i in enumerate(order):
            q = G.enter(t, fa + j * st, .22, F)
            if q <= 0: continue
            r, c = divmod(i, 7); cx_, cy_ = x0 + 30 + c * pit + 7, top + 40 + r * pit
            G.rrect(d, (cx_, cy_, cx_ + cell, cy_ + cell), 18, fill=G.mix(G.SURFACE, G.MINT_D, .55 * q), outline=G.MINT_D, width=3)
            G.state(d, "check", cx_ + cell / 2, cy_ + cell / 2 - 6, cell * .26, q)
    if G.enter(t, fa, .22, F) > 0: res.append(El(faded(booked, 1 - po), "roto.cal.booked", "roto", t_key=Q(fa)))
    return res

def calendar_cues(p, ctx):
    at = p.get("at", ctx["start"]); fa = p.get("fill_at", at + .4); st = p.get("stagger", .05)
    return G.cues_out([(at, "swipe", -19, {}), (fa, "pop", -22, {"pitch": 2}), (fa + 4 * st, "pop", -24, {"pitch": 4}), (fa + 9 * st, "ui_tick", -24, {})], ctx)

# ================================================================== cutaway: month_rows ("every month, your clinic gets")
def month_rows(t, p, ctx):
    """rows with an icon well, a mint range and a caps label; each ticks on its word. p: eyebrow, eyebrow_at,
    items [{num, text, at, mark_at, icon}], y (first row top), row_h, gap"""
    F, Q = _F(ctx), _Q(ctx); items = p.get("items", []); res = []
    x0, x1, rh, gap = 110, 970, p.get("row_h", 136), p.get("gap", 30); y0 = p.get("y", 700)
    eb = G.tidy(p.get("eyebrow", "")); ea = p.get("eyebrow_at", ctx["start"])
    box = (x0 - 50, y0 - 150, x1 + 50, y0 + len(items) * (rh + gap) + 40)
    pb = ease_out(G.enter(t, min([i["at"] for i in items] + [ea]), .3, F))
    if pb > 0: res.append(El(faded(lambda d: G.brackets(d, box, L=56, w=3), pb), "rows.brackets", "cutaway"))
    pe = ease_out(G.enter(t, ea, .3, F))
    if eb and pe > 0: res.append(El(faded(lambda d: G.label(d, G.W / 2, y0 - 70 + 16 * (1 - pe), eb, 28, tracking=8), pe), "rows.eyebrow", "cutaway", text=eb, t_key=Q(ea)))
    for k, it in enumerate(items):
        q = ease_out(G.enter(t, it["at"], .28, F))
        if q <= 0: continue
        y = y0 + k * (rh + gap); dx = -60 * (1 - q); mk = G.enter(t, it.get("mark_at", it["at"] + .4), .25, F)
        num, txt = G.tidy(str(it.get("num", ""))), G.tidy(it.get("text", "")).upper()
        def row(d, y=y, dx=dx, num=num, txt=txt, mk=mk, lit=mk > 0):
            G.rrect(d, (x0 + dx, y, x1 + dx, y + rh), 26, fill=G.CARD + (245,), outline=G.MINT_D if lit else G.CARD_B, width=4 if lit else 3)
            w = rh - 36; G.rrect(d, (x0 + dx + 18, y + 18, x0 + dx + 18 + w, y + 18 + w), 18, fill=G.WELL)
            fn = G.font("xb", 64); tx = x0 + dx + 18 + w + 34
            G.draw_text(d, (tx, y + rh / 2 + 23), num, fn, G.MINT)
            G.draw_text(d, (tx + G.text_w(num, fn) + 22, y + rh / 2 + 12), txt, G.fit_font("b", 32, txt, x1 - 110 - tx - G.text_w(num, fn), 1), G.WHITE, tracking=1)
            if mk > 0: G.state(d, "check", x1 + dx - 56, y + rh / 2, 26, mk)
        res.append(El(faded(row, q), f"rows.item{k}", "cutaway", text=f"{num} {txt}", t_key=Q(it["at"])))
        ic = it.get("icon", "event")
        if G.icon_file(ic): res.append(El(faded(lambda d, y=y, dx=dx: G.icon(d, ic, x0 + dx + 18 + (rh - 36) / 2, y + rh / 2, (rh - 36) * .5), q), f"rows.item{k}.icon", "cutaway", asset=ic, t_key=Q(it["at"])))
    return res

def month_rows_cues(p, ctx):
    c = [(p.get("eyebrow_at", ctx["start"]), "swipe", -22, {"trim": (0, .25)})]
    for k, it in enumerate(p.get("items", [])):
        c += [(it["at"], "card", -14, {"pitch": [0, .5, -.5][k % 3]}), (it.get("mark_at", it["at"] + .4), "pop", -16, {"pitch": 2 + k * .5})]
    return G.cues_out(c, ctx)

# ================================================================== cutaway: report_card ("a report full of leads")
def report_card(t, p, ctx):
    """a monthly report card: header + rows whose bars fill, each with a state. p: eyebrow, title, sub, at, icon,
    rows [{text, at, fill (0..1), state (check|xfill|null), state_at}], pill, pill_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .32, F)); res = []
    if pp <= 0: return res
    rows = p.get("rows", []); x0, x1, y0 = 130, 950, p.get("y", 640) + 50 * (1 - pp); rh, gap = 112, 22
    y1 = y0 + 190 + len(rows) * (rh + gap) + (110 if p.get("pill") else 20)
    eb = G.tidy(p.get("eyebrow", ""))
    def card(d):
        G.brackets(d, (x0 - 40, y0 - 120, x1 + 40, y1 + 40), L=56, w=3)
        if eb: G.label(d, G.W / 2, y0 - 50, eb, 28, tracking=8)
        G.rrect(d, (x0, y0, x1, y1), 34, fill=G.CARD + (245,), outline=G.CARD_B, width=3)
        G.rrect(d, (x0 + 34, y0 + 40, x0 + 134, y0 + 140), 20, fill=G.WELL)
        G.draw_text(d, (x0 + 164, y0 + 92), G.tidy(p.get("title", "")).upper(), G.font("xb", 44), G.WHITE, tracking=1)
        G.draw_text(d, (x0 + 164, y0 + 136), G.tidy(p.get("sub", "")), G.font("m", 30), G.MUTED)
        d.line(((x0 + 34, y0 + 172), (x1 - 34, y0 + 172)), fill=G.CARD_B, width=3)
    res.append(El(faded(card, pp), "report.card", "cutaway", text=G.tidy(f"{eb} {p.get('title', '')} {p.get('sub', '')}"), t_key=Q(at)))
    if G.icon_file(p.get("icon", "event")): res.append(El(faded(lambda d: G.icon(d, p.get("icon", "event"), x0 + 84, y0 + 90, 50), pp), "report.icon", "cutaway", asset=p.get("icon", "event"), t_key=Q(at)))
    for k, r in enumerate(rows):
        q = ease_out(G.enter(t, r["at"], .25, F))
        if q <= 0: continue
        y = y0 + 196 + k * (rh + gap); fl = float(r.get("fill", 1)) * ease_out(G.enter(t, r["at"] + .1, .6, F))
        st = r.get("state"); sp = G.enter(t, r.get("state_at", r["at"] + .55), .25, F); txt = G.tidy(r["text"]).upper()
        def row(d, y=y, fl=fl, st=st, sp=sp, txt=txt):
            G.rrect(d, (x0 + 34, y, x1 - 34, y + rh), 22, fill=G.SURFACE, outline=G.CARD_B, width=3)
            G.draw_text(d, (x0 + 70, y + rh / 2 + 12), txt, G.font("b", 32), G.WHITE, tracking=1)
            bx0, bx1 = x1 - 330, x1 - 120
            G.rrect(d, (bx0, y + rh / 2 - 13, bx1, y + rh / 2 + 13), 13, fill=G.mix(G.SURFACE, (0, 0, 0), .4))
            if fl > .02: G.rrect(d, (bx0, y + rh / 2 - 13, bx0 + (bx1 - bx0) * fl, y + rh / 2 + 13), 13, fill=G.NEG if st == "xfill" else G.MINT)
            if st and sp > 0: G.state(d, st, x1 - 76, y + rh / 2, 24, sp)
        res.append(El(faded(row, q), f"report.row{k}", "cutaway", text=txt, t_key=Q(r["at"])))
    pl = G.tidy(p.get("pill", "")); pa = p.get("pill_at", at + 1)
    if pl and G.enter(t, pa, .25, F) > 0:
        pq = G.enter(t, pa, .25, F)
        res.append(El(G.layer(lambda d: G.pill(d, G.W / 2, y1 - 62, pl, G.font("xb", 30), pad=(30, 14), sc=back(pq), text_p=pq)), "report.pill", "cutaway", text=pl, t_key=Q(pa)))
    return res

def report_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = [(at, "card", -14, {})]
    for k, r in enumerate(p.get("rows", [])):
        c.append((r["at"], "ui_tick", -20, {"pitch": k}))
        if r.get("state"): c.append((r.get("state_at", r["at"] + .55), "pop", -18 if r["state"] == "xfill" else -16, {"pitch": -2 if r["state"] == "xfill" else 2}))
    if p.get("pill"): c.append((p.get("pill_at", at + 1), "pop", -20, {"pitch": 3}))
    return G.cues_out(c, ctx)

# ================================================================== roto: bars_card ("paying clients" behind the head)
def bars_card(t, p, ctx):
    """a bar chart behind the head, growing left to right, the last bar lit, a trend line with a dot. p: at, eyebrow,
    values [0..1], stagger, y (baseline), height, out_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); po = _out(t, p, ctx); res = []
    vals = p.get("values", [.22, .3, .42, .55, .74, 1.0]); n = len(vals); st = p.get("stagger", .07)
    base, hmax = p.get("y", 1010), p.get("height", 560); x0, x1 = 70, 1010; pit = (x1 - x0) / n; bw = pit * .62
    if G.enter(t, at, .3, F) <= 0 or po >= 1: return res
    eb = G.tidy(p.get("eyebrow", ""))
    if eb: res.append(El(faded(lambda d: G.label(d, G.W / 2, p.get("eyebrow_y", 190), eb, 30, col=G.WHITE, tracking=9), ease_out(G.enter(t, at, .3, F)) * (1 - po)), "roto.bars.eyebrow", "roto", text=eb, t_key=Q(at)))
    tops = []
    def bars(d):
        for k, v in enumerate(vals):
            q = ease_out(G.enter(t, at + k * st, .45, F)); h = hmax * v * q; bx = x0 + k * pit + (pit - bw) / 2
            tops.append((bx + bw / 2, base - h))
            if h > 2: G.rrect(d, (bx, base - h, bx + bw, base), 12, fill=G.MINT if k == n - 1 else G.mix(G.MINT_D, G.CARD, .25))
    res.append(El(faded(bars, 1 - po), "roto.bars", "roto", text="bars", t_key=Q(at)))
    la = at + n * st + .2; ql = ease_out(G.enter(t, la, .5, F))
    if ql > 0 and len(tops) == n:
        def trend(d):
            pts = [(x, y - 60) for x, y in tops]; m = ql * (n - 1); i = int(m); fr = m - i
            seg = pts[:i + 1] + ([(pts[i][0] + (pts[i + 1][0] - pts[i][0]) * fr, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * fr)] if i < n - 1 else [])
            if len(seg) > 1: d.line(seg, fill=G.WHITE, width=5, joint="curve")
            hx, hy = seg[-1]; d.ellipse((hx - 13, hy - 13, hx + 13, hy + 13), fill=G.WHITE)
        res.append(El(faded(trend, 1 - po), "roto.bars.trend", "roto", t_key=Q(la)))
    return res

def bars_cues(p, ctx):
    at = p.get("at", ctx["start"]); n = len(p.get("values", [0] * 6)); st = p.get("stagger", .07)
    return G.cues_out([(at, "riser_air", -20, {"trim": (0, .5)}), (at + (n - 1) * st, "pop", -18, {"pitch": 3}), (at + n * st + .2, "scribble", -24, {})], ctx)

# ================================================================== roto: rupee_drift ("ad spend of 30,000 rupees")
def rupee_drift(t, p, ctx):
    """a dim marquee band scrolling behind the head + currency glyphs drifting up. p: at, text, glyph, y, count, out_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); po = _out(t, p, ctx); q = ease_out(G.enter(t, at, .3, F)); res = []
    if q <= 0 or po >= 1: return res
    txt = G.tidy(p.get("text", "")); y = p.get("y", 360); f = G.font("xb", p.get("size", 150))
    if txt:
        unit = txt + "  ·  "; uw = G.text_w(unit, f); off = ((t - at) * 140) % uw
        def band(d):
            x = -off
            while x < G.W: G.draw_text(d, (x, y), unit, f, G.mix(G.MINT_D, (0, 0, 0), .15)); x += uw
        res.append(El(faded(band, q * (1 - po)), "roto.marquee", "roto", text=txt, t_key=Q(at)))
    g = p.get("glyph", "₹"); n = int(p.get("count", 12))
    spots = [((60 + (k * 0.618 % 1) * 240) if k % 2 == 0 else (780 + (k * 0.618 % 1) * 240), 330 + (k * 0.382 % 1) * 700) for k in range(n)]
    def drift(d):
        for k, (sx, sy) in enumerate(spots):
            a = G.enter(t, at + k * .06, .3, F)
            if a <= 0: continue
            yy = sy - (t - at) * 55 - k * 3; xx = sx + 14 * math.sin((t - at) * 2.2 + k)
            sz = 1.0 + .5 * ((k * 0.73) % 1)
            G.draw_text(d, (xx, yy), g, G.font("b", int(84 * sz)), G.mix(G.MINT, G.WHITE, .1) + (int(255 * a),), anchor="ms")
    res.append(El(faded(drift, 1 - po), "roto.glyphs", "roto", text=g * 3, t_key=Q(at)))
    return res

def rupee_cues(p, ctx):
    at = p.get("at", ctx["start"])
    return G.cues_out([(at, "whoosh_soft", -18, {}), (at + .12, "pop_bubble", -24, {"pitch": 2}), (at + .36, "pop_bubble", -25, {"pitch": 4})], ctx)

# ================================================================== roto: guarantee_dial ("100% refund")
def guarantee_dial(t, p, ctx):
    """a ring of day ticks around the head, drawing clockwise; eyebrow on top. p: at, ticks (30), dur, r, eyebrow, out_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); po = _out(t, p, ctx); res = []
    if G.enter(t, at, .2, F) <= 0 or po >= 1: return res
    cx, ey, fh = _cx(ctx, t); cy = ey + fh * .12; R = p.get("r", 450); n = int(p.get("ticks", 30)); dur = p.get("dur", .9)
    def ring(d):
        for k in range(n):
            q = G.enter(t, at + dur * k / n, .18, F)
            if q <= 0: continue
            a = -math.pi / 2 + 2 * math.pi * k / n; L = 46 * ease_out(q)
            d.line(((cx + (R - L) * math.cos(a), cy + (R - L) * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))), fill=G.MINT, width=9)
        d.ellipse((cx - R - 26, cy - R - 26, cx + R + 26, cy + R + 26), outline=G.mix(G.MINT_D, (0, 0, 0), .2), width=3)
    res.append(El(faded(ring, 1 - po), "roto.dial", "roto", text="dial", t_key=Q(at)))
    eb = G.tidy(p.get("eyebrow", ""))
    if eb:
        pe = ease_out(G.enter(t, at, .3, F))
        ey_ = min(cy - R - 60, p.get("eyebrow_y", 250))
        res.append(El(faded(lambda d: G.label(d, G.W / 2, ey_, eb, 30, col=G.WHITE, tracking=8), pe * (1 - po)), "roto.dial.eyebrow", "roto", text=eb, t_key=Q(at)))
    return res

def dial_cues(p, ctx):
    at = p.get("at", ctx["start"]); d = p.get("dur", .9)
    return G.cues_out([(at, "riser_sweep", -20, {"trim": (0, d)}), (at + d, "ring", -18, {})], ctx)

# ================================================================== roto: radar ("do you run a hair and skin clinic?")
def radar(t, p, ctx):
    """rings round the head, a sweep turning, blips lighting as it passes; a label pill on top. p: at, label, blips, out_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); po = _out(t, p, ctx); q = ease_out(G.enter(t, at, .35, F)); res = []
    if q <= 0 or po >= 1: return res
    cx, ey, fh = _cx(ctx, t); cy = ey + fh * .15; Rs = (260, 400, 540); ang = (t - at) * 2.4 - math.pi / 2
    def rings(d):
        for k, R in enumerate(Rs):
            r = R * (.85 + .15 * q); d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=G.MINT_D, width=4)
        for j in range(14):                                          # the sweep: a fading fan behind the leading edge
            a1 = ang - j * .05; c = G.mix(G.MINT, G.MINT_D, j / 14) + (int(190 * (1 - j / 14)),)
            d.pieslice((cx - Rs[-1], cy - Rs[-1], cx + Rs[-1], cy + Rs[-1]), math.degrees(a1 - .05), math.degrees(a1), fill=c)
    res.append(El(faded(rings, q * (1 - po)), "roto.radar", "roto", text="radar", t_key=Q(at)))
    bl = p.get("blips", [(-.9, 1), (-.3, 2), (.4, 1), (1.1, 2), (2.0, 0), (2.7, 1), (3.6, 2)])
    def blips(d):
        for a, ri in bl:
            hit = at + ((a + math.pi / 2) % (2 * math.pi)) / 2.4
            if t < hit: continue
            k = clamp((t - hit) / .25); R = Rs[ri]; x, y = cx + R * math.cos(a), cy + R * math.sin(a); r = 22 * back(k)
            d.ellipse((x - r - 10, y - r - 10, x + r + 10, y + r + 10), outline=G.MINT, width=3)
            d.ellipse((x - r * .55, y - r * .55, x + r * .55, y + r * .55), fill=G.MINT)
    res.append(El(faded(blips, 1 - po), "roto.radar.blips", "roto", t_key=Q(at + .3)))
    lb = G.tidy(p.get("label", "")); la = p.get("label_at", at); ql = ease_out(G.enter(t, la, .3, F))
    if lb and ql > 0: res.append(El(G.layer(lambda d: G.pill(d, cx, cy - Rs[-1] - 10, lb, G.font("xb", 28), filled=False, pad=(28, 14), sc=back(ql), text_p=ql * (1 - po))), "roto.radar.label", "roto", text=lb, t_key=Q(la)))
    return res

def radar_cues(p, ctx):
    at = p.get("at", ctx["start"]); return G.cues_out([(at, "swipe", -20, {}), (at + .45, "ding", -26, {"pitch": 5}), (at + .9, "ding", -27, {"pitch": 7})], ctx)

# ================================================================== cutaway / end: contact_form ("click the link below")
def contact_form(t, p, ctx):
    """the contact card: eyebrow, title, fields typing in, the accent button, a press with a ripple, a status line.
    p: eyebrow, title, at, fields [{icon, text, at}], button, button_at, press_at, done, status, status_at, logo, logo_at"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); pp = ease_out(G.enter(t, at, .32, F)); res = []
    if pp <= 0: return res
    fields = p.get("fields", []); x0, x1 = 150, 930; y0 = p.get("y", 640) + 50 * (1 - pp); fh, gap = 100, 24
    y1 = y0 + 150 + len(fields) * (fh + gap) + 170; eb = G.tidy(p.get("eyebrow", ""))
    def card(d):
        G.brackets(d, (x0 - 50, y0 - 130, x1 + 50, y1 + 150), L=56, w=3)
        if eb: G.label(d, G.W / 2, y0 - 56, eb, 28, tracking=8)
        G.rrect(d, (x0, y0, x1, y1), 36, fill=G.CARD + (245,), outline=G.CARD_B, width=3)
        G.draw_text(d, (G.W / 2, y0 + 96), G.tidy(p.get("title", "")), G.font("b", 48), G.WHITE, anchor="ms")
        for k in range(len(fields)):
            y = y0 + 150 + k * (fh + gap); G.rrect(d, (x0 + 40, y, x1 - 40, y + fh), 20, fill=G.SURFACE, outline=G.CARD_B, width=3)
    res.append(El(faded(card, pp), "form.card", "cutaway", text=G.tidy(f"{eb} {p.get('title', '')}"), t_key=Q(at)))
    for k, fd in enumerate(fields):
        fa = fd.get("at", at + .3 + k * .35); n = len(G.tidy(fd["text"])); typed = int(n * clamp((t - fa) / max(.15, n * .035)))
        if t < fa: continue
        y = y0 + 150 + k * (fh + gap); s = G.tidy(fd["text"])[:max(1, typed)]
        res.append(El(G.layer(lambda d, y=y, s=s: G.draw_text(d, (x0 + 130, y + fh / 2 + 12), s, G.font("m", 34), G.WHITE)), f"form.field{k}", "cutaway", text=G.tidy(fd["text"]), t_key=Q(fa)))
        if G.icon_file(fd.get("icon")): res.append(El(G.layer(lambda d, y=y, ic=fd["icon"]: G.icon(d, ic, x0 + 88, y + fh / 2, 40, col=G.MUTED)), f"form.field{k}.icon", "cutaway", asset=fd["icon"], t_key=Q(fa)))
    ba = p.get("button_at", at + 1.2); pb = G.enter(t, ba, .3, F); pr = p.get("press_at"); bt = G.tidy(p.get("button", ""))
    if bt and pb > 0:
        pressed = pr is not None and t >= pr; k = clamp((t - pr) / .5) if pressed else 0
        lab = G.tidy(p.get("done", bt)) if pressed and t >= pr + .12 else bt; by = y1 - 95
        def btn(d):
            sc = back(pb) * (1 - .06 * math.sin(math.pi * clamp((t - pr) / .16))) if pressed else back(pb)
            G.pill(d, G.W / 2, by, lab, G.font("xb", 32), pad=(70, 26), sc=sc, text_p=pb)
            if pressed and k < 1:
                r = 160 + 260 * ease_out(k); d.ellipse((G.W / 2 - r, by - r * .32, G.W / 2 + r, by + r * .32), outline=G.MINT + (int(255 * (1 - k)),), width=4)
        res.append(El(G.layer(btn), "form.button", "cutaway", text=lab, t_key=Q(pr if pressed else ba)))
    stt = G.tidy(p.get("status", "")); sa = p.get("status_at", ba + .6); ps = G.enter(t, sa, .3, F)
    if stt and ps > 0:
        def status(d):
            f = G.font("sb", 32); w = G.text_w(stt, f); x = G.W / 2 - (w + 44) / 2; yy = y1 + 86
            pulse = 1 + .25 * math.sin((t - sa) * 6)
            d.ellipse((x + 12 - 12 * pulse, yy - 12 - 12 * pulse, x + 12 + 12 * pulse, yy - 12 + 12 * pulse), fill=G.MINT)
            G.draw_text(d, (x + 44, yy), stt, f, G.WHITE)
        res.append(El(faded(status, ps), "form.status", "cutaway", text=stt, t_key=Q(sa)))
    lg = p.get("logo"); la = p.get("logo_at", at)
    if lg and G.enter(t, la, .3, F) > 0:
        im = G.image(asset(ctx, lg)); pl = ease_out(G.enter(t, la, .3, F)); w = p.get("logo_w", 360)
        res.append(El(G.layer(lambda d: d.paste(im, (G.W - w) / 2, y0 - 330 + 20 * (1 - pl), w, opacity=pl)), "form.logo", "cutaway", text="logo", asset=lg, t_key=Q(la)))
    return res

def contact_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = [(at, "card", -14, {})] if at >= ctx["start"] else []
    for k, fd in enumerate(p.get("fields", [])):
        fa = fd.get("at", at + .3 + k * .35)
        if fa >= ctx["start"]: c.append((fa, "keyboard", -22, {"trim": (0, .4)}))
    ba = p.get("button_at", at + 1.2)
    if ba >= ctx["start"]: c.append((ba, "pop", -16, {"pitch": 3}))
    if p.get("press_at") is not None and p["press_at"] >= ctx["start"]: c += [(p["press_at"], "button", -14, {}), (p["press_at"] + .12, "ding", -20, {})]
    la = p.get("logo_at")
    if p.get("logo") and la is not None and la >= ctx["start"]: c.append((la, "lowhit", -14, {}))
    return G.cues_out(c, ctx)

# ================================================================== chest: big_stat ("100% / REFUND" on the chest, as in the Dentist ad)
def big_stat(t, p, ctx):
    """a big accent number counting up + a tracked caps word under it. p: value, suffix, at, count (dur), label, label_at, y, size"""
    F, Q = _F(ctx), _Q(ctx); at = p.get("at", ctx["start"]); pp = G.enter(t, at, .25, F); res = []
    if pp <= 0: return res
    v = float(p.get("value", 100)) * ease_out(G.enter(t, at, p.get("count", .6), F)); y = p.get("y", 1400)
    num = f"{int(round(v))}{p.get('suffix', '%')}"; f = G.font("xb", p.get("size", 190))
    res.append(El(faded(lambda d: G.draw_text(d, (G.W / 2, y + 30 * (1 - back(pp))), num, f, G.MINT, anchor="ms"), min(1, pp * 2)), "chest.stat", "chest", text=num, t_key=Q(at), size=p.get("size", 190)))
    lb = G.tidy(p.get("label", "")); la = p.get("label_at", at + .3); pl = ease_out(G.enter(t, la, .3, F))
    if lb and pl > 0: res.append(El(faded(lambda d: G.draw_text(d, (G.W / 2, y + 92 + 14 * (1 - pl)), lb, G.font("sb", 50), G.WHITE, tracking=14, anchor="ms"), pl), "chest.stat.label", "chest", text=lb, t_key=Q(la)))
    return res

def big_stat_cues(p, ctx):
    at = p.get("at", ctx["start"]); return G.cues_out([(at, "lowhit", -10, {"reveal": True}), (at + p.get("count", .6), "pop_bright", -18, {})], ctx)

T = {"calendar_card": (calendar_card, calendar_cues), "month_rows": (month_rows, month_rows_cues), "report_card": (report_card, report_cues),
     "bars_card": (bars_card, bars_cues), "rupee_drift": (rupee_drift, rupee_cues), "guarantee_dial": (guarantee_dial, dial_cues),
     "radar": (radar, radar_cues), "contact_form": (contact_form, contact_cues), "contact_form_end": (contact_form, contact_cues),
     "big_stat": (big_stat, big_stat_cues)}
