# Install CVES

One installer per platform. It is safe to re-run: it skips what is done and repairs what is broken, then runs
`doctor.py`, which must end with **0 fail**.

| | Mac | Windows |
|---|---|---|
| Supported | Apple Silicon, macOS 14 Sonoma or newer | Windows 10 1809+ / 11, x64 |
| GPU for matting | MPS (built in) | CUDA if an NVIDIA GPU + recent driver, else CPU |
| Installer | `bash setup/install_mac.sh` | `powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1` |
| Status | tested end to end on 2026-11-18 | **written but not yet run on Windows**: see "Windows notes" |
| Disk / time | ~8 GB, 10-20 min (most of it is torch + the 574 MB whisper model) | same |

## 1. Prerequisites (once per machine)
1. **Claude Code**, signed in with your Claude account: https://docs.claude.com/claude-code
2. **git**. Mac: `xcode-select --install`. Windows: `winget install Git.Git`.
3. **No GitHub account needed**: the repo is public (`git clone https://github.com/profitcastdev-byte/claude-video-editing-system`). Never paste a token or API key into a file in the repo.
4. **Mac only: Homebrew** (it asks for your password, so run it yourself, not through Claude):
   `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
5. **Windows only: winget** ("App Installer" from the Microsoft Store). It ships with Windows 11.

## 2. Ask Claude Code to install it
Clone the repo, open Claude Code in the folder, and paste this prompt:

```
Install this system using INSTALL.md. Read INSTALL.md and docs/ARCHITECTURE.md first.
Detect my OS. On macOS run `bash setup/install_mac.sh`; on Windows run
`powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1`. If the installer stops,
read the error, fix the cause using the Troubleshooting section of INSTALL.md, and re-run it
(it is idempotent) until the doctor prints 0 fail. Do not run anything that needs my password
or admin rights: tell me the command and wait. Do not commit anything. Then install the cves
plugin (section 4), list which optional connectors I have (section 5), and show me the final
`cves doctor` table.
```

## 3. Or install it by hand
```bash
git clone https://github.com/profitcastdev-byte/claude-video-editing-system claude-video-editing-system
cd claude-video-editing-system
```
**Mac**
```bash
bash setup/install_mac.sh            # options: --no-models, --rewrite-config, --no-path
source ~/.zprofile                   # or open a new terminal
cves doctor                          # add --deep to verify model checksums and load RVM
```
**Windows** (PowerShell, not as administrator)
```powershell
powershell -ExecutionPolicy Bypass -File setup\install_windows.ps1   # options: -NoModels, -ForceCpu, -RewriteConfig
# open a NEW terminal so the PATH change applies
cves doctor
```

### What the installer puts where
Everything lives in `~/.cves` (`%USERPROFILE%\.cves` on Windows). That is the path contract in `engine/cves/config.py`:

| Path | What |
|---|---|
| `bin/` | `ffmpeg`, `ffprobe`, `whisper-cli`, `cves`. Mac: symlinks to Homebrew `ffmpeg-full` and `whisper.cpp`. Windows: the gyan.dev full-build and whisper.cpp release `.exe` files |
| `models/` | `ggml-large-v3-turbo-q5_0.bin` (whisper), `rvm_resnet50.pth` (matting), `face_detection_yunet_2023mar.onnx` (faces); sha256-checked |
| `rvm/` | clone of PeterL1n/RobustVideoMatting at commit `53d74c6`; the engine imports `model` from it |
| `venv/` | Python 3.12: torch, opencv, PyAV, librosa, OTIO and the engine (`pip install -e engine`), pinned in `setup/requirements.txt` |
| `venv-voice/` | Python 3.11 with `deepfilternet` 0.5.6 (`deepFilter` CLI). It is separate because it needs torch < 2.2 and numpy < 2 |
| `config.yaml` | absolute paths for every tool and model. Edit a line to point at a non-default location, or set env `CVES_<KEY>` (e.g. `CVES_FFMPEG`) |

Also installed: `earshot` (`uv tool install "earshot[mcp] @ git+https://github.com/Leonxlnx/earshot"`), `yt-dlp`, `git-lfs`, `uv`,
and `rsvg-convert` (Mac). A Mac that already has models in the old places (`~/.cache/whisper-cpp`, `~/apps/matting/rvm`) gets
them copied (APFS clone, no extra disk) instead of downloaded.

## 4. Install the Claude Code plugin (from `plugin/`)
The repo is also a plugin marketplace called `cves` (`.claude-plugin/marketplace.json`). In Claude Code:
```
/plugin marketplace add profitcastdev-byte/claude-video-editing-system
/plugin install cves@cves
```
Restart Claude Code. You now have the `video-editor` skill and the `/cves:*` commands, and they work from any folder.
`/cves:install` re-runs this install and the doctor. `/cves:update` pulls the repo and re-runs the doctor.
`/plugin marketplace update cves` updates the plugin. To try local plugin changes without installing them:
`claude --plugin-dir ./plugin`.

Optional plugins and skills (superpowers, real-sfx, real-sound, earshot, remotion, hyperframes) are listed with
their install commands in [TOOLS-REGISTRY.md](TOOLS-REGISTRY.md). CVES runs without them.

## 5. Optional connectors and apps
None of these is needed for a first edit. Keys never go into this repo: connectors keep their own auth.

| What | Used for | How to connect |
|---|---|---|
| **ElevenLabs** (Claude connector) | music beds, SFX, voice fixes | claude.ai > Settings > Connectors > ElevenLabs. Claude Code sees connectors from the same account. `cves music generate ...` prints the exact tool call for Claude to make; there is no API key in code |
| **Magnific** (Claude connector) | image upscale / relight; music via `audio_music_generate` | claude.ai > Settings > Connectors > Magnific. Its image-generation tools did not load in Claude Code (200-tool limit). Re-test before relying on them; see the registry |
| **Openverse** | CC0 / CC BY music + SFX search | nothing to install, no key: `cves music search "upbeat" --kind music --min 30 --max 90`. Optional `OPENVERSE_TOKEN` env var for a higher rate limit |
| **Apify** (connector or MCP) | research: scrape competitor ads, reels, reviews | claude.ai connector, or `claude mcp add --transport http apify https://mcp.apify.com` (it asks for your Apify token in the browser) |
| **DaVinci Resolve (Free)** | control mode: Claude drives the timeline live | manual download from https://www.blackmagicdesign.com/products/davinciresolve (pick the free "DaVinci Resolve", not Studio). Then follow [docs/CONTROL-MODE.md](docs/CONTROL-MODE.md) to install the bridge |
| **Kdenlive** | control mode, open source | Mac: `brew install --cask kdenlive`. Windows: `winget install KDE.Kdenlive`. MCP setup is in [docs/CONTROL-MODE.md](docs/CONTROL-MODE.md) |

Control mode (Resolve / Kdenlive MCP servers, the hardened bridge, what Claude can change live) is documented in
**[docs/CONTROL-MODE.md](docs/CONTROL-MODE.md)**. Its setup scripts are in `setup/control/`.

## 6. Verify
```
cves doctor          # every dependency, model, GPU backend, font and asset: PASS / WARN / FAIL + a fix hint per row
cves doctor --deep   # also sha256 of each model and a real RVM weight load (about 10 s)
```
FAIL rows block editing. WARN rows are fine to start with (e.g. CPU-only torch on a laptop without NVIDIA, `cves`
not on PATH until you open a new terminal). The doctor exits 1 if anything FAILs, so Claude can loop on it.

## 7. Troubleshooting (known gotchas)
| Symptom | Cause | Fix |
|---|---|---|
| `No such filter: 'drawtext'` or `'rubberband'` | the plain Homebrew `ffmpeg` formula (or the gyan.dev *essentials* build) lacks them | Mac: `brew install ffmpeg-full`. It is keg-only, so the engine uses it by path through `~/.cves/bin/ffmpeg` -> `$(brew --prefix)/opt/ffmpeg-full/bin/ffmpeg`. Never `brew link` it over `ffmpeg`. Windows: `winget install Gyan.FFmpeg` (full), not `Gyan.FFmpeg.Essentials` |
| `ffmpeg-full` formula not found (old Homebrew) | before it reached homebrew/core | `brew update`, or `brew tap homebrew-ffmpeg/ffmpeg && brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-rubberband` (the installer tries this itself) |
| Doctor finds `ffmpeg` but filters FAIL | your PATH or `config.yaml` points at another ffmpeg | `ls -l ~/.cves/bin/ffmpeg`; remove the `ffmpeg:` line from `~/.cves/config.yaml` or fix it |
| `remotion` / `npx remotion` not found | Remotion is a global npm install, not on the default PATH | only needed for the optional remotion skills: `npm i -g @remotion/cli` |
| torch install fails: no wheel for `macosx_13_0_arm64` | torch 2.15 needs macOS 14+ | update macOS to Sonoma or newer |
| Doctor: `torch backend WARN CPU only` on a Windows PC with NVIDIA | CPU wheel installed, or a driver too old for CUDA 13.2 | update the NVIDIA driver, re-run `install_windows.ps1` (it picks `cu132` when `nvidia-smi` works). `-ForceCpu` keeps CPU |
| `objc: Class AVFFrameReceiver is implemented in both ... cv2 ... av` | opencv and PyAV each bundle libavdevice | harmless warning; we never use the camera capture classes |
| `deepFilter` missing / numpy errors in the voice step | deepfilternet installed into the main venv | it must stay in `~/.cves/venv-voice` (Python 3.11, numpy 1.26). Re-run the installer |
| Someone suggests Resemble Enhance for voice | its generative mode rewrote words in a real take | banned. Use DeepFilterNet only (see TOOLS-REGISTRY) |
| whisper model download stalls | 574 MB from Hugging Face | re-run: downloads resume (`curl -C -`) and are checksum-verified |
| Openverse `HTTP 429` | the anonymous rate limit | wait a minute, or set `OPENVERSE_TOKEN` |
| Windows: `running scripts is disabled on this system` | PowerShell execution policy | run the installer with `powershell -ExecutionPolicy Bypass -File ...` as shown, not by double-clicking |
| Windows: `cves` not found right after install | the user PATH changes only in new terminals | open a new terminal, or run `%USERPROFILE%\.cves\bin\cves.cmd doctor` |
| Windows: `whisper-cli.exe did not start` | the CUDA build cannot find CUDA runtime DLLs | delete `%USERPROFILE%\.cves\bin\whisper-cli.exe` and re-run with `-ForceCpu` (CPU whisper is fine for 60 s ads) |
| `cves` works but uses old paths | a stale `~/.cves/config.yaml` | `bash setup/install_mac.sh --rewrite-config` / `-RewriteConfig` |

### Windows notes (untested parts)
The Windows installer was written on a Mac and has not run on Windows yet. The parts marked `[UNTESTED]` in it are
the ffmpeg discovery in the winget package folder, the whisper.cpp release asset names, and keeping CUDA torch
after `requirements.txt`. If one fails, fix the script, note it in CHANGELOG.md, and open a PR (see CONTRIBUTING.md).

## 8. Uninstall
Delete `~/.cves` (`%USERPROFILE%\.cves`) and remove the `# CVES` line from `~/.zprofile` (Windows: remove the two
`.cves\bin` / uv tool entries from the user PATH). Then `uv tool uninstall earshot` and `/plugin uninstall cves@cves`.
Homebrew / winget packages stay. Remove them yourself if you don't need them.
