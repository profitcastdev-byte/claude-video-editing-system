---
description: Step 4. Fill edit.yaml from templates for the approved cut (cutaways, roto, chest, end card, zoom, captions, music, SFX)
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:plan: step 4, the edit plan

Project: `$ARGUMENTS` (or the current project). Follow the `video-editor` skill. Check that `Edit/NOTES.md` records approval 1 (the cut list). Without it, run `/cves:story` instead.

## Run
On a **voiceover / music / broll** spine (`docs/FORMATS.md`) there is no `cves prep`: write the `broll:` track (skill §2a;
`cves autocut [--every beats|downbeats|bars] --apply` proposes one on the music grid), then cutaways (text cards, stats) on
top, captions (voiceover only), music and SFX, then steps 2-4 below. No `aroll`, `roto` or `chest` keys.

1. **`cves prep`** first (aroll spine) (local, a few minutes): cut-time word timings (`Edit/words.json`), the lossless plate, the rotoscope matte and face landmarks. Every keyword time you use comes from `words.json`.
2. **`cves plan`**: on first run it writes a skeleton `Edit/edit.yaml` (schema: `docs/ARCHITECTURE.md` §4), then validates it on every run.
3. **`cves templates`** lists every template and its params (details: `docs/TEMPLATES.md`; worked example: the demo project in `examples/`).
4. After filling it in: `cves plan` (validation), then **`cves qc --stage plan`** (CUT-05 punch-in steps, FRAME-09, roto budget, cutaway share and length, early keys).

## You decide (RULEBOOK §3, §5, §6, §7)
Fill in `edit.yaml`. **Only template choices and params; write no new code.**
- `broll` (any spine): footage shots in cut time, `{src | asset, start, end, in, framing: fill | fit | kenburns, speed, audio}`; on the aroll spine they count as cutaways (share band, ≤ 8 s without the face).
- `cutaways`: one per idea, tied to the keyword time. Every cutaway illustrates its own line (no wallpaper). 3-8 s each; 40-55% of runtime; never more than 8 s without the face.
- `aroll.zoom`: alternate ≥ 1.15× across every uncovered direct cut, measured at the cut frame with the creep included. One `snap` extreme punch-in, on the key line.
- `roto`: ≤ 4 moments, ≤ 3 s each. `chest`: the client wordmark or price card. `end_card`.
- `captions`: auto, with `hide` spans under the full-screen cutaways and `fixes` for mis-heard words.
- `music` and `sfx`: drop sync; the bed level comes from the style profile (`sound.bed_lu`), so set `bed_lu` here only to override it for this video. Templates emit their own SFX cues; add `extra` only for hero hits (≤ 2). For music, see `/cves:music`.
- Items land 0 to +6 f after their keyword. Nothing appears before it's said.
- Tick `CHECKLISTS.md` §3.

If no template can show a beat, say so and propose a new template as a system change (repo `CLAUDE.md`). Don't hack it inside the project.

## Show the user
A 5-10 line summary: a beat → visual map (time, template, what it shows), the cutaway %, the roto count and the music choice. No images.

## Stop?
No approval at this step. Fix any pre-render gate FAIL, then continue to `/cves:moodboard`.
