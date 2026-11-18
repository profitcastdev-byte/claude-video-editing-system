"""Viral mode (docs/VIRAL.md): goal layer, platform profiles, retention gates RET-24..RET-32 and the platform sound slot.
The retention gates run on small synthetic videos made here with ffmpeg (no demo needed); the slot delivery test reuses
the session demo render."""
import os, json, shutil, subprocess, tempfile
import numpy as np, pytest, yaml
from cves import config as C, project, style as STY, platforms as PF, schema
from cves.qc import retention as RT

FPS = 30
W, H = 108, 192


# ------------------------------------------------------------------ synthetic media
def tone(sec, f=220.0, amp=0.3, sr=48000):
    t = np.arange(int(sec * sr)) / sr; return (amp * np.sin(2 * np.pi * f * t)).astype(np.float32)

def silence(sec, sr=48000): return np.zeros(int(sec * sr), np.float32)

def pattern(seed, w=W, h=H):
    """a textured, high-contrast frame (a stand-in for a shot)"""
    rng = np.random.default_rng(seed); small = rng.integers(0, 255, (h // 12, w // 12), np.uint8)
    return np.kron(small, np.ones((12, 12), np.uint8))[:h, :w]

def flat(v, w=W, h=H): return np.full((h, w), v, np.uint8)

def make_video(path, frames, audio=None, fps=FPS, sr=48000):
    """gray frames (list of HxW uint8) + optional mono audio -> small H.264/AAC mp4"""
    import soundfile as sf
    d = tempfile.mkdtemp(prefix="cves_viral_"); a = os.path.join(d, "a.wav")
    n = len(frames); dur = n / fps
    y = np.zeros(int(dur * sr), np.float32) if audio is None else np.pad(audio, (0, max(0, int(dur * sr) - len(audio))))[:int(dur * sr)]
    sf.write(a, y, sr)
    h, w = frames[0].shape
    raw = b"".join(np.repeat(f[:, :, None], 3, 2).tobytes() for f in frames)
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
                    "-i", a, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
                   input=raw, check=True)
    shutil.rmtree(d, ignore_errors=True); return path

def fake_project(tmp, edit=None, timeline=None, elements=None):
    d = os.path.join(str(tmp), "proj"); os.makedirs(os.path.join(d, "Edit"), exist_ok=True)
    with open(os.path.join(d, "Edit", "edit.yaml"), "w", encoding="utf-8") as f: yaml.safe_dump(edit or {}, f)
    if timeline is not None:
        with open(os.path.join(d, "Edit", "timeline.json"), "w", encoding="utf-8") as f: json.dump(timeline, f)
    if elements is not None:
        with open(os.path.join(d, "Edit", "elements.jsonl"), "w", encoding="utf-8") as f: f.writelines(json.dumps(e) + "\n" for e in elements)
    return project.Project(d)

def shots(changes, T, seed0=1):
    """frames for a T s video whose picture changes at each time in `changes` (seconds)"""
    out, k = [], 0; cs = sorted(changes)
    for i in range(int(T * FPS)):
        while k < len(cs) and i / FPS >= cs[k]: k += 1
        out.append(pattern(seed0 + k))
    return out

def gates(pr, video):
    R = []
    RT.run_retention(pr, video, lambda gid, ok, summ, det="", status=None: R.append((gid, status or ("PASS" if ok else "FAIL"), summ, det)))
    return {g: (s, m) for g, s, m, _ in R}


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


# ------------------------------------------------------------------ retention gates on synthetic renders
def test_hook_gate_pass_and_fail(tmp_path):
    good = make_video(str(tmp_path / "good.mp4"), shots([0.5, 1.5, 2.5], 3.0), tone(3.0))
    late = make_video(str(tmp_path / "late.mp4"), shots([1.8, 2.5], 3.0), tone(3.0))
    pr = fake_project(tmp_path / "p", {"goal": "viral"})
    g = gates(pr, good); assert g["RET-24"][0] == "PASS", g["RET-24"]
    g = gates(pr, late); assert g["RET-24"][0] == "WARN" and "1.80" in g["RET-24"][1], g["RET-24"]
    ad = fake_project(tmp_path / "a", {"goal": "ad"})
    assert gates(ad, late)["RET-24"][0] == "WARN"                         # ad allows 1.5 s: 1.8 s still misses
    assert "RET-25" not in gates(ad, late) and "RET-29" not in gates(ad, late)   # viral-only gates are N/A for ads

def test_text_or_subject_by_one_second(tmp_path):
    v = make_video(str(tmp_path / "flat.mp4"), [flat(90)] * int(1.5 * FPS) + [flat(160)] * int(1.5 * FPS), tone(3.0))
    pr = fake_project(tmp_path / "p", {"goal": "viral"})
    assert gates(pr, v)["RET-25"][0] == "WARN"
    els = [{"f": 12, "id": "hook.title", "role": "cutaway", "bbox": [10, 40, 90, 60], "alpha": 1.0, "text": "Wait. Look."}]
    pr2 = fake_project(tmp_path / "q", {"goal": "viral"}, elements=els)
    assert gates(pr2, v)["RET-25"][0] == "PASS"

def test_dead_air_fails_for_viral_and_warns_for_ads(tmp_path):
    audio = np.concatenate([tone(1.0), silence(1.0), tone(1.0)])
    v = make_video(str(tmp_path / "gap.mp4"), shots([0.4, 1.2, 2.0, 2.6], 3.0), audio)
    g = gates(fake_project(tmp_path / "v", {"goal": "viral"}), v)
    assert g["RET-31"][0] == "FAIL" and "longest silence 1.0" in g["RET-31"][1], g["RET-31"]
    assert gates(fake_project(tmp_path / "a", {}), v)["RET-31"][0] == "WARN"
    ok = make_video(str(tmp_path / "full.mp4"), shots([0.4, 1.2, 2.0, 2.6], 3.0), tone(3.0))
    assert gates(fake_project(tmp_path / "w", {"goal": "viral"}), ok)["RET-31"][0] == "PASS"

def test_loop_seam_detected(tmp_path):
    T = 3.0; n = int(T * FPS)
    loop = [pattern(7)] * 15 + [pattern(8)] * (n - 30) + [pattern(7)] * 15        # ends on the shot it starts with
    cut = [pattern(7)] * 15 + [pattern(8)] * (n - 30) + [pattern(9)] * 15
    pr = fake_project(tmp_path / "p", {"goal": "viral", "style": {"structure": {"loop": True}}})
    a = gates(pr, make_video(str(tmp_path / "loop.mp4"), loop, tone(T)))["RET-28"]
    b = gates(pr, make_video(str(tmp_path / "noloop.mp4"), cut, tone(T)))["RET-28"]
    assert a[0] == "PASS" and b[0] == "WARN", (a, b)
    assert "RET-28" not in gates(fake_project(tmp_path / "q", {"goal": "viral"}), make_video(str(tmp_path / "l2.mp4"), loop, tone(T)))   # structure.loop off

def test_interrupt_gaps_measured(tmp_path):
    v = make_video(str(tmp_path / "gaps.mp4"), shots([0.5, 1.0, 4.5], 5.0), tone(5.0))
    pr = fake_project(tmp_path / "p", {"goal": "viral"})
    M = RT.measure(pr, v); ts = [round(t, 2) for t, _ in M["interrupts"]]
    assert ts == [0.5, 1.0, 4.5], ts
    g = gates(pr, v)["RET-26"]
    assert g[0] == "WARN" and "longest gap 3.50 s" in g[1], g                     # viral max 2.5 s
    assert gates(fake_project(tmp_path / "a", {}), v)["RET-26"][0] == "PASS"     # ad max 4.0 s
    # timeline + element-log events merge with the picture changes; a stagger closer than merge_s is one interrupt
    tl = {"segments": [{"id": "a", "t0": 0.0}, {"id": "b", "t0": 1.0}], "cutaways": [{"id": "c1", "start": 2.0, "end": 3.0}], "transitions": []}
    els = [{"f": 75, "id": "c1.item0", "role": "cutaway", "bbox": [0, 0, 1, 1], "alpha": 1}, {"f": 76, "id": "c1.item1", "role": "cutaway", "bbox": [0, 0, 1, 1], "alpha": 1}]
    M = RT.measure(fake_project(tmp_path / "t", {"goal": "viral"}, tl, els), v)
    assert [round(t, 2) for t, _ in M["interrupts"]] == [0.5, 1.0, 2.0, 2.5, 3.0, 4.5]

def test_effect_soup_flagged(tmp_path):
    busy = [0.2 + 0.1 * k for k in range(25)]                                   # a change every 3 frames for 2.5 s
    v = make_video(str(tmp_path / "soup.mp4"), shots(busy, 3.0), tone(3.0))
    g = gates(fake_project(tmp_path / "p", {"goal": "viral"}), v)["RET-27"]
    assert g[0] == "WARN", g
    assert RT.soup_runs([0.1, 0.2, 0.3, 1.5, 3.0], 0.3, 1.5) == []

def test_payoff_and_platform_duration(tmp_path):
    v = make_video(str(tmp_path / "pay.mp4"), shots([0.5, 1.5, 2.5, 3.6], 4.0), np.concatenate([tone(3.4, amp=.05), tone(0.6, amp=.4)]))
    pr = fake_project(tmp_path / "p", {"goal": "viral", "style": {"platform": {"target": "tiktok"}}})
    g = gates(pr, v)
    assert g["RET-29"][0] == "PASS", g["RET-29"]
    assert g["RET-30"][0] == "WARN" and "ideal 9-34" in g["RET-30"][1]          # 4 s: under TikTok's ideal band, under its max


# ------------------------------------------------------------------ the platform sound slot
def test_ads_reject_the_platform_slot(tmp_path):
    pr = fake_project(tmp_path / "a", {"music": {"slot": "platform", "guide": 120}})
    errs, _ = schema.validate(pr); assert any(e.startswith("music.slot") and "goal: viral" in e for e in errs), errs
    pr = fake_project(tmp_path / "v", {"goal": "viral", "music": {"slot": "platform"}})
    errs, _ = schema.validate(pr); assert any(e.startswith("music.guide") for e in errs), errs
    pr = fake_project(tmp_path / "w", {"goal": "viral", "music": {"slot": "platform", "guide": "120 bpm"}})
    errs, _ = schema.validate(pr); assert not [e for e in errs if e.startswith(("music", "goal"))], errs
    pr = fake_project(tmp_path / "x", {"goal": "sometimes"})
    errs, _ = schema.validate(pr); assert any(e.startswith("goal") for e in errs), errs

def test_slot_platform_delivers_music_free_master_guide_and_posting(demo_rendered, tmp_path):
    import soundfile as sf
    from cves import mix, encode, deliver, qc
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
    R = []
    RT.run_retention(pr, master, lambda gid, ok, s, det="", status=None: R.append((gid, status or ("PASS" if ok else "FAIL"), s, det)))
    g = {x[0]: x for x in R}
    assert "RET-32" in g and "guide (bpm, 100.0 BPM)" in g["RET-32"][2], g.get("RET-32")
    assert g["RET-30"][1] in ("PASS", "WARN") and g["RET-31"][1] != "FAIL", (g["RET-30"], g["RET-31"])
    qc.write_stamp(pr, master, [])        # the full QC run is covered elsewhere; deliver only needs a clean stamp for this master
    final, man = deliver.deliver(pr, only="master")
    files = os.listdir(final)
    assert "POSTING.md" in files and any(f.endswith(".guide.wav") for f in files), files
    post = open(os.path.join(final, "POSTING.md"), encoding="utf-8").read()
    assert "no music on purpose" in post and "Demo trend sound" in post and "100.0 BPM" in post and "0:04.80" in post, post
    assert man["music_slot"]["slot"] == "platform" and man["music_slot"]["platform"] == "tiktok"
