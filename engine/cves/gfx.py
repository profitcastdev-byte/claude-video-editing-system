"""CVES graphics kit: stage, cards, icon wells, pills, check / cross states, corner brackets, type, timing and cue helpers.
Colours, stage, fonts and motion are NOT fixed here: `apply_style(style.load(pr))` sets them from the style profile
(docs/STYLE.md). The names below are neutral fallbacks only. Everything is drawn on the configured canvas (`set_canvas`,
from style `canvas.size`; default 1080x1920), supersampled 2x for clean edges. Read `G.W` / `G.H` / `G.U` at call time,
never import them by value: the canvas is set per process (render workers re-set it in their initializer).
`U` = min(W, H) / 1080 is the layout unit: px constants designed for a 1080-wide portrait frame scale by it.

Timing: templates quantise every animation start to a whole frame with `q(t, fps)` and use `enter(t, t0, d)` for entries,
so an element is first visible on the frame of its word (MOT-07, SND-07). The frame rate comes from `ctx["fps"]`, else
from the module-level `FPS` that render's Timeline sets (`G.FPS = TL.FPS`); with neither, times pass through unchanged."""
import math, os, re, numpy as np
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920      # the canvas of this process: set_canvas() changes it (read G.W / G.H at call time)
DESIGN = (1080, 1920)  # the reference design space of fixed-layout templates (module-level DESIGN = True)
U = 1.0                # layout unit: min(W, H) / 1080
PW, PH = W, H          # pixel size of the layers drawn (= the canvas, except inside a raster-scaled template call)
R = 1.0                # raster scale: layer px per layout px (PW / W). Relative templates lay out on a 1080-short-side
                       # canvas and are rasterised at the real canvas (set_raster), so 4K graphics are drawn at 4K
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))   # repo root
FONTS = os.path.join(ROOT, "assets", "fonts")
ICONS = os.path.join(ROOT, "assets", "icons")
MINT = (76, 141, 255); MINT_D = (42, 91, 184); WHITE = (255, 255, 255)     # "MINT" = the accent slot (historic name)
CARD = (22, 22, 27); CARD_B = (52, 52, 63); WELL = (36, 36, 58); GOLD = (214, 178, 108)
STAR = (255, 196, 70); NEG = (229, 72, 77)                                   # rating stars; negative marks (comparison crosses)
MUTED = (170, 170, 178); SURFACE = (29, 29, 42); LINE = (70, 70, 90)        # derived in apply_style from the palette

FONT_FILES = {"m": "Poppins-Medium.ttf", "sb": "Poppins-SemiBold.ttf", "b": "Poppins-Bold.ttf", "xb": "Poppins-ExtraBold.ttf",
              "serif": "CormorantGaramond.ttf", "marc": "Marcellus.ttf"}
STAGE = {"background": (11, 11, 13), "glow_bottom": (42, 42, 51), "dot_grid": (138, 138, 153)}
STYLE = {}            # the merged style profile of this process (apply_style)
FPS = None            # the timeline frame rate (render sets it; ctx["fps"] wins)

def sget(path, default=None):
    """dotted lookup in the applied style profile"""
    cur = STYLE
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return default if cur is None else cur

def _font_path(name):
    p = FONT_FILES.get(name, name)
    return p if os.path.isabs(p) else os.path.join(FONTS, p)

@lru_cache(None)
def font(name, size):
    f = ImageFont.truetype(_font_path(name), max(1, int(size)))
    if name == "serif":
        try: f.set_variation_by_axes([700])
        except Exception: pass
    return f

# ---------- easing
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def ease_out(p): return 1 - (1 - p) ** 3
def ease_in(p): return p ** 3
def ease_io(p): return 3 * p * p - 2 * p ** 3
def back(p, s=None):
    s = sget("motion.overshoot", 1.6) if s is None else s
    p -= 1; return p * p * ((s + 1) * p + s) + 1
def mo(key, default):
    """motion token from the style (`motion.entry_s`, `motion.stagger_s`, `motion.slide_px`, ...)"""
    return sget(f"motion.{key}", default)

# ---------- frame timing (MOT-07: every animation start on a whole frame)
def fps_of(ctx=None): return (ctx or {}).get("fps") or FPS

def q(t, fps=None):
    """quantise a time to the nearest whole frame (pass-through when the rate is unknown)"""
    f = fps or FPS
    if t is None or not f: return t
    return round(t * f) / f

def enter(t, t0, d, fps=None):
    """entry progress 0..1 that is first > 0 ON the frame of q(t0) (prog() would only show it one frame later)"""
    f = fps or FPS
    if f: t0 = q(t0, f) - .5 / f
    return prog(t, t0, d)

# ---------- stage
def stage():
    """Dark stage, accent glow rising from the bottom, dot grid fading upward. float32 HxWx3 0..1 (the current canvas)"""
    return _stage(W, H)

@lru_cache(4)
def _stage(W, H):
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
    base = np.zeros((H, W, 3), np.float32) + np.array(STAGE['background'], np.float32) / 255
    if sget("stage.glow", True):
        glow = np.clip((y - .48) / .52, 0, 1) ** 1.8 * (1 - .35 * x ** 2)
        base += glow[..., None] * (np.array(STAGE['glow_bottom'], np.float32) / 255)
    if sget("stage.dots", True):
        dots = Image.new("L", (W, H), 0); d = ImageDraw.Draw(dots)
        step = 56 * min(W, H) / 1080 if min(W, H) != 1080 else 56
        for gy in np.arange(30 * step / 56, H, step):
            for gx in np.arange(14 * step / 56, W, step):
                d.ellipse((gx - 1.6, gy - 1.6, gx + 1.6, gy + 1.6), fill=255)
        dots = np.asarray(dots, np.float32)[..., None] / 255
        fade = (.10 + .30 * np.clip((y - .25) / .75, 0, 1))[..., None]
        base = base * (1 - dots * fade) + np.array(STAGE['dot_grid'], np.float32) / 255 * dots * fade
    return base.astype(np.float32)

# ---------- layers (RGBA float, premultiplied composite helpers)
def new(): return Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
def to_np(im): a = np.asarray(im, np.float32) / 255; return a
def over(dst, im, opacity=1.0, inplace=False):
    """dst float HxWx3, im PIL RGBA or float HxWx4. A PIL layer is blended only inside the box of its visible pixels:
    outside it the full-frame formula gives dst exactly (dst * 1 + rgb * 0), so the result is the same and a small element
    costs its own size, not the frame's. inplace=True writes into dst (the caller owns it); else dst is left untouched."""
    if isinstance(im, Image.Image) and im.mode == "RGBA" and im.size == (dst.shape[1], dst.shape[0]):
        bb = im.getbbox()                     # alpha > 0
        out = dst if inplace else dst.copy()
        if bb is None: return out
        x0, y0, x1, y1 = bb
        a = np.asarray(im.crop(bb), np.float32) / 255
        al = a[..., 3:4] * opacity
        out[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - al) + a[..., :3] * al
        return out
    a = to_np(im) if isinstance(im, Image.Image) else im
    al = a[..., 3:4] * opacity
    return dst * (1 - al) + a[..., :3] * al

def rrect(d, box, r, fill=None, outline=None, width=2):
    x0, y0, x1, y1 = box
    if x1 - x0 < 1 or y1 - y0 < 1: return
    d.rounded_rectangle((x0, y0, x1, y1), max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2)), fill=fill, outline=outline, width=width)

# ---------- colour
def _rgb(v):
    if isinstance(v, (list, tuple)): return tuple(int(x) for x in v[:3])
    v = str(v).lstrip("#"); return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))

_SLOTS = {"accent": "MINT", "accent_dark": "MINT_D", "text": "WHITE", "card": "CARD", "card_border": "CARD_B", "icon_well": "WELL",
          "gold": "GOLD", "star": "STAR", "negative": "NEG", "muted": "MUTED", "surface": "SURFACE", "line": "LINE"}
def col(v, default=None):
    """a colour from a param: a palette slot name (accent, text, gold, muted, negative, ...), '#hex' or [r, g, b]; None -> default"""
    if v is None or v == "": return default
    if isinstance(v, str) and v in _SLOTS: return globals()[_SLOTS[v]]
    if isinstance(v, str) and v in (STYLE.get("colors") or {}): return _rgb(STYLE["colors"][v])
    try: return _rgb(v)
    except Exception: return default

def mix(a, b, t): return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def lum(rgb):
    """WCAG relative luminance of an sRGB colour (0..255)"""
    c = [v / 255 for v in rgb[:3]]
    c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]

def contrast(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + .05) / (min(la, lb) + .05)

def need_contrast(size_px):
    """WCAG target for text of this pixel size (style `legibility`)"""
    big = size_px >= sget("legibility.large_px", 48) * U          # large_px is at a 1080 short side
    return sget("legibility.large_contrast", 3.0) if big else sget("legibility.min_contrast", 4.5)

def legible_bed(im, fg, size_px, bg=None, force=0.0, reach=2):
    """a soft dark (or light) bed behind text so it reads at the WCAG target over video (GFX-15).
    im: the text layer (RGBA). fg: text colour. bg: what is behind it (default: style `legibility.video_bg`, an assumed
    worst-case mid-tone). Returns an RGBA layer to draw UNDER the text, or None when the colours already pass."""
    bg = col(bg) or _rgb(sget("legibility.video_bg", "#B4B4B4")); need = need_contrast(size_px) * sget("legibility.margin", 1.15)     # margin for AA, grade and entry fades
    Lf, Lb = lum(fg), lum(bg)
    if Lf >= Lb:   # light text: darken the surround until (Lf+.05)/(Lb'+.05) >= need
        tgt = (Lf + .05) / need - .05; a = 1 - max(0., tgt) / max(1e-6, Lb); shade = (0, 0, 0)
    else:          # dark text: lighten the surround
        tgt = need * (Lf + .05) - .05; a = (tgt - Lb) / max(1e-6, 1 - Lb); shade = (255, 255, 255)
    a = clamp(max(a, force), 0, sget("legibility.plate_max", .85))
    if a <= .02: return None
    import cv2, math
    r = max(3, int(size_px * sget("legibility.bed_spread", .18) * R))   # size_px is layout px; the layer is R x larger
    sg = max(1., r * .6); k = 2 * max(2, int(round(reach * R))) + 1
    bb = im.getbbox()                                                   # the text's box (alpha > 0)
    if bb is None: return Image.new("RGBA", im.size, (0, 0, 0, 0))
    # work on the text's box plus everything the bed can reach (dilate r, blur 3 sigma) and the blur's border reflection
    # (another 3 sigma): outside it the bed is zero, inside it every value is what the full-frame filters give
    pad = r + k + 2 * (math.ceil(3 * sg) + 2) + 2
    x0, y0, x1, y1 = max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.size[0], bb[2] + pad), min(im.size[1], bb[3] + pad)
    al = np.asarray(im.crop((x0, y0, x1, y1)))[..., 3]
    m = cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    m = cv2.GaussianBlur(m, (0, 0), sg)                                 # soft: a hard-edged bed reads as a second "ink" class
    # full strength right at the glyph edge (the 3-7 px ring GFX-15 reads); outlined text: al includes the stroke, so reach past it
    m = np.maximum(m, cv2.dilate(al, np.ones((k, k), np.uint8)))
    crop = np.zeros(al.shape + (4,), np.uint8); crop[..., :3] = shade; crop[..., 3] = (m.astype(np.float32) * a).astype(np.uint8)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.paste(Image.fromarray(crop), (x0, y0))
    return out

# ---------- type
SEPS = "·•|/–—"
def tidy(s):
    """typesetting hygiene (GFX-17): no double / leading / trailing spaces"""
    return " ".join(str(s or "").split())

def _runs(s, f, tracking=0):
    """split text into (piece, x, kind) runs. Separators surrounded by spaces get drawn spacing (sep gap), not repeated spaces.
    kind: "t" text | "e" a colour-emoji cluster (drawn from the emoji font). Glyphs the font lacks are dropped (never tofu)."""
    s = re.sub(r"\s+", " ", str(s or "")); gap = f.size * sget("type.sep_gap_em", .32) + tracking * 1.5   # tracked type gets a wider gap; collapse runs; a lone " " keeps its width
    parts = re.split(r" ([" + re.escape(SEPS) + r"]) ", s)
    out, x = [], 0.
    for j, piece in enumerate(parts):
        if j % 2: x += gap
        for seg, kind in _segs(piece, f):
            out.append((seg, x, kind)); x += _adv(seg, f, tracking, kind)
        if j % 2: x += gap
    return out, x

def _segs(piece, f):
    if not piece: return []
    if all(ord(c) < 0x80 for c in piece): return [(piece, "t")]
    out = []; emo = emoji_font() is not None
    for txt, e in emoji_split(piece):
        if e:
            if emo and emoji_img(txt, 32) is not None: out.append((txt, "e")); continue
            e = False                                   # not in the emoji font: the text font may still have it (e.g. a star)
        txt = "".join(c for c in txt if has_glyph(f, c))
        if txt: out.append((txt, "t"))
    return out

@lru_cache(8192)
def has_glyph(f, ch):
    """False when the font would draw its .notdef box for ch"""
    if ord(ch) < 0x80 or ch.isspace(): return True
    try:
        a, b = f.getmask(ch), f.getmask("\U0010FFFD")
        if a.size != b.size or f.getlength(ch) != f.getlength("\U0010FFFD"): return True
        return Image.Image()._new(a).tobytes() != Image.Image()._new(b).tobytes()
    except Exception: return True

def _emoji_w(seg, f): return f.size * 1.0 * max(1, len([c for c in seg if not (0xFE00 <= ord(c) <= 0xFE0F or ord(c) == 0x200D)]))

def _adv(s, f, tracking=0, kind="t"):
    if not s: return 0.
    if kind == "e": return _emoji_w(s, f)
    if tracking == 0: return f.getlength(s)
    return sum(f.getlength(ch) for ch in s) + tracking * (len(s) - 1)

def text_w(s, f, tracking=0):
    """advance width exactly as draw_text lays the string out"""
    return _runs(s, f, tracking)[1]

@lru_cache(4096)
def _inkbox(piece, f):
    """true ink box of a string at the pen (getbbox() only reports the advance horizontally)"""
    try:
        m, (ox, oy) = f.getmask2(piece, anchor="ls"); bb = m.getbbox()
    except Exception: bb = None
    if not bb: return None
    return ox + bb[0], ox + bb[2], oy + bb[1], oy + bb[3]

def ink(s, f, tracking=0):
    """(left, right, top, bottom) ink extents relative to the pen at the baseline, as draw_text draws"""
    l, r, t, b = 1e9, -1e9, 1e9, -1e9
    def add(bb, x):
        nonlocal l, r, t, b
        if bb: l, r, t, b = min(l, x + bb[0]), max(r, x + bb[1]), min(t, bb[2]), max(b, bb[3])
    for piece, x, kind in _runs(s, f, tracking)[0]:
        if kind == "e": add((0, _emoji_w(piece, f), -f.size * .82, f.size * .1), x)
        elif tracking == 0: add(_inkbox(piece, f), x)
        else:
            for ch in piece:
                if not ch.isspace(): add(_inkbox(ch, f), x)
                x += f.getlength(ch) + tracking
    return (0., 0., 0., 0.) if l > r else (l, r, t, b)

def draw_text(d, xy, s, f, fill, tracking=0, anchor="ls", stroke=0, stroke_fill=None):
    """tracking in px. anchor on the baseline: ls (pen left) | li (ink left) | ms (ink centre) | rs (ink right).
    Centring uses the drawn ink, not the advance (trailing space / side bearings / kerning never shift the axis, GFX-08).
    Emoji are drawn from the colour-emoji font when one exists (on the supersampled layer), else skipped."""
    x, y = xy; runs, _ = _runs(s, f, tracking)
    if anchor[0] != "l" or anchor == "li":
        l, r, _, _ = ink(s, f, tracking)
        if tracking == 0 and len(runs) == 1 and runs[0][2] == "t" and not runs[0][1] and hasattr(d, "_f"):
            # a supersampled layer draws with a k-times font whose advances round differently from the 1x font: measure the
            # ink of the font that really draws, or a centred line lands up to ~3 px off the axis of its box (GFX-08)
            bb = _inkbox(runs[0][0], d._f(f))
            if bb: l, r = bb[0] / d.k, bb[1] / d.k
        x -= {"m": (l + r) / 2, "r": r, "l": l}[anchor[0]]
    kw = {"stroke_width": stroke, "stroke_fill": stroke_fill} if stroke else {}
    op = (fill[3] / 255) if isinstance(fill, tuple) and len(fill) > 3 else 1.
    for piece, px, kind in runs:
        if kind == "e":
            if hasattr(d, "paste"):
                k = getattr(d, "k", 1); im = emoji_img(piece, int(f.size * .95 * k))
                if im is not None: d.paste(im, x + px, y - f.size * .82, f.size * .95 * im.width / im.height, opacity=op)
            continue
        if tracking == 0: d.text((x + px, y), piece, font=f, fill=fill, anchor="ls", **kw); continue
        xx = x + px
        for ch in piece:
            d.text((xx, y), ch, font=f, fill=fill, anchor="ls", **kw); xx += f.getlength(ch) + tracking

def fit_font(name, size, s, max_w, tracking=0, min_size=18):
    """the largest font <= size whose text fits max_w (long params never overflow the safe zone)"""
    sz = int(size)
    while sz > min_size and text_w(s, font(name, sz), tracking) > max_w: sz -= 2
    return font(name, sz)

def wrap(s, f, max_w, tracking=0, max_lines=None):
    """greedy word wrap by measured width"""
    lines, cur = [], []
    for w in tidy(s).split(" "):
        if cur and text_w(" ".join(cur + [w]), f, tracking) > max_w: lines.append(" ".join(cur)); cur = [w]
        else: cur.append(w)
    if cur: lines.append(" ".join(cur))
    return lines[:max_lines] if max_lines else lines

# ---------- numbers (stat / counter / chart)
def fmt_num(v, decimals=0, grouping=None, thousands=None, decimal=None):
    """grouping: intl (1,234,567) | indian (12,34,567: lakh / crore) | none. Separators from style `locale`."""
    grouping = grouping or sget("locale.grouping", "intl"); th = sget("locale.thousands", ",") if thousands is None else thousands
    dp = sget("locale.decimal", ".") if decimal is None else decimal
    neg = v < 0; v = abs(v); s = f"{v:.{int(decimals)}f}"; ip, _, fp = s.partition(".")
    if grouping == "indian" and len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]; grp = []
        while len(head) > 2: grp.insert(0, head[-2:]); head = head[:-2]
        if head: grp.insert(0, head)
        ip = th.join(grp + [tail])
    elif grouping != "none":
        ip = f"{int(ip):,}".replace(",", th)
    return ("-" if neg else "") + ip + (dp + fp if fp else "")

def count_value(value, a, dur, t, start_value=0, ease=None):
    p = prog(t, a, dur); return start_value + (value - start_value) * (ease or ease_out)(p)

def count_ticks(value, a, dur, fps=None, start_value=0, decimals=0, n_max=8, ease=None):
    """times (whole frames) at which the displayed, eased count changes, thinned to <= n_max ticks: count-up pops follow the
    digits the viewer sees (SND-07) instead of a fixed grid"""
    f = fps or FPS or 30; n = max(1, int(round(dur * f))) + 1; ts, key, prev = [], [], None; a0 = q(a, f) - .5 / f   # same clock as the drawn digits
    for k in range(n + 1):
        t = q(a, f) + k / f; shown = fmt_num(count_value(value, a0, dur, t, start_value, ease), decimals)
        if prev is not None and shown != prev:
            ts.append(t)
            if len(shown) > len(prev) or not key: key.append(t)        # first change / a new digit or separator: a new pixel event
        prev = shown
    rest = [x for x in ts if x not in key]; room = max(0, n_max - len(key))
    if len(rest) > room: rest = [rest[int(round(j * (len(rest) - 1) / max(1, room - 1)))] for j in range(room)] if room > 1 else rest[-room:] if room else []
    return sorted(set(key + rest))

# ---------- cues
def cue(t, name, gain, kw=None): return (t, name, gain, dict(kw or {}))

def cues_out(cues, ctx=None, fps=None):
    """finalise a template's cue list: clamp to the template's start (nothing sounds before it is on screen), quantise to whole
    frames (the visual event's frame), and vary pitch/gain of identical back-to-back cues (SND-09)"""
    f = fps or fps_of(ctx); t0 = (ctx or {}).get("start")
    out = []
    for c in cues:
        t, name, gain, kw = c[0], c[1], c[2], dict(c[3] if len(c) > 3 else {})
        if t is None: continue
        if t0 is not None and t < t0: t = t0
        if name in _TRANSITION_SFX and "pitch" not in kw: kw["pitch"] = 1.5     # half-step offset: never identical to a transition whoosh / swipe (SND-09)
        out.append((q(t, f), name, gain, kw))
    return vary(out)

_TRANSITION_SFX = ("swipe", "whoosh")
_VARY = (0, .6, -.5, 1.1, -1.0, .3, 1.6, -.8)
def vary(cues):
    """no two consecutive cues of the same sound with the same pitch: nudge pitch (semitones) and gain slightly"""
    cues = sorted(cues, key=lambda c: c[0]); out, run = [], 0
    for c in cues:
        t, name, gain, kw = c; kw = dict(kw)
        if out and out[-1][1] == name and out[-1][3].get("pitch", 0) == kw.get("pitch", 0) and str(out[-1][3].get("trim")) == str(kw.get("trim")):
            run += 1; dv = _VARY[run % len(_VARY)] or .45
            kw["pitch"] = round(kw.get("pitch", 0) + dv, 2); gain = gain - (.5 if run % 2 else 0)
        else: run = 0
        out.append((t, name, gain, kw))
    return out

# ---------- icons (drawn inside a well, centred at cx, cy, size s)
MAT = {"post": "event", "link": "link", "chat": "chat", "star": "star", "search": "search", "pin": "place", "phone": "call",
       "event": "event", "place": "place", "call": "call"}
def icon_file(kind):
    """icon name -> file in assets/icons (MAT alias, or any <name>_512.png dropped there); None when missing"""
    if not kind: return None
    n = MAT.get(kind, kind)
    return n + "_512.png" if os.path.exists(os.path.join(ICONS, n + "_512.png")) else None

def icon(d, kind, cx, cy, s, col=None, w=4):
    """Material Design icons (assets/icons, Apache-2.0), tinted and pasted crisp at 2x. Unknown names draw nothing."""
    col = col or MINT; f = icon_file(kind)
    if f: d.paste_icon(f, cx, cy, s * (1.25 if kind != "star" else 1.15), col)

def state(d, kind, cx, cy, r, p=1.0, colr=None):
    """check (accent filled) | cross (outlined) | xfill (negative filled) | num:<n> (numbered); p = pop progress"""
    if p <= 0: return
    rr = r * max(0., back(clamp(p)))
    if rr < .5: return
    k = rr / r
    if kind == "check":
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=colr or MINT)
        if p > .5: d.line([(cx - .375 * r * k, cy + .04 * r * k), (cx - .08 * r * k, cy + .33 * r * k), (cx + .42 * r * k, cy - .29 * r * k)], fill=CARD, width=int(.21 * r * k) + 1, joint="curve")
    elif kind == "xfill":
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=colr or NEG)
        if p > .5:
            e = .3 * r * k; d.line((cx - e, cy - e, cx + e, cy + e), fill=WHITE, width=int(.17 * r * k) + 1); d.line((cx - e, cy + e, cx + e, cy - e), fill=WHITE, width=int(.17 * r * k) + 1)
    elif str(kind).startswith("num:"):
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=colr or MINT)
        if p > .5: draw_text(d, (cx, cy + r * .36 * k), str(kind)[4:], font("b", max(8, int(r * 1.05 * k))), CARD, anchor="ms")
    else:
        c = colr or mix(WHITE, CARD, .12)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=c, width=3)
        if p > .5:
            e = .29 * r * k
            d.line((cx - e, cy - e, cx + e, cy + e), fill=c, width=4)
            d.line((cx - e, cy + e, cx + e, cy - e), fill=c, width=4)

def brackets(d, box, L=46, col=None, w=3):
    col = col or LINE; x0, y0, x1, y1 = box
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=col, width=w); d.line((x, y, x, y + sy * L), fill=col, width=w)

def card_row(d, x, y, w, h, icon_kind, title, sub, st, p_in, p_state, label_font=None, sc=1.0, draw_icon=True):
    """One UI row card. p_in: entry progress (handled by caller via offset/alpha); p_state: check/cross pop.
    sc scales the inner px (padding, type, radius, mark) with the row: h is usually 124 * sc"""
    rrect(d, (x, y, x + w, y + h), 22 * sc, fill=CARD + (240,), outline=CARD_B, width=3 * sc)
    p = 17 * sc; s = h - 2 * p; tx = x + 34 * sc
    if icon_kind:
        rrect(d, (x + p, y + p, x + p + s, y + p + s), 14 * sc, fill=WELL)
        if draw_icon: icon(d, icon_kind, x + p + s / 2, y + p + s / 2, s * .52)
        tx = x + p + s + 28 * sc
    f1 = label_font or font("b", 34 * sc); f2 = font("b", 34 * sc)
    room = (x + w - (100 if st else 34) * sc) - tx
    if text_w(title, f1, 1) > room: f1 = fit_font("b", f1.size, title, room, 1)
    if sub and text_w(sub, f2, 1) > room: f2 = fit_font("b", f2.size, sub, room, 1)
    if sub:
        draw_text(d, (tx, y + h / 2 - 6 * sc), title, f1, WHITE, tracking=1)
        draw_text(d, (tx, y + h / 2 + 34 * sc), sub, f2, MINT, tracking=1)
    else:
        draw_text(d, (tx, y + h / 2 + 12 * sc), title, f1, WHITE, tracking=1)
    if st: state(d, st, x + w - 46 * sc, y + h / 2, 24 * sc, p_state)

def label(d, cx, y, s, size=26, col=None, tracking=7):
    draw_text(d, (cx, y), s, font("sb", size), col or MUTED, tracking=tracking, anchor="ms")

def pill(d, cx, cy, s, f, filled=True, pad=(30, 16), col=None, sc=1.0, text_p=1.0):
    """a pill centred at (cx, cy). sc scales it from its own centre (entry pop); the label shows once text_p > .45"""
    col = col or MINT
    tw = text_w(s, f, 2); bw, bh = (tw + pad[0] * 2) * sc, (f.size + pad[1] * 2) * sc
    if bw < 1 or bh < 1: return None
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    if filled: rrect(d, box, bh / 2, fill=col)
    else: rrect(d, box, bh / 2, outline=WHITE, width=3)
    if text_p > .45: draw_text(d, (cx, cy + f.size * .36), s, f, CARD if filled else WHITE, tracking=2, anchor="ms")
    return box

def ss_layer(fn, scale=2):
    """draw at 2x then downsample for clean anti-aliasing. fn(draw, k) where k = scale (layer px per layout px)"""
    im = Image.new("RGBA", (PW * scale, PH * scale), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), scale * R)
    return im.resize((PW, PH), Image.LANCZOS)

def shadow(im, r=18, alpha=.55, dy=10):
    """r and dy in layout px (scaled by the raster scale R)"""
    a = np.asarray(im)[..., 3]
    sh = Image.fromarray(a).filter(ImageFilter.GaussianBlur(r * R))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); blk = Image.new("RGBA", im.size, (0, 0, 0, 255))
    out.paste(blk, (0, int(round(dy * R))), sh.point(lambda v: int(v * alpha)))
    out.alpha_composite(im); return out

def shadow_only(im, r=18, alpha=.55, dy=10):
    """just the drop shadow of a layer (log it as its own decor element, id ending '.bed', so the text bbox stays the ink)"""
    a = np.asarray(im)[..., 3]
    sh = Image.fromarray(a).filter(ImageFilter.GaussianBlur(r * R))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), (0, int(round(dy * R))), sh.point(lambda v: int(v * alpha)))
    return out

def alpha(im, a):
    """scale a layer's opacity"""
    if a >= 1: return im
    x = np.asarray(im).copy(); x[..., 3] = (x[..., 3] * max(0., a)).astype(np.uint8); return Image.fromarray(x)

# ---------- 2x supersampled drawing with 1x coordinates
_NAME = {}
_font0 = font
@lru_cache(None)
def font(name, size):
    f = _font0(name, size); _NAME[id(f)] = (name, size); return f

def _sc(v, k):
    if isinstance(v, (int, float, np.number)): return float(v) * k      # np.float32 is not a float subclass: scale it too
    if isinstance(v, (list, tuple)): return type(v)(_sc(x, k) for x in v)
    return v

class SD:
    """ImageDraw proxy: 1x coordinates in, k-times drawing out."""
    def __init__(self, im, k): self.d = ImageDraw.Draw(im); self.k = k; self.im = im
    def _f(self, f): n, s = _NAME[id(f)]; return _font0(n, s * self.k)
    def rounded_rectangle(self, box, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(_sc(box, self.k), r * self.k, fill=fill, outline=outline, width=max(1, int(round(width * self.k))))
    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(_sc(box, self.k), fill=fill, outline=outline, width=max(1, int(round(width * self.k))))
    def arc(self, box, a0, a1, fill=None, width=1):
        self.d.arc(_sc(box, self.k), a0, a1, fill=fill, width=max(1, int(round(width * self.k))))
    def pieslice(self, box, a0, a1, fill=None):
        self.d.pieslice(_sc(box, self.k), a0, a1, fill=fill)
    def line(self, xy, fill=None, width=1, joint=None):
        self.d.line(_sc(list(xy), self.k), fill=fill, width=max(1, int(round(width * self.k))), joint=joint)
    def polygon(self, xy, fill=None, outline=None, width=1):
        self.d.polygon(_sc(list(xy), self.k), fill=fill, outline=outline, width=max(1, int(round(width * self.k))))
    def rectangle(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(_sc(box, self.k), fill=fill, outline=outline, width=max(1, int(round(width * self.k))))
    def paste_icon(self, name, cx, cy, size, col=None):
        col = col or MINT
        k = self.k
        if size * k < 4: return
        im = _icon_img(name, int(size * k), tuple(col[:3]))
        self.im.alpha_composite(im, (int(cx * k - im.width / 2), int(cy * k - im.height / 2)))
    def paste(self, img, x, y, w=None, opacity=1.0):
        """paste an RGBA image with its top-left at 1x (x, y), width w (1x px; height keeps the aspect)"""
        k = self.k; w = w or img.width / k; px = max(1, int(round(w * k))); ph = max(1, int(round(px * img.height / img.width)))
        im = img.resize((px, ph), Image.LANCZOS) if (px, ph) != img.size else img
        if opacity < 1: im = alpha(im, opacity)
        X, Y = int(round(x * k)), int(round(y * k))
        if X >= self.im.width or Y >= self.im.height or X + px <= 0 or Y + ph <= 0: return
        if X < 0 or Y < 0:
            im = im.crop((max(0, -X), max(0, -Y), im.width, im.height)); X, Y = max(0, X), max(0, Y)
        self.im.alpha_composite(im, (X, Y))
    def text(self, xy, s, font=None, fill=None, anchor=None, stroke_width=0, stroke_fill=None):
        kw = {"stroke_width": int(round(stroke_width * self.k)), "stroke_fill": stroke_fill} if stroke_width else {}
        self.d.text(_sc(xy, self.k), s, font=self._f(font), fill=fill, anchor=anchor, **kw)

@lru_cache(None)
def _icon_img(name, px, col=(25, 230, 160)):
    p = os.path.join(ICONS, name)
    a = Image.open(p).convert("RGBA").resize((px, px), Image.LANCZOS).getchannel("A")
    im = Image.new("RGBA", (px, px), col + (255,)); im.putalpha(a); return im

def layer(fn, k=2):
    """fn(d) draws with 1x layout coordinates on a supersampled canvas; returns RGBA at the layer pixel size (PW x PH:
    the canvas, or the real canvas when a relative template is rasterised at R != 1: coordinates, type and strokes scale)"""
    W, H = PW, PH
    im = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0)); fn(SD(im, k * R))
    bb = im.getbbox()
    if not bb: return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = 4 * k                                                       # resize only the drawn region (+ the filter support): same pixels, far faster
    x0, y0 = max(0, (bb[0] - m) // k * k), max(0, (bb[1] - m) // k * k)
    x1, y1 = min(W * k, -(-(bb[2] + m) // k) * k), min(H * k, -(-(bb[3] + m) // k) * k)
    if (x1 - x0) * (y1 - y0) > .6 * W * H * k * k: return im.resize((W, H), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(im.crop((x0, y0, x1, y1)).resize(((x1 - x0) // k, (y1 - y0) // k), Image.LANCZOS), (x0 // k, y0 // k))
    return out

@lru_cache(64)
def image(path):
    """an asset image (RGBA), cached per process"""
    return Image.open(path).convert("RGBA")

# ---------- scripts, fallback fonts, RTL, emoji
_SCRIPTS = [("devanagari", 0x0900, 0x097F, "hi"), ("bengali", 0x0980, 0x09FF, "bn"), ("gurmukhi", 0x0A00, 0x0A7F, "pa"),
            ("gujarati", 0x0A80, 0x0AFF, "gu"), ("oriya", 0x0B00, 0x0B7F, "or"), ("tamil", 0x0B80, 0x0BFF, "ta"),
            ("telugu", 0x0C00, 0x0C7F, "te"), ("kannada", 0x0C80, 0x0CFF, "kn"), ("malayalam", 0x0D00, 0x0D7F, "ml"),
            ("sinhala", 0x0D80, 0x0DFF, "si"), ("thai", 0x0E00, 0x0E7F, "th"), ("hebrew", 0x0590, 0x05FF, "he"),
            ("arabic", 0x0600, 0x06FF, "ar"), ("arabic", 0x0750, 0x077F, "ar"), ("arabic", 0xFB50, 0xFEFF, "ar"),
            ("cyrillic", 0x0400, 0x04FF, "ru"), ("greek", 0x0370, 0x03FF, "el"), ("hangul", 0xAC00, 0xD7AF, "ko"),
            ("kana", 0x3040, 0x30FF, "ja"), ("cjk", 0x4E00, 0x9FFF, "zh")]
RTL_SCRIPTS = {"hebrew", "arabic"}

def script_of(s):
    """(script, language code) of the first non-Latin letter in s, else (None, None)"""
    for ch in str(s or ""):
        o = ord(ch)
        if o < 0x0370: continue
        for name, a, b, lang in _SCRIPTS:
            if a <= o <= b: return name, lang
    return None, None

def is_rtl(s): return script_of(s)[0] in RTL_SCRIPTS

_SYSTEM_FALLBACK = ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/SFHebrew.ttf",
                    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "C:\\Windows\\Fonts\\arial.ttf"]
_WEIGHT_WORDS = {"m": "Medium", "sb": "SemiBold", "b": "Bold", "xb": "ExtraBold", "medium": "Medium", "semibold": "SemiBold", "bold": "Bold", "extrabold": "ExtraBold"}
def font_name_for(text, short="sb", language=None):
    """the font name (FONT_FILES key or file) for this text: the style's `font_files.script_fallback` (language code or
    script name -> file, or -> {weight: file}) when the text is in a non-Latin script; else the default font `short`"""
    try:                                            # the shared map + weight rules (cves.scripts) first
        from . import scripts as SC
        from .style import Style
        p = SC.font_for_text(text, {"m": "medium", "sb": "semibold", "b": "bold", "xb": "extrabold"}.get(short, short), Style(STYLE), language)
        if p: return p
    except Exception: pass
    script, lang = script_of(text)
    if not script: return short
    fb = sget("font_files.script_fallback", {}) or {}
    for key in (lang, script, language if language and script_of(text)[1] else None):
        v = fb.get(key) if key else None
        if not v: continue
        if isinstance(v, dict):
            v = v.get(short) or v.get({"m": "medium", "sb": "semibold", "b": "bold", "xb": "extrabold"}.get(short, short)) or next(iter(v.values()))
        v = str(v); want = _WEIGHT_WORDS.get(short)
        if want:                                       # same family, the requested weight, when that file exists
            alt = re.sub(r"-(Medium|SemiBold|Bold|ExtraBold|Regular)\.", f"-{want}.", v)
            if alt != v and os.path.exists(_font_path(alt)): v = alt
        if os.path.exists(_font_path(v)): return v
    for v in _SYSTEM_FALLBACK:                         # nothing configured for this script: a broad system font, if present
        if os.path.exists(v):
            try:
                if has_glyph(font(v, 40), next(c for c in str(text) if ord(c) >= 0x0370)): return v
            except Exception: pass
    return short

def tfont(short, size, text=None, language=None):
    """font for a piece of text: script fallback when needed (templates and captions)"""
    return font(font_name_for(text, short, language) if text else short, size)

def has_raqm():
    try:
        from PIL import features; return bool(features.check("raqm"))
    except Exception: return False

def visual_order(s):
    """RTL text without a shaping engine (libraqm): reverse to visual order so it reads right to left. Never raises."""
    try:
        if not is_rtl(s) or has_raqm(): return s
        return " ".join(w[::-1] if is_rtl(w) else w for w in reversed(str(s).split(" ")))
    except Exception: return s

_EMOJI = [(0x1F000, 0x1FAFF), (0x2600, 0x27BF), (0x2B50, 0x2B55), (0x231A, 0x231B), (0x23E9, 0x23FA), (0x3297, 0x3299)]
def is_emoji(ch):
    o = ord(ch)
    return o in (0x200D, 0xFE0F, 0x20E3) or any(a <= o <= b for a, b in _EMOJI)

def emoji_split(s):
    """[(piece, is_emoji)] runs"""
    out = []
    for ch in str(s):
        e = is_emoji(ch)
        if out and out[-1][1] == e: out[-1] = (out[-1][0] + ch, e)
        else: out.append((ch, e))
    return out

_EMOJI_FONTS = ["/System/Library/Fonts/Apple Color Emoji.ttc", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                "/usr/share/fonts/noto/NotoColorEmoji.ttf", "C:\\Windows\\Fonts\\seguiemj.ttf"]
@lru_cache(None)
def emoji_font():
    """a colour-emoji font (style `captions.emoji_font`, else a system one), or None: emoji are then skipped"""
    cands = [sget("captions.emoji_font")] + _EMOJI_FONTS
    for p in cands:
        if not p: continue
        p = _font_path(p)
        if not os.path.exists(p): continue
        for size in (109, 136, 160, 96, 64):          # bitmap colour fonts only load at their strike sizes
            try: return ImageFont.truetype(p, size), size
            except Exception: continue
    return None

@lru_cache(256)
def emoji_img(cluster, px):
    """a colour emoji rendered and scaled to px tall (RGBA), or None when no colour-emoji font exists"""
    ef = emoji_font()
    if not ef: return None
    f, n = ef; ch = cluster.replace("\u200d", "").replace("\ufe0f", "") if not has_raqm() else cluster
    ch = ch[:1] if not has_raqm() else ch
    if not ch: return None
    try:
        im = Image.new("RGBA", (n * 2, n * 2), (0, 0, 0, 0)); ImageDraw.Draw(im).text((n // 2, n // 2), ch, font=f, embedded_color=True)
        bb = im.getbbox()
        if not bb or (cluster != "\U0010FFFD" and _emoji_notdef() == im.crop(bb).tobytes()): return None
        im = im.crop(bb); return im.resize((max(1, int(px * im.width / im.height)), int(px)), Image.LANCZOS)
    except Exception: return None

@lru_cache(1)
def _emoji_notdef():
    ef = emoji_font()
    if not ef: return None
    f, n = ef; im = Image.new("RGBA", (n * 2, n * 2), (0, 0, 0, 0)); ImageDraw.Draw(im).text((n // 2, n // 2), "\U0010FFFD", font=f, embedded_color=True)
    bb = im.getbbox(); return im.crop(bb).tobytes() if bb else None

def strip_emoji(s): return "".join(ch for ch in str(s) if not is_emoji(ch))

# ---------- layout (safe zone from the style)
def margin(S=None):
    """platform.margin (px at a 1080 short side) on the current canvas"""
    m = (S.get("platform.margin", 60) if S is not None else sget("platform.margin", 60))
    return float(m) * U

def safe_zone(S=None, size=None):
    """(x0, y0, x1, y1) kept free of platform UI on the canvas, or None when the style disables it (platform.safe_zone: null).
    platform.safe_zone is in 1080x1920 px for 9:16 platforms: on a 9:16 canvas it is scaled to the canvas (identity at
    1080x1920). Any other aspect uses canvas.safe_zones (fractions of the canvas per aspect, the nearest aspect wins)."""
    get = S.get if S is not None else sget
    w, h = size or (W, H)
    if S is not None:                       # platform.target (styles/platforms.yaml) wins when its aspect fits the canvas
        from . import platforms as PF
        if PF.profile_fits(S, w, h): return tuple(float(v) for v in PF.box_px(PF.profile(S)["safe"], w, h))
    z = get("platform.safe_zone")
    if not z: return None
    if abs(w / h - 9 / 16) < .01:
        return (z[0] * w / 1080, z[1] * h / 1920, z[2] * w / 1080, z[3] * h / 1920) if (w, h) != (1080, 1920) else tuple(float(v) for v in z)
    zones = get("canvas.safe_zones") or {}
    best, fr = None, None
    for k, v in zones.items():
        try:
            a, b = (float(x) for x in str(k).split(":")); d = abs(math.log((w / h) / (a / b)))
        except (ValueError, ZeroDivisionError): continue
        if best is None or d < best: best, fr = d, v
    if not fr: fr = (.05, .05, .95, .95)
    return (fr[0] * w, fr[1] * h, fr[2] * w, fr[3] * h)

def safe(S=None):
    """(x0, y0, x1, y1) kept free of platform UI: the canvas safe zone (safe_zone), else the canvas inset by platform.margin"""
    z = safe_zone(S)
    if z: return tuple(float(v) for v in z)
    m = margin(S); return (m, m, W - m, H - m)

# ---------- canvas (style canvas.size; docs/FORMATS.md)
def canvas_of(S=None, pr=None):
    """the canvas (w, h): edit.yaml project.size > style canvas.size > style platform.size (legacy alias) > 1080x1920"""
    get = S.get if S is not None else sget
    sz = ((pr.edit.get("project") or {}).get("size") if pr is not None else None) or get("canvas.size") or get("platform.size") or DESIGN
    w, h = int(sz[0]), int(sz[1])
    if w < 16 or h < 16 or w % 2 or h % 2: raise SystemExit(f"canvas {w}x{h}: width and height must be even and >= 16 (style canvas.size)")
    return w, h

def set_canvas(w, h):
    """set the canvas of this process (G.W, G.H, G.U). Spawned render workers call it again in their initializer.
    Resets the raster scale: layers are drawn at the canvas size (set_raster changes that)."""
    global W, H, U, PW, PH, R
    w, h = int(w), int(h)
    PW, PH, R = w, h, 1.0
    if (w, h) == (W, H): return
    W, H, U = w, h, min(w, h) / 1080.0
    _stage.cache_clear()

def set_raster(pw, ph):
    """draw layers at pw x ph pixels while laying out on the current canvas (W x H): every layout px is R = ph / H layer px.
    templates._canvas_render uses it to rasterise a relative template (laid out at a 1080 short side) at the real canvas."""
    global PW, PH, R
    PW, PH = int(pw), int(ph); R = PH / H if H else 1.0

def px(v):
    """layout px -> layer px (for templates that touch layer pixels directly: blur radii, np.arange over a layer, ...)"""
    return v * R

def is_design(): return (W, H) == DESIGN

def place(im, a, ox, oy, size=None):
    """map an RGBA layer (PIL) drawn in another space onto the canvas: scale a, then offset (ox, oy) in canvas px.
    Only the drawn region is resampled. Returns a canvas-sized PIL RGBA."""
    size = size or (W, H)
    if isinstance(im, np.ndarray):
        im = Image.fromarray(np.clip(im * 255 + .5, 0, 255).astype(np.uint8) if im.dtype != np.uint8 else im, "RGBA")
    out = Image.new("RGBA", size, (0, 0, 0, 0)); bb = im.getbbox()
    if not bb: return out
    x0, y0, x1, y1 = bb
    px0, py0 = int(round(ox + x0 * a)), int(round(oy + y0 * a)); pw, ph = max(1, int(round((x1 - x0) * a))), max(1, int(round((y1 - y0) * a)))
    crop = im.crop(bb)
    if (pw, ph) != crop.size: crop = crop.resize((pw, ph), Image.LANCZOS)
    if px0 >= size[0] or py0 >= size[1] or px0 + pw <= 0 or py0 + ph <= 0: return out
    if px0 < 0 or py0 < 0:
        crop = crop.crop((max(0, -px0), max(0, -py0), pw, ph)); px0, py0 = max(0, px0), max(0, py0)
    out.alpha_composite(crop, (px0, py0)); return out


# ---------- style presets (engine/cves/styles/<preset>.yaml, optionally overridden by PROJECT/Brand/style.yaml)
_COLOR_KEYS = {"accent": "MINT", "accent_dark": "MINT_D", "text": "WHITE", "card": "CARD", "card_border": "CARD_B", "icon_well": "WELL",
               "gold": "GOLD", "star": "STAR", "negative": "NEG", "muted": "MUTED", "surface": "SURFACE", "line": "LINE"}
_FONT_KEYS = {"medium": "m", "semibold": "sb", "bold": "b", "extrabold": "xb", "serif": "serif"}

def load_style(preset=None, override=None):
    """deprecated: use cves.style.load(pr). Kept so old scripts keep working."""
    from . import style as STY
    return STY.load(preset=preset, extra=STY._read(override) if override else None)

def apply_style(d, canvas=None):
    """set the palette, stage, fonts, motion and canvas (`canvas` (w, h), else the style's canvas.size) for this process,
    including names templates imported by value"""
    import sys
    g = globals(); changed = {}; cols = d.get("colors") or {}
    STYLE.clear(); STYLE.update(d)
    set_canvas(*(canvas or canvas_of()))
    for k, name in _COLOR_KEYS.items():
        if cols.get(k): changed[name] = _rgb(cols[k])
    g.update(changed)
    # derived tones (used for secondary text, inner fields and decorative lines) unless the style names them
    if not cols.get("muted"): changed["MUTED"] = mix(g["WHITE"], g["CARD"], .33)
    if not cols.get("surface"): changed["SURFACE"] = mix(g["CARD"], g["WELL"], .5)
    if not cols.get("line"): changed["LINE"] = mix(g["CARD_B"], g["MINT_D"], .45)
    g.update(changed)
    for k in ("background", "glow_bottom", "dot_grid"):
        if k in (d.get("stage") or {}): STAGE[k] = _rgb(d["stage"][k])
    for k, short in _FONT_KEYS.items():
        f = (d.get("font_files") or {}).get(k)
        if f and isinstance(f, str): FONT_FILES[short] = f
    for mod in list(sys.modules.values()):          # templates/render imported colour names by value: update them too
        if getattr(mod, "__name__", "").startswith("cves.") and mod is not sys.modules[__name__]:
            for name, val in changed.items():
                if hasattr(mod, name): setattr(mod, name, val)
    _stage.cache_clear(); font.cache_clear(); _font0.cache_clear(); _icon_img.cache_clear(); _inkbox.cache_clear(); has_glyph.cache_clear()
    return changed
