# Contributing to CVES

CVES is an open repo. Anyone can propose tools, skills, templates, rules and gates.
The house rules for changing the system are in `CLAUDE.md` ("Rules for changing the system"); this file is the how-to.

## What you can propose
| You found... | Where it goes | What the PR must include |
|---|---|---|
| a better tool, plugin, skill, model, connector or MCP server | `TOOLS-REGISTRY.md` | a row with status `evaluated` / `optional` / `core`, the exact install command, link, licence, notes. If it becomes core: both installers, `requirements.txt` (Python), a `doctor.py` check, a `cves.config` key if the engine needs its path. See "How to add a tool" in the registry |
| a rule from client or reviewer feedback | `knowledge-base/RULEBOOK.md` + `DECISIONS.md` | the feedback in the person's own words, the date, and the rule. If it is measurable, a gate too |
| a new or changed QC gate / threshold | `knowledge-base/QC-GATES.md` + `engine/cves/qc/` | id, metric, threshold, status, implementation state. Thresholds change only by a recorded decision; never loosen a gate to make a video pass |
| a new template | `engine/cves/templates/<name>.py` + registry entry | a moodboard sample in `docs/TEMPLATES.md` (ARCHITECTURE section 5) |
| an install problem (especially Windows) | `setup/` + `INSTALL.md` troubleshooting | what broke, on which OS/version, and the fix |

Not sure it is worth it? Open a GitHub issue first, with a before/after example.

## Branch and PR flow
1. `git switch main && git pull`
2. `git switch -c <type>/<short-name>`, with type one of `tool/`, `rule/`, `gate/`, `template/`, `fix/`, `docs/`.
   Example: `tool/elevenlabs-music`.
3. Make the change. Run `cves doctor` (and `cves qc` on a test project if you touched the engine, templates or gates).
4. Update **CHANGELOG.md** (under `## [Unreleased]`) and, for any tool change, **TOOLS-REGISTRY.md**, in the same PR.
5. If the plugin changed, bump `version` in `plugin/.claude-plugin/plugin.json` and run
   `claude plugin validate ./plugin` and `claude plugin validate .`.
6. Push and open a PR against `main`: what changed, why, how you tested it, and on which OS. Attach before/after
   frames or a moodboard when the look changes (stills only, no client footage).
7. One review from someone else is required. Nobody pushes straight to `main`.
8. When releasing, move `[Unreleased]` entries into a new version section with the date.

Asking Claude Code to do it: "make a branch, add <tool> to TOOLS-REGISTRY.md as evaluated with install steps,
update CHANGELOG.md, and open a PR". Claude must not merge its own PR.

## Never commit
- **Client footage or media**: raw takes, renders, frames, stems, voice files, transcripts of client takes, client
  brand files. They live in `~/CVES Projects/<Client>/...` (or `$CVES_CLIENTS`), outside the repo.
- **Keys, tokens, passwords, `.env` files, cookies.** Connectors (ElevenLabs, Magnific, Apify) keep their own auth.
  If a secret is committed by mistake, tell the repo maintainer at once: rotating the key matters more than rewriting history.
- **Unlicensed music or SFX.** Only CC0 / Public Domain / CC BY (via `cves music`, which writes CREDITS.md), the
  team's own recordings, or generated tracks credited with `cves music credit`. No ripped tracks, no "royalty free"
  files without a licence record, no NC / SA / ND licences.
- **Model weights and binaries** (`.pth`, `.onnx`, `.bin`, ffmpeg). The installers download them, checksum-pinned.
- **Fonts without a licence file** in `assets/fonts/LICENSES/`. Client paid brand fonts stay in the client's `Brand/` folder.

`.gitignore` blocks most of this, but check `git status` before every commit anyway.

## Style
- Cross-platform: `pathlib`, no hard-coded separators or absolute paths, quote every path (real paths contain spaces
  and curly apostrophes).
- Pin versions (pip `==`, git commit, sha256 for downloads). "latest" is not reproducible.
- Keep the installers idempotent: a second run must skip finished steps and change nothing.
