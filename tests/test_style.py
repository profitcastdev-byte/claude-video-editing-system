import os, yaml
from cves import style as STY, project

def test_default_is_neutral():
    S = STY.load()
    assert S.get("grade.relight") is False and S.get("grade.vignette") == 0
    assert S.get("transitions.in") == "cut" and S.get("grammar.cutaway_share") is None
    assert S["_sources"] == ["default"]

def test_merge_order(demo_copy):
    pr = project.Project(demo_copy)
    e = pr.edit; e["style"] = {"preset": "profitcast-dark", "captions": {"size": 61}}; pr.save_edit(e)
    with open(pr.e("style.yaml"), "w", encoding="utf-8") as f: yaml.safe_dump({"captions": {"size": 55, "position": "center"}, "grade": {"gamma": 1.3}}, f)
    os.makedirs(pr.p("Brand"), exist_ok=True)
    with open(pr.p("Brand", "style.yaml"), "w", encoding="utf-8") as f: yaml.safe_dump({"colors": {"accent": "#FF0000"}, "grade": {"gamma": 1.2}}, f)
    S = STY.load(pr)
    assert S["_sources"] == ["default", "preset:profitcast-dark", "inspire", "brand", "edit.yaml"]
    assert S.get("captions.size") == 61                 # edit.yaml beats everything
    assert S.get("captions.position") == "center"       # inspire beats the preset
    assert S.get("grade.gamma") == 1.2                  # brand beats inspire
    assert S.get("colors.accent") == "#FF0000"
    assert S.get("grade.relight") is True               # from the preset
    assert S.get("captions.style") == "word_reveal"     # untouched default survives deep merge

def test_unknown_preset_is_a_clear_error():
    import pytest
    with pytest.raises(SystemExit): STY.load(preset="no-such-preset")

def test_rgb():
    assert STY.rgb("#0A0B0C") == (10, 11, 12) and STY.rgb([1, 2, 3, 4]) == (1, 2, 3)
