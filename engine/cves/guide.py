"""Trending-sound slot for organic posts (docs/VIRAL.md, docs/MUSIC.md section "Platform sound slot").

    edit.yaml  music: {slot: platform, guide: Music/trend.mp3 | 128 | "128 bpm" | {bpm: 128, first_beat: 0.2} | Edit/x_beats.json,
                       sound: "<the sound's name or link in the app>", drop_cut: 6.4}

The edit is cut to a guide (a reference track, a beats.json or a bare tempo), but the delivered master carries NO music:
voice + SFX only. The poster adds the sound in the app (where the platform licenses it), so the master never holds music
we have no rights to. Mix writes the guide as its own stem (Edit/stems/guide.wav: the reference track laid where the edit
expects it, or a click track for a tempo), `cves deliver` ships it next to the master with POSTING.md (which sound, where
to start it in the track, where the drop lands). Ads never use the slot (schema error): an ad carries licensed music in
the file (RULEBOOK §0.12).

Times returned here are CUT seconds (the video's timeline) unless named `track`."""
import os, re, json
import numpy as np

SR = 48000


def is_slot(pr_or_edit):
    E = pr_or_edit if isinstance(pr_or_edit, dict) else (pr_or_edit.edit or {})
    M = E.get("music") or {}
    return isinstance(M, dict) and str(M.get("slot") or "file").strip().lower() == "platform"


def spec(pr):
    """normalised guide: {kind: file|beats|bpm|None, path, bpm, first_beat, sound, drop_cut, drop_track, offset} or None"""
    if not is_slot(pr): return None
    M = pr.edit.get("music") or {}; g = M.get("guide")
    s = {"kind": None, "path": None, "bpm": None, "first_beat": None, "sound": M.get("sound"),
         "drop_cut": M.get("drop_cut"), "drop_track": M.get("drop_track"), "offset": M.get("offset"), "raw": g}
    if isinstance(g, bool) or g is None: return s
    if isinstance(g, (int, float)): s.update(kind="bpm", bpm=float(g)); return s
    if isinstance(g, dict):
        if g.get("bpm") or g.get("tempo"): s.update(kind="bpm", bpm=float(g.get("bpm") or g.get("tempo")), first_beat=g.get("first_beat")); return s
        g = g.get("file") or g.get("beats")
        if not g: return s
    g = str(g).strip(); m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:bpm)?", g, re.I)
    if m: s.update(kind="bpm", bpm=float(m.group(1))); return s
    p = g if os.path.isabs(g) else pr.p(g)
    s.update(kind="beats" if g.lower().endswith(".json") else "file", path=p)
    return s


def problems(pr):
    """[messages] that make the slot unusable (schema errors and the QC FAIL use them)"""
    s = spec(pr)
    if s is None: return []
    if s["kind"] is None: return ["music.slot: platform needs music.guide: a reference track, a beats.json or a tempo (e.g. 120)"]
    if s["kind"] == "bpm" and not (20 <= s["bpm"] <= 300): return [f"music.guide: tempo {s['bpm']:g} BPM is outside 20-300"]
    if s["kind"] in ("file", "beats") and not os.path.exists(s["path"]): return [f"music.guide: file not found: {s['raw']}"]
    return []


def _bpb(pr, S=None):
    from . import beats as BT
    return int(BT.cfg(pr, S).get("beats_per_bar", 4))


def grid(pr, T, S=None, TL=None):
    """the guide's beat grid under the edit: {kind, tempo, beats, downbeats, offset (track s at cut 0 or None), drop_cut, notes}"""
    s = spec(pr)
    if s is None or problems(pr): return None
    bpb = _bpb(pr, S); notes = []
    if s["kind"] == "bpm":
        per = 60.0 / s["bpm"]; dc = s["drop_cut"] if isinstance(s["drop_cut"], (int, float)) and s["drop_cut"] > 0 else None
        fb = float(s["first_beat"]) if s["first_beat"] is not None else ((dc % per) if dc is not None else 0.0)
        beats = [fb + k * per for k in range(int((T - fb) / per) + 1) if fb + k * per <= T + 1e-6]
        ref = dc if dc is not None else fb
        downs = [b for b in beats if round((b - ref) / per) % bpb == 0]
        return {"kind": "bpm", "tempo": s["bpm"], "beats": beats, "downbeats": downs, "offset": None, "drop_cut": dc, "notes": notes, "spec": s}
    if s["kind"] == "beats":
        with open(s["path"], encoding="utf-8") as f: B = json.load(f)
        off = s["offset"]
        if off is None and s["drop_track"] is not None and s["drop_cut"] is not None: off = float(s["drop_track"]) - float(s["drop_cut"])
        if off is None and s["drop_cut"] and B.get("drops"): off = float(B["drops"][0]["t"]) - float(s["drop_cut"])
        off = float(off or 0.0)
        cut = lambda xs: [float(x) - off for x in xs if 0 <= float(x) - off <= T + 1e-6]
        return {"kind": "beats", "tempo": B.get("tempo"), "beats": cut(B.get("beats") or []), "downbeats": cut(B.get("downbeats") or []),
                "offset": off, "drop_cut": s["drop_cut"], "notes": notes, "spec": s}
    # a reference track: placed exactly as `cves beats` places music (beats.plan), so cut snapping and QC agree
    from . import beats as BT
    P = BT.plan(pr, TL, S=S, need_beats=True)
    if P is None: return None
    notes += P.get("notes") or []
    d = P.get("drop") or {}
    dc = d.get("cut") if (P["mode"] != "off" or s["drop_cut"]) else None
    return {"kind": "file", "tempo": (P.get("B") or {}).get("tempo"), "beats": list(P.get("beats") or []), "downbeats": list(P.get("downbeats") or []),
            "offset": float(P["offset"]), "drop_cut": dc, "notes": notes, "spec": s, "plan": P}


def click_track(beats, downbeats, N, sr=SR):
    """a quiet click on every beat (accented on downbeats): the guide stem for a bare tempo"""
    y = np.zeros(N, np.float32); L = int(.02 * sr); t = np.arange(L) / sr
    down = {round(d, 4) for d in downbeats}
    for b in beats:
        acc = round(b, 4) in down; i = int(round(b * sr))
        if i >= N: continue
        c = np.sin(2 * np.pi * (1500 if acc else 1000) * t) * np.exp(-t * 180) * (.5 if acc else .3)
        j = min(N, i + L); y[i:j] += c[:j - i].astype(np.float32)
    return y


def stem(pr, N, sr=SR, S=None, TL=None):
    """(N,) guide stem in cut time, peak -6 dBFS: the reference track laid as `cves beats` lays it, or a click track"""
    T = N / sr; g = grid(pr, T, S, TL)
    if g is None: return None, None
    if g["kind"] == "file":
        import librosa
        from . import beats as BT
        P = g["plan"]
        if P.get("lay"):
            y, _ = librosa.load(P["file"], sr=sr, mono=False); y = y if y.ndim == 2 else np.stack([y, y])
            out = BT.render(y[:2], sr, P["lay"], N).mean(1)
        else:
            y, _ = librosa.load(P["file"], sr=sr, mono=True, offset=max(0.0, g["offset"]), duration=T + 1)
            out = np.pad(y, (0, max(0, N - len(y))))[:N]
    else:
        out = click_track(g["beats"], g["downbeats"], N, sr)
    pk = float(np.abs(out).max())
    if pk > 0: out = out * (10 ** (-6 / 20) / pk)
    return out.astype(np.float32), g


def _mmss(t):
    t = max(0.0, float(t)); m, s = divmod(t, 60); return f"{int(m)}:{s:05.2f}"


def posting_md(pr, S, master_name, guide_name, T, g, cuts=()):
    """POSTING.md: what the person posting must add in the app, and where"""
    from . import platforms as PF
    E = pr.edit; s = g["spec"]; title = (E.get("project") or {}).get("title", "edit")
    pf = PF.profile(S); dur = PF.duration(S)
    sound = s.get("sound") or (os.path.basename(s["path"]) if s.get("path") else None)
    tempo = f"{g['tempo']:.1f} BPM" if g.get("tempo") else "unknown"
    L = [f"# Posting notes: {title}", "",
         f"`{master_name}` has **no music on purpose** (`music.slot: platform`): voice and sound effects only. "
         "Add the sound in the app when you post, so the platform licenses it. Never bake it into the file.", "",
         "| | |", "|---|---|",
         f"| Platform | {pf['label'] if pf else 'not set (style platform.target)'} |",
         f"| Sound to add | {sound or 'MISSING: set edit.yaml music.sound to the sound name or link'} |",
         f"| Tempo the edit is cut to | {tempo}, {_bpb(pr, S)} beats per bar |"]
    if g.get("offset") is not None:
        L.append(f"| Start the sound at | **{_mmss(g['offset'])}** into the track (the cuts are on its beat from there) |"
                 if g["offset"] >= 0 else f"| Start the sound at | 0:00, **{_mmss(-g['offset'])}** after the video starts (the app cannot delay a sound: move music.drop_cut later) |")
    else:
        L.append("| Start the sound at | where its first strong beat lands on the video's first frame (the edit is cut to the tempo only) |")
    if g.get("drop_cut") is not None: L.append(f"| The drop lands at | **{_mmss(g['drop_cut'])}** of the video |")
    L += [f"| Video length | {T:.1f} s" + (f" (platform ideal {dur[0]:g}-{dur[1]:g} s, max {dur[2]:g} s)" if dur else "") + " |",
          f"| Loop | {'yes: the end flows back into the start, keep the sound looping' if S.get('structure.loop') else 'no'} |",
          f"| Guide stem | `{guide_name}`: the reference the edit was cut to. For checking sync only; do not upload it |", "",
          "## In the app", "",
          f"1. Upload the master. Keep its original audio at 100 % (the voice and SFX are mixed to {S.get('sound.master_lufs', -14):g} LUFS).",
          f"2. Add the sound above{' and trim its start to ' + _mmss(g['offset']) if (g.get('offset') or 0) > 0 else ''}.",
          "3. Set the added sound low enough that every word stays clear: about 25-40 % on TikTok / Reels / Shorts sliders.",
          "4. Play it once with sound on: the first cut and the drop should land on the beat. If they drift, re-trim the start.", ""]
    if cuts:
        L += ["## First cuts vs the beat", "", "| cut (s) | nearest beat (s) | off (ms) |", "|---|---|---|"]
        bt = np.asarray(g["beats"] or [0.0])
        for c in list(cuts)[:8]:
            b = float(bt[int(np.argmin(np.abs(bt - c)))]); L.append(f"| {c:.3f} | {b:.3f} | {1000 * (c - b):+.0f} |")
        L.append("")
    L += ["Ads never use this slot: an ad carries licensed music in the file (RULEBOOK §0.12).", ""]
    return "\n".join(L)
