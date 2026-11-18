from cves import project, schema

def test_demo_is_valid(demo_copy):
    errs, warns = schema.validate(project.Project(demo_copy))
    assert errs == [], errs

def test_errors_carry_a_path(demo_copy):
    pr = project.Project(demo_copy); e = pr.edit
    e["cutaways"][0]["template"] = "checklst"                 # typo
    e["cutaways"][1]["params"]["value"] = "abc"               # wrong type
    e["roto"][0]["segment"] = "nope_0"                        # unknown segment
    errs, _ = schema.validate(pr, edit=e); text = "\n".join(map(str, errs))
    assert "cutaways[0]" in text and "checklist" in text      # did-you-mean
    assert "cutaways[1].params.value" in text
    assert "roto[0].segment" in text

def test_render_refuses_an_invalid_edit(demo_copy):
    import pytest
    pr = project.Project(demo_copy); e = pr.edit; e["cutaways"][0]["template"] = "nope"; pr.save_edit(e)
    with pytest.raises(SystemExit): schema.require_valid(pr)
