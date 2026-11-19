---
description: Step 6 and 7. Render, mix and encode the approved edit, then run QC and fix until there are no FAILs before showing anything
argument-hint: "[project folder] [--only <id>]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:render: steps 6 and 7, render, mix, encode, QC
Project / options: `$ARGUMENTS`. Needs approval 2 in `Edit/NOTES.md`, else `/cves:moodboard` (re-renders after notes need none).

- `cves build` (render + mix + encode + fast QC, prints the summary) or `cves render && cves mix && cves encode`. Partial: `cves render --only <id>` (one cutaway, roto or chest element), then `cves mix && cves encode`.
- Engine-fixed quality path: one decode, lossless frames, one x264 encode (crf 16, bt709). No second encode, grain or `tune film`.
- Long jobs: background if possible; read text logs, not frames.
- Then always: `cves qc` to **0 FAIL** (`/cves:qc`), the one-image contact-sheet QA pass (`knowledge-base/QA-REVIEW.md`), `cves critique`, the review loop (`/cves:review`) and `cves review signoff`.
- Decide only how to fix FAILs; change approved story / design only if a gate forces it, and say so.

**Show** (skill §4): MP4 path in `Export/`, duration, LUFS / dBTP, WARNINGs with timecodes, what changed. Then wait for notes (`/cves:notes`) or control mode (`/cves:resolve`, `/cves:kdenlive`).
