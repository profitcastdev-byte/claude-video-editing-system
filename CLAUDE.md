# CLAUDE.md: Claude Video Editing System (CVES)

This repo is CVES, a Claude-driven editing tool for talking-head videos and ads, and for voiceover-, music- and B-roll-led edits (any frame size, natively: style `canvas.size`, default 1080×1920; see `docs/FORMATS.md`). **No look is hard-coded:** palette, grade, captions, transitions, pacing and sound levels all come from a style profile, normally measured from the client's own reference edits by `cves inspire` (see `docs/CONTRACTS.md` §1 and `docs/STYLE.md`). **Claude does what the user asks; the local `cves` engine does the work; humans fine-tune in a real editor** (DaVinci Resolve or Kdenlive). The full design is in `docs/ARCHITECTURE.md`.

There are two ways to use this repo:
- **Editing a video.** Install the `cves` plugin (below) and work from any folder. The `video-editor` skill and the `/cves:*` commands run the `cves` commands. Client footage lives **outside** this repo, in `~/CVES Projects/<Client>/<YYYY-MM-DD Video>/` (override with `$CVES_CLIENTS` or the `clients_root` config key).
- **Changing the system** (engine, templates, plugin). Open this repo in Claude Code. The rules below apply.

## Before any edit
Follow `plugin/skills/video-editor/SKILL.md` when editing a video. Never hard-code a colour, font, transition or look value in the engine: add a key to `engine/cves/styles/default.yaml` and read it from the style profile.

## Where things are
| Path | What |
|---|---|
| `docs/ARCHITECTURE.md` | Workflow (§3), `edit.yaml` schema (§4), templates (§5), element log (§6), control-mode export (§7), style profile (§9) |
| `docs/CONTRACTS.md`, `docs/STYLE.md` | Engine contracts (style merge order, timebase, project files) and the style-profile schema |
| `engine/cves/` | Python package and the `cves` CLI: ingest, story, plan, moodboard, render, beats, mix, music, encode, deliver, assets, `export/`, `templates/`, `style.py` + `styles/` (default profile and optional presets) |
| `plugin/` | Claude Code plugin `cves`: `skills/video-editor/SKILL.md` (loaded every session: keep it short), its on-demand `reference/*.md`, plus `commands/*.md` (one per workflow step) |
| `.claude-plugin/marketplace.json` | Marketplace `cves`, so the plugin can be installed from this repo |
| `knowledge-base/` | `TASTE.md` + `taste/learned.yaml`: the learned taste layer (`cves learn promote --share`, docs/LEARNING.md) |
| `assets/` | Fonts (OFL), Material icons (Apache-2.0), SFX (CC0), logos |
| `setup/` | `install_mac.sh`, `install_windows.ps1`, `requirements*.txt`, `doctor.py` |
| `examples/` | A demo project (`edit.yaml`, `edl.json`, notes; no client footage) |
| `INSTALL.md`, `TOOLS-REGISTRY.md`, `CHANGELOG.md`, `CONTRIBUTING.md` | Install steps, the tools list, change history, the contribution flow |

## Install the plugin (teammates)
In Claude Code:
```
/plugin marketplace add <git URL of this repo, or a local path to your clone>
/plugin install cves@cves
```
Then restart Claude Code, and run `/cves:install` once per machine (it follows `INSTALL.md` and runs the doctor). Run `/cves:update` to pull the system and re-run the doctor, and `/plugin marketplace update cves` to update the plugin itself.

## Rules for changing the system
1. **Every tool change updates `TOOLS-REGISTRY.md` and `CHANGELOG.md` in the same PR.** A tool change means adding, removing or upgrading a plugin, skill, repo, model, connector, MCP server or binary.
2. **Every behaviour change gets a CHANGELOG entry.** This covers a new template, style key or command. A new template needs its file, its registry entry and a moodboard sample (ARCHITECTURE §5).
3. **CVES is a tool.** It does what the user asks: no quality gates, review loops, budgets or approval stops in the engine or the plugin.
4. **Never commit** footage, client media, renders, stems, API keys or tokens, `.env` files, or music without a recorded licence. The repo holds code, rules and licensed assets (with their licence noted) only. Client data stays in the projects folder (`~/CVES Projects/` by default).
5. **Keep it cross-platform** (macOS and Windows). Use `pathlib`, not hard-coded separators or absolute paths, and quote every path: real paths contain spaces.
6. **Work on a branch and open a PR.** Don't push to `main`. Keep the plugin's `version` in `plugin/.claude-plugin/plugin.json` in step with the CHANGELOG when the plugin changes, and check it with `claude plugin validate ./plugin` and `claude plugin validate .`.


## Also read
- `library/EFFECTS.md` (effects catalogue) and `library/SFX-METHOD.md` (sound and music method).
- `docs/TOOLCHAIN-NOTES.md` when a tool misbehaves.
