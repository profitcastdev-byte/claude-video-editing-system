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


def text_behind(t, p, ctx):
    """type behind the presenter. p: text (*stars* = accent), at, out_at (default 0.25 s before the slot ends),
    position above (the head covers the lower `craft.behind.overlap` of the last line) | behind (centred on the eyes) |
    low (behind the shoulders), size (px at a 1080 short side), track (0..1), color, accent, lines (max lines),
    entry rise (the letters rise out from behind the head) | slam (whole on its first frame, oversized, settling)"""
    El, faded = _el(); S = ctx.get("S") or G.STYLE; F = G.fps_of(ctx)
    B = lambda k, d=None: S.get(f"craft.behind.{k}", d) if hasattr(S, "get") else d
    at = G.q(p.get("at", ctx["start"]), F); out_at = p.get("out_at", ctx.get("end", 1e9) - float(B("exit_s", .25)))
    ent = float(B("entry_s", .5)); ex = float(B("exit_s", .25))
    pin = G.enter(t, at, ent, F)
    if pin <= 0: return []
    pout = CR.ease("inCubic", clamp((t - out_at) / max(1e-3, ex)))
    if pout >= 1: return []
    words = _runs(p["text"])
    if str(B("case", "upper")) == "upper": words = [(w.upper(), a) for w, a in words]
    if not words: return []
    face = ctx.get("face"); fa = (ctx.get("face_at") or (lambda tt: None))(at) or face
    matte = bool(ctx.get("matte_ok", True))
    sz = G.safe(); V = ctx.get("seg_view", ctx.get("view"))               # the shot's tightest framing (its zoom, or a snap punch-in in
    if V is not None:                                                      # it): the type stays in the OUTPUT safe zone (plate px =
        sx, tx, ty = float(V[0][0]), float(V[0][2]), float(V[1][2])       # (X - t) / s) on every frame and never re-fits mid-shot
        sz = ((sz[0] - tx) / sx, (sz[1] - ty) / sx, (sz[2] - tx) / sx, (sz[3] - ty) / sx)
    safe_w = sz[2] - sz[0]
    track = float(B("tracking", -4)) * G.U; max_w = safe_w * float(B("max_width", .92))
    size = float(p.get("size", B("size", 300))) * G.U; weight = str(B("weight", "xb"))
    max_lines = int(p.get("lines", B("max_lines", 2)))
    # one line if it fits at >= craft.behind.one_line_min of the size (a lone short word on its own line reads as an orphan),
    # else balanced lines; then shrink to fit, never clip
    f = G.font(weight, int(size)); lines, sp = _layout(words, f, track, max_w, 1)
    while lines[0][1] > max_w and f.size > size * float(B("one_line_min", .42)): f = G.font(weight, int(f.size * .96)); lines, sp = _layout(words, f, track, max_w, 1)
    if lines[0][1] > max_w and max_lines > 1:
        f = G.font(weight, int(size)); lines, sp = _layout(words, f, track, max_w, max_lines)
    while max(w for _, w in lines) > max_w and f.size > 24 * G.U:
        f = G.font(weight, int(f.size * .94)); lines, sp = _layout(words, f, track, max_w, max_lines)
    cap = f.size * .72; lead = f.size * .92
    pos = str(p.get("position", B("position", "above")))
    if not matte and str(B("no_matte", "above")) == "above": pos = "clear"
    if pos == "clear" and (face or fa):                                    # no matte: the type must fit between the safe top and the head
        fc = face or fa; room = fc["top"] - fc["h"] * .06 - sz[1]
        need = cap + (len(lines) - 1) * lead
        if room > 0 and need > room:
            f = G.font(weight, max(8, int(f.size * room / need))); lines, sp = _layout(words, f, track, max_w, max_lines)
            cap = f.size * .72; lead = f.size * .92
    # ---- where: from the smoothed face (plate px), following the head by `track` of its motion
    k_track = float(p.get("track", B("track", .6)))
    def anchor(fc):
        if fc is None: return G.W / 2, sz[1] + (sz[3] - sz[1]) * .3
        if pos == "behind": return fc["cx"], fc["eye_y"] + cap * .5 - (len(lines) - 1) * lead / 2
        if pos == "low": return fc["cx"], fc["chin"] + fc["h"] * .75
        if pos == "clear": return fc["cx"], fc["top"] - fc["h"] * .06
        return fc["cx"], fc["top"] + cap * float(B("overlap", .42))
    ax0, ay0 = anchor(fa); ax1, ay1 = anchor(face) if face else (ax0, ay0)
    cx = ax0 + k_track * (ax1 - ax0); base = ay0 + k_track * (ay1 - ay0)       # baseline of the LAST line
    half = max(w for _, w in lines) / 2
    cx = min(max(cx, sz[0] + half), sz[2] - half)
    base = max(base, sz[1] + cap + (len(lines) - 1) * lead)
    # ---- motion: letters rise up out of the head / shoulders, tracking breathes in; a slow push while held
    pe = CR.ease("outExpo", pin); hold = 1 + .025 * clamp((t - at) / 3)
    if str(p.get("entry", B("entry", "rise"))) == "slam":                  # lands whole on its first frame, oversized, and settles
        rise = -pout * cap * .18; breathe = 0.0; hold *= 1 + .16 * (1 - pe); alpha = 1 - pout
    else:
        rise = (1 - pe) * cap * .42 - pout * cap * .18; breathe = (1 - pe) * 10 * G.U
        alpha = min(1.0, pin * 2.6) * (1 - pout)
    col = G.col(p.get("color"), G.col(B("color", "text"), G.WHITE)); acc = G.col(p.get("accent"), G.col(B("accent", "accent"), G.MINT))
    fs = G.font(weight, max(8, int(f.size * hold)))
    def draw(d):
        n = len(lines)
        for li, (ws, w) in enumerate(lines):
            y = base - (n - 1 - li) * lead * hold + rise
            ww = w * hold + (len(ws) - 1) * breathe; x = cx - ww / 2
            for wd, a, wpx in ws:
                G.draw_text(d, (x, y), wd, fs, acc if a else col, tracking=track + breathe / max(1, len(wd)), anchor="ls")
                x += wpx * hold + sp * hold + breathe
    im = faded(draw, alpha)
    plain = " ".join(w for w, _ in words); out = []
    # legibility (GFX-15): a soft bed under the type, sized by the weaker of its colours against the assumed video tone;
    # it sits on the plate too, so the subject occludes it with the type
    weak = None if not (B("bed", False) or (not matte and pos != "clear")) else min((col, acc) if any(a for _, a in words) else (col,), key=lambda c: G.contrast(c, G._rgb(G.sget("legibility.video_bg") or (180, 180, 180))))
    bed = G.legible_bed(im, weak, f.size) if weak is not None else None
    if bed is not None: out.append(El(bed, "behind.text.bed", "roto"))
    out.append(El(im, "behind.text", "roto", text=plain, t_key=at, font=weight))
    return out


def text_behind_cues(p, ctx):
    S = ctx.get("S") or G.STYLE; snd = S.get("craft.behind.sfx", "lowhit") if hasattr(S, "get") else "lowhit"
    if not snd: return []
    return G.cues_out([(p.get("at", ctx["start"]), snd, -11, {"reveal": True})], ctx)


T = {"text_behind": (text_behind, text_behind_cues)}
