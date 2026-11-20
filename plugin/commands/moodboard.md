---
description: Step 5. Build the complete edit plan (timeline + every shot with its rendered build frames), review it once, then stop for the user's approval before the full render
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:moodboard: step 5, the edit plan for approval
Project: `$ARGUMENTS`. The **complete edit plan**, every frame from the production renderer; never mock it up elsewhere.

`cves moodboard` (~20–30 s) → `PROJECT/Moodboard/`: **`EDIT-PLAN.html`** for the user (stats header; multi-track timeline: beats, shots, framing, roto, chest, captions, transitions, SFX, music + drop; every shot with its build frames, words, framing, transitions, captions, sound; `cves qc --stage plan` results); **`EDIT-PLAN.md`** (same as text: read this); **`moodboard.jpg`** (every keyframe: your one image).

- Read `EDIT-PLAN.md` fully: beat flow, each cutaway on its own line, shot lengths, sound cues, pre-render checks.
- **`moodboard.jpg` once**, vs STYLE and RULEBOOK §4–6: series look; one hero element per frame; face clear; text in the safe zone (x 65–1015, y 269–1248); real logos; Material icons; every paused frame designed; cutaways build in readable steps.
- Fix `edit.yaml`, re-run; re-open the image only after visual changes. Tick `CHECKLISTS.md` §4.

**Show:** the **`EDIT-PLAN.html`** path + 5–8 lines (beat flow, cutaways and what each shows, roto / chest moments, music drop, departures from the inspirations). The user answers by shot number ("#7 make the counter bigger").

## Review round: the plan review page (docs/PLAN-REVIEW.md)
1. Run `cves review-plan` in the background (`--no-open` on a remote machine). It serves the plan on 127.0.0.1 and stops when the editor presses **Send**.
2. Wait for the editor's Send (or pasted Copy notes text: save it as `Edit/plan_notes.json`).
3. Run `cves plan apply-notes`: quick actions become exact `edit.yaml` edits; approved shots are locked.
4. Read **`Edit/plan_notes.pending.md` only**, not the page or the images. Never change a locked shot.
5. Open a shot's frames only if its note is visual. Then `cves moodboard` (only changed shots re-render) and the next round.

**Stop: approval 2** (skill §2; record it dated in `Edit/NOTES.md`). Next `/cves:render`.
