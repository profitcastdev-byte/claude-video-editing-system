"""Senior sound (v0.4 WS H, docs/SOUND.md): music phrases + story alignment, automatic risers / impacts, voice-envelope
ducking, the SFX bank manifest and `cves sfx fetch` (mocked: no network in tests). Synthetic media only."""
import os, sys, json, types, shutil
import numpy as np, soundfile as sf, yaml, pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))

SR = 22050
BPM = 120; BEAT = 60 / BPM; BAR = 4 * BEAT        # 2 s bars


# ------------------------------------------------------------------ synthetic music with a known structure
def _kick(n, sr, amp):
    k = np.arange(n) / sr
    return (np.sin(2 * np.pi * (48 + 90 * np.exp(-k * 45)) * k) * np.exp(-k * 16) + .3 * np.random.default_rng(1).standard_normal(n) * np.exp(-k * 400)) * amp

def song(path, plan, seed=3):
    """plan: list of (label, bars, level_from, level_to). Kick on every beat (accented on 1), a hat on the off-beats, a
    chord pad that changes every bar (5 ms attack, so the bar line is the only onset), a bass in loud bars, and a noise
    riser over any 'build'. Levels are linear amplitudes."""
    n = int(sum(b for _, b, _, _ in plan) * BAR * SR); y = np.zeros(n); rng = np.random.default_rng(seed)
    chords = [(220, 277.2, 329.6), (196, 246.9, 293.7), (174.6, 220, 261.6), (164.8, 207.7, 246.9)]
    bar0 = 0
    for label, bars, l0, l1 in plan:
        for j in range(bars):
            lv = l0 + (l1 - l0) * (j / max(1, bars - 1)); i0 = int((bar0 + j) * BAR * SR); L = int(BAR * SR)
            kk = np.arange(L) / SR
            pad = sum(np.sin(2 * np.pi * f * kk) for f in chords[(bar0 + j) % 4]) / 3 * np.minimum(1, kk / .005) * np.exp(-kk * .6) * .35
            y[i0:i0 + L] += pad * lv
            for b in range(4):
                bi = i0 + int(b * BEAT * SR); m = min(int(.3 * SR), n - bi)
                y[bi:bi + m] += _kick(m, SR, lv * (1.0 if b == 0 else .7))
                hi = i0 + int((b + .5) * BEAT * SR); h = min(int(.05 * SR), n - hi)
                y[hi:hi + h] += rng.standard_normal(h) * np.exp(-np.arange(h) / SR * 80) * .12 * lv
            if label == "drop":
                y[i0:i0 + L] += np.sin(2 * np.pi * chords[(bar0 + j) % 4][0] / 4 * kk) * .35 * lv
            if label == "build":
                u = (j + kk / BAR) / bars; y[i0:i0 + L] += rng.standard_normal(L) * .08 * u ** 2 * lv
        bar0 += bars
    st = np.stack([y, y], 1); st = st / (np.abs(st).max() + 1e-9) * .8
    sf.write(path, st, SR); return path

STRUCT = [("intro", 4, .18, .18), ("build", 4, .2, .55), ("drop", 8, 1.0, 1.0), ("outro", 4, .35, .08)]


@pytest.fixture(scope="module")
def built_song(tmp_path_factory):
    return song(str(tmp_path_factory.mktemp("song") / "song.wav"), STRUCT)


def test_phrases_find_the_build_and_the_drop(built_song):
    from cves import beats as BT
    B = BT.analyse(built_song, 4, 3.0, (60, 150))
    assert abs(B["tempo"] - BPM) < 2
    ph = BT.phrases(B, {})
    lab = [p["label"] for p in ph]
    assert lab[0] == "intro" and "drop" in lab and "build" in lab, ph
    drop = next(p for p in ph if p["label"] == "drop"); build = next(p for p in ph if p["label"] == "build")
    assert abs(drop["start"] - 16.0) <= .5 * BAR, ph                       # the drop: on its bar
    assert abs(build["start"] - 8.0) <= BAR and abs(build["end"] - drop["start"]) < 1e-3, ph
    assert ph[-1]["label"] == "outro" and abs(ph[-1]["start"] - 32.0) <= BAR, ph
    assert ph[0]["start"] == 0 and ph[-1]["end"] == B["duration"]
    assert all(p["start"] in [round(b["t"], 4) for b in B["bars"]] for p in ph[1:])      # sections change on bar lines


# ------------------------------------------------------------------ a minimal project + a stub timeline (no render)
def _project(tmp, music, music_cfg=None, clips=None, style=None):
    from cves import project
    d = os.path.join(tmp, "proj"); os.makedirs(os.path.join(d, "Edit")); os.makedirs(os.path.join(d, "Music"))
    shutil.copy(music, os.path.join(d, "Music", "song.wav"))
    E = {"project": {"client": "Test", "title": "t"}, "music": {"file": "Music/song.wav", **(music_cfg or {})}}
    if style: E["style"] = style
    yaml.safe_dump(E, open(os.path.join(d, "Edit", "edit.yaml"), "w", encoding="utf-8"))
    json.dump({"clips": clips or []}, open(os.path.join(d, "Edit", "edl.json"), "w", encoding="utf-8"))
    return project.Project(d)

def _tl(pr, segs, T, fps=30.0, cuts=(), end=0.0):
    from cves import style as STY
    S = STY.load(pr)
    return types.SimpleNamespace(pr=pr, S=S, E=pr.edit, N=int(round((T + end) * fps)), FPS=fps, T_END=T, END=end, segs=segs, snap=None,
                                 cuts=list(cuts), trans=[], root=ROOT)

STORY = [("h", "H", 0.0, 3.0), ("p", "P", 3.0, 7.0), ("pr", "PR", 7.0, 11.0), ("o", "O", 11.0, 14.0)]

def _story_segs():
    return [{"id": f"{c}_0", "clip": c, "t0": a, "t1": b} for c, _, a, b in STORY], [{"id": c, "beat": bt} for c, bt, _, _ in STORY]


def test_drop_lands_on_the_payoff_and_seams_stay_on_downbeats(built_song, tmp_path):
    from cves import beats as BT
    segs, clips = _story_segs()
    pr = _project(str(tmp_path), built_song, {"sync": "drop"}, clips)
    T = 70.0                                       # longer than the 40 s track: the bed has to loop
    segs[-1]["t1"] = T
    TL = _tl(pr, segs, T)
    P = BT.plan(pr, TL, S=TL.S)
    assert P["drop"]["cut"] == 7.0 and abs(P["drop"]["track"] - 16.0) <= .5 * BAR
    pay = P["story"]["payoff"]
    assert pay["section"] == "drop" and abs(pay["error_s"]) < 1e-3 and pay["on_downbeat"], pay
    assert P["story"]["turn"]["at"] == 3.0 and P["story"]["hook"]["at"] == 0.0
    B = P["B"]; lay = P["lay"]
    assert lay["loops"] >= 1
    for o, s0, s1 in lay["pieces"][1:]:            # every loop seam: a downbeat in the track and on the cut grid
        assert min(abs(d - s0) for d in B["downbeats"]) < 1e-3
        assert min(abs(d - o) for d in lay["downbeats"]) < 1e-3
    first = next(p for p in P["phrases"] if p["label"] == "drop" and p["starts_here"])
    assert abs(first["start"] - 7.0) < 1e-3


def test_phrase_alignment_prefers_the_build_that_starts_on_the_turn(tmp_path):
    from cves import beats as BT
    # two drops: A (bar 8) after a 4-bar build, B (bar 22) after a 2-bar build; the turn is 2 bars before the payoff
    path = song(str(tmp_path / "two.wav"), [("intro", 4, .18, .18), ("build", 4, .2, .55), ("drop", 6, 1.0, 1.0), ("intro", 6, .15, .15),
                                             ("build", 2, .25, .55), ("drop", 6, 1.0, 1.0)], seed=5)
    segs = [{"id": "h_0", "clip": "h", "t0": 0.0, "t1": 2.0}, {"id": "p_0", "clip": "p", "t0": 2.0, "t1": 6.0},
            {"id": "pr_0", "clip": "pr", "t0": 6.0, "t1": 12.0}]
    clips = [{"id": "h", "beat": "H"}, {"id": "p", "beat": "P"}, {"id": "pr", "beat": "PR"}]
    pr = _project(str(tmp_path), path, {"sync": "drop", "phrase_turn_weight": 6}, clips)
    TL = _tl(pr, segs, 12.0)
    P = BT.plan(pr, TL, S=TL.S)
    B = P["B"]
    assert len(B["drops"]) >= 2
    assert abs(P["drop"]["track"] - 44.0) <= .5 * BAR, (P["drop"], B["drops"], B["phrases"])
    assert abs(P["story"]["turn"]["error_bars"]) <= .5
    pr2 = _project(str(tmp_path / "off"), path, {"sync": "drop", "phrase_align": False}, clips)
    P2 = BT.plan(pr2, _tl(pr2, segs, 12.0), S=_tl(pr2, segs, 12.0).S)
    assert P2["drop"]["candidate"] == 0             # without phrase alignment: the strongest drop, as before


# ------------------------------------------------------------------ envelope ducking
class _S(dict):
    def get(self, path, default=None):
        cur = self
        for k in path.split("."):
            if not isinstance(cur, dict) or k not in cur: return default
            cur = cur[k]
        return cur

def _voice(sr, t0=1.0, t1=2.6, n_s=4.0):
    n = int(n_s * sr); t = np.arange(n) / sr; y = np.zeros(n)
    m = (t >= t0) & (t < t1)
    syl = np.clip(np.sin(2 * np.pi * 4.5 * (t - t0)), 0, 1) ** .5          # 4.5 syllables / s
    src = sum(np.sin(2 * np.pi * 130 * k * t) / k for k in range(1, 20))
    y[m] = (src * syl)[m] * .3
    return y + np.random.default_rng(2).standard_normal(n) * 1e-4

def test_envelope_ducking_follows_the_voice_and_recovers():
    from cves import sound as SO
    sr = 48000; vo = _voice(sr)
    S = _S({"mix": {"duck_mode": "envelope", "duck_attack_ms": 40, "duck_release_ms": "auto", "duck_release_range_ms": [250, 400], "duck_range_db": 30},
            "sound": {"duck_lookahead_s": 0.12, "duck_voice_band_db": -8, "duck_other_db": -3}})
    duck, info = SO.duck_control(vo, sr, S)
    assert info["mode"] == "envelope" and 250 <= info["release_ms"] <= 400 and info["syllable_hz"] and 3 <= info["syllable_hz"] <= 6
    rng = np.random.default_rng(4); mus = rng.standard_normal((len(vo), 2)) * .1
    out = SO.apply_duck(mus, duck, S, sr)
    def lvl(a, b): return 20 * np.log10(np.sqrt(np.mean(out[int(a * sr):int(b * sr)] ** 2)) / np.sqrt(np.mean(mus[int(a * sr):int(b * sr)] ** 2)))
    assert lvl(.2, .7) > -.3                     # before the voice: untouched
    assert lvl(1.4, 2.3) < -3.0                  # under the voice: down (mostly the voice band)
    assert lvl(3.3, 3.9) > -.5                   # 0.7 s after the last syllable: back
    a = np.argmax(duck >= .5 * duck.max()) / sr  # the dip is in place by the first syllable (attack + look-ahead)
    assert .85 <= a <= 1.1, a
    g, ginfo = SO.duck_control(vo, sr, _S(dict(S, mix={"duck_mode": "gate"})))
    assert ginfo["mode"] == "gate" and g.max() > .9   # the v0.3 fixed dips stay available


def test_envelope_ducking_breathes_between_phrases():
    """a gap between two phrases recovers part-way under envelope mode (the gate holds deeper)"""
    from cves import sound as SO
    sr = 48000; vo = _voice(sr, 1.0, 1.8, 4.0) + _voice(sr, 2.4, 3.2, 4.0)
    S = _S({"mix": {"duck_mode": "envelope"}, "sound": {"duck_lookahead_s": 0.12}})
    e, _ = SO.duck_control(vo, sr, S)
    g, _ = SO.duck_control(vo, sr, _S({"mix": {"duck_mode": "gate"}, "sound": {"duck_lookahead_s": 0.12}}))
    i = int(2.15 * sr)
    assert e[i] < g[i]


# ------------------------------------------------------------------ automatic accents
def test_riser_resolves_on_the_target_and_budget_limits_accents(built_song, tmp_path):
    from cves import sound as SO, mix as MX, sfx as SFX
    segs, clips = _story_segs()
    pr = _project(str(tmp_path), built_song, {"sync": "drop"}, clips)
    TL = _tl(pr, segs, 14.0)
    log = []; acc = SO.accents(TL, [], log)
    kinds = sorted((kw["accent"], round(kw["target"], 3)) for _, _, _, kw in acc)
    assert ("riser", 7.0) in kinds and ("impact", 7.0) in kinds and ("riser", 3.0) in kinds, log     # payoff riser + hit; out of the hook
    fin = MX._finalize(TL, acc)
    E = {s["id"]: s for s in SFX.entries(pr)}
    for t, name, g, kw in fin:
        if kw["accent"] != "riser": assert abs(t - kw["target"]) < 1e-6; continue
        pk = t + MX.peak_offset(TL, name, kw)
        assert abs(pk - kw["target"]) <= 1 / 48000 + 1e-6                     # the peak IS the target
        assert abs(t + float(E[name]["duration_s"]) - kw["target"]) <= 1 / TL.FPS   # and the riser ends on it (within a frame)
    # the restraint budget: 1 accent per 30 s -> only the payoff riser
    pr2 = _project(str(tmp_path / "b"), built_song, {"sync": "drop"}, clips, style={"creative": {"sound_accents_per_30s": 1}})
    log2 = []; acc2 = SO.accents(_tl(pr2, segs, 14.0), [], log2)
    assert [kw["accent"] for _, _, _, kw in acc2] == ["riser"]
    assert sum(1 for r in log2 if "budget" in r.get("status", "")) == 2
    # a moment that already has a low hit gets no impact; a target off every picture event gets nothing
    acc3 = SO.accents(TL, [(7.0, "lowhit", -10, {"reveal": True})], [])
    assert not any(kw["accent"] == "impact" and abs(kw["target"] - 7) < .01 for _, _, _, kw in acc3)
    segs2 = [dict(s) for s in segs]; segs2[2]["t0"] = 7.4; segs2[1]["t1"] = 7.4
    pr3 = _project(str(tmp_path / "c"), built_song, {"sync": "drop", "drop_cut": 7.0}, clips)
    lg = []; acc4 = SO.accents(_tl(pr3, segs2, 14.0), [], lg)
    assert not any(abs(kw["target"] - 7.0) < .01 for _, _, _, kw in acc4) and any("no picture event" in r.get("status", "") for r in lg)
    # edit.yaml sfx.auto: false turns them off
    pr4 = _project(str(tmp_path / "d"), built_song, {"sync": "drop"}, clips)
    E4 = pr4.edit; E4["sfx"] = {"auto": False}; pr4.save_edit(E4)
    assert SO.accents(_tl(pr4, segs, 14.0), [], []) == []


# ------------------------------------------------------------------ the SFX bank
def test_repo_manifest_is_valid_cc0_and_credited():
    from cves import sfx as SFX
    assert SFX.validate(SFX.REPO_BANK) == []
    m = SFX.read_manifest(SFX.REPO_BANK); ids = {s["file"] for s in m["sounds"]}
    audio = {f for f in os.listdir(SFX.REPO_BANK) if f.endswith((".mp3", ".wav"))}
    assert audio == ids, audio ^ ids                         # every file catalogued, nothing missing
    credits = open(os.path.join(SFX.REPO_BANK, "CREDITS.md"), encoding="utf-8").read()
    for s in m["sounds"]:
        assert s["licence"].startswith("CC0") and f"| {s['file']} |" in credits, s["id"]
        assert s["category"] in s["id"] or s["file"].endswith(".mp3")      # synthesized ids carry their category word
    assert {s["category"] for s in m["sounds"]} == set(SFX.CATEGORIES)
    wav = sum(os.path.getsize(os.path.join(SFX.REPO_BANK, f)) for f in audio if f.endswith(".wav"))
    assert wav < 5 * 1024 * 1024 and sum(1 for f in audio if f.endswith(".wav")) <= 25
    for s in m["sounds"]:
        if s["category"] == "riser" and s["file"].endswith(".wav"): assert s["duration_s"] - s["peak_at_s"] <= .1   # house risers resolve at the end

def test_pick_by_category_and_intensity():
    from cves import sfx as SFX
    E = SFX.entries()
    assert SFX.pick(E, "impact", "hard", max_s=2.0)["intensity"] == "hard"
    assert SFX.pick(E, "whoosh", "soft")["id"] == "whoosh_soft"
    assert SFX.pick(E, "nonsense") is None
    cues = [(0.0, "@pop", -18, {}), (0.5, "@pop", -18, {}), (1.0, "@impact:hard", -12, {})]
    out = SFX.resolve_cues(cues, E)
    assert out[0][1] != out[1][1] and all(not n.startswith("@") for _, n, _, _ in out)
    assert next(s for s in E if s["id"] == out[2][1])["category"] == "impact"


def test_fetch_is_cc0_only_and_records_credits(tmp_path, monkeypatch):
    from cves import sfx as SFX, music as MU
    import urllib.request
    def no_net(*a, **k): raise AssertionError("network used in a test")
    monkeypatch.setattr(urllib.request, "urlopen", no_net)
    def fake_get(url, params=None, timeout=30):
        assert params["license"] == "cc0" and params["source"] == "freesound"
        mk = lambda i, lic: {"id": f"{i:08d}-0000-0000-0000-000000000000", "title": f"Whoosh {i}", "creator": "someone", "license": lic, "license_version": "1.0",
                             "foreign_landing_url": f"https://freesound.org/s/{i}/", "url": f"https://cdn.example.org/{i}.mp3", "filetype": "mp3", "duration": 800, "source": "freesound"}
        return {"results": [mk(1, "by"), mk(2, "cc0"), mk(3, "cc0")], "page_count": 1}
    monkeypatch.setattr(MU, "_get", fake_get)
    def fake_dl(url, dst):
        t = np.arange(int(.8 * 48000)) / 48000
        sf.write(dst, (np.random.default_rng(len(url)).standard_normal(len(t)) * np.sin(np.pi * t / .8) * .3).astype(np.float32), 48000, format="WAV")
        return dst
    monkeypatch.setattr(SFX, "_download", fake_dl)
    def fake_fs(url, params=None, headers=None):
        assert headers["Authorization"] == "Token k" and 'Creative Commons 0' in params["filter"]
        return {"results": [{"id": 9, "name": "Swoosh", "username": "u", "license": "http://creativecommons.org/licenses/by/4.0/", "previews": {"preview-hq-mp3": "https://x/9.mp3"}},
                            {"id": 10, "name": "Air pass", "username": "u", "license": "http://creativecommons.org/publicdomain/zero/1.0/", "url": "https://freesound.org/s/10/",
                             "previews": {"preview-hq-mp3": "https://cdn.freesound.org/10.mp3"}, "duration": .8}]}
    monkeypatch.setattr(SFX, "_http_json", fake_fs)
    dest = str(tmp_path / "bank")
    got = SFX.fetch("whoosh", "whoosh", n=5, to=dest, freesound_key="k")
    srcs = sorted(s["source"] for s in got)
    assert srcs == ["https://freesound.org/s/10/", "https://freesound.org/s/2/", "https://freesound.org/s/3/"]    # the BY results are refused
    assert SFX.validate(dest) == []
    credits = open(os.path.join(dest, "CREDITS.md"), encoding="utf-8").read()
    assert all(s in credits for s in srcs) and "CC0 1.0" in credits
    info = sf.info(os.path.join(dest, got[0]["file"])); assert info.samplerate == 48000 and info.channels == 1
    assert all(s["id"].startswith("whoosh_") for s in got)
    again = SFX.fetch("whoosh", "whoosh", n=5, to=dest, freesound_key="k")      # idempotent: same sources are not re-added
    assert again == []
    with pytest.raises(SystemExit): SFX.add(os.path.join(dest, got[0]["file"]), "whoosh", licence="by", to=dest)   # CC0 only

def test_user_bank_resolves_in_the_mix(tmp_path, monkeypatch):
    from cves import sfx as SFX
    monkeypatch.setenv("CVES_SFX", str(tmp_path / "ub"))
    p = str(tmp_path / "x.wav"); sf.write(p, (np.sin(np.arange(9600) / 48000 * 2 * np.pi * 300) * .5).astype(np.float32), 48000)
    s = SFX.add(p, "pop", "hard", sid="pop_test", licence="own")
    assert s["bank"] if "bank" in s else True
    assert any(e["id"] == "pop_test" and e["bank"] == "user" for e in SFX.entries())
    assert SFX.pick(SFX.entries(), "pop", "hard")["id"] == "pop_test"
