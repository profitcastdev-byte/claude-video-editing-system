---
description: Step 3. Pick the takes and beats from the raw transcript (Edit/selects.yaml), build the tightened cut with `cves select`, then stop for the user's approval
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:story: step 3, beats and selects

Project: `$ARGUMENTS` (or the current project). Follow the `video-editor` skill: §0 paths, §1 load the RULEBOOK (§2 Story) and ES.

## Run
- `cves story` prints `Edit/raw_transcript.txt` (the whole take, with raw timestamps), written by `cves ingest` at step 2.
- Work only from text. **Don't open any image at this step.**

## You decide (RULEBOOK §2)
- Label every sentence H / P / A / PR / O / C / X.
- **Work backwards:** lock the complete sign-off first, then the offer, then the problems it pays off, then the proof, and pick the hook last.
- Keep the last complete take of each group that passes the stutter gate. Pick for warmth and energy, not only for accuracy.
- Order H→P→A→PR→O→C. Every boundary joins with *therefore* or *but*, never *and then*. Fix a weak join only by choosing another take or re-ordering, never with synthesised speech.
- The hook: first word ≤ 0.25 s, the topic named ≤ 2 s, a "you/your" pain, done by about 5-6 s.
- Write the setup→payoff table and cut the orphans. Close every open loop before the CTA. The brand is the last word.
- **`goal: viral`:** design the hook first (playbook §1: the first second as picture and words, the hook line re-ordered to the top), then the payoff (in the last 20 %), then the middle as re-hooks every 5-8 s. The ad beat order (H→P→A→PR→O→C) is a guide here, not a rule: tag the structure's parts with the closest beats and say in the cut list which structure you used.
- Write **`Edit/selects.yaml`**: `clips: [{id, in, out, beat}]` in raw seconds, **in story order** (re-ordering is allowed), each tagged with its `beat` (H hook, P problem, A agitation, PR proof, O offer, C CTA). Example: the demo project in `examples/`.
- Run **`cves select`**. It cleans the voice (DeepFilterNet + podcast chain, no generative models), tightens pauses to ≤ 0.25 s, frame-snaps, drops slivers under 4 frames, and writes `Edit/edl.json`, `voice_final.wav` and `voice_raw.wav`.
- Run **`cves qc --stage story`**: pauses, verbatim stutters, sign-off, length, and the story structure from your beat tags (all beats present and in order; problem ≤ 25% of runtime; proof ≤ 50%; price after proof; CTA in the last 15%). Fix any FAIL by changing `selects.yaml` (another take or other in/out points), then re-run both.
- Tick `CHECKLISTS.md` §2.

## Show the user: the cut list as text
A table with one row per kept sentence: `# | beat | in-out (s) | take | text`. Then:
- The runtime, and the % in problem + agitation.
- The connector chain, one line per boundary (for example "…so… but…").
- The setup→payoff table.
- Flags: missing proof, a weak take, anything you dropped and why.
- For `goal: viral`: the hook type and its first second, the structure, the payoff moment, and whether it loops.

## Stop: approval 1
**End your turn and wait.** Continue only on a clear yes ("approved", "go"). For change requests, revise `selects.yaml`, re-run `cves select` and show the cut list again. Record the approval with its date in `Edit/NOTES.md`. The approved, re-ordered script becomes the words-gate reference. Next: `/cves:plan`.
