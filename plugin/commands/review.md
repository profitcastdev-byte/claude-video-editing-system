---
description: Watch the render before the owner does. Build the review pack (cut strips, hook, payoff, end card, audio), look, fix, re-render, max 3 rounds, then sign off
argument-hint: "[build [vNNN|master] | apply | signoff | show]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:review: the review loop
Target: `$ARGUMENTS` (default `build` on the master `cves qc` last judged), after `cves qc` and `cves critique`, before the user sees any cut. **Follow `skills/video-editor/reference/review-loop.md` (Review loop)**: Look list, rubric, apply, rounds, sign-off. `docs/REVIEW.md`.

Pack (`cves review build`, `--json` for `jq`) → `Edit/review/rNNN/`: `index.jpg`; `strips_N.jpg` (every flagged cut strip + a few unflagged, frames -2..+2, stacked to one read each); `hook.jpg` (first 3 s at 10 fps); `ends.jpg` (payoff, end card); per-cut `cuts/cut_NN.jpg` (only to settle a doubt), `payoff.jpg`, `endcard.jpg`, `audio.json`, `findings.json`, `REVIEW.md` (Look list ≈ 4-5 reads; gates by id, detail in `QC-REPORT.txt`).

- A finding is a hint (a dark graphic after a bright shot may be the design).
- `cves review apply` = safe patches (bed level, end card length); the rest by hand in `edit.yaml` (suggested patches show the path).
- Re-run: `cves build` (or render --only + mix + encode + qc), `cves critique`, `cves review build`.
- `--verdict revise` = can't ship (pickup, proof, engine fix): tell the user what blocks it and what you need.

**Show:** nothing from the pack; the MP4 per skill §4 + one line on what the review fixed and what's open from the sign-off notes.
