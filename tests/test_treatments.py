"""Treatments (docs/TREATMENTS.md): built-in definitions, the treatment style layer, measurably different plans on both
demo spines, project overrides, pick (promote + journal + mining) and proxy renders at half size."""
import json, os, shutil, subprocess, sys
import pytest, yaml

from cves import project as PRJ, style as STY, treatments as TR, learn

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NAMES = ["punchy", "cinematic", "minimal"]


def _ydump(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: yaml.safe_dump(d, f, sort_keys=False)


def test_builtins_are_valid():
    cat = TR.catalogue()
    assert set(NAMES) <= set(cat)
    d = learn.default_style()
    assert set(d["treatments"]["offer"]) == set(NAMES)
    for n in NAMES:
        T = yaml.safe_load(open(cat[n], encoding="utf-8"))
        assert T["name"] == n and T.get("label") and T.get("summary")
        assert TR.check(T, n) == [], TR.check(T, n)
    bad = {"name": "x", "style": {"captions": {"nope": 1}}, "structure": {"transitions": "swirl", "foo": 1}}
    errs = TR.check(bad, "x")
    assert any("captions.nope" in e for e in errs) and any("swirl" in e for e in errs) and any("structure.foo" in e for e in errs)


def test_treatment_layer_sits_after_inspire_before_brand(demo_copy):
    pr = PRJ.Project(demo_copy)
    _ydump(pr.e("style.yaml"), {"captions": {"size": 40, "style": "box"}, "motion": {"energy": .1}})
    _ydump(pr.e("treatment.yaml"), {"name": "t1", "style": {"captions": {"size": 58, "style": "pop"}, "motion": {"energy": .9}}})
    S = STY.load(pr)
    assert S.get("captions.size") == 58 and S.get("captions.style") == "pop" and S.get("motion.energy") == .9      # beats inspire
    src = S["_sources"]; assert src.index("inspire") < src.index("treatment:t1")
    _ydump(pr.p("Brand", "style.yaml"), {"captions": {"size": 70}})
    S = STY.load(pr)
    assert S.get("captions.size") == 70 and S.get("captions.style") == "pop"                                          # brand wins
    assert S["_sources"].index("treatment:t1") < S["_sources"].index("brand")
    E = pr.edit; E["style"] = dict(E.get("style") or {}, captions={"style": "karaoke"}); pr.save_edit(E)
    assert STY.load(pr).get("captions.style") == "karaoke"                                                            # edit.yaml wins
    from cves import schema
    _ydump(pr.e("treatment.yaml"), {"name": "t1", "style": {"captions": {"sizee": 58}}})
    _, warns = schema.validate(pr)
    assert any(w.startswith("Edit/treatment.yaml") and "sizee" in w for w in warns), warns


def _assert_distinct(ms):
    cuts = [ms[n]["cuts"] for n in NAMES]
    caps = [ms[n]["caption_style"] for n in NAMES]
    trs = [tuple(sorted(ms[n]["transitions"])) for n in NAMES]
    assert len(set(cuts)) == 3, f"cut counts not distinct: {dict(zip(NAMES, cuts))}"
    assert len(set(caps)) == 3, f"caption styles not distinct: {dict(zip(NAMES, caps))}"
    assert len(set(trs)) == 3, f"transition families not distinct: {dict(zip(NAMES, trs))}"


def test_plans_differ_on_the_aroll_demo(demo_copy):
    pr = PRJ.Project(demo_copy); base = TR.metrics(pr)
    rows = TR.make(pr)
    assert [r["name"] for r in rows] == NAMES
    ms = {r["name"]: r["metrics"] for r in rows}
    _assert_distinct(ms)
    assert ms["punchy"]["cuts"] > base["cuts"] > ms["minimal"]["cuts"]          # denser / sparser than the base plan
    assert ms["punchy"]["punch_ins"] == 1 and ms["minimal"]["roto"] == 0 and ms["minimal"]["cutaways"] < base["cutaways"]
    assert ms["punchy"]["transitions"].get("whip") and ms["cinematic"]["transitions"].get("fade") and not ms["minimal"]["transitions"]
    assert ms["punchy"]["bed_lu"] > ms["cinematic"]["bed_lu"] > ms["minimal"]["bed_lu"]
    assert "m_stat_counter" in ms["punchy"]["motion_pieces"]
    # the plan the treatment folder holds: a valid edit, its own treatment layer, the base edit untouched
    from cves import schema
    for n in NAMES:
        v = TR.variant(pr, n)
        assert v.edit["treatment"] == n and v.e("plates") == pr.e("plates") and v.e("edit.yaml") != pr.e("edit.yaml")
        S = STY.load(v); assert f"treatment:{n}" in S["_sources"]
        errs, _ = schema.validate(v); assert not errs, (n, errs)
        P = json.load(open(os.path.join(v.work, "plan.json"), encoding="utf-8")); assert P["changes"] and P["metrics"]["cuts"] == ms[n]["cuts"]
    assert "treatment" not in pr.edit and "treatment:punchy" not in STY.load(pr)["_sources"]
    # the hook punch-in keeps CUT-05: its level differs from the next shot's by min_step
    sn = TR.variant(pr, "punchy").edit["aroll"]["snap"]; S = STY.load(TR.variant(pr, "punchy"))
    assert sn["zoom"] < 1.4 and sn["zoom"] / (1 + S.get("framing.creep")) >= S.get("framing.min_step")
    assert learn.read_journal(pr)[-1]["event"] == "treatments-make"


def test_plans_differ_on_the_voiceover_demo(spine_demo, tmp_path):
    d = str(tmp_path / "vo"); shutil.copytree(spine_demo("voiceover", "1920x1080"), d)
    pr = PRJ.Project(d); base = TR.metrics(pr)
    ms = {r["name"]: r["metrics"] for r in TR.make(pr)}
    _assert_distinct(ms)
    assert ms["cinematic"]["mean_shot_s"] > base["mean_shot_s"] and ms["cinematic"]["cuts"] < base["cuts"]
    cap = STY.load(TR.variant(pr, "cinematic")).get("grammar.max_shot_s")
    for x in TR.variant(pr, "cinematic").edit["broll"]:          # holds never break the pacing gate
        assert float(x["end"]) - float(x["start"]) <= cap + 1e-6
    tr = [x.get("transition", "cut") for x in TR.variant(pr, "punchy").edit["broll"]]
    assert 0 < tr.count("whip") < len(tr)                        # whips on sentence starts only, not on every shot


def test_project_treatments_override_and_add(demo_copy):
    pr = PRJ.Project(demo_copy)
    _ydump(pr.p("treatments", "punchy.yaml"), {"name": "punchy", "label": "Our punchy", "summary": "client cut", "style": {"captions": {"style": "one_word"}},
                                               "structure": {"transitions": "glitch"}})
    _ydump(pr.p("treatments", "docu.yaml"), {"label": "Docu", "summary": "observational", "style": {"captions": {"style": "box"}}, "structure": {"transitions": "cut", "roto": "drop"}})
    assert TR.load(pr, "punchy")["label"] == "Our punchy" and TR.load(pr, "punchy")["_source"] == "project"
    assert TR.ordered(pr) == NAMES + ["docu"]
    ms = {r["name"]: r["metrics"] for r in TR.make(pr, "punchy,docu")}
    assert ms["punchy"]["caption_style"] == "one_word" and set(ms["punchy"]["transitions"]) == {"glitch"} and ms["docu"]["roto"] == 0
    _ydump(pr.p("treatments", "bad.yaml"), {"style": {"captions": {"colour": "red"}}})
    with pytest.raises(SystemExit): TR.load(pr, "bad")
    with pytest.raises(SystemExit): TR.load(pr, "nope")
    # a learned / style preference puts its treatment first
    E = pr.edit; E["style"] = dict(E.get("style") or {}, treatments={"prefer": "minimal"}); pr.save_edit(E)
    assert TR.ordered(pr)[0] == "minimal"


def test_pick_promotes_journals_and_feeds_learning(demo_copy, tmp_path):
    pr = PRJ.Project(demo_copy); old = open(pr.e("edit.yaml"), encoding="utf-8").read()
    TR.make(pr, "punchy,minimal")
    r = TR.pick(pr, "minimal")
    assert open(pr.e("edit.yaml"), encoding="utf-8").read() == open(os.path.join(TR.tdir(pr, "minimal"), "edit.yaml"), encoding="utf-8").read()
    assert any(os.path.basename(b).startswith("edit.yaml.bak-") and open(b, encoding="utf-8").read() == old for b in r["backups"])
    assert pr.edit["treatment"] == "minimal" and os.path.exists(pr.e("treatment.yaml"))
    S = STY.load(pr); assert "treatment:minimal" in S["_sources"] and S.get("captions.style") == "highlight"
    ev = learn.read_journal(pr)[-1]
    assert ev["event"] == "treatment-pick" and ev["treatment"] == "minimal" and set(ev["offered"]) == {"punchy", "minimal"} and ev["metrics"]["cuts"]
    assert learn.facts(pr)["treatment"] == "minimal"
    # mining: the same treatment picked twice for one client -> a treatments.prefer candidate scoped to that client
    info = lambda k: {"dir": f"/x/{k}", "name": k, "client": "Acme", "goal": "viral", "platform": None, "ref": f"Acme/{k}"}
    pickev = lambda t: {"event": "treatment-pick", "treatment": t, "offered": NAMES, "client": "Acme", "goal": "viral"}
    data = [(info("a"), [pickev("cinematic")]), (info("b"), [pickev("cinematic")]), (info("c"), [pickev("punchy")])]
    c = {x["scope"]: x for x in learn.treatment_picks(data)}
    assert c["client:Acme"]["change"] == {"key": "treatments.prefer", "value": "cinematic"} and c["client:Acme"]["n"] == 3
    assert "goal:viral" in c and learn.is_style_key("treatments.prefer")
    assert not learn.treatment_picks([(info("a"), [pickev("cinematic")]), (info("b"), [pickev("punchy")])])     # no majority, no candidate
    # the cli: `cves treatments pick` on an unknown treatment is a one-line error
    rp = subprocess.run([sys.executable, "-m", "cves.cli", "--project", demo_copy, "treatments", "pick", "cinematic"], capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "engine")))
    assert rp.returncode != 0 and "cves treatments make cinematic" in rp.stderr and "Traceback" not in rp.stderr


def _probe(f): return TR._probe_size(f)[:2]


def test_proxy_renders_are_half_size_and_compare(demo_copy):
    """the A-roll path (plates + mattes resized as they decode) and the comparison sheet; the main Edit/ is untouched"""
    pr = PRJ.Project(demo_copy)
    from cves import gfx as G
    w, h = G.canvas_of(STY.load(pr), pr)
    TR.make(pr, "minimal,punchy")
    for n, f in TR.render(pr, "minimal,punchy", workers=2):
        assert _probe(f) == (w // 2, h // 2), (n, _probe(f))
        tl = json.load(open(os.path.join(TR.tdir(pr, n), "timeline.json"), encoding="utf-8"))
        assert tl["size"] == [w // 2, h // 2] and tl["proxy"] == [.5, .5]
        assert not os.path.isdir(os.path.join(TR.tdir(pr, n), "frames"))
    assert not os.path.exists(pr.e("timeline.json")) and not os.path.isdir(pr.e("frames"))          # the project itself is not rendered
    rec = TR.compare(pr)
    assert [t["name"] for t in rec["treatments"]] == ["punchy", "minimal"] and len(rec["timecodes"]) == 6
    from PIL import Image
    with Image.open(rec["sheet"]) as im: assert im.width > 6 * 100 and im.height > 2 * 100
    cw, ch = _probe(rec["video"]); assert (cw, ch) == (2 * (w // 2), h // 2)                         # portrait: side by side
