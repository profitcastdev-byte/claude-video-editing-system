"""Media templates: real pictures instead of drawn graphics (docs/MEDIA.md).
  image          still with Ken Burns (zoom / pan), full bleed or a rounded card, optional label + caption
  video_broll    a clip with in/out, speed, loop | hold, fit cover | contain; optional own audio (cue -> mix)
  screen_rec     a clip inside a phone / browser frame, zoom-to-region keyframes, cursor highlight + click pulses
  pip            the presenter (A-roll) in a corner bubble or as a cut-out over B-roll / an image / another template
  split          two panes (top/bottom or left/right), each an asset or the A-roll
  overlay_render a pre-rendered RGBA clip (ProRes 4444 / PNG sequence / PNG) over A-roll or a cutaway, blend + opacity
Every template takes `asset: <id>` from edit.yaml `assets:` (registered with `cves assets add`), logs it on El.asset, and
reads colours, radii and motion from the style (`media.*`, `motion.*`, `colors.*`). Clips are decoded with PyAV and cached
per process; frame i of the cut maps to source time (i - round(at*fps)) / fps * speed + in, at the timeline fps."""
import os, sys, math, functools, collections
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageOps
from .. import gfx as G
from ..gfx import prog, ease_out, ease_in, ease_io, back, clamp
from . import El

KIND = "cutaway"                                  # full-screen pictures; render passes the A-roll only to NEEDS_AROLL templates
KINDS = {"pip": "media", "split": "media", "overlay_render": "overlay"}
NEEDS_AROLL = {"pip", "split"}                    # render.refresh_needs_aroll(): these get ctx["aroll"]
RASTER = False                                    # pictures are composed at the layout size and scaled (see templates._canvas_render)
NATIVE = {"broll_shot"}                          # drawn on the canvas itself (templates._canvas_render); px scale by G.U
STILL_EXT = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif")


# ------------------------------------------------------------------ context (works with the current render ctx and the extended one)
def _tl(ctx):
    return getattr(ctx.get("resolve"), "__self__", None)          # Timeline, when ctx["resolve"] is the bound Timeline.resolve

def _proj(ctx):
    if ctx.get("project") is not None: return ctx["project"]
    return getattr(_tl(ctx), "pr", None)

@functools.lru_cache(8)
def _style_for(root):
    from .. import style as STY
    from ..project import Project
    return STY.load(Project(root))

def _S(ctx):
    for k in ("S", "style"):
        if ctx.get(k) is not None: return ctx[k]
    tl = _tl(ctx)
    if tl is not None: return tl.S
    pr = _proj(ctx)
    if pr is not None: return _style_for(pr.root)
    from .. import style as STY
    return STY.load()

def _fps(ctx):
    if ctx.get("fps"): return float(ctx["fps"])
    tl = _tl(ctx)
    if tl is not None: return float(tl.FPS)
    pr = _proj(ctx); edl = pr.json("edl.json") if pr is not None else None
    if edl: return float(edl["fps"])
    raise SystemExit("media templates need the timeline fps: pass ctx['fps'] (render) or run `cves select` (Edit/edl.json)")

def _asset(ref, ctx):
    """asset id (or path) -> (abs path, name logged on El.asset)"""
    if not ref: raise SystemExit("media template: `asset:` is required (an id from edit.yaml assets)")
    pr = _proj(ctx)
    if pr is not None:
        from .. import assets as AS
        p = AS.resolve(pr, ref)
        if p: return p, os.path.relpath(p, pr.root).replace(os.sep, "/")
    r = ctx.get("resolve"); p = r(ref) if r else ref
    if not os.path.exists(p): raise SystemExit(f"media: asset '{ref}' not found: declare it under edit.yaml assets and `cves assets add` it")
    return p, ref

def _is_still(path): return not os.path.isdir(path) and path.lower().endswith(STILL_EXT)

def _safe(S): return G.safe(S)

def design_box(box):
    """a style box given in 1080x1920 design px (media.card_box, media.device_box) on the current canvas: as is at
    1080x1920, scaled on another 9:16 canvas, else fitted (aspect kept) and centred in the canvas safe zone"""
    x0, y0, x1, y1 = [float(v) for v in box]
    if G.is_design(): return (x0, y0, x1, y1)
    if abs(G.W / G.H - 9 / 16) < .01: k = G.W / 1080; return (x0 * k, y0 * k, x1 * k, y1 * k)
    z = G.safe(); bw, bh = x1 - x0, y1 - y0; k = min((z[2] - z[0]) / bw, (z[3] - z[1]) / bh, G.U)
    cx, cy = (z[0] + z[2]) / 2, (z[1] + z[3]) / 2
    return (cx - bw * k / 2, cy - bh * k / 2, cx + bw * k / 2, cy + bh * k / 2)


# ------------------------------------------------------------------ sources (cached per process)
@functools.lru_cache(12)
def _still(path):
    with Image.open(path) as im: return np.ascontiguousarray(np.asarray(ImageOps.exif_transpose(im).convert("RGBA")))

class Clip:
    """random-access RGBA frames from a video file or an image-sequence folder. Sequential reads decode forward;
    a jump back or > 2 s ahead seeks. Recent frames are kept in a small LRU."""
    def __init__(self, path, fps=None):
        self.path = path; self.cache = collections.OrderedDict()
        if os.path.isdir(path):
            self.seq = sorted(os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith((".png", ".tif", ".tiff", ".webp")))
            if not self.seq: raise SystemExit(f"{path}: image sequence folder has no frames")
            self.fps = float(fps or 0) or None; self.n = len(self.seq); self.rot = 0
            return
        import av
        self.seq = None; self.c = av.open(path); self.st = self.c.streams.video[0]; self.st.thread_type = "AUTO"
        self.tb = float(self.st.time_base); self.fps = float(fps or self.st.average_rate or self.st.guessed_rate or 25)
        self.t0 = float(self.st.start_time * self.st.time_base) if self.st.start_time is not None else 0.0
        dur = float(self.st.duration * self.st.time_base) if self.st.duration else (self.c.duration or 0) / 1e6
        self.n = max(1, int(self.st.frames or round(dur * self.fps)))
        self.it = None; self.pos = -1; self.last = None; self.rot = None

    @property
    def duration(self): return self.n / (self.fps or 1)

    def _decode_to(self, idx):
        if self.it is None or idx < self.pos or idx > self.pos + 2 * self.fps:
            self.c.seek(max(0, int((idx / self.fps + self.t0) / self.tb)), stream=self.st, backward=True, any_frame=False)
            self.it = self.c.decode(self.st); self.pos = -1
        for fr in self.it:
            fi = int(round((float(fr.pts * self.tb) - self.t0) * self.fps)) if fr.pts is not None else self.pos + 1
            self.pos = fi
            if self.rot is None: self.rot = int(round(float(getattr(fr, "rotation", 0) or 0) / 90)) % 4
            self.last = fr
            if fi >= idx: break
        if self.last is None: raise SystemExit(f"{self.path}: no decodable video frames")
        a = self.last.to_ndarray(format="rgba")
        return np.ascontiguousarray(np.rot90(a, self.rot)) if self.rot else a

    def frame(self, idx):
        idx = int(min(max(idx, 0), self.n - 1))
        if idx in self.cache: self.cache.move_to_end(idx); return self.cache[idx]
        if self.seq:
            with Image.open(self.seq[idx]) as im: a = np.ascontiguousarray(np.asarray(im.convert("RGBA")))
        else: a = self._decode_to(idx)
        self.cache[idx] = a
        while len(self.cache) > 6: self.cache.popitem(last=False)
        return a

def sdr(path, ctx=None):
    """the path to decode: an HDR (PQ / HLG) clip is tonemapped to SDR BT.709 once, through the A-roll ingest chain
    (ingest.sdr_source; cached in the project's Edit/conform), so B-roll matches the graded A-roll"""
    from .. import ingest as ING
    pr = _proj(ctx or {})
    return ING.sdr_source(path, _S(ctx or {}), pr.e("conform") if pr is not None and hasattr(pr, "e") else None)

_CLIPS = {}
def clip(path, fps=None):
    k = (path, fps)
    if k not in _CLIPS: _CLIPS[k] = Clip(path, fps)
    return _CLIPS[k]

def _src_time(local, p, c, default_end="hold"):
    """cut-local seconds -> source seconds (None = nothing to show). p: in, out, speed, after loop | hold | hide"""
    sin = float(p.get("in", 0)); sout = float(p.get("out") or c.duration); sp = float(p.get("speed", 1.0))
    span = max(1e-3, sout - sin); x = local * sp
    if x >= span:
        mode = p.get("after", default_end)
        if mode == "loop": x = x % span
        elif mode == "hide": return None
        else: x = span - .5 / c.fps
    return sin + max(0.0, x)

def media_frame(t, spec, ctx, at, default_end="hold"):
    """(rgba uint8, asset name, has_alpha) for a media spec {asset, in, out, speed, after, fps} at cut time t (None if hidden)"""
    path, name = _asset(spec.get("asset"), ctx)
    if _is_still(path):
        a = _still(path); return a, name, bool((a[..., 3] < 255).any())
    c = clip(sdr(path, ctx), spec.get("fps") or (None if not os.path.isdir(path) else _fps(ctx)))
    fps = _fps(ctx); local = (round(t * fps) - round(at * fps)) / fps
    if local < 0: local = 0.0
    st = _src_time(local, spec, c, default_end)
    if st is None: return None, name, False
    a = c.frame(int(math.floor(st * c.fps + 1e-6)))
    return a, name, bool(c.seq) or a[0, 0, 3] < 255 or bool((a[::16, ::16, 3] < 255).any())


# ------------------------------------------------------------------ placement
@functools.lru_cache(64)
def _rmask(bw, bh, r, shape="rounded"):
    k = 2; im = Image.new("L", (bw * k, bh * k), 0); d = ImageDraw.Draw(im)
    if shape == "circle": d.ellipse((0, 0, bw * k - 1, bh * k - 1), fill=255)
    else: d.rounded_rectangle((0, 0, bw * k - 1, bh * k - 1), max(0, r) * k, fill=255)
    return np.asarray(im.resize((bw, bh), Image.LANCZOS), np.uint16)

def view(src, bw, bh, scale, center, alpha=False, clamp_view=True):
    """crop/scale src (uint8 RGBA) so that source point `center` lands at the box centre with `scale` (src px -> canvas px).
    Returns uint8 RGBA (bh, bw, 4). clamp_view keeps the view inside the source when it can."""
    sh, sw = src.shape[:2]; u, v = center; s = float(scale)
    if clamp_view:
        hw, hh = bw / 2 / s, bh / 2 / s
        u = min(max(u, hw), sw - hw) if sw >= 2 * hw else sw / 2
        v = min(max(v, hh), sh - hh) if sh >= 2 * hh else sh / 2
    img = src
    if s < .66:                                   # big downscale: area-average first (warpAffine alone aliases)
        f = min(1.0, s * 1.5); img = cv2.resize(src, (max(1, round(sw * f)), max(1, round(sh * f))), interpolation=cv2.INTER_AREA)
        fx, fy = img.shape[1] / sw, img.shape[0] / sh; s, u, v = s / fx, u * fx, v * fy
    if alpha:                                     # premultiply so transparent edges do not fringe dark (uint8, cv2: fast)
        a3 = cv2.merge([img[..., 3]] * 3); img = cv2.merge([*cv2.split(cv2.multiply(np.ascontiguousarray(img[..., :3]), a3, scale=1 / 255)), img[..., 3]])
    M = np.float32([[s, 0, bw / 2 - s * u], [0, s, bh / 2 - s * v]])
    out = cv2.warpAffine(img, M, (int(bw), int(bh)), flags=cv2.INTER_CUBIC if s > 1.05 else cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if alpha:
        a3 = cv2.merge([out[..., 3]] * 3)
        out = cv2.merge([*cv2.split(cv2.divide(np.ascontiguousarray(out[..., :3]), a3, scale=255)), out[..., 3]])
    return out

def fit_scale(sw, sh, bw, bh, fit): return max(bw / sw, bh / sh) if fit == "cover" else min(bw / sw, bh / sh)

def canvas_layer(box_img, x0, y0, mask=None, opacity=1.0):
    """paste a box image (uint8 RGBA) into a transparent W x H layer at (x0, y0), with an optional mask and opacity"""
    a = box_img
    if mask is not None or opacity < 1:
        a = a.copy(); al = a[..., 3].astype(np.uint16)
        if mask is not None: al = al * mask // 255
        if opacity < 1: al = (al * max(0.0, opacity)).astype(np.uint16)
        a[..., 3] = al.astype(np.uint8)
    out = np.zeros((G.H, G.W, 4), np.uint8); bh, bw = a.shape[:2]; x0, y0 = int(round(x0)), int(round(y0))
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(G.W, x0 + bw), min(G.H, y0 + bh)
    if X1 > X0 and Y1 > Y0: out[Y0:Y1, X0:X1] = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    return Image.fromarray(out, "RGBA")

@functools.lru_cache(32)
def _card_deco(box, r, border, shadow, col_b, kind="card", _wh=None):
    """drop shadow + outline for a card at box (cached: static per box)"""
    x0, y0, x1, y1 = box
    base = G.layer(lambda d: G.rrect(d, (x0, y0, x1, y1), r, fill=(0, 0, 0, 255)))
    out = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    if shadow > 0:
        out = G.shadow(base, r=22, alpha=shadow, dy=14); a = np.asarray(out).copy()
        a[..., 3] = (a[..., 3].astype(np.float32) * (1 - np.asarray(base)[..., 3] / 255)).astype(np.uint8)   # keep only the outside
        out = Image.fromarray(a, "RGBA")
    if border > 0:
        ol = G.layer(lambda d: G.rrect(d, (x0, y0, x1, y1), r, outline=col_b, width=border)); out.alpha_composite(ol)
    return out

def _entry(t, at, out_at, S, kind):
    """(dx, dy, scale, opacity) for an entry / exit animation timed by motion.*"""
    es = S.get("motion.entry_s", .28); slide = S.get("motion.slide_px", 50); ov = S.get("motion.overshoot", 1.6)
    if kind in (None, "none", False): pi = 1.0
    else: pi = prog(t, at, es)
    po = 1 - prog(t, out_at - es, es) if out_at is not None else 1.0
    if pi <= 0 or po <= 0: return 0, 0, 1, 0
    if kind == "rise": return 0, slide * (1 - ease_out(pi)), 1, ease_out(pi) * po
    if kind == "scale": return 0, 0, .86 + .14 * back(pi, ov), min(1, pi * 2) * po
    if kind == "fade": return 0, 0, 1, ease_out(pi) * po
    return 0, 0, 1, po

def _scaled_box(box, sc, dx=0, dy=0):
    x0, y0, x1, y1 = box; cx, cy = (x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy; hw, hh = (x1 - x0) / 2 * sc, (y1 - y0) / 2 * sc
    return (cx - hw, cy - hh, cx + hw, cy + hh)

def _lerp(a, b, e): return a + (b - a) * e

def _kb(t, p, ctx, S, default_zoom):
    """Ken Burns (zoom, pan_x, pan_y) at t. zoom: [from, to] or a number; pan: [[x0, y0], [x1, y1]] or [x, y] (end; -1..1)"""
    z = p.get("zoom", default_zoom); z = [z, z] if isinstance(z, (int, float)) else list(z)
    pn = p.get("pan", [0, 0]); pn = [[0, 0], pn] if pn and not isinstance(pn[0], (list, tuple)) else pn
    a = p.get("at", ctx["start"]); d = max(.1, float(p.get("kb_s", ctx["end"] - a)))
    e = prog(t, a, d); e = ease_io(e) if p.get("ease", "linear") == "io" else e
    return _lerp(z[0], z[1], e), _lerp(pn[0][0], pn[1][0], e), _lerp(pn[0][1], pn[1][1], e)

def _text_els(t, p, box, S, name, alpha=1.0):
    """label above the box, caption pill over its lower edge (both timed on their spoken words)"""
    out = []; x0, y0, x1, y1 = box; cx = (x0 + x1) / 2; sz = _safe(S)
    if p.get("label"):
        la = p.get("label_at", p.get("at")); pa = ease_out(prog(t, la, S.get("motion.entry_s", .28))) if la is not None else 1
        ly = max(sz[1] + 30, y0 - 34)
        if pa * alpha > 0:
            from . import faded
            if p.get("frame", S.get("media.frame", "bleed")) == "bleed" or p.get("label_pill"):    # over a picture: a pill keeps it readable
                ly = max(sz[1] + 40, y0 + 90) if y0 < sz[1] + 40 else ly + 20; f = G.font("sb", p.get("label_size", 26))
                def lab(d):
                    tw = G.text_w(p["label"], f, 6); bw_, bh_ = tw + 48, f.size + 26
                    G.rrect(d, (cx - bw_ / 2, ly - bh_ / 2, cx + bw_ / 2, ly + bh_ / 2), bh_ / 2, fill=G.CARD + (225,))
                    G.draw_text(d, (cx, ly + f.size * .36), p["label"], f, G.WHITE, tracking=6, anchor="ms")
                out.append(El(faded(lab, pa * alpha), f"{name}.label", "cutaway", text=p["label"], t_key=la))
            else:
                out.append(El(faded(lambda d: G.label(d, cx, ly, p["label"], p.get("label_size", 26)), pa * alpha), f"{name}.label", "cutaway", text=p["label"], t_key=la))
    if p.get("caption"):
        ca = p.get("caption_at", p.get("at")); pc = prog(t, ca, S.get("motion.entry_s", .28)) if ca is not None else 1
        if pc > 0 and alpha > 0:
            cy = p.get("caption_y") or (min(y1, sz[3] - 50) - 6); f = G.font("b", p.get("caption_size", 34)); sc = back(pc, S.get("motion.overshoot", 1.6))
            def cap(d):
                tw = G.text_w(p["caption"], f, 2); bw, bh = (tw + 60) * sc, (f.size + 32) * sc
                G.rrect(d, (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), bh / 2, fill=G.MINT)
                if pc > .4: G.draw_text(d, (cx, cy + f.size * .36), p["caption"], f, G.CARD, tracking=2, anchor="ms")
            from . import faded
            out.append(El(faded(cap, alpha), f"{name}.caption", "cutaway", text=p["caption"], t_key=ca))
    return out

def _picture_els(t, p, ctx, name, frame, asset_name, has_alpha, default_zoom, fit_default="cover"):
    """the shared still / clip layout: bleed or card, Ken Burns, entry, card decoration, label + caption"""
    S = _S(ctx); out = []
    mode = p.get("frame", S.get("media.frame", "bleed"))
    box = tuple(p.get("box") or (design_box(S.get("media.card_box", [100, 300, 980, 1200])) if mode == "card" else (0, 0, G.W, G.H)))
    at = p.get("at", ctx["start"])
    kind = p.get("enter", S.get("media.entry", "rise") if mode == "card" and at > ctx["start"] + .05 else "none")
    dx, dy, sc, op = _entry(t, at, p.get("out_at"), S, kind)
    if op <= 0: return out
    r = int(p.get("radius", S.get("media.radius", 36))) if mode == "card" else int(p.get("radius", 0))
    b = _scaled_box(box, sc, dx, dy); bw, bh = int(round(b[2] - b[0])), int(round(b[3] - b[1]))
    if bw < 2 or bh < 2: return out
    z, px, py = _kb(t, p, ctx, S, default_zoom)
    sh, sw = frame.shape[:2]; s = fit_scale(sw, sh, bw, bh, p.get("fit", fit_default)) * z
    hw, hh = bw / 2 / s, bh / 2 / s
    u = sw / 2 + px * max(0, sw / 2 - hw); v = sh / 2 + py * max(0, sh / 2 - hh)
    pic = view(frame, bw, bh, s, (u, v), alpha=has_alpha or p.get("fit") == "contain")
    if mode == "card" and p.get("fit", fit_default) == "contain" and p.get("matte", True):    # contain on a card: fill the card behind
        bg = np.zeros_like(pic); bg[..., :3] = G.CARD; bg[..., 3] = 255
        a = pic[..., 3:4].astype(np.float32) / 255; pic = (pic[..., :3] * a + bg[..., :3] * (1 - a)).astype(np.uint8)
        pic = np.dstack([pic, np.full(pic.shape[:2], 255, np.uint8)])
    if mode == "card":
        deco_args = (r, int(S.get("media.border", 3)), float(S.get("media.shadow", .5)), tuple(G.CARD_B))
        if abs(sc - 1) < 1e-3:                    # a sliding card: shift the cached rest-position decoration (no re-blur per frame)
            deco = _card_deco(tuple(round(v_) for v_ in box), *deco_args, _wh=(G.W, G.H))
            if round(dx) or round(dy):
                moved = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0)); moved.paste(deco, (int(round(dx)), int(round(dy)))); deco = moved
        else: deco = _card_deco(tuple(round(v_) for v_ in b), *deco_args, _wh=(G.W, G.H))
        if op < 1:
            a = np.asarray(deco).copy(); a[..., 3] = (a[..., 3] * op).astype(np.uint8); deco = Image.fromarray(a, "RGBA")
        out.append(El(deco, f"{name}.card", "media"))
    out.append(El(canvas_layer(pic, b[0], b[1], _rmask(bw, bh, r) if r > 0 else None, op), f"{name}.pic", "media", asset=asset_name, t_key=at))
    return out + _text_els(t, p, b, S, name, op)

def _entry_cue(p, ctx, S):
    at = p.get("at", ctx["start"]); n = p.get("sfx", S.get("media.sfx_in", "swipe"))
    if not n or at <= ctx["start"] + .1: return []           # the cutaway transition already carries the entry sound
    return [(at - .04, n, p.get("sfx_gain", -19), {"trim": (0, .25)})]

def _audio_cue(p, ctx):
    """the clip's own sound, routed to the mix (kw asset -> mix resolves the file; see docs/MEDIA.md)"""
    if not p.get("audio"): return []
    at = p.get("at", ctx["start"]); sin = float(p.get("in", 0)); dur = max(0, ctx["end"] - at) * float(p.get("speed", 1.0))
    if p.get("out") is not None: dur = min(dur, float(p["out"]) - sin)
    return [(at, f"asset:{p['asset']}", p.get("gain", -12), {"asset": p["asset"], "trim": (sin, sin + dur), "speed": p.get("speed", 1.0), "reveal": True})]


# ------------------------------------------------------------------ image
def image(t, p, ctx):
    """still with Ken Burns. p: asset, fit cover|contain, zoom [from, to], pan [[x,y],[x,y]], frame bleed|card, box, radius, at, enter, out_at, label, label_at, caption, caption_at"""
    fr, name, al = media_frame(t, p, ctx, p.get("at", ctx["start"]))
    return _picture_els(t, p, ctx, p.get("name", "image"), fr, name, al, _S(ctx).get("media.ken_burns", [1.0, 1.08]))

def image_cues(p, ctx): return _entry_cue(p, ctx, _S(ctx))


# ------------------------------------------------------------------ video_broll
def video_broll(t, p, ctx):
    """B-roll clip. p: asset, in, out, speed, after loop|hold, fit, zoom, pan, frame bleed|card, box, at, audio (bool), gain, label, caption"""
    at = p.get("at", ctx["start"])
    if t < at - 1e-6: return []
    fr, name, al = media_frame(t, p, ctx, at, p.get("after", "hold"))
    if fr is None: return []
    return _picture_els(t, p, ctx, p.get("name", "broll"), fr, name, al, 1.0)

def video_broll_cues(p, ctx): return _entry_cue(p, ctx, _S(ctx)) + _audio_cue(p, ctx)


# ------------------------------------------------------------------ screen_rec
@functools.lru_cache(16)
def _device(kind, box, url, r, _wh=None):
    """phone / browser frame around the screen area -> (frame layer, screen box)"""
    x0, y0, x1, y1 = box
    if kind == "phone":
        bz = 16; scr = (x0 + bz, y0 + bz, x1 - bz, y1 - bz)
        def fn(d):
            G.rrect(d, box, r + bz, fill=G.CARD + (255,), outline=G.CARD_B, width=3)
            cx = (x0 + x1) / 2; G.rrect(d, (cx - 70, y0 + bz + 14, cx + 70, y0 + bz + 46), 16, fill=(0, 0, 0, 255))   # island
        return G.layer(fn), scr, r
    if kind == "browser":
        bar = 66; scr = (x0, y0 + bar, x1, y1)
        def fn(d):
            G.rrect(d, box, r, fill=G.CARD + (255,), outline=G.CARD_B, width=3)
            for j, col in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
                d.ellipse((x0 + 26 + j * 30, y0 + 24, x0 + 44 + j * 30, y0 + 42), fill=col)
            G.rrect(d, (x0 + 130, y0 + 14, x1 - 30, y0 + 52), 19, fill=G.WELL)
            if url: G.draw_text(d, (x0 + 152, y0 + 42), url, G.font("m", 22), (190, 194, 204))
        return G.layer(fn), scr, max(4, r // 3)
    return None, box, r

def _rect_at(t, keys, dur):
    """zoom-to-region: each key {t, rect [x0,y0,x1,y1] in 0..1 of the source} eases the view in over `dur` (key.dur overrides)"""
    cur = (0.0, 0.0, 1.0, 1.0)
    for k in sorted(keys or [], key=lambda k: k["t"]):
        if t < k["t"]: break
        tgt = tuple(k.get("rect") or (0, 0, 1, 1)); e = ease_io(prog(t, k["t"], k.get("dur", dur)))
        cur = tuple(_lerp(a, b, e) for a, b in zip(cur, tgt))
    return cur

def _cursor_at(t, keys, move_s):
    """cursor position (0..1 source coords) gliding into each key {t, x, y} over move_s before its time"""
    ks = sorted(keys or [], key=lambda k: k["t"])
    if not ks or t < ks[0]["t"] - move_s: return None
    if t <= ks[0]["t"]: return ks[0]["x"], ks[0]["y"]
    for a, b in zip(ks, ks[1:]):
        if t <= b["t"]:
            e = ease_io(prog(t, max(a["t"], b["t"] - move_s), min(move_s, b["t"] - a["t"])))
            return _lerp(a["x"], b["x"], e), _lerp(a["y"], b["y"], e)
    return ks[-1]["x"], ks[-1]["y"]

def screen_rec(t, p, ctx):
    """screen recording in a device frame. p: asset, device phone|browser|none, box, url, zoom [{t, rect, dur?}], cursor [{t, x, y, click?}], in, out, speed, after, fit, at, enter, label, caption"""
    S = _S(ctx); at = p.get("at", ctx["start"]); out = []
    if t < at - 1e-6: return out
    dev = p.get("device", "phone")
    box = tuple(p.get("box") or design_box(S.get(f"media.device_box.{dev}", [300, 330, 780, 1250] if dev == "phone" else [60, 420, 1020, 1060])))
    kind = p.get("enter", S.get("media.entry", "rise") if at > ctx["start"] + .05 else "none")
    dx, dy, sc, op = _entry(t, at, p.get("out_at"), S, kind)
    if op <= 0: return out
    b = tuple(round(v) for v in _scaled_box(box, sc, dx, dy))
    r = int(p.get("radius", S.get("media.radius", 36)) * (1.6 if dev == "phone" else 1))
    frame_l, scr, rs = _device(dev, b, p.get("url", ""), r, (G.W, G.H))
    fr, name, al = media_frame(t, p, ctx, at, p.get("after", "hold"))
    if fr is None: return out
    sh, sw = fr.shape[:2]; bw, bh = int(scr[2] - scr[0]), int(scr[3] - scr[1])
    rx0, ry0, rx1, ry1 = _rect_at(t, p.get("zoom"), p.get("zoom_s", S.get("media.zoom_s", .6)))
    Rw, Rh = max(1, (rx1 - rx0) * sw), max(1, (ry1 - ry0) * sh)
    full = (rx1 - rx0) > .999 and (ry1 - ry0) > .999
    s = fit_scale(Rw, Rh, bw, bh, p.get("fit", "cover") if full else "cover")
    u, v = (rx0 + rx1) / 2 * sw, (ry0 + ry1) / 2 * sh
    pic = view(fr, bw, bh, s, (u, v), alpha=al or p.get("fit") == "contain")
    hw, hh = bw / 2 / s, bh / 2 / s                                        # the clamped centre (as view() used it), for the cursor
    u = min(max(u, hw), sw - hw) if sw >= 2 * hw else sw / 2; v = min(max(v, hh), sh - hh) if sh >= 2 * hh else sh / 2
    if p.get("fit") == "contain" and full:
        bg = np.zeros_like(pic); bg[..., 3] = 255; a = pic[..., 3:4].astype(np.float32) / 255
        pic = np.dstack([(pic[..., :3] * a).astype(np.uint8), bg[..., 3]])
    if frame_l is not None:
        if op < 1:
            a = np.asarray(frame_l).copy(); a[..., 3] = (a[..., 3] * op).astype(np.uint8); frame_l = Image.fromarray(a, "RGBA")
        out.append(El(frame_l, f"{p.get('name', 'screen')}.device", "media"))
    out.append(El(canvas_layer(pic, scr[0], scr[1], _rmask(bw, bh, rs), op), f"{p.get('name', 'screen')}.view", "media", asset=name, t_key=at))
    cur = _cursor_at(t, p.get("cursor"), p.get("cursor_move_s", .4))
    if cur is not None and op > 0:
        X = scr[0] + bw / 2 + (cur[0] * sw - u) * s; Y = scr[1] + bh / 2 + (cur[1] * sh - v) * s
        if scr[0] <= X <= scr[2] and scr[1] <= Y <= scr[3]:
            cs = p.get("cursor_size", S.get("media.cursor_size", 26))
            clicks = [k["t"] for k in p.get("cursor") or [] if k.get("click")]
            pul = [prog(t, c, .45) for c in clicks if 0 <= t - c < .45]
            def curs(d):
                d.ellipse((X - cs, Y - cs, X + cs, Y + cs), fill=G.MINT + (90,), outline=G.MINT + (230,), width=3)
                d.ellipse((X - 5, Y - 5, X + 5, Y + 5), fill=G.WHITE + (255,))
                for q in pul:
                    rr = cs * (1 + 1.6 * ease_out(q)); d.ellipse((X - rr, Y - rr, X + rr, Y + rr), outline=G.MINT + (int(220 * (1 - q)),), width=4)
            out.append(El(G.layer(curs), f"{p.get('name', 'screen')}.cursor", "media"))
    return out + _text_els(t, dict(p, frame="card"), b, S, p.get("name", "screen"), op)    # stage label above the device

def screen_rec_cues(p, ctx):
    S = _S(ctx); c = _entry_cue(p, ctx, S) + _audio_cue(p, ctx); n = S.get("media.sfx_click", "button")
    if n: c += [(k["t"] - .01, n, p.get("click_gain", -20), {}) for k in p.get("cursor") or [] if k.get("click")]
    return c


# ------------------------------------------------------------------ A-roll access (pip / split): the render hook
_WARNED = set()
def face_from_matte(matte):
    """(cx, cy, h) of the head from a framed matte: top of the person, centroid of the head band (no face track needed)"""
    m = matte > .5; rows = np.where(m.mean(1) > .01)[0]
    if not len(rows): return G.W / 2, G.H * .38, G.H * .18
    top = rows[0]; band = m[top + int(G.H * .03):top + int(G.H * .09)]; ys, xs = np.nonzero(band)     # the skull, above the ears
    w = (np.percentile(xs, 97) - np.percentile(xs, 3)) if len(xs) else G.W * .3
    h = min(G.H * .4, max(G.H * .06, w * 1.3)); return (float(xs.mean()) if len(xs) else G.W / 2), top + h * .5, h

def _aroll(ctx):
    """ctx["aroll"] from render: (rgb float HxWx3, matte float HxW) framed like the A-roll shot, a dict {rgb, matte, face},
    or a callable returning either. ctx["aroll_face"] = (cx, cy, h) is used when given, else the head is found from the matte."""
    a = ctx.get("aroll"); a = a() if callable(a) else a
    if a is None:
        if "aroll" not in _WARNED:
            _WARNED.add("aroll"); print("media: ctx['aroll'] not provided by render: pip/split show a placeholder (docs/MEDIA.md)", file=sys.stderr)
        return None
    if isinstance(a, (tuple, list)): a = {"rgb": a[0], "matte": a[1] if len(a) > 1 else None}
    if a.get("matte") is None: a["matte"] = np.ones(a["rgb"].shape[:2], np.float32)
    if a.get("face") is None: a["face"] = tuple(ctx["aroll_face"]) if ctx.get("aroll_face") else face_from_matte(a["matte"])
    return a

def _aroll_rgba(a, cutout=False):
    rgb = np.clip(a["rgb"] * 255 + .5, 0, 255).astype(np.uint8)
    al = np.clip(a["matte"] * 255 + .5, 0, 255).astype(np.uint8) if cutout else np.full(rgb.shape[:2], 255, np.uint8)
    return np.dstack([rgb, al])

def _layer_from_spec(t, spec, ctx, name):
    """background / pane content: {asset, ...} (image or clip, full bleed) or {template, params} -> list[El]"""
    if not spec: return []
    if spec.get("template"):
        from . import get
        return get(spec["template"])[0](t, spec.get("params") or {}, ctx)
    at = spec.get("at", ctx["start"]); fr, nm, al = media_frame(t, spec, ctx, at, spec.get("after", "loop"))
    if fr is None: return []
    q = dict(spec, frame="bleed", enter="none")
    return _picture_els(t, q, ctx, name, fr, nm, al, spec.get("zoom", 1.0))


# ------------------------------------------------------------------ pip
@functools.lru_cache(32)
def _ring(x0, y0, size, ring, r, shape, shadow, col, _wh=None):
    """accent ring + drop shadow behind the bubble (cached: static once the pop has landed)"""
    def rg(d):
        if shape == "circle": d.ellipse((x0 - ring, y0 - ring, x0 + size + ring, y0 + size + ring), fill=col + (255,))
        else: G.rrect(d, (x0 - ring, y0 - ring, x0 + size + ring, y0 + size + ring), r + ring, fill=col + (255,))
    return G.shadow(G.layer(rg), r=18, alpha=shadow, dy=10) if shadow > 0 else G.layer(rg)

def pip(t, p, ctx):
    """presenter over B-roll. p: bg {asset, in, out, ...} | {template, params}, shape circle|rounded|cutout, corner br|bl|tr|tl, size, face_zoom, scale (cutout), ring, at, out_at, label"""
    S = _S(ctx); D = S.get("media.pip") or {}; out = _layer_from_spec(t, p.get("bg"), ctx, "pip.bg")
    at = p.get("at", ctx["start"]); shape = p.get("shape", D.get("shape", "circle")); corner = p.get("corner", D.get("corner", "br"))
    es = S.get("motion.entry_s", .28); pi = prog(t, at, es) if at > ctx["start"] + .05 else 1.0
    po = 1 - prog(t, p["out_at"] - es, es) if p.get("out_at") is not None else 1.0
    if pi <= 0 or po <= 0: return out
    sc = back(pi, S.get("motion.overshoot", 1.6)) * (ease_out(po) if po < 1 else 1)
    sz = _safe(S); m = p.get("margin", D.get("margin", 60)); A = _aroll(ctx)
    if shape == "cutout":                                        # the presenter cut out by the matte, anchored to the bottom corner
        k = p.get("scale", D.get("cutout_scale", .55)) * sc; bw, bh = int(G.W * k), int(G.H * k)
        x0 = m if corner.endswith("l") else G.W - m - bw; y0 = G.H - bh if corner.startswith("b") else sz[1]
        if A is None: return out + [El(canvas_layer(np.dstack([np.full((bh, bw, 3), G.CARD, np.uint8), np.full((bh, bw), 200, np.uint8)]), x0, y0), "pip.person", "media", text="aroll hook missing")]
        src = _aroll_rgba(A, cutout=True); pic = view(src, bw, bh, k, (G.W / 2, G.H / 2), alpha=True, clamp_view=False)
        out.append(El(canvas_layer(pic, x0, y0, None, min(1, pi * 2) * po), "pip.person", "media", text="A-roll"))
        return out + _text_els(t, p, (x0, y0, x0 + bw, y0 + bh), S, "pip", po)
    size = int(p.get("size", D.get("size", 360)) * sc)
    if size < 4: return out
    x0 = m if corner.endswith("l") else G.W - m - size
    y0 = sz[1] + m / 2 if corner.startswith("t") else sz[3] - size
    r = size // 2 if shape == "circle" else int(p.get("radius", S.get("media.radius", 36)))
    if A is None:
        pic = np.dstack([np.full((size, size, 3), G.WELL, np.uint8), np.full((size, size), 255, np.uint8)]); txt = "aroll hook missing"
    else:
        fx, fy, fh = A["face"]; side = min(min(G.W, G.H) * .98, max(32, fh * p.get("face_zoom", D.get("face_zoom", 2.4))))
        pic = view(_aroll_rgba(A), size, size, size / side, (fx, fy + fh * .12)); txt = "A-roll"
    mask = _rmask(size, size, r, "circle" if shape == "circle" else "rounded")
    ring = int(p.get("ring", D.get("ring", 6)))
    if ring:
        rl = _ring(int(x0), int(y0), size, ring, r, shape, float(S.get("media.shadow", .5)), tuple(G.MINT), (G.W, G.H))
        if po < 1:
            a_ = np.asarray(rl).copy(); a_[..., 3] = (a_[..., 3] * po).astype(np.uint8); rl = Image.fromarray(a_, "RGBA")
        out.append(El(rl, "pip.ring", "media"))
    out.append(El(canvas_layer(pic, x0, y0, mask, po), "pip.bubble", "media", text=txt))
    q = dict(p, caption_y=p.get("caption_y") or (y0 - ring - 44 if corner.startswith("b") else y0 + size + ring + 44))   # caption off the face
    return out + _text_els(t, q, (x0, y0, x0 + size, y0 + size), S, "pip", po)

def pip_cues(p, ctx):
    S = _S(ctx); at = p.get("at", ctx["start"]); n = p.get("sfx", S.get("media.sfx_in", "swipe"))
    c = [(at - .02, "pop", p.get("sfx_gain", -18), {})] if at > ctx["start"] + .05 and n else []
    bg = p.get("bg") or {}
    if bg.get("template"):
        from . import get
        c += get(bg["template"])[1](bg.get("params") or {}, ctx)
    elif bg.get("audio"): c += _audio_cue(dict(bg, at=bg.get("at", at)), ctx)
    return c


# ------------------------------------------------------------------ split
def split(t, p, ctx):
    """two panes. p: layout tb|lr, ratio, gap, radius, panes [{asset, in, out, speed, after, fit, zoom, pan, label} | {aroll: true, zoom, label}], at"""
    S = _S(ctx); D = S.get("media.split") or {}; out = []
    lay = p.get("layout", "tb"); ratio = p.get("ratio", D.get("ratio", .5)); gap = p.get("gap", D.get("gap", 12)); r = p.get("radius", D.get("radius", 0))
    if lay == "tb": boxes = [(0, 0, G.W, G.H * ratio - gap / 2), (0, G.H * ratio + gap / 2, G.W, G.H)]
    else: boxes = [(0, 0, G.W * ratio - gap / 2, G.H), (G.W * ratio + gap / 2, 0, G.W, G.H)]
    es = S.get("motion.entry_s", .28); sz = _safe(S)
    for j, (pn, bx) in enumerate(zip(p.get("panes", [])[:2], boxes)):
        pat = pn.get("at", p.get("at", ctx["start"]))
        e = 1.0 if pat <= ctx["start"] + .05 else ease_out(prog(t, pat, es))
        if e <= 0: continue
        off = (1 - e) * (G.W if lay == "lr" else G.H) * (.25 if j else -.25)          # panes slide in from their own edge
        b = (bx[0] + (off if lay == "lr" else 0), bx[1] + (off if lay == "tb" else 0), bx[2] + (off if lay == "lr" else 0), bx[3] + (off if lay == "tb" else 0))
        bw, bh = int(round(b[2] - b[0])), int(round(b[3] - b[1])); name = f"split.p{j}"
        if pn.get("aroll"):
            A = _aroll(ctx)
            if A is None: pic, nm = np.dstack([np.full((bh, bw, 3), G.WELL, np.uint8), np.full((bh, bw), 255, np.uint8)]), None; txt = "aroll hook missing"
            else:
                fx, fy, fh = A["face"]; s = max(bw / G.W, bh / G.H) * pn.get("zoom", 1.0)
                pic = view(_aroll_rgba(A), bw, bh, s, (fx, fy + fh * .25)); nm, txt = None, "A-roll"
        else:
            fr, nm, al = media_frame(t, pn, ctx, pat, pn.get("after", "hold"))
            if fr is None: continue
            z, px, py = _kb(t, dict(pn, at=pat), ctx, S, 1.0); sh, sw = fr.shape[:2]
            s = fit_scale(sw, sh, bw, bh, pn.get("fit", "cover")) * z; hw, hh = bw / 2 / s, bh / 2 / s
            pic = view(fr, bw, bh, s, (sw / 2 + px * max(0, sw / 2 - hw), sh / 2 + py * max(0, sh / 2 - hh)), alpha=al); txt = None
        out.append(El(canvas_layer(pic, b[0], b[1], _rmask(bw, bh, int(r)) if r else None), name, "media", asset=nm, text=txt, t_key=pat))
        if pn.get("label") and e >= 1:
            ly = (b[3] - 60 if j == 0 else b[1] + 90) if lay == "tb" else sz[1] + 60
            ly = min(max(ly, sz[1] + 40), sz[3] - 30); f = G.font("b", pn.get("label_size", 32)); cx = (b[0] + b[2]) / 2
            out.append(El(G.layer(lambda d, cx=cx, ly=ly, f=f, s_=pn["label"]: G.pill(d, cx, ly, s_, f)), f"{name}.label", "cutaway", text=pn["label"], t_key=pn.get("label_at", pat)))
    return out

def split_cues(p, ctx):
    S = _S(ctx); c = []
    for pn in p.get("panes", []):
        pat = pn.get("at", p.get("at", ctx["start"]))
        if pat > ctx["start"] + .1 and S.get("media.sfx_in", "swipe"): c.append((pat - .04, S.get("media.sfx_in", "swipe"), -19, {"trim": (0, .25)}))
        if pn.get("audio") and pn.get("asset"): c += _audio_cue(dict(pn, at=pat), ctx)
    return c


# ------------------------------------------------------------------ overlay_render
def _blend_to_over(a, mode):
    """express a blend mode as straight-alpha 'over' so it composites through El like everything else.
    normal: as is. screen / add: unmultiply by luminance (alpha = max(rgb)), the standard treatment for light FX on black;
    multiply: alpha = 1 - luminance on black. Exact for black-background FX, approximate otherwise (docs/MEDIA.md)."""
    if mode in (None, "normal"): return a
    rgb = np.ascontiguousarray(a[..., :3]); al = np.ascontiguousarray(a[..., 3])
    if mode in ("screen", "add", "lighten"):
        mx = rgb.max(-1); col = cv2.divide(rgb, cv2.merge([mx] * 3), scale=255)       # un-multiply by luminance
        return cv2.merge([*cv2.split(col), cv2.multiply(mx, al, scale=1 / 255)])
    if mode in ("multiply", "darken"):
        inv = 255 - cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        return cv2.merge([np.zeros_like(inv)] * 3 + [cv2.multiply(inv, al, scale=1 / 255)])
    raise SystemExit(f"overlay_render: blend '{mode}' unknown (normal | screen | add | multiply)")

def overlay_render(t, p, ctx):
    """pre-rendered RGBA (ProRes 4444 / PNG sequence / PNG). p: asset, at, in, out, speed, after hide|hold|loop, fps (sequences), box, fit, opacity, blend normal|screen|add|multiply, base {template, params} | {asset} (cutaway use)"""
    out = _layer_from_spec(t, p.get("base"), ctx, "overlay.base") if p.get("base") else []
    at = p.get("at", ctx["start"])
    if t < at - 1e-6: return out
    fr, name, al = media_frame(t, p, ctx, at, p.get("after", "hide"))
    if fr is None: return out
    box = tuple(p.get("box") or (0, 0, G.W, G.H)); bw, bh = int(box[2] - box[0]), int(box[3] - box[1])
    sh, sw = fr.shape[:2]; s = fit_scale(sw, sh, bw, bh, p.get("fit", "contain"))
    pic = view(_blend_to_over(fr, p.get("blend", "normal")), bw, bh, s, (sw / 2, sh / 2), alpha=True, clamp_view=False)
    out.append(El(canvas_layer(pic, box[0], box[1], None, float(p.get("opacity", 1.0))), p.get("name", "overlay.fx"), "media", asset=name, t_key=at))
    return out

def overlay_render_cues(p, ctx):
    c = _audio_cue(p, ctx)
    if p.get("sfx"): c.append((p.get("at", ctx["start"]), p["sfx"], p.get("sfx_gain", -18), {}))
    b = p.get("base") or {}
    if b.get("template"):
        from . import get
        c += get(b["template"])[1](b.get("params") or {}, ctx)
    return c


# ------------------------------------------------------------------ broll_shot (the edit.yaml broll: track; docs/FORMATS.md)
def _blur_fill(fr, sigma, dim):
    """the frame cover-scaled to the canvas, blurred (sigma in canvas px) and dimmed: the bed under a `fit` shot"""
    sh, sw = fr.shape[:2]; k = 8; w, h = max(2, G.W // k), max(2, G.H // k)
    small = view(fr, w, h, fit_scale(sw, sh, w, h, "cover"), (sw / 2, sh / 2))
    small = cv2.GaussianBlur(small[..., :3], (0, 0), max(.5, sigma / k))
    big = cv2.resize(small, (G.W, G.H), interpolation=cv2.INTER_LINEAR).astype(np.float32) * dim
    return np.dstack([np.clip(big, 0, 255).astype(np.uint8), np.full((G.H, G.W), 255, np.uint8)])

def broll_shot(t, p, ctx):
    """one shot of the broll: track, full frame. p: asset (id or footage path), in, speed, after hold|loop, framing fill|fit,
    kenburns {zoom, pan, ease}, anchor [x, y] (fill crop centre, 0..1). Any source size / rotation / rate: frames are
    sampled by time (media_frame), so nothing is ever stretched: fill crops to the canvas aspect, fit letterboxes onto a
    blurred, dimmed copy of itself (style broll.fit_blur / broll.fit_dim)."""
    S = _S(ctx); at = ctx["start"]
    spec = {"asset": p.get("asset"), "in": p.get("in", 0), "speed": p.get("speed", 1.0), "out": p.get("out"), "fps": p.get("fps")}
    fr, name, al = media_frame(t, spec, ctx, at, p.get("after", "hold"))
    if fr is None: return []
    kb = p.get("kenburns")
    z, px, py = _kb(t, dict(kb, at=kb.get("at", at)), ctx, S, 1.0) if kb else (1.0, 0.0, 0.0)
    sh, sw = fr.shape[:2]; ax, ay = (p.get("anchor") or (.5, .5))[:2]
    if p.get("framing", "fill") == "fit":
        s = fit_scale(sw, sh, G.W, G.H, "contain") * z; hw, hh = G.W / 2 / s, G.H / 2 / s
        u = sw / 2 + px * max(0, sw / 2 - hw); v = sh / 2 + py * max(0, sh / 2 - hh)
        fg = view(fr, G.W, G.H, s, (u, v), alpha=True)
        bed = _blur_fill(fr, float(S.get("broll.fit_blur", 40)) * G.U, float(S.get("broll.fit_dim", .55)))
        a = fg[..., 3:4].astype(np.float32) / 255
        pic = np.dstack([(fg[..., :3] * a + bed[..., :3] * (1 - a)).astype(np.uint8), np.full((G.H, G.W), 255, np.uint8)])
    else:
        s = fit_scale(sw, sh, G.W, G.H, "cover") * z; hw, hh = G.W / 2 / s, G.H / 2 / s
        u = ax * sw + px * max(0, sw / 2 - hw); v = ay * sh + py * max(0, sh / 2 - hh)
        pic = view(fr, G.W, G.H, s, (u, v), alpha=al)
    return [El(canvas_layer(pic, 0, 0), p.get("name", "broll"), "media", asset=name, t_key=at)]

def broll_shot_cues(p, ctx):
    """the shot's own sound (audio: true), trimmed to the shot and played at its speed"""
    return _audio_cue(dict(p, at=ctx["start"], gain=p.get("gain", _S(ctx).get("broll.audio_gain", -14))), ctx) if p.get("audio") else []


T = {"image": (image, image_cues), "video_broll": (video_broll, video_broll_cues), "screen_rec": (screen_rec, screen_rec_cues),
     "pip": (pip, pip_cues), "split": (split, split_cues), "overlay_render": (overlay_render, overlay_render_cues),
     "broll_shot": (broll_shot, broll_shot_cues)}
