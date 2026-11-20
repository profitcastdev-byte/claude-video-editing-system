# Tools registry

The living list of every binary, model, package, plugin, skill, connector and MCP server CVES uses or has
evaluated. **Any PR that adds, removes or upgrades a tool updates this file and CHANGELOG.md** (see CONTRIBUTING.md).

Status: **core** = installed by `setup/` and needed for an edit · **optional** = improves a step, CVES works without it ·
**evaluated** = tried, not adopted (yet) · **rejected** = do not use (reason given).
Versions are the ones on the reference Mac on 2026-11-18.

## 1. Local engine
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| ffmpeg-full 9.0.2 | decode/encode, filters (drawtext, rubberband, subtitles, loudnorm), ProRes for control mode | https://formulae.brew.sh/formula/ffmpeg-full · Win: https://www.gyan.dev/ffmpeg/builds/ | core | Mac `brew install ffmpeg-full` (keg-only, used by path via `~/.cves/bin/ffmpeg`). Win `winget install Gyan.FFmpeg` (full build) | The plain `ffmpeg` formula and gyan "essentials" lack drawtext + rubberband. The doctor checks both filters |
| whisper.cpp 1.9.5 (`whisper-cli`) | word-level transcription | https://github.com/ggml-org/whisper.cpp | core | Mac `brew install whisper.cpp`. Win: release zip `whisper-bin-x64.zip` / `whisper-bin-win-cuda-12.x-x64.zip` | Binaries are attached to the `bNNNN` build releases, not the `vX.Y.Z` tags |
| ggml-large-v3-turbo-q5_0.bin | whisper model (574 MB) | https://huggingface.co/ggerganov/whisper.cpp | core | installer, sha256 `394221709cd5...7e2` | `~/.cves/models/` |
| Robust Video Matting (code @ `53d74c6`) | person matte for roto (behind-the-head) templates | https://github.com/PeterL1n/RobustVideoMatting | core | installer clones into `~/.cves/rvm` | GPL-3.0 code, run locally; we don't redistribute it |
| rvm_resnet50.pth | RVM weights (108 MB) | https://github.com/PeterL1n/RobustVideoMatting/releases/tag/v1.0.0 | core | installer, sha256 `c191a807...12ce` | `rvm_mobilenetv3.pth` (same release) is lighter; not used by the engine |
| YuNet `face_detection_yunet_2023mar.onnx` | face boxes + landmarks (faces.json, tracking) | https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet | core | installer, sha256 `8f2383e4...2fa4` | MIT |
| Python 3.12 main venv | matting, render, mix, QC, export | `setup/requirements.txt` | core | installer (`uv venv`) | torch 2.15.0 (MPS / CUDA cu132 / CPU), torchvision 0.29.2, numpy 2.5.5, opencv-python 5.0.0.93, av 19.0.2, pillow 13.0.0, soundfile 0.14.0, scipy 1.18.1, librosa 1.0.1, pyyaml 6.0.3, opentimelineio 0.18.1, onnxruntime 1.32.0 |
| OTIO adapters | `.kdenlive` and FCPXML export | https://pypi.org/project/otio-kdenlive-adapter/ · https://pypi.org/project/otio-fcpx-xml-adapter/ | core | in requirements.txt | split out of OTIO core since 0.16 |
| DeepFilterNet 0.5.6 (`deepFilter`) | voice denoise (non-generative: does not change words) | https://github.com/Rikorose/DeepFilterNet | core | installer: Python 3.11 venv `~/.cves/venv-voice` | needs torch 2.1.1 + numpy 1.26.2, hence its own venv |
| earshot 0.4.1 | "ears" for Claude: judge, compare and verify audio and mixes | https://github.com/Leonxlnx/earshot | core | `uv tool install "earshot[mcp] @ git+https://github.com/Leonxlnx/earshot"` | also ships an MCP server (`[mcp]` extra) and the `earshot` skill |
| yt-dlp 2026.10.26 | download inspiration / reference reels | https://github.com/yt-dlp/yt-dlp | core | `brew install yt-dlp` / `winget install yt-dlp.yt-dlp` | reference only, never re-publish downloaded content |
| git-lfs 3.8.1 | large binary assets in the repo | https://git-lfs.com | core | `brew install git-lfs` / `winget install GitHub.GitLFS` | |
| librsvg 2.63.4 (`rsvg-convert`) | Material SVG icons -> PNG | https://wiki.gnome.org/Projects/LibRsvg | core (Mac), optional (Win) | `brew install librsvg` | Windows uses the pre-rendered `*_512.png` icons |
| Playwright 1.58.0 (Python) + Chromium build 1208 | headless browser that renders the HTML motion pieces (`m_*` templates) to RGBA frames | https://playwright.dev/python/ | core | in requirements.txt (`playwright==1.58.0`, or `pip install -e "engine[motion]"`), then `python -m playwright install chromium` (both installers; CI adds `--with-deps` on Ubuntu) | Apache-2.0. The browser lives in the Playwright cache (`~/Library/Caches/ms-playwright`, `%LOCALAPPDATA%\ms-playwright`, `~/.cache/ms-playwright`). The doctor checks both. No third-party JS: CVES ships its own runtime (`engine/cves/motion/runtime.js`) |
| pytest 9.2.0 + pytest-xdist 3.8.0 (+ execnet 2.1.2, filelock) | the test suite, in parallel on every core (`python -m pytest -n auto tests`) | https://pytest-xdist.readthedocs.io/ | dev | in requirements.txt (both installers) and `engine[test]`; CI installs `engine[test,motion]` | MIT. Not needed to edit videos (the doctor WARNs, never FAILs). The session demo builds are shared between workers with a filelock (also a torch dependency); `-p no:xdist` runs serially |
| uv 0.11.6 | Python installs, venvs, uv tools | https://docs.astral.sh/uv/ | core | standalone installer or `brew install uv` / `winget install astral-sh.uv` | |
| Poppins (Medium, SemiBold, Bold, ExtraBold) | caption + graphics type | https://github.com/google/fonts/tree/main/ofl/poppins | core | in `assets/fonts` | OFL 1.1, licence in `assets/fonts/LICENSES/` |
| Cormorant Garamond | serif accent / wordmarks | https://github.com/google/fonts/tree/main/ofl/cormorantgaramond | core | in `assets/fonts` | OFL 1.1 |
| Material Symbols / Icons | icons in cutaways | https://github.com/google/material-design-icons | core | in `assets/icons` (+ CREDITS.md) | Apache-2.0 |
| SFX bank (28 sounds) | 13 recordings (whoosh, pop, ding, riser, boom ...) + 15 synthesized by CVES (risers, impacts, whooshes, pops, tick, room tone), catalogued in `assets/sfx/manifest.yaml` | Freesound via Openverse; `tools/make_sfx.py` | core | in `assets/sfx` (+ CREDITS.md) | CC0 only; `cves sfx` list / fetch / add / check (docs/SOUND.md) |

## 2. Claude Code plugins and skills
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| **cves** (this repo) | `video-editor` skill + `/cves:*` commands | `plugin/` | core | `/plugin marketplace add profitcastdev-byte/claude-video-editing-system` then `/plugin install cves@cves` | |
| superpowers | planning / TDD / review workflows when changing the engine | https://github.com/anthropics/claude-plugins-official | optional | `/plugin install superpowers@claude-plugins-official` | for developers of CVES, not for editing |
| real-sfx | frame-accurate placement of real recorded SFX (+ 78 CC0 UI sounds from uisfx) | https://github.com/Clipwing/skills (`skills/real-sfx`) | optional | copy `skills/real-sfx` to `~/.claude/skills/` (or the `.skill` package) | needs your own SFX library in its `config.json` |
| real-sound | soundtrack process from real licensed recordings: cue list, music edit at bar lines, measured QA, mastering | https://github.com/Leonxlnx/earshot (`skills/real-sound`) | optional | copy `skills/real-sound` to `~/.claude/skills/` | pairs with earshot |
| earshot (skill) | when and how Claude must listen before judging audio | https://github.com/Leonxlnx/earshot (`skills/earshot`) | optional (CLI is core) | copy `skills/earshot` to `~/.claude/skills/` | |
| remotion skills | code-made motion graphics (React) | https://github.com/remotion-dev/skills | optional | copy the skills to `~/.claude/skills/`; `npm i -g @remotion/cli` (4.0.474 here) | `remotion` is often not on PATH: use `npx remotion` |
| hyperframes | HTML/GSAP motion compositions rendered to video | https://github.com/heygen-com/hyperframes | optional | `npm i -g hyperframes` (0.9.59 here) + its skill | |

## 3. Connectors (Claude account, no keys in code)
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| ElevenLabs | music beds, SFX, voice tools | https://elevenlabs.io | optional | claude.ai > Settings > Connectors | `cves music generate` prints the hand-off; Claude calls the connector; `cves music credit` logs it. Commercial use per ElevenLabs plan terms |
| Magnific: upscale / relight / music | image upscale + relight for stills; `audio_music_generate`, `audio_sfx_generate` | https://magnific.ai | optional | claude.ai > Settings > Connectors | |
| Magnific: image generation | AI stills for cutaways | https://magnific.ai | **rejected for now: re-test** | - | its MCP generate tools did not load in Claude Code because of the 200-tool limit (too many tools across connectors). Re-test with fewer connectors enabled, or via tool search, and update this row |

## 4. Openverse for audio (music + SFX search)
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| Openverse API `/v1/audio/` | search CC music (Jamendo, Wikimedia ...) and SFX (Freesound) with licence filtering | https://api.openverse.org/v1/ | core | nothing: `engine/cves/music.py` | no key needed (`OPENVERSE_TOKEN` optional). `cves music search ... --kind music|sfx --min --max --license cc0,by`, `cves music download <id> Music/ [--wav]` |
| Freesound API `/apiv2/search/text/` (optional) | `cves sfx fetch` also searches Freesound when `FREESOUND_API_KEY` is set (token auth; HQ MP3 previews need no OAuth); CC0 results only | https://freesound.org/docs/api/ | optional | nothing: `engine/cves/sfx.py` | key from https://freesound.org/apiv2/apply; never commit it |

**Licence and credit rules (enforced in `music.py`):**
- Allowed: **CC0**, **Public Domain Mark**, **CC BY**. Refused: BY-SA (share-alike would bind the ad), anything NC (ads are commercial), ND, sampling+.
- Every download appends a block to `CREDITS.md` next to the file: title, creator, licence + URL, source page, Openverse id, date.
- **CC BY: the credit line must go in the post caption / description** ("Title" by Creator, CC BY x.0). CREDITS.md marks it `Attribution REQUIRED`.
- CC0: no credit required, but keep the CREDITS.md entry (proof of licence).
- Freesound files arrive as the HQ MP3 preview (the original WAV needs a Freesound login). Fine for SFX; for a hero music track prefer an original.
- Openverse sometimes returns HTTP 500 for a valid query; `music.py` retries.

## 5. Control-mode editors and their MCP servers
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| DaVinci Resolve (Free) | human fine-tuning + Claude live control | https://www.blackmagicdesign.com/products/davinciresolve | core for control mode | manual download (free "DaVinci Resolve") | see docs/CONTROL-MODE.md |
| DaVinci Resolve Studio | paid version | same | **rejected** | - | not needed: the Free version plus the in-app bridge covers everything we do |
| hiteshK03/davinci-resolve-mcp | Resolve MCP through an in-app bridge (Workspace > Scripts > CursorBridge); works on **Free** | https://github.com/hiteshK03/davinci-resolve-mcp | core for control mode | docs/CONTROL-MODE.md + `setup/control/patch_cursorbridge.py` | we install a hardened bridge (no CORS, Host / Origin checks, CVES endpoints), pinned to a reviewed upstream commit |
| samuelgursky/davinci-resolve-mcp | Resolve MCP through Resolve's external scripting API | https://github.com/samuelgursky/davinci-resolve-mcp | evaluated | - | larger tool surface; we use the in-app bridge approach so the Free version works |
| Kdenlive | open-source editor for control mode | https://kdenlive.org | optional | `brew install --cask kdenlive` / `winget install KDE.Kdenlive` | |
| 12bijaya/MCP_Server_Kdenlive | edits the `.kdenlive` project file (reload in the app) | https://github.com/12bijaya/MCP_Server_Kdenlive | optional | docs/CONTROL-MODE.md + `setup/control/patch_kdenlive_mcp.py` | |

## 6. Research
| Name | What it's for | Link | Status | Install | Notes |
|---|---|---|---|---|---|
| Apify | scrape competitor ads / reels / reviews and Meta Ad Library for hooks and style references | https://apify.com · https://mcp.apify.com | optional | claude.ai connector, or `claude mcp add --transport http apify https://mcp.apify.com` | pay-per-use; never scrape personal data beyond what the brief needs |
| Firecrawl | web search + page scraping for briefs (client sites, claims checking) | https://firecrawl.dev | optional | Firecrawl MCP / connector | |

## 7. Rejected (summary)
| Name | Why |
|---|---|
| Resemble Enhance | its generative enhancement mode **rewrote words** in a real take. Never acceptable for an ad with claims. Voice chain = DeepFilterNet only |
| Magnific image generation | MCP generate tools did not load in Claude Code (200-tool limit). Status is "re-test", not "bad" |
| DaVinci Resolve Studio | not needed: Free + in-app bridge |
| plain Homebrew `ffmpeg` / gyan "essentials" | no drawtext, no rubberband |

## How to add a tool
1. **Try it on a branch** against a real project (never client footage in the repo). Write down what it does better
   than the current tool, and what it costs: licence, price, install weight, Windows support.
2. **Add a row** in the right table with status `evaluated` (or `optional` / `core` if you are adopting it). Fill in
   every column: name + version, what it's for, link to the source repo or vendor, status, the exact install command,
   and notes (licence, gotchas).
3. **If it becomes core:** add it to `setup/install_mac.sh` **and** `setup/install_windows.ps1` (pinned version /
   commit / sha256), to `setup/requirements.txt` if it is a Python package, and a check to `setup/doctor.py`. If the
   engine needs its path, add a key in `engine/cves/config.py` (DEFAULTS), and the installers write it to `config.yaml`.
4. **If you reject one**, keep the row and say why in one line, so nobody re-tries it blindly.
5. Add a CHANGELOG entry and open a PR (CONTRIBUTING.md).
