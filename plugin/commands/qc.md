---
description: Step 7. Run every built QC gate on the final file, read the QC summary, and fix edit.yaml until there are no FAILs
argument-hint: "[project folder or final.mp4]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:qc: step 7, quality gates
Target: `$ARGUMENTS` (default the project's final MP4). Skill §3-§4.

`cves qc [file]` runs every built gate, writes `Edit/QC-REPORT.txt`, prints the summary. On a Resolve / Kdenlive export the final-file gates apply (SND-01/02, COL-01, DEL-01 to DEL-05, CUT-01 to CUT-03).

- Read the summary; `QC-REPORT.txt` (or `--json`) only for a FAIL's detail lines; grep the gate's row in `QC-GATES.md` by id.
- Cause upstream first (RULEBOOK §11): late card → keyword time in `edit.yaml`; jump cut → zoom step or snap boundary; quiet bed → `music.bed_lu`.
- Fix `edit.yaml` / selects, `cves render --only <id>`, `cves mix && cves encode`, `cves qc`, to **0 FAIL**.
- Retention (RET-24 to RET-32, `docs/VIRAL.md`): late hook → an interrupt in the first second (snap, title card, cut); long interrupt gap → a cut, zoom step or graphic; effect soup → remove effects; dead air (RET-31, FAIL for `goal: viral`) → a pause or missing bed; RET-30 FAIL → longer than the platform allows; RET-32 → cuts off the guide beat (`cves beats --sync cuts --apply`). `music.slot: platform`: SND-04 FAILs if any music reached the master.
- Never mark a FAIL as WARNING; thresholds change only via `DECISIONS.md` + PR. Unfixable (pickup, proof, engine bug) → stop and report.
- Then the single contact-sheet QA pass (`QA-REVIEW.md`); tick `CHECKLISTS.md` §10.

**Show** (0 FAIL only): "QC passed", WARNINGs with timecodes, file path (no attachment). Can't pass: blocking FAILs, why, what you need. Next `/cves:critique`, `/cves:review`.
