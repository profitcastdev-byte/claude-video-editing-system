#!/usr/bin/env bash
# Kdenlive control (fallback editor) for CVES on macOS.
#   1. installs Kdenlive (brew cask) unless present; it bundles melt
#   2. clones 12bijaya/MCP_Server_Kdenlive at the reviewed commit into ~/.cves/mcp/kdenlive-mcp
#   3. hardens it (patch_kdenlive_mcp.py: all writes confined to the workspace), makes its venv
#   4. installs the 1080x1920 23.976 Kdenlive profile CVES projects reference
#   5. prints (or with --register runs) the Claude Code registration command
#
# usage: setup/control/install_kdenlive_mcp_mac.sh [--register] [--test]
# env:   CVES_CLIENTS  workspace the MCP server may write in (default: ~/CVES Projects)
set -euo pipefail

REPO="https://github.com/12bijaya/MCP_Server_Kdenlive.git"
PIN="4733141efd1679fee29bfe0be481ab191eaf5f8f"      # reviewed 2026-11-18, see docs/CONTROL-MODE.md
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.cves/mcp/kdenlive-mcp"
WORKSPACE="${CVES_CLIENTS:-$HOME/CVES Projects}"
APP="/Applications/kdenlive.app"
REGISTER=0; TEST=0
for a in "$@"; do
  case "$a" in
    --register) REGISTER=1 ;;
    --test) TEST=1 ;;
    *) echo "unknown option $a"; exit 2 ;;
  esac
done

if [ ! -d "$APP" ]; then
  echo "==> installing Kdenlive (brew install --cask kdenlive)"
  brew install --cask kdenlive
fi
MELT="$APP/Contents/MacOS/melt"
EFFECTS="$APP/Contents/Resources/effects"
[ -x "$MELT" ] || { echo "melt not found at $MELT"; exit 1; }
echo "==> Kdenlive $(defaults read "$APP/Contents/Info.plist" CFBundleShortVersionString), $("$MELT" -version 2>&1 | head -1)"

PY="$(command -v python3.12 || command -v python3)"
mkdir -p "$HOME/.cves/mcp"
if [ ! -d "$DEST/.git" ]; then
  git clone --quiet "$REPO" "$DEST"
fi
git -C "$DEST" fetch --quiet origin
git -C "$DEST" checkout --quiet -- .            # drop a previous hardening so the pin + patch re-apply cleanly
git -C "$DEST" -c advice.detachedHead=false checkout --quiet --detach "$PIN"
[ "$(git -C "$DEST" rev-parse HEAD)" = "$PIN" ] || { echo "pin mismatch"; exit 1; }
echo "==> kdenlive-mcp at $PIN"
"$PY" "$HERE/patch_kdenlive_mcp.py" "$DEST"

"$PY" -m venv "$DEST/.venv"
"$DEST/.venv/bin/python" -m pip install --quiet --upgrade pip
EXTRA=""; [ "$TEST" = 1 ] && EXTRA="[dev]"
"$DEST/.venv/bin/python" -m pip install --quiet -c "$HERE/constraints-mcp.txt" -e "$DEST$EXTRA"
echo "==> venv ready: $DEST/.venv ($("$DEST/.venv/bin/python" -m pip show mcp | grep ^Version))"

# Kdenlive custom profile (see engine/cves/export/kdenlive.py, CUSTOM_PROFILE)
PROFILES="$HOME/Library/Application Support/kdenlive/profiles"
mkdir -p "$PROFILES"
cat >"$PROFILES/cves_vertical_hd_2398" <<'EOF'
description=Vertical HD 1080x1920 23.98 fps
frame_rate_num=24000
frame_rate_den=1001
width=1080
height=1920
progressive=1
sample_aspect_num=1
sample_aspect_den=1
display_aspect_num=9
display_aspect_den=16
colorspace=709
EOF
echo "==> Kdenlive profile: $PROFILES/cves_vertical_hd_2398"
mkdir -p "$WORKSPACE"

if [ "$TEST" = 1 ]; then
  ( cd "$DEST" && KDENLIVE_MCP_MELT="$MELT" KDENLIVE_MCP_EFFECTS_DIR="$EFFECTS" .venv/bin/python -m pytest -q tests/unit ) || echo "(expected: test_import_export_srt_files fails, it exports outside the workspace, which the hardening refuses)"
fi

CMD=(claude mcp add --scope user kdenlive
     -e "KDENLIVE_MCP_WORKSPACE=$WORKSPACE"
     -e "KDENLIVE_MCP_MELT=$MELT"
     -e "KDENLIVE_MCP_EFFECTS_DIR=$EFFECTS"
     -e "KDENLIVE_MCP_CUSTOM_PROFILE=$PROFILES/cves_vertical_hd_2398"
     -- "$DEST/.venv/bin/kdenlive-mcp")
echo
echo "Register with Claude Code (user scope):"
printf '  %q' "${CMD[@]}"; echo
if [ "$REGISTER" = 1 ]; then
  claude mcp remove --scope user kdenlive >/dev/null 2>&1 || true
  "${CMD[@]}"
fi
