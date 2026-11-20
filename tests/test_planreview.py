"""Edit plan review (docs/PLAN-REVIEW.md): quick actions -> exact edit.yaml edits, locks, the notes round-trip, the local
server (127.0.0.1 only), the page with and without the server, and changed-shot detection between rounds."""
import copy, json, os, shutil, threading, urllib.request, urllib.error
import pytest, yaml

from cves import planreview as PR
from cves.project import Project

EDIT = """\
# the plan, hand-written (this comment must survive apply-notes)
captions:
  auto: true
  fixes: {}
cutaways:
  - id: c1     # the problem list
    template: checklist
    start: 2.5
    end: 4.0
    params:
      title: "Why people swipe"
      at: 2.6
      size: 60
      items:
        - {text: "Long intros", at: 2.8}
  - id: c2
    template: stat
    start: 5.0
    end: 6.5
    params: {value: 90, suffix: "%", count: [5.2, 1.2], label: keep watching, label_at: 5.4}
  - id: c3
    template: card_list
    start: 7.0
    end: 8.0
    params: {label: Steps, items: []}
roto:
  - {segment: s5, template: kinetic_caption_emphasis, params: {word: TODAY, at: 9.2}}
chest:
  - {segment: s1, template: lower_third, params: {name: Alex, at: 1.6}}
broll:
  - {id: shotA, src: Raw/a.mp4, start: 3.0, end: 4.0}
aroll:
  zoom: {s2: 1.1}
end_card:
  template: end_card
  duration: 2.0
  params: {headline: Hi}
"""


def _proj(tmp_path, text=EDIT):
    root = tmp_path / "proj"; (root / "Edit").mkdir(parents=True); (root / "Moodboard").mkdir()
    (root / "Edit" / "edit.yaml").write_text(text, encoding="utf-8")
    return Project(str(root))


def _E(): return yaml.safe_load(EDIT)


def _ref(E, slot, i=None, **kw):
    """a shot ref as the plan writes it (planreview.ref_for)"""
    return PR.ref_for(E, slot, i, **kw)


def _notes(pr, shots, **kw):
    E = pr.edit
    d = {"version": PR.NOTES_VERSION, "overall": kw.get("overall", ""), "approve_all": kw.get("approve_all", False), "shots": []}
    for n, (key, refs, extra) in enumerate(shots, 1):
        d["shots"].append({"n": n, "key": key, "kind": "cutaway", "start": 0, "end": 1, "refs": refs, "target": 0,
                           "approved": False, "unlock": False, "note": "", "actions": [], **extra})
    return d


# ------------------------------------------------------------------ quick actions (pure: dict in, dict out)
def test_bigger_and_smaller_change_the_size_param_only():
    E = _E(); before = copy.deepcopy(E)
    r = PR.apply_action(E, _ref(E, "cutaways", 0), {"op": "bigger"})
    assert r["changed"] and E["cutaways"][0]["params"]["size"] == pytest.approx(66)
    before["cutaways"][0]["params"]["size"] = E["cutaways"][0]["params"]["size"]; assert E == before   # nothing else moved
    PR.apply_action(E, _ref(E, "cutaways", 0), {"op": "smaller"}); PR.apply_action(E, _ref(E, "cutaways", 0), {"op": "smaller"})
    assert E["cutaways"][0]["params"]["size"] == pytest.approx(54.5, abs=.1)


def test_bigger_uses_the_template_default_when_the_param_is_absent():
    E = _E(); r = PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "bigger"})      # stat: p.get("size", 230)
    assert r["changed"] and E["cutaways"][1]["params"]["size"] == pytest.approx(253)
    E = _E(); r = PR.apply_action(E, _ref(E, "roto", 0), {"op": "smaller"})       # kinetic_caption_emphasis has size too
    assert r["changed"] and "size" in E["roto"][0]["params"]


def test_bigger_without_a_size_param_is_a_note_for_claude():
    E = _E(); before = copy.deepcopy(E)
    r = PR.apply_action(E, _ref(E, "cutaways", 2), {"op": "bigger"})              # card_list: no scale / size param
    assert not r["changed"] and "note" in r and "card_list" in r["note"] and E == before


def test_bigger_on_an_aroll_shot_changes_its_zoom():
    E = _E(); r = PR.apply_action(E, _ref(E, "zoom", segment="s2", zoom=1.1), {"op": "bigger"})
    assert r["changed"] and E["aroll"]["zoom"]["s2"] == pytest.approx(1.15)
    E = _E(); r = PR.apply_action(E, _ref(E, "zoom", segment="s3", zoom=1.0), {"op": "smaller"})
    assert E["aroll"]["zoom"]["s3"] == pytest.approx(.95) and E["aroll"]["zoom"]["s2"] == 1.1


def test_earlier_and_later_shift_start_end_and_at_keys():
    E = _E(); r = PR.apply_action(E, _ref(E, "cutaways", 0), {"op": "later", "step": .25})
    c = E["cutaways"][0]; assert r["changed"]
    assert (c["start"], c["end"], c["params"]["at"], c["params"]["items"][0]["at"]) == pytest.approx((2.75, 4.25, 2.85, 3.05))
    assert c["snap"] is False                       # an exact move: the boundary snap would undo it
    assert c["params"]["size"] == 60 and c["params"]["title"] == "Why people swipe"
    E = _E(); PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "earlier"})          # default step 0.25
    c = E["cutaways"][1]
    assert (c["start"], c["end"], c["params"]["label_at"], c["params"]["count"][0], c["params"]["count"][1]) == pytest.approx((4.75, 6.25, 5.15, 4.95, 1.2))
    E = _E(); PR.apply_action(E, _ref(E, "roto", 0), {"op": "earlier", "step": .5})
    assert E["roto"][0]["params"]["at"] == pytest.approx(8.7) and "start" not in E["roto"][0]
    E = _E(); PR.apply_action(E, _ref(E, "broll", 0), {"op": "later"})
    assert (E["broll"][0]["start"], E["broll"][0]["end"]) == pytest.approx((3.25, 4.25))


def test_shift_keeps_placeholder_times_exact():
    E = {"cutaways": [{"id": "c1", "template": "stat", "start": "{start:02_problem+0.25}", "end": "{end:02_problem}", "params": {"at": "{start:02_problem}"}}]}
    PR.apply_action(E, _ref(E, "cutaways", 0), {"op": "later", "step": .25})
    c = E["cutaways"][0]
    assert (c["start"], c["end"], c["params"]["at"]) == ("{start:02_problem+0.5}", "{end:02_problem+0.25}", "{start:02_problem+0.25}")


def test_swap_keeps_shared_params_and_offers_only_valid_templates():
    E = _E(); r = PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "swap", "template": "counter"})
    c = E["cutaways"][1]
    assert r["changed"] and c["template"] == "counter" and c["params"]["value"] == 90 and c["params"]["label"] == "keep watching"
    E = _E(); PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "swap", "template": "card_list"})   # card_list: items, label, label_at, top
    assert set(E["cutaways"][1]["params"]) == {"label", "label_at"}
    ok = PR.valid_templates("cutaways")
    assert "counter" in ok and "kinetic_caption_emphasis" not in ok and "broll_shot" not in ok
    assert "kinetic_caption_emphasis" in PR.valid_templates("roto") and "stat" not in PR.valid_templates("roto")
    assert "lower_third" in PR.valid_templates("chest") and "end_card" in PR.valid_templates("end_card")
    E = _E(); before = copy.deepcopy(E)
    r = PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "swap", "template": "kinetic_caption_emphasis"})
    assert not r["changed"] and "error" in r and E == before


def test_remove_deletes_exactly_that_entry():
    E = _E(); r = PR.apply_action(E, _ref(E, "cutaways", 1), {"op": "remove"})
    assert r["changed"] and [c["id"] for c in E["cutaways"]] == ["c1", "c3"]
    E = _E(); PR.apply_action(E, _ref(E, "roto", 0), {"op": "remove"}); assert E["roto"] == [] and len(E["chest"]) == 1
    E = _E(); PR.apply_action(E, _ref(E, "end_card"), {"op": "remove"}); assert "end_card" not in E
    E = _E(); before = copy.deepcopy(E)
    r = PR.apply_action(E, _ref(E, "zoom", segment="s2", zoom=1.1), {"op": "remove"})   # an A-roll shot is speech: selects, not edit.yaml
    assert not r["changed"] and "note" in r and E == before


def test_fix_caption_adds_the_pair():
    E = _E(); r = PR.apply_action(E, _ref(E, "captions"), {"op": "fix_caption", "from": "Alena", "to": "aligner"})
    assert r["changed"] and E["captions"]["fixes"] == {"Alena": "aligner"}
    E = {"cutaways": []}; PR.apply_action(E, _ref(E, "captions"), {"op": "fix_caption", "from": "teh", "to": "the"})
    assert E["captions"]["fixes"] == {"teh": "the"}


def test_refs_find_the_entry_by_id_when_the_list_moved():
    E = _E(); ref = _ref(E, "cutaways", 1)                # c2
    E["cutaways"].insert(0, {"id": "c0", "template": "stat", "start": 0, "end": 1, "params": {}})
    PR.apply_action(E, ref, {"op": "remove"})
    assert [c["id"] for c in E["cutaways"]] == ["c0", "c1", "c3"]


# ------------------------------------------------------------------ apply-notes (files)
def test_apply_notes_patches_text_keeps_comments_and_backs_up(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    PR.write_notes(pr, _notes(pr, [("cutaways:c1", [_ref(E, "cutaways", 0)], {"actions": [{"op": "later", "step": .25}], "note": "make it pop"}),
                                   ("captions", [_ref(E, "captions")], {"actions": [{"op": "fix_caption", "from": "teh", "to": "the"}]})],
                           overall="tighter overall"))
    r = PR.apply_notes(pr)
    text = open(pr.e("edit.yaml"), encoding="utf-8").read(); E2 = yaml.safe_load(text)
    assert "# the plan, hand-written" in text and "# the problem list" in text and r["how"].startswith("text patch")
    assert E2["cutaways"][0]["start"] == pytest.approx(2.75) and E2["captions"]["fixes"] == {"teh": "the"}
    assert os.path.exists(r["backup"]) and yaml.safe_load(open(r["backup"], encoding="utf-8")) == yaml.safe_load(EDIT)
    md = open(pr.e("plan_notes.pending.md"), encoding="utf-8").read()
    assert "make it pop" in md and "tighter overall" in md and "#1" in md
    assert json.load(open(pr.e("plan_notes.json"), encoding="utf-8"))["applied_at"]
    with pytest.raises(SystemExit): PR.apply_notes(pr)                  # applied once; a second run would double the move


def test_apply_notes_remove_and_swap_still_verify(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    PR.write_notes(pr, _notes(pr, [("cutaways:c2", [_ref(E, "cutaways", 1)], {"actions": [{"op": "remove"}]}),
                                   ("cutaways:c3", [_ref(E, "cutaways", 2)], {"actions": [{"op": "swap", "template": "browser_list"}]})]))
    PR.apply_notes(pr); E2 = pr.edit
    assert [c["id"] for c in E2["cutaways"]] == ["c1", "c3"] and E2["cutaways"][1]["template"] == "browser_list"
    assert "# the problem list" in open(pr.e("edit.yaml"), encoding="utf-8").read()


def test_unsupported_quick_action_goes_to_the_pending_notes(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    PR.write_notes(pr, _notes(pr, [("cutaways:c3", [_ref(E, "cutaways", 2)], {"actions": [{"op": "bigger"}]})]))
    r = PR.apply_notes(pr)
    assert not r["applied"] and r["for_claude"]
    assert "Bigger" in open(pr.e("plan_notes.pending.md"), encoding="utf-8").read()
    assert open(pr.e("edit.yaml"), encoding="utf-8").read() == EDIT


# ------------------------------------------------------------------ locks
def test_locks_refuse_changes_until_unlocked(tmp_path):
    pr = _proj(tmp_path); E = pr.edit; ref = _ref(E, "cutaways", 0)
    PR.write_notes(pr, _notes(pr, [("cutaways:c1", [ref], {"approved": True})])); PR.apply_notes(pr)
    lock = json.load(open(pr.e("plan_lock.json"), encoding="utf-8"))
    assert "cutaways:c1" in lock["shots"] and PR.entry_hash(E["cutaways"][0]) in lock["shots"]["cutaways:c1"]["entries"].values()
    PR.write_notes(pr, _notes(pr, [("cutaways:c1", [ref], {"actions": [{"op": "remove"}]})]))
    r = PR.apply_notes(pr)
    assert r["refused"] and not r["applied"] and [c["id"] for c in pr.edit["cutaways"]] == ["c1", "c2", "c3"]
    assert "locked" in open(pr.e("plan_notes.pending.md"), encoding="utf-8").read()
    PR.write_notes(pr, _notes(pr, [("cutaways:c1", [ref], {"actions": [{"op": "later"}], "unlock": True})]))
    r = PR.apply_notes(pr)
    assert r["applied"] and pr.edit["cutaways"][0]["start"] == pytest.approx(2.75)
    assert "cutaways:c1" not in json.load(open(pr.e("plan_lock.json"), encoding="utf-8"))["shots"]


def test_a_lock_follows_the_entry_not_the_shot_number(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    PR.write_notes(pr, _notes(pr, [("cutaways:c2", [_ref(E, "cutaways", 1)], {"approved": True})])); PR.apply_notes(pr)
    # next round: the shot is #5 now and its key is reported differently; the entry hash still matches the lock
    d = _notes(pr, [("x", [], {}), ("y", [], {}), ("z", [], {}), ("w", [], {}), ("cutaways:c2", [_ref(pr.edit, "cutaways", 1)], {"actions": [{"op": "bigger"}]})])
    PR.write_notes(pr, d); r = PR.apply_notes(pr)
    assert r["refused"] and "size" not in pr.edit["cutaways"][1]["params"]


def test_approve_all_locks_every_shot_and_records_approval_2(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    PR.write_notes(pr, _notes(pr, [("cutaways:c1", [_ref(E, "cutaways", 0)], {}), ("roto:s5", [_ref(E, "roto", 0)], {})], approve_all=True))
    PR.apply_notes(pr)
    assert set(json.load(open(pr.e("plan_lock.json"), encoding="utf-8"))["shots"]) == {"cutaways:c1", "roto:s5"}
    notes = open(pr.e("NOTES.md"), encoding="utf-8").read()
    assert "Approval 2" in notes and PR.today() in notes
    PR.record_approval(pr); assert open(pr.e("NOTES.md"), encoding="utf-8").read().count("Approval 2") == 1    # idempotent


# ------------------------------------------------------------------ notes round-trip
def test_notes_round_trip_atomically(tmp_path):
    pr = _proj(tmp_path); E = pr.edit
    d = _notes(pr, [("cutaways:c1", [_ref(E, "cutaways", 0)], {"note": "ünïcode ✓", "actions": [{"op": "swap", "template": "list"}]})], overall="ok")
    PR.write_notes(pr, d)
    assert PR.read_notes(pr) == d
    assert sorted(os.listdir(pr.e())) == ["edit.yaml", "plan_notes.json"]       # no temp file left behind
    for bad in ({"shots": "nope"}, [], {"version": PR.NOTES_VERSION, "shots": [{"actions": [{"op": "rm -rf"}]}]}):
        with pytest.raises(ValueError): PR.write_notes(pr, bad)
    assert PR.read_notes(pr) == d


# ------------------------------------------------------------------ server
def _serve(pr):
    srv = PR.make_server(pr, port=0); th = threading.Thread(target=srv.serve_forever, daemon=True); th.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _post(url, body, origin=None, host=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if not isinstance(body, bytes) else body, method="POST",
                                 headers={"Content-Type": "application/json", **({"Origin": origin} if origin else {}), **({"Host": host} if host else {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()


def test_server_binds_localhost_and_writes_notes(tmp_path):
    pr = _proj(tmp_path); open(pr.p("Moodboard", "EDIT-PLAN.html"), "w", encoding="utf-8").write("<html>plan</html>")
    srv, url = _serve(pr)
    try:
        assert srv.server_address[0] == "127.0.0.1"
        with urllib.request.urlopen(url + "/", timeout=5) as r: assert b"plan" in r.read()
        d = _notes(pr, [("cutaways:c1", [_ref(pr.edit, "cutaways", 0)], {"note": "hi"})])
        st, body = _post(url + "/notes", d, origin=url)
        assert st == 200 and json.loads(body)["saved"] and PR.read_notes(pr) == d
        assert srv.notes_saved.is_set()
        assert _post(url + "/notes", d, origin="http://evil.example")[0] == 403
        assert _post(url + "/notes", d, host="evil.example")[0] == 403                      # DNS rebinding
        assert _post(url + "/notes", b"{not json", origin=url)[0] == 400
        assert _post(url + "/elsewhere", d, origin=url)[0] == 404
        with urllib.request.urlopen(url + "/notes", timeout=5) as r: assert json.loads(r.read()) == d   # GET returns the saved notes
    finally:
        srv.shutdown(); srv.server_close()


def test_server_never_binds_a_public_address(tmp_path):
    pr = _proj(tmp_path)
    with pytest.raises(ValueError): PR.make_server(pr, port=0, host="0.0.0.0")
    srv = PR.make_server(pr, port=0, host="localhost"); assert srv.server_address[0] == "127.0.0.1"; srv.server_close()


def test_server_does_not_serve_outside_moodboard(tmp_path):
    pr = _proj(tmp_path); srv, url = _serve(pr)
    try:
        with pytest.raises(urllib.error.HTTPError): urllib.request.urlopen(url + "/../Edit/edit.yaml", timeout=5)
        with pytest.raises(urllib.error.HTTPError): urllib.request.urlopen(url + "/%2e%2e/Edit/edit.yaml", timeout=5)
    finally:
        srv.shutdown(); srv.server_close()


# ------------------------------------------------------------------ page (no renderer needed)
def _plan():
    E = _E()
    return {"version": PR.NOTES_VERSION, "title": "T", "shots": [
        {"n": 1, "key": "cutaways:c1", "kind": "cutaway", "start": 2.5, "end": 4.0, "refs": [PR.ref_for(E, "cutaways", 0)], "targets": [0],
         "swap": {"0": PR.valid_templates("cutaways")}, "sizable": {"0": True}, "captions": ["Long intros"], "changed": True, "locked": False},
        {"n": 2, "key": "aroll:s2", "kind": "aroll", "start": 4.0, "end": 5.0, "refs": [PR.ref_for(E, "zoom", segment="s2", zoom=1.1)],
         "targets": [0], "swap": {}, "sizable": {"0": True}, "captions": [], "changed": False, "locked": True}]}


def test_page_controls_for_every_shot():
    P = _plan(); html = PR.page_controls(P) + "".join(PR.card_controls(s) for s in P["shots"])
    for s in P["shots"]:
        n = s["n"]
        assert f'id="approve-{n}"' in html and f'id="note-{n}"' in html
        for op in ("bigger", "smaller", "earlier", "later", "remove"): assert f'data-op="{op}"' in html
    assert 'id="send"' in html and 'id="copy"' in html and 'id="approve-all"' in html and 'id="overall"' in html
    assert "changed since last round" in PR.card_controls(P["shots"][0]) and "locked" in PR.card_controls(P["shots"][1])
    assert 'checked' in PR.card_controls(P["shots"][1])                 # a locked shot shows approved
    assert '<option value="counter">' in PR.card_controls(P["shots"][0])


def test_page_without_server_disables_send_and_keeps_copy():
    js = PR.SCRIPT
    assert "location.protocol" in js and "file:" in js and "send.disabled = true" in js
    assert "navigator.clipboard" in js and "fetch('/notes'" in js
    assert "http" not in PR.page_controls(_plan()).replace("http-equiv", "")    # no CDN, nothing leaves the machine
    data = PR.embed(_plan()); assert data.startswith('<script type="application/json" id="plan-data">') and "</script" not in data[50:-9]


# ------------------------------------------------------------------ changed shots between rounds
def test_changed_shot_detection():
    prev = {"sig": "g1", "shots": {"cutaways:c1": {"hash": "a", "frames": [10, 20]}, "aroll:s2": {"hash": "b", "frames": [30]}}}
    cur = {"cutaways:c1": {"hash": "a", "frames": [10, 20]}, "aroll:s2": {"hash": "B", "frames": [30]}, "cutaways:c9": {"hash": "n", "frames": [40]}}
    ch, reuse = PR.changed_shots(prev, cur, "g1", have={10, 20, 30})
    assert ch == {"aroll:s2", "cutaways:c9"} and reuse == {10, 20}
    ch, reuse = PR.changed_shots(prev, cur, "g2", have={10, 20, 30})     # global look changed: every frame re-renders
    assert reuse == set() and ch == {"aroll:s2", "cutaways:c9"}           # ... but only real shot changes get the badge
    ch, reuse = PR.changed_shots(None, cur, "g1", have={10})              # first round: no badges, nothing to reuse
    assert ch == set() and reuse == set()
    ch, reuse = PR.changed_shots(prev, cur, "g1", have={20, 30})          # a missing jpg is rendered again
    assert reuse == {20}


def test_shot_hash_tracks_its_edit_entries():
    E = _E(); sh = {"kind": "cutaway", "start": 2.5, "end": 4.0, "refs": [PR.ref_for(E, "cutaways", 0)], "captions": [], "trans": ["cut", "cut"]}
    h0 = PR.shot_hash(E, sh)
    E2 = _E(); E2["cutaways"][1]["params"]["value"] = 50; assert PR.shot_hash(E2, sh) == h0     # another entry
    E3 = _E(); E3["cutaways"][0]["params"]["title"] = "x"; assert PR.shot_hash(E3, sh) != h0


# ------------------------------------------------------------------ the real plan (renderer): ids map back to edit.yaml
def test_moodboard_plan_maps_every_shot_and_rerenders_only_changes(demo_copy):
    from cves import moodboard as MB
    pr = Project(demo_copy); MB.moodboard(pr)
    html = open(pr.p("Moodboard", "EDIT-PLAN.html"), encoding="utf-8").read()
    P = json.loads(html.split('id="plan-data">', 1)[1].split("</script>", 1)[0])
    E = pr.edit; keys = [s["key"] for s in P["shots"]]
    assert len(keys) == len(set(keys))
    for s in P["shots"]:
        assert f'id="approve-{s["n"]}"' in html and f'id="note-{s["n"]}"' in html
        for r in s["refs"]: assert PR.find_entry(E, r) is not None, r
    c2 = next(s for s in P["shots"] if s["key"] == "cutaways:c2")
    assert c2["refs"][0]["slot"] == "cutaways" and PR.find_entry(E, c2["refs"][0])["id"] == "c2" and "counter" in c2["swap"]["0"]
    assert any(r["slot"] == "roto" for s in P["shots"] for r in s["refs"]) and any(r["slot"] == "chest" for s in P["shots"] for r in s["refs"])
    assert any(s["kind"] == "end" and s["refs"][0]["slot"] == "end_card" for s in P["shots"])
    assert not any(s["changed"] for s in P["shots"])
    fdir = pr.p("Moodboard", "frames"); m0 = {f: os.path.getmtime(os.path.join(fdir, f)) for f in os.listdir(fdir)}
    # round 2: change c2's label only
    text = open(pr.e("edit.yaml"), encoding="utf-8").read(); En = yaml.safe_load(text)
    next(c for c in En["cutaways"] if c["id"] == "c2")["params"]["label"] = "still watching"; pr.save_edit(En)
    MB.moodboard(pr)
    html = open(pr.p("Moodboard", "EDIT-PLAN.html"), encoding="utf-8").read()
    P2 = json.loads(html.split('id="plan-data">', 1)[1].split("</script>", 1)[0])
    assert [s["key"] for s in P2["shots"] if s["changed"]] == ["cutaways:c2"] and "changed since last round" in html
    m1 = {f: os.path.getmtime(os.path.join(fdir, f)) for f in os.listdir(fdir)}
    c2f = {f"{f:05d}.jpg" for f in next(s for s in P2["shots"] if s["key"] == "cutaways:c2")["frames"]}
    assert set(m1) == set(m0) and all(m1[f] == m0[f] for f in m1 if f not in c2f) and all(m1[f] != m0[f] for f in c2f)
