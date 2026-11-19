"""SFX bank: a manifest-driven library of sound effects, chosen by category and intensity instead of by filename.

Banks (later wins on the same id):
  1. the repo's   assets/sfx/manifest.yaml      CC0 only, every file in assets/sfx/CREDITS.md (source URL + licence);
  2. the user's   ~/.cves/sfx/manifest.yaml     (`$CVES_SFX` overrides the folder) grown with `cves sfx fetch` / `add`;
  3. the project's Music/sfx/manifest.yaml.

A manifest is `{version: 1, sounds: [{id, file, category, intensity, duration_s, peak_db, loudness_lufs, peak_at_s,
licence, source, title, creator}]}` (peak_at_s: where the 10 ms RMS envelope peaks; a riser that resolves peaks at its end). Categories: whoosh, impact, riser, ui, pop, transition, ambience. Intensity: soft | medium |
hard. A cue name `@impact` / `@riser:soft` (template cues, edit.yaml sfx.extra, the auto accents in cves.sound) is
resolved to a manifest id by `pick()`, deterministically; ids carry their category word (riser_air, impact_sub), so the
SND gates that judge whooshes / risers by name keep working.

CLI (`cves sfx ...`):
    cves sfx list [--category impact] [--json]
    cves sfx fetch "<query>" --category whoosh [--n 3] [--to user|project|DIR] [--intensity medium] [--max-s 6]
    cves sfx add FILE --category impact [--intensity hard] [--id impact_door] [--source URL] [--licence cc0|own] [--to user|project|DIR]

`fetch` searches Openverse (Freesound's CC0 recordings) and, when FREESOUND_API_KEY is set, the Freesound API, keeps
CC0 only, downloads into a fresh temp folder, converts with ffmpeg to 48 kHz mono WAV (downloads are treated as
untrusted data: only ever decoded as audio, never run), and records each file's source URL and licence in the bank's
manifest and CREDITS.md."""
import os, re, json, shutil, subprocess, tempfile, datetime, urllib.parse, urllib.request
import numpy as np

CATEGORIES = ("whoosh", "impact", "riser", "ui", "pop", "transition", "ambience")
INTENSITY = {"soft": 1, "medium": 2, "hard": 3}
LICENCES = ("CC0 1.0", "CC0, synthesized by CVES", "own recording")
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO_BANK = os.path.join(REPO, "assets", "sfx")
SR = 48000
MAX_DOWNLOAD = 25 * 1024 * 1024
FREESOUND = "https://freesound.org/apiv2/search/text/"


# ------------------------------------------------------------------ banks
def user_bank():
    return os.environ.get("CVES_SFX") or os.path.join(os.path.expanduser("~"), ".cves", "sfx")

def bank_dirs(pr=None):
    """[(label, dir)] in precedence order, lowest first"""
    out = [("repo", REPO_BANK), ("user", user_bank())]
    if pr is not None: out.append(("project", pr.p("Music", "sfx")))
    return out

def read_manifest(d):
    p = os.path.join(d, "manifest.yaml")
    if not os.path.exists(p): return {"version": 1, "sounds": []}
    import yaml
    with open(p, encoding="utf-8") as f: m = yaml.safe_load(f) or {}
    m.setdefault("version", 1); m.setdefault("sounds", [])
    return m

def write_manifest(d, m):
    import yaml
    os.makedirs(d, exist_ok=True)
    m = {"version": 1, "sounds": sorted(m.get("sounds") or [], key=lambda s: (CATEGORIES.index(s["category"]) if s.get("category") in CATEGORIES else 99, s["id"]))}
    head = ("# SFX bank manifest (cves.sfx; docs/SOUND.md). One entry per file: id, file, category, intensity, measured duration,\n"
            "# peak and loudness, licence and source. `cves sfx add` / `cves sfx fetch` write it; CREDITS.md lists the same sources.\n")
    with open(os.path.join(d, "manifest.yaml"), "w", encoding="utf-8") as f:
        f.write(head); yaml.safe_dump(m, f, sort_keys=False, allow_unicode=True, width=160)

def entries(pr=None):
    """every sound of every bank, later banks overriding earlier ones by id: [{..., path, bank}]"""
    seen = {}
    for label, d in bank_dirs(pr):
        for s in read_manifest(d)["sounds"]:
            p = os.path.join(d, s.get("file", ""))
            if os.path.exists(p): seen[s["id"]] = dict(s, path=p, bank=label)
    return list(seen.values())

def validate(d):
    """problems with one bank's manifest (empty list = valid)"""
    m = read_manifest(d); bad = []; ids = set()
    for k, s in enumerate(m["sounds"]):
        w = f"sounds[{k}] {s.get('id', '?')}"
        for key in ("id", "file", "category", "intensity", "duration_s", "peak_db", "licence", "source"):
            if s.get(key) in (None, ""): bad.append(f"{w}: {key} missing")
        if s.get("id") in ids: bad.append(f"{w}: duplicate id")
        ids.add(s.get("id"))
        if s.get("category") not in CATEGORIES: bad.append(f"{w}: category {s.get('category')!r} not one of {', '.join(CATEGORIES)}")
        if s.get("intensity") not in INTENSITY: bad.append(f"{w}: intensity {s.get('intensity')!r} not one of {', '.join(INTENSITY)}")
        if s.get("licence") not in LICENCES: bad.append(f"{w}: licence {s.get('licence')!r} (CC0 only: {', '.join(LICENCES)})")
        p = os.path.join(d, s.get("file") or "")
        if not os.path.isfile(p): bad.append(f"{w}: file {s.get('file')} missing"); continue
        if s.get("duration_s") is not None:
            got = measure(p)["duration_s"]
            if abs(got - float(s["duration_s"])) > .05: bad.append(f"{w}: duration {s['duration_s']} s in the manifest, {got} s measured")
    return bad


# ------------------------------------------------------------------ measuring
def _load(path):
    import librosa
    y, _ = librosa.load(path, sr=SR, mono=True); return y

def measure(path):
    """{duration_s, peak_db, loudness_lufs (BS.1770 integrated; null under 0.4 s), peak_at_s (10 ms RMS argmax)}"""
    from .qc.extra import bs1770
    y = _load(path); dur = len(y) / SR
    pk = float(np.abs(y).max()) if len(y) else 0.0
    l = bs1770(y, SR) if dur >= .4 else float("nan")
    env = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")) if len(y) else np.zeros(1)
    return {"duration_s": round(float(dur), 3), "peak_db": round(float(20 * np.log10(pk + 1e-12)), 1),
            "loudness_lufs": None if np.isnan(l) else round(float(l), 1), "peak_at_s": round(float(np.argmax(env)) / SR, 3)}


# ------------------------------------------------------------------ choosing
def parse_name(name):
    """'@impact:hard' -> ('impact', 'hard'); a plain file name -> (None, None)"""
    if not isinstance(name, str) or not name.startswith("@"): return None, None
    cat, _, inten = name[1:].partition(":")
    return cat.strip().lower(), (inten.strip().lower() or None)

def pick(cands, category, intensity=None, exclude=(), max_s=None, min_s=None, salt=0):
    """the best manifest entry for a category (+ intensity): closest intensity, then not in `exclude`, then the
    duration bounds; ties broken by id with a deterministic rotation (`salt`) so repeated picks vary. None if none."""
    pool = [s for s in cands if s.get("category") == category]
    if not pool: return None
    want = INTENSITY.get(intensity or "medium", 2)
    def fits(s):
        d = float(s.get("duration_s") or 0)
        return (max_s is None or d <= max_s + 1e-6) and (min_s is None or d >= min_s - 1e-6)
    ok = [s for s in pool if fits(s)] or pool
    ex = set(exclude); ok2 = [s for s in ok if s["id"] not in ex] or ok
    best = min(abs(INTENSITY.get(s.get("intensity"), 2) - want) for s in ok2)
    top = sorted((s for s in ok2 if abs(INTENSITY.get(s.get("intensity"), 2) - want) == best), key=lambda s: s["id"])
    return top[salt % len(top)]

def resolve_cues(cues, cands):
    """replace @category[:intensity] cue names by manifest ids (never the same id twice in a row per category)"""
    last = {}; out = []
    for t, name, gain, kw in cues:
        cat, inten = parse_name(name)
        if cat:
            s = pick(cands, cat, inten, exclude=[last.get(cat)] if last.get(cat) else ())
            if s is None: raise SystemExit(f"sfx '{name}': no {cat} sound in any bank (cves sfx list; cves sfx fetch \"{cat}\" --category {cat})")
            last[cat] = s["id"]; name = s["id"]
        out.append((t, name, gain, kw))
    return out


# ------------------------------------------------------------------ adding / fetching
def _slug(s, n=32):
    return (re.sub(r"[^A-Za-z0-9]+", "_", str(s)).strip("_").lower() or "sound")[:n]

def _dest_dir(to, pr=None):
    if to in (None, "", "user"): return user_bank()
    if to == "project":
        if pr is None: raise SystemExit("--to project needs a project (--project or run inside one)")
        return pr.p("Music", "sfx")
    if to == "repo": return REPO_BANK
    return os.path.abspath(to)

def _ffmpeg():
    from . import config as C
    return C.get("ffmpeg")

def convert(src, dst, max_s=30.0):
    """any audio file -> 48 kHz mono 16-bit WAV with ffmpeg (audio stream only, at most max_s). The input is untrusted
    data: it is only decoded, never run; a file ffmpeg cannot decode as audio is refused."""
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    r = subprocess.run([_ffmpeg(), "-v", "error", "-nostdin", "-y", "-i", src, "-map", "0:a:0", "-vn", "-sn", "-dn", "-t", str(max_s),
                        "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", dst], capture_output=True, text=True)
    if r.returncode or not os.path.exists(dst) or os.path.getsize(dst) < 1000:
        if os.path.exists(dst): os.remove(dst)
        raise SystemExit(f"not a readable audio file: {os.path.basename(src)} ({(r.stderr or '').strip()[:160]})")
    return dst

def _credit(d, s):
    p = os.path.join(d, "CREDITS.md")
    existing = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    if f"| {s['file']} |" in existing: return p
    with open(p, "a", encoding="utf-8") as f:
        if not existing:
            f.write("# Sound effects credits\nEvery file in this folder, its licence and where it came from (CC0 only). Written by `cves sfx`.\n\n"
                    "| File | Title | Licence | Source |\n|---|---|---|---|\n")
        f.write(f"| {s['file']} | {s.get('title', s['id'])} | {s['licence']} | {s['source']} |\n")
    return p

def add(path, category, intensity="medium", sid=None, source=None, licence="cc0", title=None, creator=None, to="user", pr=None, max_s=30.0):
    """copy (converted to WAV) one file into a bank, measure it, and record it in the manifest + CREDITS.md"""
    if category not in CATEGORIES: raise SystemExit(f"--category must be one of {', '.join(CATEGORIES)}")
    if intensity not in INTENSITY: raise SystemExit(f"--intensity must be one of {', '.join(INTENSITY)}")
    lic = {"cc0": "CC0 1.0", "own": "own recording"}.get(str(licence).lower())
    if lic is None: raise SystemExit("CVES banks hold CC0 sounds only (--licence cc0), or your own recordings (--licence own)")
    if not os.path.isfile(path): raise SystemExit(f"no such file: {path}")
    if lic == "CC0 1.0" and not source: raise SystemExit("--source URL is required for a CC0 file (where it came from, for CREDITS.md)")
    d = _dest_dir(to, pr); sid = _slug(sid or f"{category}_{os.path.splitext(os.path.basename(path))[0]}", 48)
    if not sid.startswith(category): sid = f"{category}_{sid}"
    m = read_manifest(d)
    if any(s["id"] == sid for s in m["sounds"]): raise SystemExit(f"{sid} is already in {d}/manifest.yaml (pass --id)")
    dst = os.path.join(d, sid + ".wav"); convert(path, dst, max_s)
    s = {"id": sid, "file": sid + ".wav", "category": category, "intensity": intensity, **measure(dst),
         "licence": lic, "source": source or ("own recording" if lic == "own recording" else "unknown"), "title": title or sid}
    if creator: s["creator"] = creator
    m["sounds"].append(s); write_manifest(d, m); _credit(d, s)
    return s

def _http_json(url, params=None, headers=None):
    from . import music as MU
    if params: url += ("&" if "?" in url else "?") + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": MU.UA, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def _download(url, dst):
    """stream one file to dst (at most MAX_DOWNLOAD bytes)"""
    from . import music as MU
    if not url.startswith("https://"): raise SystemExit(f"refusing a non-https download: {url[:80]}")
    req = urllib.request.Request(url, headers={"User-Agent": MU.UA}); n = 0
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
        while True:
            b = r.read(1 << 16)
            if not b: break
            n += len(b)
            if n > MAX_DOWNLOAD: raise SystemExit(f"download over {MAX_DOWNLOAD >> 20} MB refused: {url[:80]}")
            f.write(b)
    return dst

def search_openverse(query, max_s=None, limit=10):
    """CC0 sound effects on Openverse (Freesound's recordings): [{title, creator, licence, source, url, duration_s, provider}]"""
    from . import music as MU
    out = []
    for r in MU.search(query, kind="sfx", max_s=max_s, license="cc0", limit=limit):
        if r.get("license") != "cc0" or not r.get("url"): continue
        out.append({"title": r["title"], "creator": r["creator"], "licence": "CC0 1.0", "source": r.get("landing_url") or r["openverse_url"],
                    "url": r["url"], "duration_s": r.get("duration_s"), "provider": "openverse", "key": f"openverse:{r['id']}"})
    return out

def search_freesound(query, key, max_s=None, limit=10):
    """CC0 results from the Freesound API (FREESOUND_API_KEY): previews download without OAuth"""
    flt = 'license:"Creative Commons 0"' + (f" duration:[0 TO {float(max_s):g}]" if max_s else "")
    d = _http_json(FREESOUND, {"query": query, "filter": flt, "fields": "id,name,username,license,previews,url,duration", "page_size": limit},
                   headers={"Authorization": f"Token {key}"})
    out = []
    for r in d.get("results") or []:
        if "publicdomain/zero" not in str(r.get("license", "")): continue          # CC0 only, whatever the filter returned
        url = (r.get("previews") or {}).get("preview-hq-mp3")
        if not url: continue
        out.append({"title": r.get("name") or str(r["id"]), "creator": r.get("username") or "unknown", "licence": "CC0 1.0",
                    "source": r.get("url") or f"https://freesound.org/s/{r['id']}/", "url": url, "duration_s": r.get("duration"),
                    "provider": "freesound", "key": f"freesound:{r['id']}"})
    return out

def fetch(query, category, n=3, to="user", intensity="medium", pr=None, max_s=6.0, freesound_key=None):
    """search (Openverse, + Freesound with a key), keep CC0, download -> convert -> measure -> manifest + CREDITS.
    Returns the added entries."""
    if category not in CATEGORIES: raise SystemExit(f"--category must be one of {', '.join(CATEGORIES)}")
    key = freesound_key if freesound_key is not None else os.environ.get("FREESOUND_API_KEY")
    res = search_openverse(query, max_s=max_s, limit=max(10, n * 3))
    if key: res += search_freesound(query, key, max_s=max_s, limit=max(10, n * 3))
    d = _dest_dir(to, pr); have = {s.get("source") for s in read_manifest(d)["sounds"]}; added = []
    for r in res:
        if len(added) >= n: break
        if r["licence"] != "CC0 1.0" or r["source"] in have: continue
        tmp = tempfile.mkdtemp(prefix="cves_sfx_dl_")         # untrusted download: its own empty folder, decoded as audio only
        try:
            raw = _download(r["url"], os.path.join(tmp, "download.bin"))
            ttl = re.sub(rf"^{category}[\s_-]*", "", _slug(r["title"]), flags=re.I) or "sound"
            sid = _slug(f"{category}_{ttl}", 40) + "_" + _slug(r["key"].split(":")[-1], 8)
            s = add(raw, category, intensity, sid=sid, source=r["source"], licence="cc0", title=r["title"], creator=r["creator"], to=to, pr=pr, max_s=max(max_s or 0, 1) + 1)
            s["provider"] = r["provider"]; added.append(s); have.add(r["source"])
        except SystemExit as e:
            print(f"skipped {r['title']!r}: {e}")
        finally: shutil.rmtree(tmp, ignore_errors=True)
    return added


# ------------------------------------------------------------------ CLI
def main(argv, project=None):
    import argparse
    from .project import Project
    ap = argparse.ArgumentParser(prog="cves sfx", description="the SFX bank: list | fetch (CC0, Openverse / Freesound) | add (docs/SOUND.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list"); l.add_argument("--category", choices=CATEGORIES); l.add_argument("--json", action="store_true")
    f = sub.add_parser("fetch"); f.add_argument("query"); f.add_argument("--category", choices=CATEGORIES, required=True)
    f.add_argument("--n", type=int, default=3); f.add_argument("--to", default="user", help="user (~/.cves/sfx, default) | project (Music/sfx) | a folder")
    f.add_argument("--intensity", choices=list(INTENSITY), default="medium"); f.add_argument("--max-s", type=float, default=6.0)
    a_ = sub.add_parser("add"); a_.add_argument("file"); a_.add_argument("--category", choices=CATEGORIES, required=True)
    a_.add_argument("--intensity", choices=list(INTENSITY), default="medium"); a_.add_argument("--id"); a_.add_argument("--source")
    a_.add_argument("--licence", "--license", default="cc0", help="cc0 (needs --source) | own"); a_.add_argument("--title")
    a_.add_argument("--to", default="user", help="user (default) | project | a folder")
    v = sub.add_parser("check", help="validate every bank's manifest")
    a = ap.parse_args(argv)
    pr = None
    root = project or os.getcwd()
    if os.path.isdir(os.path.join(root, "Edit")): pr = Project(root)
    if a.cmd == "list":
        es = sorted((s for s in entries(pr) if not a.category or s["category"] == a.category), key=lambda s: (s["category"], s["id"]))
        if a.json: print(json.dumps(es, indent=1)); return 0
        for s in es:
            print(f"{s['category']:10s} {s['intensity']:6s} {s['id']:28s} {float(s['duration_s']):5.2f} s  {s['peak_db']:6.1f} dB  {s['bank']:7s} {s['licence']}")
        print(f"{len(es)} sound(s); cue them by id or as @category[:soft|medium|hard]")
        return 0
    if a.cmd == "check":
        bad = []
        for label, d in bank_dirs(pr): bad += [f"{label}: {b}" for b in validate(d)]
        print("\n".join(bad) or "all SFX manifests valid"); return 1 if bad else 0
    if a.cmd == "fetch":
        got = fetch(a.query, a.category, a.n, a.to, a.intensity, pr, a.max_s)
        for s in got: print(f"added {s['id']} ({s['duration_s']} s, {s['licence']}) from {s['source']}")
        if not got: print("nothing added (no CC0 result, or every result is already in the bank)")
        return 0 if got else 1
    if a.cmd == "add":
        s = add(a.file, a.category, a.intensity, a.id, a.source, a.licence, a.title, to=a.to, pr=pr)
        print(f"added {s['id']} -> {_dest_dir(a.to, pr)}"); return 0
    return 0
