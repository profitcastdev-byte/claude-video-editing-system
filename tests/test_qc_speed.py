"""QC speed work (docs/QC.md "Speed", DECISIONS.md "QC speed"): every shortcut must give the gates exactly what the slow
path gave them. Plus the draft tier (never a delivery stamp) and the GFX-08 / FRAME-03 definitions from the first real job."""
import os, json, shutil, subprocess, numpy as np, pytest, cv2
from cves import project, config as C
from cves.qc import extra as X, cache as QCC


def master(d): return next(os.path.join(d, "Export", f) for f in sorted(os.listdir(os.path.join(d, "Export"))) if f.endswith(".mp4"))


# ---------------------------------------------------------------- pure helpers (fast)
def test_longest_runs_matches_the_row_loop():
    rng = np.random.default_rng(3)
    for p in (.1, .5, .9, 1.0, 0.0):
        A = rng.random((37, 53)) < p
        assert X.longest_runs(A).tolist() == [X.longest_run(r) for r in A]


@pytest.fixture(autouse=True)
def _canvas_1080(monkeypatch):
    """the module globals run_extra sets per video: a 1080 short side for the pure-helper tests"""
    monkeypatch.setattr(X, "U_", 1.0); monkeypatch.setattr(X, "W", X.W); monkeypatch.setattr(X, "H", X.H)


def _inst(iid, boxes, f0=100, role="cutaway"):
    return X.Inst(iid, [{"id": iid, "role": role, "f": f0 + j, "bbox": list(b), "alpha": 1.0} for j, b in enumerate(boxes)])


def test_gfx08_flags_two_rows_at_rest_4px_apart():
    a = _inst("card.row0", [[134, 445, 945, 643]] * 40)
    b = _inst("card.row1", [[138, 623, 951, 804]] * 40)          # left edges 4 px apart, centres 5 px: a real near miss
    static, pairs = X.gfx08([a, b], 60, lambda f: None)
    assert pairs and any("left edges 4 px apart" in p for p in pairs), pairs


def test_gfx08_ignores_a_row_still_settling_into_alignment():
    a = _inst("card.row0", [[134, 445, 945, 643]] * 60)
    # outExpo tail: < 1 px per frame for ~0.4 s while 2-8 px from rest, then at rest on row0's left edge
    xs = [142, 141, 141, 140, 140, 139, 139, 139, 138, 138, 138, 137, 137, 137, 136, 136, 136, 135, 135, 135, 135, 134, 134, 134, 134]
    b = _inst("card.row1", [[x, 623, 945, 804] for x in xs] + [[134, 623, 945, 804]] * 35)
    static, pairs = X.gfx08([a, b], 60, lambda f: None)
    assert not pairs, pairs
    rest = X.settled_boxes(b.bb)
    assert (rest[:, 0] == 134).all()


def _fake_cx(W, H, face):
    class CX:
        FPS = 30.0; cuts = []; by_f = {}
        def __init__(self): self._results = {"aroll": []}
        def aroll_M(self, f): return np.float32([[1, 0, 0], [0, 1, 0]]), {"id": "s0"}, f, face
        def in_snap(self, f): return False
        def is_aroll(self, f): return True
    return CX()


def _halo_case(ring_boost, scene_ring=0):
    """a synthetic A-roll frame: a bright subject on a uniform wall; `ring_boost` Y added 3-7 px outside the matte in the
    OUTPUT only (a pipeline halo), `scene_ring` in the graded reference too (the room: the scene, not a halo)"""
    W, H = 240, 400
    X.W, X.H = W, H
    m = np.zeros((H, W), np.uint8); cv2.ellipse(m, (120, 230), (60, 150), 0, 0, 360, 255, -1)
    d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
    ref = np.where(m > 0, 180, 90).astype(float); ref[(d >= 3) & (d <= 7)] += scene_ring
    out = ref.copy(); out[(d >= 3) & (d <= 7)] += ring_boost
    yuv = np.stack([np.clip(np.round(out), 0, 255).astype(np.uint8), np.full((H, W), 128, np.uint8), np.full((H, W), 128, np.uint8)])
    cx = _fake_cx(W, H, [60, 80, 120, 150] + [0] * 10)
    X.aroll_frame(cx, 0, yuv, m, None, np.clip(np.round(ref), 0, 255).astype(np.uint8))
    rows = []
    X.gates_frame_colour(type("C", (), dict(_results={"aroll": cx._results["aroll"]}, cuts=[], FPS=30.0, is_aroll=lambda self, f: True))(),
                         lambda gid, ok, s, det="", status=None: rows.append((gid, status or ("PASS" if ok else "FAIL"), s)))
    return cx._results["aroll"][0]["halo"], dict((g, st) for g, st, _ in rows)


def test_frame03_injected_bright_ring_fails():
    halo, st = _halo_case(ring_boost=30)
    assert halo[0] > 20 and st["FRAME-03"] == "FAIL", (halo, st)


def test_frame03_global_grade_and_scene_edges_cancel():
    halo, st = _halo_case(ring_boost=0, scene_ring=12)                 # the room has a bright strip next to the head
    assert halo[0] <= 1.0 and st["FRAME-03"] == "PASS", (halo, st)
    halo, st = _halo_case(ring_boost=0, scene_ring=-20)                # a ring darker than its wall is no halo
    assert halo[0] <= 1.0 and st["FRAME-03"] == "PASS", (halo, st)


def test_whisper_transcripts_are_cached_by_audio_bytes(tmp_path, monkeypatch):
    from cves.qc import audio_gates as AG
    w = tmp_path / "a.wav"; w.write_bytes(b"RIFF fake audio")
    calls = []
    class R:
        returncode = 0; stdout = " hello there"
    monkeypatch.setattr(AG.subprocess, "run", lambda cmd, **k: calls.append(cmd) or R())
    monkeypatch.setattr(QCC, "WHISPER_DIR", str(tmp_path / "wc"))
    assert AG._whisper(str(w), lang="en") == " hello there" and AG._whisper(str(w), lang="en") == " hello there"
    assert len(calls) == 1                                        # the second call is served from Edit/qc_cache/whisper
    AG._whisper(str(w), lang="hi"); assert len(calls) == 2        # another language = another key
    w.write_bytes(b"RIFF other audio"); AG._whisper(str(w), lang="en"); assert len(calls) == 3


# ---------------------------------------------------------------- shared decodes are byte-identical (rendered demo)
@pytest.mark.e2e
def test_plate_gop_decode_matches_a_full_decode(demo_built):
    import av
    pr = project.Project(demo_built)
    for d in ("plate", "matte"):
        for f in sorted(os.listdir(pr.e(d)))[:2]:
            p = pr.e(d, f); ks = set(range(0, 60, 6)) | {13}
            ref = {}
            with av.open(p) as c:
                for k, fr in enumerate(c.decode(video=0)):
                    if k in ks: ref[k] = fr.to_ndarray(format="gray")
                    if k >= max(ks): break
            got = X.decode_plate_frames(None, p, ks)
            assert set(got) == set(ref) and all(np.array_equal(got[k], ref[k]) for k in ref)


def test_media_pass_equals_the_separate_commands(demo_rendered, tmp_path, monkeypatch):
    from cves import qc
    from cves.qc import retention as RT
    monkeypatch.setenv("CVES_QC_CACHE", "off")
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d, ignore=shutil.ignore_patterns("frames"))
    pr = project.Project(d); v = master(d)
    frames, fps = RT.decode_gray(v)
    M = qc.media_pass(pr, v, frames.shape[1:][::-1])
    assert np.array_equal(M["ret"], frames)
    ff = C.get("ffmpeg")
    bd = subprocess.run([ff, "-hide_banner", "-i", v, "-vf", "blackdetect=d=0.03:pix_th=0.10", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    import re
    assert M["blk"] == [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)]
    Y = np.frombuffer(subprocess.run([ff, "-v", "error", "-i", v, "-vf", "select='not(mod(n,12))',extractplanes=y", "-fps_mode", "passthrough", "-f", "rawvideo",
                                      "-pix_fmt", "gray", "pipe:1"], capture_output=True).stdout, np.uint8)
    assert M["ysize"] == Y.size and M["pct"] == float(((Y < 16) | (Y > 235)).mean() * 100) and M["ext"] == int(((Y < 5) | (Y > 246)).sum())


# ---------------------------------------------------------------- full QC: serial == parallel == cached; the draft tier
def _stamp(pr): return json.load(open(pr.e("qc.json"), encoding="utf-8"))

def test_parallel_and_cached_qc_equal_the_serial_run(demo_rendered, tmp_path, monkeypatch):
    from cves import qc
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d, ignore=shutil.ignore_patterns("frames", "qc_cache"))
    pr = project.Project(d); v = master(d)
    monkeypatch.setenv("CVES_QC_PROCS", "0"); monkeypatch.setenv("CVES_QC_JOBS", "1"); monkeypatch.setenv("CVES_QC_CACHE", "off")
    nf0, rep0 = qc.run(pr, v, fast=True); s0 = _stamp(pr)
    monkeypatch.delenv("CVES_QC_PROCS"); monkeypatch.delenv("CVES_QC_JOBS"); monkeypatch.delenv("CVES_QC_CACHE")
    nf1, rep1 = qc.run(pr, v, fast=True); s1 = _stamp(pr)                # parallel, fills Edit/qc_cache/
    assert os.path.isdir(pr.e("qc_cache"))
    nf2, rep2 = qc.run(pr, v, fast=True); s2 = _stamp(pr)                # served from the cache
    strip = lambda r: r.split("\n", 1)[1]
    assert strip(rep0) == strip(rep1) == strip(rep2)
    assert s0["gates"] == s1["gates"] == s2["gates"] and nf0 == nf1 == nf2


def test_draft_tier_never_stamps_and_matches_the_full_gates(demo_rendered, tmp_path):
    from cves import qc, deliver
    from cves.qc.tiers import DRAFT
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d, ignore=shutil.ignore_patterns("frames"))
    pr = project.Project(d); v = master(d)
    if os.path.exists(pr.e("qc.json")): os.remove(pr.e("qc.json"))
    nf, rep = qc.run(pr, v, tier="draft")
    assert rep.startswith("DRAFT QC (NOT DELIVERABLE)") and "never stamps" in rep
    assert not os.path.exists(pr.e("qc.json")) and os.path.exists(pr.e("qc_draft.json")) and os.path.exists(pr.e("QC-DRAFT.txt"))
    dr = json.load(open(pr.e("qc_draft.json"), encoding="utf-8")); assert dr["tier"] == "draft" and dr["deliverable"] is False
    assert {g["id"] for g in dr["gates"]} <= DRAFT and len(dr["gates"]) >= 30
    with pytest.raises(SystemExit): deliver.deliver(pr)                 # a draft is no stamp: delivery refuses
    with pytest.raises(ValueError): qc.write_stamp(pr, v, [], tier="draft")
    qc.run(pr, v, fast=True); full = {g["id"]: g for g in _stamp(pr)["gates"]}
    for g in dr["gates"]:                                               # every draft gate is the full gate, measured the same way
        assert full[g["id"]]["status"] == g["status"] and full[g["id"]]["summary"] == g["summary"], g["id"]
