---
description: Step 3. Pick the takes and beats from the raw transcript (Edit/selects.yaml), build the tightened cut with `cves select`, then stop for the user's approval
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:story: step 3, beats and selects
Project: `$ARGUMENTS` (or the current one). Rules: RULEBOOK §2 + RULEBOOK-CORE "Story" (takes, backwards order, joins, hook timings, loops, brand last); structures `skills/video-editor/reference/formats.md`; viral `reference/viral.md` (Story). Text only: **open no image at this step.**

`cves story` prints `Edit/raw_transcript.txt` (raw timestamps, from `cves ingest`) and the structure + beats in force (e.g. `structure: offer  beats: H Hook > M Mechanism > PR Proof > R Risk reversal > C CTA`). Raw times drift 1-3 s around retakes and pauses: `cves select` re-times each clip from its `text:`.

## You decide
- **Structure** from the brief → `Edit/NOTES.md` + style `grammar.structure` (`edit.yaml style: {grammar: {structure: offer}}`, or the client's `Brand/style.yaml`); `custom` = `grammar.beats`, which also overrides any preset. Beats in its order (problem H→P→A→PR→O→C, offer H→M→PR→R→C, story H→S→T→PR→C); a weak join is fixed only by another take or re-ordering, never synthesised speech.
- Pick takes for warmth and energy, not only accuracy. Hook also names a "you/your" pain. Write the setup→payoff table; cut orphans.
- **Viral:** the structure's beat order is a guide; tag parts with the closest beats, re-hooks every 5-8 s, and name the structure in the cut list.
- **`Edit/selects.yaml`**: `clips: [{id, in, out, beat, text}]`, raw seconds, **story order** (re-ordering allowed), **`text:` = the take's exact words** (required by alignment and STORY-17). Example: demo project in `examples/` (`tools/make_demo.py`).
- **`cves select`** aligns each take (re-transcribes a window, finds `text:`, snaps `in` / `out` into the pauses around it; one line per clip: moved, match score). `WARNING` = not found, hand times kept: fix `text:` (as spoken) or the times. `align: false` keeps hand times; `--align-only` reports without cutting. Then voice clean (DeepFilterNet + podcast chain, no generative models), pauses ≤ 0.25 s, frame-snap, slivers < 4 frames dropped → `Edit/edl.json`, `voice_final.wav`, `voice_raw.wav`.
- **`cves qc --stage story`**: pauses, verbatim stutters, STORY-17 (each clip's span must contain its `text:`; FAIL lists missing words), sign-off, length, structure from your tags (all beats, in order; problem ≤ 25 % where there is a P; proof ≤ 50 %; offer after proof, or for `offer` the risk reversal after proof; CTA in the last 15 %). Fix in `selects.yaml`, re-run both. Tick `CHECKLISTS.md` §2.

## Show: the cut list as text
Structure; table `# | beat | in-out (s) | take | text` (aligned, from `edl.json`); alignment moves > 0.3 s and clips at hand times; runtime and % problem + agitation; connector chain per boundary ("…so… but…"); setup→payoff table; flags (missing proof, weak take, drops and why); viral: hook type + first second, structure, payoff, loop (at the top).

**Stop: approval 1** (skill §2). Changes: revise `selects.yaml`, `cves select`, show again. Record it dated in `Edit/NOTES.md`; the approved re-ordered script is the words-gate reference. Next `/cves:plan`.
