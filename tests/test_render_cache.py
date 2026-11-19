"""Incremental render (cves.rcache): a final render re-renders only the frames whose inputs changed, and what it leaves on
disk (frames, element log, timeline, the encoded master) is the same as a full render of the same edit."""
import os, json, shutil, hashlib, subprocess
import pytest
from cves import project, render, rcache, config as C


def _hashes(d):
    fr = os.path.join(d, "Edit", "frames")
    return {f: hashlib.sha256(open(os.path.join(fr, f), "rb").read()).hexdigest() for f in sorted(os.listdir(fr)) if f.endswith(".png")}

def _read(d, name):
    return open(os.path.join(d, "Edit", name), "rb").read()

def _edit(pr, fn):
    E = pr.edit; fn(E); pr.save_edit(E)

def _change_c2(E):
    next(c for c in E["cutaways"] if c["id"] == "c2")["params"]["label"] = "still watching"

def _video_md5(path):
    return subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", path, "-map", "0:v", "-f", "md5", "-"], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture(scope="module")
def warm(demo_built, tmp_path_factory):
    """a demo copy rendered once with the cache on"""
    d = str(tmp_path_factory.mktemp("rc") / "demo"); shutil.copytree(demo_built, d)
    pr = project.Project(d); render.render(pr)
    assert render.LAST["cached"] == 0 and render.LAST["frames"] == render.LAST["of"]
    return d


def test_unchanged_rebuild_renders_nothing(warm):
    pr = project.Project(warm); before = _hashes(warm); st = os.stat(pr.e("elements.jsonl")).st_mtime_ns
    render.render(pr)
    assert render.LAST["frames"] == 0 and render.LAST["cached"] == render.LAST["of"]
    assert _hashes(warm) == before and os.stat(pr.e("elements.jsonl")).st_mtime_ns == st     # untouched: cue_sync stays valid


def test_non_visual_style_change_renders_nothing(warm):
    pr = project.Project(warm)
    _edit(pr, lambda E: E.setdefault("style", {}).update({"sound": {"bed_lu": -12}}))
    try:
        render.render(pr); assert render.LAST["frames"] == 0
    finally:
        _edit(pr, lambda E: E["style"].pop("sound", None))


def test_one_cutaway_rerenders_its_range_and_equals_a_full_render(warm, demo_built, tmp_path):
    from cves import mix, encode
    pr = project.Project(warm)
    tl = json.load(open(pr.e("timeline.json"), encoding="utf-8")); F = tl["fps"]
    c2 = next(c for c in tl["cutaways"] if c["id"] == "c2"); lo, hi = round(c2["start"] * F), round(c2["end"] * F)
    mix.mix(pr)                                              # the cue sync's pixel scan is cached per frame from here on
    _edit(pr, _change_c2); render.render(pr)
    n = render.LAST["frames"]
    assert 0 < n <= hi - lo, (n, lo, hi)                     # only the cutaway's frames (the change sits inside it)
    assert render.LAST["cached"] == tl["frames"] - n
    # the reference: the same edit rendered from scratch with the cache off
    ref = str(tmp_path / "ref"); shutil.copytree(demo_built, ref); pf = project.Project(ref)
    _edit(pf, _change_c2); render.render(pf, cache=False)
    assert render.LAST["frames"] == render.LAST["of"]
    assert _hashes(warm) == _hashes(ref)
    for f in ("elements.jsonl", "timeline.json"): assert _read(warm, f) == _read(ref, f), f
    render.render(pf); assert render.LAST["frames"] == 0                     # --no-cache re-rendered everything and refreshed the index
    for p in (pr, pf): mix.mix(p)
    assert _read(warm, "mix.wav") == _read(ref, "mix.wav")                   # the reused cue-sync scan places every cue the same
    assert _video_md5(encode.encode(pr)) == _video_md5(encode.encode(pf))     # one master, the same as a full render's


def test_only_render_and_missing_frames_are_rerendered(warm):
    pr = project.Project(warm); render.render(pr)
    TL = render.Timeline(pr); fr = TL.frames_for("c1")
    render.render(pr, only="c1")                             # --only rewrites PNGs, not the element log: forget those frames
    os.remove(pr.e("frames", "00003.png"))
    render.render(pr)
    assert render.LAST["frames"] == len(set(fr) | {3})


def test_keys_follow_code_and_visual_style(warm, monkeypatch):
    pr = project.Project(warm); TL = render.Timeline(pr); k0 = rcache.frame_keys(TL)
    assert len(k0) == TL.N and len(set(k0)) == TL.N
    monkeypatch.setattr(rcache, "code_hash", lambda: "another engine")
    assert all(a != b for a, b in zip(k0, rcache.frame_keys(TL)))
    monkeypatch.undo()
    TL.S = dict(TL.S, grade=dict(TL.S.get("grade") or {}, gain=1.07))
    assert all(a != b for a, b in zip(k0, rcache.frame_keys(TL)))


def test_draft_build_is_small_separate_and_never_delivered(warm, tmp_path):
    from cves import build, deliver
    pr = project.Project(warm); render.render(pr); before = _hashes(warm); stamp = _read(warm, "qc.json") if os.path.exists(pr.e("qc.json")) else None
    v, nf, rep, T = build.build(pr, draft=True, log=lambda *a: None)
    assert os.path.dirname(v) == pr.e("draft") and os.path.exists(pr.e("draft", "qc.json"))
    s = json.loads(subprocess.run([C.get("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", v],
                                  capture_output=True, text=True).stdout)["streams"][0]
    assert (s["width"], s["height"]) == (540, 960)
    assert json.load(open(pr.e("draft", "qc.json"), encoding="utf-8"))["draft"] is True
    assert _hashes(warm) == before                                          # the final build's frames and cache are untouched
    assert (_read(warm, "qc.json") if os.path.exists(pr.e("qc.json")) else None) == stamp
    with pytest.raises(SystemExit, match="draft"): deliver.deliver(pr, video=v, force_unchecked=True)
    cp = str(tmp_path / "renamed.mp4"); shutil.copy(v, cp)                  # moved out of Edit/draft: the container tag still says so
    with pytest.raises(SystemExit, match="draft"): deliver.deliver(pr, video=cp, force_unchecked=True)
    build.build(pr, draft=True, log=lambda *a: None)
    from cves import render as R
    assert R.LAST["frames"] == 0                                            # a second draft of the same plan renders nothing
