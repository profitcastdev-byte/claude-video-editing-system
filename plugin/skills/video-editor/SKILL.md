---
name: video-editor
description: Runs the Claude Video Editing System (CVES), an autonomous editor for talking-head videos and ads whose look comes from each client's style profile. Use it whenever the user asks to edit, cut, trim, plan, storyboard, moodboard, render, mix, QC, review, export or deliver a video, reel or ad, or to open one in DaVinci Resolve or Kdenlive, find music for it, or apply notes to an edit. It loads the core RULEBOOK, follows the 8-step workflow with two user approvals (cut list, then moodboard), and never shows the user an edit that fails QC.
---

# CVES video editor
**You decide; the local `cves` engine does the work; humans fine-tune in a real editor.** You write text (beats, `edl.json`, `edit.yaml`); the engine renders, mixes, encodes and measures. Each `/cves:*` command (new-edit, story, plan, moodboard, render, qc, critique, review, notes, deliver, learn, resolve, kdenlive, music, install, update, ...) runs one step under this contract. For plain-words requests ("cut this ad", "make the music louder") follow the same steps without waiting for a command.

## 0. Find the system (once per session; quote every path, they contain spaces)
- **`CVES_ROOT`** = the first folder holding `knowledge-base/RULEBOOK.md` among: `$CVES_HOME`; `${CLAUDE_PLUGIN_ROOT}/..` (local clone / `--plugin-dir`); the marketplace clone under `~/.claude/plugins/marketplaces/*` (Windows `%USERPROFILE%\.claude\plugins\marketplaces\`, usually `cves` or `<owner>-<repo>`); `~/cves`, `~/claude-video-editing-system`, `%USERPROFILE%\claude-video-editing-system`. Else ask the user and suggest `CVES_HOME`.
  ```bash
  for d in "$CVES_HOME" "${CLAUDE_PLUGIN_ROOT}/.." "$HOME"/.claude/plugins/marketplaces/* "$HOME/cves" "$HOME/claude-video-editing-system"; do
    [ -n "$d" ] && [ -f "$d/knowledge-base/RULEBOOK.md" ] && { cd "$d" && pwd; break; }; done
  ```
  PowerShell: loop the same list with `Test-Path "$d/knowledge-base/RULEBOOK.md"` and print `(Resolve-Path $d).Path`.
- **`cves`**: on PATH, else `~/.cves/venv/bin/cves` (Windows `%USERPROFILE%\.cves\venv\Scripts\cves.exe`); neither → `/cves:install`. Unsure of flags → `cves <sub> --help`; never guess.
- **`PROJECT`**: `~/CVES Projects/<Client>/<YYYY-MM-DD Video Name>/` (root: `$CVES_CLIENTS`, else config `clients_root`; layout `docs/ARCHITECTURE.md` §2). Not named → list the most recent folders and ask.
- **Orient with `cves status`** (stage reached, last QC counts, open FAILs, next command) instead of opening several files.

## 1. Before you edit anything
Read, in order, and nothing else by default:
1. `knowledge-base/RULEBOOK-CORE.md`: the hard rules (§0 non-negotiables always apply) and which full-RULEBOOK section to read at each step. Read the step's section of `RULEBOOK.md` when you reach it; read the whole `RULEBOOK.md` for a new client's first edit, and before changing a rule, gate or template.
2. `knowledge-base/EDIT-STANDARD.md` (ES).
3. `LESSONS.md`: every past correction and the rule it became. Never repeat one.
4. The client's style: `<projects root>/<Client>/STYLE.md` (taste notes) and the merged style profile, plus `knowledge-base/TASTE.md`. No look is hard-coded: `styles/default.yaml` (neutral) → learned layers (`knowledge-base/taste/learned.yaml`, `~/.cves/taste/learned.yaml`, only matching goal / platform / client scope) → `style.preset` → `Edit/style.yaml` (`cves inspire`) → `Brand/style.yaml` → inline `edit.yaml style:` (`docs/CONTRACTS.md` §1, `docs/STYLE.md`). Palette, grade, captions, transitions, pacing bands, bed level and the QC thresholds all come from it. A new client has none yet: `/cves:new-edit` builds it.
5. `PROJECT/Edit/edit.yaml`, `edl.json`, `DIRECTION.md`, if they exist.

On demand (read only when doing that thing): `knowledge-base/CREATIVE.md` (senior-editor method, restraint budget, taste checks) before writing `DIRECTION.md` and before the critique; `library/EFFECTS.md` (~90 effects) when picking cutaway / transition ideas; `library/SFX-METHOD.md` for sound and music; `knowledge-base/modules/*` only for the detail behind a rule; a gate's row in `QC-GATES.md` by grepping its id (never the whole file); the files in `reference/` next to this skill, named per step below.

**Precedence:** confirmed user corrections > the client's style profile > ES > module rules. Open conflicts and defaults: `knowledge-base/DECISIONS.md`.

## 2. The workflow (`docs/ARCHITECTURE.md` §3)
In order. Don't skip a step, and don't start one whose input isn't approved. Tick `knowledge-base/CHECKLISTS.md` per stage; any "no" is fixed before the next stage or logged with a reason.

| Step | Run | You decide | You show the user | Stop? |
|---|---|---|---|---|
| 1 Setup | `cves new "<Client>" "<Video>" --raw <file>`; `cves inspire` for a new client | Brief: emotion, want + obstacle, the proof; canvas + spine + structure (`reference/formats.md`); STYLE for a new client | The brief + what's missing (proof, logo, claims) | Only if raw, inspirations or brand are missing |
| 2 Ingest | `cves ingest` | Nothing (local): raw transcript | Nothing unless it fails | No |
| 3 Story | `cves story` → write `Edit/selects.yaml` (`text:` on every clip) → `cves select` → `cves qc --stage story` | Structure (`grammar.structure`: problem H/P/A/PR/O/C, offer H/M/PR/R/C, story H/S/T/PR/C), beats + X, takes, order, connectors, setup→payoff | **The cut list** as text | **Yes: approval 1** |
| 3b Direction | write `Edit/DIRECTION.md` | Concept, arc, the ONE signature moment, motif, what we will NOT do | With the cut list or the edit plan | No (not a third approval) |
| 4 Plan | `cves prep` → `cves plan` → fill `edit.yaml` → `cves plan` → `cves qc --stage plan` | Templates + params (`cves templates`, `cves templates <name>`), keyed to `words.json`, serving DIRECTION.md | A short summary | No |
| 5 Edit plan | `cves moodboard` → `cves review-plan` → editor's Send → `cves plan apply-notes` (docs/PLAN-REVIEW.md) | Read `EDIT-PLAN.md`; review `moodboard.jpg` once; fix `edit.yaml`; each round read only `Edit/plan_notes.pending.md`, never change a locked shot | **`EDIT-PLAN.html`** (timeline + every shot with its build frames; per-shot Approve, quick actions, notes) | **Yes: approval 2** (Approve all records it) |
| 5b Treatments (open / creative brief only) | `reference/treatments.md` | 2-3 treatments; `sheet.jpg` once | `compare/sheet.jpg` + `compare.mp4` | **Yes: the user picks** (can ride with approval 2) |
| 6 Render + mix | `cves build` (render + mix + encode + fast QC) | Nothing (local) | Nothing yet | No |
| 7 QC | `cves qc` | Fix `edit.yaml` to 0 FAIL | Nothing until it passes | No |
| 7b Critique | `cves critique` (`reference/review-loop.md`) | Score the rubric honestly; fix anything < 7; log scores | Nothing yet | No |
| 7c Review loop | `cves review build` → look → fix → re-render (`reference/review-loop.md`) | Answer REVIEW.md from its images; to 0 FAIL + no high findings, max 3 rounds; `cves review signoff` | Nothing until signed off | No |
| 8a Vibe | - | Notes → `edit.yaml` changes | MP4 + QC summary | Waits for notes |
| 8b Control | `cves export resolve` / `kdenlive` | Drive the editor (`reference/modes.md`) | The project + `CONTROL.md` | Waits for the user |

**The two approvals are hard stops.** After the cut list (step 3) and after the moodboard (step 5), end your turn and wait for a clear yes. A change request means revise and show again; it is not a yes. Record each approval with its date in `PROJECT/Edit/NOTES.md`.

**Creative direction (3b).** Before filling `edit.yaml`, write `PROJECT/Edit/DIRECTION.md` (`knowledge-base/CREATIVE.md` §1): the one-line concept, the emotional arc along the beats, the ONE signature moment (time + how it is built), the recurring motif, what this video will NOT do, the goal / platform. One screen, inside the client's style and the restraint budget (style `creative:`). Plan `edit.yaml` to serve it. Any change the user asks for is a note.

**Read the reference for what you are planning:** `reference/formats.md` (canvas, spine, structure, `broll:` track), `reference/motion.md` (`m_*` pieces, roto, ramps, camera moves, transitions, the hero budget), `reference/sound.md` (music beats, accents, SFX by role, ducking, SND-32/33), `reference/viral.md` (`goal: viral` organic posts: brief questions, hook-first story, interrupt budget, the platform music slot; never for an ad).

## 3. Keep it cheap
Images cost far more than text; long output costs every turn.
- **Read text, not images:** `words.json`, the transcript, `edl.json`, `edit.yaml`, `elements.jsonl` (`grep` / `jq` it, never whole), the QC summary. Gates measure pixels so you don't have to.
- **Commands print short summaries.** `cves build` / `cves qc` end with counts, one line per FAIL, WARNs as `id: reason`, and the report path. Read `QC-REPORT.txt` only for a FAIL's detail lines; `cves qc --json`, `cves review build --json`, `cves templates --json`, `cves status --json` are for `jq` / `grep`. `-v` prints everything (full report, third-party warnings, tracebacks); use it only when a summary hides what you need. An error prints one line plus the log path (`Edit/logs/cves.log`): read the log only if the line isn't enough.
- **One image per review pass:** `moodboard.jpg` at step 5, the critique contact sheet as the QA pass before delivery (RULEBOOK §10), and the review pack's "Look" list (about 4-5 reads). Never open frames, plates or mattes one by one; one exact frame only when a gate points at it and the text can't explain it.
- **Fill templates, don't write code.** Every graphic is a template in `engine/cves/templates/` with `params` in `edit.yaml`. If none fits, say so and propose a new template as a system change (`CLAUDE.md`). No one-off scripts in a client project.
- **Re-render only what changed:** `cves render --only <id>`, never the whole video for one card. Don't re-run a gate to see the same line again.

## 4. Never show an objective fault
Before you show the user **any** render, MP4 or exported project:
1. `cves qc` on the final file. For every **FAIL**, fix the cause in `edit.yaml` (or the selects), re-render what changed, `cves qc` again, until **0 FAIL**.
2. The QA pass with `knowledge-base/QA-REVIEW.md` on the critique contact sheet (that is its one image); then the critique and the review loop to 0 FAIL and no high findings, signed off (`reference/review-loop.md`).
3. Only then deliver: the file path, a 2-3 line QC summary (passes, WARNINGs with timecodes) and anything you couldn't fix.

If a FAIL can't be fixed in `edit.yaml` (it needs a pickup, client proof, or an engine fix), stop and tell the user exactly that; never send the cut "for now" (RULEBOOK §0.10). The moodboard is the only exception (a plan, not a cut); still run the pre-render gates on `edit.yaml` first. Never lower a threshold or skip a gate to pass; thresholds change only by a recorded decision (§6). Never claim how audio sounds without `audio.json` / earshot.

## 5. Modes
Ask once per project, if unsaid; default **vibe** (notes in words → `edit.yaml`, re-render what changed, 0 FAIL, MP4 + one-line change log per note: `/cves:notes`). **Control** (export a layered project and drive Resolve / Kdenlive): `reference/modes.md`.

## 6. Notes become rules (RULEBOOK §11)
Every note is a fix now **and** a rule for later:
0. Journal it verbatim first: `cves learn note "<the user's exact words>"` (`--version vNNN` if about a delivered version). Builds, QC, deliveries and `import-edits` are journaled automatically.
1. Fix it in this project.
2. Write it generally ("cards enter 7 f after the keyword", not "c3 was late").
3. Record it in the repo on a branch and open a PR (never push to `main`): settles an open call → `DECISIONS.md` (resolved, the user's words + date); a new or changed rule → `RULEBOOK.md` in the right section, `[USER]` (and `RULEBOOK-CORE.md` if it is a hard rule); measurable → a proposed gate row in `QC-GATES.md` (id, metric, threshold, status), else a `CHECKLISTS.md` line.
4. Client-only taste ("this client hates red", "louder music") goes in that client's `STYLE.md` and style profile (`Brand/style.yaml` or `Edit/style.yaml`), never the RULEBOOK or the engine.
No git / `gh`: write the proposed diff into `PROJECT/Edit/NOTES.md` and tell the user it still has to be merged. After a delivery: ratings, results and learned taste per `reference/learning.md` (never promote a learned change without the user's yes).

## 7. Hard limits
- Don't touch the raw footage. Never commit footage, client media, API keys or unlicensed music.
- Licensed music only, credited in `PROJECT/Music/CREDITS.md` (`/cves:music`). A trending sound for an organic post is added in the app, never in the file (`music.slot: platform`).
- No generative voice enhancement or synthesised speech to fix a line: another take, or ask for a pickup. (A whole ElevenLabs voiceover the user chose and paid for is a `voiceover` spine, never a patch.)
- Icons from the Material set in `assets/icons/` only.
- Keep the full sign-off. Snap every edit to a segment boundary. Tag the delivered file `tv/bt709`. (RULEBOOK-CORE lists all the non-negotiables.)
