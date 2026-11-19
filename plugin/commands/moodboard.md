---
description: Step 5. Build the complete edit plan (timeline + every shot with its rendered build frames), review it once, then stop for the user's approval before the full render
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:moodboard: step 5, the edit plan for approval

Project: `$ARGUMENTS` (or the current project). Follow the `video-editor` skill.

The moodboard is the **complete edit plan**, not a handful of frames. Every frame in it comes from the production renderer, so the edit will look exactly like the plan. Never mock it up in another tool.

## Run
`cves moodboard`. In about 20–30 s it writes to `PROJECT/Moodboard/`:
- **`EDIT-PLAN.html`** (for the user):
  - **Header:** summary stats (runtime, shots, cuts/min, cutaway share, median shot length, roto count, captions on screen, SFX cues, music and drop, style preset).
  - **Timeline:** a multi-track view with Beats (H/P/A/PR/O/C), Shots, Framing (zoom levels, the extreme punch-in), Roto, Chest, Captions, Transitions (the kinds the style uses: cut/whip/glitch/fade), SFX (reveal hits in gold) and Music (bed level and the drop).
  - **Every shot in order:** its build frames (for a cutaway, each element landing; for a roto or chest moment, the element on screen), plus the beat, the spoken words, what's on screen, framing, transitions in → out, captions and sound cues.
  - **Pre-render check results** (`cves qc --stage plan`).
- **`EDIT-PLAN.md`:** the same plan as a text table. Read this, not the images.
- **`moodboard.jpg`:** a contact sheet of every keyframe, for your one visual review.

## You decide
- Read `EDIT-PLAN.md` fully. Check the beat flow, that every cutaway illustrates its own line, shot lengths, sound cues and the pre-render checks.
- Open **`moodboard.jpg` once**. Check it against STYLE and RULEBOOK §4–6:
  - the series look; one hero element per frame; the face clear;
  - text inside the safe zone (x 65–1015, y 269–1248); real logos; Material icons;
  - every paused frame looks designed;
  - cutaways build in readable steps.
- Fix problems in `edit.yaml` and re-run `cves moodboard`. Re-open the image only after visual changes.
- Tick `CHECKLISTS.md` §4.

## Show the user
- The path to **`EDIT-PLAN.html`**, plus a 5–8 line summary: the beat flow, the cutaways and what each shows, the roto and chest moments, the music drop, and anything that departs from the client's inspirations.
- The user replies with shot numbers to change, e.g. "#7 make the counter bigger", "#12 swap the cutaway for a card list".

## Review round: the plan review page (docs/PLAN-REVIEW.md)
1. Run `cves review-plan` in the background (`--no-open` on a remote machine). It serves the plan on 127.0.0.1 and stops when the editor presses **Send**.
2. Wait for the editor's Send (or pasted Copy notes text: save it as `Edit/plan_notes.json`).
3. Run `cves plan apply-notes`: quick actions become exact `edit.yaml` edits; approved shots are locked.
4. Read **`Edit/plan_notes.pending.md` only**, not the page or the images. Never change a locked shot.
5. Open a shot's frames only if its note is visual. Then `cves moodboard` (only changed shots re-render) and the next round.

## Stop: approval 2
**End your turn and wait.** Continue only on a clear yes. Notes mean revise and show the updated plan again. Record the approval with its date in `Edit/NOTES.md` (the page's **Approve all** does this). Next: `/cves:render`.
