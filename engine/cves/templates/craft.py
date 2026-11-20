"""Craft templates (docs/TEMPLATES.md "Craft"; docs/MOTION.md "Craft").

  text_behind   big type composited BETWEEN the background plate and the subject matte (use it in `roto:`), placed from
                the presenter's smoothed face landmarks so the head occludes the letters. It follows the head by
                `craft.behind.track` of its motion (0 = locked at its entry position, 1 = glued to the head). With no
                subject matte it degrades gracefully: the type lifts clear above the head (or sits in front with a
                legibility bed, `craft.behind.no_matte: front`), so it never prints across the face.

Everything comes from the style (`craft.behind.*`, colours, fonts) and the template counts against the restraint budget
(`creative.craft_per_30s`, `cves critique`)."""
import re
from .. import gfx as G
from .. import craft as CR
from ..gfx import clamp

KIND = "roto"
NATIVE = True               # plate / canvas px: positions come from the face track, sizes scale by G.U
PARAMS = {"text_behind": {"text": "str!", "at": "time", "out_at": "time", "position": "str", "size": "number", "track": "number",
                          "color": "color", "accent": "color", "lines": "int", "entry": "str"}}


def _el():
    from . import El, faded
    return El, faded


def _runs(text):
    """'*accent* words' -> [(word, accent)] (a star toggles the accent; punctuation may touch the stars)"""
    out, acc = [], False
    for w in str(text or "").split():
        word, a = "", False
        for part in re.split(r"(\*)", w):
            if part == "*": acc = not acc
            elif part: word += part; a = a or acc
        if word: out.append((word, a))
    return out


def _layout(words, f, track, max_w, max_lines):
    """greedy lines of words for font f (px widths with tracking)"""
    sp = G.text_w(" ", f, track) + track
    lines, cur, cw = [], [], 0.0
    for wd, a in words:
        ww = G.text_w(wd, f, track)
        if cur and cw + sp + ww > max_w and len(lines) < max_lines - 1:
            lines.append((cur, cw)); cur, cw = [], 0.0
        cw = ww if not cur else cw + sp + ww; cur.append((wd, a, ww))
    if cur: lines.append((cur, cw))
    return lines, sp


def _B(S):
    return lambda k, d=None: S.get(f"craft.behind.{k}", d) if hasattr(S, "get") else d


def _words(p, B):
    words = _runs(p.get("text"))
    if str(B("case", "upper")) == "upper": words = [(w.upper(), a) for w, a in words]
    return words


def _fit(words, size, max_w, max_lines, B):
    """(font, lines, space) for the words at `size` canvas px: one line if it fits at >= craft.behind.one_line_min of the
    size (a lone short word on its own line reads as an orphan), else balanced lines; then shrink to fit, never clip"""
    weight = str(B("weight", "xb")); track = float(B("tracking", -4)) * G.U
    f = G.font(weight, int(size)); lines, sp = _layout(words, f, track, max_w, 1)
    while lines[0][1] > max_w and f.size > size * float(B("one_line_min", .42)): f = G.font(weight, int(f.size * .96)); lines, sp = _layout(words, f, track, max_w, 1)
    if lines[0][1] > max_w and max_lines > 1:
        f = G.font(weight, int(size)); lines, sp = _layout(words, f, track, max_w, max_lines)
    while max(w for _, w in lines) > max_w and f.size > 24 * G.U:
        f = G.font(weight, int(f.size * .94)); lines, sp = _layout(words, f, track, max_w, max_lines)
    return f, lines, sp


def _max_w(B, scale):
    z = G.safe(); return (z[2] - z[0]) / max(1e-6, scale) * float(B("max_width", .92))


def fitted_size(p, S, scale=1.0):
    """the canvas px size one text_behind instance fits at in a shot shown at zoom `scale` (craft.behind_size harmonises
    every instance of a video to the smallest of these, GFX-20)"""
    B = _B(S); words = _words(p, B)
    if not words: return 1e9
    size = float(p.get("size", B("size", 300))) * G.U
    return float(_fit(words, size, _max_w(B, scale), int(p.get("lines", B("max_lines", 2))), B)[0].size)


# ---- colour: auto picks the light or dark text token from the plate behind the type (GFX-15)
_AUTO = {}

def _L2rgb(L):
    L = min(1.0, max(0.0, float(L))); c = 12.92 * L if L <= .0031308 else 1.055 * L ** (1 / 2.4) - .055
    v = int(round(c * 255)); return (v, v, v)

def _worst(c, lo, hi):
    """worst WCAG ratio of colour c over backgrounds with relative luminance in [lo, hi]"""
    L = G.lum(c)
    if lo <= L <= hi: return 1.0
    b = hi if L > hi else lo
    return (max(L, b) + .05) / (min(L, b) + .05)

def _variant(c, dark, need, lo, hi):
    """the accent's darker (on a light wall) or lighter (on a dark wall) variant that reads: the accent_dark slot first,
    then the accent mixed toward black / white in steps"""
    cands = ([G.MINT_D] if dark and c == G.MINT else []) + [G.mix(c, (0, 0, 0) if dark else (255, 255, 255), k) for k in [j / 20 for j in range(3, 19)]]
    for v in cands:
        if _worst(v, lo, hi) >= need: return v
    return cands[-1]

def _auto_colour(key, plate_lum, samples, B, size_px, has_acc, acc0):
    """(text colour, accent colour, worst-case background RGB or None) for one instance, decided once from the plate
    luminance behind its box over the hold (person masked out). samples = [(plate frame, (x0, y0, x1, y1) plate px)]"""
    if key in _AUTO: return _AUTO[key]
    light, dark = G.col(B("light", "text"), G.WHITE), G.col(B("dark", "card"), G.CARD)
    vals = []
    try: frames = plate_lum([k for k, _ in samples])
    except (OSError, ValueError, StopIteration) as e:
        print(f"cves: text_behind color auto: plate not readable ({e}); using {B('light', 'text')}"); frames = []
    import numpy as np
    for (k, Lm, A), (_, bx) in zip(frames, samples):
        h, w = Lm.shape; x0, y0, x1, y1 = [int(round(v)) for v in bx]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        if x1 - x0 < 4 or y1 - y0 < 4: continue
        m = A[y0:y1, x0:x1] < .5                                            # the wall the type is read against, not the person
        if m.sum() > 50: vals.append(Lm[y0:y1, x0:x1][m][::3])
    if not vals:
        _AUTO[key] = (light, acc0, None); return _AUTO[key]
    v = np.concatenate(vals); lo, hi = float(np.percentile(v, 10)), float(np.percentile(v, 90))
    need = G.need_contrast(size_px) * float(G.sget("legibility.margin", 1.15))
    wl, wd = _worst(light, lo, hi), _worst(dark, lo, hi)
    col, is_dark = (light, False) if wl >= need or wl >= wd else (dark, True)
    acc = acc0
    if has_acc and _worst(acc0, lo, hi) < need: acc = _variant(acc0, is_dark, need, lo, hi)
    weakest = min(_worst(col, lo, hi), _worst(acc, lo, hi) if has_acc else 99)
    bg = _L2rgb(lo if is_dark else hi) if weakest < need and B("auto_bed", True) else None
    _AUTO[key] = (col, acc, bg)
    if len(_AUTO) > 256: _AUTO.pop(next(iter(_AUTO)))
    return _AUTO[key]


def _scaled(im, hold, cx, base):
    """im scaled by `hold` about (cx, base), premultiplied (no dark fringes), bilinear. Only the type's box is premultiplied
    and only the box it lands in is un-premultiplied: elsewhere the layer is clear (premultiplied zero) before and after
    the warp, exactly as when the whole frame goes through it."""
    import math, cv2, numpy as np
    from PIL import Image
    M = np.float32([[hold, 0, cx * (1 - hold)], [0, hold, base * (1 - hold)]])
    bb = im.getbbox()
    if bb is None: return Image.new("RGBA", im.size, (0, 0, 0, 0))
    W, H = im.size; x0, y0, x1, y1 = bb
    a4 = np.zeros((H, W, 4), np.float32)
    c = np.asarray(im.crop(bb)).astype(np.float32); c[..., :3] *= c[..., 3:4] / 255; a4[y0:y1, x0:x1] = c
    w4 = cv2.warpAffine(a4, M, im.size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    m00, m02, m11, m12 = float(M[0, 0]), float(M[0, 2]), float(M[1, 1]), float(M[1, 2])
    u0, u1 = max(0, math.floor(m00 * (x0 - 1) + m02) - 3), min(W, math.ceil(m00 * (x1 + 1) + m02) + 3)   # where the box lands
    v0, v1 = max(0, math.floor(m11 * (y0 - 1) + m12) - 3), min(H, math.ceil(m11 * (y1 + 1) + m12) + 3)   # (bilinear reach + margin)
    out = np.zeros((H, W, 4), np.uint8)
    if u1 > u0 and v1 > v0:
        r = w4[v0:v1, u0:u1]; r[..., :3] /= np.maximum(r[..., 3:4], 1e-3) / 255
        out[v0:v1, u0:u1] = np.clip(r + .5, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def text_behind(t, p, ctx):
    """type behind the presenter. p: text (*stars* = accent), at, out_at (default 0.25 s before the slot ends),
    position above (the head covers the lower `craft.behind.overlap` of the last line) | behind (centred on the eyes) |
    low (behind the shoulders), size (px at a 1080 short side; default: the video's harmonised size), track (0..1),
    color (auto = light or dark token from the wall behind it), accent, lines (max lines),
    entry rise (the letters rise out from behind the head) | slam (whole on its first frame, oversized, settling)"""
    El, faded = _el(); S = ctx.get("S") or G.STYLE; F = G.fps_of(ctx); B = _B(S)
    at = G.q(p.get("at", ctx["start"]), F); out_at = p.get("out_at", ctx.get("end", 1e9) - float(B("exit_s", .25)))
    ent = float(B("entry_s", .5)); ex = float(B("exit_s", .25))
    pin = G.enter(t, at, ent, F)
    if pin <= 0: return []
    pout = CR.ease("inCubic", clamp((t - out_at) / max(1e-3, ex)))
    if pout >= 1: return []
    words = _words(p, B)
    if not words: return []
    face = ctx.get("face"); face_at = ctx.get("face_at"); fa = (face_at or (lambda tt: None))(at) or face
    matte = bool(ctx.get("matte_ok", True))
    sz = G.safe(); V = ctx.get("seg_view", ctx.get("view"))               # the shot's framing (its zoom, or a snap punch-in in it):
    if V is not None:                                                      # the type stays in the OUTPUT safe zone (plate px = (X - t) / s)
        sx, tx, ty = float(V[0][0]), float(V[0][2]), float(V[1][2])
        sz = ((sz[0] - tx) / sx, (sz[1] - ty) / sx, (sz[2] - tx) / sx, (sz[3] - ty) / sx)
    scale = float(ctx.get("seg_scale") or (float(V[0][0]) if V is not None else 1.0))   # fitted once to the shot's tightest view
    max_w = _max_w(B, scale); track = float(B("tracking", -4)) * G.U; weight = str(B("weight", "xb"))
    max_lines = int(p.get("lines", B("max_lines", 2)))
    hs = ctx.get("behind_size")
    if "size" not in p and hs:
        # the harmonised size came from fitted_size(): take the same layout decision it took (from the style size), then
        # set the shared size. Fitting again FROM the shared size is path-dependent: a two-word line that wrapped there
        # would stay on one line here and shrink below it (GFX-20 on the first real job: 169 vs 104 px)
        f, lines, sp = _fit(words, float(B("size", 300)) * G.U, max_w, max_lines, B)
        if f.size > float(hs): f = G.font(weight, int(hs)); lines, sp = _layout(words, f, track, max_w, len(lines))
    else:
        size = float(p["size"]) * G.U if "size" in p else float(B("size", 300)) * G.U
        f, lines, sp = _fit(words, size, max_w, max_lines, B)
    cap = f.size * .72; lead = f.size * .92
    pos = str(p.get("position", B("position", "above")))
    if not matte and str(B("no_matte", "above")) == "above": pos = "clear"
    if pos == "clear" and fa:                                              # no matte: the type must fit between the safe top and the head
        room = fa["top"] - fa["h"] * .06 - sz[1]; need = cap + (len(lines) - 1) * lead
        if room > 0 and need > room:
            f = G.font(weight, max(8, int(f.size * room / need))); lines, sp = _layout(words, f, track, max_w, max_lines)
            cap = f.size * .72; lead = f.size * .92
    # ---- where: from the smoothed face (plate px), following the head by `track` of its motion
    k_track = float(p.get("track", B("track", .4)))
    half = max(w for _, w in lines) / 2
    def anchor(fc):
        if fc is None: return G.W / 2, sz[1] + (sz[3] - sz[1]) * .3
        if pos == "behind": return fc["cx"], fc["eye_y"] + cap * .5 - (len(lines) - 1) * lead / 2
        if pos == "low": return fc["cx"], fc["chin"] + fc["h"] * .75
        if pos == "clear": return fc["cx"], fc["top"] - fc["h"] * .06
        return fc["cx"], fc["top"] + cap * float(B("overlap", .42))
    ax0, ay0 = anchor(fa)
    def place(tt, fc):
        kt = k_track * CR.ease("inOutSine", clamp((tt - at) / max(1e-3, ent)))   # follow the head only once the entry has landed (MOT-01)
        ax1, ay1 = anchor(fc) if fc else (ax0, ay0)
        x = ax0 + kt * (ax1 - ax0); y = ay0 + kt * (ay1 - ay0)                     # baseline of the LAST line
        return min(max(x, sz[0] + half), sz[2] - half), max(y, sz[1] + cap + (len(lines) - 1) * lead)
    if face_at is not None:
        # the clamp to the safe zone has corners: smooth the CLAMPED path too (a Gaussian in seconds; a weighted mean of
        # in-zone points stays in the zone), or the type stops dead on the safe edge with a 5 px/f^2 kink (MOT-03)
        import math
        sg = CR.smooth_s(S, F); r = int(math.ceil(3 * sg)) if sg > 0 else 0
        wsum = xs = ys = 0.0
        for j in range(-r, r + 1):
            w = math.exp(-.5 * (j / sg) ** 2) if sg > 0 else 1.0; tt = t + j / F
            x, y = place(tt, face_at(tt)); wsum += w; xs += w * x; ys += w * y
        cx, base = xs / wsum, ys / wsum
    else:
        cx, base = place(t, face)
    # ---- motion: letters rise up out of the head / shoulders, tracking breathes in; a slow push while held
    pe = CR.ease("outExpo", pin); hold = 1 + .025 * clamp((t - at) / 3)
    # the exit is a fade with a slight lift: a bigger drift over a 0.25 s fade rounds into uneven steps at 60 fps (MOT-01)
    if str(p.get("entry", B("entry", "rise"))) == "slam":                  # lands whole on its first frame, oversized, and settles
        rise = -pout * cap * .04; breathe = 0.0; hold *= 1 + .16 * (1 - pe); alpha = 1 - pout
    else:
        rise = (1 - pe) * cap * .42 - pout * cap * .04; breathe = (1 - pe) * 10 * G.U
        alpha = min(1.0, pin * 2.6) * (1 - pout)
    # ---- colour: a fixed colour, or auto (the light or dark token, whichever reads on the wall behind the type)
    has_acc = any(a for _, a in words)
    acc = G.col(p.get("accent"), G.col(B("accent", "accent"), G.MINT)); bed_bg = None
    cspec = p.get("color", B("color", "auto"))
    if str(cspec) == "auto":
        col = G.col(B("light", "text"), G.WHITE)
        pl = ctx.get("plate_lum"); fo = ctx.get("frame_of")
        if pl is not None and fo is not None:
            h0 = out_at - at - ent; n = 6
            ts = [at + ent + h0 * (j + .5) / n for j in range(n)] if h0 > .1 else [at + ent]
            smp = []
            for tt in ts:
                x, y = place(tt, (face_at or (lambda _t: face))(tt))
                smp.append((fo(tt), (x - half, y - cap - (len(lines) - 1) * lead - f.size * .08, x + half, y + f.size * .06)))
            key = (p.get("text"), round(at, 4), round(ctx.get("start", 0), 4), G.W, G.H, int(f.size), str(S.get("_sources", "")) if hasattr(S, "get") else "")
            col, acc, bed_bg = _auto_colour(key, pl, smp, B, f.size, has_acc, acc)
    else:
        col = G.col(cspec, G.WHITE)
    def draw(d):
        n = len(lines)
        for li, (ws, w) in enumerate(lines):
            y = base - (n - 1 - li) * lead + rise
            ww = w + (len(ws) - 1) * breathe; x = cx - ww / 2
            for wd, a, wpx in ws:
                G.draw_text(d, (x, y), wd, f, acc if a else col, tracking=track + breathe / max(1, len(wd)), anchor="ls")
                x += wpx + sp + breathe
    im = faded(draw, alpha)
    if abs(hold - 1) > 1e-4:                    # the push / slam scale as a sub-pixel transform about the baseline centre
        im = _scaled(im, hold, cx, base)
    plain = " ".join(w for w, _ in words); out = []
    # legibility (GFX-15): a soft bed under the type, sized by the weaker of its colours against the background (measured
    # by color: auto, else the assumed video tone); it sits on the plate too, so the subject occludes it with the type
    forced = B("bed", False) or (not matte and pos != "clear")
    if bed_bg is not None or forced:
        bg = bed_bg or G._rgb(G.sget("legibility.video_bg") or (180, 180, 180))
        weak = min((col, acc) if has_acc else (col,), key=lambda c: G.contrast(c, bg))
        bed = G.legible_bed(im, weak, f.size, bg=bg)
        if bed is not None: out.append(El(bed, "behind.text.bed", "roto"))
    out.append(El(im, "behind.text", "roto", text=plain, t_key=at, font=weight, size=round(f.size / G.U, 1)))
    return out


def text_behind_cues(p, ctx):
    S = ctx.get("S") or G.STYLE; snd = S.get("craft.behind.sfx", "lowhit") if hasattr(S, "get") else "lowhit"
    if not snd: return []
    return G.cues_out([(p.get("at", ctx["start"]), snd, -11, {"reveal": True})], ctx)


T = {"text_behind": (text_behind, text_behind_cues)}
