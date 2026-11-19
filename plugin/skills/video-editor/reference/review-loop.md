# Critique and review loop (read at steps 7b-7c, before any cut reaches the owner)

## Critique (`/cves:critique`): QC proves nothing is wrong; the critique asks whether it is good
After QC shows 0 FAIL and before you show the user any cut:
1. `cves critique` (or `cves critique vNNN`). It writes `Edit/critique/contact_sheet.jpg`, `timeline.png` (cuts, graphics,
   SFX, music energy, speech) and `CRITIQUE.md` (facts, restraint budget, rubric).
2. Fill `CRITIQUE.md` honestly, as a strict senior editor: score hook, story clarity, pacing, visual aesthetics, motion
   craft, sound design, creativity, restraint, platform fit and brand fit 1-10 with a reason each, against
   `DIRECTION.md`; then the 3 changes a senior editor would make next.
3. Fix every line below 7 that `edit.yaml` can fix, re-render what changed, `cves qc` to 0 FAIL, and critique again.
   Report what can't be fixed.
4. Log your scores: `cves learn rate <version> <overall> --by claude --scores hook=..,story=..,...`. Your self-ratings are
   compared with the user's over time.
The critique contact sheet is also the one image of the QA pass (`knowledge-base/QA-REVIEW.md`).

## Review loop (`/cves:review`, `docs/REVIEW.md`): watch the render before the owner does
Every time a cut is about to reach the owner (first cut and every revision):
**render → qc → critique → review → look and fix → re-render**, until **0 FAIL and no high findings**, max **3 rounds**.
1. `cves build` (render, mix, encode, QC), `cves qc` to 0 FAIL as far as you can, `cves critique`.
2. `cves review build`. Read `Edit/review/rNNN/REVIEW.md`, then look with the Read tool at the images its "Look" list
   names, in order: `index.jpg`, the `strips_N.jpg` sheets (every flagged cut strip plus a few unflagged ones), `hook.jpg`,
   `ends.jpg` (payoff, then end card). Open a single `cuts/cut_NN.jpg` only to settle a doubt. Answer the rubric (yes /
   no, timecode, fix). Findings are hints; you judge, and you say why you keep anything flagged. QC gates appear there by
   id only: their detail is in `QC-REPORT.txt`.
3. `cves review apply` for the safe patches; fix the rest in `edit.yaml` by hand; re-render only what changed.
4. Back to 1. Rebuilding the pack for an unchanged master reuses the round; round 3 prints "round cap reached".
5. Sign off, always: `cves review signoff --verdict ship --notes "<what is still not perfect>"`, or `--verdict revise
   --notes "<what blocks it>"` and tell the user what you need. The journal keeps the verdict and every open finding.
Never claim how audio sounds: read `audio.json` (and the earshot summary when it ran). Never loosen a QC gate or a
`review.*` threshold to end the loop.
