"""Shared fixtures. The demo project (tools/make_demo.py) is built once per test session; set CVES_DEMO_DIR to reuse one
already built (local runs), or CVES_UPDATE_GOLDEN=1 to rewrite tests/golden/ from the current renderer.

Parallel runs (pytest-xdist, `pytest -n auto`): the session builds (the demo, its full render, the spine demos) are made
ONCE per run for all workers, under a file lock in the run's shared temp folder; a worker that finds a finished build
reuses it. Builds are read-only to the tests: `demo_rendered` hands each worker its own copy (the tests in a worker write
into it, as the single-process session always did).

Markers (CONTRIBUTING.md "Tests"): `e2e` = a test that renders, mixes or encodes a demo (set automatically from the
fixtures it uses, or explicitly); CI runs `-m "not e2e"` and `-m e2e` as separate jobs. `-m "not e2e"` is the quick loop."""
import os, sys, shutil, subprocess, tempfile, pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "engine"))
# a machine's personal learned taste (~/.cves/taste/learned.yaml) must never change test renders (docs/LEARNING.md)
os.environ["CVES_TASTE"] = tempfile.mkdtemp(prefix="cves_taste_")
if os.environ.get("PYTEST_XDIST_WORKER"):     # several xdist workers on one small CI runner (7 GB, 4 cores): each worker's render
    for k, v in (("CVES_RENDER_WORKERS", "2"), ("CVES_INSPIRE_WORKERS", "1"),                                   # pool stays small, and the
                 ("NUMBA_NUM_THREADS", "1"), ("OMP_NUM_THREADS", "1"), ("MKL_NUM_THREADS", "1")):      # math libraries single-threaded: 16 torch
        os.environ.setdefault(k, v)                                                                     # processes + nested thread pools hung CI
# ... nor may a personal SFX bank (~/.cves/sfx, docs/SOUND.md) change which sounds the mix picks
os.environ["CVES_SFX"] = tempfile.mkdtemp(prefix="cves_sfx_")

E2E_FIXTURES = {"demo_rendered", "spine_demo"}


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: renders / mixes / encodes a demo project (slow; CI runs it as its own job)")


def pytest_collection_modifyitems(config, items):
    for it in items:
        if E2E_FIXTURES & set(getattr(it, "fixturenames", ())) and not it.get_closest_marker("e2e"): it.add_marker(pytest.mark.e2e)


def _shared_root(tmp_path_factory, worker_id):
    """the temp folder every xdist worker of this run shares (the per-worker basetemp's parent); the basetemp itself
    when not distributed"""
    base = tmp_path_factory.getbasetemp()
    return str(base.parent if worker_id != "master" else base)


def build_once(root, name, build):
    """build(dest) at most once per run across workers: a file lock + a done marker. -> dest"""
    from filelock import FileLock
    dest = os.path.join(root, "shared", name); done = dest + ".done"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(done): return dest
    with FileLock(dest + ".lock"):
        if not os.path.exists(done):
            shutil.rmtree(dest, ignore_errors=True); build(dest)
            open(done, "w", encoding="utf-8").close()
    return dest


def _build(dest):
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_demo.py"), dest, "--small"], check=True)


@pytest.fixture(scope="session")
def demo_built(tmp_path_factory, worker_id):
    """the demo project after make_demo (ingest state), shared read-only"""
    d = os.environ.get("CVES_DEMO_DIR")
    if d and os.path.isdir(os.path.join(d, "Edit", "plate")): return d
    return os.path.join(build_once(_shared_root(tmp_path_factory, worker_id), "demo", lambda p: _build(os.path.join(p, "demo"))), "demo")


def _render_demo(src, d):
    from cves import project, render, mix, encode
    shutil.copytree(src, d); pr = project.Project(d)
    for p in ("frames", "timeline.json", "elements.jsonl", "exposure.json"):
        q = pr.e(p); shutil.rmtree(q, ignore_errors=True) if os.path.isdir(q) else (os.path.exists(q) and os.remove(q))
    render.render(pr); mix.mix(pr); encode.encode(pr)


@pytest.fixture(scope="session")
def demo_rendered(demo_built, tmp_path_factory, worker_id):
    """a copy of the demo with a full render + mix + encode (the slow part runs once per run, for every worker)"""
    src = os.path.join(build_once(_shared_root(tmp_path_factory, worker_id), "rendered", lambda p: _render_demo(demo_built, os.path.join(p, "demo"))), "demo")
    if worker_id == "master": return src                 # one process: the session's own build, as before
    d = str(tmp_path_factory.mktemp("rendered") / "demo"); shutil.copytree(src, d, symlinks=True)
    return d


@pytest.fixture
def demo_copy(demo_built, tmp_path):
    d = str(tmp_path / "demo"); shutil.copytree(demo_built, d); return d


# ---- formats + spines (docs/FORMATS.md): small synthetic demos, built once per run per (kind, size)
_SPINE_DEMOS = {}

@pytest.fixture(scope="session")
def spine_demo(tmp_path_factory, worker_id):
    """spine_demo(kind, size="480x270") -> path of a make_demo --kind project (ingest state), shared read-only"""
    root = _shared_root(tmp_path_factory, worker_id)
    def get(kind, size="480x270"):
        key = (kind, size)
        if key not in _SPINE_DEMOS:
            def mk(p):
                subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_demo.py"), os.path.join(p, "demo"), "--small", "--kind", kind, "--size", size], check=True)
            _SPINE_DEMOS[key] = os.path.join(build_once(root, f"spine_{kind}_{size}", mk), "demo")
        return _SPINE_DEMOS[key]
    return get

def build_spine_copy(src, dst):
    """copy a spine demo and run render + mix + encode on it -> (Project, master mp4)"""
    from cves import project, render, mix, encode
    shutil.copytree(src, dst); pr = project.Project(dst)
    render.render(pr); mix.mix(pr); return pr, encode.encode(pr)
