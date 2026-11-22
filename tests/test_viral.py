"""Viral mode (docs/VIRAL.md): goal layer, platform profiles and the platform sound slot. The slot delivery test reuses
the session demo render."""
import os, json, shutil
import numpy as np, pytest, yaml
from cves import project, style as STY, platforms as PF, schema


def fake_project(tmp, edit=None, timeline=None, elements=None):
    d = os.path.join(str(tmp), "proj"); os.makedirs(os.path.join(d, "Edit"), exist_ok=True)
    with open(os.path.join(d, "Edit", "edit.yaml"), "w", encoding="utf-8") as f: yaml.safe_dump(edit or {}, f)
    if timeline is not None:
        with open(os.path.join(d, "Edit", "timeline.json"), "w", encoding="utf-8") as f: json.dump(timeline, f)
    if elements is not None:
        with open(os.path.join(d, "Edit", "elements.jsonl"), "w", encoding="utf-8") as f: f.writelines(json.dumps(e) + "\n" for e in elements)
    return project.Project(d)

# ------------------------------------------------------------------ goal, presets, platforms
def test_goal_viral_layers_the_viral_preset(tmp_path):
    ad = fake_project(tmp_path / "a", {"goal": "ad"}); vi = fake_project(tmp_path / "v", {"goal": "viral", "style": {"rhythm": {"interrupt_max_s": 3.0}}})
    assert STY.load(ad).get("structure.hook_change_s") == 1.5 and "goal:viral" not in STY.load(ad)["_sources"]
    S = STY.load(vi)
    assert S["_sources"][:2] == ["default", "goal:viral"] and S.get("structure.hook_change_s") == 1.0
    assert S.get("rhythm.interrupt_max_s") == 3.0          # edit.yaml still beats the goal layer

def test_viral_preset_only_uses_known_keys():
    d = yaml.safe_load(open(os.path.join(STY.HERE, "default.yaml"), encoding="utf-8"))
    v = yaml.safe_load(open(os.path.join(STY.HERE, "viral.yaml"), encoding="utf-8"))
    def walk(x, base, p=""):
        for k, val in x.items():
            if k == "name": continue
            assert k in base, f"viral.yaml {p}{k} is not in default.yaml"
            if isinstance(val, dict) and isinstance(base[k], dict): walk(val, base[k], f"{p}{k}.")
    walk(v, d)

@pytest.mark.parametrize("name", PF.names())
def test_platform_zones_scale_with_the_frame(name):
    S = STY.load(extra={"platform": {"target": name}}); pf = PF.profile(S)
    for w, h in ((1080, 1920), (1920, 1080)):
        x0, y0, x1, y1 = PF.safe_zone(S, w, h)
        assert 0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h
        assert abs(x0 - pf["safe"][0] * w) <= 1 and abs(y1 - pf["safe"][3] * h) <= 1        # fractions of THIS frame
    lo, hi, top = PF.duration(S); assert 0 < lo < hi <= top
    assert S.get("sound.master_lufs") == pf["lufs"]

def test_reels_profile_matches_the_v02_zone_and_tiktok_clears_the_rail():
    assert PF.safe_zone(STY.load(), 1080, 1920) == (65, 269, 1015, 1248)                         # no target: legacy box
    assert PF.safe_zone(STY.load(extra={"platform": {"target": "reels"}}), 1080, 1920) == (65, 269, 1015, 1248)
    tk = PF.safe_zone(STY.load(extra={"platform": {"target": "tiktok"}}), 1080, 1920)
    assert tk[2] <= 0.85 * 1080 and tk[3] <= 0.75 * 1920                                         # right rail + bottom caption area
    assert PF.safe_zone(STY.load(), 1920, 1080)[2] <= 1920                                       # legacy box scales too

def test_unknown_platform_is_a_clear_error(tmp_path):
    with pytest.raises(SystemExit): STY.load(extra={"platform": {"target": "myspace"}})
    pr = fake_project(tmp_path, {"style": {"platform": {"target": "myspace"}}})
    errs, _ = schema.validate(pr); assert any("platform.target" in e for e in errs), errs


# ------------------------------------------------------------------ the platform sound slot
def test_platform_slot_validation(tmp_path):
    pr = fake_project(tmp_path / "a", {"music": {"slot": "platform", "guide": 120}})       # an ad may use the slot too
    errs, _ = schema.validate(pr); assert not [e for e in errs if e.startswith(("music", "goal"))], errs
    pr = fake_project(tmp_path / "v", {"goal": "viral", "music": {"slot": "platform"}})
    errs, _ = schema.validate(pr); assert any(e.startswith("music.guide") for e in errs), errs
    pr = fake_project(tmp_path / "w", {"goal": "viral", "music": {"slot": "platform", "guide": "120 bpm"}})
    errs, _ = schema.validate(pr); assert not [e for e in errs if e.startswith(("music", "goal"))], errs
    pr = fake_project(tmp_path / "x", {"goal": "sometimes"})
    errs, _ = schema.validate(pr); assert any(e.startswith("goal") for e in errs), errs

def test_slot_platform_delivers_music_free_master_guide_and_posting(demo_rendered, tmp_path):
    import soundfile as sf
    from cves import mix, encode, deliver
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d)
    pr = project.Project(d); E = pr.edit
    E["goal"] = "viral"; E["music"] = {"slot": "platform", "guide": 100, "sound": "Demo trend sound", "drop_cut": 4.8}
    E.setdefault("style", {})["platform"] = {"target": "tiktok"}; pr.save_edit(E)
    errs, _ = schema.validate(pr); assert not errs, errs
    mix.mix(pr)
    mu, _ = sf.read(pr.e("stems", "music.wav")); assert np.abs(mu).max() < 1e-6            # no music in the mix
    gy, _ = sf.read(pr.e("stems", "guide.wav")); assert np.abs(gy).max() > 0.1             # the click guide at 100 BPM
    encode.encode(pr)
    master = next(os.path.join(d, "Export", f) for f in os.listdir(os.path.join(d, "Export")) if f.endswith(".mp4"))
    final, man = deliver.deliver(pr, only="master")
    files = os.listdir(final)
    assert "POSTING.md" in files and any(f.endswith(".guide.wav") for f in files), files
    post = open(os.path.join(final, "POSTING.md"), encoding="utf-8").read()
    assert "no music on purpose" in post and "Demo trend sound" in post and "100.0 BPM" in post and "0:04.80" in post, post
    assert man["music_slot"]["slot"] == "platform" and man["music_slot"]["platform"] == "tiktok"
