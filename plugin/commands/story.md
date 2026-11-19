---
description: Step 3. Pick the takes and beats from the raw transcript (Edit/selects.yaml), build the tightened cut with `cves select`, then stop for the user's approval
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:story: step 3, beats and selects

Project: `$ARGUMENTS` (or the current project). Follow the `video-editor` skill: §0 paths, §1 load the RULEBOOK (§2 Story) and ES.

## Run
- `cves story` prints `Edit/raw_transcript.txt` (the whole take, with raw timestamps), written by `cves ingest` at step 2, then the
  structure in force and its beats (for example `structure: offer  beats: H Hook > M Mechanism > PR Proof > R Risk reversal > C CTA`).
- The raw timestamps drift by 1-3 s around retakes and long pauses. Treat them as a guide: `cves select` re-times every clip
  from its `text:` (take alignment), so put the clip's exact words in `text:`.
- Work only from text. **Don't open any image at this step.**

## You decide (RULEBOOK §2)
- **Choose the structure from the brief** and record it in `Edit/NOTES.md`; set it as style `grammar.structure` (in
  `edit.yaml style: {grammar: {structure: offer}}` for one video, or the client's `Brand/style.yaml`):
  - `problem` (default): H hook, P problem, A agitation, PR proof, O offer, C CTA. The ad sells relief from a pain.
  - `offer`: H hook / promise, M mechanism (how it works), PR proof, R risk reversal (guarantee, refund), C CTA. The ad
    leads with the result or offer and earns it with how and proof.
  - `story`: H hook, S setup (the before), T turn (the moment it changed), PR proof (the after), C CTA.
  - `custom`: any order, written in `grammar.beats` (which also overrides any preset).
- Label every sentence with the structure's beats, or X (cut).
- **Work backwards:** lock the complete sign-off first, then the offer, then the problems it pays off, then the proof, and pick the hook last.
- Keep the last complete take of each group that passes the stutter gate. Pick for warmth and energy, not only for accuracy.
- Order the beats in the structure's order (problem H→P→A→PR→O→C, offer H→M→PR→R→C, story H→S→T→PR→C). Every boundary joins with *therefore* or *but*, never *and then*. Fix a weak join only by choosing another take or re-ordering, never with synthesised speech.
- The hook: first word ≤ 0.25 s, the topic named ≤ 2 s, a "you/your" pain, done by about 5-6 s.
- Write the setup→payoff table and cut the orphans. Close every open loop before the CTA. The brand is the last word.
- **`goal: viral`:** design the hook first (playbook §1: the first second as picture and words, the hook line re-ordered to the top), then the payoff (in the last 20 %), then the middle as re-hooks every 5-8 s. The structure's beat order is a guide here, not a rule: tag the structure's parts with the closest beats and say in the cut list which structure you used.
- Write **`Edit/selects.yaml`**: `clips: [{id, in, out, beat, text}]` in raw seconds, **in story order** (re-ordering is allowed), each tagged with its `beat` from the structure and with **`text:` = the exact words of that take** (required: take alignment and STORY-17 read it). Example: the demo project in `examples/` (`tools/make_demo.py`).
- Run **`cves select`**. It first **aligns each take**: it re-transcribes a short window around each clip, finds `text:` in it and snaps `in` / `out` into the pauses just before the first word and after the last (one line per clip: what moved, and the match score). A `WARNING` line means the text was not found and the hand times were kept: fix `text:` (the words as spoken) or the times. `align: false` on a clip keeps its hand times; `cves select --align-only` prints the report without cutting. Then it cleans the voice (DeepFilterNet + podcast chain, no generative models), tightens pauses to ≤ 0.25 s, frame-snaps, drops slivers under 4 frames, and writes `Edit/edl.json`, `voice_final.wav` and `voice_raw.wav`.
- Run **`cves qc --stage story`**: pauses, verbatim stutters, **every chosen word heard** (STORY-17: each clip's span of the cut is transcribed on its own and must contain its `text:`; a FAIL lists the missing words per clip), sign-off, length, and the story structure from your beat tags (all of the structure's beats present and in order; problem ≤ 25% of runtime where there is a P; proof ≤ 50%; offer after proof, or for `offer` the risk reversal after proof; CTA in the last 15%). Fix any FAIL by changing `selects.yaml` (another take or other in/out points), then re-run both.
- Tick `CHECKLISTS.md` §2.

## Show the user: the cut list as text
The structure (problem / offer / story / custom). A table with one row per kept sentence: `# | beat | in-out (s) | take | text`, with the aligned in-out from `edl.json`. Then:
- What alignment moved (any edge > 0.3 s) and any clip it kept at the hand times.
- The runtime, and the % in problem + agitation.
- The connector chain, one line per boundary (for example "…so… but…").
- The setup→payoff table.
- Flags: missing proof, a weak take, anything you dropped and why.
- For `goal: viral`: the hook type and its first second, the structure, the payoff moment, and whether it loops.

## Stop: approval 1
**End your turn and wait.** Continue only on a clear yes ("approved", "go"). For change requests, revise `selects.yaml`, re-run `cves select` and show the cut list again. Record the approval with its date in `Edit/NOTES.md`. The approved, re-ordered script becomes the words-gate reference. Next: `/cves:plan`.
