"""Runs one QC gate family in a separate Python process so it measures in parallel with the rest of `cves qc`
(qc.run starts it, then joins its gate rows in the place the serial run emitted them). Started as
`python -c "from cves.qc import _worker; _worker.main(IN, OUT)"`, not through multiprocessing: no re-import of the
caller's __main__, so a script that calls qc.run at top level is safe. The job and the result travel as pickle files."""
import os, pickle, subprocess, sys, tempfile, traceback

ENGINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def extra_rows(pr, video, spine, captions, tier):
    """the gate rows run_extra emits, after the N/A wrapper (exactly what the serial run appended to R)"""
    from . import na_gate
    R = []
    def gate0(gid, ok, summary, details="", status=None): R.append((gid, status or ("PASS" if ok else "FAIL"), summary, details))
    from .extra import run_extra
    run_extra(pr, video, na_gate(gate0, spine, captions), tier=tier)
    return R


JOBS = {"extra": extra_rows}


def main(inp, out):
    with open(inp, "rb") as f: name, args = pickle.load(f)
    try: res = ("ok", JOBS[name](*args))
    except BaseException as e:                       # re-raised in the parent with the child's traceback
        tb = traceback.format_exc()
        try: pickle.dumps(e); res = ("err", (e, tb))
        except Exception: res = ("err", (RuntimeError(f"{type(e).__name__}: {e}"), tb))
    with open(out, "wb") as f: pickle.dump(res, f)


class Job:
    """start(name, *args) now; .result() later (blocks). In-process when CVES_QC_PROCS=0."""
    def __init__(self, name, *args):
        self.name, self.args, self.proc = name, args, None
        if os.environ.get("CVES_QC_PROCS", "1") in ("0", "off", "false"): return
        d = tempfile.mkdtemp(prefix="cves_qcjob_"); self.inp, self.out = os.path.join(d, "in.pkl"), os.path.join(d, "out.pkl")
        with open(self.inp, "wb") as f: pickle.dump((name, args), f)
        env = dict(os.environ); env["PYTHONPATH"] = ENGINE + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        self.proc = subprocess.Popen([sys.executable, "-c", f"from cves.qc import _worker; _worker.main({self.inp!r}, {self.out!r})"], env=env)

    def result(self):
        if self.proc is None: return JOBS[self.name](*self.args)
        rc = self.proc.wait()
        try:
            with open(self.out, "rb") as f: kind, val = pickle.load(f)
        except (OSError, EOFError, pickle.UnpicklingError):
            raise RuntimeError(f"QC worker '{self.name}' died (exit {rc}) without a result")
        finally:
            import shutil; shutil.rmtree(os.path.dirname(self.inp), ignore_errors=True)
        if kind == "err":
            e, tb = val; sys.stderr.write(f"QC worker '{self.name}' failed:\n{tb}"); raise e
        return val
