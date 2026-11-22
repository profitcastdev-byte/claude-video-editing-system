import os, json, re, subprocess
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

def test_deliver_delivers_the_master_without_any_check(demo_rendered, tmp_path):
    import shutil
    from cves import deliver
    d = str(tmp_path / "p"); shutil.copytree(demo_rendered, d, ignore=shutil.ignore_patterns("frames"))
    pr = project.Project(d)
    out, man = deliver.deliver(pr, only="master")
    assert os.path.basename(out) == "v001" and man["master_sha256"] == deliver.sha256(master(d))
    names = {f["path"] for f in man["files"]}
    assert os.path.basename(master(d)) in names and any(n.endswith(".srt") for n in names)
