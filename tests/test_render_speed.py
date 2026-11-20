"""The render speed-ups are exact: every fast path gives the same numbers as the code it replaced (docs/ARCHITECTURE.md
§6b). Bit-identical frames mean the golden frames, the QC gates and the master do not move."""
import os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from cves import gfx as G, render as R, shotmatch as SM, motion as MO

RNG = np.random.default_rng(7)
H, W = 480, 270


def _layer(seed, empty=False):
    im = Image.new("RGBA", (W, H), (10, 20, 30, 0))
    if not empty:
        d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
        for _ in range(3):
            x0, y0 = int(r.integers(0, W - 60)), int(r.integers(0, H - 60))
            d.ellipse((x0, y0, x0 + int(r.integers(5, 60)), y0 + int(r.integers(5, 60))), fill=tuple(int(v) for v in r.integers(0, 255, 4)))
    return im


def _over_full(dst, im, opacity=1.0):          # the original formula, on the whole frame
    a = np.asarray(im, np.float32) / 255; al = a[..., 3:4] * opacity
    return dst * (1 - al) + a[..., :3] * al


def test_over_blends_only_the_visible_box_with_the_same_result():
    for seed in range(8):
        dst = RNG.random((H, W, 3), dtype=np.float32); im = _layer(seed, empty=seed == 3)
        for op in (1.0, .4):
            ref = _over_full(dst, im, op); keep = dst.copy()
            assert np.array_equal(G.over(dst, im, op), ref) and np.array_equal(dst, keep)      # not in place: dst untouched
            assert np.array_equal(G.over(dst.copy(), im, op, inplace=True), ref)


def test_alpha_box_matches_numpy():
    for seed in range(8):
        im = _layer(seed, empty=seed == 2); a = np.asarray(im)[..., 3]; ys, xs = np.where(a > 20)
        box, mx = R._alpha_box(im)
        assert mx == float(a.max())
        assert box == ((float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())) if len(xs) else None)


def test_shot_match_lut_shares_its_index():
    P = RNG.random((H, W, 3), dtype=np.float32); g = np.array([1.12, .93, 1.01])
    idx = np.clip(P * (SM._LUT_N - 1) + .5, 0, SM._LUT_N - 1).astype(np.int32); ref = np.empty_like(P)
    for c in range(3): ref[..., c] = SM.oetf(SM._LIN * g[c]).astype(P.dtype)[idx[..., c]]
    assert np.array_equal(SM._lut(P, g), ref) and np.array_equal(SM._lut(P, g, SM._chan_idx(P)), ref)


def test_split_boxes_is_split_alpha_in_crops():
    for seed in range(6):
        r = np.random.default_rng(seed)
        a = np.zeros((H, W, 4), np.uint8); a[..., :3] = r.integers(0, 255, (H, W, 3))
        parts = []
        for j in range(4):
            x0, y0 = int(r.integers(0, W - 80)), int(r.integers(0, H - 80)); x1, y1 = x0 + int(r.integers(10, 80)), y0 + int(r.integers(10, 80))
            a[y0:y1, x0:x1, 3] = r.integers(1, 255, (y1 - y0, x1 - x0)); parts.append([f"p{j}", "t", x0, y0, x1, y1, 1.0])
        a[5:9, 5:200, 3] = 90                                                    # loose pixels: strays and a rest layer
        parts.append(["faint", "", 10, 10, 20, 20, .01])                          # below the opacity floor: skipped
        ref = list(MO.split_alpha(a, parts, 3)); got = list(MO.split_boxes(a, parts, 3))
        assert [p for p, _ in ref] == [p for p, _, _ in got]
        for (_, full), (_, crop, (x0, y0)) in zip(ref, got):
            canvas = np.zeros_like(a); canvas[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]] = crop
            assert np.array_equal(canvas[..., 3], full[..., 3])                  # same alpha everywhere
            vis = full[..., 3] > 0
            assert np.array_equal(canvas[vis], full[vis])                         # same colour wherever it shows


def test_seek_decode_equals_sequential_decode():
    import av
    d = tempfile.mkdtemp(); path = os.path.join(d, "p.mkv")
    with av.open(path, "w") as o:
        st = o.add_stream("ffv1", rate=60); st.width, st.height, st.pix_fmt = 64, 48, "yuv420p"
        for k in range(50):
            fr = av.VideoFrame.from_ndarray(np.full((48, 64, 3), k * 5 % 255, np.uint8), format="rgb24")
            for p in st.encode(fr): o.mux(p)
        for p in st.encode(): o.mux(p)
    seq = [f.to_ndarray(format="rgb24") for f in R._frames_from(path, 0)]
    assert len(seq) == 50
    for start in (1, 11, 12, 13, 37, 49):
        got = [f.to_ndarray(format="rgb24") for f in R._frames_from(path, start)]
        assert len(got) == 50 - start and all(np.array_equal(x, y) for x, y in zip(got, seq[start:])), start


def test_chunks_cover_every_frame_once():
    class TL: pass
    tl = TL(); tl.S = {"render.chunk_min": 8}; tl.segs = [{"id": "a", "f0": 0, "n": 100}, {"id": "b", "f0": 100, "n": 37}]
    tl.A_FRAMES, tl.N = 137, 150
    want = set(range(150)) - set(range(40, 47))
    jobs = R._chunks(tl, want, 3)
    got = [f for _, fr in jobs for f in fr]
    assert sorted(got) == sorted(want) and len(got) == len(set(got))
    for sid, fr in jobs:
        lo, hi = {"a": (0, 100), "b": (100, 137), None: (137, 150)}[sid]
        assert all(lo <= f < hi for f in fr)


def test_shot_match_apply_is_the_same():
    P = RNG.random((H, W, 3), dtype=np.float32); A = (np.random.default_rng(4).random((H, W)) * 255).astype(np.uint8)
    M = {"s": {"k": [0, 10], "gs": [[1.1, .95, 1.02], [1.05, 1.0, .98]], "gb": [[.9, 1.0, 1.08], [.95, 1.02, 1.0]]}}
    import cv2
    def ref(k):                                          # the original apply: two full LUT passes + the blend
        gs, gb = SM.params_at(M, "s", k)
        def lut(g):
            idx = np.clip(P * (SM._LUT_N - 1) + .5, 0, SM._LUT_N - 1).astype(np.int32); out = np.empty_like(P)
            for c in range(3): out[..., c] = SM.oetf(SM._LIN * g[c]).astype(P.dtype)[idx[..., c]]
            return out
        a = A.astype(np.float32) / 255; a = cv2.resize(a, (a.shape[1] // 2, a.shape[0] // 2), interpolation=cv2.INTER_AREA)
        a = cv2.GaussianBlur(cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))), (0, 0), 1.5)
        a = cv2.resize(a, (P.shape[1], P.shape[0]), interpolation=cv2.INTER_LINEAR)[..., None]
        return lut(gs) * a + lut(gb) * (1 - a)
    for k in (0, 4, 10): assert np.array_equal(SM.apply(M, "s", k, P, A), ref(k))


def test_grade_without_a_tint_is_the_same():
    from cves.look import grade
    rgb = RNG.random((H, W, 3), dtype=np.float32) * 1.1
    for g in ({}, {"subject_tint": [1, 1, 1]}, {"subject_tint": [1.02, 1, .97]}, {"gamma": 1.1, "vignette": .2}):
        tint = np.array(g.get("subject_tint", [1, 1, 1]), np.float32); x = rgb
        if g.get("gamma"): x = np.clip(1.0 * x ** g["gamma"], 0, 1)
        out = x * tint
        if g.get("vignette"):
            from cves.look import _vignette
            out = out * _vignette(H, W, W / 2, H * .32, g["vignette"])
        assert np.array_equal(grade(rgb, None, None, g), np.clip(out, 0, 1).astype(np.float32)), g


def _text_layer(seed, w=540, h=960, at=None):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
    x, y = at or (int(r.integers(0, w - 200)), int(r.integers(0, h - 80)))
    d.text((x, y), "Legible words", fill=(255, 255, 255, 255), font=G.font("b", 40)); d.rectangle((x, y + 50, x + 120, y + 58), fill=(80, 200, 120, 180))
    return im


def test_legible_bed_on_the_text_box_is_the_full_frame_bed():
    import cv2
    def ref(im, fg, size_px, bg=None, force=0.0, reach=2):        # the original: every filter on the whole frame
        bg = G.col(bg) or G._rgb(G.sget("legibility.video_bg", "#B4B4B4")); need = G.need_contrast(size_px) * G.sget("legibility.margin", 1.15)
        Lf, Lb = G.lum(fg), G.lum(bg)
        if Lf >= Lb: tgt = (Lf + .05) / need - .05; a = 1 - max(0., tgt) / max(1e-6, Lb); shade = (0, 0, 0)
        else: tgt = need * (Lf + .05) - .05; a = (tgt - Lb) / max(1e-6, 1 - Lb); shade = (255, 255, 255)
        a = G.clamp(max(a, force), 0, G.sget("legibility.plate_max", .85))
        if a <= .02: return None
        al = np.asarray(im)[..., 3]; r = max(3, int(size_px * G.sget("legibility.bed_spread", .18) * G.R))
        m = cv2.GaussianBlur(cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))), (0, 0), max(1., r * .6))
        k = 2 * max(2, int(round(reach * G.R))) + 1; m = np.maximum(m, cv2.dilate(al, np.ones((k, k), np.uint8)))
        out = np.zeros(al.shape + (4,), np.uint8); out[..., :3] = shade; out[..., 3] = (m.astype(np.float32) * a).astype(np.uint8)
        return Image.fromarray(out)
    for seed, at in ((0, None), (1, (0, 0)), (2, (420, 900)), (3, None)):     # also against the frame edges
        im = _text_layer(seed, at=at)
        for fg, bg, force in (((255, 255, 255), None, 0.0), ((20, 20, 20), (90, 90, 90), 0.0), ((255, 255, 255), (200, 200, 200), .5)):
            a, b = ref(im, fg, 60, bg, force), G.legible_bed(im, fg, 60, bg, force)
            assert (a is None) == (b is None)
            if a is None: continue
            A, B = np.asarray(a), np.asarray(b)
            assert np.array_equal(A[..., 3], B[..., 3]) and np.array_equal(A[A[..., 3] > 0], B[A[..., 3] > 0])
            dst = RNG.random((960, 540, 3), dtype=np.float32)
            assert np.array_equal(_over_full(dst, a), G.over(dst, b))


def test_caption_shadow_and_box_composite_are_the_full_frame_ones():
    from PIL import ImageFilter
    from cves import captions as CAP
    G.set_canvas(540, 960)
    try:
        for seed, at in ((0, None), (1, (0, 0)), (2, (420, 900))):
            im = _text_layer(seed, at=at); cfg = {"shadow_blur": 7, "shadow_dy": 3, "shadow_alpha": .7}
            al = np.asarray(im)[..., 3]; sh = Image.fromarray(al).filter(ImageFilter.GaussianBlur(7 * G.U))
            ref = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
            ref.paste(Image.new("RGBA", (G.W, G.H), (0, 0, 0, 255)), (0, int(round(3 * G.U))), sh.point(lambda v: int(v * .7)))
            got = CAP._shadow(im, cfg)
            assert np.array_equal(np.asarray(ref), np.asarray(got))
            full = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
            for L in (ref, im): full.alpha_composite(L)
            box = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
            bs = [b for b in (L.getbbox() for L in (got, im)) if b]
            u = (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))
            for L in (got, im): box.alpha_composite(L, dest=u[:2], source=u)
            assert np.array_equal(np.asarray(full), np.asarray(box))
    finally:
        G.set_canvas(1080, 1920)


def test_faded_changes_only_the_drawn_box():
    from cves import templates as TPL
    def draw(d): d.ellipse((40, 60, 200, 220), fill=(200, 40, 90, 230))
    for alpha in (1.0, .63, .0):
        im = G.layer(draw); a = np.asarray(im).copy(); a[..., 3] = (a[..., 3] * max(0, alpha)).astype(np.uint8)
        assert np.array_equal(np.asarray(TPL.faded(draw, alpha)), a if alpha < 1 else np.asarray(im))


def test_text_behind_scale_on_its_box_is_the_full_frame_scale():
    import cv2
    from cves.templates import craft as TC
    def ref(im, hold, cx, base):
        M = np.float32([[hold, 0, cx * (1 - hold)], [0, hold, base * (1 - hold)]])
        a4 = np.asarray(im).astype(np.float32); a4[..., :3] *= a4[..., 3:4] / 255
        w4 = cv2.warpAffine(a4, M, im.size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        w4[..., :3] /= np.maximum(w4[..., 3:4], 1e-3) / 255
        return np.clip(w4 + .5, 0, 255).astype(np.uint8)
    for seed, at in ((0, None), (1, (0, 0)), (2, (420, 900)), (3, None)):
        im = _text_layer(seed, at=at)
        for hold, cx, base in ((1.0123, 270.4, 500.7), (1.16, 100.0, 40.0), (1.0004, 520.0, 950.0), (.97, 300.0, 700.0)):
            assert np.array_equal(np.asarray(TC._scaled(im, hold, cx, base)), ref(im, hold, cx, base)), (seed, hold)


def test_split_boxes_thin_far_sliver_matches_split_alpha():
    """a 2 px sliver far outside every padded box (a glyph tail mid-rise) joins the nearest part in both splitters"""
    a = np.zeros((120, 160, 4), np.uint8); a[..., :3] = 200
    a[10:30, 10:80, 3] = 255; a[90:92, 20:60, 3] = 40
    parts = [["hd", "t", 10, 10, 80, 30, 1.0]]
    ref = dict(MO.split_alpha(a, parts, 3)); got = {p: (c, o) for p, c, o in MO.split_boxes(a, parts, 3)}
    assert int((ref[""][..., 3] > 0).sum()) == 0
    crop, (x0, y0) = got["hd"]; canvas = np.zeros_like(a); canvas[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]] = crop
    assert np.array_equal(canvas[..., 3], ref["hd"][..., 3])
