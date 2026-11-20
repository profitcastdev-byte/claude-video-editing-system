"""Compact CLI output (engine/cves/out.py, tlist.py, status.py): summaries, noise filter, one-line errors, --json."""
import os, sys, json, subprocess
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REPORT = """QC REPORT  x.mp4  (12.00 s, 1080x1920, spine aroll)
2 FAIL   2 WARN   2 PASS   1 N/A   of 7 gates

[FAIL] CUT-05     punch-in step >= 1.15x at every direct A-roll cut
             cut at 3.20 s: 1.05x
             cut at 6.10 s: 1.00x
             cut at 9.00 s: 1.02x
[FAIL] GFX-15     13 text elements; worst 3.38:1
[WARN] PLAT-06    reading speed: worst 77 cps (<= 20); 1 events over
             caption 4 at 2.1 s
[WARN] SND-13     quietest 250 ms window -75.5 dBFS (> -50)
[PASS] DEL-01     1080x1920
[PASS] DEL-02     30/1
[N/A ] FRAME-01   not applicable"""

def test_summary_counts_fails_warns_path():
    from cves import out
    s = out.qc_summary(REPORT, "/p/Edit/QC-REPORT.txt")
    L = s.splitlines()
    assert L[0].startswith("QC x.mp4") and "2 FAIL  2 WARN  2 PASS  1 N/A  of 7 gates" in L[0]
    assert "FAIL CUT-05: punch-in step" in s and "cut at 3.20 s" in s and "+1 more lines" in s
    assert "FAIL GFX-15" in s and "WARN (2):" in s and "  PLAT-06: reading speed" in s and "caption 4" not in s
    assert "DEL-01" not in s and L[-1].startswith("full report: /p/Edit/QC-REPORT.txt")
    assert len(L) < len(REPORT.splitlines())
    import re; assert re.search(r"(\d+) FAIL", s).group(1) == "2"       # the plugin hook reads this

def test_qc_json_shape():
    from cves import out
    d = out.qc_json(REPORT, "r.txt", "x.mp4")
    assert d["counts"] == {"FAIL": 2, "WARN": 2, "PASS": 2, "N/A": 1}
    g = {x["id"]: x for x in d["gates"]}
    assert g["CUT-05"]["details"][0] == "cut at 3.20 s: 1.05x" and "details" not in g["DEL-01"] and g["FRAME-01"]["status"] == "N/A"

def test_stderr_filter_drops_noise_and_folds_tracebacks(tmp_path):
    log = tmp_path / "cves.log"
    code = f"""
import sys, subprocess
sys.path.insert(0, {os.path.join(ROOT, "engine")!r})
from cves import out
f = out.StderrFilter({str(log)!r}).start()
sys.stderr.write("objc[1]: Class AVFFrameReceiver is implemented in both /a/cv2/libavdevice.dylib and /b/av/libavdevice.dylib\\n")
sys.stderr.write("[ WARN:0@414.895] global net_impl_backend.cpp:388 setPreferableTarget Targets are not supported\\n")
sys.stderr.write("/v/numba/np/ufunc/dufunc.py:303: RuntimeWarning: invalid value encountered in cast\\n  return super().__call__(*args)\\n")
sys.stderr.write("keep me\\n"); sys.stderr.flush()
subprocess.run([sys.executable, "-c", "raise ValueError('boom')"])
f.stop()
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert "keep me" in r.stderr and "objc" not in r.stderr and "WARN:0" not in r.stderr and "numba" not in r.stderr, r.stderr
    assert "worker error: ValueError: boom" in r.stderr and "Traceback" not in r.stderr, r.stderr
    t = log.read_text(encoding="utf-8"); assert "objc" in t and "Traceback" in t

def _cli(*a, cwd=ROOT, env=None):
    e = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "engine")); e.update(env or {})
    return subprocess.run([sys.executable, "-m", "cves.cli", *a], capture_output=True, text=True, cwd=cwd, env=e)

def test_templates_compact_one_and_json():
    r = _cli("templates"); assert r.returncode == 0, r.stderr
    assert len(r.stdout.splitlines()) <= 10 and "cutaway (" in r.stdout and "counter" in r.stdout
    r = _cli("templates", "--kinds"); assert r.returncode == 0 and len(r.stdout.strip().splitlines()) == 1 and "cutaway" in r.stdout
    r = _cli("templates", "counter"); assert r.returncode == 0 and "params" in r.stdout and "value" in r.stdout, r.stdout + r.stderr
    r = _cli("templates", "counter", "--json"); d = json.loads(r.stdout); assert d["kind"] == "cutaway" and "value" in d["params"]
    r = _cli("templates", "--json"); d = json.loads(r.stdout); assert any(x["name"] == "counter" for x in d["cutaway"])
    r = _cli("templates", "-v"); assert len(r.stdout.splitlines()) > 30
    r = _cli("templates", "no_such_tpl"); assert r.returncode != 0 and "unknown template" in r.stderr and "Traceback" not in r.stderr

def test_error_is_one_line_with_log(demo_copy):
    os.remove(os.path.join(demo_copy, "Edit", "edl.json"))
    r = _cli("--project", demo_copy, "story")      # reads edl.json only if it exists: fine
    assert r.returncode == 0, r.stderr
    with open(os.path.join(demo_copy, "Edit", "timeline.json"), "w", encoding="utf-8") as f: f.write("{not json")
    r = _cli("--project", demo_copy, "qc", "--video", os.path.join(demo_copy, "nope.mp4"))
    assert r.returncode != 0 and "Traceback" not in r.stderr, r.stderr
    assert "error:" in r.stderr and "Edit/logs/cves.log".replace("/", os.sep) in r.stderr, r.stderr
    assert "Traceback" in open(os.path.join(demo_copy, "Edit", "logs", "cves.log"), encoding="utf-8").read()
    r = _cli("--project", demo_copy, "qc", "--video", os.path.join(demo_copy, "nope.mp4"), "-v")
    assert "Traceback" in r.stderr

def test_status_orients(demo_copy):
    r = _cli("--project", demo_copy, "status"); assert r.returncode == 0, r.stderr
    L = r.stdout.splitlines(); assert len(L) <= 16 and L[-1].startswith("next: ") and "stage:" in L[0], r.stdout
    d = json.loads(_cli("status", demo_copy, "--json").stdout)
    assert d["next"] and d["stage"] and "ingest" in d["done"]
