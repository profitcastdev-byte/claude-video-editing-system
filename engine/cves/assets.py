"""Media assets: the `assets:` block in edit.yaml + the provenance registry in Edit/assets.json (docs/MEDIA.md).

edit.yaml declares what an edit needs, by id:
    assets:
      hero_img: {path: Assets/hero.jpg}                       # a file the client supplied
      city_broll: {url: "https://...", licence: "Pexels"}     # to be downloaded by Claude
      office_shot: {generate: {provider: magnific, kind: image, prompt: "...", aspect: "9:16"}}
Templates refer to an asset by id (`params.asset: hero_img`). `cves assets add` copies a file into PROJECT/Assets/ and
records its provenance (sha256, source, prompt, model, licence, probe). `cves assets check` fails on a missing, changed or
unlicensed asset; `cves assets todo` lists the assets still to generate as ready-to-run instructions for Claude.
The engine never calls a generation API itself: Claude generates through its MCP connectors, then registers the file."""
import os, sys, json, shutil, hashlib, argparse, datetime, subprocess

REG = "assets.json"
EXT = {"image": (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"),
       "video": (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mxf"),
       "audio": (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aif", ".aiff"),
       "font": (".ttf", ".otf", ".woff", ".woff2")}
SOURCES = ("file", "stock", "magnific", "elevenlabs", "url", "client", "screen", "render")
# what Claude should call for each provider (docs/MEDIA.md, plugin/skills/video-editor/connectors.md)
PROVIDER_TOOLS = {
    ("magnific", "image"): "Magnific/Freepik images_generate (then images_upscale if smaller than the canvas)",
    ("magnific", "video"): "Magnific/Freepik video_generate (image-to-video: generate the still first)",
    ("magnific", "rgba"): "Magnific/Freepik images_generate + images_remove_background (PNG with alpha)",
    ("magnific", "upscale"): "Magnific/Freepik images_upscale on the registered source asset",
    ("magnific", "cutout"): "Magnific/Freepik images_remove_background on the registered source asset",
    ("freepik", "image"): "Magnific/Freepik images_generate",
    ("elevenlabs", "audio"): "ElevenLabs audio_tts (voiceover) / audio_sfx_generate (SFX) / audio_music_generate (music)",
    ("elevenlabs", "voice"): "ElevenLabs audio_tts", ("elevenlabs", "sfx"): "ElevenLabs audio_sfx_generate",
    ("elevenlabs", "music"): "ElevenLabs audio_music_generate",
    ("stock", "image"): "Magnific/Freepik stock_search + stock_download (check the licence field)",
    ("stock", "video"): "Magnific/Freepik stock_search (type video) + stock_download, or a search_footage connector",
}
KIND_EXT = {"image": ".png", "rgba": ".mov", "video": ".mp4", "audio": ".wav", "voice": ".mp3", "sfx": ".mp3", "music": ".mp3",
            "upscale": ".png", "cutout": ".png", "font": ".ttf"}


# ------------------------------------------------------------------ registry
def _reg_path(pr): return pr.e(REG)

_CACHE = {}
def registry(pr):
    """Edit/assets.json -> {id: record}; cached per process by mtime"""
    p = _reg_path(pr)
    if not os.path.exists(p): return {}
    m = os.path.getmtime(p)
    if _CACHE.get(p, (None,))[0] != m:
        with open(p, encoding="utf-8") as f: _CACHE[p] = (m, (json.load(f) or {}).get("assets", {}))
    return _CACHE[p][1]

def _save(pr, reg):
    with open(_reg_path(pr), "w", encoding="utf-8") as f: json.dump({"assets": reg}, f, indent=1, ensure_ascii=False)
    _CACHE.pop(_reg_path(pr), None)

def declared(pr):
    """edit.yaml `assets:` block -> {id: spec}"""
    a = pr.edit.get("assets") or {}
    if not isinstance(a, dict): raise SystemExit("edit.yaml `assets:` must be a mapping {id: {path | url | generate}}")
    return {str(k): (v if isinstance(v, dict) else {"path": v}) for k, v in a.items()}

def referenced(pr):
    """every asset id the edit uses: any `asset:` key (or `assets:` list) inside cutaways/roto/chest/end_card params, the
    broll: track and voiceover:"""
    E = pr.edit; out = []
    def walk(x, where):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "asset" and isinstance(v, str): out.append((v, where))
                elif k == "assets" and isinstance(v, list): out.extend((s, where) for s in v if isinstance(s, str))
                else: walk(v, where)
        elif isinstance(x, list):
            for v in x: walk(v, where)
    for sec in ("cutaways", "roto", "chest"):
        for c in E.get(sec) or []: walk(c.get("params") or {}, f"{sec}:{c.get('id') or c.get('segment')}")
    if E.get("end_card"): walk(E["end_card"].get("params") or {}, "end_card")
    for j, x in enumerate(E.get("broll") or []):               # the broll: track (docs/FORMATS.md); `src:` is footage, not an asset
        if isinstance(x, dict) and isinstance(x.get("asset"), str): out.append((x["asset"], f"broll[{j}]"))
    vo = E.get("voiceover") or {}
    if isinstance(vo, dict) and isinstance(vo.get("asset"), str): out.append((vo["asset"], "voiceover"))
    return out


# ------------------------------------------------------------------ probe
def sha256(path):
    h = hashlib.sha256()
    files = sorted(os.path.join(path, f) for f in os.listdir(path)) if os.path.isdir(path) else [path]
    for fp in files:
        if os.path.isdir(fp): continue
        if os.path.isdir(path): h.update(os.path.basename(fp).encode("utf-8"))
        with open(fp, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def _seq_files(d): return sorted(f for f in os.listdir(d) if f.lower().endswith((".png", ".tif", ".tiff", ".exr", ".webp")))

def kind_of(path, probe=None):
    if os.path.isdir(path): return "rgba" if (probe or {}).get("has_alpha") else "video"
    e = os.path.splitext(path)[1].lower()
    for k, exts in EXT.items():
        if e in exts:
            if k == "video" and (probe or {}).get("has_alpha"): return "rgba"
            return k
    return "file"

def _ffprobe(path):
    from . import config as C
    r = subprocess.run([C.get("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True)
    if r.returncode: raise SystemExit(f"ffprobe could not read {path}: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout)

def _rate(s):
    try:
        n, d = (s or "0/1").split("/"); return round(int(n) / int(d), 6) if int(d) else None
    except Exception: return None

def probe(path):
    """{w, h, duration, fps, has_alpha, frames?, audio?}; None for fields that do not apply"""
    out = {"w": None, "h": None, "duration": None, "fps": None, "has_alpha": False}
    from PIL import Image
    if os.path.isdir(path):                                   # image sequence (e.g. a Remotion / AE PNG export)
        fs = _seq_files(path)
        if not fs: raise SystemExit(f"{path}: folder has no .png/.tif frames")
        with Image.open(os.path.join(path, fs[0])) as im:
            out.update(w=im.width, h=im.height, has_alpha=("A" in im.getbands()) or "transparency" in im.info)
        out["frames"] = len(fs); return out
    e = os.path.splitext(path)[1].lower()
    if e in EXT["image"]:
        with Image.open(path) as im:
            out.update(w=im.width, h=im.height, has_alpha=("A" in im.getbands()) or "transparency" in im.info)
        return out
    if e in EXT["font"]: return out
    j = _ffprobe(path); fmt = j.get("format") or {}
    try: out["duration"] = round(float(fmt.get("duration")), 4)
    except (TypeError, ValueError): pass
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and out["w"] is None:
            pf = s.get("pix_fmt") or ""
            out.update(w=s.get("width"), h=s.get("height"), fps=_rate(s.get("avg_frame_rate")) or _rate(s.get("r_frame_rate")), pix_fmt=pf,
                       has_alpha=pf.startswith(("yuva", "rgba", "bgra", "argb", "abgr", "gbrap", "ya", "pal8")) or (s.get("tags") or {}).get("alpha_mode") == "1")
            rot = int(((s.get("side_data_list") or [{}])[0] or {}).get("rotation", 0) or (s.get("tags") or {}).get("rotate", 0) or 0)
            if rot % 180: out["w"], out["h"] = out["h"], out["w"]
        if s.get("codec_type") == "audio" and "audio" not in out:
            out["audio"] = {"sr": int(s.get("sample_rate") or 0), "channels": s.get("channels")}
    return out


# ------------------------------------------------------------------ resolve (used by Timeline.resolve and the media templates)
def resolve(pr, ref, strict=True):
    """asset id -> absolute path. Returns None if `ref` is not an asset id (callers then treat it as a path).
    strict: raise SystemExit (one actionable line) for a declared asset that has no file yet."""
    if not isinstance(ref, str) or not ref: return None
    reg = registry(pr)
    if ref in reg:
        p = pr.p(reg[ref]["path"])
        if os.path.exists(p): return p
        if strict: raise SystemExit(f"asset '{ref}': file missing ({reg[ref]['path']}); re-add it with `cves assets add --id {ref} --file ...`")
        return None
    dec = declared(pr).get(ref)
    if dec is None: return None
    if dec.get("path"):
        p = dec["path"] if os.path.isabs(dec["path"]) else pr.p(dec["path"])
        if os.path.exists(p): return p
        if strict: raise SystemExit(f"asset '{ref}': {dec['path']} not found; put the file there or run `cves assets add --id {ref} --file ...`")
        return None
    if strict:
        how = "download it" if dec.get("url") else "generate it"
        raise SystemExit(f"asset '{ref}' has no file yet: {how}, then `cves assets add --id {ref} --file ...` (see `cves assets todo`)")
    return None

def record(pr, ref):
    """the registry record for an asset id (or None)"""
    return registry(pr).get(ref)


# ------------------------------------------------------------------ add / list / check / todo
def add(pr, aid, file, source="file", prompt=None, licence=None, url=None, model=None, notes=None, move=False):
    if not aid or any(c in aid for c in "/\\: "): raise SystemExit("--id must be a short name without spaces or slashes (e.g. hero_img)")
    src = os.path.abspath(os.path.expanduser(file))
    if not os.path.exists(src): raise SystemExit(f"--file not found: {file}")
    if source not in SOURCES: raise SystemExit(f"--source must be one of {', '.join(SOURCES)}")
    dec = declared(pr).get(aid, {}); gen = dec.get("generate") or {}
    licence = licence or dec.get("licence")
    adir = pr.p("Assets"); os.makedirs(adir, exist_ok=True)
    inside = os.path.commonpath([src, adir]) == adir
    if inside: dst = src
    else:
        base = os.path.basename(src.rstrip(os.sep))
        want = dec.get("path") and not os.path.isabs(dec["path"]) and pr.p(dec["path"])     # edit.yaml says where it lives
        dst = want or os.path.join(adir, base)
        if not want and os.path.exists(dst) and sha256(dst) != sha256(src): dst = os.path.join(adir, f"{aid}__{base}")
        if os.path.exists(dst) and sha256(dst) != sha256(src):
            if not want: raise SystemExit(f"{dst} exists with different content: pick another --id or remove it")
            (shutil.rmtree if os.path.isdir(dst) else os.remove)(dst)                       # re-adding a declared asset replaces it
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True) if not move else shutil.move(src, dst)
        else: (shutil.move if move else shutil.copy2)(src, dst)
    pb = probe(dst)
    rec = {"id": aid, "path": os.path.relpath(dst, pr.root), "kind": kind_of(dst, pb), "sha256": sha256(dst),
           "source": source, "prompt": prompt or gen.get("prompt"), "model": model or gen.get("model"),
           "provider": gen.get("provider"), "licence": licence, "url": url or dec.get("url"),
           "created": datetime.datetime.now().isoformat(timespec="seconds"), "probe": pb}
    if notes: rec["notes"] = notes
    reg = dict(registry(pr)); reg[aid] = rec; _save(pr, reg)
    return rec

def problems(pr):
    """[(asset_id, message)] for every asset edit.yaml declares or a template references"""
    reg, dec = registry(pr), declared(pr); out = []
    ids = list(dict.fromkeys(list(dec) + [a for a, _ in referenced(pr)]))
    where = {}
    for a, w in referenced(pr): where.setdefault(a, w)
    for aid in ids:
        r = reg.get(aid)
        if r is None:
            d = dec.get(aid)
            if d is None:
                if os.path.exists(pr.p(aid)): out.append((aid, f"used by {where.get(aid)} as a raw path: declare it under edit.yaml assets and `cves assets add` it"))
                else: out.append((aid, f"used by {where.get(aid)} but not declared in edit.yaml assets"))
            elif d.get("generate"): out.append((aid, "not generated yet (cves assets todo)"))
            elif d.get("url"): out.append((aid, f"not downloaded yet from {d['url']}"))
            else: out.append((aid, f"not registered: `cves assets add --id {aid} --file {d.get('path')} --source ... --licence ...`"))
            continue
        p = pr.p(r["path"])
        if not os.path.exists(p): out.append((aid, f"file missing: {r['path']}")); continue
        if sha256(p) != r.get("sha256"): out.append((aid, f"file changed since it was registered (sha256): re-run `cves assets add --id {aid}`"))
        if not r.get("source"): out.append((aid, "no source recorded"))
        if not r.get("licence"): out.append((aid, "no licence recorded (--licence: e.g. 'client-owned', 'Freepik Premium', 'CC0', 'ElevenLabs paid plan')"))
        if r.get("source") in ("magnific", "elevenlabs") and not r.get("prompt"): out.append((aid, f"generated by {r['source']} but no prompt recorded"))
        if aid in dec and dec[aid].get("path") and os.path.normpath(dec[aid]["path"]) != os.path.normpath(r["path"]):
            out.append((aid, f"edit.yaml path {dec[aid]['path']} differs from the registered file {r['path']}"))
    return out

def todo(pr):
    """ready-to-run instructions for every declared asset that has no registered file"""
    reg, out = registry(pr), []
    for aid, d in declared(pr).items():
        if aid in reg: continue
        g = d.get("generate")
        if g:
            prov = str(g.get("provider", "magnific")).lower(); kind = str(g.get("kind", "image")).lower()
            tool = PROVIDER_TOOLS.get((prov, kind)) or PROVIDER_TOOLS.get((prov, "image")) or f"{prov} connector"
            ext = KIND_EXT.get(kind, ".bin"); fn = f"Assets/{aid}{ext}"
            spec = ", ".join(f"{k}={g[k]}" for k in ("aspect", "duration", "voice", "model", "style", "source") if g.get(k) is not None)
            out.append("\n".join([f"[{aid}] generate {kind} via {prov}" + (f" ({spec})" if spec else ""),
                                  f"  1. ask the user: cost/credits for this {kind} (do not spend credits without a yes)",
                                  f"  2. call: {tool}", f"     prompt: {g.get('prompt', '(write one from the brief)')}",
                                  f"  3. download the result to: {fn}",
                                  f"  4. cves assets add --id {aid} --file \"{fn}\" --source {'stock' if prov == 'stock' else prov} "
                                  f"--prompt \"{(g.get('prompt') or '').replace(chr(34), chr(39))}\"" + (f" --model \"{g['model']}\"" if g.get("model") else "") +
                                  f" --licence \"{d.get('licence') or '<plan/terms>'}\""]))
        elif d.get("url"):
            out.append(f"[{aid}] download {d['url']} -> Assets/  then: cves assets add --id {aid} --file Assets/<file> --source url --url \"{d['url']}\" --licence \"{d.get('licence') or '<licence>'}\"")
        elif d.get("path"):
            out.append(f"[{aid}] register the supplied file: cves assets add --id {aid} --file \"{d['path']}\" --source file --licence \"{d.get('licence') or '<licence>'}\"")
        else:
            out.append(f"[{aid}] has no path, url or generate: add one in edit.yaml assets")
    for aid, w in referenced(pr):
        if aid not in reg and aid not in declared(pr) and not os.path.exists(pr.p(aid)):
            out.append(f"[{aid}] used by {w} but not declared: add it under edit.yaml assets")
    return out


# ------------------------------------------------------------------ CLI: cves assets add|list|check|todo|resolve
def main(argv, project=None):
    from .project import Project
    ap = argparse.ArgumentParser(prog="cves assets", description="media assets: registry + provenance (docs/MEDIA.md)")
    sp = ap.add_subparsers(dest="sub", required=True)
    def proj(p): p.add_argument("project_dir", nargs="?", help="project folder (default: --project or the current folder)")
    a = sp.add_parser("add", help="copy a file into PROJECT/Assets and record its provenance"); proj(a)
    a.add_argument("--id", required=True); a.add_argument("--file", required=True)
    a.add_argument("--source", default="file", choices=SOURCES); a.add_argument("--prompt"); a.add_argument("--licence", "--license", dest="licence")
    a.add_argument("--url"); a.add_argument("--model"); a.add_argument("--notes"); a.add_argument("--move", action="store_true", help="move instead of copy")
    for n in ("list", "check", "todo"): proj(sp.add_parser(n))
    r = sp.add_parser("resolve"); proj(r); r.add_argument("id")
    argv = list(argv)
    if "--project" in argv:                     # `cves assets todo --project P` as well as `cves --project P assets todo`
        k = argv.index("--project"); project = argv[k + 1] if k + 1 < len(argv) else None; del argv[k:k + 2]
    x = ap.parse_args(argv)
    pr = Project(x.project_dir or project or os.getcwd())
    if x.sub == "add":
        rec = add(pr, x.id, x.file, x.source, x.prompt, x.licence, x.url, x.model, x.notes, x.move)
        pb = rec["probe"]; dims = f"{pb['w']}x{pb['h']}" if pb.get("w") else ""
        print(f"{rec['id']}: {rec['kind']} {dims} {('%.2fs' % pb['duration']) if pb.get('duration') else ''} {'alpha' if pb.get('has_alpha') else ''} -> {rec['path']}".replace("  ", " "))
        if not rec.get("licence"): print("warning: no licence recorded; `cves assets check` will fail until you re-add with --licence", file=sys.stderr)
        return 0
    if x.sub == "list":
        reg = registry(pr); dec = declared(pr)
        for aid in sorted(set(reg) | set(dec)):
            r = reg.get(aid)
            if r:
                pb = r.get("probe") or {}
                print(f"{aid:18s} {r['kind']:6s} {str(pb.get('w') or ''):>5s}x{str(pb.get('h') or ''):<5s} {('%6.2fs' % pb['duration']) if pb.get('duration') else '       '} "
                      f"{r.get('source') or '?':10s} {r.get('licence') or 'NO LICENCE':24s} {r['path']}")
            else:
                d = dec[aid]; st = "TO GENERATE" if d.get("generate") else ("TO DOWNLOAD" if d.get("url") else "UNREGISTERED")
                print(f"{aid:18s} {st}")
        if not reg and not dec: print("no assets declared (edit.yaml assets:) or registered (Edit/assets.json)")
        return 0
    if x.sub == "check":
        p = problems(pr)
        for aid, m in p: print(f"FAIL {aid}: {m}")
        n = len(set(list(declared(pr)) + [a for a, _ in referenced(pr)]))
        print(f"{n} asset(s), {len(p)} problem(s)"); return 1 if p else 0
    if x.sub == "todo":
        t = todo(pr); print("\n\n".join(t) if t else "nothing to generate: every declared asset is registered"); return 0
    if x.sub == "resolve":
        p = resolve(pr, x.id); print(p if p else f"'{x.id}' is not an asset id"); return 0 if p else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
