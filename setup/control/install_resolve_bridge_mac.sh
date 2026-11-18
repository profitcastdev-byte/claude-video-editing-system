#!/usr/bin/env bash
# DaVinci Resolve (Free) control for CVES on macOS.
#   1. clones hiteshK03/davinci-resolve-mcp at the reviewed commit into ~/.cves/mcp/davinci-resolve-mcp
#   2. makes its venv (MCP SDK only; --with-ai adds Whisper/Demucs/rembg, several GB, downloads models on use)
#   3. hardens CursorBridge.py (patch_cursorbridge.py) and copies it into Resolve's Scripts/Utility folder
#   4. prints (or with --register runs) the Claude Code registration command
# Resolve itself is NOT installed here: its download needs Blackmagic's registration form.
#
# usage: setup/control/install_resolve_bridge_mac.sh [--with-ai] [--register]
# env:   CVES_RESOLVE_SCRIPTS_DIR  override the Scripts/Utility target (tests)
set -euo pipefail

REPO="https://github.com/hiteshK03/davinci-resolve-mcp.git"
PIN="f812df7ab5d376592a24fb94611473fdf3a1acb2"      # reviewed 2026-11-18, see docs/CONTROL-MODE.md
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.cves/mcp/davinci-resolve-mcp"
SCRIPTS="${CVES_RESOLVE_SCRIPTS_DIR:-$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility}"
WITH_AI=0; REGISTER=0
for a in "$@"; do
  case "$a" in
    --with-ai) WITH_AI=1 ;;
    --register) REGISTER=1 ;;
    *) echo "unknown option $a"; exit 2 ;;
  esac
done

PY="$(command -v python3.12 || command -v python3)"
echo "==> python: $PY ($("$PY" --version))"

mkdir -p "$HOME/.cves/mcp"
if [ ! -d "$DEST/.git" ]; then
  git clone --quiet "$REPO" "$DEST"
fi
git -C "$DEST" fetch --quiet origin
git -C "$DEST" -c advice.detachedHead=false checkout --quiet --detach "$PIN"
[ "$(git -C "$DEST" rev-parse HEAD)" = "$PIN" ] || { echo "pin mismatch"; exit 1; }
echo "==> davinci-resolve-mcp at $PIN"

"$PY" -m venv "$DEST/venv"
"$DEST/venv/bin/python" -m pip install --quiet --upgrade pip
"$DEST/venv/bin/python" -m pip install --quiet -c "$HERE/constraints-mcp.txt" "mcp"
if [ "$WITH_AI" = 1 ]; then
  "$DEST/venv/bin/python" -m pip install --quiet -c "$HERE/constraints-mcp.txt" -r "$DEST/requirements.txt"
fi
"$DEST/venv/bin/python" -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$DEST/src/resolve_mcp_bridge.py"
echo "==> venv ready: $DEST/venv ($("$DEST/venv/bin/python" -m pip show mcp | grep ^Version))"

if [ ! -d "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve" ] && [ -z "${CVES_RESOLVE_SCRIPTS_DIR:-}" ]; then
  echo "!!  DaVinci Resolve has not been run on this Mac yet; installing the bridge anyway (it appears after install)."
fi
mkdir -p "$SCRIPTS"
"$DEST/venv/bin/python" "$HERE/patch_cursorbridge.py" "$DEST/src/CursorBridge.py" "$SCRIPTS/CursorBridge.py"

CMD=(claude mcp add --scope user davinci-resolve -- "$DEST/venv/bin/python" "$DEST/src/resolve_mcp_bridge.py")
echo
echo "Register with Claude Code (user scope):"
printf '  %q' "${CMD[@]}"; echo
if [ "$REGISTER" = 1 ]; then
  claude mcp remove --scope user davinci-resolve >/dev/null 2>&1 || true
  "${CMD[@]}"
fi
cat <<EOF

Next: open Resolve > Workspace > Scripts > Utility > CursorBridge.
The Console (Workspace > Console) should print "Bridge is running (read + write)". Version 2.0.0+cves1 = hardened.
If CursorBridge is missing from the menu or does nothing, install Python 3 from python.org (Resolve's
script runner looks for a system Python 3) and restart Resolve.
EOF
