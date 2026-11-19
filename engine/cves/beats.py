"""Beat sync: analyse the music, fit it to the edit on bar lines, and sync drop / cuts / SFX to the beat.

    cves beats [PROJECT] [--file Music/x.mp3] [--sync off|drop|cuts|full] [--apply] [--json]

1. analyse(): librosa tempo + beats, downbeats (bar phase from low-band onsets + beat-synchronous chroma change),
   sections (agglomerative over beat-synced MFCC + chroma, snapped to downbeats), an energy curve, per-bar energy
   and drop candidates (big energy rises after a quieter stretch). Cached in Edit/beats.json (track time).
2. plan(): where the track sits under the edit. Sync modes are cumulative (style `music.sync`, edit.yaml `music.sync`):
     off   the manual music.drop_track / drop_cut (legacy);
     drop  a drop candidate is aligned to the story moment (music.drop_cut if > 0, else the first clip tagged with a
           `music.drop_beats` beat in edl.json);
     cuts  drop + cutaway in/out points and graphic entry times are moved onto the nearest beat (report; --apply
           writes edit.yaml with a backup). A-roll cuts never leave their segment boundary;
     full  cuts + transition SFX (whoosh/hit/boom/riser) nudged so their peak is on the beat (mix.all_cues).
3. layout() / render(): music fit. The bed is trimmed on bar lines, looped with an equal-power crossfade on
   downbeats when the track is too short, and ends on a downbeat near the end card with a one-bar tail (or the
   track's own ending when it lands there).
All thresholds come from the style profile (`music.*`, docs/MUSIC.md). Times in beats.json are TRACK seconds;
everything returned by plan() / layout() is CUT (edit) seconds."""
import os, re, json, copy, shutil, datetime
import numpy as np

VERSION = 4


# ------------------------------------------------------------------ config
def cfg(pr, S=None, mode=None):
    """style music.* merged with edit.yaml music: (edit.yaml wins); `mode` overrides music.sync for one run"""
    from . import style as STY
    S = S or STY.load(pr)
    base = dict(S.get("music") or {})
    E = (pr.edit.get("music") or {}) if pr is not None else {}
    c = {**base, **{k: v for k, v in E.items() if v is not None}}
    if mode: c["sync"] = mode
    return c

def mode_of(c):
    m = str(c.get("sync", "off")).strip().lower()
    if m in ("false", "none", "0", ""): m = "off"
    if m not in ("off", "drop", "cuts", "full"):
        raise SystemExit(f"music.sync must be off | drop | cuts | full (got {m!r})")
    return m

def music_file(pr, file=None):
    f = file or (pr.edit.get("music") or {}).get("file")
    if not f:     # music.slot: platform: the reference track the edit is cut to stands in for the music (cves.guide)
        from . import guide as GD
        s = GD.spec(pr)
        if s and s["kind"] == "file": f = s["path"]
    if not f: return None
    p = f if os.path.isabs(f) else pr.p(f)
    if not os.path.exists(p): raise SystemExit(f"music file not found: {p} (set music.file in edit.yaml or pass --file)")
    return p


# ------------------------------------------------------------------ analysis
def _parabolic(env, i):
    if 0 < i < len(env) - 1:
        a, b, c = env[i - 1], env[i], env[i + 1]; d = a - 2 * b + c
        return i + (0.5 * (a - c) / d if d < 0 else 0.0)
    return float(i)

def _z(x):
    x = np.asarray(x, float); s = x.std()
    return (x - x.mean()) / s if s > 1e-9 else x * 0

def analyse(path, bpb=4, min_rise_db=3.0, tempo_range=(60, 150)):
    """music file -> analysis dict (track seconds). Deterministic. The tempo is folded by octaves into tempo_range
    (beat trackers often lock onto double or half time)."""
    import librosa
    sr, hop = 22050, 256
    y, _ = librosa.load(path, sr=sr, mono=True)
    dur = len(y) / sr
    if dur < 2: raise SystemExit(f"music file too short to analyse ({dur:.1f} s): {path}")
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    lo_bpm, hi_bpm = (float(x) for x in (tempo_range or (1, 1000)))
    est = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=oenv, sr=sr, hop_length=hop, start_bpm=(lo_bpm * hi_bpm) ** .5))[0])
    while est > hi_bpm and est / 2 >= lo_bpm * .99: est /= 2
    while est < lo_bpm and est * 2 <= hi_bpm * 1.01: est *= 2
    tempo, bf = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, bpm=est, units="frames")
    tempo = float(np.atleast_1d(tempo)[0]); bf = np.asarray(bf, int)
    if len(bf) < 2 * bpb: raise SystemExit(f"no steady beat found in {os.path.basename(path)} ({len(bf)} beats)")
    # refine each beat to the onset peak within +-2 hops, sub-hop by parabolic interpolation
    bt = []
    for f in bf:
        lo, hi = max(0, f - 2), min(len(oenv), f + 3); k = lo + int(np.argmax(oenv[lo:hi]))
        bt.append(_parabolic(oenv, k) * hop / sr)
    bt = np.array(bt)
    # bar phase: kick-band onsets + harmonic (chroma) change are strongest on downbeats
    M = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=hop, n_mels=64, fmax=8000)
    fr = librosa.mel_frequencies(n_mels=66, fmax=8000)[1:-1]; nlow = max(2, int((fr < 150).sum()))
    low_env = librosa.onset.onset_strength(S=librosa.power_to_db(M[:nlow]), sr=sr, hop_length=hop)
    low_at = np.array([low_env[max(0, f - 1):f + 2].max() for f in bf])
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop)
    cs = librosa.util.sync(chroma, bf, aggregate=np.median)[:, 1:]          # column i = beat i .. beat i+1
    cs = cs[:, :len(bf)]; cn = cs / (np.linalg.norm(cs, axis=0, keepdims=True) + 1e-9)
    chg = np.r_[0.0, 1 - (cn[:, 1:] * cn[:, :-1]).sum(0)]
    # big energy rises (section starts, drops) almost always land on a downbeat: they vote for the phase, weighted by dB
    pb = librosa.util.sync(M.sum(0, keepdims=True), bf, aggregate=np.mean)[0, 1:len(bf) + 1]; eb = 10 * np.log10(pb + 1e-12)
    rise = np.array([eb[i:i + 2].mean() - eb[max(0, i - 2):i].mean() if i >= 2 else 0. for i in range(len(eb))])
    # only local maxima count (the 2-beat window smears a rise over neighbours); squared, so one big drop outvotes
    # the small entries a piano or vocal pickup makes on an upbeat
    pk = np.array([rise[i] >= min_rise_db and rise[i] >= rise[max(0, i - 1)] and rise[i] >= rise[min(len(rise) - 1, i + 1)] for i in range(len(rise))])
    vote = np.array([float((rise[p::bpb][pk[p::bpb]] ** 2).sum()) for p in range(bpb)])
    vote = vote / vote.sum() if vote.sum() > 0 else np.zeros(bpb)
    score = _z(low_at) + _z(chg)
    ph = [float(score[p::bpb].mean()) + 4 * float(vote[p]) for p in range(bpb)]; phase = int(np.argmax(ph))
    srt = sorted(ph); conf = float(srt[-1] - srt[-2])
    # the tracker drops weak beats at the very start / end: extend the grid at the median period to cover the track
    per = float(np.median(np.diff(bt[-16:]))); pre_n = 0; ext = list(bt)
    while ext[-1] + per < dur - .05: ext.append(ext[-1] + per)
    per0 = float(np.median(np.diff(bt[:16])))
    while ext[0] - per0 > .05: ext.insert(0, ext[0] - per0); pre_n += 1
    n_ext = len(ext) - len(bt); bt = np.array(ext); phase = (phase + pre_n) % bpb
    db_t = bt[phase::bpb]
    # per-bar energy (full band + low band) and chroma, for drops and loop matching
    t_fr = librosa.frames_to_time(np.arange(M.shape[1]), sr=sr, hop_length=hop)
    pw, plow = M.sum(0), M[:nlow].sum(0)
    edges = list(db_t) + [min(dur, db_t[-1] + np.median(np.diff(db_t)))]
    bars = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t_fr >= a) & (t_fr < b)
        if not m.any(): continue
        ch = chroma[:, m].mean(1)
        bars.append({"t": round(float(a), 4), "db": round(float(10 * np.log10(pw[m].mean() + 1e-12)), 2),
                     "low_db": round(float(10 * np.log10(plow[m].mean() + 1e-12)), 2),
                     "chroma": [round(float(v), 3) for v in ch / (ch.max() + 1e-9)]})
    E = np.array([b["db"] for b in bars]); L = np.array([b["low_db"] for b in bars]); med = float(np.median(E))
    # drop candidates: bars whose next 2 bars are much louder than the 4 before
    raw = []
    for j in range(2, len(bars) - 1):
        pre, post = float(np.median(E[max(0, j - 4):j])), float(E[j:j + 2].mean())
        lpre, lpost = float(np.median(L[max(0, j - 4):j])), float(L[j:j + 2].mean())
        rise, lrise = post - pre, lpost - lpre
        if rise < min_rise_db: continue
        raw.append({"t": bars[j]["t"], "bar": j, "score": round(rise + .5 * max(0., lrise) + (1.0 if pre < med else 0.), 2),
                    "rise_db": round(rise, 2), "low_rise_db": round(lrise, 2), "pre_db": round(pre - med, 2),
                    "post_db": round(post - med, 2), "after_low": bool(pre < med)})
    drops = []
    for c in sorted(raw, key=lambda c: -c["score"]):
        if all(abs(c["bar"] - d["bar"]) >= 4 for d in drops): drops.append(c)
        if len(drops) >= 8: break
    # sections (beat-synced timbre + harmony), snapped to downbeats
    mf = librosa.util.sync(librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13), bf)[:, 1:len(bf) + 1]
    feat = np.vstack([np.apply_along_axis(_z, 1, mf), cs[:, :mf.shape[1]]])
    k = int(np.clip(round(dur / 20), 2, 10))
    try: bnd = librosa.segment.agglomerative(feat, k)
    except Exception: bnd = np.array([0])
    st = sorted(set([0.0] + [float(min(db_t, key=lambda d: abs(d - bt[min(i, len(bt) - 1)]))) for i in bnd if i > 0])) + [dur]
    sections = []
    for a, b in zip(st[:-1], st[1:]):
        if b - a < 1e-3: continue
        m = (t_fr >= a) & (t_fr < b)
        e = float(10 * np.log10(pw[m].mean() + 1e-12)) - med if m.any() else 0.0
        sections.append({"start": round(a, 3), "end": round(b, 3), "energy_db": round(e, 2), "level": "low" if e < -3 else "high" if e > 2 else "mid"})
    # energy curve, 4 per second, dB re the median bar
    step = 0.25; curve = []
    for a in np.arange(0, dur, step):
        m = (t_fr >= a) & (t_fr < a + step)
        curve.append(round(float(10 * np.log10(pw[m].mean() + 1e-12)) - med, 1) if m.any() else None)
    st_ = os.stat(path)
    return {"version": VERSION, "file": os.path.abspath(path), "size": st_.st_size, "mtime": int(st_.st_mtime),
            "duration": round(dur, 4), "tempo": round(tempo, 2), "beats_per_bar": bpb,
            "bar_s": round(float(np.median(np.diff(db_t))), 4), "downbeat_phase": phase, "extrapolated_beats": n_ext, "downbeat_confidence": round(conf, 2),
            "beats": [round(float(t), 4) for t in bt], "downbeats": [round(float(t), 4) for t in db_t],
            "sections": sections, "energy": {"step_s": step, "db": curve}, "bars": bars, "drops": drops}

def load(pr, file=None, refresh=False, S=None):
    """Edit/beats.json for the project's music (re-analysed when the file, its size/mtime or the bar length changed).
    `phrases` (intro / build / drop / break / body / outro) are derived from the cached bars on every load (cheap)."""
    path = music_file(pr, file)
    if path is None: raise SystemExit("no music: set music.file in edit.yaml or pass --file")
    c = cfg(pr, S); B = pr.json("beats.json"); st = os.stat(path); a = _args(c)
    if (refresh or not B or B.get("version") != VERSION or B.get("file") != os.path.abspath(path) or B.get("size") != st.st_size
            or B.get("mtime") != int(st.st_mtime) or B.get("args") != a):
        B = analyse(path, *a); B["args"] = a; B["phrases"] = phrases(B, c); pr.save_json("beats.json", B)
    else: B["phrases"] = phrases(B, c)
    return B


# ------------------------------------------------------------------ phrases (music sections a story can sit on)
PHRASE_LABELS = ("intro", "build", "drop", "body", "break", "outro")

def _novelty(B):
    """per-bar novelty: energy step (dB / 6) + harmonic change (1 - chroma cosine) x 2, bar j vs bar j-1"""
    bars = B["bars"]; n = len(bars); nov = np.zeros(n)
    for j in range(1, n):
        a, b = np.array(bars[j - 1]["chroma"]), np.array(bars[j]["chroma"])
        cos = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        nov[j] = abs(bars[j]["db"] - bars[j - 1]["db"]) / 6 + 2 * (1 - cos)
    return nov

def phrases(B, c=None):
    """music sections in TRACK seconds, on bar lines: [{start, end, bar0, bar1, label, energy_db}].
    Boundaries: bar 0, every drop candidate (B['drops']) and novelty peaks (energy step + chroma change, z >= 1.5,
    >= music.phrase_min_bars apart). Labels: a section that starts on a loud drop candidate (its next bars at or over the
    median bar) is a `drop`; the bars rising into it (each >= music.build_step_db over the bar before, >= 2 bars and
    >= music.build_min_rise_db in all) are its `build`; the first section is the `intro`, a last section that falls
    >= 1.5 dB under the one before (or sits under the median) is the `outro`; other sections are `body` (within 3 dB of
    the loudest) or `break` (under the median). The first section starts at 0 and the last ends at the track's end."""
    c = c or {}; bars = B.get("bars") or []; n = len(bars)
    if n == 0: return []
    min_bars = max(1, int(c.get("phrase_min_bars", 2))); build_rise = float(c.get("build_min_rise_db", 2.0)); step = float(c.get("build_step_db", 1.0))
    E = np.array([b["db"] for b in bars]); med = float(np.median(E)); dur = float(B["duration"])
    cand = {int(d["bar"]): d for d in B.get("drops") or [] if 0 < int(d["bar"]) < n}
    loud = sorted(j for j, d in cand.items() if float(d.get("post_db", 0)) >= 0)          # a real drop lands at or over the median
    nov = _novelty(B); z = _z(nov)
    peaks = [j for j in range(1, n) if z[j] >= 1.5 and nov[j] >= nov[j - 1] and (j == n - 1 or nov[j] >= nov[j + 1])]
    bnd = sorted(set([0] + sorted(cand)))
    for j in sorted(peaks, key=lambda j: -nov[j]):     # strongest novelty first; never closer than min_bars to a boundary
        if all(abs(j - b) >= min_bars for b in bnd): bnd = sorted(bnd + [j])
    bnd.append(n)
    # builds: walk back from each drop while every bar rose by `step` over the one before; the build starts on the first
    # bar that rose (the bar it rose from belongs to the section before)
    builds = {}
    for j in loud:
        k = j - 1
        while k - 1 >= 0 and E[k] >= E[k - 1] + step and (j - k) < 16: k -= 1
        if j - 1 - k >= 2 and E[j - 1] - E[k] >= build_rise: builds[j] = k + 1
    cuts = sorted(set(bnd) | set(builds.values()))
    segs = [[a, b] for a, b in zip(cuts[:-1], cuts[1:]) if b > a]
    out = []
    for a, b in segs:
        lab = "build" if any(builds.get(j) is not None and builds[j] <= a and b <= j for j in loud) else None
        out.append([a, b, lab])
    merged = []                                            # a build split by a novelty peak is one build
    for a, b, lab in out:
        if merged and lab == "build" and merged[-1][2] == "build" and merged[-1][1] == a: merged[-1][1] = b
        else: merged.append([a, b, lab])
    lv = [float(E[a:b].mean()) - med for a, b, _ in merged]; hi = max(lv)
    res = []
    for i, (a, b, lab) in enumerate(merged):
        if lab is None:
            if a in loud: lab = "drop"
            elif i == 0: lab = "intro"
            elif i == len(merged) - 1 and len(merged) > 1 and (lv[i] <= lv[i - 1] - 1.5 or lv[i] < 0): lab = "outro"
            elif lv[i] >= hi - 3: lab = "body"
            elif lv[i] < 0: lab = "break"
            else: lab = "body"
        t0 = 0.0 if a == 0 else float(bars[a]["t"]); t1 = float(bars[b]["t"]) if b < n else dur
        res.append({"start": round(t0, 4), "end": round(t1, 4), "bar0": a, "bar1": b, "label": lab, "energy_db": round(lv[i], 2)})
    return res

def phrases_cut(lay, ph):
    """phrases mapped through a layout (loops) into CUT seconds: [{label, start, end, track_start, piece}]"""
    out = []
    for k, (o, s0, s1) in enumerate(lay["pieces"]):
        for p in ph:
            a, b = max(p["start"], s0), min(p["end"], s1)
            if b - a > 1e-3:
                out.append({"label": p["label"], "start": round(o + a - s0, 4), "end": round(o + b - s0, 4),
                            "track_start": p["start"], "starts_here": abs(a - p["start"]) < 1e-3, "piece": k})
    return out

def _args(c):
    return [int(c.get("beats_per_bar", 4)), float(c.get("drop_min_rise_db", 3.0)), [float(x) for x in (c.get("tempo_range") or [60, 150])]]


# ------------------------------------------------------------------ placement (track -> cut time)
def _first_tagged(TL, beats_):
    edl = TL.pr.json("edl.json", {}) or {}; beat_of = {k["id"]: k.get("beat") for k in edl.get("clips", [])}
    want = [str(b) for b in (beats_ or [])]
    for i, s in enumerate(TL.segs):
        if beat_of.get(s.get("clip")) in want: return i, s, beat_of[s["clip"]]
    return None, None, None

def story_moment(TL, c):
    """cut time of the default drop moment (the payoff): music.drop_cut if > 0, else the first clip tagged with a drop
    beat, else the reveal (the extreme punch-in, aroll.snap)."""
    dc = c.get("drop_cut")
    if isinstance(dc, (int, float)) and dc > 0: return float(dc), "music.drop_cut"
    _, s, b = _first_tagged(TL, c.get("drop_beats"))
    if s is not None: return float(s["t0"]), f"first {b} beat ({s['clip']})"
    if getattr(TL, "snap", None): return float(TL.snap[0]), "the reveal (aroll.snap punch-in)"
    return None, "no drop moment (set music.drop_cut or tag clips with beat: in selects.yaml)"

def story_moments(TL, c):
    """{hook, turn, payoff}: (cut s, why) or (None, why). hook = music.hook_cut if > 0, else the first clip tagged with a
    music.hook_beats beat; turn = music.turn_cut if > 0, else the first music.turn_beats clip, else the end of the hook;
    payoff = story_moment() (the drop moment). `hook_end` is where the hook's last tagged segment ends."""
    out = {}
    hc = c.get("hook_cut"); i, s, b = _first_tagged(TL, c.get("hook_beats"))
    if isinstance(hc, (int, float)) and hc > 0: out["hook"] = (float(hc), "music.hook_cut")
    elif s is not None: out["hook"] = (float(s["t0"]), f"first {b} beat ({s['clip']})")
    else: out["hook"] = (None, "no hook (tag a clip beat: H or set music.hook_cut)")
    he = None
    if s is not None:
        edl = TL.pr.json("edl.json", {}) or {}; beat_of = {k["id"]: k.get("beat") for k in edl.get("clips", [])}
        j = i
        while j + 1 < len(TL.segs) and beat_of.get(TL.segs[j + 1].get("clip")) == b: j += 1
        he = float(TL.segs[j]["t1"]) if j + 1 < len(TL.segs) else None
    out["hook_end"] = (he, "end of the hook" if he is not None else "no hook end")
    tc = c.get("turn_cut"); _, s2, b2 = _first_tagged(TL, c.get("turn_beats"))
    if isinstance(tc, (int, float)) and tc > 0: out["turn"] = (float(tc), "music.turn_cut")
    elif s2 is not None: out["turn"] = (float(s2["t0"]), f"first {b2} beat ({s2['clip']})")
    elif he is not None: out["turn"] = (he, "end of the hook")
    else: out["turn"] = (None, "no turn (tag a clip beat: P / A or set music.turn_cut)")
    out["payoff"] = story_moment(TL, c)
    return out

def plan(pr, TL=None, S=None, need_beats=False, mode=None):
    """where the music sits. Returns {file, mode, fit, offset, drop, B, lay, beats, downbeats, notes} in cut seconds."""
    from .render import Timeline
    TL = TL or Timeline(pr); c = cfg(pr, S or TL.S, mode); M = pr.edit.get("music") or {}
    path = music_file(pr)
    if not path: return None
    mode = mode_of(c); fit = str(c.get("fit", "bars")).lower(); notes = []
    T = TL.N / TL.FPS
    B = None
    if mode != "off" or fit == "bars" or need_beats:
        try: B = load(pr, S=S or TL.S)
        except SystemExit as e:
            if mode != "off": raise
            notes.append(f"beat analysis unavailable ({e}); legacy fit"); fit = "none"
    drop = {"track": float(M.get("drop_track") or 0), "cut": float(M.get("drop_cut") or 0), "source": "edit.yaml (manual)"}
    if mode != "off":
        t_cut, why = story_moment(TL, c)
        cands = B["drops"] or [{"t": d, "score": 0, "bar": i} for i, d in enumerate(B["downbeats"][:1])]
        pick = c.get("drop_pick", "auto")
        if t_cut is None:
            notes.append(why); t_cut = 0.0
        if isinstance(pick, int) and not isinstance(pick, bool):
            if not 0 <= pick < len(cands): raise SystemExit(f"music.drop_pick {pick}: beats.json has {len(cands)} drop candidates (0..{len(cands) - 1})")
            ch = cands[pick]
        else:     # auto: strongest candidate whose placement needs no silent lead-in
            ok = [d for d in cands if d["t"] - t_cut >= 0]
            ch = (ok or cands)[0]
            if not ok: notes.append(f"every drop candidate is earlier in the track than the moment ({t_cut:.2f} s); the music enters late")
            elif _phrase_on(c):        # phrase alignment: among the usable drops, prefer the one whose build starts on the turn
                turn = story_moments(TL, c)["turn"][0]
                if turn is not None and turn < t_cut:
                    bar = float(B.get("bar_s") or 2.0); best = None
                    for k, d in enumerate(ok):
                        b0 = next((p["start"] for p in B.get("phrases") or [] if p["label"] == "build" and abs(p["end"] - d["t"]) < 1e-3), None)
                        miss = min(abs((b0 - (d["t"] - t_cut)) - turn) / bar, 4.0) if b0 is not None else 4.0
                        sc = float(d.get("score") or 0) - float(c.get("phrase_turn_weight", 1.0)) * miss - .01 * k
                        if best is None or sc > best[0]: best = (sc, d, miss)
                    if best[1] is not ch: notes.append(f"phrase alignment: drop candidate {cands.index(best[1])} (its build starts {best[2]:.2f} bar(s) from the turn) over {cands.index(ch)}")
                    ch = best[1]
        drop = {"track": float(ch["t"]), "cut": float(t_cut), "source": why, "candidate": cands.index(ch), "score": ch.get("score")}
    offset = drop["track"] - drop["cut"]
    if fit != "bars": offset = max(0.0, offset)
    out = {"file": path, "mode": mode, "fit": fit, "offset": offset, "drop": drop, "B": B, "T": T, "notes": notes,
           "tolerance": float(c.get("snap_tolerance_s", 0.12)), "cfg": c}
    if B is not None:
        lay = layout(B, offset, T, c, t_end_card=TL.T_END if TL.END else None)
        out.update(lay=lay, beats=lay["beats"], downbeats=lay["downbeats"])
        out["phrases"] = phrases_cut(lay, B.get("phrases") or phrases(B, c))
        out["story"] = story_alignment(TL, c, out)
    else:
        bt = []; out.update(lay=None, beats=bt, downbeats=bt, phrases=[], story={})
    return out

def _phrase_on(c):
    v = c.get("phrase_align", True)
    return v is True or str(v).strip().lower() in ("true", "on", "yes", "1")

def story_alignment(TL, c, P):
    """story beats vs music sections, in cut seconds: payoff vs the drop section start, turn vs the build start, hook vs
    the intro. Each entry: {at, why, section, section_at, error_s, error_bars, on_downbeat}."""
    ms = story_moments(TL, c); ph = P.get("phrases") or []; bar = float((P.get("lay") or {}).get("bar_s") or 2.0)
    downs = np.asarray(P.get("downbeats") or []); out = {}
    want = {"payoff": ("drop",), "turn": ("build", "drop"), "hook": ("intro", "build", "body", "drop")}
    for k in ("hook", "turn", "payoff"):
        t, why = ms[k]
        if t is None: out[k] = {"at": None, "why": why}; continue
        starts = [p for p in ph if p["starts_here"] and p["label"] in want[k]]
        if k == "hook":            # the hook sits IN a section (usually the intro); report the one under it
            cur = next((p for p in ph if p["start"] - 1e-6 <= t < p["end"]), None)
            out[k] = {"at": t, "why": why, "section": cur["label"] if cur else None, "section_at": cur["start"] if cur else None}; continue
        if not starts: out[k] = {"at": t, "why": why, "section": None}; continue
        p = min(starts, key=lambda p: abs(p["start"] - t)); e = p["start"] - t
        out[k] = {"at": t, "why": why, "section": p["label"], "section_at": p["start"], "error_s": round(e, 4), "error_bars": round(e / bar, 3),
                  "on_downbeat": bool(len(downs) and float(np.min(np.abs(downs - p["start"]))) < 2e-3)}
    return out


# ------------------------------------------------------------------ music fit
def _bar_sim(B, i, j):
    """similarity of bar i and bar j (chroma cosine, minus energy difference)"""
    a, b = B["bars"][i], B["bars"][j]
    ca, cb = np.array(a["chroma"]), np.array(b["chroma"])
    cos = float(ca @ cb / (np.linalg.norm(ca) * np.linalg.norm(cb) + 1e-9))
    return cos - abs(a["db"] - b["db"]) / 12 - abs(a["low_db"] - b["low_db"]) / 24

def layout(B, offset, T, c, t_end_card=None):
    """pieces of the track laid end to end (loops on downbeats) + the ending, all in cut seconds."""
    L = B["duration"]; dbs = B["downbeats"]; bar = B["bar_s"]; xf = float(c.get("loop_xfade_s", 0.08))
    min_bars = int(c.get("loop_min_bars", 4)); bi = {b["t"]: i for i, b in enumerate(B["bars"])}
    pieces = []; out, src = 0.0, offset; lead = 0.0
    if src < 0: out, lead, src = -src, -src, 0.0
    for _ in range(64):
        need = T - out
        if src + need <= L - .02: pieces.append([out, src, src + need]); break
        A = [d for d in dbs if d > src + bar * .99 and d + xf / 2 <= L - .01 and d in bi and bi[d] > 0]
        if not A: pieces.append([out, src, L]); break
        # seamless seam: the bar before the jump target sounds like the bar before the jump point, and the bar the
        # target starts sounds like the bar the jump point would have started. The jump point is one of the last
        # 8 downbeats (an outro or a fade at the very end is skipped when an earlier bar matches better).
        def seam(da, d):
            ia, j = bi[da], bi[d]; v = _bar_sim(B, ia - 1, j - 1)
            return v + (_bar_sim(B, ia, j) if ia < len(B["bars"]) else v)
        best = None
        for k, da in enumerate(reversed(A[-8:])):
            for d in dbs:
                if d in bi and bi[d] > 0 and d <= da - min_bars * bar + 1e-3:
                    sc = seam(da, d) - .02 * k
                    if best is None or sc > best[0]: best = (sc, da, d)
        if best is None: pieces.append([out, src, L]); break
        _, d_a, d_b = best
        if d_a <= src + bar * .99: pieces.append([out, src, L]); break
        pieces.append([out, src, d_a]); out += d_a - src; src = d_b
    beats, downs = [], []
    for o, s0, s1 in pieces:
        beats += [o + b - s0 for b in B["beats"] if s0 - 1e-6 <= b < s1 - 1e-6]
        downs += [o + d - s0 for d in dbs if s0 - 1e-6 <= d < s1 - 1e-6]
    last = pieces[-1]; track_end_out = last[0] + (last[2] - last[1]) if abs(last[2] - L) < .03 else None
    end = {"kind": "fade_bar"}
    if track_end_out is not None and T - 1.5 * bar <= track_end_out <= T + .02:
        end = {"kind": "natural", "at": track_end_out}
    else:
        tail_min = float(c.get("end_min_tail_s", 0.5)); nb = float(c.get("end_tail_bars", 1))
        cand = [d for d in downs if d <= T - tail_min]
        if t_end_card is not None:      # prefer the downbeat nearest the end card when it leaves a tail
            near = [d for d in cand if d >= t_end_card - bar]
            cand = near or cand
        d_end = cand[-1] if cand else max(0.0, T - tail_min)
        end = {"kind": "fade_bar", "downbeat": d_end, "fade_end": min(T, d_end + nb * bar)}
    return {"pieces": pieces, "lead_in": lead, "beats": beats, "downbeats": downs, "end": end, "xfade_s": xf, "bar_s": bar,
            "loops": len(pieces) - 1}

def render(y, sr, lay, N):
    """y: (channels, n) full track at sr -> (N, channels) bed laid out per `lay` (equal-power crossfades on the seams)."""
    ch = y.shape[0]; out = np.zeros((ch, N), np.float32); h = int(lay["xfade_s"] * sr) // 2
    P = lay["pieces"]
    for k, (o, s0, s1) in enumerate(P):
        a, b = int(round(s0 * sr)), int(round(s1 * sr)); oa = int(round(o * sr))
        a0 = max(0, a - (h if k > 0 else 0)); b1 = min(y.shape[1], b + (h if k < len(P) - 1 else 0))
        seg = y[:, a0:b1].astype(np.float32).copy(); o0 = oa - (a - a0); n = seg.shape[1]
        fi, fo = a - a0, b1 - b                          # fade-in / fade-out half-widths actually available
        if k > 0 and fi: w = min(2 * fi, n); seg[:, :w] *= np.sin(np.linspace(0, np.pi / 2, w))[None]
        if k < len(P) - 1 and fo: w = min(2 * fo, n); seg[:, n - w:] *= np.cos(np.linspace(0, np.pi / 2, w))[None]
        if k == 0 and lay["lead_in"] > 0:
            f = min(int(.05 * sr), n); seg[:, :f] *= np.linspace(0, 1, f)[None]
        i0, i1 = max(0, o0), min(N, o0 + n)
        if i1 > i0: out[:, i0:i1] += seg[:, i0 - o0:i1 - o0]
    e = lay["end"]
    if e["kind"] == "natural":
        i = int(e["at"] * sr); f = int(.02 * sr)
        if 0 < i <= N: out[:, max(0, i - f):i] *= np.linspace(1, 0, i - max(0, i - f))[None]; out[:, i:] = 0
    else:
        i, j = int(e["downbeat"] * sr), int(e["fade_end"] * sr)
        if j > i: out[:, i:j] *= (np.cos(np.linspace(0, np.pi / 2, j - i)) ** 2)[None]
        out[:, j:] = 0
        f = int(.02 * sr)                        # never a click at the very last sample
        if j > N and N > f: out[:, N - f:] *= np.linspace(1, 0, f)[None]
    return out.T


# ------------------------------------------------------------------ cuts mode
def _nearest(grid, t, tol):
    if not len(grid): return None
    g = np.asarray(grid); k = int(np.argmin(np.abs(g - t)))
    return float(g[k]) if abs(g[k] - t) <= tol else None

def _q(t, fps): return round(t * fps) / fps

def _qb(b, t, fps, tol):
    """the frame time nearest the beat b that keeps the move from t within tol (None if neither neighbour does)"""
    f = b * fps; opts = sorted({int(np.floor(f)), int(np.ceil(f))}, key=lambda k: abs(k - f))
    for k in opts:
        if abs(k / fps - t) <= tol + 1e-9: return k / fps
    return None

def _time_keys(d, path=()):
    """(path, value) for graphic entry times in a params tree: keys `at`, `*_at`, `enter`"""
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and (k == "at" or k.endswith("_at") or k == "enter") and not k.startswith("out"):
                yield path + (k,), float(v)
            elif isinstance(v, (dict, list)): yield from _time_keys(v, path + (k,))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if isinstance(v, (dict, list)): yield from _time_keys(v, path + (i,))

def _set(d, path, v):
    for k in path[:-1]: d = d[k]
    d[path[-1]] = v

def _siblings(d, path):
    for k in path[:-1]: d = d[k]
    return [float(v) for k, v in d.items() if k != path[-1] and isinstance(v, (int, float)) and not isinstance(v, bool)
            and (k == "at" or k.endswith("_at") or k == "enter")] if isinstance(d, dict) else []

def suggest(pr, TL, P):
    """cutaway in/out + graphic-entry moves onto beats. Returns (moves, report_lines). Never moves an A-roll cut."""
    c = P["cfg"]; tol = P["tolerance"]; fps = TL.FPS; beats = P["beats"]; downs = set(round(d, 4) for d in P["downbeats"])
    lead = float(c.get("gfx_lead_s", 0.25)); min_ar = float(c.get("min_aroll_s", 0.5)); half = .5 / fps
    words = [w for w in pr.json("words.json", []) if len(w) >= 3]
    bounds = sorted(set([s["t0"] for s in TL.segs] + [TL.T_END]))
    on_b = lambda t: min(abs(b - t) for b in bounds) < half
    seg_of = lambda t: next((s for s in TL.segs if s["t0"] - 1e-6 <= t < s["t1"] - 1e-6), None)
    first_word = lambda t: next((w[0] for w in words if w[1] > t + half), None)
    els = {}
    if os.path.exists(pr.e("elements.jsonl")):
        for l in open(pr.e("elements.jsonl"), encoding="utf-8"):
            r = json.loads(l)
            if r["id"] not in els: els[r["id"]] = r
    cuts = sorted(TL.cuts, key=lambda x: x["start"]); moves, rep = [], []
    on_before = on_after = total = 0
    def beat_label(b): return "downbeat" if round(b, 4) in downs else "beat"
    for idx, cu in enumerate(cuts):
        prev_end = max([x["end"] for x in cuts[:idx]] or [0.0]); nxt = min([x["start"] for x in cuts[idx + 1:]] or [TL.T_END])
        for edge in ("start", "end"):
            t = cu[edge]; total += 1
            b = _nearest(beats, t, tol)
            if b is not None and abs(b - t) <= 1 / fps: on_before += 1; on_after += 1; rep.append(f"  {cu['id']}.{edge:5s} {t:7.3f}  on the {beat_label(b)} ({(b - t) * 1000:+.0f} ms)"); continue
            if b is None: rep.append(f"  {cu['id']}.{edge:5s} {t:7.3f}  no beat within {tol * 1000:.0f} ms: keep"); continue
            nt = _qb(b, t, fps, tol); d = (nt - t) if nt is not None else 0.0; why = None
            if nt is None: why = "the beat's frame is outside the tolerance"
            elif abs(d) < 1e-6: why = "already within a frame"
            elif edge == "start":
                if on_b(t) and d > 0: why = "would show a sliver of the next shot before the cutaway"
                elif seg_of(t - half) is not seg_of(nt - half) and not on_b(t): why = "would cross an A-roll cut"
                else:
                    s = seg_of(nt - half); piece = nt - max(s["t0"] if s else 0, prev_end)
                    fw = first_word(t); keys = [e["t_key"] for e in els.values() if e.get("t_key") is not None and e["role"] == "cutaway" and abs(e["f"] / fps - t) < half]
                    bound = max([x - lead for x in ([fw] if fw is not None else []) + keys] or [-1e9])
                    if nt <= prev_end + min_ar: why = f"leaves under {min_ar:.2f} s after the previous cutaway"
                    elif piece < min_ar: why = f"leaves a {piece:.2f} s A-roll sliver (< {min_ar:.2f} s)"
                    elif d < 0 and nt < bound - 1e-6: why = f"GFX-01: would show {bound + lead - nt:.2f} s before it is said"
            else:
                if on_b(t) and d < 0: why = "would show a sliver of the shot before the A-roll cut"
                elif seg_of(t + half) is not seg_of(nt + half) and not on_b(t): why = "would cross an A-roll cut"
                elif nt >= nxt - min_ar: why = f"leaves under {min_ar:.2f} s before the next cutaway or the end card"
                else:
                    s = seg_of(nt + half); piece = min(s["t1"] if s else TL.T_END, nxt) - nt
                    if piece < min_ar: why = f"leaves a {piece:.2f} s A-roll sliver (< {min_ar:.2f} s)"
            if why: rep.append(f"  {cu['id']}.{edge:5s} {t:7.3f}  {beat_label(b)} at {b:.3f} ({d * 1000:+.0f} ms): keep, {why}"); continue
            moves.append({"kind": "cutaway", "id": cu["id"], "edge": edge, "old": t, "new": nt, "beat": b}); on_after += 1
            rep.append(f"  {cu['id']}.{edge:5s} {t:7.3f} -> {nt:7.3f}  ({d * 1000:+.0f} ms, {beat_label(b)} at {b:.3f})")
    gm = []; g_on = g_after = g_tot = 0
    span = {cu["id"]: (cu["start"], cu["end"]) for cu in cuts}
    for m in moves: span[m["id"]] = (m["new"], span[m["id"]][1]) if m["edge"] == "start" else (span[m["id"]][0], m["new"])
    segt = {s["id"]: (s["t0"], s["t1"]) for s in TL.segs}
    groups = [("cutaways", x.get("id"), x, span.get(x.get("id"))) for x in TL.E.get("cutaways", [])]
    for k in ("roto", "chest"):
        for x in TL.E.get(k, []):
            ids = [x["segment"]] if isinstance(x["segment"], str) else x["segment"]
            rng = [segt[i] for i in ids if i in segt]
            groups.append((k, x["segment"] if isinstance(x["segment"], str) else ",".join(ids), x, (min(r[0] for r in rng), max(r[1] for r in rng)) if rng else None))
    for kind, gid, item, rng in groups:
        if rng is None: continue
        for path, v in _time_keys(item.get("params") or {}):
            if v < rng[0] + half or v >= rng[1] - half: continue      # clamped to the shot start / after it: moving changes nothing
            g_tot += 1; b = _nearest(beats, v, tol); name = f"{kind}:{gid}." + ".".join(str(p) for p in path)
            if b is not None and abs(b - v) <= 1 / fps: g_on += 1; g_after += 1; continue
            if b is None: continue
            nv = _qb(b, v, fps, tol)
            if nv is None or nv < rng[0] + half or nv >= rng[1] - half: continue
            sib = _siblings(item["params"], path)
            if any(min(v, nv) - 1e-6 <= s_ <= max(v, nv) + 1e-6 for s_ in sib): rep.append(f"  {name} {v:.3f}: keep (would reorder with a sibling time)"); continue
            said = min((w[0] for w in words if abs(w[0] - v) <= .35), key=lambda w0: abs(w0 - v), default=v)
            if nv < said - lead - 1e-6: rep.append(f"  {name} {v:.3f}: keep (GFX-01, its word is at {said:.2f} s)"); continue
            gm.append({"kind": kind, "id": gid, "path": list(path), "old": v, "new": round(nv, 3), "beat": b}); g_after += 1
            rep.append(f"  {name} {v:.3f} -> {nv:.3f} ({(nv - v) * 1000:+.0f} ms, {beat_label(b)} at {b:.3f})")
    head = [f"cut points on the beat (within 1 frame): {on_before}/{total} now, {on_after}/{total} with the moves",
            f"graphic entries on the beat: {g_on}/{g_tot} now, {g_after}/{g_tot} with the moves",
            f"A-roll cuts are never moved (engine invariant: edits snap to segment boundaries)"]
    return moves + gm, head + rep


# ------------------------------------------------------------------ apply (edit.yaml, comments kept)
def _block(lines, start_re):
    """[i0, i1) line range of the list item whose first line matches start_re"""
    i0 = next((i for i, l in enumerate(lines) if re.search(start_re, l)), None)
    if i0 is None: return None
    ind = len(lines[i0]) - len(lines[i0].lstrip())
    i1 = i0 + 1
    while i1 < len(lines):
        l = lines[i1]; s = l.strip()
        if s and not s.startswith("#") and (len(l) - len(l.lstrip())) <= ind: break
        i1 += 1
    return i0, i1

def _fmt(v): return ("%.3f" % v).rstrip("0").rstrip(".") if "." in "%.3f" % v else "%.3f" % v

def _patch(text, E_new, edits):
    lines = text.split("\n")
    for start_re, key, old, new, insert_after in edits:
        rg = _block(lines, start_re)
        if rg is None: return None
        i0, i1 = rg      # old=None: replace the key's single value whatever it is; else match the number
        pat = re.compile(r"(?<![\w-])(" + re.escape(key) + r":[ \t]*)(" + (r"[^\s,}#]+" if old is None else r"-?\d+(?:\.\d+)?") + ")")
        hits = [(i, m) for i in range(i0, i1) for m in pat.finditer(lines[i]) if old is None or abs(float(m.group(2)) - old) < 5e-4]
        if len(hits) == 1:
            i, m = hits[0]; lines[i] = lines[i][:m.start(2)] + new + lines[i][m.end(2):]
        elif not hits and insert_after:
            j = next((i for i in range(i0, i1) if re.search(r"(?<![\w-])" + re.escape(insert_after) + r":", lines[i])), None)
            if j is None: return None
            ind = re.match(r"\s*(?:-\s*)?", lines[j]).end(); lines.insert(j + 1, " " * ind + f"{key}: {new}")
        else: return None
    import yaml
    out = "\n".join(lines)
    return out if yaml.safe_load(out) == E_new else None

def apply(pr, P, moves):
    """write the drop placement + moves into edit.yaml (backup first). Comments are kept when the text patch verifies."""
    import yaml
    src = pr.e("edit.yaml"); text = open(src, encoding="utf-8").read(); E = yaml.safe_load(text); En = copy.deepcopy(E); edits = []
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); bak = pr.e(f"edit.yaml.bak-{stamp}"); shutil.copy2(src, bak)
    mu = En.setdefault("music", {}) or {}; En["music"] = mu
    if P["mode"] != "off":
        if mode_of(cfg(pr)) != P["mode"]:      # the run's mode becomes the edit's, so `cves mix` uses the same placement
            mu["sync"] = P["mode"]; edits.append((r"^music:", "sync", None, P["mode"], "file"))
        for k in ("drop_track", "drop_cut"):
            nv = round(P["drop"]["track" if k == "drop_track" else "cut"], 3); ov = (E.get("music") or {}).get(k)
            if ov is None or abs(float(ov) - nv) >= 5e-4:
                mu[k] = nv; edits.append((r"^music:", k, float(ov) if ov is not None else -1e9, _fmt(nv), "file"))
    for m in moves:
        if m["kind"] == "cutaway":
            item = next(x for x in En["cutaways"] if x.get("id") == m["id"]); re_id = r"^\s*-\s*id:\s*" + re.escape(str(m["id"])) + r"\s*(#.*)?$"
            ov = item[m["edge"]]; item[m["edge"]] = round(m["new"], 3)
            edits.append((re_id, m["edge"], float(ov), _fmt(round(m["new"], 3)), None))
            if item.get("snap", True) is not False:
                other = "end" if m["edge"] == "start" else "start"
                TLv = m.get("resolved_other"); other_moved = any(x is not m and x["kind"] == "cutaway" and x["id"] == m["id"] for x in moves)
                if TLv is not None and not other_moved and abs(float(item[other]) - TLv) >= 5e-4:      # the other edge was snapped: pin its resolved time
                    edits.append((re_id, other, float(item[other]), _fmt(round(TLv, 3)), None)); item[other] = round(TLv, 3)
                had = "snap" in item; item["snap"] = False
                edits.append((re_id, "snap", None, "false", None if had else "end"))
        else:
            coll = En["cutaways"] if m["kind"] == "cutaways" else En[m["kind"]]
            if m["kind"] == "cutaways": item = next(x for x in coll if x.get("id") == m["id"]); re_id = r"^\s*-\s*id:\s*" + re.escape(str(m["id"])) + r"\s*(#.*)?$"
            else:
                item = next(x for x in coll if (x["segment"] if isinstance(x["segment"], str) else ",".join(x["segment"])) == m["id"])
                first = m["id"].split(",")[0]; re_id = r"^\s*-\s*\{?\s*segment:\s*\[?\s*" + re.escape(first) + r"\b"
            _set(item["params"], m["path"], m["new"])
            edits.append((re_id, str(m["path"][-1]), m["old"], _fmt(m["new"]), None))
    out = _patch(text, En, edits)
    how = "text patch (comments kept)"
    if out is None:
        out = yaml.safe_dump(En, sort_keys=False, allow_unicode=True, width=140); how = "re-dumped (comments lost; see the backup)"
    with open(src, "w", encoding="utf-8") as f: f.write(out)
    return bak, how


# ------------------------------------------------------------------ CLI
def report(pr, mode=None, apply_=False, file=None, as_json=False, refresh=False):
    from .render import Timeline
    if file:      # analyse a given file (e.g. a candidate track) and write Edit/beats.json for it
        path = music_file(pr, file); a = _args(cfg(pr))
        B = analyse(path, *a); B["args"] = a; pr.save_json("beats.json", B)
        lines = _summary(B)
        cur = music_file(pr)
        if not cur or os.path.abspath(cur) != os.path.abspath(path): lines.append(f"(not the edit's music: set music.file: {file} in edit.yaml to sync to it)")
        print(json.dumps(B, indent=1) if as_json else "\n".join(lines)); return 0
    B = load(pr, refresh=refresh)
    lines = _summary(B)
    TL = Timeline(pr); P = plan(pr, TL, mode=mode)
    lines += ["", f"sync mode: {P['mode']}   fit: {P['fit']}"]
    d = P["drop"]
    lines.append(f"drop: track {d['track']:.3f} s -> cut {d['cut']:.3f} s ({d['source']}"
                 + (f", candidate {d['candidate']} score {d['score']}" if "candidate" in d else "") + f"); music offset {P['offset']:+.3f} s")
    lay = P.get("lay")
    if lay:
        e = lay["end"]
        lines.append(f"fit: {lay['loops']} loop(s), lead-in {lay['lead_in']:.2f} s, ending "
                     + (f"natural at {e['at']:.2f} s" if e["kind"] == "natural" else f"on the downbeat at {e['downbeat']:.3f} s, one-bar tail to {e['fade_end']:.3f} s")
                     + f" (video {P['T']:.3f} s)")
    lines += [f"note: {n}" for n in P["notes"]]
    if P.get("phrases"):
        lines.append("sections (cut s): " + "  ".join(f"{p['start']:.2f} {p['label']}" for p in P["phrases"] if p["starts_here"] or p["piece"] == 0 and p["start"] < 1e-3))
        for k in ("hook", "turn", "payoff"):
            s = P["story"].get(k) or {}
            if s.get("at") is None: lines.append(f"  {k:6s} -: {s.get('why', '')}"); continue
            if "error_s" in s: lines.append(f"  {k:6s} {s['at']:7.3f} s ({s['why']}): {s['section']} starts {s['error_s'] * 1000:+.0f} ms away ({s['error_bars']:+.2f} bar){'' if s['on_downbeat'] else ', NOT on a downbeat'}")
            else: lines.append(f"  {k:6s} {s['at']:7.3f} s ({s['why']}): " + (f"inside the {s['section']}" if s.get("section") else "no matching section"))
    moves = []
    if P["mode"] in ("cuts", "full"):
        moves, rep = suggest(pr, TL, P)
        for m in moves:
            if m["kind"] == "cutaway":
                cu = next(x for x in TL.cuts if x["id"] == m["id"]); m["resolved_other"] = cu["end" if m["edge"] == "start" else "start"]
        lines += ["", f"beat moves (tolerance {P['tolerance'] * 1000:.0f} ms):"] + rep
    if P["mode"] == "full":
        from . import mix as MX
        snaps = []; MX.all_cues(TL, plan=P, log=snaps)
        lines += ["", f"SFX beat nudges at mix time (current edit.yaml): {len(snaps)}"] + [f"  {n} peak {a:.3f} -> {b:.3f} ({(b - a) * 1000:+.0f} ms)" for n, a, b in snaps[:20]]
    if apply_:
        if P["mode"] == "off": raise SystemExit("--apply needs a sync mode: pass --sync drop|cuts|full or set music.sync")
        bak, how = apply(pr, P, moves)
        lines += ["", f"applied {len(moves)} move(s) + drop placement to Edit/edit.yaml ({how}); backup {os.path.basename(bak)}"]
    elif moves: lines += ["", "run again with --apply to write these into edit.yaml (a backup is kept)"]
    rec = dict(B); rec["plan"] = {"mode": P["mode"], "offset": P["offset"], "drop": P["drop"], "lay": lay, "moves": moves}
    pr.save_json("beats.json", rec)
    print(json.dumps(rec["plan"], indent=1, default=float) if as_json else "\n".join(lines))
    return 0

def _summary(B):
    L = [f"{os.path.basename(B['file'])}: {B['duration']:.1f} s, {B['tempo']:.1f} BPM, {len(B['beats'])} beats, "
         f"{len(B['downbeats'])} bars of {B['beats_per_bar']} ({B['bar_s']:.3f} s), downbeat phase {B['downbeat_phase']} (confidence {B['downbeat_confidence']})",
         "sections: " + "  ".join(f"{s['start']:.1f}-{s['end']:.1f} {s['level']}({s['energy_db']:+.1f})" for s in B["sections"]),
         "phrases: " + "  ".join(f"{p['start']:.1f}-{p['end']:.1f} {p['label']}({p['energy_db']:+.1f})" for p in B.get("phrases") or []),
         "drop candidates (track s, score, rise dB):"]
    L += [f"  [{i}] {d['t']:7.3f}  score {d['score']:5.2f}  rise {d['rise_db']:+.1f} dB (low {d['low_rise_db']:+.1f}){'  after a low stretch' if d['after_low'] else ''}"
          for i, d in enumerate(B["drops"])] or ["  none (no rise above music.drop_min_rise_db)"]
    return L
