"""Tool and model locations. Order: env var > ~/.cves/config.yaml > defaults below (installers put everything there).
Same keys on Mac and Windows. `cves doctor` checks every one."""
import os, sys, shutil, yaml
from functools import lru_cache

HOME = os.path.expanduser("~")
CVES = os.environ.get("CVES_HOME", os.path.join(HOME, ".cves"))
WIN = sys.platform.startswith("win")
EXE = ".exe" if WIN else ""

def _first(*paths):
    for p in paths:
        if p and (shutil.which(p) or os.path.exists(p)): return shutil.which(p) or p
    return paths[0]

DEFAULTS = {
    "clients_root": lambda: "~/CVES Projects",      # where `cves new` puts client project folders
    # binaries
    "ffmpeg": lambda: _first(os.path.join(CVES, "bin", "ffmpeg" + EXE), "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "ffmpeg"),
    "ffprobe": lambda: _first(os.path.join(CVES, "bin", "ffprobe" + EXE), "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe", "ffprobe"),
    "whisper": lambda: _first(os.path.join(CVES, "bin", "whisper-cli" + EXE), "whisper-cli"),
    "deepfilter": lambda: _first(os.path.join(CVES, "venv-voice", "Scripts" if WIN else "bin", "deepFilter" + EXE),
                                 os.path.join(HOME, "apps", "voice", ".venv", "bin", "deepFilter"), "deepFilter"),
    "earshot": lambda: _first("earshot"),
    # models
    "whisper_model": lambda: _first(os.path.join(CVES, "models", "ggml-large-v3-turbo-q5_0.bin"),
                                    os.path.join(HOME, ".cache", "whisper-cpp", "ggml-large-v3-turbo-q5_0.bin")),
    "rvm_repo": lambda: _first(os.path.join(CVES, "rvm"), os.path.join(HOME, "apps", "matting", "rvm", "src")),
    "rvm_weights": lambda: _first(os.path.join(CVES, "models", "rvm_resnet50.pth"), os.path.join(HOME, "apps", "matting", "rvm", "rvm_resnet50.pth")),
    "yunet": lambda: _first(os.path.join(CVES, "models", "face_detection_yunet_2023mar.onnx"),
                            os.path.join(HOME, ".claude", "skills", "effects", "models", "yunet.onnx")),
}

@lru_cache(None)
def _file_cfg():
    p = os.path.join(CVES, "config.yaml")
    return yaml.safe_load(open(p, encoding="utf-8")) or {} if os.path.exists(p) else {}

def get(key):
    env = os.environ.get("CVES_" + key.upper())
    if env: return env
    if key in _file_cfg(): return os.path.expanduser(str(_file_cfg()[key]))
    return DEFAULTS[key]()

def device():
    import torch
    if torch.cuda.is_available(): return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available(): return "mps"
    return "cpu"
