"""Any frame size (docs/FORMATS.md): the canvas comes from style canvas.size, every consumer reads G.W / G.H at call time,
spawned render workers re-set it, safe zones follow the aspect, templates lay out on any canvas, and a landscape
voiceover + B-roll edit renders, mixes, encodes and passes QC with 0 FAIL (presenter gates N/A).
The 1080x1920 golden frames (test_render_golden.py) prove the default path did not move."""
import os, json, multiprocessing as mp, numpy as np, pytest
from conftest import build_spine_copy
from cves import gfx as G, style as STY, project, templates as TPL


@pytest.fixture(autouse=True)
def _default_canvas():
    yield
    G.set_canvas(*G.DESIGN)


def test_canvas_from_style_and_edit(demo_copy):
    pr = project.Project(demo_copy)
    assert G.canvas_of(STY.load(pr), pr) == (1080, 1920)                     # the default: unchanged
    E = pr.edit; E["style"] = {"canvas": {"size": [1920, 1080]}}; pr.save_edit(E)
    assert G.canvas_of(STY.load(pr), pr) == (1920, 1080)
    E["project"]["size"] = [1080, 1080]; pr.save_edit(E)                     # edit.yaml project.size wins
    assert G.canvas_of(STY.load(pr), pr) == (1080, 1080)
    with pytest.raises(SystemExit): G.canvas_of(STY.Style({"canvas": {"size": [1081, 1920]}}))


def test_safe_zones_follow_the_aspect():
    S = STY.load()
    assert G.safe_zone(S, (1080, 1920)) == tuple(float(v) for v in S.get("platform.safe_zone"))   # identity at 1080x1920
    z = G.safe_zone(S, (2160, 3840)); assert z == tuple(2 * v for v in S.get("platform.safe_zone"))
    for size in ((1920, 1080), (1080, 1080), (1080, 1350), (1920, 804)):
        x0, y0, x1, y1 = G.safe_zone(S, size)
        assert 0 < x0 < x1 < size[0] and 0 < y0 < y1 < size[1], (size, (x0, y0, x1, y1))
        assert (x1 - x0) / size[0] > .8                                       # wide text area on every aspect


def test_fixed_template_fits_a_landscape_canvas():
    """a third-party module with a hard-coded 1080x1920 layout (DESIGN = True) is fitted (never stretched) into the safe
    zone on 16:9. (The built-in v0.2 cutaways are relative now: tests/test_weak_spots.py)"""
    import types
    from PIL import ImageDraw
    from cves.templates import El
    def box(t, p, ctx):
        im = G.new(); ImageDraw.Draw(im).rectangle((140, 600, 940, 1300), fill=(255, 255, 255, 255)); return [El(im, "fx.box", "cutaway")]
    mod = types.ModuleType("cves_test_fixed"); mod.T = {"_fixed_box": (box, lambda p, ctx: [])}; mod.DESIGN = True; mod.KIND = "cutaway"
    TPL._register(mod, "test")
    try:
        assert TPL.LAYOUT["_fixed_box"] == "fixed"
        G.apply_style(STY.load(), canvas=(1920, 1080)); ctx = {"start": 0.0, "end": 2.0, "fps": 30}
        els = TPL.get("_fixed_box")[0](1.0, {}, ctx)
        assert els and all(el.im.size == (1920, 1080) for el in els)
        z = G.safe(); b = els[0].im.getbbox()
        assert z[0] - 2 <= b[0] and b[2] <= z[2] + 2 and z[1] - 2 <= b[1] and b[3] <= z[3] + 2, (b, z)
        assert abs((b[2] - b[0]) / (b[3] - b[1]) - 800 / 700) < .03                 # one uniform scale: no stretch
        a, _, _ = TPL._fit_for("_fixed_box", box, {}, ctx)
        assert 0 < a <= 1.0                                                       # never upscaled
    finally:
        for d in (TPL.REGISTRY, TPL.KIND, TPL.SOURCE, TPL.LAYOUT, TPL.RASTER): d.pop("_fixed_box", None)


def _probe_canvas(_): return (G.W, G.H)

def test_canvas_reset_inside_spawned_workers(spine_demo):
    """spawn re-imports every module: the worker's canvas must come from its initializer (render._init), not the default"""
    from cves import render
    d = spine_demo("voiceover", "480x270")
    G.set_canvas(1080, 1920)
    with mp.get_context("spawn").Pool(1) as p:                               # no initializer: the module default
        assert p.apply(_probe_canvas, (0,)) == (1080, 1920)
    with render.Pool(1, initializer=render._init, initargs=(d,)) as p:      # what render uses
        assert p.apply(render.canvas_of_worker) == (480, 270)


def test_square_canvas_captions_inside_safe_zone(spine_demo, tmp_path):
    """the same voiceover edit on a 1:1 canvas (B-roll needs no re-ingest): every caption sits inside the 1:1 safe zone"""
    import shutil
    from cves import render
    d = str(tmp_path / "sq"); shutil.copytree(spine_demo("voiceover", "480x270"), d); pr = project.Project(d)
    E = pr.edit; E["style"] = {"canvas": {"size": [360, 360]}}; pr.save_edit(E)
    TL = render.Timeline(pr); assert TL.size == (360, 360)
    z = G.safe_zone(TL.S); n = 0
    for f in range(0, TL.A_FRAMES, 9):
        img, recs = render.compose(TL, f)
        assert img.shape[:2] == (360, 360)
        for r in recs:
            if r["role"] != "caption": continue
            n += 1; x0, y0, x1, y1 = r["bbox"]
            assert z[0] - 1 <= x0 and x1 <= z[2] + 1 and z[1] - 1 <= y0 and y1 <= z[3] + 1, (f, r["bbox"], z)
    assert n > 5


def test_reframe_from_any_master():
    from cves import variants as V
    S = STY.load()
    g = V.reframe_geometry("9:16", 1920, 1080, S); assert g["axis"] == "x" and g["out"] == (608, 1080)       # landscape -> vertical: crop the width
    g = V.reframe_geometry("1:1", 1920, 1080, S); assert g["axis"] == "x" and g["out"] == (1080, 1080)
    g = V.reframe_geometry("2.39:1", 1920, 1080, S); assert g["axis"] == "y" and g["out"][0] == 1920 and g["out"][1] < 1080
    g = V.reframe_geometry("16:9", 1080, 1920, S); assert g["wide"] and g["out"] == (1920, 1080)          # the v0.2 path: unchanged
    with pytest.raises(SystemExit): V.reframe_geometry("16:9", 1920, 1080, S)


def test_landscape_voiceover_broll_builds_and_passes_qc(spine_demo, tmp_path):
    from cves import qc, config as C
    import subprocess
    pr, v = build_spine_copy(spine_demo("voiceover", "480x270"), str(tmp_path / "vo"))
    s = json.loads(subprocess.run([C.get("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                   "-of", "json", v], capture_output=True, text=True).stdout)["streams"][0]
    assert (s["width"], s["height"]) == (480, 270)
    nf, rep = qc.run(pr, v, fast=True); st = pr.json("qc.json")
    assert nf == 0, rep
    by = {g["id"]: g["status"] for g in st["gates"]}
    for gid in ("FRAME-01", "FRAME-04", "COL-06", "CUT-05", "RET-22"): assert by.get(gid) == "N/A", (gid, by.get(gid))
    for gid in ("PLAT-02", "PLAT-04", "PLAT-08", "SND-04", "MOT-14", "DEL-01"): assert by.get(gid) in ("PASS", "WARN"), (gid, by.get(gid))
    assert st["na"] >= 15
    TL = pr.json("timeline.json"); assert TL["spine"] == "voiceover" and TL["size"] == [480, 270]
    els = [json.loads(l) for l in open(pr.e("elements.jsonl"), encoding="utf-8")]
    shots = [e for e in els if e["id"].startswith("broll.")]
    assert shots and all(e["bbox"] == [0, 0, 479, 269] for e in shots)      # every B-roll frame fills the canvas (fill and fit)
    from cves import deliver                                                 # reframe the landscape master to 9:16 (crop the width)
    out, man = deliver.deliver(pr, "9:16")
    v916 = next(x for x in man["variants"] if x["id"] == "9x16")
    assert v916["status"] == "delivered", v916
    from cves import moodboard
    moodboard.moodboard(pr)
    from PIL import Image
    im = Image.open(pr.p("Moodboard", "frames", sorted(os.listdir(pr.p("Moodboard", "frames")))[0]))
    assert abs(im.width / im.height - 16 / 9) < .02                          # moodboard keeps the canvas aspect


def test_broll_rotated_phone_clip_is_upright(tmp_path):
    """a phone clip stored on its side with a display rotation flag is decoded upright by the B-roll reader (as ffmpeg shows it)"""
    import subprocess
    from cves import config as C
    from cves.templates import media
    up, side, flag = (str(tmp_path / f) for f in ("up.mp4", "side.mp4", "flag.mp4"))
    ff = lambda *a: subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", *a], check=True)
    ff("-f", "lavfi", "-i", "color=c=gray:s=180x320:d=0.5,drawbox=x=0:y=0:w=60:h=60:c=red:t=fill", "-pix_fmt", "yuv420p", up)
    ff("-i", up, "-vf", "transpose=2", "-pix_fmt", "yuv420p", side)
    try: ff("-display_rotation:v:0", "-90", "-i", side, "-c", "copy", flag)
    except subprocess.CalledProcessError: pytest.skip("this ffmpeg cannot write a display rotation flag")
    a = media.Clip(flag).frame(0)
    assert a.shape[:2] == (320, 180) and a[10, 10, 0] > 150 and a[10, 10, 1] < 100, (a.shape, a[10, 10])
