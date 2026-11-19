"""WS E: journal -> mining -> human-approved promotion -> learned style layer; taste study; critique pack. Synthetic data only."""
import json, os, subprocess, sys
import pytest, yaml

from cves import learn, project, style as STY, config as C

CLIENTS = ("Acme Bakery", "Zenith Dental", "Orbit Gym", "Nova Optics")


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "projects"; kb = tmp_path / "repo" / "knowledge-base"
    (kb / "taste").mkdir(parents=True); root.mkdir()
    (tmp_path / "repo" / "LESSONS.md").write_text("# Lessons\n\n| # | Correction | Now enforced by |\n|---|---|---|\n| 1 | a | b |\n", encoding="utf-8")
    monkeypatch.setenv("CVES_CLIENTS", str(root)); monkeypatch.setenv("CVES_TASTE", str(tmp_path / "taste")); monkeypatch.setenv("CVES_KB_DIR", str(kb))
    return {"root": str(root), "kb": str(kb), "tmp": tmp_path}


def _proj(env, client, title, goal=None, **edit):
    d = project.new(client, title, root=env["root"]); pr = project.Project(d)
    E = pr.edit
    if goal: E["goal"] = goal
    E.update(edit); pr.save_edit(E); return pr


def _facts(**kw):
    f = {"transitions.in": "cut", "captions.size": 50, "sound.bed_lu": -10, "templates": ["stat"]}; f.update(kw); return f


def _fleet(env, n=4):
    """n projects (different clients, goal viral): each had captions raised by a human in the editor, then was delivered + rated"""
    prs = []
    for i in range(n):
        pr = _proj(env, CLIENTS[i], f"Video {i}", goal="viral", style={"captions": {"size": 50}})
        E0 = pr.edit; E1 = json.loads(json.dumps(E0)); E1["style"]["captions"]["size"] = 56 + i
        learn.on_import(pr, E0, {"edit": E1, "applied": ["caption size"], "not_mapped": []})
        whip = i < n - 1
        learn.append(pr, "deliver", version="v001", facts=_facts(**{"transitions.in": "whip" if whip else "cut"}))
        learn.append(pr, "rate", version="v001", score=8.5 if whip else 4.0, by="owner")
        learn.append(pr, "note", text="the music is too quiet, make it louder")
        prs.append(pr)
    return prs


def test_hooks_journal_and_never_break(env, capsys):
    pr = _proj(env, "Acme Bakery", "Hooks")
    learn.on_build(pr)                                            # first build: facts, snapshot
    learn.append(pr, "note", text="bigger captions please")
    E = pr.edit; E["style"] = {"captions": {"size": 60}}; pr.save_edit(E)
    learn.on_build(pr)                                            # revision after a note
    ev = learn.read_journal(pr); kinds = [e["event"] for e in ev]
    assert kinds == ["build", "note", "revision", "build"], kinds
    rev = ev[2]; assert rev["after_notes"] and any(c["path"] == "style.captions.size" and c["new"] == 60 for c in rev["changes"])
    assert all(e["cves"] and e["t"] for e in ev) and "style_hash" in ev[0]
    assert ev[0]["facts"]["captions.size"] == 50 and ev[3]["facts"]["captions.size"] == 60
    # a broken project must not break the command that journals
    E["style"] = {"preset": "no-such-preset"}; pr.save_edit(E)
    assert learn.on_qc(pr) is None and learn.on_deliver(pr, {"version": "v002"}) is None
    os.chmod(pr.e(), 0o500) if os.name != "nt" else None
    try: assert learn.on_build(pr) is None                         # unwritable Edit/: logged, not raised
    finally: os.chmod(pr.e(), 0o700) if os.name != "nt" else None
    assert "journal skipped" in capsys.readouterr().err
    # the CLI path
    from cves import cli
    with pytest.raises(SystemExit) as e: cli.main(["--project", pr.root, "learn", "results", "v001", "--platform", "meta", "--hook-rate", "0.31", "ctr=0.02"])
    assert e.value.code == 0
    r = learn.read_journal(pr)[-1]; assert r["event"] == "results" and r["metrics"] == {"hook_rate": 0.31, "ctr": 0.02} and r["platform"] == "meta"


def test_mine_finds_corrections_correlations_notes(env):
    _fleet(env, 4)
    cands, rep = learn.mine()
    by = {(c["kind"], (c.get("change") or {}).get("key")): c for c in cands}
    corr = by[("correction", "captions.size")]
    assert corr["n"] == 4 and corr["type"] == "style" and corr["change"]["value"] >= 56 and corr["scope"] == "goal:viral"
    cor = by[("correlation", "transitions.in")]
    assert cor["change"]["value"] == "whip" and cor["n"] == 4 and cor["effect"] > 4 and cor["confidence"] > 0
    notes = by[("notes", "sound.bed_lu")]
    assert notes["change"]["value"] == -8 and notes["n"] == 4
    assert os.path.exists(os.path.join(env["tmp"], "taste", "candidates.jsonl"))


def test_mine_refuses_small_samples(env):
    _fleet(env, 2)
    cands, rep = learn.mine()
    assert not [c for c in cands if c["kind"] == "correlation"]
    assert any("n=2" in r and "< 3" in r for r in rep), rep


def test_promote_applies_only_in_scope_and_forget_reverts(env):
    _fleet(env, 4); cands, _ = learn.mine()
    cid = next(c["id"] for c in cands if c["kind"] == "correlation" and c["change"]["key"] == "transitions.in")
    learn.promote(cid)                                            # scope goal:viral, personal layer
    L = yaml.safe_load(open(os.path.join(env["tmp"], "taste", "learned.yaml"), encoding="utf-8"))
    assert L["scopes"]["goal:viral"]["transitions"]["in"] == "whip"
    viral = _proj(env, "Acme Bakery", "Viral one", goal="viral"); ad = _proj(env, "Acme Bakery", "Ad one", goal="ad"); plain = _proj(env, "Acme Bakery", "Plain")
    S = STY.load(viral); assert S.get("transitions.in") == "whip" and "learned:personal" in S["_sources"]
    src = S["_sources"]; assert src[0] == "default" and src.index("learned:personal") == 1 + ("goal:viral" in src)   # after default (+ the viral goal layer), before preset/inspire/brand/edit
    for p in (ad, plain):
        S = STY.load(p); assert S.get("transitions.in") == "cut" and "learned:personal" not in S["_sources"]
    E = viral.edit; E["style"] = {"preset": "profitcast-dark"}; viral.save_edit(E)   # the preset beats the learned layer
    S = STY.load(viral); assert [x for x in S["_sources"] if x != "goal:viral"][:3] == ["default", "learned:personal", "preset:profitcast-dark"]
    with pytest.raises(SystemExit): learn.promote(cid)            # already promoted
    learn.forget(cid)
    assert "learned:personal" not in STY.load(viral)["_sources"]
    L = yaml.safe_load(open(os.path.join(env["tmp"], "taste", "learned.yaml"), encoding="utf-8"))
    assert "goal:viral" not in (L.get("scopes") or {}) and cid not in (L.get("_promoted") or {})
    assert next(c for c in learn.read_candidates() if c["id"] == cid)["status"] == "new"


def test_promote_validates_style_keys(env):
    _fleet(env, 4); cands, _ = learn.mine()
    c = next(c for c in cands if c["type"] == "style"); c["change"]["key"] = "captions.no_such_key"
    learn._write_jsonl(os.path.join(env["tmp"], "taste", "candidates.jsonl"), [c])
    with pytest.raises(SystemExit, match="not a key"): learn.promote(c["id"])


def test_share_is_anonymised(env):
    _fleet(env, 4); cands, _ = learn.mine()
    one = _proj(env, "Solo Client", "Only")                        # a client-scoped candidate cannot be shared
    style_c = next(c for c in cands if c["kind"] == "correction" and c["change"]["key"] == "captions.size")
    rule_c = next(c for c in cands if c["type"] == "rule" or c["kind"] == "notes")
    learn.promote(style_c["id"], scope="global", share=True)
    if rule_c["type"] != "rule":                                   # force a rule-type candidate through the LESSONS path
        rule_c = dict(rule_c, type="rule", rule="Check music first: notes keep asking for it. (Acme Bakery said so)", id="Ltest001")
        learn._write_jsonl(os.path.join(env["tmp"], "taste", "candidates.jsonl"), learn.read_candidates() + [rule_c])
    learn.promote(rule_c["id"], scope="goal:viral", share=True)
    shared = [os.path.join(env["kb"], "TASTE.md"), os.path.join(env["kb"], "taste", "learned.yaml"), os.path.join(env["tmp"], "repo", "LESSONS.md")]
    text = "".join(open(p, encoding="utf-8").read() for p in shared)
    for name in CLIENTS + ("Solo Client",):
        assert name.lower() not in text.lower(), name
    assert env["root"] not in text and str(env["tmp"]) not in text and "Video 0" not in text
    assert style_c["id"] in text and rule_c["id"] in text and "| 2 |" in text
    assert yaml.safe_load(open(shared[1], encoding="utf-8"))["scopes"]["global"]["captions"]["size"] == style_c["change"]["value"]
    learn._write_jsonl(os.path.join(env["tmp"], "taste", "candidates.jsonl"),
                       learn.read_candidates() + [dict(style_c, id="Lclient1", scope="client:Solo Client", status="new")])
    with pytest.raises(SystemExit, match="stays local"): learn.promote("Lclient1", share=True)
    learn.forget(style_c["id"])                                   # shared forget removes the entry and the key
    assert style_c["id"] not in open(shared[0], encoding="utf-8").read()
    assert not (yaml.safe_load(open(shared[1], encoding="utf-8")).get("scopes") or {}).get("global")
    assert one


def test_reject_is_not_proposed_again(env):
    _fleet(env, 4); cands, _ = learn.mine()
    cid = cands[0]["id"]
    assert learn.main(["reject", cid, "--why", "not my taste"]) == 0
    cands2, rep = learn.mine()
    assert cid not in {c["id"] for c in cands2} and any("rejected before" in r for r in rep)


def _clip(path, colors=("red", "blue", "green", "white"), seg=0.8, size="180x320", audio=True):
    ff = C.get("ffmpeg"); n = len(colors)
    ins = []
    for c in colors: ins += ["-f", "lavfi", "-i", f"color=c={c}:s={size}:d={seg}:r=25"]
    if audio: ins += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seg * n}"]
    fc = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    cmd = [ff, "-v", "error", "-y"] + ins + ["-filter_complex", fc, "-map", "[v]"] + (["-map", f"{n}:a", "-c:a", "aac"] if audio else []) + \
          ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest", str(path)]
    subprocess.run(cmd, check=True); return str(path)


def test_study_measures_synthetic_clips(env):
    tdir = env["tmp"] / "_Taste"; tdir.mkdir()
    lines = []
    for i in range(3):
        _clip(tdir / f"great{i}.mp4"); lines.append(f"great{i}.mp4 | viral | fast colour changes {i}")
    _clip(tdir / "ad0.mp4"); lines.append("ad0.mp4 | ad | one ad only")
    (tdir / "notes.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out, new = learn.study(str(tdir), max_s=10)
    st = json.load(open(os.path.join(env["tmp"], "taste", "study.json"), encoding="utf-8"))
    assert st["kinds"]["viral"]["n"] == 3 and st["kinds"]["ad"]["n"] == 1
    m = st["kinds"]["viral"]["metrics"]; assert m["cuts"] >= 2 and m["median_shot_s"] < 1.5
    assert not any(str(tdir) in json.dumps(f) for f in st["files"])            # measurements only: names, no paths, no media
    assert not [f for f in os.listdir(os.path.join(env["tmp"], "taste")) if f.endswith(".mp4")]
    assert any(c["scope"] == "goal:viral" for c in new) and not any(c["scope"] == "goal:ad" for c in new)
    assert any("ad" in l and "< 3" in l for l in out)


def test_critique_pack_on_tiny_video(env):
    pr = _proj(env, "Acme Bakery", "Critique")
    os.makedirs(pr.p("Export"), exist_ok=True); _clip(pr.p("Export", "Critique.mp4"), size="270x480")
    from cves.critique import critique
    r = critique(pr)
    for k in ("sheet", "timeline", "md"): assert os.path.getsize(r[k]) > 1000, k
    md = open(r["md"], encoding="utf-8").read()
    for word in ("Hook strength", "Story clarity", "Pacing", "Visual aesthetics", "Motion craft", "Sound design", "Creativity", "Restraint",
                 "Platform fit", "Brand fit", "3 changes", "--by claude"):
        assert word in md, word
    assert r["facts"]["shots"] >= 3 and learn.read_journal(pr)[-1]["event"] == "critique"
    assert learn.main(["rate", "master", "7", "--by", "claude", "--scores", "hook=7,story=6", "--project", pr.root]) == 0
    assert learn.read_journal(pr)[-1]["scores"] == {"hook": 7.0, "story": 6.0}


def test_critique_counts_broll_footage_as_shots_not_graphics():
    from cves import critique as CR

    class _P:
        edit = {}
        def json(self, name, default=None):
            return {"cutaways": [{"id": "b01", "template": "broll_shot", "start": 0.0, "end": 2.0},
                                 {"id": "b02", "template": "broll_shot", "start": 2.0, "end": 4.0},
                                 {"id": "c1", "template": "m_kinetic_title", "start": 1.0, "end": 3.0}]} if name == "timeline.json" else default
    shots, gfx, _ = CR.structure(_P(), 4.0)[:3]
    assert [g[2] for g in gfx] == ["c1"]                       # only the designed graphic counts toward the restraint budget
    assert any(abs(s[0] - 2.0) < 1e-6 for s in shots)          # the B-roll cut at 2.0 s is a shot boundary


def test_team_layer_shared_folder(env, monkeypatch, tmp_path):
    """--team writes to a shared folder every editor points at; it merges between the repo and the personal layer"""
    _fleet(env, 4); cands, _ = learn.mine()
    cid = next(c["id"] for c in cands if c["kind"] == "correlation" and c["change"]["key"] == "transitions.in")
    with pytest.raises(SystemExit, match="no team layer"): learn.promote(cid, team=True)
    team = tmp_path / "Shared Drive" / "taste"; monkeypatch.setenv("CVES_TEAM_TASTE", str(team))
    with pytest.raises(SystemExit, match="pick one"): learn.promote(cid, share=True, team=True)
    learn.promote(cid, team=True)
    L = yaml.safe_load(open(team / "learned.yaml", encoding="utf-8"))
    assert L["scopes"]["goal:viral"]["transitions"]["in"] == "whip" and L["_promoted"][cid]["by"]
    assert not os.path.exists(os.path.join(env["tmp"], "taste", "learned.yaml")) or "goal:viral" not in (yaml.safe_load(open(os.path.join(env["tmp"], "taste", "learned.yaml"), encoding="utf-8")) or {}).get("scopes", {})
    viral = _proj(env, "Acme Bakery", "Viral team", goal="viral")
    src = STY.load(viral)["_sources"]; assert "learned:team" in src and STY.load(viral).get("transitions.in") == "whip"
    assert [n for n, _ in STY.learned_paths()] == ["repo", "team", "personal"]
    learn.forget(cid)
    assert "learned:team" not in STY.load(viral)["_sources"]
