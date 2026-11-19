"""v0.4 workstream J (weak spots): the v0.2 UI cutaways and roto cards laid out natively per canvas, relative templates
rasterised at the canvas's real resolution (no 4K softness), HDR B-roll tonemapped like A-roll, import-edits for B-roll and
motion tracks, and the full Kdenlive round trip (skipped without melt)."""
import os, json, shutil, subprocess, numpy as np, pytest
from cves import gfx as G, style as STY, templates as TPL, config as C

LEGACY = {
    "search_rows": {"label": "WHAT PEOPLE SEARCH", "pills": ["dentist", "near me"], "pill_times": {"left": [0.2, .5], "plus": .8, "right": 1.0},
                    "rows": [{"q": "best dentist near me", "type": [1.4, 2.0], "tag": 2.1, "check": 2.4},
                             {"q": "emergency dentist open now", "type": [2.0, 2.6], "check": 2.8},
                             {"q": "teeth whitening price", "type": [2.6, 3.0], "check": 3.1}], "tag_text": "local", "enter": 0.0},
    "card_list": {"label": "WHAT YOU GET", "label_at": 0, "items": [
        {"icon": "post", "title": "Weekly posts", "sub": "on Google", "at": .2, "state": "check"}, {"icon": "star", "title": "Review replies", "at": .4, "state": "check"},
        {"icon": "chat", "title": "Q&A answers", "at": .6, "state": "check"}, {"icon": "pin", "title": "Map ranking", "sub": "top 3", "at": .8, "state": "check"}]},
    "stat": {"value": 90, "suffix": "%", "count": [0.1, .8], "label": "KEEP WATCHING", "label_at": 0, "icon": "star", "unit": "of viewers", "unit_at": 1.0},
    "browser_list": {"head": [["Your", 0.0], ["website", .1], ["done", .2, True]], "enter": 0, "hero_at": .3,
                     "rows": [{"text": "Home page", "at": .5}, {"text": "Service pages", "at": .7}, {"text": "Blog posts", "at": .9}, {"text": "Booking form", "at": 1.1}],
                     "pill": "IN 7 DAYS", "pill_at": 1.3},
    "map_card": {"at": 0, "pins": 5}, "big_words": {"words": [["EVERY", 0.0], ["SINGLE", .1], ["DAY", .2, True]], "out_at": 9},
    "listing_card": {"at": 0, "stars": 5}, "top3_card": {"at": 0, "badge": "TOP 3", "badge_at": .3, "rows": 3},
}


@pytest.fixture(autouse=True)
def _default_canvas():
    yield
    G.apply_style(STY.load(), canvas=G.DESIGN)


def _draw(name, size, t=2.9, p=None):
    S = STY.load(); G.apply_style(S, canvas=size)
    ctx = {"start": 0.0, "end": 4.0, "fps": 30, "resolve": lambda x: x, "S": S}
    return TPL.get(name)[0](t, p or LEGACY[name], ctx)


def _union(els):
    bbs = [e.im.getbbox() for e in els if e.im.getbbox() and not e.id.endswith(".glow")]
    return (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))


# ---------------------------------------------------------------- 1. legacy cutaways laid out per canvas
def test_legacy_templates_are_relative_now():
    for n in LEGACY: assert TPL.LAYOUT[n] == "relative" and TPL.RASTER[n], n


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1080), (1080, 1350), (3840, 2160)])
def test_legacy_cutaways_fill_the_safe_zone(size):
    """landscape / square: every legacy cutaway and roto card stays inside the safe zone and fills it on one axis
    (the old fixed layout was fitted at <= 1x and sat small in the middle of a 16:9 frame)"""
    for n in LEGACY:
        els = _draw(n, size); assert els and all(e.im.size == size for e in els), n
        u = _union(els); z = G.safe(); tol = 2 * G.U
        assert z[0] - tol <= u[0] and u[2] <= z[2] + tol and z[1] - tol <= u[1] and u[3] <= z[3] + tol, (n, size, u, z)
        fw, fh = (u[2] - u[0]) / (z[2] - z[0]), (u[3] - u[1]) / (z[3] - z[1])
        assert max(fw, fh) >= .7, (n, size, round(fw, 2), round(fh, 2))


def test_card_list_is_two_columns_on_landscape():
    els = [e for e in _draw("card_list", (1920, 1080)) if e.id.startswith("list.item")]
    xs = sorted({e.im.getbbox()[0] // 20 for e in els}); assert len(xs) == 2, xs               # two column edges
    els = [e for e in _draw("card_list", (1080, 1920)) if e.id.startswith("list.item")]
    assert len({e.im.getbbox()[0] // 20 for e in els}) == 1                                    # one column on 9:16


def test_vertical_layout_keeps_the_design_numbers():
    """9:16 draws the original 1080x1920 coordinates (the golden frames hold): first card at x 120 / y 750 (with a label)"""
    it = next(e for e in _draw("card_list", (1080, 1920)) if e.id == "list.item0")
    x0, y0, _, _ = it.im.getbbox(); assert abs(x0 - 120) <= 4 and abs(y0 - 750) <= 4, (x0, y0)
    pin = next(e for e in _draw("top3_card", (1080, 1920)) if e.id == "roto.badge")
    b = pin.im.getbbox(); assert abs((b[0] + b[2]) / 2 - 540) <= 2 and abs((b[1] + b[3]) / 2 - 300) <= 2, b


# ---------------------------------------------------------------- 2. no 4K softness
def _sharpness(img):
    a = np.asarray(img.convert("L"), np.float32)
    g = np.maximum(np.abs(np.diff(a, axis=1))[:-1, :], np.abs(np.diff(a, axis=0))[:, :-1])
    return float(np.percentile(g[g > 4], 95))


@pytest.mark.parametrize("size", [(3840, 2160), (2160, 3840)])
@pytest.mark.parametrize("name,params", [("card_list", None), ("title_card", {"lines": ["Crisp at 4K", "every edge"], "at": 0.0})])
def test_4k_graphics_are_drawn_at_4k(size, name, params):
    """a relative template at 4K is rasterised at 4K (type, strokes and icons scale by G.U): its edges are at least
    1.5x sharper than the old path (drawn at a 1080 short side, then scaled up)"""
    from PIL import Image
    def frame(raster):
        TPL.RASTER[name] = raster
        try: els = _draw(name, size, p=params)
        finally: TPL.RASTER[name] = True
        img = np.zeros((size[1], size[0], 3), np.float32) + .05
        for e in els: img = G.over(img, e.im)
        return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    a, b = _sharpness(frame(True)), _sharpness(frame(False))
    assert a >= 1.5 * b, (name, size, a, b)


def test_raster_scale_is_the_identity_at_1080():
    S = STY.load(); G.apply_style(S, canvas=(1080, 1920)); assert (G.PW, G.PH, G.R) == (1080, 1920, 1.0)
    G.apply_style(S, canvas=(1920, 1080)); assert (G.PW, G.PH, G.R) == (1920, 1080, 1.0)
