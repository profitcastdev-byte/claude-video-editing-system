import os, json, re, subprocess, pytest
from cves import project, config as C

def probe(path):
    return json.loads(subprocess.run([C.get("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,sample_rate",
                                      "-of", "json", path], capture_output=True, text=True).stdout)["streams"]

def master(d): return next(os.path.join(d, "Export", f) for f in os.listdir(os.path.join(d, "Export")) if f.endswith(".mp4"))

def test_encode_follows_the_project_timebase(demo_rendered):
    v = next(s for s in probe(master(demo_rendered)) if s["codec_type"] == "video")
    assert (v["width"], v["height"]) == (1080, 1920) and v["r_frame_rate"] == "30/1"     # the demo is 30 fps, not 23.976

def test_mix_loudness(demo_rendered):
    r = subprocess.run([C.get("ffmpeg"), "-hide_banner", "-i", os.path.join(demo_rendered, "Edit", "mix.wav"), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); P = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    assert -14.6 <= I <= -13.4 and P <= -0.9, (I, P)

def test_qc_runs_and_stamps(demo_rendered):
    from cves import qc
    pr = project.Project(demo_rendered); nf, report = qc.run(pr, master(demo_rendered), fast=True)
    st = json.load(open(pr.e("qc.json"), encoding="utf-8"))
    assert st["sha256"] == qc.sha256(master(demo_rendered)) and st["fail"] == nf
    ids = {g["id"] for g in st["gates"]}
    assert len(ids) >= 70 and "not measured" not in " ".join(g["summary"] for g in st["gates"] if g["id"].startswith(("CUT", "SND-0"))), report
    for gid in ("DEL-01", "DEL-02", "DEL-03", "SND-01", "SND-02", "CUT-05", "SND-08", "SND-09", "MOT-07", "MOT-12", "GFX-17"):
        g = next((g for g in st["gates"] if g["id"] == gid), None)
        assert g and g["status"] != "FAIL", f"{gid}: {g}"

def test_deliver_refuses_without_a_passing_stamp(demo_rendered, tmp_path):
    import shutil
    from cves import deliver
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d, ignore=shutil.ignore_patterns("frames"))
    pr = project.Project(d); st = pr.e("qc.json")
    if os.path.exists(st): os.remove(st)
    with pytest.raises(SystemExit): deliver.deliver(pr)
