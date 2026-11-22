"""Motion craft (docs/MOTION.md "Craft"): text behind the speaker, speed ramps, camera moves, match cuts, the transitions
library and the 30 motion pieces. Synthetic media only."""
import os, json, shutil
import numpy as np, pytest, yaml

from cves import craft as CR, style as STY, gfx as G

S = STY.load()


# ------------------------------------------------------------------ speed ramps
@pytest.mark.parametrize("spec", ["slam", "punch_in", "ease_out", "speed_up", "hold", {"keys": [[0, 3], [.5, .1], [1, 2]], "ease": "inOutExpo"}])
def test_ramp_is_monotonic_and_hits_its_endpoints(spec):
    dur, sin, sout = 2.4, 1.5, 4.25
    ts = np.linspace(0, dur, 241)
    src = [CR.ramp_src(t, dur, spec, S, sin, 1.0, sout)[0] for t in ts]
    assert abs(src[0] - sin) < 1e-9 and abs(src[-1] - sout) < 1e-9          # the shot keeps its in / out exactly
    assert all(b > a for a, b in zip(src, src[1:]))                           # strictly increasing: never stalls or reverses
    free = [CR.ramp_src(t, dur, spec, S, sin, 1.0)[0] for t in ts]           # no out: consumes base x dur x mean speed
    assert abs(free[-1] - (sin + CR.ramp_span(dur, spec, S))) < 1e-9
    assert all(b > a for a, b in zip(free, free[1:]))


def test_ramp_speed_follows_the_keys():
    f, v, cum = CR.ramp_table("slam", S)
    keys = CR.ramp_keys("slam", S)
    for a, b in keys: assert abs(np.interp(a, f, v) - max(b, S.get("craft.ramp.min_speed"))) < 1e-6
    with pytest.raises(SystemExit): CR.ramp_keys({"preset": "nope"}, S)


def test_ramp_frame_blending():
    class Clip:                                   # frame i is a flat grey of value 10 * i
        fps, n = 10.0, 20
        def frame(self, i): return np.full((4, 4, 4), 10 * min(max(int(i), 0), self.n - 1), np.uint8)
    c = Clip()
    assert CR.ramp_frame(c, 0.45, .2, 30, "nearest")[0, 0, 0] in (40, 50)
    assert CR.ramp_frame(c, 0.45, .2, 30, "blend")[0, 0, 0] == 45            # slow: crossfade of the two neighbours
    fast = CR.ramp_frame(c, 1.0, 8.0, 30, "blend")[0, 0, 0]                  # fast: an average over the shutter window
    assert 80 <= fast <= 120


def test_varispeed_audio_length_and_pitch():
    sr = 8000; y = np.sin(2 * np.pi * 200 * np.arange(sr * 3) / sr).astype(np.float32)
    kw = CR.ramp_audio_kw({"keys": [[0, 1], [1, 1]]}, S, 1.5, 0.0, 2.0)          # constant 2x: one octave up
    out = CR.varispeed(y, sr, dict(kw, sin=0.0))
    assert len(out) == int(1.5 * sr)
    spec = np.abs(np.fft.rfft(out)); hz = np.argmax(spec) * sr / len(out)
    assert 380 < hz < 420


# ------------------------------------------------------------------ transitions
@pytest.mark.parametrize("kind", CR.TRANSITIONS)
def test_transitions_are_deterministic(kind):
    G.set_canvas(108, 192)
    try:
        img = np.random.default_rng(3).random((192, 108, 3)).astype(np.float32)
        mt = np.zeros((192, 108), np.float32); mt[60:150, 30:80] = 1
        for e in (.15, .6, 1.0):
            for after in (False, True):
                a = CR.transition(kind, img.copy(), e, after, 77, S, mt)
                b = CR.transition(kind, img.copy(), e, after, 77, S, mt)
                assert a.shape == img.shape and np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
                assert np.array_equal(a, b), f"{kind} e={e} after={after} is not deterministic"
        assert np.array_equal(CR.transition(kind, img, 0.0, False, 1, S), img)        # outside the window: untouched
        assert not np.array_equal(CR.transition(kind, img, 1.0, False, 1, S), img)    # on the cut: visibly transformed
    finally:
        G.set_canvas(*G.canvas_of(S))


# ------------------------------------------------------------------ camera moves
def test_camera_moves_are_eased_and_seeded():
    push = [CR.camera(f, {"move": "push", "amount": .1}, S)["z"] for f in np.linspace(0, 1, 11)]
    assert push[0] == 1 and abs(push[-1] - 1.1) < 1e-9 and all(b >= a for a, b in zip(push, push[1:]))
    assert push[1] - push[0] < push[5] - push[4]                                # eased: slow out of the start
    pl = CR.camera(0, {"move": "pan_left"}, S)["px"]; pr_ = CR.camera(1, {"move": "pan_left"}, S)["px"]
    assert pl > 0 > pr_
    a = CR.camera(.37, {"move": "drift"}, S, seed=5, dur=4); b = CR.camera(.37, {"move": "drift"}, S, seed=5, dur=4)
    c = CR.camera(.37, {"move": "drift"}, S, seed=6, dur=4)
    assert a == b and a != c and a["z"] > 1                                      # same seed, same wobble; zoom hides the edges
    with pytest.raises(SystemExit): CR.camera(.5, {"move": "dolly_zoom"}, S)


def test_parallax_layers(tmp_path):
    from PIL import Image
    h, w = 120, 180; img = np.zeros((h, w, 3), np.uint8); img[:] = (90, 120, 160); img[40:90, 70:120] = (230, 200, 60)
    dep = np.zeros((h, w), np.uint8); dep[40:90, 70:120] = 255
    Image.fromarray(img).save(tmp_path / "s.png"); Image.fromarray(dep).save(tmp_path / "d.png")
    fg, bg = CR.parallax_layers(str(tmp_path / "s.png"), str(tmp_path / "d.png"))
    assert fg[65, 95, 3] == 255 and fg[5, 5, 3] == 0                            # the near object is the foreground
    assert abs(int(bg[65, 95, 0]) - 90) < 40                                     # the hole behind it is filled with background


# ------------------------------------------------------------------ match cuts
def test_match_cut_aligns_the_salient_shape():
    def frame(cx, cy, r):
        yy, xx = np.mgrid[0:270, 0:480]; im = np.full((270, 480, 3), 60, np.uint8)
        im[((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r] = (240, 220, 180); return im
    a, b = frame(330, 100, 40), frame(150, 170, 25)
    m = CR.match_transform(a, b, "centroid")
    assert abs(m["ax"] - 330 / 480) < .04 and abs(m["by"] - 170 / 270) < .04
    assert 1.3 < m["scale"] < 1.9 or m["scale"] == 1.6                          # 40 / 25 = 1.6 (clamped to scale_range)
    r, dX, dY = CR.match_view_shift(m, 480, 270)
    # the view centre now shows the canvas point whose transform lands on the outgoing shape
    q = (480 / 2 + dX, 270 / 2 + dY); land = ((q[0] - m["bx"] * 480) * r + m["ax"] * 480, (q[1] - m["by"] * 270) * r + m["ay"] * 270)
    assert abs(land[0] - 240) < 1e-6 and abs(land[1] - 135) < 1e-6
    best = CR.find_in(a, lambda t: frame(150 + 60 * t, 170 - 25 * t, 25 + 5 * t), 0, 3, 1.0, "centroid")
    assert best[0][1] == 3.0                                                     # the in-point whose shape lines up best


def test_schema_knows_the_craft_fields(demo_copy):
    from cves import project, schema
    pr = project.Project(demo_copy); E = pr.edit
    E["cutaways"][0]["in"] = "light_leak"
    E["broll"] = [{"src": "Raw/demo.mp4", "start": 0.0, "end": 1.0, "snap": False, "ramp": {"preset": "slam", "audio": "pitch"}, "camera": {"move": "push"}}]
    pr.save_edit(E); errs, _ = schema.validate(pr)
    assert not [e for e in errs if "broll" in e or "transition" in e], errs
    E["broll"][0]["camera"] = {"move": "dolly"}; E["broll"][0]["ramp"] = {"keys": [[0, 1], [1, -1]]}; pr.save_edit(E)
    errs, _ = schema.validate(pr)
    assert any("camera" in e for e in errs) and any("ramp.keys" in e for e in errs)


# ------------------------------------------------------------------ text behind the speaker (A-roll render path)
def _render_one(pr, f, out):
    from cves import render
    os.makedirs(out, exist_ok=True); render.render(pr, only=[f], out_dir=out, workers=1)
    from PIL import Image
    return np.asarray(Image.open(os.path.join(out, f"{f:05d}.png")).convert("RGB")).astype(np.int16)


def _warped_matte(pr, sid, f):
    from cves import render
    import av
    TL = render.Timeline(pr); s = next(x for x in TL.segs if x["id"] == sid); k = f - s["f0"]
    with av.open(pr.e("plate", f"{sid}.mkv")) as c:
        P = next(fr for j, fr in enumerate(c.decode(video=0)) if j == k).to_ndarray(format="rgb48le").astype(np.float32) / 65535
    with av.open(pr.e("matte", f"{sid}.mkv")) as c:
        A = next(fr for j, fr in enumerate(c.decode(video=0)) if j == k).to_ndarray(format="gray")
    return render.aroll_frame(TL, s, k, f / TL.FPS, P, A)[1]


def test_text_behind_is_occluded_by_the_subject(demo_copy, tmp_path):
    from cves import project
    pr = project.Project(demo_copy); E = pr.edit
    E["chest"] = []; E["roto"] = []; E["cutaways"] = []; E.pop("end_card", None); pr.save_edit(E)
    f = 60; base = _render_one(pr, f, str(tmp_path / "a"))
    E["roto"] = [{"segment": "01_hook_0", "template": "text_behind", "params": {"text": "TWO *SECONDS*", "at": 0.2}}]; pr.save_edit(E)
    withtext = _render_one(pr, f, str(tmp_path / "b"))
    diff = np.abs(withtext - base).max(-1)
    m = _warped_matte(pr, "01_hook_0", f)
    solid = m > .98
    import cv2
    solid = cv2.erode(solid.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)    # 7 px in from the soft (anti-aliased) edge
    assert diff[solid].max() <= 2, "type shows through the subject (the matte must sit on top)"
    assert (diff[m < .02] > 40).sum() > 2000, "no type visible outside the subject"
    ys, xs = np.where(diff > 40)
    assert ys.min() < G.H * .6                                                  # high in the frame, around the head
    assert (diff[solid] <= 2).all() and (m[ys, xs] < .5).mean() > .95            # what shows is the part off the subject


def test_text_behind_without_a_matte_clears_the_face(demo_copy, tmp_path):
    from cves import project, render
    pr = project.Project(demo_copy); E = pr.edit
    E["chest"] = []; E["cutaways"] = []; E.pop("end_card", None)
    E["roto"] = [{"segment": "01_hook_0", "template": "text_behind", "params": {"text": "TWO SECONDS", "at": 0.2}}]; pr.save_edit(E)
    os.remove(pr.e("matte", "01_hook_0.mkv"))                                 # no subject matte for this shot
    f = 60; out = str(tmp_path / "c")
    img = _render_one(pr, f, out)
    TL = render.Timeline(pr); assert TL.matte_ok["01_hook_0"] is False
    from cves.templates import craft as TC
    s = TL.segs[0]; ctx = TL.ctx(s["t0"], s["t1"], **CR.roto_ctx(TL, s, f - s["f0"]))
    els = TC.text_behind(f / TL.FPS, E["roto"][0]["params"], ctx)
    a = np.asarray(els[-1].im)[..., 3]; ys = np.where(a.max(1) > 20)[0]
    assert ys.max() < ctx["face"]["top"] + 1, "with no matte the type must sit clear above the head"
    assert img.shape[0] == G.H


# ------------------------------------------------------------------ the 30 motion pieces
from cves import motion as MO
_ok, _why = MO.available()


@pytest.mark.skipif(not _ok, reason=f"motion renderer unavailable: {_why}")
@pytest.mark.parametrize("size", [(1080, 1920), (1920, 1080)], ids=["portrait", "landscape"])
def test_all_pieces_render_a_frame(size, tmp_path):
    pieces = MO.discover()
    builtin = {n: p for n, p in pieces.items() if p.origin == "builtin"}
    assert len(builtin) >= 30, sorted(builtin)
    page = MO.CHROME.get_page(size); errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    bad = []
    for name, pc in sorted(builtin.items()):
        pv = (pc.meta.get("preview") or {}); params = dict(pv.get("params") or {})
        dur = float(pv.get("duration") or pc.duration)
        job = MO.Job(pc, params, S, size, 10, 0.0, dur, exit=False, root=str(tmp_path))
        folder = tmp_path / name; folder.mkdir()
        errors.clear()
        try: MO._load(page, job, folder)
        except Exception as e: bad.append(f"{name}: load {e}"); continue
        parts = page.evaluate("t => window.__seek(t)", dur * .8) or []
        again = page.evaluate("t => window.__seek(t)", dur * .8) or []
        png = page.screenshot(omit_background=True, type="png")
        from PIL import Image
        import io
        a = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))
        if errors: bad.append(f"{name}: page error {errors[0]}")
        if a.shape[:2] != (size[1], size[0]): bad.append(f"{name}: frame {a.shape}")
        if (a[..., 3] > 200).sum() < 500: bad.append(f"{name}: nothing opaque drawn at t={dur * .8:.2f}")
        if parts != again: bad.append(f"{name}: seek is not pure (same t, different parts)")
        texts = [p for p in parts if p[1]]
        if not texts: bad.append(f"{name}: no text block logged")
        off = [p[0] for p in texts if p[2] < -2 or p[3] < -2 or p[4] > size[0] + 2 or p[5] > size[1] + 2]
        if off and name != "m_ticker": bad.append(f"{name}: text off the canvas {off}")
    assert not bad, "\n".join(bad)
