---
description: Step 6 and 7. Render, mix and encode the approved edit, then run QC and fix until there are no FAILs before showing anything
argument-hint: "[project folder] [--only <id>]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:render: steps 6 and 7, render, mix, encode, QC

Project and options: `$ARGUMENTS`. Follow the `video-editor` skill. Check that `Edit/NOTES.md` records approval 2 (the moodboard). Without it, run `/cves:moodboard` first. A re-render after notes doesn't need a new approval.

## Run
```bash
cves render && cves mix && cves encode
```
- Partial re-render: `cves render --only <id>` (one cutaway, roto or chest element), then `cves mix && cves encode`.
- The quality path is fixed by the engine: one decode, lossless frames, one x264 encode (crf 16, bt709 tags). Don't add a second encode, grain or `tune film`.
- These are long local jobs. Run them in the background if your tools allow it, and read the text logs rather than watching frames.

## Then always: QC (the same as `/cves:qc`)
1. `cves qc` → `Edit/QC-REPORT.txt`.
2. For every FAIL: fix the cause in `edit.yaml` or the selects, re-render only what changed, re-encode, re-run QC. Loop until there are **0 FAILs**.
3. Do the one contact-sheet QA pass (`knowledge-base/QA-REVIEW.md`): one image only.

## You decide
Only how to fix FAILs. Don't change approved story or design choices unless a gate forces it. If it does, say so.

## Show the user
Only after 0 FAILs: the MP4 path in `Export/`, the duration, the loudness (LUFS / dBTP), the WARNINGs with timecodes, and what changed since the last version. Never show a render that has FAILs (RULEBOOK §0.10).

## Stop?
Delivery. Wait for notes (`/cves:notes`) or a request for control mode (`/cves:resolve`, `/cves:kdenlive`).
