"""Inspire v2 (hear / feel / see / mix-and-match) on synthetic references (tests/_inspire_refs.py): a 120 BPM click track
cut exactly on the beat that loops, the same music cut half a beat late, and a voice over a bed."""
import os, sys, subprocess, shutil
import pytest, yaml

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


pytestmark = pytest.mark.xdist_group("inspire_v2")      # the module fixture is built once, on one worker (--dist loadgroup)


@pytest.fixture(scope="module")
def proj(tmp_path_factory):
    import _inspire_refs as R
    from cves import project, inspire
    d = tmp_path_factory.mktemp("insp") / "proj"; (d / "Edit").mkdir(parents=True)
    R.make_all(str(d / "Inspirations"))
    pr = project.Project(str(d))
    out = inspire.run(pr, dry_run=False, max_s=30)
    return pr, out


def _ref(pr, lab):
    from cves import inspire
    p = os.path.join(pr.e("inspire", "cache"), lab + ".pkl"); assert os.path.exists(p), p
    import pickle
    with open(p, "rb") as f: return pickle.load(f)[1]


def test_cut_on_beat(proj):
    pr, _ = proj
    on, off = _ref(pr, "onbeat")["feel"]["cut_on_beat"], _ref(pr, "offbeat")["feel"]["cut_on_beat"]
    assert on["ratio"] >= .9 and on["n"] >= 8, on
    assert off["ratio"] <= .2, off
    assert on["ratio"] > 2 * on["chance"]


def test_tempo_and_voice(proj):
    pr, _ = proj
    h = _ref(pr, "onbeat")["hear"]
    assert abs(h["tempo"]["bpm"] - 120) <= 2, h["tempo"]
    assert h["voice"]["present"] is False and h["music"]["present"] is True       # music-only clip: no voice
    v = _ref(pr, "voice")["hear"]
    assert v["voice"]["present"] is True and v["music"]["present"] is True
    assert abs(v["tempo"]["bpm"] - 96) <= 2 and -25 < v["gap_lu"] < -3


def test_loop_seam(proj):
    pr, _ = proj
    assert _ref(pr, "onbeat")["feel"]["loop"]["loop"] is True
    assert _ref(pr, "offbeat")["feel"]["loop"]["loop"] is False
    assert _ref(pr, "voice")["feel"]["loop"]["loop"] is False


def test_hook_and_interrupts(proj):
    pr, _ = proj
    f = _ref(pr, "onbeat")["feel"]
    assert abs(f["hook"]["first_cut_s"] - 1.0) <= .07 and f["interrupts"]["max_s"] <= 1.1
    assert _ref(pr, "voice")["feel"]["interrupts"]["max_s"] > 2


def test_report_sheets_and_style(proj):
    pr, out = proj
    d = pr.e("inspire"); rep = open(os.path.join(d, "REPORT.md"), encoding="utf-8").read()
    for lab in ("onbeat", "offbeat", "voice"):
        p = os.path.join(d, f"{lab}-sheet.jpg"); assert os.path.getsize(p) > 5000
        assert f"## " in rep and lab in rep and f"{lab}-sheet.jpg" in rep
    assert "## The mix" in rep and "Cut on beat" in rep and "Loop seam" in rep
    rv = open(os.path.join(d, "aesthetic-review.md"), encoding="utf-8").read()
    assert "What to steal" in rv and "## onbeat" in rv
    import cv2
    im = cv2.imread(os.path.join(d, "onbeat-sheet.jpg")); assert im.shape[0] > im.shape[1] > 500      # 4 x 3 vertical tiles
    from cves import style as STY
    S = STY.load(pr)
    assert S["_sources"][-1] == "inspire"
    mix = out["_inspire"]["mix"]
    assert set(mix) >= {"pacing", "sound", "structure"} and all("source" in v for v in mix.values())
    assert out["_inspire"]["aesthetics"]["onbeat"]["orientation"] == "vertical"


def test_refs_yaml_rank_decides_a_disagreement(proj):
    pr, _ = proj
    from cves import inspire
    ry = os.path.join(pr.p("Inspirations"), "refs.yaml")
    try:
        for first, second in (("offbeat", "onbeat"), ("onbeat", "offbeat")):
            with open(ry, "w", encoding="utf-8") as f:
                yaml.safe_dump({"refs": {f"{first}.mp4": {"rank": 1, "kind": "viral"}, f"{second}.mp4": {"rank": 2}, "voice.mp4": {"rank": 3}}}, f)
            out = inspire.run(pr, dry_run=True, max_s=30)
            m = out["_inspire"]["mix"]["pacing"]
            assert m["consistency"] < .6 and m["source"] == first, m
            exp = 1.0 if first == "onbeat" else 0.0
            assert abs(out["rhythm"]["cut_on_beat"] - exp) <= .2
        # authority beats rank
        with open(ry, "w", encoding="utf-8") as f:
            yaml.safe_dump({"onbeat.mp4": {"rank": 1}, "voice.mp4": {"rank": 3, "use": ["pacing"]}}, f)
        out = inspire.run(pr, dry_run=True, max_s=30)
        assert out["_inspire"]["mix"]["pacing"]["source"] == "voice" and "authority" in out["_inspire"]["mix"]["pacing"]["rule"]
    finally:
        if os.path.exists(ry): os.remove(ry)


def test_mix_override(proj, capsys):
    pr, _ = proj
    from cves import inspire
    out = inspire.run(pr, dry_run=True, max_s=30, mix="pacing=voice,structure=offbeat")
    mx = out["_inspire"]["mix"]
    assert mx["pacing"]["source"] == "voice" and mx["pacing"]["rule"] == "forced by --mix"
    assert mx["structure"]["source"] == "offbeat" and out["structure"]["loop"] is False
    txt = capsys.readouterr().out
    assert "PACING" in txt and "forced by --mix" in txt and "onbeat" in txt     # the per-dimension table, candidates per ref
    with pytest.raises(SystemExit): inspire.run(pr, dry_run=True, mix="pacing=nosuchref")
    with pytest.raises(SystemExit): inspire.run(pr, dry_run=True, mix="vibes=onbeat")


def test_cli_flags(proj):
    pr, _ = proj
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "engine") + os.pathsep + os.environ.get("PYTHONPATH", ""))
    r = subprocess.run([sys.executable, "-m", "cves.cli", "inspire", pr.root, "--dry-run", "--max-s", "30", "--mix", "grade=onbeat,pacing=offbeat"],
                       capture_output=True, text=True, env=env, cwd=ROOT, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "per-dimension mix" in r.stdout and "(cached)" in r.stdout


def test_agreement_and_decide_units():
    from cves import inspire_mix as MX, style as STY
    from cves.inspire import Evidence
    assert MX.agreement([1.0, 1.0]) == 1 and MX.agreement([1.0, 3.0]) < .2
    assert MX.agreement(["#FF0000", "#FE0101"]) > .9 and MX.agreement(["#FF0000", "#0000FF"]) == 0
    assert MX.agreement(["cut", "cut", "whip"]) == pytest.approx(2 / 3)
    assert MX.dim_of("captions.size") == "captions" and MX.dim_of("rhythm.cut_on_beat") == "pacing" and MX.dim_of("rhythm.tempo_bpm") == "sound"
    a, b = Evidence(), Evidence()
    a.put("transitions.in", "whip", "x", 5, .9); b.put("transitions.in", "fade", "y", 5, .9)
    a.put("transitions.whip_s", .2, "x", 5, .9)
    pooled = Evidence(); pooled.put("transitions.in", "whip", "p", 10, .9)
    ev, plan, rows = MX.decide({"A": a, "B": b}, pooled, {"B": {"rank": 1}, "A": {"rank": 2}}, STY.load())
    assert plan["motion"]["source"] == "B" and ev.keys["transitions.in"] == "fade" and "transitions.whip_s" not in ev.keys   # B's look kept whole
    ev, plan, _ = MX.decide({"A": a, "B": b}, pooled, {}, STY.load(), forced={"motion": "A"})
    assert ev.keys["transitions.in"] == "whip" and ev.keys["transitions.whip_s"] == .2
