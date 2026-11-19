---
description: Senior-editor review. Build the critique pack (contact sheet, energy timeline, rubric), score it honestly, fix anything below 7, log the scores
argument-hint: "[vNNN | master]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:critique: the senior-editor pass

Target: `$ARGUMENTS` (default `master`, the file `cves qc` last judged). Rules: `knowledge-base/CREATIVE.md` and `knowledge-base/QA-REVIEW.md`. Run it after `cves qc` shows 0 FAIL and before the user sees the cut.

## Run
`cves critique [vNNN|master]` writes `PROJECT/Edit/critique/`:
- `contact_sheet.jpg`: one frame per shot plus key moments (frame 0, each graphic settled, the last frame), labelled with time and id / template;
- `timeline.png`: cuts, graphics, SFX hits, music energy, speech on/off and loudness on one time axis;
- `CRITIQUE.md`: measured facts, the restraint budget (style `creative:`), and the rubric to fill.

## You decide
1. Read the facts and the budget in `CRITIQUE.md`. Look at `contact_sheet.jpg` once and `timeline.png` once (this is the review image pass of skill §3).
2. Score every rubric line 1-10 with one honest reason: hook, story clarity, pacing / rhythm, visual aesthetics, motion craft, sound design, creativity (is there ONE memorable moment?), restraint (anything gratuitous?), platform fit, brand fit. Compare against `Edit/DIRECTION.md`: did the signature moment land, does the motif pay off, did we keep the "will NOT do" list? Be the strict senior editor, not the proud author.
3. Write the 3 changes a senior editor would make next.
4. Fix every line below 7 that can be fixed in `edit.yaml` (re-render only what changed, `cves qc` to 0 FAIL, critique again). Anything that needs a pickup, proof or a new template: say so.
5. Log it: `cves learn rate <version> <overall> --by claude --why "<one line>" --scores hook=..,story=..,pacing=..,aesthetics=..,motion=..,sound=..,creativity=..,restraint=..,platform=..,brand=..`.

Next: the review loop (`/cves:review`): it watches the render itself, cut by cut.

## Show the user
Nothing from the critique by default: show the MP4 as the skill says, with one line on what the critique changed. Show `CRITIQUE.md` if the user asks why something was done.
