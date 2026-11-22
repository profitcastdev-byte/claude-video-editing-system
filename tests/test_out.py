"""Compact CLI output (engine/cves/out.py, tlist.py, status.py): noise filter, one-line errors, --json."""
import os, sys, json, subprocess
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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
    r = _cli("--project", demo_copy, "deliver", "--video", os.path.join(demo_copy, "nope.mp4"))
    assert r.returncode != 0 and "Traceback" not in r.stderr, r.stderr
    assert "error:" in r.stderr and "Edit/logs/cves.log".replace("/", os.sep) in r.stderr, r.stderr
    assert "Traceback" in open(os.path.join(demo_copy, "Edit", "logs", "cves.log"), encoding="utf-8").read()
    r = _cli("--project", demo_copy, "-v", "deliver", "--video", os.path.join(demo_copy, "nope.mp4"))
    assert "Traceback" in r.stderr

def test_status_orients(demo_copy):
    r = _cli("--project", demo_copy, "status"); assert r.returncode == 0, r.stderr
    L = r.stdout.splitlines(); assert len(L) <= 16 and L[-1].startswith("next: ") and "stage:" in L[0], r.stdout
    d = json.loads(_cli("status", demo_copy, "--json").stdout)
    assert d["next"] and d["stage"] and "ingest" in d["done"]
