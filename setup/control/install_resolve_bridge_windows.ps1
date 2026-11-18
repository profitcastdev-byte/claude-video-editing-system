# DaVinci Resolve (Free) control for CVES on Windows 10/11.
#   1. clones hiteshK03/davinci-resolve-mcp at the reviewed commit into %USERPROFILE%\.cves\mcp\davinci-resolve-mcp
#   2. makes its venv (MCP SDK only; -WithAI adds Whisper/Demucs/rembg, several GB, downloads models on use)
#   3. hardens CursorBridge.py (patch_cursorbridge.py) and copies it into Resolve's Scripts\Utility folder
#   4. prints (or with -Register runs) the Claude Code registration command
# Resolve itself is NOT installed here: its download needs Blackmagic's registration form.
#
# usage:  powershell -ExecutionPolicy Bypass -File setup\control\install_resolve_bridge_windows.ps1 [-WithAI] [-Register]
param([switch]$WithAI, [switch]$Register)
$ErrorActionPreference = "Stop"

$Repo = "https://github.com/hiteshK03/davinci-resolve-mcp.git"
$Pin  = "f812df7ab5d376592a24fb94611473fdf3a1acb2"   # reviewed 2026-11-18, see docs\CONTROL-MODE.md
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dest = Join-Path $env:USERPROFILE ".cves\mcp\davinci-resolve-mcp"
$Scripts = if ($env:CVES_RESOLVE_SCRIPTS_DIR) { $env:CVES_RESOLVE_SCRIPTS_DIR } else {
    Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility" }

function Find-Python {
    foreach ($c in @(@("py", "-3.12"), @("py", "-3"), @("python"))) {
        try { & $c[0] $c[1..9] --version *> $null; if ($LASTEXITCODE -eq 0) { return ,$c } } catch {}
    }
    throw "Python 3.10+ not found. Install Python 3.12 from python.org (tick 'Add to PATH')."
}
$Py = Find-Python
Write-Host "==> python: $($Py -join ' ')"

New-Item -ItemType Directory -Force (Join-Path $env:USERPROFILE ".cves\mcp") | Out-Null
if (-not (Test-Path (Join-Path $Dest ".git"))) { git clone --quiet $Repo $Dest }
git -C $Dest fetch --quiet origin
git -C $Dest -c advice.detachedHead=false checkout --quiet --detach $Pin
if ((git -C $Dest rev-parse HEAD).Trim() -ne $Pin) { throw "pin mismatch" }
Write-Host "==> davinci-resolve-mcp at $Pin"

& $Py[0] $Py[1..9] -m venv (Join-Path $Dest "venv")
$VPy = Join-Path $Dest "venv\Scripts\python.exe"
& $VPy -m pip install --quiet --upgrade pip
& $VPy -m pip install --quiet -c (Join-Path $Here "constraints-mcp.txt") mcp
if ($WithAI) { & $VPy -m pip install --quiet -c (Join-Path $Here "constraints-mcp.txt") -r (Join-Path $Dest "requirements.txt") }
Write-Host "==> venv ready: $VPy"

if (-not (Test-Path (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve")) -and -not $env:CVES_RESOLVE_SCRIPTS_DIR) {
    Write-Host "!!  DaVinci Resolve has not been run yet; installing the bridge anyway (it appears after install)."
}
New-Item -ItemType Directory -Force $Scripts | Out-Null
& $VPy (Join-Path $Here "patch_cursorbridge.py") (Join-Path $Dest "src\CursorBridge.py") (Join-Path $Scripts "CursorBridge.py")
if ($LASTEXITCODE -ne 0) { throw "bridge hardening failed" }

$Server = Join-Path $Dest "src\resolve_mcp_bridge.py"
Write-Host ""
Write-Host "Register with Claude Code (user scope):"
Write-Host "  claude mcp add --scope user davinci-resolve -- `"$VPy`" `"$Server`""
if ($Register) {
    claude mcp remove --scope user davinci-resolve 2>$null | Out-Null
    claude mcp add --scope user davinci-resolve -- $VPy $Server
}
Write-Host ""
Write-Host "Next: open Resolve > Workspace > Scripts > Utility > CursorBridge."
Write-Host "Workspace > Console should print 'Bridge is running (read + write)'. Version 2.0.0+cves1 = hardened."
Write-Host "If CursorBridge is missing or does nothing, install Python 3 from python.org for all users and restart Resolve."
