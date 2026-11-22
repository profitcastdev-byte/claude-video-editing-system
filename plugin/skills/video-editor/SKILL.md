---
name: video-editor
description: Runs the Claude Video Editing System (CVES), a local `cves` engine for talking-head videos, ads and reels. Use it whenever the user asks to edit, cut, trim, plan, storyboard, moodboard, render, mix, export or deliver a video, reel or ad, to open one in DaVinci Resolve or Kdenlive, find music for it, or apply notes to an edit. It is a tool: it does exactly what the user asks with the `cves` commands, and nothing they did not ask for.
---

# CVES video editor
**CVES is a tool. Do exactly what the user asks, with the `cves` commands; nothing more.** You write text (`selects.yaml`, `edit.yaml`); the engine transcribes, aligns, renders, mixes, encodes and delivers. Each `/cves:*` command (new-edit, story, plan, moodboard, render, notes, deliver, music, assets, inspire, treatments, motion, learn, resolve, kdenlive, install, update) is one job. Plain-words requests ("cut this ad", "make the music louder") need no command.

## 0. Find the system (once per session; quote every path, they contain spaces)
- **`CVES_ROOT`** = the first folder holding `engine/cves/__init__.py` among: `$CVES_HOME`; `${CLAUDE_PLUGIN_ROOT}/..` (local clone / `--plugin-dir`); the marketplace clone under `~/.claude/plugins/marketplaces/*` (Windows `%USERPROFILE%\.claude\plugins\marketplaces\`, usually `cves` or `<owner>-<repo>`); `~/cves`, `~/claude-video-editing-system`, `%USERPROFILE%\claude-video-editing-system`. Else ask the user and suggest `CVES_HOME`.
  ```bash
  for d in "$CVES_HOME" "${CLAUDE_PLUGIN_ROOT}/.." "$HOME"/.claude/plugins/marketplaces/* "$HOME/cves" "$HOME/claude-video-editing-system"; do
    [ -n "$d" ] && [ -f "$d/engine/cves/__init__.py" ] && { cd "$d" && pwd; break; }; done
  ```
  PowerShell: loop the same list with `Test-Path "$d/engine/cves/__init__.py"` and print `(Resolve-Path $d).Path`.
- **`cves`**: on PATH, else `~/.cves/venv/bin/cves` (Windows `%USERPROFILE%\.cves\venv\Scripts\cves.exe`); neither → `/cves:install`. Unsure of flags → `cves <sub> --help`; never guess.
- **`PROJECT`**: `~/CVES Projects/<Client>/<YYYY-MM-DD Video Name>/` (root: `$CVES_CLIENTS`, else config `clients_root`). Not named → list the most recent folders and ask.
- **Orient with `cves status`** (stage reached, next command) instead of opening several files.

## 1. How to work
- Do what the instruction says, in the order it says, and stop. No extra steps, no "improvements", no changes the user did not ask for.
- Ask only when an instruction is ambiguous (two readings give clearly different cuts) or something the job needs is missing (no raw file, no music file). Then one short question.
- Nothing is graded or gated: there is no QC, review or approval step. Show the user what they asked to see, when they ask.
- The user's taste lives in the style profile (§4); read it when you plan, so a plan matches their look. It is a description, not a rule to enforce.
- Say what you ran and where the result is. If a command fails, give its one-line error and the fix you suggest.

## 2. Project layout
```
PROJECT/  Raw/ (takes as shot)  Inspirations/ (reference edits)  Brand/ (logo, claims.md, style.yaml)  Music/ (+ CREDITS.md)
          Edit/ (edit.yaml, selects.yaml, style.yaml, edl.json, words.json, faces.json, voice_*.wav, plate/, matte/, frames/,
                 elements.jsonl, timeline.json, mix.json, stems/, NOTES.md, journal.jsonl)
          Moodboard/ (EDIT-PLAN.html / .md, moodboard.jpg)   Export/ (<title>.mp4, vNNN/ deliveries, control/)
```
Full file list: `docs/CONTRACTS.md` §3. Layout and schema: `docs/ARCHITECTURE.md` §2, §4.

## 3. Commands (what → how)
| The user wants | Run |
|---|---|
| a new project | `cves new "<Client>" "<Video>" --raw "<file>"`, then `cves ingest` (`/cves:new-edit`) |
| the client's look measured | `cves inspire` (`/cves:inspire`) |
| the transcript / a cut | `cves story` → write `Edit/selects.yaml` (`clips: [{id, in, out, beat, text}]`) → `cves select` (`/cves:story`) |
| graphics, captions, music planned | `cves prep` (A-roll) → `cves plan` (skeleton, then validates) → fill `edit.yaml` from `cves templates` (`/cves:plan`) |
| the plan to look at | `cves moodboard` → `Moodboard/EDIT-PLAN.html`; editor notes via `cves review-plan` + `cves plan apply-notes` (`/cves:moodboard`) |
| a render | `cves build` (render + mix + encode); `cves build --draft` (half size); `cves render --only <id>` + `cves mix && cves encode` for one element (`/cves:render`) |
| changes in words | edit `edit.yaml`, re-render what changed (`/cves:notes`) |
| files to hand over | `cves deliver [--variants 4:5,1:1,cut15] [--only master] [--video X]` → `Export/vNNN/` (`/cves:deliver`) |
| music / SFX | `cves music search|download|generate|credit`, `cves beats`, `cves sfx list|fetch` (`/cves:music`) |
| pictures, B-roll, VO | `cves assets todo|add|check|list` (`/cves:assets`) |
| creative options | `cves treatments make|render|compare|pick` (`/cves:treatments`) |
| an editor project | `cves export resolve|kdenlive`, `cves control update --only <id>`, `cves import-edits` (`/cves:resolve`, `/cves:kdenlive`) |
| notes, ratings, learned taste | `cves learn note|rate|results|mine|promote|reject|forget|study` (`/cves:learn`) |
| a check of the install / the plan | `cves doctor`, `cves validate` |

## 4. edit.yaml and the style
- **Slots:** `spine` (aroll | voiceover | music | broll), `aroll` (`zoom`, `creep`, `snap`), `captions` (`auto`, `hide`, `fixes`), `cutaways`, `roto`, `chest`, `end_card`, `broll`, `transitions`, `music`, `sfx` (`auto`, `extra`), `assets`, `variants`, `delivery`, `style`. Times are cut seconds, keyed to `Edit/words.json`. Templates and their params: `cves templates [<name>]`, `docs/TEMPLATES.md`; example: `examples/`. Cutaways snap to segment boundaries unless `snap: false`. One roto per segment renders.
- **Style merge** (later wins): `styles/default.yaml` → learned layers (`knowledge-base/taste/learned.yaml`, team, `~/.cves/taste/learned.yaml`) → `style.preset` → `Edit/style.yaml` (`cves inspire`) → `Brand/style.yaml` → `edit.yaml style:` (`docs/STYLE.md`). Client notes in words: `<projects root>/<Client>/STYLE.md`.
- References next to this skill, read only for that job: `reference/formats.md` (canvas, spine, structure, `broll:`), `reference/motion.md`, `reference/sound.md`, `reference/viral.md`, `reference/treatments.md`, `reference/modes.md`, `reference/learning.md`; `library/EFFECTS.md`, `library/SFX-METHOD.md` for ideas.

## 5. Keep it cheap
- **Read text, not images:** `words.json`, the transcript, `edl.json`, `edit.yaml`, `EDIT-PLAN.md`, `elements.jsonl` (`grep` / `jq`, never whole). `--json` on `cves templates`, `cves status`, `cves validate` is for `jq`.
- Commands print short summaries; `-v` prints everything. An error prints one line plus `Edit/logs/cves.log`: read the log only if the line isn't enough.
- Open an image only when the user asks you to look, or a visual instruction can't be checked from text: one sheet (`moodboard.jpg`), never frames one by one.
- **Fill templates, don't write code.** If no template fits, say so; a new template is a change to the system (`CLAUDE.md`). No one-off scripts in a client project.
- **Re-render only what changed:** `cves render --only <id>`.
- Never claim how audio sounds without measuring it (`Edit/mix.json`, earshot if installed).

## 6. Safety
- Never overwrite `Raw/`. Never commit footage, client media, music or keys to the repo.
- Spending credits or money (generation, stock downloads): say what and the cost, and wait for a yes (`connectors.md`). No API key in a file or a command.
