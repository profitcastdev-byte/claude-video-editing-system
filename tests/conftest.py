"""Shared fixtures. The demo project (tools/make_demo.py) is built once per test session; set CVES_DEMO_DIR to reuse one
already built (local runs), or CVES_UPDATE_GOLDEN=1 to rewrite tests/golden/ from the current renderer."""
import os, sys, shutil, subprocess, tempfile, pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))
# a machine's personal learned taste (~/.cves/taste/learned.yaml) must never change test renders (docs/LEARNING.md)
os.environ["CVES_TASTE"] = tempfile.mkdtemp(prefix="cves_taste_")

def _build(dest):
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_demo.py"), dest, "--small"], check=True)

@pytest.fixture(scope="session")
def demo_built():
    """the demo project after make_demo (ingest state), shared read-only"""
    d = os.environ.get("CVES_DEMO_DIR")
    if d and os.path.isdir(os.path.join(d, "Edit", "plate")): return d
    d = os.path.join(tempfile.mkdtemp(prefix="cves_demo_"), "demo"); _build(d); return d

@pytest.fixture(scope="session")
def demo_rendered(demo_built, tmp_path_factory):
    """a copy of the demo with a full render + mix + encode (session-wide: the slow part runs once)"""
    from cves import project, render, mix, encode
    d = str(tmp_path_factory.mktemp("rendered") / "demo"); shutil.copytree(demo_built, d)
    pr = project.Project(d)
    for p in ("frames", "timeline.json", "elements.jsonl", "exposure.json"):
        q = pr.e(p); shutil.rmtree(q, ignore_errors=True) if os.path.isdir(q) else (os.path.exists(q) and os.remove(q))
    render.render(pr); mix.mix(pr); encode.encode(pr)
    return d

@pytest.fixture
def demo_copy(demo_built, tmp_path):
    d = str(tmp_path / "demo"); shutil.copytree(demo_built, d); return d
