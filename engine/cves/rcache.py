"""Incremental render: the frame cache (docs/ARCHITECTURE.md §6b, docs/CONTRACTS.md §3 `frames/_cache.json`).

Every frame of a full render is keyed by a hash of everything that decides its pixels and its element records:

  * global: the engine code (every .py of the package, the motion pieces / runtime, the repo's fonts and icons), the merged
    style minus the sections the renderer never reads (sound, mix, voice, music, delivery, review, treatments, qc, story,
    autocut, render), the canvas, proxy, rate, timeline length, the end card, the caption config, the roto list (text_behind
    harmonises one size across instances), snap / creep / lift, the broll track, the assets registry and a listing
    (path, size, mtime) of Raw/, Assets/, Brand/, Edit/conform/ and the user template / motion folders (~/.cves/templates,
    ~/.cves/motion, $CVES_TEMPLATES, $CVES_MOTION);
  * per A-roll segment, for the frames that show it: the segment, its plate / matte files (size, mtime), its face track,
    zoom, colour match / exposure gain, roto and chest entries;
  * per frame: the frame index, the cutaway covering it (its whole entry), the transition state there (kind, strength,
    side, boundary), the caption events and hide windows that contain it.

`cves render` / `cves build` then re-render only the frames whose key changed (one cutaway tweak re-renders that
cutaway's range, plus any A-roll shot whose framing the change moved) and rebuild `Edit/elements.jsonl` from the records
of the untouched frames, so frames, element log and the encoded master are the same as a full render's. A frame whose
PNG is missing is rendered again. The index (`<frames>/_cache.json`) records the element log it pairs with (sha256):
anything else that rewrote the log invalidates every frame. `--only` renders drop their frames from the index.
Off with style `render.cache: false` or `--no-cache`."""
import os, json, math, hashlib, functools

VERSION = 1
INDEX = "_cache.json"
# style sections the renderer never reads (audio, delivery, review loop, story step): a change there re-renders nothing
NON_VISUAL = ("sound", "mix", "voice", "music", "delivery", "review", "treatments", "qc", "story", "autocut", "render", "_evidence")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def _h(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


@functools.lru_cache(1)
def code_hash():
    """every file of the engine that can change a pixel: the package's .py (QC excluded), motion pieces and runtime, and
    a listing of the repo's fonts / icons"""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(HERE):
        dirs[:] = sorted(d for d in dirs if d not in ("qc", "__pycache__"))
        for f in sorted(files):
            if f.endswith((".py", ".js", ".css", ".html", ".yaml", ".yml", ".json", ".svg")):
                p = os.path.join(root, f); h.update(os.path.relpath(p, HERE).replace(os.sep, "/").encode())
                with open(p, "rb") as fh: h.update(fh.read())
    for sub in ("fonts", "icons", "logos"):
        d = os.path.join(REPO, "assets", sub)
        for root, dirs, files in os.walk(d):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(root, f); h.update(f"{os.path.relpath(p, REPO)}:{os.path.getsize(p)}".encode())
    return h.hexdigest()


def _listing(*dirs):
    out = []
    for d in dirs:
        for root, sub, files in os.walk(d):
            sub.sort()
            for f in sorted(files):
                p = os.path.join(root, f)
                try: st = os.stat(p)
                except OSError: continue
                out.append([os.path.relpath(p, d), st.st_size, st.st_mtime_ns])
    return out


def _user_dirs():
    """template / motion-piece folders outside the repo and the project (they are code too)"""
    d = [os.path.expanduser("~/.cves/templates"), os.path.expanduser("~/.cves/motion")]
    for k in ("CVES_TEMPLATES", "CVES_MOTION"):
        if os.environ.get(k): d.append(os.environ[k])
    return [x for x in d if os.path.isdir(x)]


def _fsig(p):
    try: st = os.stat(p); return [st.st_size, st.st_mtime_ns]
    except OSError: return None


def style_hash(S):
    return _h({k: v for k, v in dict(S).items() if k not in NON_VISUAL})


def enabled(S):
    v = S.get("render.cache", True)
    return v is True or str(v).strip().lower() in ("true", "on", "yes", "1")


def frame_keys(TL, mode="final"):
    """one hex key per frame 0..TL.N-1 (see the module doc)"""
    from . import render as R, craft as CR
    pr, E = TL.pr, TL.E
    try: behind = CR.behind_size(TL)
    except Exception: behind = "?"                   # noqa: BLE001  (a template error surfaces in the render itself)
    glob_ = {"v": VERSION, "code": code_hash(), "style": style_hash(TL.S), "mode": mode, "size": list(TL.size), "proxy": TL.proxy,
             "fps": TL.FPS, "N": TL.N, "A": TL.A_FRAMES, "end": [TL.T_END, TL.END, E.get("end_card")], "cap": TL.cap_cfg if hasattr(TL, "cap_cfg") else None,
             "roto": E.get("roto"), "behind": behind, "snap": TL.snap, "creep": TL.creep, "lift": sorted(TL.lift), "spine": TL.spine,
             "broll": E.get("broll"), "assets": E.get("assets"), "assets_json": _fsig(pr.e("assets.json")),
             "media": _listing(pr.p("Raw"), pr.p("Assets"), pr.p("Brand"), pr.e("conform")),
             "user": _listing(*_user_dirs())}
    gh = _h(glob_)
    seg_h = {}
    for s in TL.segs:
        sid = s["id"]
        seg_h[sid] = _h({"seg": {k: s.get(k) for k in ("id", "in", "out", "src", "f0", "n", "kind", "clip")},
                         "plate": _fsig(pr.e("plate", f"{sid}.mkv")), "matte": _fsig(pr.e("matte", f"{sid}.mkv")),
                         "faces": (TL.faces or {}).get(sid), "zoom": TL.zoom.get(sid), "match": (TL.match or {}).get(sid),
                         "gain": (TL.gain or {}).get(sid), "roto": TL.roto.get(sid), "chest": TL.chest.get(sid),
                         "matte_ok": TL.matte_ok.get(sid), "lift": sid in TL.lift})
    def by_frame(spans):
        """{frame: [span]} for spans (a, b, ...) with a <= frame / fps < b (the test compose uses), in span order"""
        out = {}
        for sp in spans:
            for i in range(max(0, int(math.floor(sp[0] * TL.FPS)) - 1), min(TL.N, int(math.ceil(sp[1] * TL.FPS)) + 1)):
                if sp[0] <= i / TL.FPS < sp[1]: out.setdefault(i, []).append(sp)
        return out
    caps = by_frame(getattr(TL, "caps", []) or []); hide = by_frame(getattr(TL, "cap_hide", []) or [])
    segs = sorted(TL.segs, key=lambda s: s["f0"]); j = 0
    keys = []
    for i in range(TL.N):
        t = i / TL.FPS; c = TL.in_cut(t)
        while j < len(segs) and i >= segs[j]["f0"] + segs[j]["n"]: j += 1
        s = segs[j] if j < len(segs) and segs[j]["f0"] <= i else None
        uses_seg = s is not None and (c is None or c.get("template") in R.NEEDS_AROLL or mode == "aroll" or s.get("kind") in ("broll", "gap"))
        kind, e, after = R.trans_strength(TL, t)
        tr = [kind, round(e, 9), after, round(CR.boundary(TL, t), 6)] if kind else None
        keys.append(_h([gh, i, seg_h.get(s["id"]) if uses_seg else None, c, tr, caps.get(i, []), hide.get(i, [])])[:32])
    return keys


def _log_sha(path):
    if not os.path.exists(path): return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load(out_dir, log_path):
    """{frame: key} of the frames whose PNG and element records are known good, else {}"""
    p = os.path.join(out_dir, INDEX)
    try:
        with open(p, encoding="utf-8") as fh: d = json.load(fh)
    except (OSError, ValueError): return {}
    if d.get("v") != VERSION or d.get("log_sha") != _log_sha(log_path): return {}
    have = set(os.listdir(out_dir))
    return {int(f): k for f, k in (d.get("keys") or {}).items() if f"{int(f):05d}.png" in have}


def save(out_dir, keys, log_path):
    """write the index for {frame: key} (atomic). keys=None removes it."""
    p = os.path.join(out_dir, INDEX)
    if keys is None:
        if os.path.exists(p): os.remove(p)
        return
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"v": VERSION, "log_sha": _log_sha(log_path), "keys": {str(f): k for f, k in sorted(keys.items())}}, fh)
    os.replace(tmp, p)


def drop(out_dir, frames):
    """forget frames (an `--only` render rewrote their PNGs but not the element log)"""
    p = os.path.join(out_dir, INDEX)
    try:
        with open(p, encoding="utf-8") as fh: d = json.load(fh)
    except (OSError, ValueError): return
    ks = d.get("keys") or {}
    for f in frames: ks.pop(str(int(f)), None)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh: json.dump(d, fh)
    os.replace(tmp, p)


def old_records(log_path, frames):
    """{frame: [json lines]} from the existing element log, for the frames kept"""
    out = {f: [] for f in frames}
    if not frames or not os.path.exists(log_path): return out
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            j = line.find('"f": ')
            if j < 0: continue
            k = j + 5; e = k
            while e < len(line) and line[e].isdigit(): e += 1
            f = int(line[k:e])
            if f in out: out[f].append(line if line.endswith("\n") else line + "\n")
    return out
