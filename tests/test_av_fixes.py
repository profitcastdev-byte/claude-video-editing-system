"""Timing, audio and colour fixes from the first 60 fps client job (CHANGELOG [Unreleased] "AV"): SFX cue sync onto the
logged picture events, caption fragments round cutaways, the adaptive voice gate, the per-shot colour match and the
band-aware vocal-to-music guard. Synthetic media only."""
import os, sys, json, types
import numpy as np, soundfile as sf, yaml, pytest, cv2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))

SR = 48000


# ------------------------------------------------------------------ helpers
def _project(tmp, fps=60.0, n=240, elements=(), cutaways=(), edit=None):
    """a minimal rendered project: timeline.json + elements.jsonl (one record per (id, frame))"""
    d = tmp / "proj"
    for f in ("Edit", "Music/sfx", "Raw"): (d / f).mkdir(parents=True, exist_ok=True)
    (d / "Edit" / "edit.yaml").write_text(yaml.safe_dump(edit or {}), encoding="utf-8")
    tl = {"spine": "aroll", "fps": fps, "fps_rational": [int(fps), 1], "size": [1080, 1920], "frames": n, "a_frames": n,
          "segments": [{"id": "s0", "t0": 0.0, "t1": n / fps, "f0": 0, "n": n}], "cutaways": list(cutaways), "transitions": [],
          "snap": None, "zoom": {}, "creep": 0}
    (d / "Edit" / "timeline.json").write_text(json.dumps(tl), encoding="utf-8")
    with open(d / "Edit" / "elements.jsonl", "w", encoding="utf-8") as fh:
        for eid, f0, f1 in elements:
            for f in range(f0, f1):
                fh.write(json.dumps({"f": f, "id": eid, "role": "cutaway", "bbox": [100, 100, 300, 200], "alpha": 1.0}) + "\n")
    return d

def _pop(path, onset_s=0.025, dur=0.3):
    """a click with silence before it: its onset (10 % of the 10 ms RMS peak) sits ~onset_s into the file"""
    n = int(dur * SR); y = np.zeros(n); k = int(onset_s * SR); m = int(.04 * SR)
    t = np.arange(m) / SR; y[k:k + m] = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 90) * .8
    sf.write(path, y, SR)

def _tl(d, fps=60.0):
    from cves import project, style as STY
    pr = project.Project(str(d))
    return types.SimpleNamespace(pr=pr, S=STY.load(pr), FPS=fps, root=ROOT)


# ------------------------------------------------------------------ 1. SND-07: cue onsets land on their picture event at 60 fps
def test_cue_sync_puts_onsets_on_element_entries_at_60fps(tmp_path):
    from cves import sound as SO
    from cves import events as X
    d = _project(tmp_path, elements=[("card.title", 37, 120), ("card.row0", 90, 200)])
    _pop(str(d / "Music" / "sfx" / "tpop.wav"))
    TL = _tl(d); on = SO.onset_offset(str(d / "Music" / "sfx" / "tpop.wav"))
    assert on * 60 > 1.0              # the file's onset alone is more than a frame late at 60 fps (the bug)
    cues = [(37 / 60, "tpop", -18, {}),                 # quantised to the entry frame: onset 1.5 f late before the fix
            (93 / 60, "tpop", -18, {}),                 # a template that asked 3 frames late
            (170 / 60, "tpop", -18, {}),                # no picture event within 6 frames: keeps its time
            (60 / 60, "tpop", -18, {"sync": False})]    # opted out
    log = []; out = SO.sync_cues(TL, cues, log)
    t = {round(c[0], 6): c for c in out}
    onsets = sorted((c[0] + on) * 60 for c in out)
    assert any(abs(x - 37) < .02 for x in onsets) and any(abs(x - 90) < .02 for x in onsets)
    assert round(170 / 60, 6) in t and round(1.0, 6) in t
    assert len(log) == 2 and all("appears" in r["event"] for r in log)
    # every synced onset within 1 frame of a visual event (here: exactly on it)
    cx = X.Ctx(TL.pr, None); evt = np.array([e[0] for e in X.visual_events(cx)])
    for c in out:
        if c[3].get("synced"): assert np.min(np.abs((c[0] + on - evt) * 60)) < .05

def test_cue_sync_is_exact_at_30_and_60_fps(tmp_path):
    """the same template time, two frame rates: the onset is on the entry frame at both (no 30 fps tuning left)"""
    from cves import sound as SO
    for fps in (30.0, 60.0):
        sub = tmp_path / f"f{int(fps)}"; sub.mkdir()
        f0 = int(round(.6 * fps)); d = _project(sub, fps=fps, n=int(4 * fps), elements=[("x.title", f0, f0 + 30)])
        _pop(str(d / "Music" / "sfx" / "tpop.wav"), onset_s=.031)
        TL = _tl(d, fps); on = SO.onset_offset(str(d / "Music" / "sfx" / "tpop.wav"))
        (t, *_), = SO.sync_cues(TL, [(f0 / fps, "tpop", -18, {})])
        assert abs((t + on) * fps - f0) < .02, fps

def test_cue_sync_leaves_peak_placed_cues_alone(tmp_path):
    from cves import sound as SO
    d = _project(tmp_path, elements=[("a", 30, 60)]); _pop(str(d / "Music" / "sfx" / "tpop.wav"))
    TL = _tl(d); c = (0.48, "tpop", -18, {"peak_at": 0.5})
    assert SO.sync_cues(TL, [c]) == [c]

def test_cue_sync_off_switch(tmp_path):
    from cves import sound as SO
    d = _project(tmp_path, elements=[("a", 30, 60)], edit={"style": {"sound": {"cue_sync": False}}}); _pop(str(d / "Music" / "sfx" / "tpop.wav"))
    TL = _tl(d); c = (30 / 60, "tpop", -18, {})
    assert SO.sync_cues(TL, [c]) == [c]


# ------------------------------------------------------------------ 2. captions: no fragment flashes round a cutaway
def _hidden(lo, hi):
    return lambda f: lo <= f < hi                   # a full-screen cutaway over frames lo..hi-1

def _runs(events, hidden, fps):
    """[(event start, frames in one unbroken visible run, text)] for every visible run of every event"""
    import math
    out = []
    for a, b, ws in events:
        fr = [f for f in range(int(math.ceil(a * fps - 1e-6)), int(math.ceil(b * fps - 1e-6))) if not hidden(f)]
        run = []
        for f in fr + [None]:
            if run and (f is None or f != run[-1] + 1): out.append((a, len(run), " ".join(w for w, _ in ws))); run = []
            if f is not None: run.append(f)
    return out

def test_caption_tail_after_a_cutaway_is_skipped_when_its_words_were_covered():
    from cves import captions as CAP
    fps = 60.0; hid = _hidden(120, 600)            # cutaway 2.0 s - 10.0 s
    ev = [(1.0, 2.5, [("Every", 1.03), ("single", 1.4), ("month", 1.7)]),
          (2.5, 10.01, [("four", 2.53), ("to", 4.0), ("six", 6.0), ("cases.", 9.0)]),       # visible for 1 frame after the cover
          (10.01, 11.5, [("We", 10.03), ("show", 10.4), ("ads.", 10.9)])]
    assert any(n == 1 for _, n, _ in _runs(ev, hid, fps))                                    # the bug: a 1-frame caption
    log = []; out = CAP.schedule(ev, hid, fps, {"min_on_s": .83}, log)
    assert all(n / fps >= .83 for _, n, _ in _runs(out, hid, fps))
    assert [w for _, _, ws in out for w, _ in ws] == [w for _, _, ws in ev for w, _ in ws]   # no word dropped from the list
    assert log and log[0]["action"].startswith("skipped")
    nxt = next(e for e in out if e[2][0][0] == "We")
    assert abs(nxt[0] - 10.0) < 1e-6                     # starts on the cut: no caption-less frame after it (first word 2 f later)

def test_caption_words_still_to_be_said_after_a_cutaway_move_into_the_next_event():
    from cves import captions as CAP
    fps = 60.0; hid = _hidden(120, 600)
    ev = [(2.2, 10.2, [("Book", 2.23), ("your", 9.3), ("free", 10.03)]),                     # 12 frames after the cover
          (10.2, 12.0, [("consult", 10.23), ("today", 11.0)])]
    log = []; out = CAP.schedule(ev, hid, fps, {"min_on_s": .83, "max_chars": 34}, log)
    runs = _runs(out, hid, fps)
    assert all(n / fps >= .83 for _, n, _ in runs)
    assert runs[-1][2] == "free consult today"           # 'free' is shown with the next words, not lost
    assert "merged" in log[0]["action"]

def test_caption_flash_before_a_cutaway_is_held_by_the_previous_event():
    from cves import captions as CAP
    fps = 60.0; hid = _hidden(300, 900)            # cutaway 5.0 s - 15.0 s
    ev = [(3.0, 4.97, [("If", 3.03), ("your", 3.5), ("clinic", 4.0)]),
          (4.97, 16.2, [("got", 4.99), ("this", 15.2), ("every", 15.5)])]                   # flashes 2 frames before the cover
    assert any(n <= 2 for _, n, _ in _runs(ev, hid, fps))
    log = []; out = CAP.schedule(ev, hid, fps, {"min_on_s": .83}, log)
    runs = _runs(out, hid, fps)
    assert all(n / fps >= .83 for _, n, _ in runs)
    assert runs[0][2] == "If your clinic got"            # held on screen with the word it would have flashed
    assert runs[1][2] == "this every"

def test_caption_schedule_keeps_events_that_do_not_touch_a_cover():
    from cves import captions as CAP
    ev = [(0.0, 0.5, [("Hi", .03)]), (0.5, 3.0, [("there", .53)])]
    assert CAP.schedule(ev, lambda f: False, 60.0, {"min_on_s": .83}) == ev


# ------------------------------------------------------------------ 3. SND-19: the adaptive gate on noise + tone
def _speech_like(seed, noise_db, n_words=14):
    """'words' (harmonic tone bursts at about -18 dBFS) separated by short gaps of room noise at noise_db"""
    rng = np.random.default_rng(seed); parts, mask = [], []
    for j in range(n_words):
        L = int(rng.uniform(.18, .4) * SR); t = np.arange(L) / SR
        env = np.minimum(1, t / .01) * np.minimum(1, (L / SR - t) / .03)
        w = sum(np.sin(2 * np.pi * f * t) / k for k, f in enumerate((180, 360, 720, 1440, 2880), 1)) * .12 * env
        parts.append(w); mask.append(np.ones(L, bool))
        G = int(rng.uniform(.06, .16) * SR); parts.append(np.zeros(G)); mask.append(np.zeros(G, bool))
    y = np.concatenate(parts); m = np.concatenate(mask)
    from scipy.signal import butter, sosfilt
    nz = sosfilt(butter(2, [200, 5000], "band", fs=SR, output="sos"), rng.standard_normal(len(y)))
    nz *= 10 ** (noise_db / 20) / np.sqrt(np.mean(nz ** 2))
    return y + nz, m

def _p5(y):
    h = int(.02 * SR); d = 20 * np.log10(np.array([np.sqrt(np.mean(y[i:i + h] ** 2)) for i in range(0, len(y) - h, h)]) + 1e-9)
    return float(np.percentile(d, 5))

def test_adaptive_gate_pulls_the_room_under_minus_60_and_keeps_the_words():
    from cves import voicegate as VG
    y, words = _speech_like(1, -48)
    assert _p5(y) > -60                                   # a room a fixed gate leaves in
    out, info = VG.apply(y, SR, [(0, len(y), "take")])
    assert _p5(out) <= -60, info
    # words keep their level (inner part of each word, away from the ramps)
    from scipy.ndimage import binary_erosion
    core = binary_erosion(words, np.ones(int(.04 * SR)))
    loss = 20 * np.log10(np.sqrt(np.mean(out[core] ** 2)) / np.sqrt(np.mean(y[core] ** 2)))
    assert loss > -0.5, loss
    # no clicks: the gain never jumps more than the depth over the attack ramp (no sample-to-sample steps)
    g = np.abs(out) / np.maximum(np.abs(y), 1e-9); assert np.isfinite(g).all()

def test_adaptive_gate_threshold_follows_each_room():
    from cves import voicegate as VG
    quiet, _ = _speech_like(2, -55); loud, _ = _speech_like(3, -40)
    y = np.concatenate([quiet, loud]); n = len(quiet)
    out, info = VG.apply(y, SR, [(0, n, "quiet"), (n, len(y), "loud")])
    assert info["loud"]["floor_db"] > info["quiet"]["floor_db"] + 8
    assert info["loud"]["open_db"] > info["quiet"]["open_db"] + 8          # measured, not fixed
    assert info["loud"]["range_db"] > info["quiet"]["range_db"]             # a louder room needs more depth to reach the target
    assert _p5(out[n:]) <= -60 and _p5(out[:n]) <= -60

def test_voice_chain_records_the_adaptive_gate_as_non_generative():
    from cves import ingest as I
    assert "agate" not in I.voice_af()                                    # the fixed gate is gone from the ffmpeg chain


# ------------------------------------------------------------------ 4. COL-06 / 07: two shots, different white balance
def _shot(wb, skin=(.72, .50, .42), wall=(.62, .60, .56), h=480, w=270):
    """a display-referred frame: a wall and a face ellipse (the subject matte) in linear light scaled by the white
    balance wb, + its matte and a face row (box + 5 YuNet landmarks) for the cheek patches"""
    from cves import shotmatch as SM
    lin_s, lin_w = SM.eotf(np.array(skin)) * wb, SM.eotf(np.array(wall)) * wb
    img = np.ones((h, w, 3)) * SM.oetf(lin_w)
    yy, xx = np.mgrid[0:h, 0:w]; sub = ((xx - w / 2) / 70) ** 2 + ((yy - 220) / 110) ** 2 <= 1
    sub |= (yy > 320) & (np.abs(xx - w / 2) < 110)                        # shoulders: the matte reaches the bottom
    img[sub] = SM.oetf(lin_s)
    matte = (sub * 255).astype(np.uint8)
    face = [w / 2 - 60, 140, 120, 160, w / 2 - 30, 190, w / 2 + 30, 190, w / 2, 220, w / 2 - 25, 260, w / 2 + 25, 260]
    return img.astype(np.float32), matte, face

def _lab(rgb): return cv2.cvtColor(np.asarray(rgb, np.float32).reshape(1, 1, 3), cv2.COLOR_RGB2Lab)[0, 0]

def test_colour_match_removes_a_white_balance_shift_between_two_shots():
    from cves import shotmatch as SM
    A, mA, fA = _shot(np.array([1.0, 1.0, 1.0]))
    B, mB, fB = _shot(np.array([1.18, 1.0, .82]) * .9)                  # warmer and darker take
    lin = lambda x: None if x is None else SM.eotf(x)
    ref = {"skin": lin(SM.skin_rgb(A, fA)), "wall": lin(SM.wall_rgb(A, mA, fA, near=10, far=80))}
    src = {"skin": lin(SM.skin_rgb(B, fB)), "wall": lin(SM.wall_rgb(B, mB, fB, near=10, far=80))}
    assert src["wall"] is not None and ref["wall"] is not None
    d_before = np.linalg.norm(_lab(SM.skin_rgb(A, fA)) - _lab(SM.skin_rgb(B, fB)))
    assert d_before > 5
    gs, gb = SM.gains(src, ref)
    M = {"B": {"k": [0, 10], "gs": [gs.tolist()] * 2, "gb": [gb.tolist()] * 2}}
    C = SM.apply(M, "B", 5, B, mB)
    for k, (pa, pc) in {"skin": (SM.skin_rgb(A, fA), SM.skin_rgb(C, fB)), "wall": (SM.wall_rgb(A, mA, fA, 10, 80), SM.wall_rgb(C, mB, fB, 10, 80))}.items():
        assert np.linalg.norm(_lab(pa) - _lab(pc)) < 1.5, k               # COL-06: direct cuts <= 3
    ya, yc = (np.array(SM.skin_rgb(x, fA)) @ [.2126, .7152, .0722] for x in (A, C))
    assert abs(yc / ya - 1) < .02                                          # COL-07: skin Y within 6 %

def test_colour_match_never_lifts_black_and_stays_monotonic():
    from cves import shotmatch as SM
    ramp = np.linspace(0, 1, 257, dtype=np.float32)[None, :, None].repeat(3, 2)
    for g in (.7, 1.0, 1.45):
        out = SM.apply({"s": {"k": [0], "gs": [[g] * 3], "gb": [[g] * 3]}}, "s", 0, ramp)
        assert out[0, 0].max() < 1e-3                                      # black stays black (no muddy lift)
        assert (np.diff(out[0, :, 0]) >= -1e-6).all()

def test_colour_match_split_between_subject_and_wall_is_limited():
    from cves import shotmatch as SM
    gs, gb = SM.gains({"skin": np.array([.5, .3, .2]), "wall": np.array([.2, .2, .2])}, {"skin": np.array([.25, .15, .1]), "wall": np.array([.3, .3, .3])}, split_max=.18)
    assert np.all(np.abs(np.log(gs) - np.log(gb)) <= .18 + 1e-9)

def test_colour_match_smooths_drift_inside_a_shot():
    """a shot whose light drifts slowly is followed; a one-sample landmark glitch is not chased"""
    from cves import shotmatch as SM
    ks = list(range(0, 240, 4)); ref = {"skin": np.array([.3, .2, .15]), "wall": np.array([.25, .25, .24])}
    rows = []
    for k in ks:
        d = 1 + .2 * k / 240                                             # +20 % over the shot
        s = ref["skin"] * d * (1.6 if k == 120 else 1)                  # a glitch at k = 120
        rows.append((k, s, ref["wall"] * d))
    meas = {"ref": [(k, ref["skin"], ref["wall"]) for k in ks], "drift": rows}
    stats = {"ref": dict(ref), "drift": {"skin": np.median([r[1] for r in rows], 0), "wall": np.median([r[2] for r in rows], 0)}}
    c = SM.cfg_of({"grade": {"shot_match_drift": 1.0, "shot_match_smooth_s": .5}})
    M = SM.corrections(meas, stats, "ref", c, 60.0)
    g = np.array(M["drift"]["gs"])[:, 1]; k = np.array(M["drift"]["k"])
    assert g[0] > g[-1] * 1.1                                            # follows the drift (brighter later -> lower gain)
    assert abs(g[k == 120][0] - np.interp(120, k[k != 120], g[k != 120])) < .03     # the glitch is not chased


# ------------------------------------------------------------------ 5. masking: the bed's speech band clears every word
def test_vmr_guard_guarantees_the_vocal_to_music_ratio_while_speaking():
    from cves import sound as SO, style as STY
    rng = np.random.default_rng(5); N = 6 * SR; t = np.arange(N) / SR
    vo = np.zeros(N); words = []
    for a in np.arange(.3, 3.5, .7):
        i, j = int(a * SR), int((a + .45) * SR); vo[i:j] = sum(np.sin(2 * np.pi * f * t[i:j]) for f in (220, 1200, 2400, 3300)) * .05
        words.append([a, a + .45, "w"])
    from scipy.signal import butter, sosfilt
    bright = sosfilt(butter(2, [900, 4500], "band", fs=SR, output="sos"), rng.standard_normal(N)) * .12   # a busy, bright bed
    mus = np.stack([bright, bright], 1).astype(np.float32)
    S = STY.Style({"mix": {"vmr_min_db": 8.0}})
    def vmr(m):
        pv = SO._band_power(vo, SR, 1000, 4000, .4, .1); pm = SO._band_power(m.sum(1) / np.sqrt(2), SR, 1000, 4000, .4, .1)
        tt = np.arange(len(pv)) * .1; sp = np.array([any(a - .05 <= x <= b + .05 for a, b, _ in words) for x in tt])
        r = 10 * np.log10(pv[sp] / pm[sp]); return r, tt, sp
    r0, _, _ = vmr(mus); assert (r0 < 6).mean() > .3                       # masked before
    out, info = SO.vmr_guard(vo, mus, SR, S, words)
    r1, tt, sp = vmr(out)
    assert (r1 < 6).mean() <= .1, info                                       # at most 10 % of speech windows under 6 dB
    assert np.median(r1) >= 8 - .5 and np.median(r1) > np.median(r0) + 5
    # away from speech the bed is untouched
    far = np.ones(N, bool)
    for a, b, _ in words: far[max(0, int((a - 1.5) * SR)):int((b + 1.5) * SR)] = False      # 6 release time constants
    assert far.any() and np.allclose(out[far], mus[far], atol=2e-3)
