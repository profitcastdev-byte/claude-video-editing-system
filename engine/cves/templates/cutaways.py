"""Full-screen cutaways on the stage (UI cards, typed searches, counters). Content builds on the spoken words.
Every element has an entry (fade / slide / scale from its own centre), every animation start is quantised to a whole frame
(G.enter / G.q), and every cue lands on the frame its visual event appears (G.cues_out). No copy lives here: every string
comes from params. Layout is in the 1080x1920 design space, inside the style's safe zone."""
import numpy as np
from PIL import Image, ImageFilter
from .. import gfx as G
from ..gfx import prog, ease_out, back, W, H

KIND = "cutaway"
DESIGN = True             # fixed 1080x1920 layout: fitted into the canvas safe zone on other canvases (templates._canvas_render)
def _el(): from . import El, faded; return El, faded
def _t(ctx): F = G.fps_of(ctx); return F, (lambda v: G.q(v, F))

# ------------------------------------------------------------------ search_rows
X0, X1 = 110, 970          # shared left / right edge of the head pill and the rows (GFX-08)
def search_rows(t, p, ctx):
    """typed search rows. p: label, pills [left, right], pill_times {left: [start, dur], plus: t, right: t}, rows [{q, type:[a,b], tag, check, stars?}],
    tag_text, enter (t first element lands), rows_in"""
    El, faded = _el(); out = []; F, Q = _t(ctx)
    enter = p.get("enter", ctx["start"] - .15); entry = G.mo("entry_s", .28)
    pT = ease_out(G.enter(t, enter, entry, F)); pt = p.get("pill_times", {}) or {}
    pills = list(p.get("pills") or ["", ""]) + ["", ""]; lw, rw = G.tidy(pills[0]), G.tidy(pills[1])
    pW = G.enter(t, *pt["left"], F) if "left" in pt else G.enter(t, enter + .3, .45, F)
    lab = G.tidy(p.get("label", ""))
    if lab and pT > 0:
        out.append(El(faded(lambda d: G.label(d, 540, 600, lab, 26), pT), "search.label", "cutaway", text=lab, t_key=Q(enter)))
    if pT > 0:
        def head(d):
            f = G.font("b", 34); vis = lw[:int(len(lw) * pW + .999)] if pW > 0 else ""
            dy = G.mo("slide_px", 50) * .4 * (1 - pT)
            G.rrect(d, (X0, 640 + dy, 560, 724 + dy), 42, outline=G.WHITE, width=3)
            if vis: G.draw_text(d, (335, 695 + dy), vis, f, G.WHITE, tracking=2, anchor="ms")
            if "plus" in pt and t >= Q(pt["plus"]) - .5 / (F or 60):
                G.draw_text(d, (613, 698 + dy), "+", G.font("b", 44), G.WHITE, anchor="ms")
        out.append(El(faded(head, pT), "search.head", "cutaway", text=lw, t_key=Q(enter)))
    pN = G.enter(t, pt.get("right", enter + 1.1), .3, F)
    if pN > 0 and rw:
        def near(d): G.pill(d, 820, 682, rw, G.font("b", 34), pad=(34, 25), sc=back(pN), text_p=pN)
        out.append(El(G.layer(near), "search.pill", "cutaway", text=rw, t_key=Q(pt.get("right", enter + 1.1))))
    tag = G.tidy(p.get("tag_text", ""))
    rows_in = p.get("rows_in", enter + 1.3); stg = G.mo("stagger_s", .12)
    for k, r in enumerate(p.get("rows", [])):
        a, b = r["type"]; chk = r.get("check"); tg = r.get("tag")
        r_at = rows_in + k * stg; pp = ease_out(G.enter(t, r_at, .3, F))
        if pp <= 0: continue
        def row(d, k=k, r=r, a=a, b=b, chk=chk, tg=tg, pp=pp):
            y = 790 + k * 140 + 30 * (1 - pp)                       # rises into place while fading in (MOT-12)
            done = chk is not None and t >= Q(chk) - .5 / (F or 60)
            G.rrect(d, (X0, y, X1, y + 116), 24, fill=G.CARD + (245,), outline=(G.MINT_D if done else G.CARD_B), width=3)
            G.icon(d, "search", X0 + 50, y + 46, 34, col=G.MUTED)
            tp = G.enter(t, a, b - a, F); qs = G.tidy(r["q"]); s = qs[:int(len(qs) * tp + .999)] if tp > 0 else ""
            f = G.font("m", 36)
            if s: G.draw_text(d, (X0 + 90, y + 60), s, f, G.WHITE)
            cx = X0 + 90 + G.text_w(s, f) + 8
            if a <= t < (tg if tg is not None else b) and int(t * 2.4) % 2 == 0: d.line((cx, y + 28, cx, y + 66), fill=G.MINT, width=3)
            qq = G.enter(t, tg, .22, F) if (tg is not None and tag) else 0
            if qq > 0:
                ft = G.font("sb", 24); tw = G.text_w(tag, ft) + 30; sc = back(qq); x0 = cx + 14
                G.rrect(d, (x0, y + 60 - 22 * sc, x0 + tw * sc, y + 60 + 14 * sc), 18, fill=G.MINT_D)
                if qq > .5: G.draw_text(d, (x0 + 15, y + 61), tag, ft, G.mix(G.WHITE, G.MINT, .25))
            if done:
                G.state(d, "check", X1 - 50, y + 58, 22, G.enter(t, chk, .22, F)); ps = G.enter(t, chk + .05, .3, F)
                for j in range(int(r.get("stars", 5))):
                    if ps * 5 > j: G.icon(d, "star", X0 + 106 + j * 30, y + 92, 20, col=G.STAR)
                d.line((X0 + 270, y + 92, X0 + 270 + 220 * ease_out(ps), y + 92), fill=G.SURFACE, width=6)
        out.append(El(faded(row, pp), f"search.row{k}", "cutaway", text=G.tidy(r["q"]), t_key=Q(r_at), asset="search"))
    if pT > 0: out.append(El(faded(lambda d: G.brackets(d, (80, 560, 1000, 1250)), pT), "search.brackets", "cutaway"))
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
def card_list(t, p, ctx):
    """cards building one by one. p: label (optional), label_at, items [{icon, title, sub, at, state: check|cross|null, state_at}], top (y of first card)"""
    El, faded = _el(); out = []; F, Q = _t(ctx); items = p.get("items", []); lab = G.tidy(p.get("label", ""))
    top = p.get("top", 640 if not lab else 750); entry = G.mo("entry_s", .28); slide = G.mo("slide_px", 50) * .72
    pB = ease_out(G.enter(t, min([it["at"] for it in items] + [ctx["start"]]), entry, F))
    if lab:
        la = p.get("label_at", ctx["start"] - .15); pl = ease_out(G.enter(t, la, .3, F))
        if pl > 0: out.append(El(faded(lambda d: G.label(d, 540, top - 50, lab, 26), pl), "list.label", "cutaway", text=lab, t_key=Q(la)))
    for k, it in enumerate(items):
        pp = ease_out(G.enter(t, it["at"], entry, F))
        if pp <= 0: continue
        y = top + k * 150; st = it.get("state"); sa = it.get("state_at", it["at"] + .25)
        sp = G.enter(t, sa, .25, F)
        out.append(El(faded(lambda d, y=y, it=it, pp=pp, st=st, sp=sp: G.card_row(d, 120 - slide * (1 - pp), y, 840, 124, it.get("icon"), G.tidy(it["title"]), G.tidy(it.get("sub")) or None,
                                                                                    st if (st and sp > 0) else None, 1, sp), pp),
                      f"list.item{k}", "cutaway", text=G.tidy(f"{it['title']} {it.get('sub') or ''}"), t_key=Q(it["at"]), asset=it.get("icon")))
    h = top + len(items) * 150
    if pB > 0: out.append(El(faded(lambda d: G.brackets(d, (80, top - 40 - (70 if lab else 0), 1000, h + 10)), pB), "list.brackets", "cutaway"))
    return out

def card_list_cues(p, ctx):
    c = []
    if p.get("label") and p.get("label_at") is not None: c.append((p["label_at"], "swipe", -22, {"trim": (0, .25)}))
    for k, it in enumerate(p.get("items", [])):
        c.append((it["at"], "card", -14, {"pitch": [0, .5, -.5, 1][k % 4]}))
        if it.get("state"): c.append((it.get("state_at", it["at"] + .25), "pop", -19 if it["state"] == "cross" else -16, {"pitch": (-2 if it["state"] == "cross" else 2) + (k % 3) * .4}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ counter / stat (big number)
def counter(t, p, ctx):
    """a number counting up. p: value, count [start, dur], start_value, prefix, suffix, suffix_at, decimals, grouping (intl|indian|none),
    size, color, icon (or null), icon_at, label, label_at, label_mode (type|fade), unit (caption under the number), unit_at, pill, pill_at,
    align (center|left), y (number baseline)"""
    El, faded = _el(); out = []; F, Q = _t(ctx)
    align = p.get("align", "center"); sz = G.safe(); ax = 540 if align == "center" else sz[0] + p.get("pad", 60)
    anc = "ms" if align == "center" else "li"; y = p.get("y", 960)
    ia = p.get("icon_at", ctx["start"] - .15); la = p.get("label_at", ctx["start"])
    pi = G.enter(t, ia, .3, F); lab = G.tidy(p.get("label", ""))
    pl = G.enter(t, la, .35 if p.get("label_mode", "type") == "type" else .3, F)
    if p.get("icon") and pi > 0:
        def ic(d):
            s = 92 * back(pi); cx = 540 if align == "center" else ax + 46
            G.rrect(d, (cx - s / 2, y - 360 - s / 2, cx + s / 2, y - 360 + s / 2), 22 * back(pi), fill=G.WELL)
            if pi > .5: G.icon(d, p["icon"], cx, y - 360, 46 * min(1, back(pi)))
        out.append(El(G.layer(ic), "counter.icon", "cutaway", asset=p["icon"], t_key=Q(ia)))
    if lab and pl > 0:
        if p.get("label_mode", "type") == "type":
            out.append(El(G.layer(lambda d: G.label(d, ax, y - 240, lab[:int(len(lab) * pl + .999)], 26) if align == "center" else
                                  G.draw_text(d, (ax, y - 240), lab[:int(len(lab) * pl + .999)], G.font("sb", 26), G.MUTED, tracking=7, anchor="li")),
                          "counter.head", "cutaway", text=lab, t_key=Q(la)))
        else:
            out.append(El(faded(lambda d: G.draw_text(d, (ax, y - 240 + 20 * (1 - ease_out(pl))), lab, G.font("sb", 26), G.MUTED, tracking=7, anchor=anc), ease_out(pl)),
                          "counter.head", "cutaway", text=lab, t_key=Q(la)))
    a, dur = p.get("count", [ctx["start"], .8]); v = float(p.get("value", 0)); v0 = float(p.get("start_value", 0)); dec = int(p.get("decimals", 0))
    pc = G.enter(t, a, dur, F)
    if pc > 0:
        n = G.count_value(v, Q(a) - .5 / (F or 60), dur, t, v0); suf = p.get("suffix", "")
        shown_suf = suf if (suf and t >= Q(p.get("suffix_at", a + dur)) - .5 / (F or 60)) else ""
        txt = f"{p.get('prefix', '')}{G.fmt_num(n, dec, p.get('grouping'))}{shown_suf}"
        final = f"{p.get('prefix', '')}{G.fmt_num(v, dec, p.get('grouping'))}{suf}"
        cc = G.col(p.get("color"), G.MINT); sc = .7 + .3 * back(min(1, pc * 2.5))
        f = G.fit_font("xb", int(p.get("size", 230) * sc), final, (sz[2] - sz[0]) - 80)
        def num(d): G.draw_text(d, (ax, y), txt, f, cc, anchor=anc)
        im = G.layer(num); glow = Image.fromarray(np.asarray(im)[..., 3]).filter(ImageFilter.GaussianBlur(28))
        g = Image.new("RGBA", (W, H), cc + (0,)); g.putalpha(glow.point(lambda x: int(x * .45)))
        out += [El(g, "counter.glow", "cutaway"), El(G.alpha(im, min(1, pc * 4)), "counter.value", "cutaway", text=final, t_key=Q(a))]
    ua = p.get("unit_at", a + dur); pq = ease_out(G.enter(t, ua, .3, F)); unit = G.tidy(p.get("unit", ""))
    if pq > 0 and unit:
        out.append(El(faded(lambda d: G.draw_text(d, (ax, y + 90 + 24 * (1 - pq)), unit, G.fit_font("b", 50, unit, sz[2] - sz[0] - 80, 4), G.WHITE, tracking=4, anchor=anc), pq),
                      "counter.unit", "cutaway", text=unit, t_key=Q(ua)))
    pe = G.enter(t, p.get("pill_at", 1e9), .28, F); pil = G.tidy(p.get("pill", ""))
    if pe > 0 and pil:
        out.append(El(G.layer(lambda d: G.pill(d, 540 if align == "center" else ax + G.text_w(pil, G.font("b", 32), 2) / 2 + 30, y + 190, pil, G.font("b", 32), pad=(30, 14), sc=back(pe), text_p=pe)),
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
def browser_list(t, p, ctx):
    """p: head [[word, at, accent?], ...], enter, hero_at, hero_icon, rows [{text, at, icon?}], row_icon, pill, pill_at"""
    El, faded = _el(); out = []; F, Q = _t(ctx); head = p.get("head") or []
    if head:
        f = G.font("xb", 64); tr = 2; sp = G.text_w(" ", f) + tr * 2
        words = [(G.tidy(w[0]), w[1], len(w) > 2 and bool(w[2])) for w in head]
        offs, x = [], 0.
        for w, _, _ in words: offs.append(x); x += G.text_w(w, f, tr) + sp
        il = offs[0] + G.ink(words[0][0], f, tr)[0]; ir = offs[-1] + G.ink(words[-1][0], f, tr)[1]
        x0 = 540 - (il + ir) / 2                                   # centred on the drawn ink of the whole line, on the card axis (GFX-08)
        def hd(d):
            for (w, at, acc), ox in zip(words, offs):
                qv = G.enter(t, at, .28, F)
                if qv <= 0: continue
                dy = 30 * (1 - back(qv)) if acc else 18 * (1 - ease_out(qv))
                G.draw_text(d, (x0 + ox, 580 - dy), w, f, (G.MINT if acc else G.WHITE) + (int(255 * min(1, qv * 2)),), tracking=tr)
        if G.enter(t, words[0][1], .28, F) > 0:
            out.append(El(G.layer(hd), "browser.head", "cutaway", text=" ".join(w for w, _, _ in words), t_key=Q(words[0][1])))
    pb = ease_out(G.enter(t, p.get("enter", ctx["start"] - .15), .35, F))
    if pb > 0:
        def browser(d):
            y0 = 640 + 40 * (1 - pb)
            G.rrect(d, (130, y0, 950, y0 + 520), 28, fill=G.CARD + (245,), outline=G.CARD_B, width=3)
            for k in range(3): d.ellipse((168 + k * 30, y0 + 30, 184 + k * 30, y0 + 46), fill=G.LINE)
            G.rrect(d, (290, y0 + 22, 900, y0 + 54), 16, fill=G.SURFACE)
            ph = ease_out(G.enter(t, p.get("hero_at", ctx["start"] + 1), .4, F))
            if ph > 0:
                G.rrect(d, (170, y0 + 90, 170 + 420 * ph, y0 + 120), 12, fill=G.MUTED)
                G.rrect(d, (170, y0 + 138, 170 + 260 * ph, y0 + 162), 12, fill=G.MINT)
                if p.get("hero_icon", "pin"): G.icon(d, p.get("hero_icon", "pin"), 850, y0 + 125, 54 * min(1, back(ph)))
        out.append(El(faded(browser, pb), "browser.card", "cutaway"))
        for k, r in enumerate(p.get("rows", [])):
            qv = ease_out(G.enter(t, r["at"], .25, F))
            if qv <= 0: continue
            def row(d, k=k, r=r, qv=qv):
                y0 = 640 + 40 * (1 - pb); yy = y0 + 200 + k * 100; dx = 30 * (1 - qv)
                G.rrect(d, (170 - dx, yy, 910 - dx, yy + 82), 18, fill=G.SURFACE, outline=(G.MINT_D if qv >= 1 else G.CARD_B), width=2)
                G.rrect(d, (190 - dx, yy + 17, 238 - dx, yy + 65), 12, fill=G.WELL); G.icon(d, r.get("icon", p.get("row_icon", "post")), 214 - dx, yy + 41, 26)
                G.draw_text(d, (262 - dx, yy + 52), r["text"], G.fit_font("b", 28, r["text"], 560, 2), G.WHITE, tracking=2)
                G.state(d, "check", 866 - dx, yy + 41, 18, G.enter(t, r["at"] + .15, .2, F))
            out.append(El(faded(row, qv), f"browser.row{k}", "cutaway", text=G.tidy(r["text"]), t_key=Q(r["at"]), asset=r.get("icon", p.get("row_icon", "post"))))
    pe = G.enter(t, p.get("pill_at", 1e9), .25, F); pil = G.tidy(p.get("pill", ""))
    if pe > 0 and pil:
        out.append(El(G.layer(lambda d: G.pill(d, 540, 1200, pil, G.font("b", 30), pad=(34, 16), sc=back(pe), text_p=pe)), "browser.pill", "cutaway", text=pil, t_key=Q(p.get("pill_at"))))
    if pb > 0: out.append(El(faded(lambda d: G.brackets(d, (95, 500, 985, 1250)), pb), "browser.brackets", "cutaway"))
    return out

def browser_list_cues(p, ctx):
    c = [(p.get("enter", ctx["start"]), "swipe", -19, {})]
    for w in p.get("head") or []: c.append((w[1], "lowhit" if len(w) > 2 and w[2] else "pop", -13 if len(w) > 2 and w[2] else -18, {}))
    for k, r in enumerate(p.get("rows", [])): c += [(r["at"], "card", -18, {"pitch": k * .5}), (r["at"] + .15, "pop", -22, {"pitch": k + 1})]
    if p.get("pill") and p.get("pill_at") is not None: c.append((p["pill_at"], "pop", -16, {}))
    return G.cues_out(c, ctx)

T = {"search_rows": (search_rows, search_rows_cues), "card_list": (card_list, card_list_cues),
     "counter": (counter, counter_cues), "stat": (counter, counter_cues), "browser_list": (browser_list, browser_list_cues)}
