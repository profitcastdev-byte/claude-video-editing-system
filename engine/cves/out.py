"""Console output shaping for the `cves` CLI: quiet third-party noise, compact summaries, one-line errors.

Claude reads every line a command prints, so the default output is short and points at the full file; `-v` (or
CVES_VERBOSE=1) restores the full text. Nothing here changes what a command writes to disk.

  quiet_env()          env vars + warning filters for this process and every worker it spawns (OpenCV log level, numba)
  StderrFilter         fd-level stderr filter for the CLI process tree: drops the known third-party noise (the duplicate
                       libavdevice objc class lines, OpenCV `[ WARN:` lines, numba warnings) and folds worker tracebacks
                       into their last line; everything dropped is appended to a log file
  error_line(...)      one actionable line for an exception + where the traceback was logged"""
import os, re, sys, threading, traceback, warnings

NOISE = [re.compile(p) for p in (
    r"^objc\[\d+\]: Class \w+ is implemented in both .*libavdevice",     # cv2 and av both bundle libavdevice (macOS)
    r"^\[ ?WARN:\d+@[\d.]+\] global ",                                   # OpenCV log lines (DNN backend / target, videoio)
    r"^\[ INFO:\d+@[\d.]+\] global ",
    r"NumbaWarning|NumbaDeprecationWarning|NumbaPerformanceWarning",
    r"[/\\]numba[/\\].*: \w*Warning: ",                                  # a warnings.warn line raised inside numba
    r"^OMP: Info #\d+",                                                  # OpenMP banner (torch / librosa)
)]

def verbose_requested(argv):
    return os.environ.get("CVES_VERBOSE", "").strip() not in ("", "0") or any(a in ("-v", "--verbose") for a in (argv or []))

def quiet_env():
    """call before cv2 / numba are imported; workers inherit the env vars (spawn re-imports cves.cli)"""
    os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")          # [ WARN:0@..] net_impl_backend.cpp setPreferableTarget
    os.environ.setdefault("OPENCV_VIDEOIO_DEBUG", "0")
    os.environ.setdefault("KMP_WARNINGS", "0")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"numba(\.|$)")
    try:
        from numba.core.errors import NumbaWarning                 # only if numba is already importable cheaply
        warnings.filterwarnings("ignore", category=NumbaWarning)
    except Exception: pass
    cv2 = sys.modules.get("cv2")
    if cv2 is not None:
        try: cv2.setLogLevel(2)                                   # 2 = ERROR
        except Exception: pass

def is_noise(line):
    return any(p.search(line) for p in NOISE)

class StderrFilter:
    """Redirect fd 2 of this process (inherited by every worker and subprocess) through a filter thread.
    Known noise lines are dropped; a Python traceback block from a worker is folded into its final exception line.
    Dropped text goes to `log` (appended). verbose=True passes everything through untouched (no thread)."""
    def __init__(self, log=None, verbose=False):
        self.log, self.verbose, self.saved, self.th, self.dropped = log, verbose, None, None, 0

    def start(self):
        if self.verbose: return self
        try:
            sys.stderr.flush(); fd = sys.stderr.fileno()
            if fd != 2: return self
            self.saved = os.dup(2); self.out_fd = os.dup(2); r, w = os.pipe(); os.dup2(w, 2); os.close(w)
        except Exception:
            self.saved = None; return self
        self.tb, self.after_exc, self.warned = None, False, False
        self.th = threading.Thread(target=self._pump, args=(r,), daemon=True); self.th.start()
        return self

    def stop(self):
        if self.saved is None: return
        try: sys.stderr.flush()
        except Exception: pass
        os.dup2(self.saved, 2); os.close(self.saved); self.saved = None   # closes our write end; the thread sees EOF
        if self.th: self.th.join(timeout=2.0)

    def _keep(self, text):
        try: os.write(self.out_fd, text.encode("utf-8", "replace"))
        except Exception: pass

    def _drop(self, text):
        self.dropped += 1
        if not self.log: return
        try:
            os.makedirs(os.path.dirname(self.log), exist_ok=True)
            with open(self.log, "a", encoding="utf-8") as f: f.write(text if text.endswith("\n") else text + "\n")
        except Exception: pass

    def _pump(self, r):
        buf = b""
        with os.fdopen(r, "rb", buffering=0) as fh:
            while True:
                chunk = fh.read(4096)
                if not chunk: break
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1); self._line(raw.decode("utf-8", "replace") + "\n")
        if buf: self._line(buf.decode("utf-8", "replace"))
        if self.tb: self._flush_tb()
        try: os.close(self.out_fd)
        except Exception: pass

    def _flush_tb(self):
        tb, self.tb, self.after_exc = self.tb, None, False
        self._drop("".join(tb))
        last = next((l for l in reversed(tb) if l.strip() and not l.startswith((" ", "\t", "Traceback", "Process "))), tb[-1]).rstrip()
        hint = f" (traceback in {self.log})" if self.log else ""
        self._keep(f"worker error: {_cut(last, 300)}{hint}\n")

    _CONT = ("Traceback (most recent call last):", "During handling of the above exception", "The above exception was the direct cause")

    def _line(self, line):
        s = line.rstrip("\n")
        if self.tb is not None:
            if not s.strip(): self.tb.append(line); return
            if s.startswith((" ", "\t")) or s.startswith(self._CONT):
                self.tb.append(line); self.after_exc = False; return
            if not self.after_exc:                 # the exception line closes the block (a chained one may follow)
                self.tb.append(line); self.after_exc = True; return
            self._flush_tb()
        if re.match(r"^Process \w+-\d+:$", s) or s.startswith("Traceback (most recent call last):"):
            self.tb, self.after_exc = [line], False; return
        if is_noise(s):
            self._drop(line); self.warned = bool(re.search(r"Warning: ", s)); return
        if self.warned and re.match(r"^\s{2,}\S", s):
            self.warned = False; self._drop(line); return    # the source line python prints under a warning
        self.warned = False
        self._keep(line)

def _cut(s, n):
    s = " ".join(str(s).split()); return s if len(s) <= n else s[:n - 1].rstrip() + "…"

# ---- errors
def error_line(cmd, exc, log):
    msg = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    kind = type(exc).__name__
    hint = {"FileNotFoundError": "a file is missing: check the path, or run the step that writes it first",
            "KeyError": "a key is missing in edit.yaml / style / a JSON file: `cves validate` names the bad key",
            "ModuleNotFoundError": "a dependency is not installed: run `cves doctor`"}.get(kind, "")
    s = f"cves {cmd or ''}: error: {kind}: {_cut(msg, 300)}".replace("  ", " ")
    if hint: s += f"\n  hint: {hint}"
    return s + f"\n  traceback: {log}  (re-run with -v to print it)"

def write_traceback(log, exc_info=None):
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f: f.write("".join(traceback.format_exception(*(exc_info or sys.exc_info()))) + "\n")
    except Exception: pass
    return log
