# Kdenlive control (fallback editor) for CVES on Windows 10/11.
#   1. installs Kdenlive (winget KDE.Kdenlive) unless present; it bundles melt
#   2. clones 12bijaya/MCP_Server_Kdenlive at the reviewed commit into %USERPROFILE%\.cves\mcp\kdenlive-mcp
#   3. hardens it (patch_kdenlive_mcp.py), makes its venv
#   4. installs the 1080x1920 23.976 Kdenlive profile CVES projects reference
#   5. prints (or with -Register runs) the Claude Code registration command
#
# usage:  powershell -ExecutionPolicy Bypass -File setup\control\install_kdenlive_mcp_windows.ps1 [-Register] [-Test]
param([switch]$Register, [switch]$Test)
$ErrorActionPreference = "Stop"

$Repo = "https://github.com/12bijaya/MCP_Server_Kdenlive.git"
$Pin  = "4733141efd1679fee29bfe0be481ab191eaf5f8f"   # reviewed 2026-11-18, see docs\CONTROL-MODE.md
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dest = Join-Path $env:USERPROFILE ".cves\mcp\kdenlive-mcp"
$Workspace = if ($env:CVES_CLIENTS) { $env:CVES_CLIENTS } else { Join-Path $env:USERPROFILE "CVES Projects" }

function Find-Kdenlive {
    foreach ($root in @("$env:ProgramFiles\kdenlive", "${env:ProgramFiles(x86)}\kdenlive", "$env:LOCALAPPDATA\Programs\kdenlive")) {
        $melt = Join-Path $root "bin\melt.exe"
        if (Test-Path $melt) { return $root }
    }
    return $null
}
$KRoot = Find-Kdenlive
if (-not $KRoot) {
    Write-Host "==> installing Kdenlive (winget install KDE.Kdenlive)"
    winget install --id KDE.Kdenlive -e --accept-package-agreements --accept-source-agreements
    $KRoot = Find-Kdenlive
    if (-not $KRoot) { throw "Kdenlive installed but melt.exe not found; set KDENLIVE_MCP_MELT by hand" }
}
$Melt = Join-Path $KRoot "bin\melt.exe"
$Effects = (Get-ChildItem -Path $KRoot -Recurse -Directory -Filter effects -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "kdenlive" } | Select-Object -First 1).FullName
Write-Host "==> Kdenlive at $KRoot (melt: $Melt, effects: $Effects)"

function Find-Python {
    foreach ($c in @(@("py", "-3.12"), @("py", "-3"), @("python"))) {
        try { & $c[0] $c[1..9] --version *> $null; if ($LASTEXITCODE -eq 0) { return ,$c } } catch {}
    }
    throw "Python 3.10+ not found. Install Python 3.12 from python.org (tick 'Add to PATH')."
}
$Py = Find-Python

New-Item -ItemType Directory -Force (Join-Path $env:USERPROFILE ".cves\mcp") | Out-Null
if (-not (Test-Path (Join-Path $Dest ".git"))) { git clone --quiet $Repo $Dest }
git -C $Dest fetch --quiet origin
git -C $Dest checkout --quiet -- .
git -C $Dest -c advice.detachedHead=false checkout --quiet --detach $Pin
if ((git -C $Dest rev-parse HEAD).Trim() -ne $Pin) { throw "pin mismatch" }
Write-Host "==> kdenlive-mcp at $Pin"
& $Py[0] $Py[1..9] (Join-Path $Here "patch_kdenlive_mcp.py") $Dest
if ($LASTEXITCODE -ne 0) { throw "hardening failed" }

& $Py[0] $Py[1..9] -m venv (Join-Path $Dest ".venv")
$VPy = Join-Path $Dest ".venv\Scripts\python.exe"
& $VPy -m pip install --quiet --upgrade pip
$Spec = if ($Test) { "$Dest[dev]" } else { $Dest }
& $VPy -m pip install --quiet -c (Join-Path $Here "constraints-mcp.txt") -e $Spec
$Exe = Join-Path $Dest ".venv\Scripts\kdenlive-mcp.exe"
Write-Host "==> venv ready: $Exe"

# Kdenlive custom profile (QStandardPaths::AppDataLocation = %APPDATA%\kdenlive)
$Profiles = Join-Path $env:APPDATA "kdenlive\profiles"
New-Item -ItemType Directory -Force $Profiles | Out-Null
$KProfile = Join-Path $Profiles "cves_vertical_hd_2398"
@"
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
"@ | Set-Content -Encoding ascii -NoNewline:$false $KProfile
Write-Host "==> Kdenlive profile: $KProfile"
New-Item -ItemType Directory -Force $Workspace | Out-Null

if ($Test) {
    Push-Location $Dest
    $env:KDENLIVE_MCP_MELT = $Melt; $env:KDENLIVE_MCP_EFFECTS_DIR = $Effects
    & $VPy -m pytest -q tests\unit
    Write-Host "(expected: test_import_export_srt_files fails; it exports outside the workspace, which the hardening refuses)"
    Pop-Location
}

Write-Host ""
Write-Host "Register with Claude Code (user scope):"
Write-Host "  claude mcp add --scope user kdenlive -e `"KDENLIVE_MCP_WORKSPACE=$Workspace`" -e `"KDENLIVE_MCP_MELT=$Melt`" -e `"KDENLIVE_MCP_EFFECTS_DIR=$Effects`" -e `"KDENLIVE_MCP_CUSTOM_PROFILE=$KProfile`" -- `"$Exe`""
if ($Register) {
    claude mcp remove --scope user kdenlive 2>$null | Out-Null
    claude mcp add --scope user kdenlive -e "KDENLIVE_MCP_WORKSPACE=$Workspace" -e "KDENLIVE_MCP_MELT=$Melt" `
        -e "KDENLIVE_MCP_EFFECTS_DIR=$Effects" -e "KDENLIVE_MCP_CUSTOM_PROFILE=$KProfile" -- $Exe
}
