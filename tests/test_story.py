"""Story step: take alignment in `cves select`, STORY-17 (every chosen word is heard) and named story structures.
Runs on the synthetic demo (tools/make_demo.py): its voice is synthesized, so whisper is replaced by the demo's known word
times (raw_words.json), distorted the way whisper.cpp DTW times are (onsets late, a word's end on its last token)."""
import os, json, shutil
import numpy as np, pytest, yaml
from cves import project, align as AL, structure as STR, style as STY, ingest as ING, schema as SC
from cves.qc import audio_gates as AG
import cves.qc as QC


# ------------------------------------------------------------------ helpers
def _raw_words(pr):
    return [w[:3] for w in pr.json("raw_words.json")]

def _fake_whisper(pr, calls=None, late=.12):
    """align._transcribe stand-in: the demo's true words inside [a, b], each start `late` s late (DTW-like)"""
    W = _raw_words(pr)
    def tr(wav, a, b, lang):
        if calls is not None: calls.append((a, b))
        return [[round(s + late, 3), round(max(s + late, e - .02), 3), t] for s, e, t in W if s >= a and e <= b]
    return tr

def _sentences(pr):
    """{clip id: (first word start, last word end, prev sentence end, next sentence start)} from the demo's words"""
    W = pr.json("raw_words.json"); edl = pr.json("edl.json"); out = {}
    for k, c in enumerate(edl["clips"]):
        n = len(c["text"].split()); i = next(i for i in range(len(W)) if W[i][0] >= c["in"] - 1e-6)
        out[c["id"]] = (W[i][0], W[i + n - 1][1], W[i - 1][1] if i else 0.0, W[i + n][0] if i + n < len(W) else 1e9)
    return out

def _write_selects(pr, clips):
    with open(pr.e("selects.yaml"), "w", encoding="utf-8") as f: yaml.safe_dump({"clips": clips}, f, sort_keys=False)

def _set_style(pr, **grammar):
    E = pr.edit; E.setdefault("style", {}).setdefault("grammar", {}).update(grammar); pr.save_edit(E)
    return STY.load(pr)


# ------------------------------------------------------------------ text normalisation and scores
def test_tokens_normalise_numbers_and_symbols():
    assert AL.tokens("We've done this for 300+ clients") == AL.tokens("we've done this for three hundred plus clients")
    assert AL.tokens("You get a hundred percent refund.") == ["you", "get", "100", "percent", "refund"] == AL.tokens("you get 100% refund")
    assert AL.tokens("four to six implant patients") == ["4", "to", "6", "implant", "patients"] == AL.tokens("4-6 implant patients")
    assert AL.tokens("Forty two thousand") == ["42000"]
    hyp, own = AL.word_tokens([[0, 1, "three"], [1, 2, "hundred"], [2, 3, "plus"]])
    assert hyp == ["300", "plus"] and own == [1, 2]

def test_best_run_picks_the_take_with_the_text():
    W = "We've done this for 300 plus industries. We've done this for 300+ clients across".split()
    hyp, own = AL.word_tokens([[k, k + .5, w] for k, w in enumerate(W)])
    i, j, sc, head, tail = AL.best_run(AL.tokens("We've done this for 300 plus clients"), hyp)
    assert (own[i], own[j - 1]) == (7, 12) and sc == 1.0 and head == tail == 0

def test_recall_ignores_fillers_and_lists_missing_words():
    sc, miss = AL.recall("Not happy in 30 days? You get a hundred percent refund.", "um not happy in thirty days you get a 100%")
    assert miss == ["refund"] and abs(sc - .9) < 1e-9
    assert AL.recall("three hundred plus clients", "300+ client")[0] == 1.0
    assert AL.recall("We've done this for 300 plus clients", "I've done this for 300 plus clients", edges=True)[2] == (True, False)


# ------------------------------------------------------------------ take alignment
def test_alignment_fixes_bad_in_and_out(demo_copy, monkeypatch):
    pr = project.Project(demo_copy); monkeypatch.setattr(AL, "_transcribe", _fake_whisper(pr))
    truth = _sentences(pr); clips = [dict(c) for c in ING._clips(pr)]
    # deliberately bad hand times: the first clip cuts into its last word, the second clips its first word and runs on into
    # the next sentence, the third starts a word early inside the previous sentence
    a, b, c = clips[0], clips[1], clips[2]
    a["out"] = round(truth[a["id"]][1] - .3, 3)
    b["in"] = round(truth[b["id"]][0] + .3, 3); b["out"] = round(truth[b["id"]][3] + .25, 3)
    c["in"] = round(truth[c["id"]][2] - .25, 3)
    S = STY.load(pr); lines = []
    recs = AL.align_clips(pr, clips, {x["id"]: None for x in clips}, S, lang="en", out=lines.append)
    assert len(lines) == len(clips) and all(r["status"] in ("moved", "unchanged") for r in recs), lines
    wav = AL.wav16(pr); t, db = AL.energy(wav, 0, 30); floor = np.percentile(db, 10)
    for x in clips:
        s0, s1, prev_end, next_start = truth[x["id"]]
        assert prev_end - 1e-3 <= x["in"] <= s0 + 1e-3, (x["id"], x["in"], truth[x["id"]])
        assert s1 - 1e-3 <= x["out"] <= next_start + 1e-3, (x["id"], x["out"], truth[x["id"]])
        for edge in (x["in"], x["out"]):          # never cut inside speech energy
            k = int(np.argmin(np.abs(t - edge))); assert db[k] < floor + 12, (x["id"], edge, db[k], floor)
        assert x["aligned"]["hand"] and x["aligned"]["score"] >= .99
    assert "in" in lines[1] and "->" in lines[1]

def test_low_score_keeps_hand_times_and_warns(demo_copy, monkeypatch):
    pr = project.Project(demo_copy); monkeypatch.setattr(AL, "_transcribe", _fake_whisper(pr))
    clips = [dict(c) for c in ING._clips(pr)][:1]; clips[0]["text"] = "completely unrelated words nobody said here"
    hand = (clips[0]["in"], clips[0]["out"]); lines = []
    rec = AL.align_clips(pr, clips, {clips[0]["id"]: None}, STY.load(pr), lang="en", out=lines.append)[0]
    assert rec["status"] == "kept_low_score" and (clips[0]["in"], clips[0]["out"]) == hand
    assert lines[0].startswith("WARNING")

def test_opt_out_per_clip_and_by_style(demo_copy, monkeypatch):
    pr = project.Project(demo_copy); calls = []; monkeypatch.setattr(AL, "_transcribe", _fake_whisper(pr, calls))
    clips = [dict(c) for c in ING._clips(pr)]; clips[0]["align"] = False; clips[0]["in"] += .2
    recs = AL.align_clips(pr, clips, {c["id"]: None for c in clips}, STY.load(pr), lang="en", out=None)
    assert recs[0]["status"] == "off" and clips[0]["in"] == recs[0]["hand"][0]
    assert all(r["status"] != "off" for r in recs[1:])
    E = pr.edit; E.setdefault("style", {})["story"] = {"align": False}; pr.save_edit(E); calls.clear()
    clips = [dict(c) for c in ING._clips(pr)]
    recs = AL.align_clips(pr, clips, {c["id"]: None for c in clips}, STY.load(pr), lang="en", out=None)
    assert all(r["status"] == "off" for r in recs) and not calls

def test_window_transcripts_are_cached(demo_copy, monkeypatch):
    pr = project.Project(demo_copy); calls = []; monkeypatch.setattr(AL, "_transcribe", _fake_whisper(pr, calls))
    S = STY.load(pr); clips = [dict(c) for c in ING._clips(pr)]
    AL.align_clips(pr, clips, {c["id"]: None for c in clips}, S, lang="en", out=None); n = len(calls)
    assert n == len(clips) * AL.settings(S)["passes"]
    clips = [dict(c) for c in ING._clips(pr)]
    AL.align_clips(pr, clips, {c["id"]: None for c in clips}, S, lang="en", out=None)
    assert len(calls) == n and os.listdir(pr.e("align", "cache"))

def test_dtw_preset_names():
    assert AL.dtw_preset("/x/ggml-large-v3-turbo-q5_0.bin") == "large.v3.turbo"
    assert AL.dtw_preset("ggml-base.en.bin") == "base.en" and AL.dtw_preset("my-model.bin") is None


# ------------------------------------------------------------------ cves select + STORY-17
def _fake_df(pr, c, audio):
    """ingest._df_clip without DeepFilterNet: the windowed raw clip stands in for the cleaned one"""
    import soundfile as sf
    os.makedirs(pr.e("voice", "in"), exist_ok=True); os.makedirs(pr.e("voice", "df"), exist_ok=True)
    a, b = max(0, c["in"] - ING.PAD), c["out"] + ING.PAD
    y, sr = sf.read(audio, start=int(a * ING.SR), stop=int(b * ING.SR))
    p = pr.e("voice", "in", f"{c['id']}.wav"); sf.write(p, y, sr); q = pr.e("voice", "df", f"{c['id']}_DeepFilterNet3.wav"); shutil.copy(p, q)
    return q

def _fake_heard(pr):
    """align.span_text stand-in: the true raw words whose middle lands in [t0, t1] of the cut (mapped through edl segments)"""
    W = _raw_words(pr)
    def heard(wav, t0, t1, lang, prompt=None):
        edl = pr.json("edl.json"); F = edl["fps"]; t, out = 0.0, []
        for s in edl["segments"]:
            L = round((s["out"] - s["in"]) * F) / F
            for a, b, w in W:
                m = (a + b) / 2
                if s["in"] <= m <= s["out"] and t0 <= t + m - s["in"] <= t1: out.append(w)
            t += L
        return " ".join(out)
    return heard

@pytest.fixture
def story_cut(demo_copy, monkeypatch):
    pr = project.Project(demo_copy)
    monkeypatch.setattr(AL, "_transcribe", _fake_whisper(pr)); monkeypatch.setattr(ING, "_df_clip", _fake_df)
    monkeypatch.setattr(AL, "span_text", _fake_heard(pr)); monkeypatch.setattr(AG, "stutters", lambda pr, lang=None: [])
    clips = ING._clips(pr); truth = _sentences(pr)
    clips[0]["out"] = round(truth[clips[0]["id"]][1] - .3, 3)          # hand out clips the last word: alignment repairs it
    _write_selects(pr, clips)
    ING.select(pr); return pr

def test_select_records_alignment_in_edl(story_cut):
    edl = story_cut.json("edl.json")
    assert all("aligned" in c and c["aligned"]["status"] in ("moved", "unchanged") for c in edl["clips"])
    assert edl["clips"][0]["aligned"]["status"] == "moved" and edl["clips"][0]["aligned"]["hand"][1] < edl["clips"][0]["out"]
    nf, rep = QC.run_stage(story_cut, "story")
    line = next(l for l in rep.splitlines() if "STORY-17" in l); assert line.startswith("[PASS]"), rep

def test_story17_fails_when_a_clip_is_truncated(story_cut):
    pr = story_cut; edl = pr.json("edl.json"); W = _raw_words(pr)
    last = edl["clips"][-1]; segs = [s for s in edl["segments"] if s["clip"] == last["id"]]
    words = [w for w in W if segs[0]["in"] <= (w[0] + w[1]) / 2 <= segs[-1]["out"]]
    segs[-1]["out"] = round(words[-2][0] - .01, 5)                       # drop the clip's last two words
    pr.save_json("edl.json", edl)
    nf, rep = QC.run_stage(pr, "story")
    i = next(k for k, l in enumerate(rep.splitlines()) if "STORY-17" in l); L = rep.splitlines()
    assert L[i].startswith("[FAIL]") and nf >= 1, rep
    det = L[i + 1]
    assert last["id"] in det and AL.tokens(words[-1][2])[0] in det and AL.tokens(words[-2][2])[0] in det, rep

def test_story17_fails_one_lost_last_word(story_cut):
    """recall alone passes one lost word of a long clip; a lost last word is a clipped take and fails anyway"""
    pr = story_cut; edl = pr.json("edl.json"); W = _raw_words(pr)
    c = max(edl["clips"], key=lambda c: len(c["text"].split())); segs = [s for s in edl["segments"] if s["clip"] == c["id"]]
    words = [w for w in W if segs[0]["in"] <= (w[0] + w[1]) / 2 <= segs[-1]["out"]]
    segs[-1]["out"] = round(words[-1][0] - .01, 5); pr.save_json("edl.json", edl)
    E = pr.edit; E.setdefault("qc", {})["words_recall_min"] = .5; pr.save_edit(E)
    nf, rep = QC.run_stage(project.Project(pr.root), "story"); L = rep.splitlines(); i = next(k for k, l in enumerate(L) if "STORY-17" in l)
    assert L[i].startswith("[FAIL]") and "last word lost" in L[i + 1], rep
    E["qc"]["words_edges"] = False; pr.save_edit(E)
    nf, rep = QC.run_stage(project.Project(pr.root), "story")
    assert next(l for l in rep.splitlines() if "STORY-17" in l).startswith("[PASS]"), rep

def test_story17_skips_clips_without_text(story_cut):
    pr = story_cut; edl = pr.json("edl.json"); edl["clips"][1].pop("text"); pr.save_json("edl.json", edl)
    nf, rep = QC.run_stage(pr, "story")
    line = next(l for l in rep.splitlines() if "STORY-17" in l)
    assert "without text" in line and edl["clips"][1]["id"] in line

def test_story17_names_hint_a_proper_noun_to_its_clips(story_cut, monkeypatch):
    """whisper mangles a name it doesn't know (a clinic heard as "Mediterranean"): qc.names sends it as a hint, only to the
    clips whose text: has it, so every other clip is still heard unaided"""
    pr = story_cut; clips = [c for c in pr.json("edl.json")["clips"] if c.get("text")]
    name = max((t for t in AL.tokens(clips[0]["text"]) if t.isalpha()), key=len)   # clip 0's longest word plays the name
    base, sent = _fake_heard(pr), []
    def heard(wav, t0, t1, lang, prompt=None):
        sent.append(prompt)
        hinted = bool(prompt) and name in prompt.lower()
        return " ".join(w if hinted or AL.tokens(w)[:1] != [name] else "Mediterranean" for w in base(wav, t0, t1, lang).split())
    monkeypatch.setattr(AL, "span_text", heard)
    nf, rep = QC.run_stage(project.Project(pr.root), "story")
    assert next(l for l in rep.splitlines() if "STORY-17" in l).startswith("[FAIL]"), rep
    E = pr.edit; E.setdefault("qc", {})["names"] = [name.capitalize(), "Profitcast"]; pr.save_edit(E); sent.clear()
    nf, rep = QC.run_stage(project.Project(pr.root), "story")
    assert next(l for l in rep.splitlines() if "STORY-17" in l).startswith("[PASS]"), rep
    n_with = sum(name in AL.tokens(c["text"]) for c in clips)
    assert sorted(p for p in sent if p) == [name.capitalize()] * n_with and sent.count(None) == len(clips) - n_with


# ------------------------------------------------------------------ named story structures
def test_structure_presets_and_override():
    S = STY.Style({"grammar": {"structure": "offer"}})
    assert STR.beats_of(S) == ["H", "M", "PR", "R", "C"]
    assert STR.music_beats(S) == {"hook_beats": ["H"], "turn_beats": ["M"], "drop_beats": ["PR"]}
    assert STR.beats_of(STY.Style({})) == ["H", "P", "A", "PR", "O", "C"]
    assert STR.beats_of(STY.Style({"grammar": {"structure": "story"}})) == ["H", "S", "T", "PR", "C"]
    S = STY.Style({"grammar": {"structure": "offer", "beats": ["H", "P", "PR", "C"]}})          # grammar.beats wins
    assert STR.beats_of(S) == ["H", "P", "PR", "C"] and STR.music_beats(S)["turn_beats"] == ["P"]
    assert STR.music_beats(STY.Style({"grammar": {"beats": ["H", "M", "PR", "R", "C"]}}))["drop_beats"] == ["PR"]
    assert STR.label("R") == "Risk reversal" and STR.label("M") == "Mechanism" and set(STR.COLORS) >= {"M", "R", "S", "T"}

def test_default_style_has_no_fixed_order():
    S = STY.load()
    assert S.get("grammar.structure") == "problem" and S.get("grammar.beats") is None
    assert S.get("music.turn_beats") is None and S.get("story.align") is True and S.get("qc.words_recall_min") == .85

def test_music_beats_follow_the_structure(demo_copy):
    from cves import beats as BT
    pr = project.Project(demo_copy)
    c = BT.cfg(pr); assert c["turn_beats"] == ["P", "A"] and c["drop_beats"] == ["PR", "O"]
    S = _set_style(pr, structure="offer"); pr = project.Project(demo_copy)
    c = BT.cfg(pr, S); assert c["turn_beats"] == ["M"] and c["drop_beats"] == ["PR"]
    E = pr.edit; E["music"] = dict(E.get("music") or {}, drop_beats=["R"]); pr.save_edit(E); pr = project.Project(demo_copy)
    assert BT.cfg(pr)["drop_beats"] == ["R"]                                                 # an explicit value wins

def test_schema_knows_the_structure_beats(demo_copy):
    pr = project.Project(demo_copy); clips = ING._clips(pr)
    clips[1]["beat"] = "M"; _write_selects(pr, clips)
    _, warns = SC.validate(pr); assert any("clips[1].beat" in w for w in warns)
    _set_style(pr, structure="offer"); pr = project.Project(demo_copy)
    _, warns = SC.validate(pr); assert not any("clips[1].beat" in w for w in warns)
    clips[1]["beat"] = "P"; _write_selects(pr, clips)
    _, warns = SC.validate(pr); assert any("clips[1].beat" in w and "Mechanism" in w for w in warns)   # P is not an offer beat
    clips[2].pop("text"); _write_selects(pr, clips)
    _, warns = SC.validate(pr); assert any("without text" in w for w in warns)
    _set_style(pr, structure="offr"); pr = project.Project(demo_copy)
    _, warns = SC.validate(pr); assert any("grammar.structure" in w for w in warns)

def test_story_gates_follow_the_structure(story_cut):
    pr = story_cut; edl = pr.json("edl.json")
    tags = ["H", "PR", "R", "C"] if len(edl["clips"]) == 4 else ["H", "M", "PR", "R", "C"]
    for c, b in zip(edl["clips"], tags): c["beat"] = b
    pr.save_json("edl.json", edl)
    _set_style(pr, structure="offer"); pr = project.Project(pr.root)
    nf, rep = QC.run_stage(pr, "story"); L = {l.split()[1]: l for l in rep.splitlines() if l.startswith("[")}
    assert "STORY-13" not in L                                                               # no P beat in an offer ad
    assert "(offer: H > M > PR > R > C)" in L["STORY-01"]
    assert "risk reversal after the proof" in L["STORY-07"] and L["STORY-07"].startswith("[PASS]")
    _set_style(pr, structure="problem"); pr = project.Project(pr.root)
    nf, rep = QC.run_stage(pr, "story"); L = {l.split()[1]: l for l in rep.splitlines() if l.startswith("[")}
    assert L["STORY-01"].startswith("[FAIL]") and "not in this structure: R" in rep
