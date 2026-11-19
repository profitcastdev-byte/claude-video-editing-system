"""End cards (after the last spoken word; <= 3 s, hard cut, no black - PLAT-11/12).
logo_end: logo + label + pill. end_card: the generic call-to-action card (headline, button, handle / URL, optional QR,
optional logo): display type scaled from the canvas, the block centred in the safe zone, every element on one centre
axis. Every element enters from its own centre / with a fade."""
from .. import gfx as G
from ..gfx import ease_out, ease_in, back

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

def _balanced(words, f, max_w):
    """two lines of about equal width (the break that minimises the longer line), or one line when it fits"""
    one = " ".join(words)
    if G.text_w(one, f) <= max_w or len(words) < 2: return [one]
    best = min(range(1, len(words)), key=lambda j: max(G.text_w(" ".join(words[:j]), f), G.text_w(" ".join(words[j:]), f)))
    return [" ".join(words[:best]), " ".join(words[best:])]

def end_layout(p):
    """the end card's type scale and block, from the canvas (layout px): {hs, lines, hf, bf, df, gap, ..., top, total, cx}.
    The headline sits at display size (a fraction of the safe zone, `size` = px at a 1080 short side overrides it), wrapped
    to two balanced lines when one does not fit; the whole block is centred in the safe zone and shrinks to fit it."""
    z = G.safe(); zw, zh = z[2] - z[0], z[3] - z[1]; cx = (z[0] + z[2]) / 2; maxw = zw * .9
    hl = p.get("headline"); given = not isinstance(hl, str) and hl is not None
    hl = [G.tidy(x) for x in ([hl] if isinstance(hl, str) else list(hl or [])) if G.tidy(x or "")]
    btn, hdl = G.tidy(p.get("button") or ""), G.tidy(p.get("handle") or "")
    logo, qr = p.get("logo"), p.get("qr")
    hs = float(p.get("size", min(zw * .12, zh * .115)))
    for _ in range(40):
        hf = G.font("xb", int(hs))
        lines = hl if given else (_balanced(" ".join(hl).split(" "), hf, maxw) if hl else [])
        if all(G.text_w(x, hf) <= maxw for x in lines): break
        hs *= .95
    def block(hs):
        lead = hs * 1.04; bf = hs * .46; df = hs * .36; gap = hs * .6
        parts = []
        if logo: parts.append(("logo", hs * 1.15))
        if lines: parts.append(("headline", lead * len(lines)))
        if btn: parts.append(("button", bf + 2 * bf * .78))
        if hdl: parts.append(("handle", df * 1.3))
        if qr: parts.append(("qr", hs * 2.6))
        total = sum(h for _, h in parts) + gap * max(0, len(parts) - 1)
        return dict(lead=lead, bf=bf, df=df, gap=gap, parts=parts, total=total)
    b = block(hs)
    if b["total"] > zh * .9:                                    # never leave the safe zone: scale the whole block
        hs *= zh * .9 / b["total"]; hf = G.font("xb", int(hs)); b = block(hs)
    top = (z[1] + z[3]) / 2 - b["total"] / 2 - zh * .02        # optical centre: a touch above the geometric one
    return dict(b, hs=hs, hf=hf, lines=lines, btn=btn, hdl=hdl, logo=logo, qr=qr, top=top, cx=cx, maxw=maxw)

def end_card(t, p, ctx):
    """generic CTA end card. p: headline (str: wrapped to <= 2 balanced lines | [lines]), button, handle, icon (left of the
    handle), qr (needs the qrcode lib), logo, size (headline px at a 1080 short side; default: display size from the safe
    zone), button_color, at / logo_at / headline_at / button_at / handle_at / qr_at (default: a short cascade from the card
    start), press_at. Every element is centred on one axis (the safe-zone centre) and the block is centred in the safe zone."""
    from .generic import asset, _qr_matrix, _warn
    import numpy as np
    El, faded = _el(); F = G.fps_of(ctx); Q = lambda v: G.q(v, F); at = p.get("at", ctx["start"]); res = []
    L = end_layout(p); cx = L["cx"]; y = L["top"]; ent = G.mo("entry_s", .28); stg = G.mo("stagger_s", .12); slide = G.mo("slide_px", 50)
    oa = p.get("out_at"); out = ease_in(G.enter(t, oa, .2, F)) if oa is not None else 0.
    times = {"logo": p.get("logo_at", at), "headline": p.get("headline_at", at + (.15 if L["logo"] else 0)), "button": p.get("button_at", at + .45),
             "handle": p.get("handle_at", at + .65), "qr": p.get("qr_at", at + .8)}
    mat = _qr_matrix(str(L["qr"])) if L["qr"] else None
    if L["qr"] and mat is None: _warn("end_card qr: install the `qrcode` package (pip install qrcode) to draw QR codes; skipped")
    for kind, h in L["parts"]:
        if kind == "logo":
            pl = ease_out(G.enter(t, times["logo"], ent, F))
            if pl > 0:
                lg = G.image(asset(ctx, L["logo"])); lh = h; lw = min(L["maxw"] * .5, lh * lg.width / lg.height); lh = lw * lg.height / lg.width
                sc = .92 + .08 * pl; yy = y + (h - lh * sc) / 2 + 16 * (1 - pl)
                res.append(El(G.layer(lambda d, yy=yy, lw=lw, sc=sc, pl=pl: d.paste(lg, cx - lw * sc / 2, yy, lw * sc, opacity=pl * (1 - out))),
                              "end.logo", "end", text="logo", asset=L["logo"], t_key=Q(times["logo"])))
        elif kind == "headline":
            if G.enter(t, times["headline"], ent, F) > 0:
                def head(d, y0=y):
                    yy = y0
                    for j, x in enumerate(L["lines"]):
                        qv = ease_out(G.enter(t, times["headline"] + j * stg, ent, F)); yy += L["lead"]
                        if qv > 0: G.draw_text(d, (cx, yy - L["hs"] * .24 + slide * .5 * (1 - qv)), x, L["hf"], G.WHITE + (int(255 * qv * (1 - out)),), anchor="ms")
                res.append(El(G.layer(head), "end.headline", "end", text=" ".join(L["lines"]), t_key=Q(times["headline"])))
        elif kind == "button":
            pb = G.enter(t, times["button"], .3, F)
            if pb > 0:
                pr = p.get("press_at"); press = 1 - .06 * np.sin(np.pi * min(1., (t - G.q(pr, F)) / .18)) if pr is not None and t >= G.q(pr, F) else 1
                bf = G.fit_font("xb", int(L["bf"]), L["btn"], L["maxw"] - L["bf"] * 2.6, 2)
                bc = G.col(p.get("button_color"), G.MINT)
                res.append(El(G.alpha(G.layer(lambda d, yc=y + h / 2: G.pill(d, cx, yc, L["btn"], bf, pad=(bf.size * 1.3, bf.size * .78), col=bc, sc=back(pb) * press, text_p=pb)), 1 - out),
                              "end.button", "end", text=L["btn"], t_key=Q(times["button"])))
        elif kind == "handle":
            pd = ease_out(G.enter(t, times["handle"], ent, F))
            if pd > 0:
                f = G.fit_font("sb", int(L["df"]), L["hdl"], L["maxw"] - L["df"] * 1.6, 1); ic = p.get("icon"); isz = f.size * .8
                iw = isz * 1.45 if ic and G.icon_file(ic) else 0
                l, r, _, _ = G.ink(L["hdl"], f, 1); gx = cx - (iw + r - l) / 2      # icon + ink centred as one group on the axis
                def hd(d, yb=y + h * .78):
                    dy = 14 * (1 - pd)
                    if iw: G.icon(d, ic, gx + isz / 2, yb - f.size * .36 + dy, isz, col=G.MINT)
                    G.draw_text(d, (gx + iw, yb + dy), L["hdl"], f, G.WHITE, tracking=1, anchor="li")
                res.append(El(faded(hd, pd * (1 - out)), "end.handle", "end", text=L["hdl"], t_key=Q(times["handle"])))
        elif kind == "qr" and mat is not None:
            pq = G.enter(t, times["qr"], .3, F)
            if pq > 0:
                side = h; nm = mat.shape[0]; cell = (side - 36) / nm; s_ = .85 + .15 * back(pq)
                def qrd(d, cy=y + h / 2):
                    S_ = side * s_; c_ = cell * s_; ox, oy = cx - S_ / 2 + 18 * s_, cy - S_ / 2 + 18 * s_
                    G.rrect(d, (cx - S_ / 2, cy - S_ / 2, cx + S_ / 2, cy + S_ / 2), 18 * s_, fill=G.WHITE)
                    for (r_, c2) in zip(*np.where(mat)): d.rectangle((ox + c2 * c_, oy + r_ * c_, ox + (c2 + 1) * c_ + .3, oy + (r_ + 1) * c_ + .3), fill=(0, 0, 0))
                res.append(El(G.alpha(G.layer(qrd), min(1, pq * 2) * (1 - out)), "end.qr", "end", text=str(L["qr"]), t_key=Q(times["qr"])))
        y += h + L["gap"]
    return res

def end_card_cues(p, ctx):
    from .generic import cta_cues
    return cta_cues({**p, "at": p.get("at", ctx["start"])}, ctx)

T = {"logo_end": (logo_end, logo_end_cues), "end_card": (end_card, end_card_cues)}
