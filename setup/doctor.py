#!/usr/bin/env python3
"""CVES doctor: checks every dependency, model file, GPU backend and font, prints a pass/fail table with fix hints.

    ~/.cves/venv/bin/python setup/doctor.py          (Mac)
    %USERPROFILE%\\.cves\\venv\\Scripts\\python setup\\doctor.py   (Windows)
    cves doctor                                       (same thing, once the engine is installed)
    ... --deep   also verifies model checksums and imports RVM (slower)
    ... --json   machine-readable output

Exit code 0 when nothing FAILs (WARN rows are allowed), 1 otherwise.
Every path comes from cves.config (env var > ~/.cves/config.yaml > defaults); every key in DEFAULTS is checked.
"""
import argparse, hashlib, importlib, importlib.metadata, json, os, platform, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = sys.platform.startswith("win")
MAC = sys.platform == "darwin"
INSTALLER = r"powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1" if WIN else "bash setup/install_mac.sh"

SHA = {  # same pins as the installers
    "whisper_model": "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2",
    "rvm_weights": "c191a807251164c073dce5fa408e7a816070d539b882b2a3150330a9fec112ce",
    "yunet": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
}
MIN_SIZE = {"whisper_model": 500_000_000, "rvm_weights": 100_000_000, "yunet": 200_000}
FONTS = ["Poppins-Medium.ttf", "Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "Poppins-ExtraBold.ttf", "CormorantGaramond.ttf"] + \
        [f"NotoSans{sc}-{w}.ttf" for sc in ("Devanagari", "Tamil", "Telugu", "Kannada", "Malayalam", "Bengali", "Gujarati")
         for w in ("Medium", "SemiBold", "Bold", "ExtraBold")]
# import name -> pip name (pins are read from setup/requirements.txt)
PKGS = {"torch": "torch", "torchvision": "torchvision", "numpy": "numpy", "scipy": "scipy", "cv2": "opencv-python",
        "onnxruntime": "onnxruntime", "av": "av", "PIL": "pillow", "soundfile": "soundfile", "librosa": "librosa",
        "yaml": "pyyaml", "requests": "requests", "opentimelineio": "opentimelineio"}

rows = []


def add(group, name, status, detail="", fix=""):
    rows.append({"group": group, "check": name, "status": status, "detail": detail, "fix": fix})


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "not found"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 126, str(e)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pins():
    out = {}
    try:
        for line in open(os.path.join(REPO, "setup", "requirements.txt"), encoding="utf-8"):
            m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s#]+)", line.strip())
            if m:
                out[m.group(1).lower()] = m.group(2)
    except OSError:
        pass
    return out


def load_config():
    try:
        import cves.config as cfg  # installed editable
        return cfg
    except ImportError:
        sys.path.insert(0, os.path.join(REPO, "engine"))
        try:
            import cves.config as cfg
            add("engine", "cves package", "WARN", "imported from the repo, not installed in this venv",
                f"{INSTALLER}  (or: pip install -e engine)")
            return cfg
        except Exception as e:  # yaml missing etc.
            add("engine", "cves.config", "FAIL", f"cannot import: {e}", f"run doctor with the CVES venv python, or {INSTALLER}")
            return None


# ---------------------------------------------------------------------------------------------- checks
def check_python():
    v = sys.version_info
    st = "PASS" if (v.major, v.minor) == (3, 12) else "WARN"
    add("python", "interpreter", st, f"{platform.python_version()} at {sys.executable}",
        "" if st == "PASS" else "run doctor with ~/.cves/venv python (3.12)")
    if shutil.which("cves"):
        add("python", "cves CLI on PATH", "PASS", shutil.which("cves"))
    else:
        add("python", "cves CLI on PATH", "WARN", "not on PATH",
            "open a new terminal; Mac: ~/.cves/bin is added in ~/.zprofile; Windows: %USERPROFILE%\\.cves\\bin in user PATH")


def check_binary(cfg, key, version_args, label=None):
    path = cfg.get(key)
    label = label or key
    found = shutil.which(path) or (path if os.path.exists(path) else None)
    hint = f"{INSTALLER}  (or set {key}: in ~/.cves/config.yaml / env CVES_{key.upper()})"
    if not found:
        add("binaries", label, "FAIL", f"missing: {path}", hint)
        return None
    if version_args is None:
        add("binaries", label, "PASS", found)
        return found
    code, out = run([found] + version_args)
    first = next((l.strip() for l in out.splitlines() if l.strip()), "")
    add("binaries", label, "PASS" if code == 0 else "FAIL", f"{first[:70]}  [{found}]", "" if code == 0 else hint)
    return found if code == 0 else None


def check_ffmpeg(ff):
    if not ff:
        return
    _, filters = run([ff, "-hide_banner", "-filters"])
    _, encoders = run([ff, "-hide_banner", "-encoders"])
    fix = ("brew install ffmpeg-full; the plain `ffmpeg` formula lacks these. ~/.cves/bin/ffmpeg must point at "
           "$(brew --prefix)/opt/ffmpeg-full/bin/ffmpeg") if not WIN else \
          "install the gyan.dev FULL build (winget install Gyan.FFmpeg), not essentials, and copy it to %USERPROFILE%\\.cves\\bin"
    for f in ("drawtext", "rubberband", "subtitles", "loudnorm"):
        ok = re.search(rf"\s{f}\s", filters) is not None
        add("ffmpeg", f"filter {f}", "PASS" if ok else "FAIL", "", "" if ok else fix)
    for e in ("libx264", "prores_ks", "pcm_s24le", "aac"):
        ok = re.search(rf"\s{e}\s", encoders) is not None
        add("ffmpeg", f"encoder {e}", "PASS" if ok else "FAIL", "", "" if ok else fix)


def check_models(cfg, deep):
    for key in ("whisper_model", "rvm_weights", "yunet"):
        path = cfg.get(key)
        if not os.path.isfile(path):
            add("models", key, "FAIL", f"missing: {path}", f"{INSTALLER}  (downloads into ~/.cves/models)")
            continue
        size = os.path.getsize(path)
        if size < MIN_SIZE[key]:
            add("models", key, "FAIL", f"too small ({size} bytes), partial download?", f"delete it and re-run {INSTALLER}")
            continue
        if deep:
            ok = sha256(path) == SHA[key]
            add("models", key, "PASS" if ok else "FAIL", f"{size / 1e6:.1f} MB, sha256 {'ok' if ok else 'MISMATCH'}  [{path}]",
                "" if ok else f"delete it and re-run {INSTALLER}")
        else:
            add("models", key, "PASS", f"{size / 1e6:.1f} MB  [{path}]")
    repo = cfg.get("rvm_repo")
    if not os.path.isfile(os.path.join(repo, "model", "__init__.py")):
        add("models", "rvm_repo", "FAIL", f"no model/ package in {repo}",
            f"git clone https://github.com/PeterL1n/RobustVideoMatting {repo}  (or re-run {INSTALLER})")
        return
    if not deep:
        add("models", "rvm_repo", "PASS", repo)
        return
    try:
        sys.path.insert(0, repo)
        import torch
        from model import MattingNetwork  # noqa
        net = MattingNetwork("resnet50").eval()
        net.load_state_dict(torch.load(cfg.get("rvm_weights"), map_location="cpu"))
        add("models", "rvm_repo", "PASS", f"MattingNetwork(resnet50) loads weights  [{repo}]")
    except Exception as e:
        add("models", "rvm_repo", "FAIL", f"import/load failed: {e}"[:120], f"re-run {INSTALLER}")


def check_packages():
    want = pins()
    for mod, pip_name in PKGS.items():
        try:
            m = importlib.import_module(mod)
            ver = None
            for dist in (pip_name, pip_name + "-headless") if pip_name.startswith("opencv") else (pip_name,):
                try:
                    ver = importlib.metadata.version(dist)
                    break
                except importlib.metadata.PackageNotFoundError:
                    pass
            ver = str(ver or getattr(m, "__version__", "?"))
            pin = want.get(pip_name)
            base = ver.split("+")[0]
            if pin and base != pin:
                add("packages", pip_name, "WARN", f"{ver} (pinned {pin})", "pip install -r setup/requirements.txt")
            else:
                add("packages", pip_name, "PASS", ver)
        except Exception as e:
            add("packages", pip_name, "FAIL", f"import {mod} failed: {e}"[:100], "pip install -r setup/requirements.txt")
    for adapter in ("kdenlive", "fcpx_xml"):
        try:
            import opentimelineio as otio
            names = [a.name for a in otio.plugins.ActiveManifest().adapters]
            ok = adapter in names
            add("packages", f"otio adapter {adapter}", "PASS" if ok else "WARN", "" if ok else f"have: {', '.join(names)[:60]}",
                "" if ok else "pip install otio-kdenlive-adapter otio-fcpx-xml-adapter")
        except Exception:
            pass


def check_gpu(cfg):
    try:
        import torch
    except Exception:
        add("gpu", "torch backend", "FAIL", "torch not importable", "pip install -r setup/requirements.txt")
        return
    dev = cfg.device() if cfg and hasattr(cfg, "device") else "cpu"
    if dev == "mps":
        add("gpu", "torch backend", "PASS", f"MPS (Apple GPU), torch {torch.__version__}")
    elif dev == "cuda":
        add("gpu", "torch backend", "PASS", f"CUDA {torch.version.cuda}: {torch.cuda.get_device_name(0)}")
    else:
        fix = ("NVIDIA GPU present but CPU torch installed: re-run install_windows.ps1 (it picks the CUDA wheel when nvidia-smi works)"
               if shutil.which("nvidia-smi") else "no GPU backend: matting runs on CPU (several x slower). Fine for short clips.")
        add("gpu", "torch backend", "WARN", f"CPU only, torch {torch.__version__}", fix)
    try:
        x = torch.ones(64, 64, device=dev)
        float((x @ x).sum())
        add("gpu", f"tensor op on {dev}", "PASS", "")
    except Exception as e:
        add("gpu", f"tensor op on {dev}", "FAIL", str(e)[:100], "update torch / GPU driver")


def check_assets():
    fdir = os.path.join(REPO, "assets", "fonts")
    try:
        from PIL import ImageFont, features
        add("fonts", "complex-script shaping (raqm)", "PASS" if features.check("raqm") else "WARN",
            "available" if features.check("raqm") else "off: Indic/Arabic captions will mis-shape",
            "mac: brew install fribidi harfbuzz, then export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib; linux: apt install libfribidi0 libraqm0")
    except Exception:
        ImageFont = None
    for f in FONTS:
        p = os.path.join(fdir, f)
        if not os.path.isfile(p):
            add("fonts", f, "FAIL", "missing", "git pull (fonts are committed in assets/fonts)")
            continue
        if ImageFont:
            try:
                fam, style = ImageFont.truetype(p, 40).getname()
                add("fonts", f, "PASS", f"{fam} {style}")
            except Exception as e:
                add("fonts", f, "FAIL", f"unreadable: {e}", "git lfs pull / re-download from google/fonts")
        else:
            add("fonts", f, "PASS", "present (PIL not available to load it)")
    lic = os.path.join(fdir, "LICENSES")
    for f in ("OFL-Poppins.txt", "OFL-CormorantGaramond.txt"):
        ok = os.path.isfile(os.path.join(lic, f))
        add("fonts", f"LICENSES/{f}", "PASS" if ok else "WARN", "", "" if ok else "restore assets/fonts/LICENSES from git")
    for sub, what in (("icons", "Material icons (Apache-2.0)"), ("sfx", "SFX (CC0)")):
        d = os.path.join(REPO, "assets", sub)
        n = len([x for x in os.listdir(d) if not x.startswith(".")]) if os.path.isdir(d) else 0
        cred = os.path.isfile(os.path.join(d, "CREDITS.md"))
        st = "PASS" if n > 1 and cred else "WARN"
        add("assets", sub, st, f"{what}: {n} files, CREDITS.md {'yes' if cred else 'NO'}", "" if st == "PASS" else "git pull")


def check_tools():
    tools = [("yt-dlp", ["--version"], "WARN", "brew install yt-dlp" if MAC else "winget install yt-dlp.yt-dlp"),
             ("git", ["--version"], "FAIL", "install git"),
             ("git-lfs", ["version"], "WARN", "brew install git-lfs && git lfs install" if MAC else "winget install GitHub.GitLFS"),
             ("uv", ["--version"], "FAIL", "brew install uv" if MAC else "winget install astral-sh.uv"),
             ("rsvg-convert", ["--version"], "WARN" if WIN else "FAIL",
              "brew install librsvg" if MAC else "optional on Windows (engine falls back to PNG icons)"),
             ("claude", ["--version"], "WARN", "install Claude Code: https://docs.claude.com/claude-code")]
    for name, args, sev, fix in tools:
        exe = shutil.which(name)
        if not exe:
            add("tools", name, sev, "not on PATH", fix)
            continue
        code, out = run([exe] + args, timeout=20)
        first = next((l.strip() for l in out.splitlines() if l.strip()), "")
        add("tools", name, "PASS" if code == 0 else sev, first[:70], "" if code == 0 else fix)


def check_config_keys(cfg, seen):
    """Any DEFAULTS key not covered by a dedicated check still gets an existence check."""
    for key in cfg.DEFAULTS:
        if key in seen:
            continue
        p = cfg.get(key)
        ok = bool(shutil.which(p) or os.path.exists(p))
        add("config", key, "PASS" if ok else "FAIL", p, "" if ok else f"set {key}: in ~/.cves/config.yaml or re-run {INSTALLER}")


# ---------------------------------------------------------------------------------------------- output
def print_table():
    w = {"group": 9, "check": 26, "status": 6, "detail": 62}
    line = "+" + "+".join("-" * (w[k] + 2) for k in w) + "+"
    print(line)
    print("| " + " | ".join(k.upper().ljust(w[k]) for k in w) + " |")
    print(line)
    for r in rows:
        cells = []
        for k in w:
            v = str(r[k])
            cells.append((v if len(v) <= w[k] else v[: w[k] - 3] + "...").ljust(w[k]))
        print("| " + " | ".join(cells) + " |")
    print(line)
    fails = [r for r in rows if r["status"] == "FAIL"]
    warns = [r for r in rows if r["status"] == "WARN"]
    print(f"\n{len(rows) - len(fails) - len(warns)} pass, {len(warns)} warn, {len(fails)} fail")
    hints = [r for r in rows if r["status"] != "PASS" and r["fix"]]
    if hints:
        print("\nFix hints:")
        for r in hints:
            print(f"  [{r['status']}] {r['group']}/{r['check']}: {r['fix']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check the CVES install")
    ap.add_argument("--deep", action="store_true", help="verify model checksums and load RVM weights")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = ap.parse_args(argv)
    rows.clear()

    check_python()
    cfg = load_config()
    seen = set()
    if cfg:
        add("engine", "config", "PASS", os.path.join(cfg.CVES, "config.yaml") +
            (" (found)" if os.path.isfile(os.path.join(cfg.CVES, "config.yaml")) else " (absent: using defaults)"))
        ff = check_binary(cfg, "ffmpeg", ["-hide_banner", "-version"])
        check_binary(cfg, "ffprobe", ["-hide_banner", "-version"])
        check_ffmpeg(ff)
        check_binary(cfg, "whisper", ["--version"], "whisper (whisper-cli)")
        check_binary(cfg, "deepfilter", None, "deepfilter (deepFilter)")
        check_binary(cfg, "earshot", ["--help"])  # earshot has no --version flag
        check_models(cfg, a.deep)
        seen = {"ffmpeg", "ffprobe", "whisper", "deepfilter", "earshot", "whisper_model", "rvm_repo", "rvm_weights", "yunet"}
        check_config_keys(cfg, seen)
    check_packages()
    check_gpu(cfg)
    check_assets()
    check_tools()

    if a.json:
        print(json.dumps(rows, indent=1))
    else:
        print(f"CVES doctor  ({platform.system()} {platform.release()} {platform.machine()})\n")
        print_table()
    return 1 if any(r["status"] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
