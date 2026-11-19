"""Edit/qc_cache/: measurements of the delivered master that `cves qc`, `cves review` and a QC re-run share, so the same
file is not decoded (or transcribed) twice. Every entry is keyed by the master's sha256 (and CACHE_VERSION): a new
render is a new key, so a cached value can never describe another file. Whisper transcripts are keyed by the sha256 of
the exact audio file sent plus the command line (binary, model, language, prompt).

Layout: Edit/qc_cache/<sha256[:20]>-v<CACHE_VERSION>/<name>.npz|json   (the last KEEP masters are kept)
        Edit/qc_cache/whisper/<sha256 of audio + command>.txt

A cache entry holds exactly what the measurement code computed (numpy arrays saved losslessly, floats as float64), so a
gate reading it reports the same value as one that decoded the file. `CVES_QC_CACHE=off` disables reading and writing
(the parity proof in knowledge-base/DECISIONS.md ran both ways). Docs: docs/QC.md "Speed"."""
import hashlib, json, os, shutil, tempfile
import numpy as np

CACHE_VERSION = 1          # bump when a cached measurement's definition changes (decode size, detector, thresholds)
KEEP = 4                   # master keys kept per project (variants and A/B renders share one Edit/)


def enabled():
    return os.environ.get("CVES_QC_CACHE", "on").lower() not in ("0", "off", "false", "no")


def sha256(path, bs=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(bs), b""): h.update(b)
    return h.hexdigest()


_SHA = {}
def master_sha(video):
    """sha256 of the master, memoised on (path, size, mtime) for one process (QC and the stamp hash the file once)"""
    st = os.stat(video); k = (os.path.abspath(video), st.st_size, st.st_mtime_ns)
    if k not in _SHA: _SHA[k] = sha256(video)
    return _SHA[k]


def root(pr): return pr.e("qc_cache")


def key_dir(pr, video, create=False):
    d = os.path.join(root(pr), f"{master_sha(video)[:20]}-v{CACHE_VERSION}")
    if create and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True); _prune(pr, keep=d)
    return d


def _prune(pr, keep):
    r = root(pr)
    try: ds = [os.path.join(r, x) for x in os.listdir(r) if x != "whisper" and os.path.isdir(os.path.join(r, x))]
    except OSError: return
    ds = sorted((d for d in ds if d != keep), key=lambda d: os.path.getmtime(d), reverse=True)
    for d in ds[KEEP - 1:]: shutil.rmtree(d, ignore_errors=True)


def _atomic(path, write):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".part"); os.close(fd)
    try:
        write(tmp); os.replace(tmp, path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise


def load_arrays(pr, video, name, meta=None):
    """-> dict of arrays (+ '_meta' dict) or None. `meta` must equal the saved meta (decode size, model, ...) to hit."""
    if not enabled(): return None
    p = os.path.join(key_dir(pr, video), name + ".npz")
    if not os.path.exists(p): return None
    try:
        with np.load(p, allow_pickle=False) as z:
            d = {k: z[k] for k in z.files}
        m = json.loads(str(d.pop("_meta"))) if "_meta" in d else {}
        if meta is not None and m != json.loads(json.dumps(meta)): return None
        d["_meta"] = m; return d
    except (OSError, ValueError, KeyError): return None


def save_arrays(pr, video, name, arrays, meta=None):
    if not enabled(): return
    p = os.path.join(key_dir(pr, video, create=True), name + ".npz")
    a = {k: np.asarray(v) for k, v in arrays.items()}; a["_meta"] = np.array(json.dumps(meta or {}))
    try:
        _atomic(p, lambda t: np.savez(open(t, "wb"), **a))
    except OSError: pass


def load_json(pr, video, name):
    if not enabled(): return None
    p = os.path.join(key_dir(pr, video), name + ".json")
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return None


def save_json(pr, video, name, obj):
    if not enabled(): return
    p = os.path.join(key_dir(pr, video, create=True), name + ".json")
    def w(t):
        with open(t, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False)
    try: _atomic(p, w)
    except OSError: pass


# ---------------------------------------------------------------- whisper transcripts (keyed by the audio bytes)
WHISPER_DIR = None          # set by qc.run for the project being judged; None = no transcript cache (other callers)


def whisper_key(path, cmd):
    return hashlib.sha256((sha256(path) + "\0" + "\0".join(cmd)).encode("utf-8")).hexdigest()


def whisper_get(path, cmd):
    if not WHISPER_DIR or not enabled(): return None, None
    k = whisper_key(path, cmd); p = os.path.join(WHISPER_DIR, k + ".txt")
    try:
        with open(p, encoding="utf-8") as f: return f.read(), k
    except OSError: return None, k


def whisper_put(k, text):
    if not WHISPER_DIR or not enabled() or k is None: return
    p = os.path.join(WHISPER_DIR, k + ".txt")
    def w(t):
        with open(t, "w", encoding="utf-8") as f: f.write(text)
    try: _atomic(p, w)
    except OSError: pass
