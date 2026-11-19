"""WS F: the review loop (`cves review`). Synthetic media only: a two-shot clip drawn in numpy, with seeded defects
(a black frame at the cut, a duplicated frame, an audio pop, music over the voice, a caption a frame off the cut)."""
import json, os, shutil, subprocess, sys
import numpy as np, pytest, soundfile as sf, yaml

from cves import config as C, learn, project, review as RV

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W, H, FPS, CUT = 270, 480, 30, 60          # 4 s, one cut at frame 60 (2.0 s)
SR = 48000


def _frames(black_at=None, dup_at=None, static_s=0.0):
    yy, xx = np.mgrid[0:H, 0:W]; rng = np.random.default_rng(0); tex = rng.integers(0, 40, (H, W + 400)).astype(np.float32)
    out = []
    for f in range(120):
        sh = 0 if f < static_s * FPS else f * 3
        base = 150 if f < CUT else 105
        t = np.roll(tex, -sh, axis=1)[:, :W] + (xx * .1 if f < CUT else yy * .05)
        im = np.clip(base + t - 20, 0, 255)
        rgb = np.stack([im, im * (.9 if f < CUT else 1.05), im * (1.1 if f < CUT else .8)], -1).clip(0, 255).astype(np.uint8)
        out.append(rgb)
    if dup_at is not None: out[dup_at] = out[dup_at - 1].copy()
    if black_at is not None: out[black_at] = np.zeros_like(out[0])
    return out


def _audio(pop=False):
    t = np.arange(4 * SR) / SR; y = .2 * np.sin(2 * np.pi * 220 * t)
    if pop: y[int(2.0 * SR):] += .35          # a DC step exactly on the cut: the classic click of a hard audio edit
    return np.stack([y, y], 1).astype(np.float32)


def _write_video(path, frames, audio):
    wav = path + ".wav"; sf.write(wav, audio, SR)
    cmd = [C.get("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", path]
    subprocess.run(cmd, input=b"".join(f.tobytes() for f in frames), check=True); os.remove(wav)


EDIT = """# a hand-written edit: this comment must survive `cves review apply`
project:
  client: Acme Bakery
  title: Review test
music:
  file: Music/bed.wav   # the bed
  bed_lu: -10
end_card:
  template: end_card
  duration: 0.5         # too short on purpose
  params: {headline: Hi}
"""


@pytest.fixture
def proj(tmp_path, monkeypatch):
    monkeypatch.setenv("CVES_TASTE", str(tmp_path / "taste"))
    def make(black_at=None, dup_at=None, pop=False, static_s=0.0, edit=EDIT):
        d = project.new("Acme Bakery", "Review test", root=str(tmp_path / "projects")); pr = project.Project(d)
        with open(pr.e("edit.yaml"), "w", encoding="utf-8") as f: f.write(edit)
        _write_video(pr.p("Export", "Review test.mp4"), _frames(black_at, dup_at, static_s), _audio(pop))
        pr.save_json("timeline.json", {"spine": "aroll", "fps": FPS, "fps_rational": [FPS, 1], "size": [W, H], "frames": 120, "a_frames": 105,
                                       "segments": [{"id": "a", "t0": 0.0, "t1": 2.0, "kind": "aroll"}, {"id": "b", "t0": 2.0, "t1": 3.5, "kind": "aroll"}],
                                       "cutaways": [], "transitions": []})
        return pr
    return make


def kinds(r, sev=None): return [x["kind"] for x in r["findings"] if sev is None or x["severity"] == sev]


def test_seeded_black_frame_at_cut_is_found(proj):
    r = RV.build(proj(black_at=CUT + 1))
    fl = [x for x in r["findings"] if x["kind"] == "flash_frame"]
    assert fl and fl[0]["severity"] == "high" and fl[0]["cut"] == 1 and abs(fl[0]["t"] - (CUT + 1) / FPS) < 1e-3, r["findings"]
    for k in ("index", "hook", "payoff", "endcard"): assert os.path.getsize(r["paths"][k]) > 2000, k
    assert len(r["paths"]["cuts"]) == 2 and os.path.getsize(r["paths"]["cuts"][0]) > 2000
    md = open(r["md"], encoding="utf-8").read()
    assert "Ready to show the owner: NO" in md and "Rubric" in md and "flash_frame" in md and "signoff" in md


def test_clean_cut_has_no_picture_findings(proj):
    pr = proj()
    with open(pr.e("elements.jsonl"), "w", encoding="utf-8") as f:     # a graphic entering at 0.5 s: the hook has its interrupt
        for fr in range(15, 50): f.write(json.dumps({"f": fr, "id": "title", "role": "title", "alpha": 1.0, "text": "Hi"}) + "\n")
    r = RV.build(pr)
    assert not {"flash_frame", "freeze_frame", "audio_pop", "dead_hook", "caption_cut"} & set(kinds(r)), r["findings"]
    a = json.load(open(os.path.join(r["dir"], "audio.json"), encoding="utf-8"))
    assert a["integrated_lufs"] is not None and a["sections"][0]["name"] == "hook" and len(a["cuts"]) == 2


def test_duplicate_frame_and_audio_pop(proj):
    r = RV.build(proj(dup_at=CUT + 1, pop=True))
    assert "freeze_frame" in kinds(r), r["findings"]
    pop = [x for x in r["findings"] if x["kind"] == "audio_pop"]
    assert pop and abs(pop[0]["t"] - 2.0) < 1e-3, r["audio"]["cuts"]


def test_dead_hook_and_qc_dedupe(proj):
    pr = proj(static_s=2.0)
    assert "dead_hook" in kinds(RV.build(pr), "high")
    sha = RV._sha(pr.p("Export", "Review test.mp4"))      # QC already says it: one finding (the gate), not two
    pr.save_json("qc.json", {"video": pr.p("Export", "Review test.mp4"), "sha256": sha, "fail": 1, "warn": 0, "pass": 0,
                             "gates": [{"id": "RET-24", "status": "FAIL", "summary": "first interrupt 2.0 s"}]})
    r = RV.build(pr)
    hooks = [x for x in r["findings"] if x["kind"] == "dead_hook"]
    assert len(hooks) == 1 and hooks[0].get("gate") == "RET-24" and r["qc_fail"] == 1


def test_caption_change_a_frame_after_the_cut(proj):
    pr = proj()
    with open(pr.e("elements.jsonl"), "w", encoding="utf-8") as f:
        for fr in range(0, 100):
            f.write(json.dumps({"f": fr, "id": "cap@0" if fr <= CUT else "cap@2", "role": "caption", "alpha": 1.0, "text": "one" if fr <= CUT else "two"}) + "\n")
    r = RV.build(pr)
    c = [x for x in r["findings"] if x["kind"] == "caption_cut"]
    assert c and c[0]["severity"] == "med" and c[0]["cut"] == 1


def test_music_masking_and_safe_apply_keeps_comments(proj):
    pr = proj(); os.makedirs(pr.e("stems"))
    rng = np.random.default_rng(1); n = 4 * SR
    from scipy.signal import butter, sosfilt
    sos = butter(4, [1000, 4000], "bandpass", fs=SR, output="sos")
    voice = sosfilt(sos, rng.standard_normal(n)) * .05; music = sosfilt(sos, rng.standard_normal(n)) * .2      # music 12 dB over the voice band
    sf.write(pr.e("stems", "voice.wav"), voice.astype(np.float32), SR); sf.write(pr.e("stems", "music.wav"), music.astype(np.float32), SR)
    pr.save_json("words.json", [[0.2, 1.8, "hello"], [2.2, 3.4, "there"]])
    r = RV.build(pr)
    m = next(x for x in r["findings"] if x["kind"] == "music_masks_voice")
    assert m["severity"] == "high" and m["patch"]["safe"] and m["patch"]["set"]["music.bed_lu"] < -10
    e = next(x for x in r["findings"] if x["kind"] == "end_card")
    assert e["patch"] == {"set": {"end_card.duration": 1.0}, "safe": True}
    res = RV.apply(pr)
    assert {a["kind"] for a in res["applied"]} == {"music_masks_voice", "end_card"} and os.path.exists(res["backup"])
    text = open(pr.e("edit.yaml"), encoding="utf-8").read(); E = yaml.safe_load(text)
    assert E["end_card"]["duration"] == 1.0 and E["music"]["bed_lu"] == m["patch"]["set"]["music.bed_lu"]
    assert "this comment must survive" in text and "# the bed" in text, text          # text patch, not a re-dump
    assert RV.apply(pr)["applied"] == []                                                  # recorded: never applied twice
    ev = [e_["event"] for e_ in learn.read_journal(pr)]
    assert "review" in ev and "review-apply" in ev
    st = RV.load_state(pr); assert set(st["rounds"][-1]["applied"]) == {a["id"] for a in res["applied"]}


def test_unsafe_patches_are_never_applied():
    E = {"cutaways": [{"id": "c1", "start": 1.0, "end": 2.0}]}
    RV.apply_patch(E, {"set": {"cutaways[c1].end": 2.033}}); assert E["cutaways"][0]["end"] == 2.033
    RV.apply_patch(E, {"append": {"transitions": {"t": 2.0, "kind": "fade"}}}); assert E["transitions"] == [{"t": 2.0, "kind": "fade"}]
    with pytest.raises(KeyError): RV.apply_patch(E, {"set": {"cutaways[c9].end": 1}})


def test_round_cap_and_signoff(proj):
    pr = proj(black_at=CUT)
    r1 = RV.build(pr); assert r1["round"] == 1 and not r1["cap_reached"]
    assert RV.build(pr)["round"] == 1                     # the same render again: the same round, not a new one
    def new_render():                                     # simulate a re-render (a different master)
        st = RV.load_state(pr); st["rounds"][-1]["sha256"] = "x" * 64; RV.save_state(pr, st)
    new_render(); assert RV.build(pr)["round"] == 2
    new_render(); r3 = RV.build(pr); assert r3["round"] == 3 and r3["cap_reached"]
    assert "Round cap reached" in open(r3["md"], encoding="utf-8").read()
    new_render()
    with pytest.raises(SystemExit, match="round cap reached"): RV.build(pr)
    with pytest.raises(SystemExit): RV.signoff(pr, "ship", "")          # notes are required: what is still wrong
    s = RV.signoff(pr, "revise", "black frame at the cut is a renderer fault")
    assert s["verdict"] == "revise" and any(o["kind"] == "flash_frame" for o in s["open"])
    j = learn.read_journal(pr)[-1]; assert j["event"] == "review-signoff" and j["open"] and j["notes"]
    st = RV.load_state(pr); assert st["loop"] == 2 and st["rounds"] == [] and len(st["history"]) == 1
    r = RV.build(pr); assert r["round"] == 1 and os.path.basename(r["dir"]) == "r004"     # a new loop; packs are never overwritten
    assert "round 1/3" in RV.show(pr)


def test_cli_review(proj):
    pr = proj()
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "engine"))
    run = lambda *a: subprocess.run([sys.executable, "-m", "cves.cli", "--project", pr.root, "review", *a], capture_output=True, text=True, env=env)
    r = run("show"); assert r.returncode == 0 and "no review round" in r.stdout
    r = run("build"); assert r.returncode == 0 and "review round 1/3" in r.stdout, r.stdout + r.stderr
    r = run("apply", "--dry-run"); assert r.returncode == 0 and "would apply" in r.stdout, r.stdout + r.stderr
    r = run("signoff"); assert r.returncode != 0 and "verdict" in (r.stdout + r.stderr)
    r = run("signoff", "--verdict", "ship", "--notes", "end card short"); assert r.returncode == 0 and "signed off" in r.stdout, r.stdout + r.stderr


def test_review_on_the_rendered_demo_finds_a_seeded_black_frame(demo_rendered, tmp_path):
    """the real render path: copy the demo master, black out the first frame after its first A-roll cut, review it"""
    d = str(tmp_path / "demo"); shutil.copytree(demo_rendered, d); pr = project.Project(d)
    tl = pr.json("timeline.json"); fps = tl["fps"]
    fc = int(round(tl["segments"][1]["t0"] * fps))
    src = sorted(f for f in os.listdir(pr.p("Export")) if f.endswith(".mp4"))[0]; v = pr.p("Export", src); tmp = v + ".tmp.mp4"
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-i", v, "-vf", f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='eq(n,{fc + 1})'",
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy", tmp], check=True)
    os.replace(tmp, v)
    r = RV.build(pr)
    fl = [x for x in r["findings"] if x["kind"] == "flash_frame"]
    assert fl and abs(fl[0]["t"] - (fc + 1) / fps) < 1.5 / fps and fl[0]["severity"] == "high", r["findings"]
    assert any(x["kind"] == "qc_missing" or x["kind"] == "qc_stale" for x in r["findings"])     # the loop needs QC on this render
    assert len(r["paths"]["cuts"]) >= 3
