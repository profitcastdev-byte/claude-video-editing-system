"""Take alignment (`cves select`) and the "every chosen word is heard" check (STORY-17, `cves qc --stage story`).

Why: long-form whisper word times drift by 1-3 s around retakes and long pauses (a pause gets absorbed into a word),
so in/out points read off `raw_words.json` clip words. Re-transcribing a short window around each clip is much closer,
but still noisy at the window edges, so alignment:
  1. transcribes `story.align_passes` windows around the hand in/out (in - w .. out + w, w = story.align_window_s,
     widened per pass; clamped to the file; cached in Edit/align/), word level, with the project's language;
  2. fuzzy-matches the clip's `text:` to the best contiguous word run in each (case, punctuation and numbers
     normalised: "300 plus" = "300+", "a hundred percent" = "100%", "four to six" = "4-6");
  3. takes the first-word start and last-word end over the passes whose score >= story.align_min_score (their median
     when they agree, else the estimate nearest the hand time: a pass that merged two takes is outvoted);
  4. snaps each edge to the nearest pause in the speech energy (never inside speech), with the pads in
     story.align_pad_s ([in, out]).
A low score keeps the hand times (and warns). Opt out per clip (`align: false`) or for the style (`story.align: false`).
Every clip's result is recorded in edl.json clips[].aligned = {in, out, score, status, hand: [in, out]}.

STORY-17 transcribes each clip's own span of voice_final.wav (never the whole file: whisper skips sentences on long
files) and scores the recall of the clip's `text:` words (fillers ignored, the same normalisation)."""
import os, re, json, hashlib, difflib, tempfile, shutil, unicodedata
import numpy as np, soundfile as sf

FILLERS = {"um", "umm", "uh", "uhm", "uhh", "erm", "er", "ah", "ahh", "hmm", "mm", "mhm", "huh"}
SMALL = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                    "fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
WORD_S = .3        # a typical spoken word, s: how far an edge estimate moves per reference word missing there
MULT = {"hundred": 100, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "million": 10 ** 6, "crore": 10 ** 7}


# ------------------------------------------------------------------ text normalisation
def _raw_tokens(s):
    s = unicodedata.normalize("NFKC", str(s)).lower().replace("’", "'").replace("`", "'")
    s = re.sub(r"(\d),(\d{3})\b", r"\1\2", s)                              # 1,000 -> 1000
    s = re.sub(r"(\d)\s*[-–]\s*(\d)", r"\1 to \2", s)                   # 4-6 -> 4 to 6
    s = s.replace("%", " percent ").replace("+", " plus ").replace("&", " and ").replace("'", "")
    s = "".join(ch if ch.isalnum() or ch.isspace() or unicodedata.category(ch).startswith("M") else " " for ch in s)
    return s.split()

def _number_spans(tw):
    """spelled numbers -> digits as [(token, i0, i1)] over the input tokens: 'three hundred' -> '300', 'a hundred' ->
    '100', 'forty two' -> '42'; every other token passes through"""
    out, i = [], 0
    while i < len(tw):
        w = tw[i]
        starts = w in SMALL or w in TENS or (w == "a" and i + 1 < len(tw) and tw[i + 1] in MULT)
        if not starts: out.append((w, i, i + 1)); i += 1; continue
        total, cur, last, j = 0, 0, None, i
        while j < len(tw):
            x = tw[j]
            if x == "a" and j == i: cur, last = 1, "a"
            elif x in SMALL and (last is None or last == "mult" or (last == "tens" and SMALL[x] < 10)): cur += SMALL[x]; last = "small"
            elif x in TENS and last in (None, "mult"): cur += TENS[x]; last = "tens"
            elif x in MULT and last in ("small", "tens", "a"):
                if MULT[x] == 100: cur = (cur or 1) * 100
                else: total += (cur or 1) * MULT[x]; cur = 0
                last = "mult"
            else: break
            j += 1
        if last == "a": out.append((w, i, i + 1)); i += 1; continue
        out.append((str(total + cur), i, j)); i = j
    return out

def tokens(text):
    """normalised word tokens of a text (lower case, no punctuation, numbers as digits, + and % spelled)"""
    return [t for t, _, _ in _number_spans(_raw_tokens(text))]

def word_tokens(words):
    """(tokens, owner) for [[t0, t1, word], ...]: owner[k] = index of the (last) word token k came from. Spelled numbers
    that whisper split over several words ("three", "hundred") become one token."""
    raw, own = [], []
    for k, w in enumerate(words):
        for t in _raw_tokens(w[2]): raw.append(t); own.append(k)
    toks, town = [], []
    for t, i0, i1 in _number_spans(raw): toks.append(t); town.append(own[i1 - 1])
    return toks, town

def _same(a, b):
    if a == b: return True
    if a.rstrip("s") == b.rstrip("s") and min(len(a), len(b)) >= 3: return True
    return min(len(a), len(b)) >= 4 and difflib.SequenceMatcher(None, a, b).ratio() >= .8

def _canon(ref, hyp):
    """hyp tokens rewritten to the reference spelling where they are a near match (plural, small typo)"""
    vocab = set(ref); out = []
    for h in hyp:
        if h in vocab or not vocab: out.append(h); continue
        m = next((r for r in vocab if _same(r, h)), None); out.append(m or h)
    return out


# ------------------------------------------------------------------ matching
def best_run(ref, hyp, hint=None):
    """best contiguous run hyp[i:j] for the reference tokens -> (i, j, score, head, tail) or None (head / tail = reference
    words the run misses at its start / end). score = difflib ratio; ties go
    to the run whose edges match the reference's first / last word, then to the one nearest `hint(i, j)` (smaller)."""
    m, n = len(ref), len(hyp)
    if not m or not n: return None
    h = _canon(ref, hyp); k = max(2, int(round(.35 * m))); best = None
    for i in range(n):
        for L in range(max(1, m - k), m + k + 1):
            if i + L > n: break
            sc = difflib.SequenceMatcher(None, ref, h[i:i + L], autojunk=False).ratio()
            key = sc + .02 * (h[i] == ref[0]) + .02 * (h[i + L - 1] == ref[-1])
            if best is None or key > best[0] + 1e-9 or (abs(key - best[0]) <= 1e-9 and hint and hint(i, i + L) < hint(best[1], best[2])):
                best = (key, i, i + L, sc)
    _, i, j, sc = best
    while j - i > 1 and h[i] not in ref[:2]: i += 1                         # drop stray edge words the ratio tolerated
    while j - i > 1 and h[j - 1] not in ref[-2:]: j -= 1
    head = ref.index(h[i]) if h[i] in ref else 0                                     # reference words missing before the run
    tail = ref[::-1].index(h[j - 1]) if h[j - 1] in ref else 0      # ... and after it
    return i, j, difflib.SequenceMatcher(None, ref, h[i:j], autojunk=False).ratio(), head, tail

def recall(ref_text, heard_text, edges=False):
    """(share of the reference's words heard, [missing words in order]); fillers ignored, numbers normalised.
    edges=True adds a third value: (first word missing, last word missing), the signature of a clipped take"""
    ref = [t for t in tokens(ref_text) if t not in FILLERS]
    hyp = [t for t in _canon(ref, tokens(heard_text)) if t not in FILLERS]
    if not ref: return (1.0, [], (False, False)) if edges else (1.0, [])
    sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False); got = set()
    for a, _, size in sm.get_matching_blocks(): got.update(range(a, a + size))
    out = (len(got) / len(ref), [ref[i] for i in range(len(ref)) if i not in got])
    return out + ((0 not in got, len(ref) - 1 not in got),) if edges else out


# ------------------------------------------------------------------ audio
def wav16(pr, src=None):
    """a 16 kHz mono wav of a source (the one transcribe_raw wrote, else made once into Edit/align/)"""
    from . import ingest as ING
    src = ING.norm_src(pr, src)
    cand = pr.e("raw16.wav") if src == ING.primary(pr) else pr.e("sources", ING._slug(src) + ".16k.wav")
    if os.path.exists(cand): return cand
    out = pr.e("align", ING._slug(src) + ".16k.wav")
    if not os.path.exists(out):
        os.makedirs(pr.e("align"), exist_ok=True)
        a = pr.e("raw_audio.wav") if src == ING.primary(pr) and os.path.exists(pr.e("raw_audio.wav")) else ING._extract_audio(pr, src)
        ING.to16k(a, out)
    return out

def _read(wav, a, b):
    info = sf.info(wav); sr = info.samplerate
    y, sr = sf.read(wav, start=max(0, int(a * sr)), stop=min(info.frames, int(b * sr)))
    return (y.mean(1) if y.ndim > 1 else y), sr

def energy(wav, a, b):
    """(t, dB) every 10 ms over [a, b] (30 ms RMS frames), streamed from the file"""
    y, sr = _read(wav, a, b); hop, win = int(.01 * sr), int(.03 * sr)
    if len(y) < win: return np.array([a]), np.array([-120.0])
    db = np.array([20 * np.log10(np.sqrt(np.mean(y[i:i + win] ** 2)) + 1e-9) for i in range(0, len(y) - win, hop)])
    return a + np.arange(len(db)) * .01 + .015, db

def dtw_preset(model_path):
    """whisper.cpp --dtw preset for a ggml model file ('ggml-large-v3-turbo-q5_0.bin' -> 'large.v3.turbo'), or None"""
    from . import config as C
    try: forced = C.get("whisper_dtw")
    except Exception: forced = None
    if forced: return None if str(forced).lower() in ("off", "none", "false") else str(forced)
    n = re.sub(r"^ggml-|\.bin$", "", os.path.basename(str(model_path or ""))); n = re.sub(r"-q\d(_\d)?$|-f16$|-f32$", "", n)
    n = n.replace("-", ".")
    ok = {"tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large.v1", "large.v2", "large.v3", "large.v3.turbo"}
    return n if n in ok else None

def _whisper_dtw(wav, base, lang, preset):
    """[[t0, t1, word]] from whisper.cpp token-level DTW times (-ojf --dtw, flash attention off: DTW needs it off).
    t0 = the DTW time of the word's first token, t1 = of its last token (punctuation included). None if DTW gave none."""
    from . import config as C, ingest as ING
    ING.sh([C.get("whisper"), "-m", C.get("whisper_model"), "-f", wav, "-l", lang, "-ojf", "-of", base, "-dtw", preset, "-nfa"])
    with open(base + ".json", encoding="utf-8") as f: j = json.load(f)
    W, seen = [], False
    for seg in j.get("transcription") or []:
        for tk in seg.get("tokens") or []:
            tx = tk.get("text") or ""
            if tx.startswith("[_") or not tx.strip(): continue
            td = tk.get("t_dtw", -1)
            if td is None or td < 0: continue
            td = td / 100; seen = True
            if tx.startswith(" ") or not W: W.append([td, td, tx.strip()])
            else: W[-1][1] = max(W[-1][1], td); W[-1][2] += tx
    W = [w for w in W if tokens(w[2])]          # a lone punctuation word carries no text
    return W if seen and W else None

def _transcribe(wav, a, b, lang):
    """[[t0, t1, word]] of wav[a:b] in file seconds, word level. whisper.cpp DTW token times when the model has a DTW
    preset (segment times stretch the first and last word to the window edges), else -ml 1 segment times. Tests patch this."""
    from . import config as C, ingest as ING
    d = tempfile.mkdtemp(prefix="cves_align_")
    try:
        y, sr = _read(wav, a, b); p = os.path.join(d, "w.wav"); sf.write(p, y, sr); W = None
        pre = dtw_preset(C.get("whisper_model"))
        if pre:
            try: W = _whisper_dtw(p, os.path.join(d, "d"), lang, pre)
            except Exception: W = None
        if W is None: W, _ = ING._whisper_once(p, os.path.join(d, "w"), None, lang)
    finally: shutil.rmtree(d, ignore_errors=True)
    return [[round(s + a, 3), round(e + a, 3), t] for s, e, t in W]

def window_words(pr, wav, a, b, lang):
    """cached _transcribe(): Edit/align/cache/<key>.json, keyed by file, mtime, window, model and language"""
    from . import config as C
    st = os.stat(wav)
    key = hashlib.sha1(f"{os.path.abspath(wav)}|{st.st_size}|{int(st.st_mtime)}|{a:.3f}|{b:.3f}|{C.get('whisper_model')}|{lang}".encode()).hexdigest()[:16]
    p = pr.e("align", "cache", key + ".json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return json.load(f)["words"]
    W = _transcribe(wav, a, b, lang)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: json.dump({"wav": wav, "window": [a, b], "lang": lang, "words": W}, f, indent=1)
    return W


# ------------------------------------------------------------------ snapping
def _runs(mask):
    """[(i0, i1)] index runs where mask is True (i1 exclusive)"""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            out.append((i, j)); i = j
        else: i += 1
    return out

MIN_PAUSE_S = .06   # a quiet run at least this long is a pause between words; shorter ones may be a stop inside a word
INWARD_S = .1       # an edge may also move this far into the clip (the word estimate can be late / early by that much)

def snap(t, db, est, side, search=.5, pad=.05, quiet_db=12.0):
    """an edge time near `est` that sits in a pause, never inside speech. side 'in': the end of the nearest pause before
    the first word (looking back up to `search` s, and INWARD_S after est), minus pad but never past the middle of the
    pause (the next word's onset stays out); 'out': the start of the nearest pause after the last word, plus pad. Pauses >= MIN_PAUSE_S win over shorter quiet runs.
    Without any quiet run in reach, the quietest 10 ms in reach. -> (time, had_pause)"""
    if len(db) < 3: return est, False
    floor = float(np.percentile(db, 10)); quiet = db < floor + quiet_db
    lo, hi = (est - search, est + INWARD_S) if side == "in" else (est - INWARD_S, est + search)
    sel = (t >= lo) & (t <= hi)
    if not sel.any(): return est, False
    runs = [(float(t[i0]) - .005, float(t[i1 - 1]) + .005) for i0, i1 in _runs(quiet & sel)]
    runs = [r for r in runs if r[1] - r[0] >= MIN_PAUSE_S] or runs
    # DTW word times run late at a word's onset and land near its end: prefer a pause before the first word's estimate
    # and after the last word's
    if side == "in": runs = [r for r in runs if r[1] <= est + .03] or runs
    else: runs = [r for r in runs if r[0] >= est - .03] or runs
    if runs:
        if side == "in":
            r0, r1 = min(runs, key=lambda r: abs(r[1] - est)); return round(max((r0 + r1) / 2, r1 - pad), 3), True
        r0, r1 = min(runs, key=lambda r: abs(r[0] - est)); return round(min((r0 + r1) / 2, r0 + pad), 3), True
    idx = np.where(sel)[0]; k = idx[int(np.argmin(db[idx]))]
    return round(float(t[k]), 3), False


# ------------------------------------------------------------------ alignment
def settings(S):
    pad = S.get("story.align_pad_s", [.04, .08])
    pad = list(pad) if isinstance(pad, (list, tuple)) else [float(pad), float(pad)]
    return {"on": S.get("story.align", True) is not False, "window": float(S.get("story.align_window_s", 1.5)),
            "min_score": float(S.get("story.align_min_score", .8)), "pad": (float(pad[0]), float(pad[-1])),
            "passes": max(1, int(S.get("story.align_passes", 3))), "search": float(S.get("story.align_search_s", .5)),
            "quiet_db": float(S.get("story.align_quiet_db", 12))}

MERGE_GAP_S = 1.0   # a jump this long between two matched words ...
MERGE_SPEECH = .35  # ... over audio that is at least this much speech means whisper skipped a retake in that pass
AGREE_S = .3        # pass estimates this close agree (median); wider apart they are different takes: the one nearest the hand time

def consensus(xs, hand):
    """one edge estimate from the passes: their median when they agree, else the one nearest the hand-picked time
    (whisper merges two takes of a repeated line in some windows; the hand time says which take was meant)"""
    if max(xs) - min(xs) <= AGREE_S: return float(np.median(xs))
    return float(min(xs, key=lambda x: abs(x - hand)))

def align_clip(pr, c, wav, lang, A, dur=None):
    """-> aligned record {in, out, score, status, hand, heard, ...} (does not change c)"""
    hin, hout = float(c["in"]), float(c["out"]); ref = tokens(c.get("text") or "")
    rec = {"in": hin, "out": hout, "score": None, "hand": [hin, hout]}
    if not ref: rec["status"] = "no_text"; return rec
    dur = dur if dur is not None else sf.info(wav).duration
    wmax = A["window"] * (1.2 if A["passes"] > 2 else 1)
    et, edb = energy(wav, max(0.0, hin - wmax), min(dur, hout + wmax)); efloor = float(np.percentile(edb, 10)) if len(edb) else -120.0
    def merged(ws):
        """whisper dropped a retake inside the run: a > MERGE_GAP_S jump between two words over audio that is mostly speech"""
        for p_, q_ in zip(ws[:-1], ws[1:]):
            a_, b_ = p_[1] + .1, q_[0] - .1
            if q_[0] - p_[1] > MERGE_GAP_S and b_ > a_:
                m_ = (et >= a_) & (et <= b_)
                if m_.any() and float(np.mean(edb[m_] > efloor + A["quiet_db"])) > MERGE_SPEECH: return True
        return False
    cand, scores, heard = [], [], ""
    for k in range(A["passes"]):
        w = A["window"] * (1, .8, 1.2, .9, 1.1)[k % 5] if A["passes"] > 1 else A["window"]
        a, b = round(max(0.0, hin - w), 3), round(min(dur, hout + w), 3)
        W = window_words(pr, wav, a, b, lang)
        hyp, own = word_tokens(W)
        r = best_run(ref, hyp, hint=lambda i, j: abs(W[own[i]][0] - hin) + abs(W[own[j - 1]][1] - hout))
        if not r: continue
        i, j, sc, head, tail = r; scores.append(sc); run = W[own[i]:own[j - 1] + 1]
        if sc >= A["min_score"]:      # a reference word whisper missed at an edge: move the estimate out by ~a word each
            cand.append((W[own[i]][0] - WORD_S * head, W[own[j - 1]][1] + WORD_S * tail, merged(run)))
            heard = heard or " ".join(x[2] for x in run)
        elif not heard: heard = " ".join(x[2] for x in run)
    clean = [x for x in cand if not x[2]] or cand        # passes that merged two takes are outvoted by any clean pass
    starts, ends = [x[0] for x in clean], [x[1] for x in clean]
    rec["passes"] = len(cand); rec["merged_passes"] = sum(1 for x in cand if x[2])
    rec["score"] = round(max(scores), 3) if scores else 0.0; rec["heard"] = heard
    if not starts:
        rec["status"] = "kept_low_score"; return rec
    e_in, e_out = consensus(starts, hin), consensus(ends, hout)
    if e_out <= e_in: rec["status"] = "kept_low_score"; return rec
    lo, hi = max(0.0, e_in - A["search"] - .05), min(dur, e_out + A["search"] + .05)
    t, db = energy(wav, lo, hi)
    n_in, p_in = snap(t, db, e_in, "in", A["search"], A["pad"][0], A["quiet_db"])
    n_out, p_out = snap(t, db, e_out, "out", A["search"], A["pad"][1], A["quiet_db"])
    if n_out - n_in < .1: rec["status"] = "kept_low_score"; return rec
    rec.update({"in": n_in, "out": n_out, "est": [round(e_in, 3), round(e_out, 3)], "pause": [p_in, p_out],
                "status": "moved" if (abs(n_in - hin) >= .005 or abs(n_out - hout) >= .005) else "unchanged"})
    return rec

def report_line(cid, rec):
    hin, hout = rec["hand"]
    if rec["status"] == "off": return f"align {cid}: off (align: false / story.align: false), hand times kept"
    if rec["status"] == "no_text": return f"align {cid}: no text: in selects.yaml, hand times kept (STORY-17 skips it too)"
    if rec["status"] == "kept_low_score":
        return (f"WARNING align {cid}: text not found in the takes around {hin:.2f}-{hout:.2f} s (score {rec['score']:.2f}), "
                f"hand times kept; heard: {rec.get('heard', '')[:90]!r}")
    np_ = "" if all(rec.get("pause", [True, True])) else "  (no pause at an edge: cut at the quietest point)"
    if rec.get("passes") and rec.get("merged_passes") == rec["passes"]:
        np_ += "  (WARNING: whisper merged two takes in every pass: check which take this is by ear)"
    return (f"align {cid}: in {hin:.2f} -> {rec['in']:.2f} ({rec['in'] - hin:+.2f})  out {hout:.2f} -> {rec['out']:.2f} "
            f"({rec['out'] - hout:+.2f})  score {rec['score']:.2f}{np_}")

def align_clips(pr, clips, srcs, S, lang=None, out=print):
    """re-time every clip with a text: field in place (in/out) and add clips[k]['aligned']. -> list of records"""
    from . import ingest as ING
    A = settings(S); lang = lang or ING.whisper_language(pr, S); recs = []
    for c in clips:
        if not A["on"] or c.get("align") is False:
            rec = {"in": float(c["in"]), "out": float(c["out"]), "score": None, "status": "off", "hand": [float(c["in"]), float(c["out"])]}
        else:
            try: rec = align_clip(pr, c, wav16(pr, srcs.get(c["id"])), lang, A)
            except Exception as e:      # whisper missing or failing: never block the cut, keep the hand times
                rec = {"in": float(c["in"]), "out": float(c["out"]), "score": 0.0, "status": "kept_low_score", "hand": [float(c["in"]), float(c["out"])],
                       "heard": f"(alignment failed: {type(e).__name__}: {e})"}
        c["in"], c["out"] = rec["in"], rec["out"]; c["aligned"] = rec; recs.append(rec)
        if out: out(report_line(c["id"], rec))
    return recs


# ------------------------------------------------------------------ STORY-17: every chosen word is heard
def clip_spans(edl):
    """{clip id: (t0, t1)} cut-time span of each clip's segments (frame-rounded like the story gates)"""
    F = edl["fps"]; t = 0.0; spans = {}
    for s in edl["segments"]:
        L = round((s["out"] - s["in"]) * F) / F; a, b = spans.get(s["clip"], (t, t)); spans[s["clip"]] = (min(a, t), t + L); t += L
    return spans

def span_text(wav, t0, t1, lang):
    """whisper text of wav[t0:t1] (16 kHz mono temp copy). Tests patch this."""
    from .qc import audio_gates as AG
    d = tempfile.mkdtemp(prefix="cves_heard_")
    try:
        y, sr = _read(wav, t0, t1)
        if sr != 16000:
            import librosa
            y = librosa.resample(y, orig_sr=sr, target_sr=16000); sr = 16000
        p = os.path.join(d, "c.wav"); sf.write(p, y, sr)
        return AG._whisper(p, lang=lang)
    finally: shutil.rmtree(d, ignore_errors=True)

def clip_recall(pr, lang, pad=.08):
    """[{clip, score, missing, edge: [first lost, last lost], heard}] per clip of edl.json (score None = no text: skipped)"""
    edl = pr.json("edl.json"); spans = clip_spans(edl); wav = pr.e("voice_final.wav"); dur = sf.info(wav).duration; out = []
    for c in edl["clips"]:
        if c["id"] not in spans: continue
        if not (c.get("text") or "").strip(): out.append({"clip": c["id"], "score": None, "missing": [], "edge": [False, False], "heard": ""}); continue
        t0, t1 = spans[c["id"]]; heard = span_text(wav, max(0.0, t0 - pad), min(dur, t1 + pad), lang)
        sc, miss, edge = recall(c["text"], heard, edges=True)
        out.append({"clip": c["id"], "score": sc, "missing": miss, "edge": list(edge), "heard": " ".join(heard.split()), "span": [round(t0, 2), round(t1, 2)]})
    return out
