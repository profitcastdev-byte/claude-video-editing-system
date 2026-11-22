"""Graphics fixes from the first client job (a 9:16 60 fps selfie ad): text_behind auto colour (GFX-15), one size per
video (GFX-20), seconds-based face smoothing (MOT-03), monotonic roto card entries at any frame rate (MOT-01), roto cards in
the free space beside the head + the GFX-27 cover gate, and the end card layout (GFX-08). Synthetic media only."""
import json, types
import numpy as np, pytest

from cves import craft as CR, style as STY, gfx as G
from cves.templates import craft as TC, roto as RO
from cves import templates as TPL

S = STY.load()


@pytest.fixture(autouse=True)
def _canvas():
    G.apply_style(S, canvas=(1080, 1920)); TC._AUTO.clear(); RO._PLACED.clear()
    yield
    G.apply_style(S, canvas=(1080, 1920))


def _alpha_bbox(im):
    a = np.asarray(im)[..., 3]; ys, xs = np.where(a > 20)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None


def _face(cx=540., top=520.):
    return {"cx": cx, "eye_y": top + 260, "top": top, "chin": top + 640, "w": 460., "h": 620.}


# ------------------------------------------------------------------ GFX-15: color auto
def _wall(L, person=None):
    """a fake plate_lum: a flat wall of relative luminance L, the person (matte) in the given box"""
    def pl(ks):
        out = []
        for k in ks:
            Lm = np.full((1920, 1080), L, np.float32); A = np.zeros((1920, 1080), np.float32)
            if person: x0, y0, x1, y1 = person; A[y0:y1, x0:x1] = 1.0
            out.append((k, Lm, A))
        return out
    return pl


def _behind(text, wall, t=1.5, **kw):
    ctx = {"start": 0.0, "end": 3.0, "fps": 60, "S": S, "face": _face(), "face_at": lambda tt: _face(),
           "frame_of": lambda tt: int(round(tt * 60)), "plate_lum": wall, "matte_ok": True}
    ctx.update(kw)
    return TPL.get("text_behind")[0](t, {"text": text, "at": 0.2}, ctx)


def _ink(el, accent=False):
    """the colour of the drawn type: median RGB of its opaque pixels (accent=True: the bluest ones)"""
    a = np.asarray(el.im); m = a[..., 3] > 240; px = a[..., :3][m].astype(int)
    if accent: px = px[px[:, 2] - px[:, 0] > 20]
    return tuple(np.median(px, 0).astype(int))


def test_auto_colour_reads_on_a_light_and_on_a_dark_wall():
    need = G.need_contrast(100) * S.get("legibility.margin")
    light_wall = _behind("DENTIST?", _wall(.55))
    el = [e for e in light_wall if e.id == "behind.text"][0]
    ink = _ink(el); bg = TC._L2rgb(.55)
    assert G.lum(ink) < .05, f"a light wall gets the dark token, got {ink}"
    assert G.contrast(ink, bg) >= need
    TC._AUTO.clear()
    dark_wall = [e for e in _behind("DENTIST?", _wall(.02)) if e.id == "behind.text"][0]
    assert G.lum(_ink(dark_wall)) > .9, "a dark wall keeps the light token"


def test_auto_accent_takes_its_darker_variant_on_a_light_wall():
    els = _behind("*100%* REFUND", _wall(.45))
    el = [e for e in els if e.id == "behind.text"][0]
    acc = _ink(el, accent=True)
    assert acc[2] > acc[0], f"the accent keeps its hue, got {acc}"
    assert G.contrast(acc, TC._L2rgb(.45)) >= G.need_contrast(100), "the accent must pass GFX-15 on the wall"
    assert G.lum(acc) < G.lum(G.MINT), "on a light wall the accent goes darker"


def test_auto_adds_a_bed_when_no_token_reads():
    half = lambda ks: [(k, np.where(np.arange(1080)[None, :] < 540, .015, .9).astype(np.float32) * np.ones((1920, 1), np.float32),
                        np.zeros((1920, 1080), np.float32)) for k in ks]       # half black, half white wall behind the type
    ids = [e.id for e in _behind("DENTIST?", half)]
    assert "behind.text.bed" in ids


def test_fixed_colour_skips_the_measurement():
    called = []
    def pl(ks): called.append(ks); return []
    ctx = {"start": 0.0, "end": 3.0, "fps": 60, "S": S, "face": _face(), "face_at": lambda tt: _face(), "frame_of": lambda tt: 0, "plate_lum": pl}
    TPL.get("text_behind")[0](1.5, {"text": "HI", "at": 0.2, "color": "text"}, ctx)
    assert not called


# ------------------------------------------------------------------ GFX-20: one size per video
def _tl(roto, zoom=None, creep=0.0, snap=None):
    segs = [{"id": r["segment"], "t0": 3.0 * j, "t1": 3.0 * j + 3, "f0": 180 * j, "n": 180} for j, r in enumerate(roto)]
    return types.SimpleNamespace(E={"roto": roto}, S=S, segs=segs, zoom=zoom or {}, creep=creep, snap=snap, faces={}, FPS=60.0)


def test_text_behind_instances_share_the_smallest_fitted_size():
    roto = [{"segment": "a", "template": "text_behind", "params": {"text": "DENTIST?"}},
            {"segment": "b", "template": "text_behind", "params": {"text": "*100%* REFUND"}},
            {"segment": "c", "template": "text_behind", "params": {"text": "HI", "size": 120}}]       # explicit: kept, left out
    TL = _tl(roto)
    own = [TC.fitted_size(r["params"], S, CR.seg_scale(TL, r["segment"])) for r in roto[:2]]
    assert own[0] > own[1] * 1.15                                     # the short word alone would be much bigger
    hs = CR.behind_size(TL); assert hs == min(own)
    heights = []
    for r in roto[:2]:
        ctx = {"start": 0.0, "end": 3.0, "fps": 60, "S": S, "face": _face(), "behind_size": hs, "seg_scale": 1.0}
        el = [e for e in TPL.get("text_behind")[0](2.0, dict(r["params"], at=0.2, color="text"), ctx) if e.id == "behind.text"][0]
        b = _alpha_bbox(el.im); heights.append(b[3] - b[1])
    assert max(heights) / min(heights) < 1.1, heights                 # GFX-20 compares glyph heights at 15 %


def test_fit_uses_the_tightest_zoom_of_the_shot():
    TL = _tl([{"segment": "a", "template": "text_behind", "params": {"text": "A LONG LINE OF TYPE"}}], zoom={"a": 1.2}, creep=.05)
    assert abs(CR.seg_scale(TL, "a") - 1.26) < 1e-9
    assert TC.fitted_size({"text": "A LONG LINE OF TYPE"}, S, 1.26) < TC.fitted_size({"text": "A LONG LINE OF TYPE"}, S, 1.0)


# ------------------------------------------------------------------ MOT-03: smoothing in seconds
def _jitter_faces(n, fps, seed=1):
    """a head drifting slowly with 15 px detection jitter, as raw face rows [x, y, w, h]"""
    rng = np.random.default_rng(seed); t = np.arange(n) / fps
    x = 300 + 120 * np.sin(t * .9) + rng.normal(0, 15, n); y = 520 + 30 * np.sin(t * 1.3) + rng.normal(0, 10, n)
    return [[float(a), float(b), 460.0, 620.0] for a, b in zip(x, y)]


@pytest.mark.parametrize("fps", [30, 60])
def test_face_track_is_calm_at_any_frame_rate(fps):
    n = 4 * fps; TL = types.SimpleNamespace(faces={"s": _jitter_faces(n, fps)}, S=S, FPS=float(fps))
    cx = np.array([CR.face_track(TL, "s", k)["cx"] for k in range(n)])
    d2 = np.abs(np.diff(cx, 2))
    assert d2.max() < .5, f"face track second difference {d2.max():.2f} px/f^2 at {fps} fps"


def test_text_behind_follow_has_no_shake_at_60fps_even_on_the_safe_edge():
    fps = 60; n = 240; F = _jitter_faces(n, fps)
    for f in F: f[0] -= 260                          # the head drifts far left: the type is pushed onto the safe edge and off it
    TL = types.SimpleNamespace(faces={"s": F}, S=S, FPS=float(fps))
    fa = lambda tt: CR.face_track(TL, "s", int(round(tt * fps)))
    cs = []
    for k in range(60, n):
        t = k / fps
        ctx = {"start": 0.0, "end": n / fps, "fps": fps, "S": S, "face": fa(t), "face_at": fa, "frame_of": lambda tt: int(round(tt * fps))}
        el = [e for e in TPL.get("text_behind")[0](t, {"text": "DENTIST?", "at": 0.2, "color": "text"}, ctx) if e.id == "behind.text"][0]
        b = _alpha_bbox(el.im); cs.append(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    c = np.array(cs); a = np.abs(c[2:] - 2 * c[1:-1] + c[:-2]).max(1)
    z = G.safe(); assert c[:, 0].min() < z[0] + 600                  # it did reach the left part of the zone
    assert (a > 2.5).sum() < 2, f"MOT-03: up to {a.max():.1f} px/f^2"


# ------------------------------------------------------------------ MOT-01: roto card entries at any frame rate
@pytest.mark.parametrize("name", ["map_card", "listing_card", "top3_card"])
@pytest.mark.parametrize("fps", [24, 30, 60])
def test_roto_card_entry_decelerates_monotonically(name, fps):
    ctx = {"start": 10.0, "end": 13.0, "fps": fps, "S": S}
    ys = []
    for j in range(int(.5 * fps)):
        els = TPL.get(name)[0](10.0 + j / fps, {"at": 10.0}, ctx)
        b = _alpha_bbox(els[0].im) if els else None
        if b: ys.append(b[1])
    steps = -np.diff(ys)
    assert steps.sum() > 0 and (steps >= 0).all()
    assert (np.diff(steps) <= 0).all(), f"{name} at {fps} fps: steps {steps.tolist()} grow"


def test_rise_offsets_are_whole_pixels_with_shrinking_steps():
    for R, n in ((40.0, 21.0), (11.2, 8.4), (120.0, 10.5), (40.0, 4.2)):
        off = RO._rise_steps(R, n); st = -np.diff(off)
        assert off[0] == round(R * (1 - G.ease_out(.5 / n))) and off[-1] == 0
        assert all(float(v).is_integer() for v in off) and (st >= 0).all() and (np.diff(st) <= 0).all()


# ------------------------------------------------------------------ roto cards in the free space + GFX-27
def _person(x0=230, x1=850, top=280):
    return lambda ks: [(k, np.full((1920, 1080), .5, np.float32), _body(x0, x1, top)) for k in ks]


def _body(x0, x1, top):
    A = np.zeros((1920, 1080), np.float32); A[top:, x0:x1] = 1; A[1150:, :] = 1          # head + shoulders
    return A


def _card_ctx(pl):
    return {"start": 10.0, "end": 13.0, "fps": 60, "S": S, "plate_lum": pl, "frame_of": lambda tt: int(round((tt - 10) * 60)), "matte_ok": True}


def test_map_card_moves_into_the_free_space_beside_the_head():
    els = TPL.get("map_card")[0](12.0, {"at": 10.0}, _card_ctx(_person(330, 830)))
    b = _alpha_bbox(els[0].im); A = _body(330, 830, 280)
    cover = A[b[1]:b[3] + 1, b[0]:b[2] + 1].mean()
    assert cover <= S.get("roto.max_cover") + .02, f"card {b} is {cover:.0%} behind the subject"
    z = G.safe(); assert z[0] - 1 <= b[0] and b[2] <= z[2] + 1 and z[1] - 1 <= b[1] and b[3] <= z[3] + 1
    assert b[2] < 330 + .25 * (b[2] - b[0]), f"the left side has more room (265 px vs 177): card at {b}"


def test_card_takes_the_side_with_more_room():
    els = TPL.get("map_card")[0](12.0, {"at": 10.0}, _card_ctx(_person(x0=420, x1=900)))
    b = _alpha_bbox(els[0].im); assert b[2] < 420 + .25 * (b[2] - b[0]), f"left has 355 px, right 107: card at {b}"


def test_card_keeps_its_designed_place_when_nothing_fits_or_when_fixed():
    designed = _alpha_bbox(TPL.get("map_card")[0](12.0, {"at": 10.0}, {"start": 10.0, "end": 13.0, "fps": 60, "S": S})[0].im)
    full = lambda ks: [(k, np.full((1920, 1080), .5, np.float32), np.ones((1920, 1080), np.float32)) for k in ks]
    assert _alpha_bbox(TPL.get("map_card")[0](12.0, {"at": 10.0}, _card_ctx(full))[0].im) == designed
    assert _alpha_bbox(TPL.get("map_card")[0](12.0, {"at": 10.0, "place": "fixed"}, _card_ctx(_person()))[0].im) == designed


# ------------------------------------------------------------------ GFX-08 / layout: the end card
P_END = {"headline": "More patients. Reported in rupees.", "button": "TAP THE LINK BELOW", "handle": "Profitcast", "icon": "link"}


@pytest.mark.parametrize("size", [(1080, 1920), (1920, 1080), (1080, 1080), (2160, 3840)])
def test_end_card_is_one_axis_display_type_centred_in_the_safe_zone(size):
    G.apply_style(S, canvas=size)
    els = TPL.get("end_card")[0](41.5, P_END, {"start": 40.0, "end": 42.0, "fps": 60, "S": S, "resolve": lambda x: x})
    bb = {e.id: _alpha_bbox(e.im) for e in els}
    assert set(bb) == {"end.headline", "end.button", "end.handle"}
    cxs = [(b[0] + b[2]) / 2 for b in bb.values()]
    assert max(cxs) - min(cxs) <= 2 * max(1, G.U), f"centre axes {cxs} (GFX-08)"
    z = G.safe(); top = min(b[1] for b in bb.values()); bot = max(b[3] for b in bb.values())
    assert z[1] <= top and bot <= z[3] and z[0] <= min(b[0] for b in bb.values()) and max(b[2] for b in bb.values()) <= z[2]
    mid = (top + bot) / 2; assert abs(mid - (z[1] + z[3]) / 2) < .08 * (z[3] - z[1]), "the block sits in the middle of the safe zone"
    h = bb["end.headline"]; u = min(G.W, G.H) / 1080
    assert (h[3] - h[1]) > 150 * u, "the headline is display type on two lines"
    assert (h[2] - h[0]) > .5 * (z[2] - z[0]), "the headline fills the zone's width"


def test_end_card_logo_sits_above_the_headline(tmp_path):
    from PIL import Image
    p = tmp_path / "logo.png"; Image.new("RGBA", (400, 120), (255, 255, 255, 255)).save(p)
    els = TPL.get("end_card")[0](41.5, dict(P_END, logo=str(p)), {"start": 40.0, "end": 42.0, "fps": 60, "S": S, "resolve": lambda x: x})
    bb = {e.id: _alpha_bbox(e.im) for e in els}
    assert bb["end.logo"][3] < bb["end.headline"][1]
    assert abs((bb["end.logo"][0] + bb["end.logo"][2]) / 2 - (bb["end.headline"][0] + bb["end.headline"][2]) / 2) <= 2
