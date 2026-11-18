"""CVES motion layer: senior-grade motion design as HTML/CSS compositions rendered by headless Chromium (Playwright)
to RGBA frames (docs/MOTION.md).

A *piece* is a folder with `piece.html` (markup + style + a script that calls `CVES.piece({setup, seek, cues})`) and
`meta.yaml` (title, kinds, params with types / defaults, preview params). The engine wraps it in a page with:
- our own runtime (`runtime.js`: easing, tween, stagger, word split, timeline, fake motion blur), no third-party JS;
- `base.css` (type scale, surfaces, word masks);
- the style profile as CSS variables (colours, fonts from assets/fonts, motion tokens, the safe zone).

Every frame comes from `window.__seek(t)` (t = seconds since the piece starts): nothing runs on the wall clock, so the
same t always gives the same pixels. Frames are rendered ONCE per (html, runtime, params, style subset, size, fps,
duration) and cached as PNGs under `PROJECT/Edit/motion/<hash>/`. `prerender(pr, TL)` renders every motion piece a
timeline uses before render's spawn pool starts, so workers only read PNGs; a worker that finds no cache renders on
demand (atomic directory rename: a race only wastes time, never corrupts).

Pieces are discovered in `engine/cves/motion/pieces/`, then `~/.cves/motion/`, then `PROJECT/Brand/motion/` (later
folders override earlier ones). Templates `m_<piece>` are registered by `cves.templates.motion`."""
import os, json, hashlib, shutil, tempfile, pathlib, atexit, copy
from functools import lru_cache
import yaml
from .. import gfx as G

HERE = pathlib.Path(__file__).resolve().parent
RUNTIME, BASE_CSS, BUILTIN = HERE / "runtime.js", HERE / "base.css", HERE / "pieces"
VERSION = 1                       # bump to invalidate every cached render when the page assembly changes
INSTALL_HINT = "run `python -m playwright install chromium` (in the CVES venv) to install the motion renderer's Chromium"
PIP_HINT = "pip install playwright==1.58.0 && python -m playwright install chromium"
DEFAULT_MOTION = {"ease": "expo", "energy": 0.5, "overshoot": 1.6, "blur_on_fast": True, "blur_max_u": 1.6, "exit_s": 0.32,
                  "entry_s": 0.28, "stagger_s": 0.12, "shutter": 0.5, "type_ratio": 1.25, "radius_u": 2.6,
                  "glass_alpha": 0.72, "safe": None, "safe_fallback": [0.06, 0.07, 0.94, 0.93], "hero_min_gap_s": 8.0}
PARAM_TYPES = {"str", "number", "int", "bool", "list", "dict", "time", "path", "color", "asset", "any"}
PATH_TYPES = ("path", "asset", "icon")      # icon: a name in assets/icons (svg) or a path


# ------------------------------------------------------------------ pieces
class Piece:
    """one motion piece folder: piece.html + meta.yaml"""
    def __init__(self, folder, origin="builtin"):
        self.dir = pathlib.Path(folder); self.origin = origin
        self.html_path = self.dir / "piece.html"
        meta = yaml.safe_load((self.dir / "meta.yaml").read_text(encoding="utf-8")) if (self.dir / "meta.yaml").exists() else {}
        self.meta = meta or {}
        base = self.dir.name
        self.name = self.meta.get("name") or (base if base.startswith("m_") else "m_" + base)
        self.kinds = list(self.meta.get("kinds") or ["cutaway", "overlay"])
        self.params = self.meta.get("params") or {}
        self.title = self.meta.get("title") or self.name
        self.description = " ".join(str(self.meta.get("description") or "").split())
        self.hero = bool(self.meta.get("hero", False))
        self.duration = float(self.meta.get("duration", 3.0))

    def defaults(self):
        return {k: copy.deepcopy(v.get("default")) for k, v in self.params.items() if isinstance(v, dict) and v.get("default") is not None}

    def schema_types(self):
        """{param: "type" / "type!"} for cves validate (schema.PARAMS)"""
        out = {}
        for k, v in self.params.items():
            v = v if isinstance(v, dict) else {"type": v}
            ty = str(v.get("type", "any")); ty = "str" if ty == "icon" else ty if ty in PARAM_TYPES else "any"
            out[k] = ty + ("!" if v.get("required") else "")
        out.setdefault("at", "time"); out.setdefault("duration", "number"); out.setdefault("exit", "bool")
        return out

    def source_hash(self):
        """hash of every text file in the piece folder (its html, css, js, meta)"""
        h = hashlib.sha256()
        for f in sorted(self.dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".html", ".css", ".js", ".yaml", ".yml", ".json", ".svg"):
                h.update(f.relative_to(self.dir).as_posix().encode()); h.update(f.read_bytes())
        return h.hexdigest()


def piece_dirs(project_root=None):
    """(folder, origin) in override order: built-in, ~/.cves/motion, $CVES_MOTION, PROJECT/Brand/motion"""
    out = [(BUILTIN, "builtin"), (pathlib.Path(os.path.expanduser("~/.cves/motion")), "user")]
    if os.environ.get("CVES_MOTION"): out.append((pathlib.Path(os.environ["CVES_MOTION"]), "env"))
    if project_root: out.append((pathlib.Path(project_root) / "Brand" / "motion", "project"))
    return out


def scan(folder, origin):
    """every piece folder (has piece.html) directly inside folder"""
    folder = pathlib.Path(folder); found = {}
    if not folder.is_dir(): return found
    for d in sorted(folder.iterdir()):
        if d.is_dir() and (d / "piece.html").exists() and not d.name.startswith((".", "_")):
            p = Piece(d, origin); found[p.name] = p
    return found


def discover(project_root=None):
    found = {}
    for d, origin in piece_dirs(project_root): found.update(scan(d, origin))
    return found


PIECES = {}                       # name -> Piece, filled by cves.templates.motion (and register_dir for project pieces)


# ------------------------------------------------------------------ style -> CSS variables
def _rgb(v, default):
    try: return G._rgb(v) if v not in (None, "") else default
    except Exception: return default


def palette(S):
    """every colour slot the pieces may use, from the style (derived tones as gfx.apply_style derives them)"""
    cols = (S.get("colors") if hasattr(S, "get") else None) or {}
    out = {k: _rgb(cols.get(k), getattr(G, name)) for k, name in G._COLOR_KEYS.items() if k not in ("muted", "surface", "line")}
    out["muted"] = _rgb(cols.get("muted"), None) or G.mix(out["text"], out["card"], .33)
    out["surface"] = _rgb(cols.get("surface"), None) or G.mix(out["card"], out["icon_well"], .5)
    out["line"] = _rgb(cols.get("line"), None) or G.mix(out["card_border"], out["accent_dark"], .45)
    stage = (S.get("stage") if hasattr(S, "get") else None) or {}
    out["bg"] = _rgb(stage.get("background"), G.STAGE["background"])
    return out


def motion_cfg(S):
    m = dict(DEFAULT_MOTION); m.update({k: v for k, v in ((S.get("motion") or {}) if hasattr(S, "get") else {}).items() if v is not None})
    return m


def _sget(S, path, default=None):
    cur = S
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur: return default
        cur = cur[k]
    return default if cur is None else cur


def safe_frac(S, size):
    """(x0, y0, x1, y1) fractions of the canvas kept free of platform UI. `motion.safe` wins; else the style's
    `platform.safe_zone` (px in the `platform.size` design space) when that space has the canvas's aspect; else
    `motion.safe_fallback`."""
    m = motion_cfg(S); w, h = size
    if m.get("safe"): return tuple(float(v) for v in m["safe"])
    z = _sget(S, "platform.safe_zone"); ds = _sget(S, "canvas.size") or _sget(S, "platform.size")
    if z and ds and abs(ds[0] / ds[1] - w / h) < .01:
        return (z[0] / ds[0], z[1] / ds[1], z[2] / ds[0], z[3] / ds[1])
    return tuple(float(v) for v in m["safe_fallback"])


_FONT_WEIGHTS = (("medium", "m", 500), ("semibold", "sb", 600), ("bold", "b", 700), ("extrabold", "xb", 800))
_SCRIPT_FONTS = [("Devanagari", "U+0900-097F, U+1CD0-1CFF, U+A8E0-A8FF"), ("Bengali", "U+0980-09FF"), ("Gujarati", "U+0A80-0AFF"),
                 ("Tamil", "U+0B80-0BFF"), ("Telugu", "U+0C00-0C7F"), ("Kannada", "U+0C80-0CFF"), ("Malayalam", "U+0D00-0D7F")]


def fonts(S):
    """{css weight: font file} for the sans family and the serif file, from the style's font_files"""
    ff = (S.get("font_files") if hasattr(S, "get") else None) or {}
    sans = {}
    for key, short, wt in _FONT_WEIGHTS:
        p = G._font_path(ff.get(key) or G.FONT_FILES.get(short))
        if os.path.exists(p): sans[wt] = os.path.abspath(p)
    serif = G._font_path(ff.get("serif") or G.FONT_FILES.get("serif"))
    return sans, (os.path.abspath(serif) if os.path.exists(serif) else None)


def _font_faces(S):
    sans, serif = fonts(S); css = []
    for wt, p in sorted(sans.items()):
        css.append(f"@font-face{{font-family:'CVES Sans';src:url('{pathlib.Path(p).as_uri()}');font-weight:{wt};font-style:normal;font-display:block}}")
    for script, rng in _SCRIPT_FONTS:          # non-Latin text falls through to the Noto files shipped in assets/fonts
        for wt, word in ((500, "Medium"), (600, "SemiBold"), (700, "Bold"), (800, "ExtraBold")):
            p = pathlib.Path(G.FONTS) / f"NotoSans{script}-{word}.ttf"
            if p.exists():
                css.append(f"@font-face{{font-family:'CVES Sans';src:url('{p.as_uri()}');font-weight:{wt};unicode-range:{rng};font-display:block}}")
    if serif:
        css.append(f"@font-face{{font-family:'CVES Serif';src:url('{pathlib.Path(serif).as_uri()}');font-weight:300 800;font-display:block}}")
    loads = [f"{wt} 40px 'CVES Sans'" for wt in sorted(sans)] + (["700 40px 'CVES Serif'"] if serif else [])
    return "\n".join(css), loads


def css_vars(S, size):
    """the :root custom properties a piece can use (docs/MOTION.md lists them)"""
    w, h = size; u = min(w, h) / 100; m = motion_cfg(S); pal = palette(S); x0, y0, x1, y1 = safe_frac(S, size)
    v = {"--u": f"{u:.4f}px", "--u-px": f"{u:.4f}", "--w": f"{w}px", "--h": f"{h}px",
         "--font-sans": "'CVES Sans', system-ui, sans-serif", "--font-serif": "'CVES Serif', Georgia, serif",
         "--safe-l": f"{x0 * 100:.3f}%", "--safe-t": f"{y0 * 100:.3f}%", "--safe-r": f"{(1 - x1) * 100:.3f}%", "--safe-b": f"{(1 - y1) * 100:.3f}%",
         "--safe-w": f"{(x1 - x0) * w:.2f}px", "--safe-h": f"{(y1 - y0) * h:.2f}px",
         "--r": f"{float(m['radius_u']) * u:.2f}px", "--r-s": f"{float(m['radius_u']) * u * .55:.2f}px",
         "--glass-alpha": f"{float(m['glass_alpha']):.3f}", "--landscape": "1" if w > h else "0"}
    r = float(m["type_ratio"])
    for k in range(10): v[f"--t-{k}"] = f"{2.2 * r ** k * u:.2f}px"            # modular type scale, --t-0 smallest
    for k, s in enumerate((1, 2, 3, 4.5, 6, 9), 1): v[f"--s-{k}"] = f"{s * u:.2f}px"
    for k, c in pal.items():
        n = k.replace("_", "-"); v[f"--{n}"] = f"rgb({c[0]} {c[1]} {c[2]})"; v[f"--{n}-rgb"] = f"{c[0]} {c[1]} {c[2]}"
    return v


def style_subset(S, size):
    """everything of the style a piece can see (the cache key uses it)"""
    sans, serif = fonts(S)
    return {"vars": css_vars(S, size), "motion": motion_cfg(S), "fonts": [sans, serif]}


# ------------------------------------------------------------------ jobs (one piece instance on the timeline)
def _is_time_key(k): return isinstance(k, str) and (k == "at" or k.endswith("_at"))


def rel_times(x, t0):
    """params with every `at` / `*_at` time made piece-relative (cut-time seconds -> seconds since the piece starts)"""
    if isinstance(x, dict):
        return {k: (round(v - t0, 6) if _is_time_key(k) and isinstance(v, (int, float)) and not isinstance(v, bool) else rel_times(v, t0)) for k, v in x.items()}
    if isinstance(x, list): return [rel_times(v, t0) for v in x]
    return x


def _uri(p):
    try:
        q = pathlib.Path(p)
        return q.resolve().as_uri() if q.exists() else None
    except (OSError, ValueError): return None


def page_params(piece, p, t0, resolve=None):
    """defaults + params, times piece-relative, path/asset params as file:// URIs (missing files -> null)"""
    out = piece.defaults(); out.update({k: copy.deepcopy(v) for k, v in (p or {}).items() if k not in ("duration", "exit")})
    out = rel_times(out, t0)
    for k, spec in piece.params.items():
        ty = spec.get("type") if isinstance(spec, dict) else spec
        if ty in PATH_TYPES and out.get(k):
            v = str(out[k])
            if ty == "icon" and not any(c in v for c in "/\\.") and _uri(os.path.join(G.ICONS, v + ".svg")):
                out[k] = _uri(os.path.join(G.ICONS, v + ".svg")); continue
            path = resolve(v) if resolve else v
            out[k] = _uri(path) or _uri(os.path.join(G.ROOT, v))
    return out


class Job:
    """one piece instance: where it sits on the timeline and the exact page it renders"""
    def __init__(self, piece, params, S, size, fps, start, dur, exit=False, resolve=None, root=None):
        self.piece, self.S, self.size, self.fps = piece, S, (int(size[0]), int(size[1])), float(fps)
        self.start = round(float(start) * self.fps) / self.fps          # clock zero on a whole frame (MOT-07)
        self.dur = max(1 / self.fps, float(dur)); self.n = max(1, int(round(self.dur * self.fps)))
        self.end = self.start + self.n / self.fps; self.exit = bool(exit)
        self.params = page_params(piece, params, self.start, resolve)
        self.root = pathlib.Path(root) if root else default_cache_root()
        key = {"v": VERSION, "piece": piece.source_hash(), "runtime": _file_hash(RUNTIME), "base": _file_hash(BASE_CSS),
               "params": self.params, "style": style_subset(S, self.size), "size": self.size, "fps": self.fps, "n": self.n, "exit": self.exit}
        self.key = hashlib.sha256(json.dumps(key, sort_keys=True, default=str).encode()).hexdigest()[:20]
        self.dir = self.root / self.key

    def frame_index(self, t): return min(self.n - 1, max(0, int(round((t - self.start) * self.fps))))
    def frame_path(self, k): return self.dir / f"{k:05d}.png"
    @property
    def done(self): return (self.dir / "manifest.json").exists()
    def manifest(self): return json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))

    def boot(self):
        return {"params": self.params, "motion": motion_cfg(self.S),
                "ctx": {"w": self.size[0], "h": self.size[1], "fps": self.fps, "dur": self.n / self.fps, "exit": self.exit}}


@lru_cache(None)
def _file_hash_cached(p, mtime, size):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def _file_hash(p):
    st = os.stat(p); return _file_hash_cached(str(p), st.st_mtime_ns, st.st_size)


def default_cache_root():
    """$CVES_MOTION_CACHE (prerender sets it to PROJECT/Edit/motion for its workers), else ~/.cves/cache/motion"""
    return pathlib.Path(os.environ.get("CVES_MOTION_CACHE") or os.path.expanduser(os.path.join("~", ".cves", "cache", "motion")))


def page_html(job):
    """the full page for a job: fonts, CSS variables, base.css, boot data, runtime, then the piece"""
    faces, loads = _font_faces(job.S)
    vars_ = css_vars(job.S, job.size)
    boot = job.boot(); boot["fonts"] = loads
    root = ":root{" + ";".join(f"{k}:{v}" for k, v in vars_.items()) + "}"
    body = job.piece.html_path.read_text(encoding="utf-8")
    return ("<!doctype html><html><head><meta charset=\"utf-8\">\n"
            f"<style>{faces}\n{root}</style>\n<style>{BASE_CSS.read_text(encoding='utf-8')}</style>\n"
            f"<script>window.__CVES_BOOT = {json.dumps(boot)};</script>\n"
            f"<script>{RUNTIME.read_text(encoding='utf-8')}</script>\n</head><body>\n{body}\n</body></html>\n")


# ------------------------------------------------------------------ Chromium (one browser, one page per process)
class _Chromium:
    pw = browser = page = None; size = None

    def get_page(self, size):
        if self.page is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise SystemExit(f"motion pieces need Playwright + Chromium: {PIP_HINT}")
            try:
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch(args=["--allow-file-access-from-files", "--force-color-profile=srgb",
                                                             "--font-render-hinting=none", "--disable-lcd-text", "--hide-scrollbars"])
            except Exception as e:      # playwright raises its own Error when the browser build is missing
                self.close()
                if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                    raise SystemExit(f"motion pieces need Chromium: {INSTALL_HINT}")
                raise
            ctx = self.browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=1)
            self.page = ctx.new_page(); self.size = tuple(size)
            atexit.register(self.close)
        elif tuple(size) != self.size:
            self.page.set_viewport_size({"width": size[0], "height": size[1]}); self.size = tuple(size)
        return self.page

    def close(self):
        for x in (self.browser, self.pw):
            try:
                if x is self.pw and x: x.stop()
                elif x: x.close()
            except Exception: pass
        self.pw = self.browser = self.page = None


CHROME = _Chromium()


@lru_cache(1)
def available():
    """(True, "") when Playwright and its Chromium are installed, else (False, why)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, f"playwright is not installed ({PIP_HINT})"
    try:
        with sync_playwright() as pw:
            exe = pw.chromium.executable_path
        return (True, "") if exe and os.path.exists(exe) else (False, f"Chromium missing: {INSTALL_HINT}")
    except Exception as e:
        return False, f"playwright failed: {e}"[:200]


def _load(page, job, folder):
    """write the page into folder and open it (file:// so @font-face file URLs and image assets load)"""
    html = folder / "index.html"; html.write_text(page_html(job), encoding="utf-8")
    page.goto(html.resolve().as_uri(), wait_until="load")
    return page.evaluate("() => CVES.__ready()")


def render(job, log=None):
    """render every frame of a job to PNG (cached). Returns the job's cache folder."""
    if job.done: return job.dir
    job.root.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f".{job.key}.", dir=str(job.root)))
    try:
        page = CHROME.get_page(job.size)
        res = _load(page, job, tmp); text = []
        for k in range(job.n):
            text.append(page.evaluate("t => window.__seek(t)", k / job.fps) or "")
            page.screenshot(path=str(tmp / f"{k:05d}.png"), omit_background=True, type="png")
        man = {"piece": job.piece.name, "n": job.n, "fps": job.fps, "size": list(job.size), "dur": job.n / job.fps,
               "text": text, "cues": res.get("cues", []), "params": job.params, "version": VERSION}
        (tmp / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
        (tmp / "index.html").unlink(missing_ok=True)
        try: os.replace(tmp, job.dir)
        except OSError:
            if not job.done: raise                         # someone else finished the same job first: theirs is identical
        if log: log(f"motion: {job.piece.name} {job.n} frames {job.size[0]}x{job.size[1]} -> {job.dir.name}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return job.dir


def cues_for(job):
    """the piece's own sound cues (piece-relative seconds): from the rendered manifest, else from the page (no frames),
    else from meta.yaml `cues:` when Chromium is missing"""
    if job.done: return job.manifest().get("cues", [])
    side = job.root / f"{job.key}.cues.json"
    if side.exists(): return json.loads(side.read_text(encoding="utf-8"))
    if available()[0]:
        job.root.mkdir(parents=True, exist_ok=True)
        tmp = pathlib.Path(tempfile.mkdtemp(prefix=f".{job.key}.c.", dir=str(job.root)))
        try:
            cues = _load(CHROME.get_page(job.size), job, tmp).get("cues", [])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        side.write_text(json.dumps(cues), encoding="utf-8"); return cues
    return [list(c) + [{}] * (4 - len(c)) for c in (job.piece.meta.get("cues") or [])]


def render_piece(piece, params, S, size, fps, duration, out_dir, exit=False, resolve=None, log=None):
    """render one piece standalone (piece-relative times) into the cache folder out_dir; returns the Job (frames in job.dir)"""
    piece = PIECES.get(piece) or discover().get(piece) if isinstance(piece, str) else piece
    if piece is None: raise SystemExit(f"unknown motion piece. Available: {', '.join(sorted(PIECES or discover()))}")
    job = Job(piece, params, S, size, fps, 0.0, duration, exit=exit, resolve=resolve, root=out_dir)
    render(job, log); return job


# ------------------------------------------------------------------ timeline hook
def prerender(pr, TL, log=print):
    """render every motion piece the timeline uses ONCE, before render's spawn pool starts (workers only read PNGs).
    Also points the workers at PROJECT/Edit/motion and warns when hero pieces sit closer than motion.hero_min_gap_s."""
    from .. import templates as TPL
    os.environ["CVES_MOTION_CACHE"] = pr.e("motion")
    jobs, heroes = [], []
    def add(name, params, ctx):
        fns = TPL.REGISTRY.get(name)
        job_fn = getattr(fns[0], "motion_job", None) if fns else None
        if not job_fn: return
        job = job_fn(params or {}, ctx)
        if job is None: return
        jobs.append(job)
        if job.piece.hero: heroes.append((job.start, name))
    for c in TL.cuts: add(c["template"], c.get("params"), TL.ctx(c["start"], c["end"]))
    segs = {s["id"]: s for s in TL.segs}
    for r in TL.E.get("roto", []) or []:
        s = segs.get(r.get("segment"))
        if s: add(r["template"], r.get("params"), TL.ctx(s["t0"], s["t1"]))
    for sid, lst in TL.chest.items():
        s = segs.get(sid)
        if s:
            for c in lst: add(c["template"], c.get("params"), TL.ctx(s["t0"], s["t1"], chin=None, chin_hold=None))
    if TL.END: add(TL.E["end_card"]["template"], TL.E["end_card"].get("params"), TL.ctx(TL.T_END, TL.T_END + TL.END))
    gap = float(motion_cfg(TL.S).get("hero_min_gap_s") or 0)
    heroes.sort()
    for (a, n1), (b, n2) in zip(heroes, heroes[1:]):
        if gap and b - a < gap and log: log(f"motion: hero pieces {n1} @{a:.2f}s and {n2} @{b:.2f}s are {b - a:.1f}s apart (motion.hero_min_gap_s {gap:g}): restraint")
    seen = set()
    for j in jobs:
        if j.key in seen: continue
        seen.add(j.key); render(j, log)
    return len(seen)


# ------------------------------------------------------------------ preview (cves motion preview)
def _stage_bg(size, S, kind="stage"):
    """an RGB float preview background: the dark stage (cutaways) or a mid-tone stand-in for video (overlays)"""
    import numpy as np
    w, h = size; y = np.linspace(0, 1, h)[:, None]; x = np.linspace(-1, 1, w)[None, :]
    if kind == "video":       # warm mid-tones with a soft subject blob: the worst case for legibility (GFX-15)
        base = np.zeros((h, w, 3), np.float32) + np.array([.42, .36, .31], np.float32)
        blob = np.exp(-((x * .9) ** 2 + ((y - .55) * 2.2) ** 2) * 2.2)[..., None]
        return np.clip(base * (.75 + .45 * (1 - y))[..., None] * 1.0 + blob * np.array([.18, .14, .1], np.float32), 0, 1)
    pal = palette(S); bg = np.array(pal["bg"], np.float32) / 255
    glow = (np.clip((y - .48) / .52, 0, 1) ** 1.8 * (1 - .35 * x ** 2))[..., None]
    glow_c = np.array(_rgb(_sget(S, "stage.glow_bottom"), G.STAGE["glow_bottom"]), np.float32) / 255
    return np.clip(bg + glow * glow_c, 0, 1).astype(np.float32)


def composite(job, k, bg):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(job.frame_path(k)).convert("RGBA"), np.float32) / 255
    return bg * (1 - a[..., 3:4]) + a[..., :3] * a[..., 3:4]


def preview(name, params=None, size=None, out=None, duration=None, fps=30, S=None, bg=None, at=None, frames=8, log=print):
    """render a piece standalone and write a contact sheet (.png), one frame (--at, .png) or a clip (.mp4)"""
    import numpy as np
    from PIL import Image, ImageDraw
    from .. import style as STY
    S = S or STY.load(); G.apply_style(S); size = tuple(size or (G.W, G.H))
    pieces = discover(); pc = pieces.get(name) or pieces.get("m_" + name)
    if pc is None: raise SystemExit(f"unknown motion piece '{name}'. Available: {', '.join(sorted(pieces))}")
    p = dict((pc.meta.get("preview") or {}).get("params") or {}); p.update(params or {})
    dur = float(duration or (pc.meta.get("preview") or {}).get("duration") or pc.duration)
    exit_ = bool(p.pop("exit", pc.kinds[:1] == ["overlay"]))
    root = pathlib.Path(tempfile.gettempdir()) / "cves-motion-preview"
    job = render_piece(pc, p, S, size, fps, dur, root, exit=exit_, log=log)
    kind = bg or ("video" if pc.kinds[:1] == ["overlay"] else "stage")
    back = _stage_bg(job.size, S, kind) if kind != "transparent" else None
    out = pathlib.Path(out or f"{pc.name}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    def frame(k):
        if back is None: return Image.open(job.frame_path(k)).convert("RGBA")
        return Image.fromarray((np.clip(composite(job, k, back), 0, 1) * 255 + .5).astype(np.uint8))
    if out.suffix.lower() == ".mp4":
        import subprocess
        from .. import config as CFG
        cmd = [CFG.get("ffmpeg"), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{job.size[0]}x{job.size[1]}",
               "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", str(out)]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for k in range(job.n): pr.stdin.write(np.asarray(frame(k).convert("RGB")).tobytes())
        pr.stdin.close(); rc = pr.wait()
        if rc: raise SystemExit(f"ffmpeg failed ({rc}) writing {out}")
        return out
    if at is not None:
        frame(job.frame_index(float(at))).save(out); return out
    # contact sheet: `frames` moments across the piece, labelled with their time
    ks = sorted({min(job.n - 1, int(round(f * (job.n - 1)))) for f in np.linspace(.04, .985, frames)})
    cols = 4 if job.size[0] < job.size[1] else 3
    sc = min(1.0, 2400 / (cols * job.size[0])); tw, th = int(job.size[0] * sc), int(job.size[1] * sc)
    rows = -(-len(ks) // cols); pad = 16; lab = 34
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * (th + lab) + (rows + 1) * pad), (24, 24, 28))
    d = ImageDraw.Draw(sheet); f = G.font("sb", 22)
    for j, k in enumerate(ks):
        x = pad + (j % cols) * (tw + pad); y = pad + (j // cols) * (th + lab + pad)
        sheet.paste(frame(k).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y + lab))
        d.text((x, y + 4), f"{pc.name}  t={k / job.fps:.2f}s  {job.size[0]}x{job.size[1]}", font=f, fill=(200, 200, 210))
    sheet.save(out); return out


def main(argv=None):
    """cves motion list | preview <piece> [--params JSON] [--size WxH] [--out file.png|.mp4] [--duration s] [--fps n] [--at t] [--bg ...]"""
    import argparse
    ap = argparse.ArgumentParser(prog="cves motion", description="motion pieces: list them, preview one (docs/MOTION.md)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("list", help="every motion piece: name, kinds, origin, params")
    pv = sp.add_parser("preview", help="render one piece to a contact sheet (.png), a frame (--at) or a clip (.mp4)")
    pv.add_argument("piece"); pv.add_argument("--params", default="{}", help="JSON params (times piece-relative)")
    pv.add_argument("--size", default=None, help="WxH (default: the style's platform.size)"); pv.add_argument("--out")
    pv.add_argument("--duration", type=float); pv.add_argument("--fps", type=float, default=30); pv.add_argument("--at", type=float, help="one frame at this time (png)")
    pv.add_argument("--bg", choices=["stage", "video", "transparent"]); pv.add_argument("--project", help="use this project's style and Brand/motion pieces")
    a = ap.parse_args(argv)
    from .. import style as STY
    pr = None
    if getattr(a, "project", None):
        from ..project import Project
        pr = Project(a.project)
    if a.cmd == "list":
        pcs = discover(pr.root if pr else None)
        for n in sorted(pcs):
            pc = pcs[n]; ps = ", ".join(f"{k}{'!' if isinstance(v, dict) and v.get('required') else ''}" for k, v in pc.params.items())
            print(f"{n:22s} {'/'.join(pc.kinds):26s} {pc.origin:8s} {pc.title}{'  [hero]' if pc.hero else ''}\n{'':22s} params: {ps}")
        return 0
    S = STY.load(pr) if pr else STY.load()
    if a.size: size = tuple(int(v) for v in a.size.lower().split("x"))
    else: size = tuple(int(v) for v in (_sget(S, "canvas.size") or _sget(S, "platform.size") or (G.W, G.H)))
    if pr: os.environ["CVES_MOTION"] = str(pathlib.Path(pr.root) / "Brand" / "motion")
    try: params = json.loads(a.params)
    except json.JSONDecodeError as e: raise SystemExit(f"--params is not valid JSON: {e}")
    out = preview(a.piece, params, size, a.out, a.duration, a.fps, S, a.bg, a.at)
    print(out); return 0
