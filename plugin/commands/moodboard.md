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

**Stop: approval 2** (skill §2; record it dated in `Edit/NOTES.md`). Next `/cves:render`.
