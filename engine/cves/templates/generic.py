"""Generic, style-driven templates for any talking-head / short-form edit: title_card, checklist (list), comparison,
quote (testimonial), steps (timeline), logo_reveal, progress_bar, chart, cta. (stat / counter live in cutaways.py,
lower_third and kinetic_caption_emphasis in overlays.py, end_card in end.py.)

Rules every template here follows:
- every string comes from params (no copy in code); colours via gfx palette slots or `color:` params (slot name or hex);
  fonts via gfx; motion tokens from the style (`motion.entry_s`, `stagger_s`, `slide_px`, `overshoot`);
- `align: center|left` (and `layout:` where it makes sense); everything sits inside `platform.safe_zone`;
- stable element ids with text and a frame-quantised t_key; every element has an entry (fade / rise / scale from its centre);
- cues land on the frame their visual event appears and never before the template starts (gfx.cues_out)."""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .. import gfx as G
from ..gfx import ease_out, ease_in, back, clamp

KIND = "cutaway"
def _el(): from . import El, faded; return El, faded

# ------------------------------------------------------------------ shared helpers
class _K:
    """per-call timing + layout kit: k.q(t) (frame-quantised), k.e(t0, d) (entry progress), k.box, k.ax / k.anc (align)"""
    def __init__(self, t, p, ctx):
        self.t, self.p, self.ctx = t, p, ctx; self.F = G.fps_of(ctx)
        x0, y0, x1, y1 = G.safe(); pad = p.get("pad", 50)
        self.box = (x0 + pad, y0, x1 - pad, y1); self.w = self.box[2] - self.box[0]
        self.align = p.get("align", "center"); self.cx = (self.box[0] + self.box[2]) / 2
        self.ax = self.cx if self.align == "center" else self.box[0]; self.anc = "ms" if self.align == "center" else "li"
        self.start = ctx.get("start", 0.); self.stg = p.get("stagger", G.mo("stagger_s", .12)); self.entry = G.mo("entry_s", .28)
        self.slide = G.mo("slide_px", 50)
    def q(self, v): return G.q(v, self.F)
    def e(self, t0, d=None): return G.enter(self.t, t0, self.entry if d is None else d, self.F)
    def out(self):
        oa = self.p.get("out_at"); return ease_in(G.enter(self.t, oa, .2, self.F)) if oa is not None else 0.

def asset(ctx, path):
    """resolve an asset path (project, then repo); a missing file is a user error with one actionable line"""
    q = ctx["resolve"](path) if ctx.get("resolve") else path
    if not os.path.exists(q): raise SystemExit(f"asset not found: {path} (put it in the project folder, e.g. Brand/, or register it with `cves assets`)")
    return q

def _items(lst, key="text"):
    """params lists accept plain strings or dicts"""
    return [x if isinstance(x, dict) else {key: x} for x in (lst or [])]

def _txt(v): return G.tidy(v if v is not None else "")

def _block_top(k, h, y=None):
    """top of a block of height h: params y, else vertically centred in the safe zone"""
    if y is not None: return y
    return (k.box[1] + k.box[3]) / 2 - h / 2

_warned = set()
def _warn(msg):
    if msg not in _warned: _warned.add(msg); print(f"cves: {msg}", file=sys.stderr)

# ------------------------------------------------------------------ title_card
def title_card(t, p, ctx):
    """big kinetic type, 1-3 lines. p: lines [str | {text, at, color, size}], at, reveal (words|lines|none), stagger, size (120),
    font (xb), color, accent (words drawn in the accent colour), eyebrow, eyebrow_at, align, y (block centre), line_gap (1.06)"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    lines = _items(p.get("lines"))[:3]
    if not lines: return res
    at = p.get("at", k.start); reveal = p.get("reveal", "words"); fname = p.get("font", "xb")
    acc = {x.lower() for x in (p.get("accent") or [])}; base_c = G.col(p.get("color"), G.WHITE); acc_c = G.col(p.get("accent_color"), G.MINT)
    fonts = [G.fit_font(fname, ln.get("size", p.get("size", 120)), _txt(ln["text"]), k.w, 2) for ln in lines]
    lh = [f.size * p.get("line_gap", 1.06) for f in fonts]; block = sum(lh)
    cy = p.get("y", (k.box[1] + k.box[3]) / 2); top = cy - block / 2
    eb = _txt(p.get("eyebrow"))
    if eb:
        ea = p.get("eyebrow_at", at); pe = ease_out(k.e(ea))
        if pe > 0: res.append(El(faded(lambda d: G.draw_text(d, (k.ax, top - 40 + 16 * (1 - pe)), eb, G.font("sb", 28), G.col(p.get("eyebrow_color"), G.MINT), tracking=6, anchor=k.anc), pe * (1 - out)),
                                 "title.eyebrow", "cutaway", text=eb, t_key=k.q(ea)))
    cur = at; y = top
    for li, (ln, f) in enumerate(zip(lines, fonts)):
        txt = _txt(ln["text"]); words = txt.split(" "); la = ln.get("at", cur)
        wt = ln.get("words_at") or [la + (j * k.stg if reveal == "words" else 0) for j in range(len(words))]
        if reveal == "none": wt = [at] * len(words); la = at
        cur = (wt[-1] + k.stg * 2) if reveal == "words" else la + k.stg * 3
        y += lh[li]; base = y - lh[li] * .22
        if k.e(la) <= 0: continue
        tr = 2; sp = G.text_w(" ", f) + tr * 2; offs, xx = [], 0.
        for w in words: offs.append(xx); xx += G.text_w(w, f, tr) + sp
        il = offs[0] + G.ink(words[0], f, tr)[0]; ir = offs[-1] + G.ink(words[-1], f, tr)[1]
        x0 = (k.cx - (il + ir) / 2) if k.align == "center" else k.box[0] - il
        lc = G.col(ln.get("color"), None)
        def draw(d, words=words, offs=offs, wt=wt, f=f, base=base, x0=x0, lc=lc):
            for w, ox, ta in zip(words, offs, wt):
                qv = G.enter(t, ta, k.entry, k.F)
                if qv <= 0: continue
                c = lc or (acc_c if w.lower().strip(".,!?") in acc else base_c)
                G.draw_text(d, (x0 + ox, base + k.slide * .6 * (1 - ease_out(qv))), w, f, c + (int(255 * min(1, qv * 1.7) * (1 - out)),), tracking=tr)
        res.append(El(G.layer(draw), f"title.line{li}", "cutaway", text=txt, t_key=k.q(la), font=fname))
    return res

def title_card_cues(p, ctx):
    lines = _items(p.get("lines"))[:3]; at = p.get("at", ctx["start"]); mode = p.get("sfx", "lines"); reveal = p.get("reveal", "words")
    stg = p.get("stagger", G.mo("stagger_s", .12)); c = []; cur = at
    if p.get("eyebrow"): c.append((p.get("eyebrow_at", at), "pop", -24, {"pitch": 2}))
    for li, ln in enumerate(lines):
        words = _txt(ln["text"]).split(" "); la = ln.get("at", cur) if reveal != "none" else at
        wt = ln.get("words_at") or [la + (j * stg if reveal == "words" else 0) for j in range(len(words))]
        cur = (wt[-1] + stg * 2) if reveal == "words" else la + stg * 3
        if mode == "words": c += [(x, "pop", -24, {"pitch": j * .5}) for j, x in enumerate(wt)]
        elif mode == "lines": c.append((la, "swipe" if li else "lowhit", -20 if li else -13, {"trim": (0, .3)} if li else {"reveal": True}))
        if reveal == "none": break
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ checklist / list
def checklist(t, p, ctx):
    """n items with check / cross / number / bullet marks, staggered. p: items [str | {text, sub, at, mark, mark_at}], title, title_at,
    mark (check|cross|xfill|number|bullet|none), style (card|plain), align (plain only), at / items_at (base time), stagger, y (top), size (40)"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out(); items = _items(p.get("items"))
    if not items: return res
    style = p.get("style", "card"); size = p.get("size", 40); f = G.font("b", size); fs = G.font("sb", int(size * .7))
    rh = (size * 2.6 if any(it.get("sub") for it in items) else size * 2.2) if style == "card" else size * 1.9
    gap = p.get("gap", 24 if style == "card" else 10); title = _txt(p.get("title"))
    th = 90 if title else 0; block = th + len(items) * (rh + gap) - gap; top = _block_top(k, block, p.get("y"))
    base = p.get("items_at", p.get("at", k.start)); spread = p.get("item_spacing", k.stg * 3)
    if title:
        ta = p.get("title_at", base); pt = ease_out(k.e(ta))
        if pt > 0: res.append(El(faded(lambda d: G.draw_text(d, (k.ax, top + 44 + 16 * (1 - pt)), title, G.fit_font("xb", 56, title, k.w, 1), G.WHITE, tracking=1, anchor=k.anc), pt * (1 - out)),
                                 "checklist.title", "cutaway", text=title, t_key=k.q(ta)))
    mk0 = p.get("mark", "check")
    for i, it in enumerate(items):
        at = it.get("at", base + .25 + i * spread); pp = ease_out(k.e(at))
        if pp <= 0: continue
        y = top + th + i * (rh + gap); mk = it.get("mark", mk0); ma = it.get("mark_at", at + .18)
        txt, sub = _txt(it.get("text")), _txt(it.get("sub"))
        x0, x1 = (k.box[0], k.box[2]) if (style == "card" or k.align == "left") else (k.box[0], k.box[2])
        mx = x0 + (size * 1.3 if style == "card" else size * .55); tx = mx + size * 1.15
        room = x1 - tx - (30 if style == "card" else 0)
        ft = G.fit_font("b", size, txt, room, 1); fsub = G.fit_font("sb", int(size * .7), sub, room, 1) if sub else fs
        centred = style == "plain" and k.align == "center"
        if centred:     # centred plain list: mark + text centred as a group
            gw = size * 1.15 + G.ink(txt, ft, 1)[1]; mx = k.cx - gw / 2 + size * .5; tx = mx + size * .65 + size * .5
        def row(d, y=y, txt=txt, sub=sub, ft=ft, fsub=fsub, mx=mx, tx=tx, pp=pp):
            dx = -36 * (1 - pp) if style == "card" else 0; dy = 0 if style == "card" else k.slide * .4 * (1 - pp)
            if style == "card": G.rrect(d, (x0 + dx, y, x1 + dx, y + rh), 22, fill=G.CARD + (240,), outline=G.CARD_B, width=3)
            yb = y + rh / 2 + (ft.size * .36 if not sub else -2) + dy
            G.draw_text(d, (tx + dx, yb), txt, ft, G.WHITE, tracking=1)
            if sub: G.draw_text(d, (tx + dx, yb + fsub.size * 1.35), sub, fsub, G.MINT, tracking=1)
        res.append(El(faded(row, pp * (1 - out)), f"checklist.row{i}", "cutaway", text=G.tidy(f"{txt} {sub}"), t_key=k.q(at)))
        if mk and mk != "none":
            pm = k.e(ma, .25)
            if pm > 0:
                kind = {"number": f"num:{i + 1}", "cross": "cross", "xfill": "xfill", "check": "check", "bullet": "bullet"}.get(mk, mk)
                def mark(d, y=y, mx=mx, pm=pm, kind=kind, pp=pp):
                    dx = -36 * (1 - pp) if style == "card" else 0; cy = y + rh / 2 + (0 if style == "card" else k.slide * .4 * (1 - pp))
                    if kind == "bullet": r = size * .16 * max(0, back(pm)); d.ellipse((mx + dx - r, cy - r, mx + dx + r, cy + r), fill=G.MINT)
                    else: G.state(d, kind, mx + dx, cy, size * .55, pm)
                res.append(El(G.alpha(G.layer(mark), 1 - out), f"checklist.mark{i}", "cutaway", t_key=k.q(ma)))
    return res

def checklist_cues(p, ctx):
    items = _items(p.get("items")); base = p.get("items_at", p.get("at", ctx["start"])); stg = p.get("stagger", G.mo("stagger_s", .12))
    spread = p.get("item_spacing", stg * 3); c = []; style = p.get("style", "card"); mk0 = p.get("mark", "check")
    if p.get("title"): c.append((p.get("title_at", base), "swipe", -20, {"trim": (0, .3)}))
    for i, it in enumerate(items):
        at = it.get("at", base + .25 + i * spread); mk = it.get("mark", mk0)
        c.append((at, "card" if style == "card" else "swipe", -15 if style == "card" else -23, {"trim": (0, .25)} if style != "card" else {}))
        if mk and mk != "none": c.append((it.get("mark_at", at + .18), "pop", -18, {"pitch": {"cross": -2, "xfill": -3}.get(mk, 2) + i * .5}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ comparison
def comparison(t, p, ctx):
    """two columns (before / after, us vs them) with marks. p: left {title, items, mark (xfill)}, right {title, items, mark (check)},
    at (columns in), rows_at [t, ...] (one per row; else staggered), highlight (right|left|none), vs (label between heads, optional),
    layout (columns|stacked), size (38)"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    L, R = p.get("left") or {}, p.get("right") or {}; li, ri = _items(L.get("items")), _items(R.get("items"))
    n = max(len(li), len(ri)); at = p.get("at", k.start); size = p.get("size", 38); hl = p.get("highlight", "right")
    rows_at = p.get("rows_at") or [at + .45 + j * k.stg * 3 for j in range(n)]
    stacked = p.get("layout", "columns") == "stacked"; gap = 30
    rh = size * 2.9; head_h = 110
    if stacked:
        cw = k.w; cols = [("left", L, li, k.box[0]), ("right", R, ri, k.box[0])]
        card_h = head_h + n * rh + 30; total = card_h * 2 + gap
    else:
        cw = (k.w - gap) / 2; cols = [("left", L, li, k.box[0]), ("right", R, ri, k.box[0] + cw + gap)]
        card_h = head_h + n * rh + 30; total = card_h
    top = _block_top(k, total, p.get("y"))
    for ci, (side, C, its, x) in enumerate(cols):
        y = top + (ci * (card_h + gap) if stacked else 0); ca = at + (ci * k.stg if not stacked else ci * k.stg * 2)
        pc = ease_out(k.e(ca))
        if pc <= 0: continue
        hot = hl == side
        def card(d, x=x, y=y, hot=hot, pc=pc):
            dy = k.slide * .5 * (1 - pc)
            G.rrect(d, (x, y + dy, x + cw, y + card_h + dy), 28, fill=G.CARD + (245,), outline=(G.MINT if hot else G.CARD_B), width=4 if hot else 3)
        res.append(El(faded(card, pc * (1 - out)), f"cmp.card.{side}", "cutaway", t_key=k.q(ca)))
        ttl = _txt(C.get("title"))
        if ttl:
            fh = G.fit_font("xb", int(size * 1.2), ttl, cw - 60, 2)
            def head(d, x=x, y=y, ttl=ttl, fh=fh, hot=hot, pc=pc):
                dy = k.slide * .5 * (1 - pc)
                G.draw_text(d, (x + cw / 2, y + 72 + dy), ttl, fh, G.MINT if hot else G.MUTED, tracking=2, anchor="ms")
            res.append(El(faded(head, pc * (1 - out)), f"cmp.head.{side}", "cutaway", text=ttl, t_key=k.q(ca)))
        mk = C.get("mark", "check" if side == "right" else "xfill")
        for j, it in enumerate(its):
            ra = it.get("at", rows_at[min(j, len(rows_at) - 1)] + (k.stg if side == "right" and not stacked else 0)); pr = ease_out(k.e(ra))
            if pr <= 0: continue
            txt = _txt(it.get("text")); mx = x + 46; tx = x + 88; room = cw - 88 - 24
            lines = G.wrap(txt, G.font("sb", size), room, 0, 2); fl = G.font("sb", size)
            if len(lines) > 1 and any(G.text_w(l, fl) > room for l in lines): fl = G.fit_font("sb", size, max(lines, key=len), room)
            ry = y + head_h + j * rh
            def row(d, ry=ry, lines=lines, fl=fl, tx=tx, pr=pr):
                dx = 24 * (1 - pr); n_ = len(lines); y0 = ry + rh / 2 - (n_ - 1) * fl.size * .62 + fl.size * .36
                for m, l in enumerate(lines): G.draw_text(d, (tx + dx, y0 + m * fl.size * 1.24), l, fl, G.WHITE)
            res.append(El(faded(row, pr * (1 - out)), f"cmp.{side}{j}", "cutaway", text=txt, t_key=k.q(ra)))
            pm = k.e(ra + .1, .25)
            if pm > 0 and mk != "none":
                res.append(El(G.alpha(G.layer(lambda d, ry=ry, mx=mx, pm=pm: G.state(d, mk, mx, ry + rh / 2, size * .62, pm)), 1 - out), f"cmp.{side}{j}.mark", "cutaway", t_key=k.q(ra + .1)))
    vs = _txt(p.get("vs"))
    if vs and not stacked:
        va = p.get("vs_at", at + k.stg); pv = k.e(va, .25)
        if pv > 0: res.append(El(G.layer(lambda d: G.pill(d, k.cx, top + head_h / 2 + 8, vs, G.font("xb", 30), pad=(22, 14), sc=back(pv), text_p=pv)), "cmp.vs", "cutaway", text=vs, t_key=k.q(va)))
    return res

def comparison_cues(p, ctx):
    at = p.get("at", ctx["start"]); stg = p.get("stagger", G.mo("stagger_s", .12)); L, R = p.get("left") or {}, p.get("right") or {}
    li, ri = _items(L.get("items")), _items(R.get("items")); n = max(len(li), len(ri)); stacked = p.get("layout", "columns") == "stacked"
    rows_at = p.get("rows_at") or [at + .45 + j * stg * 3 for j in range(n)]
    c = [(at, "swipe", -19, {})]
    if p.get("vs"): c.append((p.get("vs_at", at + stg), "pop", -20, {}))
    for side, its in (("left", li), ("right", ri)):
        C = L if side == "left" else R; mk = C.get("mark", "check" if side == "right" else "xfill")
        for j, it in enumerate(its):
            ra = it.get("at", rows_at[min(j, len(rows_at) - 1)] + (stg if side == "right" and not stacked else 0))
            if mk != "none": c.append((ra + .1, "pop", -19, {"pitch": (2 if mk == "check" else -3) + j * .4}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ quote / testimonial
def _stars(d, x, cy, n, size, p_):
    """n stars (half steps allowed) from x, popping in one by one with progress p_"""
    full = int(n); half = n - full >= .25; tot = full + (1 if half else 0)
    for j in range(5):
        qv = clamp(p_ * 5 * 1.25 - j)
        if qv <= 0: continue
        s = size * max(0, back(qv)); sx = x + j * size * 1.25 + size / 2
        G.icon(d, "star", sx, cy, s, col=G.mix(G.CARD_B, G.WHITE, .15))          # empty star
        if j < full: G.icon(d, "star", sx, cy, s, col=G.STAR)
        elif j == full and half and s > 2:
            px = max(2, int(s * 1.15 * d.k)); im = G._icon_img(G.icon_file("star"), px, tuple(G.STAR)).crop((0, 0, px // 2, px))
            d.paste(im, sx - s * 1.15 / 2, cy - s * 1.15 / 2, s * 1.15 / 2)

def _avatar(path, px):
    im = G.image(path); s = min(im.size); im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((px, px), Image.LANCZOS)
    m = Image.new("L", (px * 4, px * 4), 0); ImageDraw.Draw(m).ellipse((0, 0, px * 4 - 1, px * 4 - 1), fill=255); m = m.resize((px, px), Image.LANCZOS)
    out = Image.new("RGBA", (px, px), (0, 0, 0, 0)); out.paste(im, (0, 0), m); return out

def quote(t, p, ctx):
    """a quote / testimonial. p: text, name, role, avatar (asset), stars (0-5, halves ok), at, name_at, stars_at, align, size (52),
    font (b | serif), card (true), quote_mark (true), max_lines (6), line_stagger"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    txt = _txt(p.get("text")); at = p.get("at", k.start); size = p.get("size", 52); fname = p.get("font", "b")
    inner = k.w - (80 if p.get("card", True) else 0)
    f = G.tfont(fname, size, txt)
    lines = G.wrap(txt, f, inner, 0)
    while len(lines) > p.get("max_lines", 6) and f.size > 26: f = G.tfont(fname, f.size - 4, txt); lines = G.wrap(txt, f, inner, 0)
    lh = f.size * 1.3; stars = float(p.get("stars", 0) or 0); name, role = _txt(p.get("name")), _txt(p.get("role"))
    has_av = bool(p.get("avatar")); foot = (120 if (name or has_av) else 0) + (70 if stars else 0)
    mark_h = 110 if p.get("quote_mark", True) else 0
    h = mark_h + len(lines) * lh + 40 + foot + (60 if p.get("card", True) else 0); top = _block_top(k, h, p.get("y"))
    pc = ease_out(k.e(at)); x0, x1 = k.box[0], k.box[2]; tx = k.cx if k.align == "center" else x0 + (40 if p.get("card", True) else 0)
    if pc <= 0: return res
    if p.get("card", True):
        res.append(El(faded(lambda d: G.rrect(d, (x0, top + k.slide * .4 * (1 - pc), x1, top + h + k.slide * .4 * (1 - pc)), 32, fill=G.CARD + (245,), outline=G.CARD_B, width=3), pc * (1 - out)),
                      "quote.card", "cutaway", t_key=k.q(at)))
    y = top + 30
    if p.get("quote_mark", True):
        pm = k.e(at + .05, .3)
        if pm > 0:
            res.append(El(G.alpha(G.layer(lambda d: G.draw_text(d, (tx, y + 120), "“", G.font("serif", int(200 * (.6 + .4 * back(pm)))), G.MINT, anchor=k.anc)), min(1, pm * 2) * (1 - out)),
                          "quote.mark", "cutaway", t_key=k.q(at + .05)))
        y += mark_h
    la = p.get("text_at", at + .15); ls = p.get("line_stagger", k.stg * .8)
    if lines and k.e(la) > 0:
        def body(d):
            for j, l in enumerate(lines):
                qv = ease_out(G.enter(t, la + j * ls, k.entry, k.F))
                if qv > 0: G.draw_text(d, (tx, y + (j + .8) * lh + 18 * (1 - qv)), l, f, G.WHITE + (int(255 * qv * (1 - out)),), anchor=k.anc)
        res.append(El(G.layer(body), "quote.text", "cutaway", text=txt, t_key=k.q(la)))
    y += len(lines) * lh + 40
    if stars:
        sa = p.get("stars_at", la + len(lines) * ls + .2); ps = k.e(sa, .5); ssz = 40
        if ps > 0:
            sw = 5 * ssz * 1.25 - ssz * .25; sx = k.cx - sw / 2 if k.align == "center" else tx
            res.append(El(G.alpha(G.layer(lambda d: _stars(d, sx, y + 20, stars, ssz, ps)), 1 - out), "quote.stars", "cutaway", text=f"{stars:g}/5", t_key=k.q(sa), asset="star"))
        y += 70
    if name or has_av:
        na = p.get("name_at", la + len(lines) * ls + .35); pn = ease_out(k.e(na))
        if pn > 0:
            av = _avatar(asset(ctx, p["avatar"]), max(8, int(round(G.px(192))))) if has_av else None; fnm = G.font("b", 36); frl = G.font("m", 28)
            tw = max(G.text_w(name, fnm), G.text_w(role, frl) if role else 0); gw = (96 + 24 if av else 0) + tw
            gx = k.cx - gw / 2 if k.align == "center" else tx
            def foot_(d):
                dy = 16 * (1 - pn)
                if av is not None: d.paste(av, gx, y + dy, 96)
                nx = gx + (120 if av is not None else 0)
                G.draw_text(d, (nx, y + 44 + dy + (0 if role else 16)), name, fnm, G.WHITE, anchor="li")
                if role: G.draw_text(d, (nx, y + 86 + dy), role, frl, G.MUTED, anchor="li")
            res.append(El(faded(foot_, pn * (1 - out)), "quote.name", "cutaway", text=G.tidy(f"{name} {role}"), t_key=k.q(na), asset=p.get("avatar")))
    return res

def quote_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = [(at, "swipe", -19, {})]; stg = p.get("stagger", G.mo("stagger_s", .12))
    la = p.get("text_at", at + .15); n = max(1, len(_txt(p.get("text"))) // 28)   # line count estimate for the default times
    ls = p.get("line_stagger", stg * .8)
    if p.get("stars"):
        sa = p.get("stars_at", la + n * ls + .2); ns = int(np.ceil(float(p["stars"])))
        c += [(sa + j * .5 / (5 * 1.25), "pop", -26, {"pitch": 2 + j}) for j in range(min(ns, 5))]
    if p.get("name") or p.get("avatar"): c.append((p.get("name_at", la + n * ls + .35), "card", -20, {}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ steps / timeline
def steps(t, p, ctx):
    """1-5 steps joined by a line that draws from node to node. p: steps [str | {title, sub, at}], layout (vertical|horizontal), at, title,
    title_at, number (true), size (46), y"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out(); st = _items(p.get("steps"), "title")
    if not st: return res
    if len(st) > 5: raise SystemExit(f"steps: at most 5 steps (got {len(st)}); split them over two cutaways")
    at = p.get("at", k.start); spread = p.get("step_spacing", k.stg * 4)
    times = [s.get("at", at + .25 + j * spread) for j, s in enumerate(st)]; size = p.get("size", 46); r = size * .75
    horiz = p.get("layout", "vertical") == "horizontal"; title = _txt(p.get("title")); th = 100 if title else 0
    n = len(st)
    if horiz:
        span = k.w; xs = [k.box[0] + span * (j + .5) / n for j in range(n)]; h = th + r * 2 + 170; top = _block_top(k, h, p.get("y")); ys = [top + th + r] * n
    else:
        gap = p.get("gap", size * 4.2); h = th + (n - 1) * gap + r * 2; top = _block_top(k, h, p.get("y")); xs = [k.box[0] + r] * n; ys = [top + th + r + j * gap for j in range(n)]
    if title:
        ta = p.get("title_at", at); pt = ease_out(k.e(ta))
        if pt > 0: res.append(El(faded(lambda d: G.draw_text(d, (k.cx if horiz or k.align == "center" else k.box[0], top + 50 + 14 * (1 - pt)), title, G.fit_font("xb", 56, title, k.w, 1), G.WHITE, anchor="ms" if horiz or k.align == "center" else "li"), pt * (1 - out)),
                                 "steps.title", "cutaway", text=title, t_key=k.q(ta)))
    for j in range(n - 1):                            # connector j: from node j (at its time) to node j+1 (by its time)
        a, b = times[j], times[j + 1]; pl = G.enter(t, a + .1, max(.1, b - a - .1), k.F)
        if pl <= 0: continue
        def ln(d, j=j, pl=pl):
            (x0, y0), (x1, y1) = (xs[j], ys[j]), (xs[j + 1], ys[j + 1])
            if horiz: x0, x1 = x0 + r + 8, x1 - r - 8
            else: y0, y1 = y0 + r + 8, y1 - r - 8
            d.line((x0, y0, x0 + (x1 - x0) * ease_out(pl), y0 + (y1 - y0) * ease_out(pl)), fill=G.LINE, width=6)
        res.append(El(G.alpha(G.layer(ln), 1 - out), f"steps.line{j}", "cutaway", t_key=k.q(a + .1)))
    for j, s in enumerate(st):
        pn = k.e(times[j], .3)
        if pn <= 0: continue
        res.append(El(G.alpha(G.layer(lambda d, j=j, pn=pn: G.state(d, f"num:{j + 1}" if p.get("number", True) else "check", xs[j], ys[j], r, pn)), 1 - out),
                      f"steps.node{j}", "cutaway", text=str(j + 1) if p.get("number", True) else None, t_key=k.q(times[j])))
        tt, sb = _txt(s.get("title")), _txt(s.get("sub")); ta = times[j] + .08; pt = ease_out(k.e(ta))
        if pt <= 0 or not tt: continue
        if horiz:
            colw = k.w / n - 16; ft = G.fit_font("b", int(size * .8), tt, colw, 0, 16); fsb = G.fit_font("sb", int(size * .6), sb, colw, 0, 14) if sb else None
            def tx(d, j=j, tt=tt, sb=sb, ft=ft, fsb=fsb, pt=pt):
                yb = ys[j] + r + 60 + 16 * (1 - pt); G.draw_text(d, (xs[j], yb), tt, ft, G.WHITE, anchor="ms")
                if sb: G.draw_text(d, (xs[j], yb + fsb.size * 1.4), sb, fsb, G.MUTED, anchor="ms")
        else:
            room = k.box[2] - (xs[j] + r + 30); ft = G.fit_font("b", size, tt, room, 0); fsb = G.fit_font("sb", int(size * .7), sb, room, 0) if sb else None
            def tx(d, j=j, tt=tt, sb=sb, ft=ft, fsb=fsb, pt=pt):
                x = xs[j] + r + 30 - 24 * (1 - pt); yb = ys[j] + (ft.size * .36 if not sb else -4)
                G.draw_text(d, (x, yb), tt, ft, G.WHITE, anchor="li")
                if sb: G.draw_text(d, (x, yb + fsb.size * 1.35), sb, fsb, G.MUTED, anchor="li")
        res.append(El(faded(tx, pt * (1 - out)), f"steps.text{j}", "cutaway", text=G.tidy(f"{tt} {sb}"), t_key=k.q(ta)))
    return res

def steps_cues(p, ctx):
    st = _items(p.get("steps"), "title"); at = p.get("at", ctx["start"]); stg = p.get("stagger", G.mo("stagger_s", .12)); spread = p.get("step_spacing", stg * 4)
    c = [(p.get("title_at", at), "swipe", -20, {"trim": (0, .3)})] if p.get("title") else []
    c += [(s.get("at", at + .25 + j * spread), "pop", -17, {"pitch": j * 1.0}) for j, s in enumerate(st[:5])]
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ logo_reveal
def logo_reveal(t, p, ctx):
    """a logo from an asset. p: logo, at, mode (scale|wipe|fade), width (560), y (centre, 860), glow (true), tagline, tagline_at, tagline_color"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    at = p.get("at", k.start); pp = k.e(at, p.get("dur", .55)); mode = p.get("mode", "scale")
    if pp <= 0: return res
    lg = G.image(asset(ctx, p["logo"])); wpx = min(p.get("width", 560), k.w); hpx = wpx * lg.height / lg.width; cy = p.get("y", 860 if G.is_design() else (k.box[1] + k.box[3]) / 2)
    e = ease_out(pp); sc = (.78 + .22 * back(pp)) if mode == "scale" else 1.0; op = min(1, pp * 2.2) if mode != "wipe" else 1.0
    def mark(d):
        w = wpx * sc; d.paste(lg, k.cx - w / 2, cy - hpx * sc / 2, w, opacity=op * (1 - out))
    im = G.layer(mark)
    if mode == "wipe":
        a = np.asarray(im).copy(); xs = np.arange(a.shape[1])[None, :]; x0 = G.px(k.cx - wpx / 2); edge = x0 + e * G.px(wpx + 80)
        a[..., 3] = (a[..., 3] * np.clip((edge - xs) / G.px(80), 0, 1)).astype(np.uint8); im = Image.fromarray(a)
    if p.get("glow", True):
        gl = Image.fromarray(np.asarray(im)[..., 3]).filter(ImageFilter.GaussianBlur(G.px(40)))
        g = Image.new("RGBA", im.size, G.col(p.get("glow_color"), G.MINT) + (0,)); g.putalpha(gl.point(lambda v: int(v * .5 * e))); res.append(El(g, "logo.glow", "cutaway"))
    res.append(El(im, "logo.mark", "cutaway", text="logo", t_key=k.q(at), asset=p["logo"]))
    tg = _txt(p.get("tagline")); ta = p.get("tagline_at", at + .45); pt = ease_out(k.e(ta))
    if tg and pt > 0:
        f = G.fit_font("sb", p.get("tagline_size", 40), tg, k.w, 10)
        res.append(El(faded(lambda d: G.draw_text(d, (k.cx, cy + hpx / 2 + 90 + 16 * (1 - pt)), tg, f, G.col(p.get("tagline_color"), G.WHITE), tracking=10, anchor="ms"), pt * (1 - out)),
                      "logo.tagline", "cutaway", text=tg, t_key=k.q(ta)))
    return res

def logo_reveal_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = [(at, "whoosh", -20, {"trim": (0, .35)}), (at, "lowhit", -13, {"reveal": True})]
    if p.get("tagline"): c.append((p.get("tagline_at", at + .45), "pop", -21, {"pitch": -2}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ progress_bar
def progress_bar(t, p, ctx):
    """a bar filling to a value. p: value (0-1, or 0-max), max (1 or 100), from (0), at, dur (1.0), label, label_at, show_value (true),
    suffix ('%'), prefix, decimals, color, y (track centre), height (34)"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    at = p.get("at", k.start); dur = p.get("dur", 1.0); mx = float(p.get("max", 100 if float(p.get("value", 0)) > 1 else 1))
    v = float(p.get("value", 0)) / mx; v0 = float(p.get("from", 0)) / mx; y = p.get("y", 900 if G.is_design() else (k.box[1] + k.box[3]) / 2); h = p.get("height", 34)
    ent = p.get("enter", at - .25); pe = ease_out(k.e(ent)); x0, x1 = k.box[0], k.box[2]; c = G.col(p.get("color"), G.MINT)
    lab = _txt(p.get("label")); la = p.get("label_at", ent)
    if lab:
        pl = ease_out(k.e(la))
        if pl > 0: res.append(El(faded(lambda d: G.draw_text(d, (x0, y - h - 34 + 14 * (1 - pl)), lab, G.fit_font("b", 40, lab, k.w * .7, 1), G.WHITE, tracking=1, anchor="li"), pl * (1 - out)),
                                 "progress.label", "cutaway", text=lab, t_key=k.q(la)))
    if pe <= 0: return res
    res.append(El(faded(lambda d: G.rrect(d, (x0, y - h / 2, x0 + (x1 - x0) * (.6 + .4 * pe), y + h / 2), h / 2, fill=G.SURFACE, outline=G.CARD_B, width=2), pe * (1 - out)),
                  "progress.track", "cutaway", t_key=k.q(ent)))
    pf = k.e(at, dur)
    if pf > 0:
        cur = v0 + (v - v0) * ease_out(pf)
        res.append(El(G.alpha(G.layer(lambda d: G.rrect(d, (x0, y - h / 2, x0 + max(h, (x1 - x0) * cur), y + h / 2), h / 2, fill=c)), 1 - out), "progress.fill", "cutaway", t_key=k.q(at)))
        if p.get("show_value", True):
            dec = int(p.get("decimals", 0)); shown = cur * (100 if mx == 1 and p.get("suffix", "%") == "%" else mx)
            fin = v * (100 if mx == 1 and p.get("suffix", "%") == "%" else mx)
            s = f"{p.get('prefix', '')}{G.fmt_num(shown, dec, p.get('grouping'))}{p.get('suffix', '%')}"
            res.append(El(G.alpha(G.layer(lambda d: G.draw_text(d, (x1, y - h - 34), s, G.font("xb", 56), c, anchor="rs")), min(1, pf * 4) * (1 - out)),
                          "progress.value", "cutaway", text=f"{p.get('prefix', '')}{G.fmt_num(fin, dec, p.get('grouping'))}{p.get('suffix', '%')}", t_key=k.q(at)))
    return res

def progress_bar_cues(p, ctx):
    at = p.get("at", ctx["start"]); dur = p.get("dur", 1.0); F = G.fps_of(ctx); mx = float(p.get("max", 100 if float(p.get("value", 0)) > 1 else 1))
    c = [(p.get("enter", at - .25), "swipe", -21, {"trim": (0, .3)})]
    scale = 100 if mx == 1 else 1
    ticks = G.count_ticks(float(p.get("value", 0)) * scale, at, dur, F, float(p.get("from", 0)) * scale, int(p.get("decimals", 0)), int(p.get("ticks", 5)))
    c += [(x, "pop", -31, {"pitch": 6 + j * .7}) for j, x in enumerate(ticks)]
    c.append((at + dur, "ding", -22, {}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ chart
def chart(t, p, ctx):
    """a simple bar or line chart from params data. p: kind (bar|line), data [{label, value} | [label, value]], at, stagger, dur, title, title_at,
    prefix, suffix, decimals, max (auto), highlight (index or label; else all accent), show_values (true), y (top), height (560)"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out()
    data = [(str(x[0]), float(x[1])) if isinstance(x, (list, tuple)) else (str(x.get("label", "")), float(x.get("value", 0))) for x in (p.get("data") or [])]
    if not data: return res
    kind = p.get("kind", "bar"); at = p.get("at", k.start); n = len(data); title = _txt(p.get("title"))
    th = 100 if title else 0; height = p.get("height", 560 if G.is_design() else min(560, (k.box[3] - k.box[1]) - th - 90)); total = th + height + 90; top = _block_top(k, total, p.get("y"))
    base_y = top + th + height; x0, x1 = k.box[0], k.box[2]; vmax = float(p.get("max") or max(v for _, v in data) or 1)
    hl = p.get("highlight"); hi = (hl if isinstance(hl, int) else next((j for j, (l, _) in enumerate(data) if l == hl), None)) if hl is not None else None
    dec = int(p.get("decimals", 0)); fmt = lambda v: f"{p.get('prefix', '')}{G.fmt_num(v, dec, p.get('grouping'))}{p.get('suffix', '')}"
    stg = p.get("stagger", k.stg * 1.5); times = [at + .25 + j * stg for j in range(n)]; dur = p.get("dur", .5)
    if title:
        ta = p.get("title_at", at); pt = ease_out(k.e(ta))
        if pt > 0: res.append(El(faded(lambda d: G.draw_text(d, (k.ax, top + 56 + 14 * (1 - pt)), title, G.fit_font("xb", 54, title, k.w, 1), G.WHITE, anchor=k.anc), pt * (1 - out)),
                                 "chart.title", "cutaway", text=title, t_key=k.q(ta)))
    pa = ease_out(k.e(at, .35))
    if pa > 0: res.append(El(faded(lambda d: d.line((x0, base_y, x0 + (x1 - x0) * pa, base_y), fill=G.LINE, width=4), 1 - out), "chart.axis", "cutaway", t_key=k.q(at)))
    slot = (x1 - x0) / n; bw = min(slot * .62, 160); fl = G.font("sb", 28); fv = G.font("b", 36)
    def colr(j): return G.MINT if (hi is None or j == hi) else G.mix(G.CARD_B, G.WHITE, .25)
    pts = []
    for j, (lb, v) in enumerate(data):
        cx = x0 + slot * (j + .5); pb = k.e(times[j], dur); hgt = height * .9 * max(0, v) / vmax
        pts.append((cx, base_y - hgt))
        if pb <= 0: continue
        e = ease_out(pb)
        if kind == "bar":
            res.append(El(G.alpha(G.layer(lambda d, cx=cx, hgt=hgt, e=e, j=j: G.rrect(d, (cx - bw / 2, base_y - hgt * e, cx + bw / 2, base_y), min(18, bw / 4), fill=colr(j))), 1 - out),
                          f"chart.bar{j}", "cutaway", t_key=k.q(times[j])))
        lf = G.fit_font("sb", 28, lb, slot - 10, 0, 16)
        res.append(El(faded(lambda d, cx=cx, lb=lb, lf=lf: G.draw_text(d, (cx, base_y + 48), lb, lf, G.MUTED, anchor="ms"), min(1, pb * 2) * (1 - out)), f"chart.lbl{j}", "cutaway", text=lb, t_key=k.q(times[j])))
        if p.get("show_values", True):
            pv = k.e(times[j] + dur * .6, .25)
            if pv > 0:
                vy = base_y - hgt - (24 if kind == "bar" else 40)
                res.append(El(faded(lambda d, cx=cx, vy=vy, v=v, j=j, pv=pv: G.draw_text(d, (cx, vy + 10 * (1 - pv)), fmt(v), G.fit_font("b", 36, fmt(v), slot - 6, 0, 16), colr(j) if hi is not None else G.WHITE, anchor="ms"), ease_out(pv) * (1 - out)),
                              f"chart.val{j}", "cutaway", text=fmt(v), t_key=k.q(times[j] + dur * .6)))
    if kind == "line":
        pl = k.e(times[0], times[-1] - times[0] + dur)
        if pl > 0:
            def line(d):
                segs = len(pts) - 1; reach = ease_out(pl) * max(1, segs)
                for j in range(segs):
                    qv = clamp(reach - j)
                    if qv <= 0: break
                    (ax_, ay), (bx, by) = pts[j], pts[j + 1]; d.line((ax_, ay, ax_ + (bx - ax_) * qv, ay + (by - ay) * qv), fill=G.MINT, width=7, joint="curve")
            res.append(El(G.alpha(G.layer(line), 1 - out), "chart.line", "cutaway", t_key=k.q(times[0])))
        for j, (cx, cy) in enumerate(pts):
            pq = k.e(times[j], .25)
            if pq > 0:
                def dot(d, cx=cx, cy=cy, pq=pq, j=j):
                    r_ = 13 * max(0, back(pq)); d.ellipse((cx - r_, cy - r_, cx + r_, cy + r_), fill=colr(j), outline=G.CARD, width=4)
                res.append(El(G.alpha(G.layer(dot), 1 - out),
                                    f"chart.pt{j}", "cutaway", t_key=k.q(times[j])))
    return res

def chart_cues(p, ctx):
    n = len(p.get("data") or []); at = p.get("at", ctx["start"]); stg = p.get("stagger", G.mo("stagger_s", .12) * 1.5)
    c = [(at, "swipe", -21, {"trim": (0, .3)})] + [(at + .25 + j * stg, "pop", -19, {"pitch": j * .8}) for j in range(n)]
    if p.get("title") and abs(p.get("title_at", at) - at) > .1: c.append((p.get("title_at", at), "swipe", -22, {"trim": (0, .25)}))
    return G.cues_out(c, ctx)

# ------------------------------------------------------------------ cta (cutaway) / end_card (end.py)
def _qr_matrix(data):
    """QR modules as a bool matrix, from the optional `qrcode` (or `segno`) library; None when neither is installed"""
    try:
        import qrcode
        q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M); q.add_data(data); q.make(fit=True)
        return np.array(q.get_matrix(), bool)
    except ImportError: pass
    try:
        import segno
        return np.array([[bool(v) for v in row] for row in segno.make(data, error="m").matrix], bool)
    except ImportError: return None

def cta_render(t, p, ctx, prefix="cta", role="cutaway"):
    """headline, button, handle / URL, QR (when the qrcode lib is installed), logo. p: headline (str | [lines]), button, handle, icon (left of the
    handle, e.g. link), qr (data to encode), logo, at, logo_at, headline_at, button_at, handle_at, qr_at, press_at, button_color, y"""
    El, faded = _el(); k = _K(t, p, ctx); res = []; out = k.out(); at = p.get("at", k.start)
    hl = p.get("headline"); hl = [hl] if isinstance(hl, str) else list(hl or []); hl = [_txt(x) for x in hl if _txt(x)]
    btn, hdl = _txt(p.get("button")), _txt(p.get("handle")); qr = p.get("qr"); logo = p.get("logo")
    mat = _qr_matrix(str(qr)) if qr else None
    if qr and mat is None: _warn("cta qr: install the `qrcode` package (pip install qrcode) to draw QR codes; skipped")
    fh = [G.fit_font("xb", p.get("size", 84), x, k.w, 1) for x in hl]
    lh_ = 0 if not logo else 200; hh = sum(f.size * 1.08 for f in fh); bh = 120 if btn else 0; dh = 80 if hdl else 0; qh = 300 if mat is not None else 0
    total = lh_ + hh + (50 + bh if btn else 0) + (40 + dh if hdl else 0) + (50 + qh if qh else 0); y = _block_top(k, total, p.get("y"))
    times = {"logo": p.get("logo_at", at), "headline": p.get("headline_at", at + (.15 if logo else 0)), "button": p.get("button_at", at + .45),
             "handle": p.get("handle_at", at + .65), "qr": p.get("qr_at", at + .8)}
    if logo:
        pl = ease_out(k.e(times["logo"]))
        if pl > 0:
            lg = G.image(asset(ctx, logo)); wpx = min(p.get("logo_width", 360), k.w); lhp = wpx * lg.height / lg.width; s = .9 + .1 * pl
            yy = y + (160 - lhp) / 2
            res.append(El(G.layer(lambda d: d.paste(lg, k.cx - wpx * s / 2, yy + 20 * (1 - pl), wpx * s, opacity=pl * (1 - out))), f"{prefix}.logo", role, text="logo", asset=logo, t_key=k.q(times["logo"])))
        y += lh_
    if hl:
        ph = ease_out(k.e(times["headline"]))
        if ph > 0:
            def head(d):
                yy = y
                for j, (x, f) in enumerate(zip(hl, fh)):
                    qv = ease_out(G.enter(t, times["headline"] + j * k.stg, k.entry, k.F)); yy += f.size * 1.08
                    if qv > 0: G.draw_text(d, (k.cx, yy - f.size * .2 + k.slide * .5 * (1 - qv)), x, f, G.WHITE + (int(255 * qv * (1 - out)),), anchor="ms")
            res.append(El(G.layer(head), f"{prefix}.headline", role, text=" ".join(hl), t_key=k.q(times["headline"])))
        y += hh
    if btn:
        y += 50; pb = k.e(times["button"], .3)
        if pb > 0:
            pr = p.get("press_at"); press = 1 - .06 * np.sin(np.pi * clamp((t - G.q(pr, k.F)) / .18)) if pr is not None and t >= G.q(pr, k.F) else 1
            bc = G.col(p.get("button_color"), G.MINT)
            res.append(El(G.alpha(G.layer(lambda d: G.pill(d, k.cx, y + bh / 2, btn, G.fit_font("xb", 46, btn, k.w - 140, 2), pad=(60, 34), col=bc, sc=back(pb) * press, text_p=pb)), 1 - out),
                          f"{prefix}.button", role, text=btn, t_key=k.q(times["button"])))
        y += bh
    if hdl:
        y += 40; pd = ease_out(k.e(times["handle"]))
        if pd > 0:
            f = G.fit_font("sb", 40, hdl, k.w - 80, 1); ic = p.get("icon"); iw = 52 if ic and G.icon_file(ic) else 0
            gw = iw + G.ink(hdl, f, 1)[1]; gx = k.cx - gw / 2
            def hd(d):
                dy = 14 * (1 - pd)
                if iw: G.icon(d, ic, gx + 20, y + dh / 2 - 12 + dy, 32, col=G.MINT)
                G.draw_text(d, (gx + iw, y + dh / 2 + 2 + dy), hdl, f, G.WHITE, tracking=1)
            res.append(El(faded(hd, pd * (1 - out)), f"{prefix}.handle", role, text=hdl, t_key=k.q(times["handle"])))
        y += dh
    if mat is not None:
        y += 50; pq = k.e(times["qr"], .3)
        if pq > 0:
            nm = mat.shape[0]; side = qh; cell = (side - 36) / nm; x0 = k.cx - side / 2; s = .85 + .15 * back(pq)
            def qrd(d):
                cxq, cyq = k.cx, y + side / 2; S_ = side * s; c_ = cell * s; ox, oy = cxq - S_ / 2 + 18 * s, cyq - S_ / 2 + 18 * s
                G.rrect(d, (cxq - S_ / 2, cyq - S_ / 2, cxq + S_ / 2, cyq + S_ / 2), 18 * s, fill=G.WHITE)
                for (r_, c2) in zip(*np.where(mat)): d.rectangle((ox + c2 * c_, oy + r_ * c_, ox + (c2 + 1) * c_ + .3, oy + (r_ + 1) * c_ + .3), fill=(0, 0, 0))
            res.append(El(G.alpha(G.layer(qrd), min(1, pq * 2) * (1 - out)), f"{prefix}.qr", role, text=str(qr), t_key=k.q(times["qr"])))
    return res

def cta_cues(p, ctx):
    at = p.get("at", ctx["start"]); c = []
    if p.get("logo"): c.append((p.get("logo_at", at), "lowhit", -14, {}))
    if p.get("headline"): c.append((p.get("headline_at", at + (.15 if p.get("logo") else 0)), "swipe", -19, {"trim": (0, .3)}))
    if p.get("button"): c.append((p.get("button_at", at + .45), "pop", -16, {}))
    if p.get("press_at") is not None and p.get("button"): c.append((p["press_at"], "button", -17, {}))
    if p.get("handle"): c.append((p.get("handle_at", at + .65), "pop", -22, {"pitch": 3}))
    if p.get("qr") and _qr_matrix("x") is not None: c.append((p.get("qr_at", at + .8), "card", -20, {}))
    return G.cues_out(c, ctx)

def cta(t, p, ctx):
    """call to action. p: headline (str | lines), button, press_at, handle, icon, qr (needs the qrcode lib), logo, at, *_at, button_color, y"""
    return cta_render(t, p, ctx, "cta", "cutaway")

T = {"title_card": (title_card, title_card_cues), "checklist": (checklist, checklist_cues), "list": (checklist, checklist_cues),
     "comparison": (comparison, comparison_cues), "quote": (quote, quote_cues), "testimonial": (quote, quote_cues),
     "steps": (steps, steps_cues), "timeline": (steps, steps_cues), "logo_reveal": (logo_reveal, logo_reveal_cues),
     "progress_bar": (progress_bar, progress_bar_cues), "chart": (chart, chart_cues), "cta": (cta, cta_cues)}
