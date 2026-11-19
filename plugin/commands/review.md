---
description: Watch the render before the owner does. Build the review pack (cut strips, hook, payoff, end card, audio), look, fix, re-render, max 3 rounds, then sign off
argument-hint: "[build [vNNN|master] | apply | signoff | show]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:review: the review loop

Target: `$ARGUMENTS` (default `build` on the master `cves qc` last judged). Reference: `docs/REVIEW.md`. Run it after
`cves qc` and `cves critique`, before the user sees any cut (skill §4b).

## Run
`cves review build` writes `PROJECT/Edit/review/rNNN/`: `index.jpg` + `cuts/cut_NN.jpg` (frames -2..+2 around every cut),
`hook.jpg` (first 3 s at 10 fps), `payoff.jpg`, `endcard.jpg`, `audio.json`, `findings.json` and `REVIEW.md`.

## You decide
1. Read `REVIEW.md` once. Then look, with the Read tool: `index.jpg`, every flagged cut strip and 2-3 unflagged ones,
   `hook.jpg`, `payoff.jpg`, `endcard.jpg`. Never claim how audio sounds: use `audio.json` (and earshot when it ran).
2. Answer every rubric question in `REVIEW.md` (yes / no, timecode, the fix). A finding is a hint: a dark graphic after a
   bright shot may be the design. Say why you keep anything flagged.
3. Fix: `cves review apply` applies the safe patches (bed level, end card length). Do the rest by hand in `edit.yaml`
   (suggested patches show the path); re-render only what changed.
4. Re-run: `cves build` (or render --only + mix + encode + qc), `cves critique`, `cves review build`.
5. Repeat until QC has **0 FAIL** and there are **no high findings**, at most 3 rounds (round 3 says "round cap reached").
6. Sign off, always, with what is still wrong:
   `cves review signoff --verdict ship --notes "..."` or `--verdict revise --notes "..."` (cannot ship: needs a pickup,
   proof, an engine fix). The journal keeps the verdict and the open findings.

## Show the user
Nothing from the pack by default: the MP4 as the skill says, with one line on what the review fixed and anything still open
from your sign-off notes. With `--verdict revise`, tell the user what blocks the cut and what you need.

## Stop?
Not while a high finding or a QC FAIL is fixable and rounds remain. Never loosen a QC gate or a `review.*` threshold to pass.
