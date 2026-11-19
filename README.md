# Claude Video Editing System (CVES)

An autonomous editing agent for short-form talking-head video (Reels, Shorts, TikTok, paid social ads), built on Claude Code.
**Claude makes the decisions, local code does the work, and people can take over in a real editor.**

No look is hard-coded. Each client's style is **measured from their own reference edits** (`cves inspire`) into a style profile. That profile drives the grade, captions, transitions, framing, pacing, sound levels and the QC thresholds. The engine knows craft, not a house style.

The craft comes from a 73-video curriculum covering motion, editing, graphic design, retention, sound, narrative, composition, colour and platform. It is distilled into a rulebook of 185 quality rules. **96 of them are measured automatically on every render** (`cves qc`), plus 18 early checks on the story and the plan. The rest are checked by eye on the edit plan and contact sheets. A render with any failing gate cannot be delivered.

## Two ways to work
| | **Vibe mode** | **Control mode** |
|---|---|---|
| You | Talk: "make the hook punchier", "music louder" | Edit in DaVinci Resolve (free) or Kdenlive, and/or prompt |
| Claude | Story → plan → edit plan → render → QC → delivery | Same first cut, exported as a layered project; your edits import back into `edit.yaml` (`cves import-edits`) |
| Output | QC-stamped versioned delivery (MP4, SRT/VTT, cover, reframes, variants) | Layered project (A-roll, cutaways, overlays, editable captions, voice/music/SFX stems) + the same delivery |

## The workflow
1. `/cves:new-edit`: project folders. Drop in footage (any camera, any orientation, frame rate, HDR or SDR) and the client's reference edits.
2. `cves inspire`: measures the reference edits and writes `Edit/style.yaml`. Without references, the neutral defaults or a named preset apply.
3. Ingest: probe and conform every source, transcribe (any whisper language, chunked for long files), clean the voice (DeepFilterNet, never generative), lossless plates, subject matte, face landmarks.
4. **Story:** Claude picks the takes and tags the story beats. **You approve the cut list.**
5. **Plan:** Claude fills `edit.yaml` from templates and media (graphics, images, B-roll, screen recordings, picture-in-picture, generated assets), then runs `cves validate`.
6. **Edit plan:** a multi-track timeline plus every shot with frames from the final renderer, its words, framing, transitions and sound. **You approve.**
6b. Open or creative brief: `cves treatments` builds 2-3 takes (punchy / cinematic / minimal) as fast half-size proxies and a side-by-side sheet; you pick one (docs/TREATMENTS.md).
7. Render → beat-synced mix (music sections on the story beats, risers and impacts, voice-following ducking; docs/SOUND.md) → encode → `cves qc`. Then **Claude watches its own cut** (`cves review`: frame strips at every cut, the hook, payoff and end card, audio checks; docs/REVIEW.md) and fixes and re-renders, up to 3 rounds, until there are 0 FAILs and no high findings, before you see it.
8. `cves deliver`: a versioned `Export/vNNN/` with the master, captions, cover, 4:5 / 1:1 / 16:9 reframes, hook, end-card and music variants, and 15 / 30 s cut-downs. Every variant passes QC itself, and delivery refuses a file QC hasn't approved.

Your notes become rules or gates, so they never come back (`LESSONS.md`). CVES also journals every edit, note, rating and result, mines them for repeated patterns, and proposes them as taste you approve (`cves learn`, `docs/LEARNING.md`): nothing changes the look until a person promotes it.

## Try it without footage
```bash
python tools/make_demo.py ~/CVES-demo
cves --project ~/CVES-demo build
```
This builds a synthetic project (a drawn presenter, a synthesised voice, a generated music bed; no real person or licensed media) and renders, mixes, encodes and QCs it. The demo's presenter is drawn, so the face-detection gates that re-detect on the final file report on it; everything else is a normal edit.

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
| `engine/` | the `cves` Python package + CLI: ingest, inspire, style, templates, media, render, captions, mix, beats, encode, QC, deliver, variants, control-mode export/import |
| `engine/cves/styles/` | `default.yaml` (neutral, every key documented in [docs/STYLE.md](docs/STYLE.md)) and optional presets |
| `plugin/` | the Claude Code plugin: `/cves:*` commands, the editor skill, the connector guide and the QC hook that blocks unapproved delivery |
| `knowledge-base/` | trained from 73 videos: RULEBOOK (read before every edit), CHECKLISTS, QA-REVIEW, QC-GATES (172 rules, generated implementation status), DECISIONS, EDIT-STANDARD, 9 module dissections |
| `docs/` | ARCHITECTURE, CONTRACTS (engine interfaces), STYLE, INGEST, TEMPLATES, MEDIA, MUSIC, DELIVERY, CONTROL-MODE, TOOLCHAIN-NOTES |
| `library/` | EFFECTS.md (about 90 effects catalogued from reference reels), SFX-METHOD.md (sound and music method) |
| `assets/` | fonts (OFL, incl. Noto for 7 Indic scripts), Material icons (Apache-2.0), CC0 sound effects |
| `tools/` | `make_demo.py` (synthetic demo), `lint.py` (portability and no-hard-coded-style lint), `gate_status.py` |
| `tests/` | unit tests and golden-frame tests on the demo; CI runs them on macOS, Windows and Linux |
| `setup/` | one-shot installers (Mac / Windows) and `doctor.py` |
| `TOOLS-REGISTRY.md` | every plugin, skill, repo and connector we use or have evaluated. **Update it when you find better ones.** |

## Generated media and audio
- **Magnific** and **ElevenLabs** (Claude connectors) generate images, video, voice, music and SFX when the footage isn't enough. The engine never calls them itself: Claude generates, asks before spending credits, and registers each file with `cves assets add`, with its provenance. QC fails any asset without a source and licence (`AST-01`).
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
- **Not every gate is automated:** 96 of the 185 rules are. The others need instruments that don't exist yet (role and intent tags, blur and banding detectors, music-stem gates); see `knowledge-base/QC-GATES.md`.
- **Footage limits the grade can't remove:** on the first test ad, two colour gates still fail. COL-06 (cut-to-cut colour match) fails where skin drifts within a shot and where the wall patch changes between punch-ins. FRAME-03 (edge halo) fails where a bright door frame sits next to the shoulder and where hair is motion-blurred. Both report honestly instead of being loosened.
- **Windows CI** runs the test suite; a full edit on a Windows machine has not been tried by hand yet.
- **Linux is not a supported editing platform.** CI runs the tests there, but Ubuntu's own `melt` (MLT 7.36) ignores overlay transparency in landscape projects, so Kdenlive playback is verified with the MLT that ships in Kdenlive (7.43, macOS), not on Linux.

## Rules for changing the system
Branch → PR. CI (lint, tests and the gate table) must pass. Every new tool goes into `TOOLS-REGISTRY.md` and `CHANGELOG.md`; every threshold change gets a line in `knowledge-base/DECISIONS.md`; every new style key goes into `default.yaml` with a comment.
Never commit client footage, client names, API keys or unlicensed music. See [CONTRIBUTING.md](CONTRIBUTING.md).
