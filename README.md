# Claude Video Editing System (CVES)

An editing tool for short-form talking-head video (Reels, Shorts, TikTok, paid social ads), driven by Claude Code.
**Claude does what you ask, local code does the work, and people can take over in a real editor.**

No look is hard-coded. Each client's style is **measured from their own reference edits** (`cves inspire`) into a style profile. That profile drives the grade, captions, transitions, framing, pacing and sound levels. There is no house style.

CVES is a tool: it does exactly what you ask. It does not grade, gate or second-guess the edit, and it never makes a change you didn't ask for.

## Two ways to work
| | **Vibe mode** | **Control mode** |
|---|---|---|
| You | Talk: "make the hook punchier", "music louder" | Edit in DaVinci Resolve (free) or Kdenlive, and/or prompt |
| Claude | Story → plan → edit plan → render → delivery | Same first cut, exported as a layered project; your edits import back into `edit.yaml` (`cves import-edits`) |
| Output | Versioned delivery (MP4, SRT/VTT, cover, reframes, variants) | Layered project (A-roll, cutaways, overlays, editable captions, voice/music/SFX stems) + the same delivery |

## The workflow
1. `/cves:new-edit`: project folders. Drop in footage (any camera, any orientation, frame rate, HDR or SDR) and the client's reference edits.
2. `cves inspire`: measures the reference edits and writes `Edit/style.yaml`. Without references, the neutral defaults or a named preset apply.
3. Ingest: probe and conform every source, transcribe (any whisper language, chunked for long files), clean the voice (DeepFilterNet, never generative), lossless plates, subject matte, face landmarks.
4. **Story:** the takes and story beats you ask for go into `selects.yaml`; `cves select` aligns and tightens them.
5. **Plan:** Claude fills `edit.yaml` from templates and media (graphics, images, B-roll, screen recordings, picture-in-picture, generated assets), then runs `cves validate`.
6. **Edit plan:** a multi-track timeline plus every shot with frames from the final renderer, its words, framing, transitions and sound, with note boxes per shot (`cves review-plan`).
6b. Ask for treatments: `cves treatments` builds 2-3 takes (punchy / cinematic / minimal) as fast half-size proxies and a side-by-side sheet; you pick one (docs/TREATMENTS.md).
7. Render → beat-synced mix (music sections on the story beats, risers and impacts, voice-following ducking; docs/SOUND.md) → encode (`cves build`).
8. `cves deliver`: a versioned `Export/vNNN/` with the master, captions, cover, 4:5 / 1:1 / 16:9 reframes, hook, end-card and music variants, and 15 / 30 s cut-downs.

CVES can journal notes, ratings and results, mine them for repeated patterns, and propose them as taste you approve (`cves learn`, `docs/LEARNING.md`): nothing changes the look until a person promotes it.

## Try it without footage
```bash
python tools/make_demo.py ~/CVES-demo
cves --project ~/CVES-demo build
```
This builds a synthetic project (a drawn presenter, a synthesised voice, a generated music bed; no real person or licensed media) and renders, mixes and encodes it.

**Editors: start with [EDITORS.md](EDITORS.md)** (install, the 7-step workflow, team setup, fast commands).

## Install (Mac Apple Silicon or Windows 10/11)
You need Claude Code. In Claude Code:
```
/plugin marketplace add profitcastdev-byte/claude-video-editing-system
/plugin install cves@cves
```
Restart Claude Code and run `/cves:install`. It installs every tool, model and shared skill, then runs `cves doctor`.
**[INSTALL.md](INSTALL.md)** has the details, the manual steps (DaVinci Resolve Free, connector logins) and troubleshooting.

## What's where
| Path | What |
|---|---|
| `engine/` | the `cves` Python package + CLI: ingest, inspire, style, templates, media, render, captions, mix, beats, encode, deliver, variants, control-mode export/import |
| `engine/cves/styles/` | `default.yaml` (neutral, every key documented in [docs/STYLE.md](docs/STYLE.md)) and optional presets |
| `plugin/` | the Claude Code plugin: `/cves:*` commands, the editor skill, the connector guide |
| `knowledge-base/` | the learned taste layer: `TASTE.md`, `taste/learned.yaml` (`cves learn promote --share`) |
| `docs/` | ARCHITECTURE, CONTRACTS (engine interfaces), STYLE, INGEST, TEMPLATES, MEDIA, MUSIC, DELIVERY, CONTROL-MODE, TOOLCHAIN-NOTES |
| `library/` | EFFECTS.md (about 90 effects catalogued from reference reels), SFX-METHOD.md (sound and music method) |
| `assets/` | fonts (OFL, incl. Noto for 7 Indic scripts), Material icons (Apache-2.0), CC0 sound effects |
| `tools/` | `make_demo.py` (synthetic demo), `lint.py` (portability and no-hard-coded-style lint), `make_sfx.py` |
| `tests/` | unit tests and golden-frame tests on the demo; CI runs them on macOS, Windows and Linux |
| `setup/` | one-shot installers (Mac / Windows) and `doctor.py` |
| `TOOLS-REGISTRY.md` | every plugin, skill, repo and connector we use or have evaluated. **Update it when you find better ones.** |

## Generated media and audio
- **Magnific** and **ElevenLabs** (Claude connectors) generate images, video, voice, music and SFX when the footage isn't enough. The engine never calls them itself: Claude generates, asks before spending credits, and registers each file with `cves assets add`, with its provenance (`cves assets check` lists any asset without a source and licence).
- **Openverse** (`cves music search`): licence-checked music and SFX (CC0 / CC-BY, filtered for commercial use). Credits are logged automatically to `Music/CREDITS.md`.
- Never ship unlicensed music in a paid ad.

## Known limits (honest)
- **Native formats.** Any canvas renders natively (`canvas.size`, docs/FORMATS.md). The v0.2 UI cutaways (`search_rows`,
  `card_list`, `stat`, `browser_list`) and the roto cards now lay out per canvas shape (the original layout on 9:16, a
  scaled block on square canvases, a landscape arrangement with two-column lists on wide ones), and relative templates are
  rasterised at the canvas's real resolution (photo cards and panes included), so 4K graphics are crisp. A third-party
  template that touches layer pixels without `G.px` must set `RASTER = False` and is then scaled up (docs/TEMPLATES.md).
- **HDR.** PQ and HLG A-roll and B-roll / media clips are tonemapped to SDR BT.709 through the same chain. HDR stills (PQ
  AVIF / HEIC) are not; without ffmpeg's `zscale` the fallback only re-matrixes colours (docs/INGEST.md).
- **Resolve round trip:** the Kdenlive round trip (export, edit the project, melt render, `import-edits`, rebuild) is an
  automated test. DaVinci Resolve is not installed on the build machine, so a live Resolve import and a Resolve-written
  FCPXML have not been tested; [docs/RESOLVE-CHECKLIST.md](docs/RESOLVE-CHECKLIST.md) is the script for the first person with Resolve.
- **Complex scripts** (Indic, Arabic) need Pillow with libraqm for correct shaping; `cves doctor` reports whether it is available.
- **Footage limits the grade can't remove:** skin colour that drifts within a shot, or a bright door frame next to a motion-blurred shoulder, still shows through the shot match and the relight.
- **Windows CI** runs the test suite; a full edit on a Windows machine has not been tried by hand yet.
- **Linux is not a supported editing platform.** CI runs the tests there, but Ubuntu's own `melt` (MLT 7.36) ignores overlay transparency in landscape projects, so Kdenlive playback is verified with the MLT that ships in Kdenlive (7.43, macOS), not on Linux.

## Rules for changing the system
Branch → PR. CI (lint and tests) must pass. Every new tool goes into `TOOLS-REGISTRY.md` and `CHANGELOG.md`; every new style key goes into `default.yaml` with a comment.
Never commit client footage, client names, API keys or unlicensed music. See [CONTRIBUTING.md](CONTRIBUTING.md).
