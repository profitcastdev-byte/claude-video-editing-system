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
line breaks and fixed word positions (words never shift while the line builds). `schedule()` then resolves fragments a
cutaway / snap / hide window would leave on screen for less than `captions.min_on_s` (PLAT-06 / 07)."""
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

def _measure(cfg):
    """(chars(phrase), measured lines(phrase)) for a resolved captions config; phrase = [(word, t)]"""
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
    return L, nlines

def fits(ph, cfg):
    """True when a phrase obeys the style's caption limits (max_chars, measured max_lines)"""
    cfg = resolve(cfg); L, nlines = _measure(cfg)
    maxc = 1 if cfg.get("style") == "one_word" else cfg.get("max_chars", 34)
    return L(ph) <= maxc and (maxc <= 1 or nlines(ph) <= max(1, int(cfg.get("max_lines", 2))))

def _ends(w): return str(w).rstrip("\"')”’").endswith((".", "?", "!"))

def schedule(events, hidden, fps, cfg, log=None):
    """events [(a, b, [(word, t)])] -> events with no fragment on screen for less than `captions.min_on_s`.

    The renderer hides captions under drawn cutaways, chest graphics, the roto snap, hide windows and the end card
    (`hidden(frame) -> bool`). An event that straddles one of those leaves a fragment: a caption that flashes for a few
    frames before the cover starts, or resumes for a few frames after it ends (PLAT-07: 1 frame; PLAT-06: 1320 cps).
    Every visible run shorter than min_on_s is resolved, words are never lost from what the viewer can read:
      * a run AFTER a cover (the event resumes): its words still to be spoken move into the next event when that fits the
        style limits and crosses no sentence end; words already spoken under the cover were never readable, so they go;
        when nothing is left to say the fragment is skipped (the event ends where the cover ends);
      * a run BEFORE a cover (the event starts just before it): its words join the previous event (held on screen up to
        the cover) when that fits; the rest of the event resumes after the cover;
      * otherwise the event is kept as it is (a short event is better than lost words).
    `log` collects one dict per decision."""
    if not events: return events
    cfg = resolve(cfg); mn = float(cfg.get("min_on_s", 0.83) or 0)
    if mn <= 0 or str(cfg.get("style", "word_reveal")) == "none": return events
    lead = float(cfg.get("lead_s", .03)); log = log if log is not None else []
    ev = [[float(a), float(b), list(ws)] for a, b, ws in events]

    def runs(a, b):
        f0, f1 = int(math.ceil(a * fps - 1e-6)), int(math.ceil(b * fps - 1e-6))     # frames f with a <= f / fps < b
        out, cur = [], None
        for f in range(f0, f1):
            if not hidden(f):
                if cur and cur[1] == f: cur[1] = f + 1
                else: cur = [f, f + 1]; out.append(cur)
        return [tuple(r) for r in out], f0, f1

    k, guard = 0, 0
    while k < len(ev) and guard < 20 * len(ev) + 20:
        guard += 1; k = max(0, k); a, b, ws = ev[k]; rs, f0, f1 = runs(a, b)
        short = [r for r in rs if (r[1] - r[0]) / fps < mn - 1e-9]
        if not short or not ws: k += 1; continue
        r = short[0]; covered_before = r[0] > f0 and hidden(r[0] - 1); covered_after = r[1] < f1 and hidden(r[1])
        rec = {"event": f"caption@{a:.2f}", "run": [r[0], r[1] - 1], "on_s": round((r[1] - r[0]) / fps, 3)}
        if covered_before:                            # resumes after a cover for a moment
            t_run = r[0] / fps
            left = [w for w in ws if w[1] - lead >= t_run - 1e-9]       # words still to be said when the caption resumes
            gone = ws[:len(ws) - len(left)]
            nxt = ev[k + 1] if k + 1 < len(ev) else None
            if not left:
                ev[k][1] = t_run; rec["action"] = "skipped: its words were spoken under the cover"
                nxt = ev[k + 1] if k + 1 < len(ev) else None
                if nxt and nxt[2] and nxt[0] > t_run and (nxt[2][0][1] * fps - r[0]) <= 2 + 1e-6:
                    nxt[0] = t_run; rec["action"] += "; the next event starts on the cut"   # no caption-less frame right after the cut
            elif nxt and nxt[0] <= b + 1e-6 and not any(_ends(w) for w, _ in left) and fits(left + nxt[2], cfg):
                nxt[0] = max(t_run, left[0][1] - lead); nxt[2] = left + nxt[2]
                if gone: ev[k][1] = t_run; ev[k][2] = gone
                else: ev.pop(k)
                rec["action"] = f"merged {len(left)} word(s) into the next event"
            else:
                rec["action"] = "kept: its words do not fit the next event"; log.append(rec); k += 1; continue
            log.append(rec); continue                  # re-check (the event may have another short run)
        if covered_after:                              # starts just before a cover
            t_end = r[1] / fps
            head = [w for w in ws if w[1] - lead < t_end - 1e-9]; rest = ws[len(head):]
            prv = ev[k - 1] if k > 0 else None
            if head and prv and prv[1] >= a - 1e-6 and not _ends(prv[2][-1][0]) and not any(_ends(w) for w, _ in head[:-1]) \
                    and fits(prv[2] + head, cfg):
                prv[2] = prv[2] + head
                if rest: prv[1] = t_end; ev[k][0] = max(t_end, rest[0][1] - lead); ev[k][2] = rest
                else: prv[1] = max(prv[1], b); ev.pop(k)
                rec["action"] = f"held the previous event over {len(head)} word(s)"; log.append(rec); k -= 1; continue
            rec["action"] = "kept: its words do not fit the previous event"; log.append(rec); k += 1; continue
        k += 1
    return [(a, b, ws) for a, b, ws in ev if b > a and ws]

_PUNCT = ".,?!;:\"'"

def fix_word(w, fixes):
    """captions.fixes: a mis-heard word -> its spelling. Keys match whatever their case and punctuation ("Alena",
    "dentists,"); the fix's spelling and case win, the spoken word keeps its punctuation (first real job: "Alena" -> aligner)"""
    if not fixes: return w
    F = {str(k).strip(_PUNCT).lower(): str(v) for k, v in fixes.items()}
    core = w.strip(_PUNCT); rep = F.get(core.lower())
    if rep is None or not core: return w
    pre, post = w[:w.index(core)], w[w.index(core) + len(core):]
    return pre + (rep.strip(_PUNCT) or rep) + post       # the fix's own spelling and case; the spoken word's punctuation

def build(words, cfg, t_end):
    """words: [[start, end, word]] (cut time) -> [(start, end, [(word, t)])] phrases.
    A phrase ends at a sentence end, before max_chars, or before it would need more than max_lines measured lines."""
    cfg = resolve(cfg)
    fixes = cfg.get("fixes", {}) or {}; maxc = cfg.get("max_chars", 34); mode = cfg.get("case", "sentence")
    maxl = max(1, int(cfg.get("max_lines", 2))); maxc = 1 if cfg.get("style") == "one_word" else maxc
    L, nlines = _measure(cfg)
    toks = []
    for s, e, w in words: toks.append((fix_word(w, fixes), s))
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

def _shadow(im, cfg):
    """the caption's drop shadow: its alpha blurred (style captions.shadow_blur), at shadow_alpha, shadow_dy lower, as a
    canvas layer. Worked on the text's box plus the blur's reach and its edge replication (twice the box blur's support),
    so every pixel equals the full-frame blur + paste and the rest of the canvas stays clear."""
    import math
    rad = cfg.get("shadow_blur", 7) * G.U; dy = int(round(cfg.get("shadow_dy", 3) * G.U)); k = cfg.get("shadow_alpha", .7)
    base = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    bb = im.getbbox()
    if bb is None: return base
    pad = 2 * 3 * (math.ceil(rad) + 2) + 4
    x0, y0, x1, y1 = max(0, bb[0] - pad), max(0, bb[1] - pad), min(G.W, bb[2] + pad), min(G.H, bb[3] + pad)
    al = Image.fromarray(np.asarray(im.crop((x0, y0, x1, y1)))[..., 3])
    sh = al.filter(ImageFilter.GaussianBlur(rad)).point(lambda v: int(v * k))
    base.paste(Image.new("RGBA", sh.size, (0, 0, 0, 255)), (x0, y0 + dy), sh)
    return base

def _bright_under(im, frame, sz):
    """the bright end (p98 luminance) of the picture under a text layer, as an RGB tuple, or None without a frame. The
    bed is then sized for what is really behind the words, not only for the style's assumed mid-tone (GFX-15 on the first
    real job: a white caption over a window-lit cheek at 2.8:1)"""
    if frame is None or getattr(frame, "ndim", 0) != 3 or frame.shape[2] < 3: return None
    bb = im.getbbox()                                            # alpha != 0
    if bb is None: return None
    p = int(sz * .3); H_, W_ = frame.shape[:2]
    y0, y1, x0, x1 = max(0, bb[1] - p), min(H_, bb[3] - 1 + p + 1), max(0, bb[0] - p), min(W_, bb[2] - 1 + p + 1)
    patch = np.asarray(frame[y0:y1, x0:x1, :3], np.float32)
    if patch.size == 0: return None
    if patch.max() <= 1.001: patch = patch * 255
    L = .2126 * patch[..., 0] + .7152 * patch[..., 1] + .0722 * patch[..., 2]
    sel = patch[L >= np.percentile(L, 98)]          # p98: a thin bright detail (a chain, a mic clip) crossing the words counts too
    return tuple(int(round(v)) for v in sel.mean(0)) if len(sel) else None

def element(TL, t, chin, events, S, frame=None):
    """the caption layer at time t (or None) as a templates.El"""
    from .templates import El
    cfg = resolve(S.get("captions") or {}); style = cfg.get("style", "word_reveal")
    if style == "none": return None
    if style not in STYLES: style = "word_reveal"
    for a, b, words in events:
        if not (a <= t < b): continue
        lead = cfg.get("lead_s", .03)
        spoken = [wt <= t + lead or (i == 0 and t >= a) for i, (_, wt) in enumerate(words)]   # an event pulled onto a cut shows its first word from its start
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
            layers.append(_shadow(im, cfg))
            if cfg.get("legible", True):
                bg = G.sget("legibility.video_bg_broll", "#C8C8C8") if over_broll else None   # full-bleed footage runs brighter than a presenter's wall
                seen = _bright_under(im, frame, sz) if G.sget("legibility.measure", True) else None
                if seen is not None and G.lum(seen) > G.lum(G.col(bg) or G._rgb(G.sget("legibility.video_bg", "#B4B4B4"))):
                    bg = seen      # the real frame is brighter than the assumed worst case (a window-lit cheek): size the bed for it
                # the bed keeps the main colour's polarity but is as dark as the darkest light fill needs: an accent word
                # (emphasis / highlight) is darker than white and failed GFX-15 on a mid-tone shirt under the white's bed
                fills = [em_col[:3] for tk, *_ in placed if tk["emph"]] + ([hi[:3]] if style in ("highlight", "one_word", "karaoke") and cfg.get("highlight_mode", "text") != "pill" else [])
                Lb = G.lum(G.col(bg) or G._rgb(G.sget("legibility.video_bg", "#B4B4B4"))); need = G.need_contrast(sz) * G.sget("legibility.margin", 1.15)
                force = max([0.0] + [1 - max(0., (G.lum(c) + .05) / need - .05) / max(1e-6, Lb) for c in fills if G.lum(c) <= G.lum(col[:3]) and G.lum(c) < Lb])
                bed = G.legible_bed(im, col[:3], sz, bg=bg, force=force, reach=2 + 2 * math.ceil(outline * G.U))   # an outline pushes the glyph edge out
                if bed is not None: layers.insert(0, bed)
        out = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
        boxes = [b for b in (L.getbbox() for L in layers + [im]) if b]      # a clear source pixel leaves the clear canvas as it is:
        if boxes:                                                          # composite only the union of the visible boxes
            u = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
            for L in layers + [im]: out.alpha_composite(L, dest=u[:2], source=u)
        return El(out, f"caption@{a:.2f}", "caption", text=" ".join(w for w, _ in words), t_key=words[0][1], font=fname)
    return None
