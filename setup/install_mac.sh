#!/usr/bin/env bash
# CVES one-shot installer for macOS (Apple Silicon, macOS 14+).
# Idempotent: re-run it any time; finished steps are skipped, broken ones are repaired.
#
#   bash setup/install_mac.sh                 # full install
#   bash setup/install_mac.sh --no-models     # skip the ~700 MB model downloads
#   bash setup/install_mac.sh --rewrite-config  # overwrite ~/.cves/config.yaml with the defaults below
#   bash setup/install_mac.sh --no-path       # do not touch ~/.zprofile (CI / sandbox test: CVES_HOME=/tmp/x)
#
# Layout it creates (the path contract in engine/cves/config.py):
#   ~/.cves/bin/        ffmpeg, ffprobe, whisper-cli (symlinks to Homebrew ffmpeg-full / whisper.cpp), cves
#   ~/.cves/models/     ggml-large-v3-turbo-q5_0.bin, rvm_resnet50.pth, face_detection_yunet_2023mar.onnx
#   ~/.cves/rvm/        clone of PeterL1n/RobustVideoMatting (pinned commit)
#   ~/.cves/venv/       Python 3.12 main venv, engine installed editable
#   ~/.cves/venv-voice/ Python 3.11 venv with deepfilternet (deepFilter CLI)
#   ~/.cves/config.yaml absolute paths for every key in cves.config.DEFAULTS
#   earshot             uv tool, on PATH (~/.local/bin)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CVES="${CVES_HOME:-$HOME/.cves}"
NO_MODELS=0; REWRITE_CONFIG=0; NO_PATH=0
for a in "$@"; do
  case "$a" in
    --no-models) NO_MODELS=1 ;;
    --rewrite-config) REWRITE_CONFIG=1 ;;
    --no-path) NO_PATH=1 ;;
    -h|--help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown option: $a"; exit 2 ;;
  esac
done

# ---- pinned sources -------------------------------------------------------------------------------
RVM_GIT="https://github.com/PeterL1n/RobustVideoMatting.git"
RVM_COMMIT="53d74c6826735f01f4406b5ca9075eee27bec094"
RVM_URL="https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_resnet50.pth"
RVM_SHA="c191a807251164c073dce5fa408e7a816070d539b882b2a3150330a9fec112ce"
YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_SHA="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
WHISPER_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
WHISPER_SHA="394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"
EARSHOT_SRC="earshot[mcp] @ git+https://github.com/Leonxlnx/earshot"
VOICE_PKGS=(deepfilternet==0.5.6 torch==2.1.1 torchaudio==2.1.1 numpy==1.26.2 soundfile==0.12.1)
BREW_PKGS=(ffmpeg-full whisper.cpp yt-dlp git-lfs librsvg uv)

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32mok\033[0m  %s\n' "$*"; }
warn() { printf '    \033[33m!!\033[0m  %s\n' "$*"; }
die()  { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*"; exit 1; }

# ---- 0. platform --------------------------------------------------------------------------------
say "Checking platform"
[ "$(uname -s)" = "Darwin" ] || die "this script is for macOS; on Windows run setup/install_windows.ps1"
[ "$(uname -m)" = "arm64" ] || warn "not Apple Silicon: RVM will run on CPU (slow). Intel Macs are untested."
MACV="$(sw_vers -productVersion)"; [ "${MACV%%.*}" -ge 14 ] || die "macOS $MACV: torch 2.15 needs macOS 14 (Sonoma) or newer"
ok "macOS $MACV $(uname -m)"
xcode-select -p >/dev/null 2>&1 || die "Xcode Command Line Tools missing: run  xcode-select --install  then re-run this script"
ok "Xcode Command Line Tools"

# ---- 1. Homebrew packages -------------------------------------------------------------------------
say "Homebrew packages"
if ! command -v brew >/dev/null 2>&1; then
  [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
command -v brew >/dev/null 2>&1 || die "Homebrew not found. Install it (needs your password), then re-run:
  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
BREW_PREFIX="$(brew --prefix)"
# formula -> command that proves it is already there (installed some other way, e.g. uv's standalone installer)
brew_cmd() { case "$1" in yt-dlp) echo yt-dlp ;; git-lfs) echo git-lfs ;; librsvg) echo rsvg-convert ;; uv) echo uv ;; *) echo "" ;; esac; }
for p in "${BREW_PKGS[@]}"; do
  c="$(brew_cmd "$p")"
  if brew list --versions "$p" >/dev/null 2>&1; then ok "$p $(brew list --versions "$p" | awk '{print $2}')"
  elif [ -n "$c" ] && command -v "$c" >/dev/null 2>&1; then ok "$p (already on PATH: $(command -v "$c"))"
  else
    echo "    installing $p ..."
    if ! brew install "$p"; then
      if [ "$p" = "ffmpeg-full" ]; then
        # Older Homebrew without the core ffmpeg-full formula: use the homebrew-ffmpeg tap (also has drawtext + rubberband)
        warn "core ffmpeg-full failed; trying the homebrew-ffmpeg/ffmpeg tap"
        brew tap homebrew-ffmpeg/ffmpeg && brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-rubberband
      else die "brew install $p failed"; fi
    fi
  fi
done
# The plain `ffmpeg` formula lacks drawtext and rubberband. We never rely on it: the engine uses ~/.cves/bin/ffmpeg.
FF_DIR="$BREW_PREFIX/opt/ffmpeg-full/bin"
[ -x "$FF_DIR/ffmpeg" ] || FF_DIR="$BREW_PREFIX/opt/ffmpeg/bin"     # tap fallback installs as "ffmpeg"
FILTERS="$("$FF_DIR/ffmpeg" -hide_banner -filters 2>/dev/null || true)"   # captured: grep -q on a pipe + pipefail = SIGPIPE
grep -q ' drawtext ' <<<"$FILTERS" || die "$FF_DIR/ffmpeg has no drawtext filter"
grep -q ' rubberband ' <<<"$FILTERS" || die "$FF_DIR/ffmpeg has no rubberband filter"
ok "ffmpeg at $FF_DIR has drawtext + rubberband"
WHISPER_BIN="$BREW_PREFIX/opt/whisper.cpp/bin/whisper-cli"
[ -x "$WHISPER_BIN" ] || WHISPER_BIN="$(command -v whisper-cli || true)"
[ -x "$WHISPER_BIN" ] || die "whisper-cli not found after installing whisper.cpp"
if git config --global --get filter.lfs.process >/dev/null 2>&1; then ok "git-lfs already configured"
else git lfs install --skip-repo >/dev/null && ok "git-lfs hooks (user level)"; fi
UV="$(command -v uv)"

# ---- 2. ~/.cves/bin -------------------------------------------------------------------------------
say "Linking binaries into $CVES/bin"
mkdir -p "$CVES/bin" "$CVES/models"
ln -sfn "$FF_DIR/ffmpeg"  "$CVES/bin/ffmpeg"
ln -sfn "$FF_DIR/ffprobe" "$CVES/bin/ffprobe"
ln -sfn "$WHISPER_BIN"    "$CVES/bin/whisper-cli"
ok "ffmpeg -> $FF_DIR/ffmpeg"; ok "whisper-cli -> $WHISPER_BIN"

# ---- 3. main venv (Python 3.12) ---------------------------------------------------------------------
say "Main venv (Python 3.12) at $CVES/venv"
if [ ! -x "$CVES/venv/bin/python" ] || ! "$CVES/venv/bin/python" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))'; then
  rm -rf "$CVES/venv"; "$UV" venv --python 3.12 "$CVES/venv"
fi
"$UV" pip install --python "$CVES/venv/bin/python" -r "$REPO/setup/requirements.txt"
"$UV" pip install --python "$CVES/venv/bin/python" -e "$REPO/engine"
"$CVES/venv/bin/python" -c 'import torch; print("    torch", torch.__version__, "MPS available:", torch.backends.mps.is_available())'
# motion layer: the Chromium build Playwright drives (idempotent: an installed build is skipped)
"$CVES/venv/bin/python" -m playwright install chromium && ok "Chromium for motion pieces (playwright)"
ln -sfn "$CVES/venv/bin/cves" "$CVES/bin/cves" 2>/dev/null || true

# ---- 4. voice venv (Python 3.11, deepfilternet) ----------------------------------------------------
say "Voice venv (Python 3.11) at $CVES/venv-voice"
if [ ! -x "$CVES/venv-voice/bin/python" ] || ! "$CVES/venv-voice/bin/python" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))'; then
  rm -rf "$CVES/venv-voice"; "$UV" venv --python 3.11 "$CVES/venv-voice"
fi
"$UV" pip install --python "$CVES/venv-voice/bin/python" "${VOICE_PKGS[@]}"
[ -x "$CVES/venv-voice/bin/deepFilter" ] && ok "deepFilter CLI" || die "deepFilter CLI missing in venv-voice"
# Resemble Enhance is deliberately NOT installed: its generative mode rewrote words (see TOOLS-REGISTRY.md).

# ---- 5. RVM code -------------------------------------------------------------------------------------
say "Robust Video Matting code at $CVES/rvm"
if [ ! -d "$CVES/rvm/.git" ]; then git clone --quiet "$RVM_GIT" "$CVES/rvm"; fi
git -C "$CVES/rvm" fetch --quiet origin || warn "could not fetch RVM (offline?); using the existing clone"
git -C "$CVES/rvm" -c advice.detachedHead=false checkout --quiet "$RVM_COMMIT"
ok "RVM @ ${RVM_COMMIT:0:7}"

# ---- 6. models ---------------------------------------------------------------------------------------
sha() { shasum -a 256 "$1" | awk '{print $1}'; }
fetch_model() {  # name url sha [existing local copies to clone instead of downloading...]
  local name="$1" url="$2" want="$3"; shift 3
  local dest="$CVES/models/$name"
  if [ -f "$dest" ] && [ "$(sha "$dest")" = "$want" ]; then ok "$name (present)"; return; fi
  for src in "$@"; do
    if [ -f "$src" ] && [ "$(sha "$src")" = "$want" ]; then
      cp -c "$src" "$dest" 2>/dev/null || cp "$src" "$dest"; ok "$name (copied from $src)"; return
    fi
  done
  echo "    downloading $name ..."
  curl -fL --retry 3 -C - -o "$dest.part" "$url" || die "download failed: $url"
  [ "$(sha "$dest.part")" = "$want" ] || { rm -f "$dest.part"; die "checksum mismatch for $name"; }
  mv "$dest.part" "$dest"; ok "$name (downloaded)"
}
if [ "$NO_MODELS" = 1 ]; then
  say "Skipping models (--no-models)"
else
  say "Models in $CVES/models"
  fetch_model ggml-large-v3-turbo-q5_0.bin "$WHISPER_URL" "$WHISPER_SHA" "$HOME/.cache/whisper-cpp/ggml-large-v3-turbo-q5_0.bin"
  fetch_model rvm_resnet50.pth "$RVM_URL" "$RVM_SHA" "$HOME/apps/matting/rvm/rvm_resnet50.pth"
  fetch_model face_detection_yunet_2023mar.onnx "$YUNET_URL" "$YUNET_SHA" "$HOME/.claude/skills/effects/models/yunet.onnx"
fi

# ---- 7. earshot ----------------------------------------------------------------------------------------
say "earshot (uv tool)"
TOOLS="$("$UV" tool list 2>/dev/null || true)"
if grep -q '^earshot ' <<<"$TOOLS"; then ok "$(grep '^earshot ' <<<"$TOOLS")"
else "$UV" tool install "$EARSHOT_SRC"; fi
[ "$NO_PATH" = 1 ] || "$UV" tool update-shell >/dev/null 2>&1 || true

# ---- 8. config.yaml ------------------------------------------------------------------------------------
say "Config"
CFG="$CVES/config.yaml"
if [ -f "$CFG" ] && [ "$REWRITE_CONFIG" = 0 ]; then
  ok "$CFG exists, left as is (use --rewrite-config to regenerate)"
else
  EARSHOT_BIN="$(command -v earshot || echo "$HOME/.local/bin/earshot")"
  cat > "$CFG" <<YAML
# Written by setup/install_mac.sh on $(date +%Y-%m-%d). Absolute paths; env vars CVES_<KEY> override any line.
ffmpeg: $CVES/bin/ffmpeg
ffprobe: $CVES/bin/ffprobe
whisper: $CVES/bin/whisper-cli
deepfilter: $CVES/venv-voice/bin/deepFilter
earshot: $EARSHOT_BIN
whisper_model: $CVES/models/ggml-large-v3-turbo-q5_0.bin
rvm_repo: $CVES/rvm
rvm_weights: $CVES/models/rvm_resnet50.pth
yunet: $CVES/models/face_detection_yunet_2023mar.onnx
YAML
  ok "wrote $CFG"
fi

# ---- 9. PATH ---------------------------------------------------------------------------------------------
say "PATH"
PROFILE="$HOME/.zprofile"
LINE="export PATH=\"$CVES/bin:\$HOME/.local/bin:\$PATH\"  # CVES"
if [ "$NO_PATH" = 1 ]; then ok "skipped (--no-path); add $CVES/bin and ~/.local/bin to PATH yourself"
elif grep -qF '# CVES' "$PROFILE" 2>/dev/null; then ok "$PROFILE already has the CVES PATH line"
else printf '\n%s\n' "$LINE" >> "$PROFILE"; ok "added ~/.cves/bin and ~/.local/bin to PATH in $PROFILE (open a new terminal)"; fi
export PATH="$CVES/bin:$HOME/.local/bin:$PATH"

# ---- 10. doctor ------------------------------------------------------------------------------------------
say "Installing Claude Code plugins and skills (setup/skills.json)"
"$CVES/venv/bin/python" "$REPO/setup/install_skills.py" || echo "  (some skills failed: see above; re-run python setup/install_skills.py later)"

say "Running doctor"
"$CVES/venv/bin/python" "$REPO/setup/doctor.py" || { echo; die "doctor found problems: fix the FAIL rows above, then re-run this script"; }
echo
echo "CVES is installed. Open a new terminal (or: source ~/.zprofile) and run:  cves doctor"
