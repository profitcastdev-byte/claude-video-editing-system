"""Speech gates: pauses (CUT-02), words vs raw (CUT-01), stutters (CUT-03). Whisper lessons baked in:
it skips sentences on long files (transcribe in ~8 s chunks), invents words over music tails (use the voice stem),
and hides disfluencies unless prompted verbatim."""
import os, re, difflib, subprocess, tempfile, unicodedata
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf, librosa
from .. import config as C
from . import cache as QCC

DEFAULT_LANG = "en"     # used when a caller passes no lang; gates with a project pass ingest.whisper_language(pr)

def workers():
    """whisper processes run side by side (each call is independent; results are joined in order): CVES_QC_WHISPER_JOBS"""
    try: return max(1, int(os.environ.get("CVES_QC_WHISPER_JOBS", "") or min(3, max(1, (os.cpu_count() or 2) // 3))))
    except ValueError: return 1

def _pmap(fn, items):
    items = list(items); n = min(workers(), len(items))
    if n <= 1: return [fn(x) for x in items]
    with ThreadPoolExecutor(n) as ex: return list(ex.map(fn, items))

def gaps(wav, mx=.25):
    y, sr = sf.read(wav); y = y.mean(1) if y.ndim > 1 else y
    hop = int(.01 * sr); r = np.array([np.sqrt(np.mean(y[i:i + 2 * hop] ** 2)) for i in range(0, len(y) - 2 * hop, hop)])
    db = 20 * np.log10(r + 1e-9); sp = db > max(db.max() - 38, -55); idx = np.where(sp)[0]
    g = [(a * .01, (b - a) * .01) for a, b in zip(idx[:-1], idx[1:]) if (b - a) * .01 > mx]
    return g

def _whisper(path, prompt=None, lang=None):
    """plain text of a short wav. lang: whisper code or 'auto' (default DEFAULT_LANG); the English verbatim prompt is
    only sent for English, so it cannot pull another language towards English"""
    lang = (lang or DEFAULT_LANG).lower()
    if prompt and not lang.startswith("en"): prompt = None
    cmd = [C.get("whisper"), "-m", C.get("whisper_model"), "-l", lang, "-nt", "-f", path] + (["--prompt", prompt] if prompt else [])
    # inside `cves qc` the transcript is cached by the audio bytes + this command line (qc/cache.py): a re-run hears the same
    key = [C.get("whisper"), C.get("whisper_model"), "-l", lang, "-nt"] + (["--prompt", prompt] if prompt else [])
    hit, k = QCC.whisper_get(path, key)
    if hit is not None: return hit
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0: QCC.whisper_put(k, r.stdout)
    return r.stdout

def transcribe_chunked(path, lang=None):
    y, sr = sf.read(path); y = y.mean(1) if y.ndim > 1 else y
    y = librosa.resample(y, orig_sr=sr, target_sr=16000); sr = 16000
    rms = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")); cuts = [0]
    while cuts[-1] + 9 * sr < len(y):
        a, b = cuts[-1] + 6 * sr, cuts[-1] + 9 * sr; cuts.append(a + int(np.argmin(rms[a:b])))
    cuts.append(len(y)); d = tempfile.mkdtemp(); paths = []
    for k, (a, b) in enumerate(zip(cuts[:-1], cuts[1:])):
        p = os.path.join(d, f"c{k}.wav"); sf.write(p, y[a:b], sr); paths.append(p)
    return " ".join(_pmap(lambda p: _whisper(p, lang=lang), paths))

NUM = {"four triple nine": "4999", "four nine nine nine": "4999", "4 to 9": "4999", "thirty": "30", "three": "3"}
def _strip_punct(s, keep=""):
    """drop punctuation and symbols but keep letters and combining marks of any script (Indic vowel signs are marks)"""
    return "".join(ch for ch in s if ch in keep or not unicodedata.category(ch).startswith(("P", "S", "C")) or ch == " ")

def norm(s):
    s = s.lower().replace("+", " plus").replace("-", " ").replace(",", "")
    for k, v in NUM.items(): s = s.replace(k, v)
    return _strip_punct(s).split()

def words(processed, reference, lang=None):
    got, ref = norm(transcribe_chunked(processed, lang)), norm(transcribe_chunked(reference, lang))
    sm = difflib.SequenceMatcher(a=ref, b=got, autojunk=False); bad = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal": bad.append(f"{op}: ref[{' '.join(ref[i1:i2])}] heard[{' '.join(got[j1:j2])}]")
    lost = [b for b in bad if b.startswith("delete") and len(b.split("]")[0].split()) >= 3]
    return sm.ratio(), bad, not lost and sm.ratio() >= .95

def stutters(pr, lang=None):
    from .. import ingest as ING
    edl = pr.json("edl.json"); d = tempfile.mkdtemp(); lang = lang or ING.whisper_language(pr)
    prompt = "Verbatim with repetitions and false starts: I, I mean, we, we do, want, want to."
    def one(js):
        j, s = js; p = os.path.join(d, f"s{j}.wav")
        subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-ss", str(s["in"]), "-to", str(s["out"]), "-i", ING.source_audio(pr, s.get("src")), "-ar", "16000", "-ac", "1", p])
        def reps_of(text):
            w = re.sub(r"\s+", " ", "".join(ch if ch.isspace() or ch == "'" or not unicodedata.category(ch).startswith(("P", "S", "C")) else " " for ch in text.lower())).split()
            r = [i for i in range(1, len(w)) if w[i] == w[i - 1]] + [i for i in range(3, len(w)) if w[i - 1:i + 1] == w[i - 3:i - 1]]
            return w, [i for i in r if f"{w[i - 1]} {w[i]}" not in ("every single", "very very")]
        text = _whisper(p, prompt, lang); w, r = reps_of(text)
        if r and max(sum(1 for x in w if x == w[i]) for i in r) >= 4:   # prompt loop on proper nouns -> recheck unprompted
            text = _whisper(p, lang=lang); w, r = reps_of(text)
        return f"{s['id']} ({s['in']:.2f}-{s['out']:.2f}s raw): {' '.join(text.split())}" if r else None
    return [x for x in _pmap(one, enumerate(edl["segments"])) if x]       # segments are independent: joined in edl order
