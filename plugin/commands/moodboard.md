---
description: Build the edit plan page (timeline + every shot with its rendered build frames), and apply the editor's notes from the plan review page
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:moodboard: the edit plan page
Project: `$ARGUMENTS`. Every frame comes from the production renderer; never mock it up elsewhere.

`cves moodboard` (~20-30 s; `--full` re-renders every keyframe) → `PROJECT/Moodboard/`: **`EDIT-PLAN.html`** (stats; multi-track timeline: beats, shots, framing, roto, chest, captions, transitions, SFX, music + drop; every shot with its build frames, words, framing, transitions, captions, sound; per-shot Approve, quick actions, notes); **`EDIT-PLAN.md`** (the same as text: read this, not the page); **`moodboard.jpg`** (every keyframe on one sheet).

**Show:** the `EDIT-PLAN.html` path + a few lines (shots, cutaways, music drop). The user answers by shot number ("#7 make the counter bigger").

## Editor notes through the plan review page (docs/PLAN-REVIEW.md), when the user wants them
1. `cves review-plan` in the background (`--no-open` on a remote machine): serves the plan on 127.0.0.1, stops when the editor presses **Send**.
2. Wait for Send (or pasted Copy notes text: save it as `Edit/plan_notes.json`).
3. `cves plan apply-notes`: quick actions become exact `edit.yaml` edits; approved shots are locked.
4. Read **`Edit/plan_notes.pending.md` only** and make those changes; never change a locked shot. Then `cves moodboard` (only changed shots re-render).
