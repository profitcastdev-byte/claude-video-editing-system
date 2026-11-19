<#
CVES one-shot installer for Windows 10/11 (x64). Idempotent: re-run it any time.

  powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1
  powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1 -NoModels        # skip ~700 MB downloads
  powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1 -ForceCpu        # CPU torch even with an NVIDIA GPU
  powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1 -RewriteConfig   # regenerate %USERPROFILE%\.cves\config.yaml

Layout (the path contract in engine\cves\config.py):
  %USERPROFILE%\.cves\bin\         ffmpeg.exe, ffprobe.exe (gyan.dev FULL build), whisper-cli.exe + DLLs, cves.cmd
  %USERPROFILE%\.cves\models\      ggml-large-v3-turbo-q5_0.bin, rvm_resnet50.pth, face_detection_yunet_2023mar.onnx
  %USERPROFILE%\.cves\rvm\         clone of PeterL1n/RobustVideoMatting (pinned commit)
  %USERPROFILE%\.cves\venv\        Python 3.12 main venv (CUDA torch if nvidia-smi works, else CPU torch)
  %USERPROFILE%\.cves\venv-voice\  Python 3.11 + deepfilternet (Scripts\deepFilter.exe)
  %USERPROFILE%\.cves\config.yaml  absolute paths for every key in cves.config.DEFAULTS

STATUS: written on a Mac and NOT yet run on Windows. Sections marked [UNTESTED] are the ones most likely to need a
fix on the first real run (asset names, install folders). Report problems in the team channel / a PR.
Needs: Windows 10 1809+ (winget + curl.exe + tar.exe ship with it), ~8 GB free disk, no admin rights.
#>
[CmdletBinding()]
param([switch]$NoModels, [switch]$ForceCpu, [switch]$RewriteConfig)

# "Continue", not "Stop": under Windows PowerShell 5.1, "Stop" turns any stderr line from a native tool (git, uv,
# winget progress) into a terminating error. Native exit codes are checked explicitly; cmdlets use -ErrorAction Stop.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"   # Invoke-WebRequest is 10x slower with the progress bar
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo = Split-Path -Parent $PSScriptRoot
$Cves = if ($env:CVES_HOME) { $env:CVES_HOME } else { Join-Path $env:USERPROFILE ".cves" }
$Bin = Join-Path $Cves "bin"; $Models = Join-Path $Cves "models"

# ---- pinned sources (same as install_mac.sh) -----------------------------------------------------------
$RvmGit = "https://github.com/PeterL1n/RobustVideoMatting.git"
$RvmCommit = "53d74c6826735f01f4406b5ca9075eee27bec094"
$ModelPins = @(
  @{ Name = "ggml-large-v3-turbo-q5_0.bin"; Url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"; Sha = "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2" },
  @{ Name = "rvm_resnet50.pth"; Url = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_resnet50.pth"; Sha = "c191a807251164c073dce5fa408e7a816070d539b882b2a3150330a9fec112ce" },
  @{ Name = "face_detection_yunet_2023mar.onnx"; Url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"; Sha = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4" }
)
$TorchVer = "2.15.0"; $TorchVisionVer = "0.29.2"
$TorchCudaIndex = "https://download.pytorch.org/whl/cu132"   # torch 2.15.0 wheels exist for cu132 and cu134 (checked 2026-11-18)
$TorchCpuIndex = "https://download.pytorch.org/whl/cpu"
$VoicePkgs = @("deepfilternet==0.5.6", "torch==2.1.1", "torchaudio==2.1.1", "numpy==1.26.2", "soundfile==0.12.1")
$EarshotSrc = "earshot[mcp] @ git+https://github.com/Leonxlnx/earshot"
$WingetPkgs = @(
  @{ Id = "Git.Git"; Cmd = "git" },
  @{ Id = "GitHub.GitLFS"; Cmd = "git-lfs" },
  @{ Id = "astral-sh.uv"; Cmd = "uv" },
  @{ Id = "yt-dlp.yt-dlp"; Cmd = "yt-dlp" },
  @{ Id = "Gyan.FFmpeg"; Cmd = $null }          # gyan.dev FULL build (has drawtext + rubberband); NOT Gyan.FFmpeg.Essentials
)

function Say($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m) { Write-Host "    ok  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    !!  $m" -ForegroundColor Yellow }
function Die($m) { Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Get-Sha($p) { (Get-FileHash -Algorithm SHA256 -Path $p).Hash.ToLower() }
function Invoke-Checked([string]$exe, [string[]]$argv) {
  & $exe @argv
  if ($LASTEXITCODE -ne 0) { Die "$exe $($argv -join ' ') failed (exit $LASTEXITCODE)" }
}

# ---- 0. platform ------------------------------------------------------------------------------------------
Say "Checking platform"
if (-not [Environment]::Is64BitOperatingSystem) { Die "64-bit Windows required" }
$build = [Environment]::OSVersion.Version.Build
if ($build -lt 17763) { Die "Windows 10 1809 (build 17763) or newer required; this is build $build" }
Ok "Windows build $build"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Die "winget not found. Install 'App Installer' from the Microsoft Store (https://aka.ms/getwinget), then re-run."
}
New-Item -ItemType Directory -Force -Path $Cves, $Bin, $Models | Out-Null

# ---- 1. winget packages -----------------------------------------------------------------------------------
Say "winget packages"
foreach ($p in $WingetPkgs) {
  $listed = winget list --id $p.Id --exact --accept-source-agreements 2>$null | Select-String -SimpleMatch $p.Id
  if ($listed) { Ok "$($p.Id) (installed)"; continue }
  Write-Host "    installing $($p.Id) ..."
  winget install --id $p.Id --exact --silent --scope user --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) {
    # some packages have no user-scope installer; retry with the default scope (may show a UAC prompt)
    winget install --id $p.Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { Warn "winget install $($p.Id) failed (exit $LASTEXITCODE); continuing, fallbacks below" }
  }
}
Refresh-Path
foreach ($c in @("git", "uv")) { if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { Die "$c not on PATH after install; open a new PowerShell and re-run" } }
git lfs install --skip-repo | Out-Null; Ok "git-lfs hooks (user level)"
$Uv = (Get-Command uv).Source

# ---- 2. ffmpeg FULL build -> .cves\bin ------------------------------------------------------- [UNTESTED]
Say "ffmpeg (gyan.dev full build) -> $Bin"
$ffSrc = $null
$wingetPkgDir = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
if (Test-Path $wingetPkgDir) {
  $ffSrc = Get-ChildItem -Path $wingetPkgDir -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "Gyan\.FFmpeg_" -and $_.FullName -match "full_build" } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if (-not $ffSrc) {
  # Fallback: the gyan.dev builds mirrored on GitHub (GyanD/codexffmpeg), *-full_build.zip
  Warn "winget ffmpeg not found; downloading the full build zip from GyanD/codexffmpeg"
  $rel = Invoke-RestMethod -ErrorAction Stop -Uri "https://api.github.com/repos/GyanD/codexffmpeg/releases/latest" -Headers @{ "User-Agent" = "cves-installer" }
  $asset = $rel.assets | Where-Object { $_.name -match "^ffmpeg-.*-full_build\.zip$" } | Select-Object -First 1
  if (-not $asset) { Die "no full_build.zip in GyanD/codexffmpeg $($rel.tag_name)" }
  $zip = Join-Path $env:TEMP $asset.name
  curl.exe -fL --retry 3 -o $zip $asset.browser_download_url; if ($LASTEXITCODE -ne 0) { Die "ffmpeg download failed" }
  $dst = Join-Path $Cves "ffmpeg"; Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue
  Expand-Archive -ErrorAction Stop -Path $zip -DestinationPath $dst -Force
  $ffSrc = Get-ChildItem -Path $dst -Recurse -Filter ffmpeg.exe | Select-Object -First 1
}
if (-not $ffSrc) { Die "could not find an ffmpeg full build" }
Copy-Item -ErrorAction Stop -Force (Join-Path $ffSrc.DirectoryName "ffmpeg.exe") $Bin
Copy-Item -ErrorAction Stop -Force (Join-Path $ffSrc.DirectoryName "ffprobe.exe") $Bin
$filters = & (Join-Path $Bin "ffmpeg.exe") -hide_banner -filters 2>$null | Out-String
if ($filters -notmatch "\sdrawtext\s") { Die "ffmpeg has no drawtext: this is the essentials build, install Gyan.FFmpeg (full)" }
if ($filters -notmatch "\srubberband\s") { Die "ffmpeg has no rubberband filter: install the gyan.dev FULL build" }
Ok "ffmpeg from $($ffSrc.DirectoryName) (drawtext + rubberband present)"

# ---- 3. GPU detection ---------------------------------------------------------------------------------------
$HasNvidia = $false
if (-not $ForceCpu -and (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
  & nvidia-smi -L 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $HasNvidia = $true }
}
if ($HasNvidia) { Ok "NVIDIA GPU: $((& nvidia-smi --query-gpu=name,driver_version --format=csv,noheader) -join '; ')" }
else { Warn "no usable NVIDIA GPU (or -ForceCpu): CPU torch, CPU whisper. Matting will be slow but works." }

# ---- 4. whisper.cpp release binaries -> .cves\bin ------------------------------------------------- [UNTESTED]
Say "whisper.cpp (release binaries) -> $Bin"
if (Test-Path (Join-Path $Bin "whisper-cli.exe")) { Ok "whisper-cli.exe present" }
else {
  # Binaries are attached to the bNNNN build releases, not to the vX.Y.Z tags; take the newest release that has them.
  $rels = Invoke-RestMethod -ErrorAction Stop -Uri "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=15" -Headers @{ "User-Agent" = "cves-installer" }
  $want = if ($HasNvidia) { "^whisper-bin-win-cuda-12\.\d+\.\d+-x64\.zip$" } else { "^whisper-bin-x64\.zip$" }
  $asset = $null
  foreach ($r in $rels) { $asset = $r.assets | Where-Object { $_.name -match $want } | Select-Object -First 1; if ($asset) { Ok "release $($r.tag_name): $($asset.name)"; break } }
  if (-not $asset -and $HasNvidia) {
    Warn "no CUDA build found; using the CPU build"
    foreach ($r in $rels) { $asset = $r.assets | Where-Object { $_.name -eq "whisper-bin-x64.zip" } | Select-Object -First 1; if ($asset) { break } }
  }
  if (-not $asset) { Die "no whisper.cpp Windows binaries found in the last 15 releases" }
  $zip = Join-Path $env:TEMP $asset.name
  curl.exe -fL --retry 3 -o $zip $asset.browser_download_url; if ($LASTEXITCODE -ne 0) { Die "whisper.cpp download failed" }
  $tmp = Join-Path $env:TEMP "whisper-cpp-x"; Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
  Expand-Archive -ErrorAction Stop -Path $zip -DestinationPath $tmp -Force
  $cli = Get-ChildItem -Path $tmp -Recurse -Filter whisper-cli.exe | Select-Object -First 1
  if (-not $cli) { Die "whisper-cli.exe not in $($asset.name)" }
  Copy-Item -ErrorAction Stop -Force (Join-Path $cli.DirectoryName "*.exe") $Bin   # brings whisper-cli + helpers
  Copy-Item -ErrorAction Stop -Force (Join-Path $cli.DirectoryName "*.dll") $Bin   # whisper.dll, ggml*.dll (+ CUDA runtime DLLs in the CUDA zip)
  Ok "whisper-cli.exe installed"
}
& (Join-Path $Bin "whisper-cli.exe") --help 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Warn "whisper-cli.exe did not start (missing DLL / CUDA runtime?). Delete $Bin\whisper-cli.exe and re-run with -ForceCpu." }

# ---- 5. Python via uv -----------------------------------------------------------------------------------------
Say "Python 3.12 + 3.11 (uv-managed, no admin)"
Invoke-Checked $Uv @("python", "install", "3.12", "3.11")

# ---- 6. main venv ------------------------------------------------------------------------------------------------
$Venv = Join-Path $Cves "venv"; $Py = Join-Path $Venv "Scripts\python.exe"
Say "Main venv (Python 3.12) at $Venv"
$needVenv = $true
if (Test-Path $Py) { & $Py -c "import sys; sys.exit(sys.version_info[:2] != (3, 12))"; if ($LASTEXITCODE -eq 0) { $needVenv = $false } }
if ($needVenv) { Remove-Item -Recurse -Force $Venv -ErrorAction SilentlyContinue; Invoke-Checked $Uv @("venv", "--python", "3.12", $Venv) }
# torch FIRST from the PyTorch index, so requirements.txt's torch==2.15.0 pin is already satisfied by +cu132 / +cpu
$idx = if ($HasNvidia) { $TorchCudaIndex } else { $TorchCpuIndex }
Invoke-Checked $Uv @("pip", "install", "--python", $Py, "--index-url", $idx, "torch==$TorchVer", "torchvision==$TorchVisionVer")
Invoke-Checked $Uv @("pip", "install", "--python", $Py, "-r", (Join-Path $Repo "setup\requirements.txt"))
Invoke-Checked $Uv @("pip", "install", "--python", $Py, "-e", (Join-Path $Repo "engine"))
# [UNTESTED] guard: if the requirements step swapped CUDA torch for the PyPI CPU wheel, put the CUDA one back
if ($HasNvidia) {
  & $Py -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)"
  if ($LASTEXITCODE -ne 0) {
    Warn "torch lost CUDA; reinstalling from $TorchCudaIndex"
    Invoke-Checked $Uv @("pip", "install", "--python", $Py, "--reinstall-package", "torch", "--reinstall-package", "torchvision", "--index-url", $TorchCudaIndex, "torch==$TorchVer", "torchvision==$TorchVisionVer")
  }
}
& $Py -c "import torch; print('    torch', torch.__version__, 'CUDA available:', torch.cuda.is_available())"
# motion layer: the Chromium build Playwright drives (idempotent: an installed build is skipped)
Invoke-Checked $Py @("-m", "playwright", "install", "chromium"); Ok "Chromium for motion pieces (playwright)"
Set-Content -Path (Join-Path $Bin "cves.cmd") -Value "@echo off`r`n`"$Venv\Scripts\cves.exe`" %*" -Encoding ASCII

# ---- 7. voice venv -------------------------------------------------------------------------------------------------
$VVenv = Join-Path $Cves "venv-voice"; $VPy = Join-Path $VVenv "Scripts\python.exe"
Say "Voice venv (Python 3.11, deepfilternet) at $VVenv"
$needV = $true
if (Test-Path $VPy) { & $VPy -c "import sys; sys.exit(sys.version_info[:2] != (3, 11))"; if ($LASTEXITCODE -eq 0) { $needV = $false } }
if ($needV) { Remove-Item -Recurse -Force $VVenv -ErrorAction SilentlyContinue; Invoke-Checked $Uv @("venv", "--python", "3.11", $VVenv) }
Invoke-Checked $Uv (@("pip", "install", "--python", $VPy) + $VoicePkgs)
if (-not (Test-Path (Join-Path $VVenv "Scripts\deepFilter.exe"))) { Die "deepFilter.exe missing in $VVenv\Scripts" }
Ok "deepFilter.exe"
# Resemble Enhance is deliberately NOT installed (its generative mode rewrote words).

# ---- 8. RVM code ------------------------------------------------------------------------------------------------------
$Rvm = Join-Path $Cves "rvm"
Say "Robust Video Matting code at $Rvm"
if (-not (Test-Path (Join-Path $Rvm ".git"))) { Invoke-Checked git @("clone", "--quiet", $RvmGit, $Rvm) }
git -C $Rvm fetch --quiet origin 2>$null
Invoke-Checked git @("-C", $Rvm, "-c", "advice.detachedHead=false", "checkout", "--quiet", $RvmCommit)
Ok "RVM @ $($RvmCommit.Substring(0,7))"

# ---- 9. models -----------------------------------------------------------------------------------------------------------
if ($NoModels) { Say "Skipping models (-NoModels)" }
else {
  Say "Models in $Models"
  foreach ($m in $ModelPins) {
    $dest = Join-Path $Models $m.Name
    if ((Test-Path $dest) -and ((Get-Sha $dest) -eq $m.Sha)) { Ok "$($m.Name) (present)"; continue }
    Write-Host "    downloading $($m.Name) ..."
    $part = "$dest.part"
    curl.exe -fL --retry 3 -C - -o $part $m.Url
    if ($LASTEXITCODE -ne 0) { Die "download failed: $($m.Url)" }
    if ((Get-Sha $part) -ne $m.Sha) { Remove-Item -Force $part; Die "checksum mismatch for $($m.Name)" }
    Move-Item -Force $part $dest; Ok "$($m.Name) (downloaded)"
  }
}

# ---- 10. earshot ------------------------------------------------------------------------------------------------------------
Say "earshot (uv tool)"
$tools = & $Uv tool list 2>$null | Out-String
if ($tools -match "(?m)^earshot ") { Ok "earshot installed" } else { Invoke-Checked $Uv @("tool", "install", $EarshotSrc) }
& $Uv tool update-shell 2>$null | Out-Null
$UvToolBin = (& $Uv tool dir --bin 2>$null | Out-String).Trim()

# ---- 11. config.yaml ----------------------------------------------------------------------------------------------------------
Say "Config"
$Cfg = Join-Path $Cves "config.yaml"
if ((Test-Path $Cfg) -and -not $RewriteConfig) { Ok "$Cfg exists, left as is (use -RewriteConfig to regenerate)" }
else {
  $earshotExe = Join-Path $UvToolBin "earshot.exe"
  # single-quoted YAML scalars: backslashes are literal
  $lines = @(
    "# Written by setup/install_windows.ps1 on $(Get-Date -Format yyyy-MM-dd). Env vars CVES_<KEY> override any line.",
    "ffmpeg: '$Bin\ffmpeg.exe'",
    "ffprobe: '$Bin\ffprobe.exe'",
    "whisper: '$Bin\whisper-cli.exe'",
    "deepfilter: '$VVenv\Scripts\deepFilter.exe'",
    "earshot: '$earshotExe'",
    "whisper_model: '$Models\ggml-large-v3-turbo-q5_0.bin'",
    "rvm_repo: '$Rvm'",
    "rvm_weights: '$Models\rvm_resnet50.pth'",
    "yunet: '$Models\face_detection_yunet_2023mar.onnx'"
  )
  [IO.File]::WriteAllLines($Cfg, $lines)   # UTF-8 without BOM (PS 5.1 Set-Content would add one)
  Ok "wrote $Cfg"
}

# ---- 12. PATH (user scope) ------------------------------------------------------------------------------------------------------
Say "PATH"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User"); if (-not $userPath) { $userPath = "" }
$add = @($Bin, $UvToolBin) | Where-Object { $_ -and ($userPath -split ";") -notcontains $_ }
if ($add) {
  [Environment]::SetEnvironmentVariable("Path", (($add -join ";") + ";" + $userPath).TrimEnd(";"), "User")
  Ok "added to user PATH: $($add -join ', ') (open a new terminal)"
} else { Ok "user PATH already has $Bin" }
Refresh-Path

# ---- 13. doctor ------------------------------------------------------------------------------------------------------------------
Say "Running doctor"
Write-Host "Installing Claude Code plugins and skills (setup\skills.json)"
& $Py (Join-Path $Repo "setup\install_skills.py")
& $Py (Join-Path $Repo "setup\doctor.py")
if ($LASTEXITCODE -ne 0) { Die "doctor found problems: fix the FAIL rows above, then re-run this script" }
Write-Host "`nCVES is installed. Open a NEW terminal and run:  cves doctor" -ForegroundColor Green
