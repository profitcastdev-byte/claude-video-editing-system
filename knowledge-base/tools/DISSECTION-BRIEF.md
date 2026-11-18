# Dissection brief: one curriculum module

You are training a Claude-driven video editing system that replaces a human editor for short-form vertical ads
(CVES: talking-head selfie ads, 9:16, 30–60 s, Instagram/Meta Reels; the edit standard is
`knowledge-base/EDIT-STANDARD.md`, and per-client looks come from a style profile, see `docs/STYLE.md`).
Keep universal best practice separate from per-client taste: a rule that is really a look choice (a colour, a
transition kind, a caption position, a level) should be written as a style-profile key, not as a house rule.
The system edits with code (ffmpeg, whisper.cpp word timings, RVM matting, YuNet face boxes, Python/PIL compositing,
librosa/earshot audio analysis), so rules are only useful if they are concrete enough to execute or to measure.

## Read everything
Read EVERY transcript in your module folder IN FULL, start to finish (use offset/limit reads for long files; do not
skim, sample or stop at the first half). The user's instruction is "put the entire video under the knife".
If a transcript header says WEAK MATCH, judge whether it is still on topic; if not, say so and extract what is useful.

## Write `modules/<module number> <module name>.md` with these sections

### A. Per-video dissection (one block per video, in curriculum order)
- Source line: id, real title, channel, URL, duration, transcript word count, match quality.
- Thesis in 1–2 sentences.
- **Every** teachable rule, technique, number, example and anti-pattern in the video, as numbered imperative rules,
  each tagged with the transcript timestamp `[mm:ss]`. Keep exact numbers (frames, ms, dB, %, px, counts, ratios).
  Expect 10–40 rules per video; long videos more. Do not merge distinct ideas; do not invent anything not in the transcript.
- Short quotes only (under 15 words) where the wording itself matters.

### B. Module synthesis
1. **Best practices**: the consolidated rules, de-duplicated across the 8 videos, ordered by impact, each citing its
   source ids (e.g. `[2.4, 2.6]`). Mark rules as UNIVERSAL or CONTEXT (say when they apply).
2. **Short-form ad translation**: how each rule applies to a 9:16, 30–60 s talking-head ad specifically; flag rules
   that do NOT transfer (e.g. feature-film continuity) and why.
3. **Checklist (pre-edit / during edit / pre-delivery)**: binary yes/no items an editor ticks.
4. **QA (human-judgement review)**: questions a senior editor asks while watching, with what "good" looks like.
5. **QC (automatable gates)**: measurable checks with a metric, a pass threshold, and HOW to measure it with the
   toolchain above (name the signal: e.g. "shot length from cut list", "YuNet face box vs text bbox",
   "ebur128 LU of music stem vs voice", "frame-diff spike count per second", "caption chars per second").
   Only give a numeric threshold if the videos support it or it is an industry norm you name as such.
6. **Anti-patterns / failure modes** to detect, each with a symptom and the fix.
7. **Conflicts & open questions**: where videos disagree with each other or with EDIT-STANDARD.md, and your call.

Be exhaustive. Length is expected (thousands of words). Accuracy over volume: every rule must trace to a timestamp.
Return to the orchestrator: the file path, per-video rule counts, and the 10 highest-impact rules for this module.
