"""Timeline spines (docs/FORMATS.md): voiceover / music / broll edits and the broll: track, on synthetic media only.
Music cuts land on the beat grid, the clip's own sound reaches the mix, face-only stages skip,
the VO ingest tightens pauses, and the aroll spine takes B-roll from the same track."""
import os, json, shutil, subprocess, numpy as np, pytest, soundfile as sf
from conftest import build_spine_copy
from cves import gfx as G, project, schema, spines as SP, config as C


@pytest.fixture(autouse=True)
def _default_canvas():
    yield
    G.set_canvas(*G.DESIGN)


def test_spine_and_broll_validation(spine_demo, tmp_path):
    d = str(tmp_path / "v"); shutil.copytree(spine_demo("voiceover", "480x270"), d); pr = project.Project(d)
    e, w = schema.validate(pr); assert not e, e
    E = pr.edit; E["spine"] = "podcast"; pr.save_edit(E)
    assert any(x.startswith("spine:") for x in schema.validate(pr)[0])
    E["spine"] = "voiceover"; E["broll"][1]["start"] = 0.5                  # overlaps shot 0
    E["broll"][2]["src"] = "Assets/broll_city.mp4"                          # both src and asset
    E["broll"][3]["framing"] = "stretch"; pr.save_edit(E)
    errs = " ".join(schema.validate(pr)[0])
    assert "overlaps broll[0]" in errs and "exactly one of src" in errs and "broll[3].framing" in errs, errs


def _gaps(wav, mx=.25):
    """pauses longer than mx s between speech (10 ms RMS windows within 38 dB of the peak)"""
    y, sr = sf.read(wav); y = y.mean(1) if y.ndim > 1 else y
    hop = int(.01 * sr); r = np.array([np.sqrt(np.mean(y[i:i + 2 * hop] ** 2)) for i in range(0, len(y) - 2 * hop, hop)])
    db = 20 * np.log10(r + 1e-9); idx = np.where(db > max(db.max() - 38, -55))[0]
    return [(a * .01, (b - a) * .01) for a, b in zip(idx[:-1], idx[1:]) if (b - a) * .01 > mx]

def test_voiceover_ingest_tightens_pauses(tmp_path):
    """a VO with long pauses -> voice_final.wav without gaps > 0.25 s, voice_raw.wav as recorded, edl.json on the voiceover spine"""
    d = tmp_path / "vo"; [os.makedirs(d / x) for x in ("Edit", "Assets", "Raw")]
    sr = 48000; t = np.arange(int(sr * .6)) / sr; word = (np.sin(2 * np.pi * 180 * t) * np.hanning(len(t)) * .5).astype(np.float32)
    gap = np.zeros(int(sr * 1.1), np.float32); y = np.concatenate([gap[:4800], word, gap, word, gap, word, gap[:9600]])
    sf.write(str(d / "Assets" / "vo.wav"), y, sr)
    pr = project.Project(str(d)); pr.save_edit({"project": {"title": "vo"}, "spine": "voiceover", "voiceover": {"file": "Assets/vo.wav"}})
    info = SP.ingest_voiceover(pr, words=False)
    assert info["pieces"] == 3 and info["tight_s"] < info["vo_s"] - 2.0, info
    assert not _gaps(pr.e("voice_final.wav"))
    edl = pr.json("edl.json"); assert edl["spine"] == "voiceover" and edl["segments"] == [] and abs(edl["duration"] - sf.info(pr.e("voice_final.wav")).duration) < .01
    assert [s["name"] for s in pr.json("voice_chain.json")["steps"]][:2] == ["extract", "pause_tighten"]
    assert "skipped" in SP.ingest_voiceover(pr, words=False)                 # unchanged inputs: nothing redone


def test_music_spine_cuts_land_on_beats(spine_demo, tmp_path):
    from cves import beats as BT, render
    src = spine_demo("music", "480x270"); pr0 = project.Project(src)
    TL = render.Timeline(pr0); P = BT.plan(pr0, TL, need_beats=True); grid = np.array(P["downbeats"])
    starts = [s["start"] for s in pr0.edit["broll"]][1:]
    assert starts and all(np.min(np.abs(grid - s)) <= 1 / TL.FPS + 1e-6 for s in starts), (starts, grid[:6])
    assert TL.zoom == {} and TL.roto == {} and TL.caps == []                  # no presenter, no voice: no punch-ins, no captions
    track, info = SP.autocut(pr0, every="beats", min_shot=1.0, folder="Assets")
    beats = np.array(P["beats"])
    assert all(np.min(np.abs(beats - x["start"])) <= 1e-3 for x in track[1:]) and all(b["start"] - a["start"] >= 1.0 - 1e-6 for a, b in zip(track, track[1:]))
    pr, v = build_spine_copy(src, str(tmp_path / "mu"))
    assert os.path.getsize(v) > 0 and pr.json("timeline.json")["spine"] == "music"


def test_broll_spine_with_native_audio(spine_demo, tmp_path):
    from cves import mix, render
    pr, v = build_spine_copy(spine_demo("broll", "480x270"), str(tmp_path / "br"))
    TL = render.Timeline(pr); cues = mix.all_cues(TL)
    own = [c for c in cues if c[1].startswith("asset:")]
    assert len(own) == 2 and all(c[3].get("trim") for c in own)              # two shots carry their own sound
    sx, _ = sf.read(pr.e("stems", "sfx.wav")); vo, _ = sf.read(pr.e("stems", "voice.wav"))
    assert np.abs(sx).max() > 1e-3 and np.abs(vo).max() == 0                  # clip sound in the mix, no voice
    segs = pr.json("timeline.json")["segments"]
    assert [s["kind"] for s in segs] == ["broll"] * 5 and sum(s["n"] for s in segs) == pr.json("timeline.json")["a_frames"]


def test_aroll_spine_takes_broll_from_the_track(demo_copy):
    """mixed: the talking-head demo + one broll: shot (a rotated-free 4:3 test clip) = a cutaway with captions over it"""
    from cves import render
    clip = os.path.join(demo_copy, "Raw", "cityscape.mp4")
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1440x1080:rate=25", "-t", "3", "-pix_fmt", "yuv420p", clip], check=True)
    pr = project.Project(demo_copy); E = pr.edit
    t0 = 1.0                                                                  # inside the hook, before the first drawn cutaway
    E["broll"] = [{"src": "Raw/cityscape.mp4", "start": t0, "end": t0 + 1.2, "in": 0.5, "framing": "fit", "snap": False}]; pr.save_edit(E)
    assert not schema.validate(pr)[0]
    TL = render.Timeline(pr); c = TL.in_cut(t0 + .5)
    assert c and c.get("broll") and c["template"] == "broll_shot"
    f = round((t0 + .6) * TL.FPS); img, recs = render.compose(TL, f)
    roles = {r["role"] for r in recs}
    assert "media" in roles and "caption" in roles, roles                     # B-roll picture + the captions continue over it
    assert img.shape[:2] == (1920, 1080)


def test_voiceover_ingest_is_idempotent(spine_demo, tmp_path):
    """regression: `cves ingest` again on a voiceover project changes nothing (same voice_final, words, edl, timeline),
    so the broll: track still fits"""
    import hashlib
    from cves import cli, render
    d = str(tmp_path / "vo"); shutil.copytree(spine_demo("voiceover", "480x270"), d); pr = project.Project(d)
    sha = lambda f: hashlib.sha256(open(pr.e(f), "rb").read()).hexdigest()
    before = {f: sha(f) for f in ("voice_final.wav", "voice_raw.wav", "words.json")}; T0 = render.Timeline(pr).T_END
    for _ in range(2): cli.main(["--project", d, "ingest"])
    assert {f: sha(f) for f in before} == before
    assert render.Timeline(pr).T_END == T0 and not schema.validate(pr)[0]
    E = pr.edit; E["voiceover"]["tighten"] = False; pr.save_edit(E)            # a changed setting is redone
    assert "skipped" not in SP.ingest_voiceover(pr, words=False)
