"""Full-screen cutaways on the stage (UI cards, typed searches, counters). Content builds on the spoken words.
Every element has an entry (fade / slide / scale from its own centre), every animation start is quantised to a whole frame
(G.enter / G.q), and every cue lands on the frame its visual event appears (G.cues_out). No copy lives here: every string
comes from params. Relative templates: laid out per canvas shape (templates/_layout.py: the original vertical layout on
9:16, a scaled arrangement on square canvases, a landscape arrangement on wide ones) inside the style's safe zone, and
rasterised at the canvas's real resolution."""
import numpy as np
from PIL import Image, ImageFilter
from .. import gfx as G
from ..gfx import prog, ease_out, back
from . import _layout as LY

KIND = "cutaway"
def _el(): from . import El, faded; return El, faded
def _t(ctx): F = G.fps_of(ctx); return F, (lambda v: G.q(v, F))

# ------------------------------------------------------------------ search_rows
def _search_geo(n):
    """(s, X0, X1, cx, Y) for n rows. Tall: the 1080x1920 numbers (X0 110, X1 970 = the shared left / right edge of the head
    pill and the rows, GFX-08; Y(v) = v). Square: the same block scaled to fit. Wide: wider rows, type scaled up to the zone."""
    m = LY.mode(); bot = max(1250, 790 + (n - 1) * 140 + 116 + 64)          # the block: label (560) .. brackets bottom
    if m == "tall":
        dy = LY.tall_dy(); return 1.0, 110, 970, 540, (lambda v: v + dy), (560, 1250)
    z = LY.zone(); bh = bot - 560
    if m == "wide":
        s = LY.fit(920, bh, grow=1.3); half = min(z[4] * .47, max(460 * s, z[4] * .36))
    else:
        s = LY.fit(920, bh, grow=1.0); half = 430 * s + 30 * s
    y0 = z[7] - bh * s / 2
    return s, z[6] - half + 30 * s, z[6] + half - 30 * s, z[6], (lambda v: y0 + (v - 560) * s), (560, bot)

def search_rows(t, p, ctx):
    """typed search rows. p: label, pills [left, right], pill_times {left: [start, dur], plus: t, right: t}, rows [{q, type:[a,b], tag, check, stars?}],
    tag_text, enter (t first element lands), rows_in"""
    El, faded = _el(); out = []; F, Q = _t(ctx)
    s, X0, X1, cx, Y, (b0, b1) = _search_geo(len(p.get("rows", [])))
    enter = p.get("enter", ctx["start"] - .15); entry = G.mo("entry_s", .28)
    pT = ease_out(G.enter(t, enter, entry, F)); pt = p.get("pill_times", {}) or {}
    pills = list(p.get("pills") or ["", ""]) + ["", ""]; lw, rw = G.tidy(pills[0]), G.tidy(pills[1])
    pW = G.enter(t, *pt["left"], F) if "left" in pt else G.enter(t, enter + .3, .45, F)
    lab = G.tidy(p.get("label", ""))
    if lab and pT > 0:
        out.append(El(faded(lambda d: G.label(d, cx, Y(600), lab, 26 * s), pT), "search.label", "cutaway", text=lab, t_key=Q(enter)))
    hx1 = X0 + 450 * s                                                  # the head pill: 450 px wide, the "+" just after it
    if pT > 0:
        def head(d):
            f = G.font("b", 34 * s); vis = lw[:int(len(lw) * pW + .999)] if pW > 0 else ""
            dy = G.mo("slide_px", 50) * .4 * (1 - pT) * s
            G.rrect(d, (X0, Y(640) + dy, hx1, Y(724) + dy), 42 * s, outline=G.WHITE, width=3 * s)
            if vis: G.draw_text(d, ((X0 + hx1) / 2, Y(695) + dy), vis, f, G.WHITE, tracking=2, anchor="ms")
            if "plus" in pt and t >= Q(pt["plus"]) - .5 / (F or 60):
                G.draw_text(d, (hx1 + 53 * s, Y(698) + dy), "+", G.font("b", 44 * s), G.WHITE, anchor="ms")
        out.append(El(faded(head, pT), "search.head", "cutaway", text=lw, t_key=Q(enter)))
    pN = G.enter(t, pt.get("right", enter + 1.1), .3, F)
    if pN > 0 and rw:
        rx = X1 - 150 * s if LY.mode() != "tall" else 820                   # the right pill ends near the row edge
        def near(d): G.pill(d, rx, Y(682), rw, G.font("b", 34 * s), pad=(34 * s, 25 * s), sc=back(pN), text_p=pN)
        out.append(El(G.layer(near), "search.pill", "cutaway", text=rw, t_key=Q(pt.get("right", enter + 1.1))))
    tag = G.tidy(p.get("tag_text", ""))
    rows_in = p.get("rows_in", enter + 1.3); stg = G.mo("stagger_s", .12)
    for k, r in enumerate(p.get("rows", [])):
        a, b = r["type"]; chk = r.get("check"); tg = r.get("tag")
        r_at = rows_in + k * stg; pp = ease_out(G.enter(t, r_at, .3, F))
        if pp <= 0: continue
        def row(d, k=k, r=r, a=a, b=b, chk=chk, tg=tg, pp=pp):
            y = Y(790 + k * 140) + 30 * (1 - pp) * s                     # rises into place while fading in (MOT-12)
            done = chk is not None and t >= Q(chk) - .5 / (F or 60)
            G.rrect(d, (X0, y, X1, y + 116 * s), 24 * s, fill=G.CARD + (245,), outline=(G.MINT_D if done else G.CARD_B), width=3 * s)
            G.icon(d, "search", X0 + 50 * s, y + 46 * s, 34 * s, col=G.MUTED)
            tp = G.enter(t, a, b - a, F); qs = G.tidy(r["q"]); st = qs[:int(len(qs) * tp + .999)] if tp > 0 else ""
            f = G.font("m", 36 * s)
            if st: G.draw_text(d, (X0 + 90 * s, y + 60 * s), st, f, G.WHITE)
            tx = X0 + 90 * s + G.text_w(st, f) + 8 * s
            if a <= t < (tg if tg is not None else b) and int(t * 2.4) % 2 == 0: d.line((tx, y + 28 * s, tx, y + 66 * s), fill=G.MINT, width=3 * s)
            qq = G.enter(t, tg, .22, F) if (tg is not None and tag) else 0
            if qq > 0:
                ft = G.font("sb", 24 * s); tw = G.text_w(tag, ft) + 30 * s; sc = back(qq); x0 = tx + 14 * s
                G.rrect(d, (x0, y + (60 - 22 * sc) * s, x0 + tw * sc, y + (60 + 14 * sc) * s), 18 * s, fill=G.MINT_D)
                if qq > .5: G.draw_text(d, (x0 + 15 * s, y + 61 * s), tag, ft, G.mix(G.WHITE, G.MINT, .25))
            if done:
                G.state(d, "check", X1 - 50 * s, y + 58 * s, 22 * s, G.enter(t, chk, .22, F)); ps = G.enter(t, chk + .05, .3, F)
                for j in range(int(r.get("stars", 5))):
                    if ps * 5 > j: G.icon(d, "star", X0 + (106 + j * 30) * s, y + 92 * s, 20 * s, col=G.STAR)
                d.line((X0 + 270 * s, y + 92 * s, X0 + (270 + 220 * ease_out(ps)) * s, y + 92 * s), fill=G.SURFACE, width=6 * s)
        out.append(El(faded(row, pp), f"search.row{k}", "cutaway", text=G.tidy(r["q"]), t_key=Q(r_at), asset="search"))
    if pT > 0: out.append(El(faded(lambda d: G.brackets(d, (X0 - 30 * s, Y(b0), X1 + 30 * s, Y(b1)), L=46 * s, w=3 * s), pT), "search.brackets", "cutaway"))
    return out

def search_rows_cues(p, ctx):
    c = []; pt = p.get("pill_times", {}) or {}
    if "left" in pt: c.append((pt["left"][0], "keyboard", -22, {"trim": (1.0, 1.0 + pt["left"][1])}))
    if "plus" in pt: c.append((pt["plus"], "pop", -24, {"pitch": -3}))
    if "right" in pt: c.append((pt["right"], "pop", -16, {}))
    for k, r in enumerate(p.get("rows", [])):
        a, b = r["type"]; c.append((a, "keyboard", -22, {"trim": (1.0, 1.0 + b - a)}))
        if r.get("tag") is not None and p.get("tag_text"): c.append((r["tag"], "pop", -21, {"pitch": 3}))
        if r.get("check") is not None: c.append((r["check"], "ding", -26, {"pitch": [0, 1, -1, 2][k % 4]}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ card_list (check / cross list)
def _list_geo(n, lab, top_p):
    """[(x, y) per item], card w, s, (bracket box), label centre x / baseline. Tall: the 1080x1920 numbers (cards at x 120,
    840 x 124 every 150 px from `top`). Square: scaled to fit. Wide: two columns (column-major: reading order runs down the
    left column first) once there are 3+ items, type scaled up to fill the zone."""
    m = LY.mode()
    if m == "tall":
        top = top_p if top_p is not None else (640 if not lab else 750); top += LY.tall_dy()
        pos = [(120, top + k * 150) for k in range(n)]
        return pos, 840, 1.0, (80, top - 40 - (70 if lab else 0), 1000, top + n * 150 + 10), (540, top - 50)
    z = LY.zone(); cols = 2 if (m == "wide" and n >= 4) else 1; rows = -(-n // cols)
    lh = 120 if lab else 0; bh = rows * 150 - 26 + lh + 80                  # label + cards + bracket margins, at s = 1
    gap = 60
    s = LY.fit(cols * (600 if cols == 2 else 840) + (cols - 1) * gap + 80, bh, grow=1.3 if m == "wide" else 1.0)
    cw = min(840 * s * (1.12 if cols == 2 else 1.25 if m == "wide" else 1), (z[4] * .94 - 80 * s - (cols - 1) * gap * s) / cols)
    tw = cols * cw + (cols - 1) * gap * s; x0 = z[6] - tw / 2
    y0 = z[7] - bh * s / 2 + (40 + lh) * s                                  # first card top
    pos = [(x0 + (k // rows) * (cw + gap * s), y0 + (k % rows) * 150 * s) for k in range(n)]
    return pos, cw, s, (x0 - 40 * s, y0 - (40 + lh) * s, x0 + tw + 40 * s, y0 + rows * 150 * s + 10 * s), (z[6], y0 - 50 * s)

def card_list(t, p, ctx):
    """cards building one by one. p: label (optional), label_at, items [{icon, title, sub, at, state: check|cross|null, state_at}], top (y of first card)"""
    El, faded = _el(); out = []; F, Q = _t(ctx); items = p.get("items", []); lab = G.tidy(p.get("label", ""))
    pos, cw, s, box, (lx, ly) = _list_geo(len(items), lab, p.get("top") if LY.mode() == "tall" else None)
    entry = G.mo("entry_s", .28); slide = G.mo("slide_px", 50) * .72 * s
    pB = ease_out(G.enter(t, min([it["at"] for it in items] + [ctx["start"]]), entry, F))
    if lab:
        la = p.get("label_at", ctx["start"] - .15); pl = ease_out(G.enter(t, la, .3, F))
        if pl > 0: out.append(El(faded(lambda d: G.label(d, lx, ly, lab, 26 * s), pl), "list.label", "cutaway", text=lab, t_key=Q(la)))
    for k, it in enumerate(items):
        pp = ease_out(G.enter(t, it["at"], entry, F))
        if pp <= 0: continue
        (x, y) = pos[k]; st = it.get("state"); sa = it.get("state_at", it["at"] + .25)
        sp = G.enter(t, sa, .25, F)
        out.append(El(faded(lambda d, x=x, y=y, it=it, pp=pp, st=st, sp=sp: G.card_row(d, x - slide * (1 - pp), y, cw, 124 * s, it.get("icon"), G.tidy(it["title"]), G.tidy(it.get("sub")) or None,
                                                                                         st if (st and sp > 0) else None, 1, sp, sc=s), pp),
                      f"list.item{k}", "cutaway", text=G.tidy(f"{it['title']} {it.get('sub') or ''}"), t_key=Q(it["at"]), asset=it.get("icon")))
    if pB > 0: out.append(El(faded(lambda d: G.brackets(d, box, L=46 * s, w=3 * s), pB), "list.brackets", "cutaway"))
    return out

def card_list_cues(p, ctx):
    c = []
    if p.get("label") and p.get("label_at") is not None: c.append((p["label_at"], "swipe", -22, {"trim": (0, .25)}))
    for k, it in enumerate(p.get("items", [])):
        c.append((it["at"], "card", -14, {"pitch": [0, .5, -.5, 1][k % 4]}))
        if it.get("state"): c.append((it.get("state_at", it["at"] + .25), "pop", -19 if it["state"] == "cross" else -16, {"pitch": (-2 if it["state"] == "cross" else 2) + (k % 3) * .4}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ counter / stat (big number)
def _counter_geo(y, icon, label, unit, pill, final="", size=230):
    """(s, y baseline, centre x). Tall: y 960 (or p.y), sizes as designed. Square / wide: the block (icon -406 .. pill +225
    around the baseline) centred in the safe zone and scaled to fill its height (up to 1.3x on wide canvases)."""
    m = LY.mode(); z = LY.zone()
    if m == "tall": return 1.0, (960 + LY.tall_dy()) if y is None else y, 540
    top = 406 if icon else (266 if label else 230); bot = 225 if pill else (130 if unit else 40)
    bw = max(560, G.text_w(final, G.font("xb", size)) + 80, G.text_w(G.tidy(label or ""), G.font("sb", 26), 7) + 80)
    s = LY.fit(bw, top + bot, grow=1.5)
    return s, (z[7] - (top + bot) * s / 2 + top * s) if y is None else y, z[6]

def counter(t, p, ctx):
    """a number counting up. p: value, count [start, dur], start_value, prefix, suffix, suffix_at, decimals, grouping (intl|indian|none),
    size, color, icon (or null), icon_at, label, label_at, label_mode (type|fade), unit (caption under the number), unit_at, pill, pill_at,
    align (center|left), y (number baseline)"""
    El, faded = _el(); out = []; F, Q = _t(ctx)
    v_ = float(p.get("value", 0)); fin_ = f"{p.get('prefix', '')}{G.fmt_num(v_, int(p.get('decimals', 0)), p.get('grouping'))}{p.get('suffix', '')}"
    s, y, cx = _counter_geo(p.get("y"), p.get("icon"), p.get("label"), p.get("unit"), p.get("pill"), fin_, p.get("size", 230))
    align = p.get("align", "center"); sz = G.safe(); ax = cx if align == "center" else sz[0] + p.get("pad", 60)
    anc = "ms" if align == "center" else "li"
    ia = p.get("icon_at", ctx["start"] - .15); la = p.get("label_at", ctx["start"])
    pi = G.enter(t, ia, .3, F); lab = G.tidy(p.get("label", ""))
    pl = G.enter(t, la, .35 if p.get("label_mode", "type") == "type" else .3, F)
    if p.get("icon") and pi > 0:
        def ic(d):
            sq = 92 * back(pi) * s; icx = cx if align == "center" else ax + 46 * s; iy = y - 360 * s
            G.rrect(d, (icx - sq / 2, iy - sq / 2, icx + sq / 2, iy + sq / 2), 22 * back(pi) * s, fill=G.WELL)
            if pi > .5: G.icon(d, p["icon"], icx, iy, 46 * min(1, back(pi)) * s)
        out.append(El(G.layer(ic), "counter.icon", "cutaway", asset=p["icon"], t_key=Q(ia)))
    if lab and pl > 0:
        ly = y - 240 * s; fl = 26 * s
        if p.get("label_mode", "type") == "type":
            out.append(El(G.layer(lambda d: G.label(d, ax, ly, lab[:int(len(lab) * pl + .999)], fl) if align == "center" else
                                  G.draw_text(d, (ax, ly), lab[:int(len(lab) * pl + .999)], G.font("sb", fl), G.MUTED, tracking=7, anchor="li")),
                          "counter.head", "cutaway", text=lab, t_key=Q(la)))
        else:
            out.append(El(faded(lambda d: G.draw_text(d, (ax, ly + 20 * (1 - ease_out(pl)) * s), lab, G.font("sb", fl), G.MUTED, tracking=7, anchor=anc), ease_out(pl)),
                          "counter.head", "cutaway", text=lab, t_key=Q(la)))
    a, dur = p.get("count", [ctx["start"], .8]); v = float(p.get("value", 0)); v0 = float(p.get("start_value", 0)); dec = int(p.get("decimals", 0))
    pc = G.enter(t, a, dur, F)
    if pc > 0:
        n = G.count_value(v, Q(a) - .5 / (F or 60), dur, t, v0); suf = p.get("suffix", "")
        shown_suf = suf if (suf and t >= Q(p.get("suffix_at", a + dur)) - .5 / (F or 60)) else ""
        txt = f"{p.get('prefix', '')}{G.fmt_num(n, dec, p.get('grouping'))}{shown_suf}"
        final = f"{p.get('prefix', '')}{G.fmt_num(v, dec, p.get('grouping'))}{suf}"
        cc = G.col(p.get("color"), G.MINT); sc = .7 + .3 * back(min(1, pc * 2.5))
        f = G.fit_font("xb", int(p.get("size", 230) * s * sc), final, (sz[2] - sz[0]) - 80 * s)
        def num(d): G.draw_text(d, (ax, y), txt, f, cc, anchor=anc)
        im = G.layer(num); glow = Image.fromarray(np.asarray(im)[..., 3]).filter(ImageFilter.GaussianBlur(G.px(28 * s)))
        g = Image.new("RGBA", im.size, cc + (0,)); g.putalpha(glow.point(lambda x: int(x * .45)))
        out += [El(g, "counter.glow", "cutaway"), El(G.alpha(im, min(1, pc * 4)), "counter.value", "cutaway", text=final, t_key=Q(a))]
    ua = p.get("unit_at", a + dur); pq = ease_out(G.enter(t, ua, .3, F)); unit = G.tidy(p.get("unit", ""))
    if pq > 0 and unit:
        out.append(El(faded(lambda d: G.draw_text(d, (ax, y + (90 + 24 * (1 - pq)) * s), unit, G.fit_font("b", 50 * s, unit, sz[2] - sz[0] - 80 * s, 4), G.WHITE, tracking=4, anchor=anc), pq),
                      "counter.unit", "cutaway", text=unit, t_key=Q(ua)))
    pe = G.enter(t, p.get("pill_at", 1e9), .28, F); pil = G.tidy(p.get("pill", ""))
    if pe > 0 and pil:
        fp = G.font("b", 32 * s)
        out.append(El(G.layer(lambda d: G.pill(d, cx if align == "center" else ax + G.text_w(pil, fp, 2) / 2 + 30 * s, y + 190 * s, pil, fp, pad=(30 * s, 14 * s), sc=back(pe), text_p=pe)),
                      "counter.pill", "cutaway", text=pil, t_key=Q(p.get("pill_at"))))
    return out

def counter_cues(p, ctx):
    F = G.fps_of(ctx); a, dur = p.get("count", [ctx["start"], .8]); c = []
    if p.get("icon"): c.append((p.get("icon_at", ctx["start"]), "pop", -18, {}))
    if p.get("label") and p.get("label_at") is not None:
        c.append((p["label_at"], "keyboard", -24, {"trim": (3.0, 3.5)}) if p.get("label_mode", "type") == "type" else (p["label_at"], "swipe", -22, {"trim": (0, .25)}))
    ticks = G.count_ticks(float(p.get("value", 0)), a, dur, F, float(p.get("start_value", 0)), int(p.get("decimals", 0)), int(p.get("ticks", 6)))
    opaque = G.q(a, F) + dur / 4 if F else a + dur / 4      # the value fades in over the first quarter: no pop on a half-visible digit (SND-07)
    ticks = [tk for tk in ticks if tk >= opaque - 1e-6] or ticks[-1:]
    for k, tk in enumerate(ticks): c.append((tk, "pop", -31, {"pitch": 6 + k * .7}))        # rising pitch with the digits
    if p.get("suffix"): c.append((p.get("suffix_at", a + dur), "lowhit", -12, {"reveal": True}))
    if p.get("unit") and p.get("unit_at") is not None: c.append((p["unit_at"], "swipe", -21, {"trim": (0, .3)}))
    if p.get("pill") and p.get("pill_at") is not None: c.append((p["pill_at"], "pop", -16, {}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ browser_list (a web page card + deliverable rows)
def _browser_geo(n):
    """(s, card x0, x1, Y(v), row boxes [(x0, x1, top)], card bottom (tall px), bracket box (tall y), centre x).
    Tall: the 1080x1920 numbers (card 130..950 x 640..1160, rows inside at 200 + k * 100). Square: scaled to fit. Wide: a
    wider card, rows in two columns from 4 rows on, scaled up to fill the zone."""
    m = LY.mode()
    if m == "tall":
        dy = LY.tall_dy(); Y = lambda v: v + dy; cb = 640 + max(520, 220 + n * 100)           # 4+ rows: the card grows
        return 1.0, 130, 950, Y, [(170, 910, 840 + k * 100) for k in range(n)], cb, (500, max(1250, cb + 90)), 540
    z = LY.zone(); cols = 2 if (m == "wide" and n >= 4) else 1; rows = -(-n // cols)
    ch = max(440, 240 + rows * 100); bh = 140 + ch + (100 if n else 60)            # head .. card .. pill, at s = 1
    s = LY.fit(890, bh, grow=1.25 if m == "wide" else 1.0)
    cw = min(z[4] * .9, 820 * s * (1.55 if m == "wide" else 1.0)); x0 = z[6] - cw / 2; x1 = z[6] + cw / 2
    y0 = z[7] - bh * s / 2; Y = lambda v: y0 + (v - 500) * s
    inner = (x1 - x0) - 80 * s; gap = 30 * s; rw = (inner - (cols - 1) * gap) / cols
    boxes = [(x0 + 40 * s + (k // rows) * (rw + gap), x0 + 40 * s + (k // rows) * (rw + gap) + rw, 840 + (k % rows) * 100) for k in range(n)]
    return s, x0, x1, Y, boxes, 640 + ch, (500, 640 + ch + 90), z[6]

def browser_list(t, p, ctx):
    """p: head [[word, at, accent?], ...], enter, hero_at, hero_icon, rows [{text, at, icon?}], row_icon, pill, pill_at"""
    El, faded = _el(); out = []; F, Q = _t(ctx); head = p.get("head") or []; rows = p.get("rows", [])
    s, cx0, cx1, Y, boxes, cbot, (b0, b1), cx = _browser_geo(len(rows))
    if head:
        f = G.font("xb", 64 * s); tr = 2; sp = G.text_w(" ", f) + tr * 2
        words = [(G.tidy(w[0]), w[1], len(w) > 2 and bool(w[2])) for w in head]
        offs, x = [], 0.
        for w, _, _ in words: offs.append(x); x += G.text_w(w, f, tr) + sp
        il = offs[0] + G.ink(words[0][0], f, tr)[0]; ir = offs[-1] + G.ink(words[-1][0], f, tr)[1]
        if ir - il > (cx1 - cx0):                                  # a long head never runs past the card
            f = G.font("xb", 64 * s * (cx1 - cx0) / (ir - il)); offs, x = [], 0.; sp = G.text_w(" ", f) + tr * 2
            for w, _, _ in words: offs.append(x); x += G.text_w(w, f, tr) + sp
            il = offs[0] + G.ink(words[0][0], f, tr)[0]; ir = offs[-1] + G.ink(words[-1][0], f, tr)[1]
        x0 = cx - (il + ir) / 2                                    # centred on the drawn ink of the whole line, on the card axis (GFX-08)
        def hd(d):
            for (w, at, acc), ox in zip(words, offs):
                qv = G.enter(t, at, .28, F)
                if qv <= 0: continue
                dy = (30 * (1 - back(qv)) if acc else 18 * (1 - ease_out(qv))) * s
                G.draw_text(d, (x0 + ox, Y(580) - dy), w, f, (G.MINT if acc else G.WHITE) + (int(255 * min(1, qv * 2)),), tracking=tr)
        if G.enter(t, words[0][1], .28, F) > 0:
            out.append(El(G.layer(hd), "browser.head", "cutaway", text=" ".join(w for w, _, _ in words), t_key=Q(words[0][1])))
    pb = ease_out(G.enter(t, p.get("enter", ctx["start"] - .15), .35, F))
    if pb > 0:
        cw = cx1 - cx0; k_ = cw / 820                                 # hero bars follow the card width
        def browser(d):
            y0 = Y(640) + 40 * (1 - pb) * s; yb = y0 + (cbot - 640) * s
            G.rrect(d, (cx0, y0, cx1, yb), 28 * s, fill=G.CARD + (245,), outline=G.CARD_B, width=3 * s)
            for k in range(3): d.ellipse((cx0 + (38 + k * 30) * s, y0 + 30 * s, cx0 + (54 + k * 30) * s, y0 + 46 * s), fill=G.LINE)
            G.rrect(d, (cx0 + 160 * s, y0 + 22 * s, cx1 - 50 * s, y0 + 54 * s), 16 * s, fill=G.SURFACE)
            ph = ease_out(G.enter(t, p.get("hero_at", ctx["start"] + 1), .4, F))
            if ph > 0:
                G.rrect(d, (cx0 + 40 * s, y0 + 90 * s, cx0 + 40 * s + 420 * ph * k_, y0 + 120 * s), 12 * s, fill=G.MUTED)
                G.rrect(d, (cx0 + 40 * s, y0 + 138 * s, cx0 + 40 * s + 260 * ph * k_, y0 + 162 * s), 12 * s, fill=G.MINT)
                if p.get("hero_icon", "pin"): G.icon(d, p.get("hero_icon", "pin"), cx1 - 100 * s, y0 + 125 * s, 54 * min(1, back(ph)) * s)
        out.append(El(faded(browser, pb), "browser.card", "cutaway"))
        for k, r in enumerate(rows):
            qv = ease_out(G.enter(t, r["at"], .25, F))
            if qv <= 0: continue
            bx0, bx1, by = boxes[k]
            def row(d, k=k, r=r, qv=qv, bx0=bx0, bx1=bx1, by=by):
                yy = Y(by) + 40 * (1 - pb) * s; dx = 30 * (1 - qv) * s
                G.rrect(d, (bx0 - dx, yy, bx1 - dx, yy + 82 * s), 18 * s, fill=G.SURFACE, outline=(G.MINT_D if qv >= 1 else G.CARD_B), width=2 * s)
                G.rrect(d, (bx0 + 20 * s - dx, yy + 17 * s, bx0 + 68 * s - dx, yy + 65 * s), 12 * s, fill=G.WELL); G.icon(d, r.get("icon", p.get("row_icon", "post")), bx0 + 44 * s - dx, yy + 41 * s, 26 * s)
                G.draw_text(d, (bx0 + 92 * s - dx, yy + 52 * s), r["text"], G.fit_font("b", 28 * s, r["text"], (bx1 - bx0) - 180 * s, 2), G.WHITE, tracking=2)
            out.append(El(faded(row, qv), f"browser.row{k}", "cutaway", text=G.tidy(r["text"]), t_key=Q(r["at"]), asset=r.get("icon", p.get("row_icon", "post"))))
            pc = G.enter(t, r["at"] + .15, .2, F)
            if pc > 0:                       # the check is its own element: its pop cue has a logged visual event (SND-07)
                def chk(d, qv=qv, bx1=bx1, by=by, pc=pc):
                    yy = Y(by) + 40 * (1 - pb) * s; dx = 30 * (1 - qv) * s
                    G.state(d, "check", bx1 - 44 * s - dx, yy + 41 * s, 18 * s, pc)
                out.append(El(faded(chk, qv), f"browser.row{k}.check", "cutaway", t_key=Q(r["at"] + .15)))
    pe = G.enter(t, p.get("pill_at", 1e9), .25, F); pil = G.tidy(p.get("pill", ""))
    if pe > 0 and pil:
        out.append(El(G.layer(lambda d: G.pill(d, cx, Y(cbot + 40), pil, G.font("b", 30 * s), pad=(34 * s, 16 * s), sc=back(pe), text_p=pe)), "browser.pill", "cutaway", text=pil, t_key=Q(p.get("pill_at"))))
    if pb > 0: out.append(El(faded(lambda d: G.brackets(d, (cx0 - 35 * s, Y(b0), cx1 + 35 * s, Y(b1)), L=46 * s, w=3 * s), pb), "browser.brackets", "cutaway"))
    return out

def browser_list_cues(p, ctx):
    c = [(p.get("enter", ctx["start"]), "swipe", -19, {})]
    for w in p.get("head") or []: c.append((w[1], "lowhit" if len(w) > 2 and w[2] else "pop", -13 if len(w) > 2 and w[2] else -18, {}))
    for k, r in enumerate(p.get("rows", [])): c += [(r["at"], "card", -18, {"pitch": k * .5}), (r["at"] + .15, "pop", -22, {"pitch": k + 1})]
    if p.get("pill") and p.get("pill_at") is not None: c.append((p["pill_at"], "pop", -16, {}))
    return G.cues_out(c, ctx)

T = {"search_rows": (search_rows, search_rows_cues), "card_list": (card_list, card_list_cues),
     "counter": (counter, counter_cues), "stat": (counter, counter_cues), "browser_list": (browser_list, browser_list_cues)}
