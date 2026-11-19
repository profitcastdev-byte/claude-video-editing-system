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


# ---------------------------------------------------------------- 3. HDR B-roll -> SDR, the A-roll way
def _hdr_clip(path, trc):
    """a synthetic 10-bit clip tagged BT.2020 + PQ (16) or HLG (18) in the H.264 VUI"""
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25:duration=1", "-c:v", "libx264",
                    "-profile:v", "high10", "-pix_fmt", "yuv420p10le", "-bsf:v", f"h264_metadata=colour_primaries=9:transfer_characteristics={trc}:matrix_coefficients=9",
                    path], check=True)


def _rgb_frames(path, vf=None, n=1):
    w, h = 320, 180
    out = subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", path, "-frames:v", str(n), *(["-vf", vf + ",scale=out_color_matrix=bt709:out_range=pc,format=rgb24"] if vf else
                          ["-vf", "scale=in_color_matrix=bt709:out_color_matrix=bt709:out_range=pc,format=rgb24"]), "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(n, h, w, 3)


@pytest.mark.parametrize("trc,name", [(16, "smpte2084"), (18, "arib-std-b67")])
def test_hdr_broll_is_tonemapped_like_aroll(demo_copy, trc, name):
    from cves import ingest as ING, project
    from cves.templates import media as M
    if not (ING._has_filter("zscale") and ING._has_filter("tonemap")): pytest.skip("ffmpeg without zscale/tonemap (fallback path only)")
    pr = project.Project(demo_copy); src = pr.p("Assets", f"hdr_{trc}.mp4"); _hdr_clip(src, trc)
    P = ING.probe_file(src); assert P["hdr"] and P["color_transfer"] == name
    S = STY.load(pr)
    out = ING.sdr_source(src, S, pr.e("conform"))
    assert out != src and out.startswith(pr.e("conform")) and ING.sdr_source(src, S, pr.e("conform")) == out      # cached
    Q = ING.probe_file(out); assert not Q["hdr"] and Q["color_transfer"] == "bt709" and Q["color_primaries"] == "bt709"
    assert M.Clip(out).n == M.Clip(src).n == 25
    # the same chain as A-roll ingest: decoding the proxy == the original through ingest._tonemap_chain
    ref = _rgb_frames(src, ING._tonemap_chain(P, S)[1])[0].astype(np.int16); got = _rgb_frames(out)[0].astype(np.int16)
    assert np.abs(ref - got).mean() < 1.0
    raw = _rgb_frames(src)[0].astype(np.int16); assert np.abs(raw - got).mean() > 5      # and it is not the untouched HDR signal
    # what the templates decode (broll_shot / video_broll / pip panes all go through media_frame)
    ctx = {"project": pr, "fps": 25, "S": S, "resolve": lambda x: x}
    fr, _, _ = M.media_frame(0.4, {"asset": src}, ctx, 0.0)
    assert np.abs(fr[..., :3].astype(np.int16) - M.Clip(out).frame(10)[..., :3]).mean() < .5
    S2 = STY.Style({**S, "ingest": {**S["ingest"], "hdr": {**S["ingest"]["hdr"], "broll": False}}})
    assert ING.sdr_source(src, S2, pr.e("conform")) == src                             # style ingest.hdr.broll: false


def test_sdr_broll_is_left_alone(tmp_path):
    from cves import ingest as ING
    src = str(tmp_path / "sdr.mp4")
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=25:duration=0.4", "-pix_fmt", "yuv420p", src], check=True)
    assert ING.sdr_source(src, STY.load(), str(tmp_path / "c")) == src and not os.path.exists(tmp_path / "c")


# ---------------------------------------------------------------- 4. import-edits: B-roll and motion tracks
def _layers_fixture(pr, clips):
    ctl = pr.p("Export", "control"); os.makedirs(os.path.join(ctl, "media"), exist_ok=True)
    for c in clips:
        p = os.path.join(ctl, c["path"]); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").close()
    man = {"schema": "cves.layers/1", "name": "t", "fps": [30, 1], "size": [1080, 1920], "duration": 20.0, "clips": clips, "captions": [],
           "source": {"segments": [], "edit_sha256": None}}
    json.dump(man, open(os.path.join(ctl, "layers.json"), "w", encoding="utf-8"))
    return ctl


def test_import_edits_maps_broll_and_motion(demo_copy, monkeypatch):
    """B-roll moved / head-trimmed / speed-changed / deleted and motion pieces trimmed map back onto edit.yaml"""
    from cves import project, importer as IM
    pr = project.Project(demo_copy); E = pr.edit
    E["broll"] = [{"src": "Assets/a.mp4", "start": 2.0, "end": 3.0, "in": 1.0, "speed": 0.5, "snap": False},
                  {"src": "Assets/b.mp4", "start": 4.0, "end": 5.0}, {"id": "hero", "src": "Assets/c.mp4", "start": 6.0, "end": 7.0}]
    E["cutaways"].append({"id": "m1", "template": "m_kinetic_title", "start": 8.0, "end": 10.0, "params": {"text": "Hi", "at": 8.0, "duration": 2.0}})
    E["chest"].append({"segment": E["chest"][0]["segment"], "template": "m_lower_third", "params": {"name": "A", "at": 1.0, "duration": 2.5}})
    pr.save_edit(E); kchest = len(E["chest"]) - 1
    L = lambda i, tr, a, b, ref, alpha=False: {"id": i, "track": tr, "path": f"media/{i}.mov", "start": a, "end": b, "source_in": 0.0, "edit_ref": ref, "alpha": alpha}
    _layers_fixture(pr, [L("b01", "V2", 2.0, 3.0, "broll.b01"), L("b02", "V2", 4.0, 5.0, "cutaways.b02"), L("hero", "V2", 6.0, 7.0, "broll.hero"),
                         L("m1", "V2", 8.0, 10.0, "cutaways.m1"), L(f"chest_{kchest}", "V3", 1.0, 3.5, f"chest.{kchest}", True)])
    ctl = pr.p("Export", "control"); P = lambda i, a, b, si=0, sp=None: IM.Placement("V2", "video", os.path.join(ctl, "media", f"{i}.mov"), a, b, si, speed=sp,
                                                                                    effects=[f"speed {sp:g}x"] if sp else [])
    ed = IM.Edited(fps=(30, 1), captions=None, unmapped=[], source="x", placements=[
        P("b01", 66, 90, 6),                 # head trimmed 6 frames (start 2.0 -> 2.2) at speed 0.5: in 1.0 -> 1.1
        P("b02", 135, 165, 0, 2.0),          # moved +15 frames and played at 2x in the editor
        P("m1", 246, 300, 6),                # motion cutaway: head trimmed 6 frames
        IM.Placement("V3", "video", os.path.join(ctl, "media", f"chest_{kchest}.mov"), 30, 90, 0)])   # chest motion piece: tail trimmed 0.5 s
    monkeypatch.setattr(IM, "parse", lambda path, src=None: ed)
    r = IM.import_edits(pr, os.path.join(ctl, "layers.json"))
    B = {(x.get("id") or x["src"]): x for x in r["edit"]["broll"]}
    assert (B["Assets/a.mp4"]["start"], B["Assets/a.mp4"]["end"], B["Assets/a.mp4"]["in"]) == (2.2, 3.0, 1.1)
    assert (B["Assets/b.mp4"]["start"], B["Assets/b.mp4"]["end"], B["Assets/b.mp4"]["speed"]) == (4.5, 5.5, 2.0)
    assert "hero" not in B                                                    # not placed any more: deleted
    m1 = next(c for c in r["edit"]["cutaways"] if c["id"] == "m1")
    assert (m1["start"], m1["end"], m1["params"]["at"], m1["params"]["duration"]) == (8.2, 10.0, 8.2, 1.8)
    ch = r["edit"]["chest"][kchest]["params"]; assert (ch["at"], ch["duration"]) == (1.0, 2.0)
    assert not [n for n in r["not_mapped"] if "b02" in n and "speed" in n], r["not_mapped"]
    assert not [n for n in r["not_mapped"] if f"chest_{kchest}" in n], r["not_mapped"]


# ---------------------------------------------------------------- 5. the full Kdenlive round trip (melt)
def _mlt_clock(frames, fps):
    s = frames * fps[1] / fps[0]; h, rem = divmod(s, 3600); m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{sec:06.3f}"


def test_kdenlive_round_trip(tmp_path):
    """export -> edit project.kdenlive as a person would (move a cutaway, trim a B-roll head, shift a caption) -> melt
    renders it -> import-edits -> edit.yaml has the changes -> the project renders again"""
    import sys, xml.etree.ElementTree as ET, yaml
    from cves.export import kdenlive as KD
    from cves import project, importer as IM, render, mix
    if not KD.find_melt(): pytest.skip("melt not installed (Kdenlive's engine; set CVES_MELT)")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); env = dict(os.environ, PYTHONPATH=os.path.join(root, "engine"))
    d = str(tmp_path / "rt")
    subprocess.run([sys.executable, os.path.join(root, "tools", "make_demo.py"), d, "--small", "--size", "540x960"], check=True, env=env)
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=540x960:rate=30:duration=4", "-pix_fmt", "yuv420p",
                    os.path.join(d, "Assets", "broll_rt.mp4")], check=True)
    pr = project.Project(d); E = pr.edit; s0 = pr.json("edl.json")["segments"][0]; t1 = round(s0["out"] - s0["in"], 3)
    E["broll"] = [{"src": "Assets/broll_rt.mp4", "start": round(t1 - .9, 3), "end": t1, "in": 0.5, "snap": False}]; pr.save_edit(E)
    from cves import encode
    render.render(pr); mix.mix(pr); encode.encode(pr)
    subprocess.run([sys.executable, "-m", "cves.cli", "--project", d, "export", "kdenlive"], check=True, env=env, capture_output=True)
    ctl = pr.p("Export", "control"); kd = os.path.join(ctl, "project.kdenlive"); man = json.load(open(os.path.join(ctl, "layers.json"), encoding="utf-8"))
    fps = tuple(man["fps"]); F = fps[0] / fps[1]; lay = {c["id"]: c for c in man["clips"]}
    assert lay["b01"]["edit_ref"] == "broll.b01" and lay["c2"]["edit_ref"] == "cutaways.c2"
    # ---- the human edit, in the file Kdenlive saves
    tree = ET.parse(kd); r = tree.getroot(); prod = {e.get("id"): e for e in r if e.tag in ("producer", "chain")}
    res = lambda e: next((p.text for p in prod[e.get("producer")].findall("property") if p.get("name") == "resource"), "")
    fr = lambda v: IM._mlt_time(v, fps)
    for pl in r.findall("playlist"):
        if pl.get("id") == "main_bin": continue                                   # the project bin, not the timeline
        items = list(pl)
        for k, it in enumerate(items):
            if it.tag != "entry" or it.get("producer") not in prod: continue
            name = os.path.basename(res(it))
            if name == "b01.mov":         # trim the B-roll head 6 frames: the blank before it grows by 6
                assert items[k - 1].tag == "blank"
                items[k - 1].set("length", _mlt_clock(fr(items[k - 1].get("length")) + 6, fps)); it.set("in", _mlt_clock(6, fps))
            if name == "c2.mov":          # move cutaway c2 6 frames later: a 6-frame blank before it, 6 frames less after
                pl.insert(k, ET.Element("blank", {"length": _mlt_clock(6, fps)}))
                nxt = items[k + 1]; assert nxt.tag == "blank"; nxt.set("length", _mlt_clock(fr(nxt.get("length")) - 6, fps))
    tree.write(kd, encoding="utf-8", xml_declaration=True)
    srt = kd + ".srt"; txt = open(srt, encoding="utf-8").read()
    cap = man["captions"][0]; a, b = cap["start"] - .2, cap["end"] - .2          # shift the first caption 6 frames earlier
    ts = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)):03d}"
    open(srt, "w", encoding="utf-8").write(txt.replace(txt.splitlines()[1], f"{ts(a)} --> {ts(b)}", 1))
    # ---- melt loads and renders the edited project
    out = tmp_path / "check.mp4"; chk = KD.melt_check(__import__("pathlib").Path(kd), render_to=out)
    assert chk["ok"], chk
    # ---- import
    r = IM.import_edits(pr, kd, src="kdenlive")
    E2 = yaml.safe_load(open(pr.e("edit.yaml"), encoding="utf-8"))
    br = E2["broll"][0]; assert abs(br["start"] - (lay["b01"]["start"] + .2)) < .5 / F and abs(br["in"] - 0.7) < 1e-6, (br, r["applied"])
    c2 = next(c for c in E2["cutaways"] if c["id"] == "c2"); assert abs(c2["start"] - (lay["c2"]["start"] + .2)) < .5 / F and c2["snap"] is False, c2
    ev = E2["captions"]["events"]; assert any(abs(e["start"] - round(a, 3)) < .5 / F for e in ev), ev
    assert not [n for n in r["not_mapped"] if "b01" in n or "c2" in n], r["not_mapped"]
    # ---- rebuild
    render.render(project.Project(d)); TL = json.load(open(pr.e("timeline.json"), encoding="utf-8"))
    cuts = {c["id"]: c for c in TL["cutaways"]}
    assert abs(cuts["b01"]["start"] - br["start"]) < .5 / F and abs(cuts["c2"]["start"] - c2["start"]) < .5 / F


def test_4k_media_cards_are_drawn_at_4k(tmp_path):
    """the picture templates (media.py) sample their source and draw their card / mask at the real canvas too"""
    from PIL import Image
    y, x = np.mgrid[0:1600, 0:2400]; src = np.stack([x * 255 // 2400, y * 255 // 1600, (x + y) % 200 + 40], -1).astype(np.uint8)
    src[700:900, 1000:1400] = 255; path = str(tmp_path / "still.png"); Image.fromarray(src).save(path)
    p = {"asset": path, "frame": "card", "label": "THE PLAN", "caption": "step one"}
    def frame(raster, size=(3840, 2160)):
        TPL.RASTER["image"] = raster
        try: els = _draw("image", size, t=1.0, p=p)
        finally: TPL.RASTER["image"] = True
        assert all(e.im.size == size for e in els)
        img = np.zeros((size[1], size[0], 3), np.float32) + .05
        for e in els: img = G.over(img, e.im)
        return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    a, b = frame(True), frame(False)
    assert _sharpness(a) >= 1.3 * _sharpness(b)
    sm = lambda im: np.asarray(im.resize((480, 270), Image.BOX), np.float32)
    assert np.abs(sm(a) - sm(b)).mean() < 2.0                                  # same layout, only sharper
