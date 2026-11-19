# Review loop (`cves review`)

QC proves nothing measurable is wrong; the critique asks whether the plan is good. The review loop is the third pass: a
senior editor **watches the render** before anyone else does. `cves review` builds a review pack from the encoded master
(not from `edit.yaml`), turns what it can measure into findings, and leaves the looking and judging to Claude. The engine
never calls a model and never scores taste.

```
cves review build [vNNN|master]                 review pack for this render -> Edit/review/rNNN/ (one round)
cves review apply [--only F01,F03] [--dry-run]  apply the safe patches of the latest round to edit.yaml (backup kept)
cves review signoff --verdict ship|revise --notes "..."   record the verdict + what is still wrong; closes the loop
cves review show [--json]                       the latest round: counts, open findings, paths
```

## 1. The loop

Run it after `cves build` (render, mix, encode, QC) and `cves critique`, before the owner sees any cut:

1. `cves qc` on the master (0 FAIL is the goal) and `cves critique`.
2. `cves review build`. Read `REVIEW.md`, then look with the Read tool at the images its **Look** list names, in order:
   `index.jpg`, the `strips_N.jpg` sheets (every flagged cut + `review.look_unflagged` others), `hook.jpg`, `ends.jpg`
   (payoff over end card); about 4-5 image reads. Open a single `cuts/cut_NN.jpg` only to settle a doubt. Answer the
   rubric in `REVIEW.md`.
3. Fix: `cves review apply` for the safe patches; everything else by hand in `edit.yaml` (the suggested patches show where).
4. Re-render (`cves build`, or `cves render --only ...` + `cves mix` + `cves encode` + `cves qc`), `cves critique`, and
   `cves review build` again.
5. Stop when QC has **0 FAIL** and there are **no high findings**, or when the round cap is reached. Then sign off:
   `cves review signoff --verdict ship --notes "<what is still not perfect>"`, or `--verdict revise --notes "<why not>"`.

**Round cap.** A loop has at most style `review.max_rounds` (3) rounds, tracked in `Edit/review/state.json`. Rebuilding
the pack for the same master (same sha256) redoes the current round instead of using a new one. In round 3 `build` prints
and writes "round cap reached"; a 4th round is refused until the sign-off. The sign-off closes the loop; the next `build`
starts round 1 of a new loop. A loop can't run forever, and it can't silently pass: every sign-off journals the high and
med findings still open, QC's FAIL count and Claude's notes (`review-signoff` event, [LEARNING.md](LEARNING.md)).
Shipping with open high findings or QC FAILs is allowed but recorded with a warning; `cves deliver` still refuses a master
whose QC has a FAIL.

## 2. The pack (`Edit/review/rNNN/`)

Packs are numbered across loops and never overwritten (except a rebuild of the same round).

| file | content |
|---|---|
| `cuts/cut_NN.jpg` | one contact image per cut: the frames at `review.cut_offsets` (default -2..+2; 0 = the first frame of the incoming shot, yellow), flagged frames in red, the cut's label (segments, cutaway in / out, B-roll shot) |
| `index.jpg` | every cut on one sheet: last frame before, first frame after; cuts with a finding in red |
| `strips_N.jpg` | the cut strips to look at, stacked: every flagged cut plus `review.look_unflagged` (3) unflagged ones spread over the video, as many per sheet as fit `review.look_px` (1560 px, about one image read) |
| `ends.jpg` | `payoff.jpg` over `endcard.jpg`, one read |
| `hook.jpg` | the first `review.hook_s` (3) s at `review.hook_fps` (10); the first visual change in green |
| `payoff.jpg` | `review.payoff_frames` (6) frames across the payoff window (`structure.payoff_window`) before the end card |
| `endcard.jpg` | the end card: entry, +0.25 s, middle, last frame (the last second when there is no end card) |
| `cuts.json` | per cut: timeline time and frame, the frame where the picture really changes (`picture_offset_f`), label, image, finding kinds |
| `audio.json` | integrated loudness and loudness per section (hook / body / payoff / end card, BS.1770); per cut the click ratio and peak; silences; end tail level; vocal-to-music ratio over speech (`vmr`); `earshot` (`earshot measure --json --light` on the master, or the reason it was skipped) |
| `findings.json` | `[{id, severity, t, kind, message, patch?, cut?, gate?}]`, high first; `applied: true` once applied |
| `REVIEW.md` | only what Claude must look at and decide: the ready-to-show verdict, the **Look** list (images in read order), the findings to judge (QC gates that only restate a QC-REPORT line are listed by id, not repeated), one line of facts, the sound summary, the rubric, the loop in one line |
| `applied.json`, `signoff.json` | what `apply` changed (with the backup name) and the sign-off record |

**Cut positions.** The cuts come from `critique.structure` (timeline segments, cutaway edges, B-roll shots, the end card).
Each is moved to the frame where the picture actually changes (within 2 frames); a cut hidden under a full-frame graphic
keeps its timeline frame. `picture_offset_f` in `cuts.json` shows any drift between the timeline time and the picture.

## 3. Findings

`severity` is `high` (blocks showing the owner), `med` (fix unless there is a reason) or `low` (look at it). `t` is the
time in the master (s), `null` for whole-file findings. `patch` is a machine-applicable `edit.yaml` change:

```json
{"set": {"end_card.duration": 1.0}, "safe": true}
{"set": {"cutaways[c3].end": 10.333}, "safe": false}
{"append": {"transitions": {"t": 3.467, "kind": "fade"}}, "safe": false}
```

Paths are dotted, with `[id]` (or `[segment]`, or a list index) selecting a list item. `cves review apply` applies only
`safe: true` patches (level and duration changes that cannot break the edit), once each; it writes a timestamped
`edit.yaml.bak-*`, keeps comments when the text patch verifies (the same approach as `cves beats --apply`) and records
the change in `applied.json`, `state.json` and the journal. Unsafe patches are suggestions: Claude applies them by hand
after looking (a moved cutaway edge may be re-snapped; a transition counts against the restraint budget).

| kind | severity | what | detector (style keys) | patch |
|---|---|---|---|---|
| `flash_frame` | high | a black or white frame, or a one-frame glitch, within 2 frames of a cut (not under a fade) | mean luma vs the shots either side (`review.black_luma`, `review.flash_delta`); a frame unlike both neighbours (`review.glitch_ratio`) | none: a render / snap fault to find |
| `freeze_frame` | med | a duplicated frame at a cut on a moving shot, or a cut that does not change the picture | frame step vs the local motion (`review.freeze_ratio`, `review.freeze_motion`) | none |
| `luma_jump` | low (med between footage shots above 1.5x) | a big brightness step across a hard cut | mean-luma step (`review.luma_jump`) with no transition at the cut | unsafe: a fade |
| `caption_cut` | med (1 frame) / low (2) | the caption changes 1-2 frames off a cut | caption signature per frame from `elements.jsonl` (`review.caption_near_f`) | unsafe: move the cutaway edge onto the caption change |
| `micro_shot` | med | a shot of fewer than `review.min_shot_f` frames | shot lengths | none |
| `dead_hook` | high | no visual change before `structure.hook_change_s` | largest frame step vs `retention.scene_diff`, cuts and graphic entries (`elements.jsonl`); replaced by QC RET-24 / RET-09 when QC already reports it | none (creative) |
| `end_card` | med | end card shorter than `review.end_card_min_s` | `edit.yaml end_card.duration` | **safe**: `end_card.duration` |
| `audio_pop` | med (high above 2x) | a click / discontinuity within a frame of a cut, attributed to the loudest offending stem | 2nd difference vs its p99.5 in the 0.3 s around (`review.click_ratio`, `review.click_floor_db`) | none (a crossfade or a cut on a pause) |
| `music_masks_voice` | high (p10 < 0 dB) / med | music too loud in the speech band under the words | 1-4 kHz vocal-to-music ratio over `words.json` spans from `stems/voice.wav` + `stems/music.wav` (`review.vmr_min_db`, `review.mask_share`) | **safe**: lower `music.bed_lu` (at most `review.bed_step_max_db`) |
| `section_level` | low | hook / body / payoff loudness step | BS.1770 per section (`review.section_jump_lu`) | none |
| `silence` | low | a silent gap inside the body | 50 ms windows under `review.silence_db` for `review.silence_s` (skipped when QC RET-31 reports dead air) | none |
| `abrupt_end` | low | the audio is still loud in the last 50 ms | `review.end_tail_db` | none |
| `qc` (or the matching kind) | high (FAIL) / low (WARN) | every QC gate that did not pass, read from `Edit/qc.json` | never re-measured | none |
| `qc_missing`, `qc_stale` | med | no `qc.json`, or it judged another file | sha256 of the master | run `cves qc` |
| `restraint`, `critique_missing` | low | a `creative.*` budget OVER in `critique.json`, or no critique | read from `Edit/critique/critique.json` | none |

Findings are hints, not verdicts: a dark graphic after a bright A-roll shot is usually the design, a silence can be a
deliberate drop-out. Claude decides, and says why in the rubric. **No machine finding proves the cut is good.**

## 4. The rubric (in `REVIEW.md`)

Claude answers each question by looking at the images, with yes / no, the timecode and the fix:

- **Cuts** (`index.jpg`, flagged strips): every cut on a word or action boundary; no black, white, duplicated or
  half-rendered frame; the eye lands where the last shot left it; captions change on the cut; A-roll framing changes
  enough or the jump is covered.
- **Hook** (`hook.jpg`): a visual change by the hook time; would you stop scrolling on frame 0; topic readable sound-off.
- **Payoff** (`payoff.jpg`): it delivers what the hook promised and is the visual peak.
- **End card** (`endcard.jpg`): on long enough to read twice; CTA legible and inside the safe zone; brand right.
- **Sound** (`audio.json`): voice clear over music everywhere; no pop at a cut; no section jumping in level; no
  unintended silence.
- **Verdict**: would a senior editor show this to the owner now? If not, the one change that matters most.

## 5. What it reuses (no duplicated gates)

- QC: `Edit/qc.json` (FAIL / WARN gates become findings, matched to this master by sha256). Thresholds are never changed
  by the review; `review.*` keys tune only the detectors no gate covers.
- Critique: `critique.structure` for the cut list, `critique.json` for the restraint budget.
- Style: `structure.hook_change_s`, `structure.payoff_window`, `retention.scene_diff`, `sound.bed_lu`.
- `beats._patch` for comment-keeping edits of `edit.yaml`.
- `earshot` is optional: `review.earshot: auto` runs `earshot measure` when it is on PATH (`config.get("earshot")`); a
  missing or failing earshot is recorded as `skipped` and never breaks the pack.
