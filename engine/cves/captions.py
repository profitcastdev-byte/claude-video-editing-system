"""Captions: phrase building + rendering, entirely from the style profile (`captions:` section, docs/STYLE.md).
Styles: word_reveal (words appear as spoken) | one_word (one word at a time, big) | highlight (full phrase, the current word
in the accent colour, or on an accent pill with `highlight_mode: pill`) | box (phrase on rounded boxes) | karaoke (full phrase,
spoken words fill in) | pop (each word pops in with a scale overshoot) | bounce (each word drops in with a bounce) | none.
Flags: `outline` (stroke px instead of / as well as the shadow), `shadow`, `emphasis` (keywords + numbers bigger, in a colour),
`emoji` (colour emoji when a colour-emoji font exists, else skipped), `per_style` (max_chars / max_lines / size_scale per style).
Position: chin (just under the face; never over it - FRAME-01 wins over the safe zone) | lower_third | center | y:<px>.
With no presenter on screen (B-roll, voiceover / music / broll spines) `chin` sits low in the safe zone (a lower third).
Width: lines wrap by measured width inside the canvas safe zone (gfx.safe_zone) minus `captions.pad_x`.
Px values (size, gaps, pads) are designed for a 1080 short side and scale by gfx.U on other canvases (docs/FORMATS.md).
Scripts: non-Latin text uses `font_files.script_fallback` (language code or script -> font); RTL never crashes (visual order
without libraqm). Lessons baked in: never cross a sentence end; break before natural joining words; sentence case; fixed
line breaks and fixed word positions (words never shift while the line builds)."""
import math, os, re
import numpy as np
from PIL import Image, ImageFilter
from . import gfx as G

JOIN = {"every", "that's", "because", "and", "but", "so", "for", "to", "with", "where", "which", "in", "then", "or", "if", "when", "than"}
SHORT = {"medium": "m", "semibold": "sb", "bold": "b", "extrabold": "xb", "serif": "serif"}
STYLES = ("word_reveal", "one_word", "highlight", "box", "karaoke", "pop", "bounce", "none")
_PER_STYLE = {"one_word": {"max_chars": 1, "max_lines": 1, "size_scale": 1.5}}     # built-in fallbacks; the style's per_style wins

def resolve(cfg):
    """captions config with the active style's per_style overrides applied"""
    cfg = dict(cfg or {}); st = cfg.get("style", "word_reveal")
    ps = {**_PER_STYLE.get(st, {}), **((cfg.get("per_style") or {}).get(st) or {})}
    return {**cfg, **ps}

def _case(w, mode, first):
    if mode == "upper": return w.upper()
    if mode == "lower": return w.lower()
    if mode == "sentence" and first: return w[:1].upper() + w[1:]
    return w

def _avail(cfg, S=None):
    z = G.safe_zone(S)
    x0, x1 = (z[0], z[2]) if z else (G.margin(S), G.W - G.margin(S))
    return max(200. * G.U, (x1 - x0) - 2 * cfg.get("pad_x", 85) * G.U), (x0 + x1) / 2

def _font(cfg, text, scale=1.0):
    size = cfg.get("size", 50) * cfg.get("size_scale", 1.0) * scale * G.U
    return G.tfont(SHORT.get(cfg.get("font", "semibold"), cfg.get("font", "sb")), int(round(size)), text, cfg.get("language")), size

def build(words, cfg, t_end):
    """words: [[start, end, word]] (cut time) -> [(start, end, [(word, t)])] phrases.
    A phrase ends at a sentence end, before max_chars, or before it would need more than max_lines measured lines."""
    cfg = resolve(cfg)
    fixes = cfg.get("fixes", {}) or {}; maxc = cfg.get("max_chars", 34); mode = cfg.get("case", "sentence")
    maxl = max(1, int(cfg.get("max_lines", 2))); maxc = 1 if cfg.get("style") == "one_word" else maxc
    L = lambda ph: len(" ".join(x for x, _ in ph))
    try:
        avail, _ = _avail(cfg)
        def nlines(ph):
            txt = " ".join(x for x, _ in ph); f, _ = _font(cfg, txt); ws = txt.split(" "); n, cur = 1, []
            for w in ws:
                if cur and G.text_w(" ".join(cur + [w]), f) > avail: n += 1; cur = [w]
                else: cur.append(w)
            return n
    except Exception:
        nlines = lambda ph: 1
    toks = []
    for s, e, w in words:
        k = w.strip(".,?!").lower()
        toks.append((fixes.get(w.lower(), fixes.get(k, w) if w.lower() == k else w), s))
    phrases, cur = [], []
    for w, s in toks:
        if cur and (L(cur + [(w, s)]) > maxc or (maxc > 1 and nlines(cur + [(w, s)]) > maxl)):
            j = max([i for i, (x, _) in enumerate(cur) if i > 0 and x.lower().strip(",") in JOIN] or [len(cur)])
            if L(cur[:j]) < 12: j = len(cur)
            phrases.append(cur[:j]); cur = cur[j:]
        cur.append((w, s))
        if w.endswith((".", "?", "!")) or (w.endswith(",") and L(cur) > 14):
            phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    cap_next = True
    for ph in phrases:
        for i, (w, t) in enumerate(ph):
            ph[i] = (_case(w, mode, cap_next and i == 0), t)
        cap_next = ph[-1][0].endswith((".", "?", "!"))
    ev = []
    for k, ph in enumerate(phrases):
        a = ph[0][1] - .03; b = phrases[k + 1][0][1] - .03 if k + 1 < len(phrases) else t_end
        ev.append((a, b, ph))
    return ev

def _color(v, S):
    """palette name or #RRGGBB[AA] -> (r, g, b, a)"""
    cols = S.get("colors") or {}
    if isinstance(v, str) and v in cols: v = cols[v]
    if isinstance(v, (list, tuple)): c = tuple(int(x) for x in v); return c[:3] + ((c[3],) if len(c) > 3 else (255,))
    v = str(v).lstrip("#")
    try:
        rgb = tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)); a = int(v[6:8], 16) if len(v) >= 8 else 255
    except ValueError: rgb, a = G.WHITE, 255
    return rgb + (a,)

_NUM = re.compile(r"\d")
def _key(w): return re.sub(r"[^\w']+", "", w.lower())

def _bounce(p):
    """ease-out bounce 0..1"""
    n, d = 7.5625, 2.75
    if p < 1 / d: return n * p * p
    if p < 2 / d: p -= 1.5 / d; return n * p * p + .75
    if p < 2.5 / d: p -= 2.25 / d; return n * p * p + .9375
    p -= 2.625 / d; return n * p * p + .984375

def element(TL, t, chin, events, S):
    """the caption layer at time t (or None) as a templates.El"""
    from .templates import El
    cfg = resolve(S.get("captions") or {}); style = cfg.get("style", "word_reveal")
    if style == "none": return None
    if style not in STYLES: style = "word_reveal"
    for a, b, words in events:
        if not (a <= t < b): continue
        lead = cfg.get("lead_s", .03)
        spoken = [wt <= t + lead for _, wt in words]
        n_shown = sum(spoken)
        reveal = style in ("word_reveal", "one_word", "pop", "bounce")
        if not n_shown and reveal: return None
        phrase = " ".join(w for w, _ in words)
        f, size = _font(cfg, phrase)
        fname = os.path.splitext(os.path.basename(G._font_path(G.font_name_for(phrase, SHORT.get(cfg.get("font", "semibold"), "sb"), cfg.get("language")))))[0]
        emo = cfg.get("emoji", True)
        em = cfg.get("emphasis") or {}; emw = {_key(x) for x in (em.get("words") or [])}; emnum = em.get("numbers", True)
        em_scale = float(em.get("scale", 1.15)); em_col = _color(em.get("color", "accent"), S)
        rtl = G.is_rtl(phrase)
        avail, cx = _avail(cfg, S)

        # ---- tokens: display word (visual order for RTL; emoji drawn by gfx from the colour-emoji font or skipped), emphasis, font, width
        def token(i, w, wt):
            disp = G.visual_order(w) if rtl else w
            if not emo: disp = G.strip_emoji(disp)
            k = _key(w); emph = bool(k) and (k in emw or (emnum and bool(_NUM.search(w))))
            ff = G.tfont(SHORT.get(cfg.get("font", "semibold"), "sb"), int(round(size * (em_scale if emph else 1))), w, cfg.get("language")) if emph else f
            return dict(i=i, w=disp, t=wt, emph=emph, f=ff, wd=G.text_w(disp, ff))
        toks = [token(i, w, wt) for i, (w, wt) in enumerate(words)]
        toks = [x for x in toks if x["wd"] > 0] or toks
        sp = G.text_w(" ", f) if f.getlength(" ") else size * .28
        # ---- fixed line breaks by measured width (shrink up to 3 steps rather than lose words to max_lines)
        maxl = 1 if style == "one_word" else max(1, int(cfg.get("max_lines", 2)))
        def lay(scale):
            lines, cur, cw = [], [], 0.
            for x in toks:
                w = x["wd"] * scale
                if cur and cw + sp * scale + w > avail: lines.append(cur); cur, cw = [x], w
                else: cw = cw + (sp * scale if cur else 0) + w; cur.append(x)
            if cur: lines.append(cur)
            return lines
        scale = 1.0; lines = lay(scale)
        if style != "one_word":
            for _ in range(3):
                if len(lines) <= maxl: break
                scale *= .9; lines = lay(scale)
            lines = lines[:maxl]
        if rtl: lines = [ln[::-1] for ln in lines]
        sz = size * scale; lh = sz * cfg.get("line_height", 1.32)
        safe = G.safe_zone(S) or (0, 0, G.W, G.H); u = G.U
        block = (len(lines) - 1) * lh + sz; block_max = (maxl - 1) * lh + sz
        pos = str(cfg.get("position", "chin")); pad_b = cfg.get("pad_bottom", 20) * u
        gap, min_gap = cfg.get("chin_gap", 70) * u, cfg.get("chin_min_gap", 72) * u
        over_broll = chin is None
        if chin is None:          # no presenter on screen (B-roll): chin / lower_third sit low in the safe zone
            chin = -1e9
            if pos == "chin": pos = "low"
        if pos == "low": top = safe[3] - pad_b - block_max; top = min(top, safe[3] - pad_b - block)
        elif pos == "chin":
            top = max(chin + gap, safe[3] - pad_b - block_max)       # sit low in the safe zone, under the chin
            halo = sz * G.sget("legibility.bed_spread", .18) if cfg.get("legible", True) and cfg.get("shadow", True) else 0
            top = min(top, safe[3] - pad_b - block); top = max(top, chin + min_gap + halo)   # the bed / shadow never reaches the face (FRAME-01)
        elif pos == "lower_third": top = max(G.H * cfg.get("lower_third_y", .68), chin + min_gap)
        elif pos == "center": top = G.H / 2 - block / 2
        elif pos.startswith("y:"): top = float(pos[2:])
        else: top = chin + gap
        col = _color(cfg.get("color", "#FFFFFF"), S); hi = _color(cfg.get("highlight_color", "accent"), S)
        dim = tuple(int(c * cfg.get("karaoke_dim", .55)) for c in col[:3])
        outline = float(cfg.get("outline", 0) or 0); oc = _color(cfg.get("outline_color", "#000000"), S)[:3]
        cur_i = n_shown - 1
        pop_s = cfg.get("pop_s", .16); fade_s = cfg.get("reveal_s", 0)

        # ---- per-word positions (fixed), then state per style
        placed = []; yy = top + sz * .8
        for ln in lines:
            ws = [x["wd"] * scale for x in ln]; tot = sum(ws) + sp * scale * (len(ln) - 1); x = cx - tot / 2
            for tk, wd in zip(ln, ws):
                placed.append((tk, x, yy, wd, tk["i"])); x += wd + sp * scale
            yy += lh

        def draw(d):
            if style == "box":
                bc = _color(cfg.get("box_color", "#000000B0"), S); pad = sz * cfg.get("box_pad", .35)
                rows = {}
                for tk, x, y, wd, k in placed: rows.setdefault(y, []).append((x, x + wd))
                for y, spans in rows.items():
                    G.rrect(d, (min(s for s, _ in spans) - pad, y - sz * .95, max(e for _, e in spans) + pad, y + sz * .35), sz * cfg.get("box_radius", .3), fill=bc)
            for tk, x, y, wd, k in placed:
                said = spoken[k] if k < len(spoken) else True
                if reveal and not said: continue
                if style == "one_word" and k != cur_i: continue
                fill = col[:3]; sc = 1.0; dy = 0.; op = 1.0
                if tk["emph"] and said: fill = em_col[:3]
                if style == "one_word": fill = em_col[:3] if tk["emph"] else hi[:3]
                elif style == "highlight" and k == cur_i:
                    if cfg.get("highlight_mode", "text") == "pill":
                        pad = sz * .18; G.rrect(d, (x - pad, y - sz * .9, x + wd + pad, y + sz * .3), sz * .25, fill=hi[:3])
                        fill = G.CARD if G.contrast(G.CARD, hi[:3]) > G.contrast(col[:3], hi[:3]) else col[:3]
                    else: fill = hi[:3]
                elif style == "karaoke": fill = (em_col[:3] if tk["emph"] else hi[:3]) if said else dim
                if style in ("pop", "one_word"):
                    pp = G.prog(t, tk["t"] - lead, pop_s); sc = .55 + .45 * G.back(pp) if pp < 1 else 1.0; op = 1. if pp > 0 else 0.   # opaque from its first frame: a fading word fails GFX-15 over bright footage
                elif style == "bounce":
                    pp = G.prog(t, tk["t"] - lead, pop_s * 2.2); dy = -sz * .45 * (1 - _bounce(pp)); op = min(1., pp * 4)
                elif style == "word_reveal":
                    op = G.prog(t, tk["t"] - lead, fade_s) if fade_s > 0 else 1.
                if op <= 0: continue
                fn = G._NAME.get(id(tk["f"]), ("sb", 0))[0]
                ff = tk["f"] if (sc == 1 and scale == 1) else G.font(fn, max(6, int(round(tk["f"].size * scale * sc))))
                ww = wd * sc; xx = x + (wd - ww) / 2; ccy = y - sz * .35; by = ccy + (y - ccy) * sc + dy
                G.draw_text(d, (xx, by), tk["w"], ff, tuple(fill[:3]) + (int(255 * op),), stroke=outline * sc, stroke_fill=oc + (int(255 * op),) if outline else None)
        im = G.layer(draw)
        layers = []
        if cfg.get("shadow", True) and style != "box":
            al = np.asarray(im)[..., 3]
            sh = Image.fromarray(al).filter(ImageFilter.GaussianBlur(cfg.get("shadow_blur", 7) * G.U))
            base = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
            base.paste(Image.new("RGBA", (G.W, G.H), (0, 0, 0, 255)), (0, int(round(cfg.get("shadow_dy", 3) * G.U))), sh.point(lambda v: int(v * cfg.get("shadow_alpha", .7))))
            layers.append(base)
            if cfg.get("legible", True):
                bg = G.sget("legibility.video_bg_broll", "#C8C8C8") if over_broll else None   # full-bleed footage runs brighter than a presenter's wall
                # the bed keeps the main colour's polarity but is as dark as the darkest light fill needs: an accent word
                # (emphasis / highlight) is darker than white and failed GFX-15 on a mid-tone shirt under the white's bed
                fills = [em_col[:3] for tk, *_ in placed if tk["emph"]] + ([hi[:3]] if style in ("highlight", "one_word", "karaoke") and cfg.get("highlight_mode", "text") != "pill" else [])
                Lb = G.lum(G.col(bg) or G._rgb(G.sget("legibility.video_bg", "#B4B4B4"))); need = G.need_contrast(sz) * G.sget("legibility.margin", 1.15)
                force = max([0.0] + [1 - max(0., (G.lum(c) + .05) / need - .05) / max(1e-6, Lb) for c in fills if G.lum(c) <= G.lum(col[:3]) and G.lum(c) < Lb])
                bed = G.legible_bed(im, col[:3], sz, bg=bg, force=force, reach=2 + 2 * math.ceil(outline * G.U))   # an outline pushes the glyph edge out
                if bed is not None: layers.insert(0, bed)
        out = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
        for L in layers: out.alpha_composite(L)
        out.alpha_composite(im)
        return El(out, f"caption@{a:.2f}", "caption", text=" ".join(w for w, _ in words), t_key=words[0][1], font=fname)
    return None
