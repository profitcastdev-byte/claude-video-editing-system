---
description: Step 7. Run every built QC gate on the final file, read QC-REPORT.txt, and fix edit.yaml until there are no FAILs
argument-hint: "[project folder or final.mp4]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:qc: step 7, quality gates

Target: `$ARGUMENTS` (the current project's final MP4 by default). Follow the `video-editor` skill (§4).

## Run
`cves qc [file]` runs every built gate in `knowledge-base/QC-GATES.md` and writes `Edit/QC-REPORT.txt` (FAILs in detail, WARNINGs listed). It also works on a file exported from Resolve or Kdenlive: the same final-file gates apply (SND-01/02, COL-01, DEL-01 to DEL-05, CUT-01 to CUT-03).

## You decide
- Read `QC-REPORT.txt` once. For each FAIL, look up only that gate's row in `QC-GATES.md` (grep its id) to see the metric and the threshold.
- Find the cause upstream first (RULEBOOK §11): a late card is usually a keyword time in `edit.yaml`; a jump cut is a zoom step or a snap boundary; a quiet bed is `music.bed_lu`.
- Fix it in `edit.yaml` (or the selects), re-render only what changed (`cves render --only <id>`, then `cves mix && cves encode`), and re-run `cves qc`. Repeat until there are **0 FAILs**.
- Retention gates (RET-24 to RET-32, `docs/VIRAL.md`): a late hook is a missing interrupt in the first second (a snap, a title card, a cut); a long interrupt gap needs a cut, a zoom step or a graphic; effect soup means removing effects, not adding; dead air (RET-31, FAIL for `goal: viral`) is a pause or a missing bed; RET-30 FAIL means the post is longer than the platform allows; RET-32 means cuts off the guide beat (`cves beats --sync cuts --apply`). With `music.slot: platform`, SND-04 FAILs if any music reached the master.
- Never edit a threshold, skip a gate or mark a FAIL as a WARNING. A threshold changes only through `DECISIONS.md` and a PR.
- If a FAIL needs something you can't make (a pickup shot, client proof, an engine bug), stop and report it.
- Then do the single contact-sheet QA pass with `QA-REVIEW.md`, and tick `CHECKLISTS.md` §10.

## Show the user
After 0 FAILs only: "QC passed", the WARNING list with timecodes, and the file path. If it can't pass, list the blocking FAILs, why you can't fix them, and what you need from the user. Don't attach the file.

## Stop?
Not while there are FAILs you can fix. Then `/cves:critique` and the review loop (`/cves:review`) before delivery.
