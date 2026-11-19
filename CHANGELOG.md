# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

### Changed (Claude token cost: quiet, compact output and leaner always-loaded docs)
- **Quiet CLI by default** (`cves.out`). Run as a program, `cves` filters its stderr at the file-descriptor level, so
  workers and subprocesses are covered: the duplicate libavdevice `objc[...] Class AVF... is implemented in both` lines,
  OpenCV `[ WARN:...] global ...` lines (also `OPENCV_LOG_LEVEL=ERROR`, set before cv2 loads and inherited by workers)
  and numba RuntimeWarnings are dropped; a worker's traceback is folded into one `worker error: <exception>` line. All of
  it goes to `PROJECT/Edit/logs/cves.log` (else `~/.cves/logs/cves.log`; the previous run is `cves.log.prev`). An
  exception prints one actionable line plus the log path instead of a traceback. `-v` / `--verbose` (or
  `CVES_VERBOSE=1`) restores everything. Called with an argv (tests, other code), `cli.main` behaves as before.
- **`cves build` / `cves qc` print a short summary**: counts, one line per FAIL (+ up to 2 detail lines), WARNs as
  `id: reason` one-liners, the full report path. `Edit/QC-REPORT.txt` and `qc.json` are unchanged; `-v` prints the full
  report; the `N FAIL` wording the plugin hook reads is kept. Demo build (4 FAIL, 11 WARN): 113 lines / 10.3 k chars -> 21 lines / 1.8 k chars.
- **`cves templates`** prints one line per kind (7 lines instead of ~105); `--kinds` one line; `NAME` one template's
  kind, doc, the params its code reads (with defaults) and its `docs/TEMPLATES.md` section; `-v` the old full list.
- **`cves review build`** console: QC findings that only restate a QC line are grouped by gate id; it names the images to
  read. `REVIEW.md` lists only what Claude must look at and decide: a **Look** list (images in read order), the findings
  to judge (QC-only findings by id, detail in QC-REPORT.txt), facts in one line, sound in two, the rubric, the loop in
  one line. New sheets `strips_N.jpg` (every flagged cut strip + `review.look_unflagged` (3) others, stacked to
  `review.look_px` (1560 px, about one image read)) and `ends.jpg` (payoff over end card): the pack is read in about
  4-5 image reads instead of one per cut. The per-cut `cuts/cut_NN.jpg`, `payoff.jpg`, `endcard.jpg` are still written.
- **Leaner skill and command docs.** `plugin/skills/video-editor/SKILL.md` keeps every rule and step but moves reference
  detail to on-demand `reference/*.md` (formats, treatments, motion, sound, viral, review-loop, learning, modes) that it
  names per step; `plugin/commands/*.md` point to those instead of restating them (56.1 k -> 38.7 k chars).
  **`knowledge-base/RULEBOOK-CORE.md`** (new) holds the hard rules and which `RULEBOOK.md` section to read at each step;
  it is loaded every session instead of the full RULEBOOK, which is read per step, in full for a new client's first edit
  and before any rule / gate / template change. `CREATIVE.md` is read before DIRECTION.md and the critique.

### Added
- `cves status [PROJECT] [--json]`: one screen with the stage reached, the last QC counts, open FAILs, the review round,
  deliveries and the next command (read-only).
- `--json` on `cves qc` (counts + every gate, details for FAIL / WARN), `cves review build` and `cves templates`.
- Style keys `review.look_unflagged`, `review.look_px` (docs/STYLE.md).

### Fixed (first real job, integration)
- Prep no longer reuses a stale plate / matte after a re-cut that keeps segment ids (render ran out of frames); legacy plates are adopted when their length matches.
- FRAME-03 judges the halo the pipeline added (output vs the source plate at the same edge), not the room's own edges.
- `cves qc --stage plan` validates like `cves build`; abutting cutaways within half a frame no longer error.
- Motion pieces: stray edge pixels join the nearest part (no 1 px element with a jumping box, MOT-01).
- `text_behind`: harmonised instances keep the harmonising fit's line layout (GFX-20).
- `captions.fixes`: case- and punctuation-insensitive keys (`Alena: aligner` works).

### Added
- **Take alignment in `cves select`** (`cves.align`, docs/INGEST.md "Take alignment"). Long-form whisper word times drift
  by 1-3 s around retakes and pauses, so clip edges picked from `raw_words.json` clipped words. Every `selects.yaml` clip
  with `text:` is now re-timed: `story.align_passes` windows around the hand in/out are transcribed with whisper.cpp DTW
  token times (cached in `Edit/align/`), the text is fuzzy-matched (numbers normalised: "300 plus" = "300+", "a hundred
  percent" = "100%"), the passes are pooled (a pass that merged two takes is outvoted) and each edge snaps into the nearest
  pause, never inside speech, with `story.align_pad_s`. A low score keeps the hand times and warns. One report line per clip;
  `edl.json` clips record `aligned: {in, out, score, status, hand}`. Opt out per clip (`align: false`) or per style
  (`story.align: false`). `cves select --align-only` prints the report alone.
- **STORY-17 "every chosen word is heard"** (`cves qc --stage story`): each clip's own span of `voice_final.wav` is
  transcribed separately (a whole-file pass skipped a sentence that was in the cut) and its word recall against `text:` must
  reach `qc.words_recall_min` (0.85), and a clip whose first or last word is lost fails on its own (`qc.words_edges`); the missing words are listed per clip, and clips without `text:` are skipped and named.
  QC-GATES.md: 184 rows (STORY-14 was already the loops gate).
- **Named story structures**: style `grammar.structure: problem | offer | story | custom` (`cves.structure`). `problem` =
  H P A PR O C (the old fixed order), `offer` = H M PR R C (M mechanism, R risk reversal), `story` = H S T PR C (S setup,
  T turn); `grammar.beats` still overrides. The labels show in `cves story`, the moodboard / edit plan and `cves validate`
  (a beat outside the structure warns, as does a clip without `text:`). Music `hook_beats` / `turn_beats` / `drop_beats`
  now default per structure (offer: turn M, drop PR). STORY-13 runs only when the structure has a P beat; STORY-07 checks
  the offer after the proof, or for `offer` the risk reversal after the proof.
- New style keys `grammar.structure`, `story.align*` (7), `qc.words_recall_min`, `qc.words_edges`; `grammar.beats` and `music.hook_beats` /
  `turn_beats` / `drop_beats` now default to null (= from the structure). `tools/make_demo.py` writes `text:` on every
  clip; `tests/test_story.py`.

### Changed
- `/cves:story`, the `video-editor` skill, RULEBOOK §2 and CHECKLISTS §2: choose the structure in the brief, tag with its
  beats, write `text:` on every clip, read the alignment report.
### Fixed (first 60 fps client job: timing, audio and colour)
- **SFX on their picture event at any frame rate (SND-07).** Templates quantised a cue to the frame of its visual event, but the sound file starts there: its onset comes 17-40 ms later (1-3 frames at 60 fps; under a frame at 30 fps, where the bug hid), and some cues carried 30 fps-tuned offsets (the snap's `-0.01 s`). After render, `mix` now moves every cue so that its measured onset (a riser: its peak) lands exactly on the nearest picture event within `sound.cue_sync_max_f` (6) frames of the time the template asked for: element entries / changes from the element log and cuts first, a strong pixel-change onset on a graphic frame (measured on the rendered frames, `sound.cue_sync_pixel_min`) only when no logged event is that close. This is the event list SND-07 judges (`qc.extra.visual_events`, shared now). Peak-placed cues (transition whooshes, automatic risers), media audio and `sync: false` cues are left alone; synced cues are not beat-nudged. Pixel events are cached in `Edit/cue_sync.json` with the render they belong to, so `cves qc` rebuilds the same cue list; `mix.json cue_sync` lists every move. `m_list_build`'s check / cross mark is now its own logged part that pops in with its stroke on the frame of its pop cue (it used to sit, unlogged, in its row).
- **No 1-frame captions round cutaways (PLAT-06 / PLAT-07).** `captions.schedule()` (called by the Timeline) knows where the renderer hides captions (drawn cutaways, the roto snap, `captions.hide`, the end card) and resolves every visible fragment shorter than `captions.min_on_s` (0.83 s): a caption that would resume for a few frames after a cutaway moves its still-unspoken words into the next event when they fit the style limits and cross no sentence end, or is skipped when all its words were spoken under the cutaway; one that would flash just before a cutaway is held by the previous event. Words are never lost from what can be read. On the test ad: `caption@9.21` (1 frame) and `caption@30.95` (4 frames) are gone.
- **Adaptive voice gate (SND-19).** The fixed ffmpeg `agate` (threshold 0.02) left the room between words at -49.7 dBFS. `cves.voicegate` replaces it at the end of the voice chain: per take it measures the room left between the words (10th percentile of a 10 ms voice-band envelope on the tightened voice) and the speech level (90th), sets the threshold between them and the depth that takes the room to `voice.gate.floor_target_db` (-72), and works as a downward expander (ratio 6, 8 ms look-ahead, 15 ms hold, 2 / 40 ms ramps in dB): tails fade, never chop; no pumping. DeepFilterNet stays the only denoiser; `voice_chain.json` records the step `adaptive_gate` (generative: false) with each take's measurements. Shared by the A-roll and voiceover spines (`ingest.polish_voice`). Test ad: p5 -49.7 -> -64.4 dBFS.
- **Per-shot colour match (COL-06 / COL-07).** `cves.shotmatch` (style `grade.shot_match`, on by default) matches every A-roll shot to a reference shot (`hook`, `median` or a segment id) in linear light before the look: the subject gets a per-channel gain that maps its skin (the two cheek patches) onto the reference skin, the background one that maps its wall (matte background round the head) onto the reference wall, blended through the matte and never more than `shot_match_split_max` apart. Inside a shot `shot_match_drift` of the light drift is followed, smoothed over `shot_match_smooth_s` (a head turn is not chased). It supersedes `grade.exposure_match` while on. Cached in `Edit/shot_match.json`; `edit.yaml aroll.shot_match: false` turns it off for one video.
- **The music clears every word (review masking).** After envelope ducking, `mix` measures the voice and the bed in 1-4 kHz over 0.4 s windows while a word is spoken (the review's measure, including ffmpeg's mono downmix) and trims the bed's speech band wherever the ratio is under `review.vmr_min_db` + `mix.vmr_margin_db` (8 dB), at most `mix.vmr_max_cut_db` (12), smoothed; the bed is then re-levelled and checked again. `mix.json vmr_guard` records it. Test ad: 11 % of speech windows under 6 dB (worst at 5.10 s) -> 0 %.

### Added
- Style keys `sound.cue_sync`, `cue_sync_max_f`, `cue_sync_pixel_min`; `captions.min_on_s`; `voice.gate.*` (new `voice:` section); `grade.shot_match`, `shot_match_reference`, `shot_match_strength`, `shot_match_drift`, `shot_match_smooth_s`, `shot_match_step_f`, `shot_match_gain_range`, `shot_match_split_max`; `mix.vmr_guard`, `vmr_band_hz`, `vmr_min_db`, `vmr_margin_db`, `vmr_max_cut_db`, `vmr_window_s`, `vmr_attack_ms`, `vmr_release_ms` (default.yaml, docs/STYLE.md); `edit.yaml aroll.shot_match`.
- `tests/test_av_fixes.py` (synthetic media): cue onsets on their entry frame at 30 and 60 fps, caption fragments round a cutaway (skipped, merged, held), the adaptive gate on noise + tone in two rooms, the colour match on two shots with different white balance (+ black never lifted, drift followed, a glitch not chased), the vocal-to-music guard.
- Decisions in knowledge-base/DECISIONS.md ("AV fixes from the first 60 fps job"); docs/SOUND.md §3 and §6, docs/INGEST.md "Voice chain", docs/CONTRACTS.md §3.
### Fixed (graphics, found on the first client job: a 9:16 60 fps selfie ad)
- **`text_behind` contrast (GFX-15).** New default `craft.behind.color: auto`: the template measures the graded plate behind its box over the hold (the person masked out, `render.plate_lum`) and uses the light or dark token (`craft.behind.light` / `dark`) that reaches the GFX-15 target; a failing `*accent*` becomes its darker (`accent_dark`, then mixed toward black) or lighter variant, and a soft bed is added when neither token reads (`craft.behind.auto_bed`). White type over a light beige wall reached 1.93-2.2:1.
- **`text_behind` size (GFX-20).** Every instance without its own `size` uses one size per video, the smallest size any instance fits at (`craft.behind_size`), each fitted once at its shot's tightest zoom (`craft.seg_scale`), so it never re-fits mid-shot. "DENTIST?" and "100% REFUND" were 77 vs 94 px.
- **`text_behind` shake (MOT-03).** The face track is smoothed with a zero-phase Gaussian whose sigma is in seconds (`craft.behind.smooth_s`, 0.2 s, replaces `smooth_frames`), over the whole segment track; the clamped path is smoothed again so the type no longer stops dead on the safe edge (that was the 5 px/f^2 kink). `craft.behind.track` default 0.6 -> 0.4 (subtle).
- **Roto card entries (MOT-01).** `map_card`, `listing_card` and `top3_card` rise by whole raster pixels with per-frame steps that never grow, so the ease-out stays monotonic at any frame rate (at 60 fps half-pixel steps rounded to 2, 3, 1, 2).
- **End card centring (GFX-08).** `gfx.draw_text` measures a centred line's ink with the font that really draws it on the supersampled layer (the 1x font's rounded advances put a headline up to 3 px off its button's axis). Applies to every ink-centred line.

- **Caption accent words (GFX-15).** The caption bed is as dark as the darkest emphasis / highlight colour needs (it was sized for the white only: a blue `100%` on a maroon shirt read 1.95:1).
- **QC measurement at 60 fps (thresholds unchanged).** GFX-08 needs an element still for ±0.05 s, not just between neighbouring frames (ease-out tails crept < 1 px a frame); GFX-15 / GFX-20 skip glyphs the person cuts when measuring type size, and GFX-20 compares the type size a template logs (`El(..., size=)`, `size` in elements.jsonl; `text_behind` logs it).
- **`text_behind` exit** is a fade with a slight lift (the larger drift rounded into uneven steps at 60 fps, MOT-01).

### Changed
- **`end_card`** has its own layout (no longer the `cta` cutaway's): display type scaled from the canvas, the headline wrapped to two balanced lines when one does not fit, button / handle / optional `logo` / `qr` scaled with it, the block centred in the safe zone (shrinks to fit it), every element on one centre axis, at any canvas size. Golden frame `end_card.png` regenerated for it.
- **Roto cards place themselves** in the free space beside or above the head (`roto.place: auto`, or a card's `place` param): from the subject matte over the slot, the largest scale (down to `roto.min_scale`) at which the presenter covers at most `roto.max_cover` of the card, on the brightest free wall. When nothing fits, the designed position stays and GFX-27 judges it.

### Added
- **QC gate GFX-27** (roto card hidden by the subject): mean share of a roto card's area covered by the subject matte over its hold; WARN above `roto.occlusion_warn` (0.40), FAIL above `roto.occlusion_fail` (0.65) (knowledge-base/DECISIONS.md). `cves review` turns it into a `roto_hidden` finding at the card's time. `cves qc` now measures 96 gates.
- New style keys `craft.behind.smooth_s`, `light`, `dark`, `auto_bed` and the `roto:` section (default.yaml, docs/STYLE.md).
- Tests on synthetic media: auto colour on a light and a dark wall, size harmonisation, the face-track smoothing at 60 fps, monotonic roto entries at 24 / 30 / 60 fps, free-space placement and GFX-27 (`tests/test_gfx_fixes.py`).

## [0.4.0] - 2026-11-19

### Added
- **Review loop** (`cves review build|apply|signoff|show`, workstream F, docs/REVIEW.md): Claude watches the render, not the plan. `cves review build [vNNN|master]` writes a never-overwritten review pack per round, `Edit/review/rNNN/`: one contact image per cut (frames -2..+2, the cut frame and flagged frames marked) plus an index sheet, the hook at 10 fps for its first 3 s, the payoff window and the end card; `audio.json` (BS.1770 loudness per section, vocal-to-music ratio in the speech band from the stems, clicks at every cut, silence gaps, end tail, `earshot measure` when installed); `findings.json` (`{id, severity, t, kind, message, patch?}`) and `REVIEW.md` with a rubric Claude answers by looking. Detectors: black / white / one-frame flashes at cuts, duplicate frames, luma jumps across hard cuts, captions changing 1-2 frames off a cut, micro shots, audio pops at cuts, music masking the voice, a dead hook (`structure.hook_change_s`), a short end card, section level steps, silence, a cut-off audio tail. QC FAIL / WARN gates and the critique's restraint budget become findings (read, not re-measured). Cuts are refined to the frame where the picture really changes (`cuts.json` records the offset).
- `cves review apply` applies only the safe patches (`music.bed_lu`, `end_card.duration`), keeps comments when the text patch verifies, backs up `edit.yaml` and records what it applied; `cves review signoff --verdict ship|revise --notes` journals the verdict and every finding still open. Loops are capped at `review.max_rounds` (3) in `Edit/review/state.json`: round 3 says the cap is reached, a 4th round is refused until the sign-off.
- Journal events `review`, `review-apply`, `review-signoff` (docs/LEARNING.md); style section `review:` (25 keys, docs/STYLE.md); `/cves:review` and the review loop in the `video-editor` skill (render → qc → critique → review → fix → re-render, until 0 FAIL and no high findings, before the owner sees a cut); `tests/test_review.py` with seeded defects.
- **Senior sound** (v0.4 WS H, docs/SOUND.md).
  - **Music phrases.** `beats.phrases()` labels the music's sections on bar lines from the bar energy and a novelty curve (energy step + chroma change): `intro`, `build` (the bars rising into a drop), `drop`, `body`, `break`, `outro`. `cves beats` prints them and stores them in `beats.json`.
  - **Phrase alignment.** `beats.story_moments()` gives the hook (`music.hook_beats` [H] / `hook_cut`), the turn (`music.turn_beats` [P, A] / `turn_cut`, else the end of the hook) and the payoff (the drop moment, now falling back to the `aroll.snap` reveal). With `music.phrase_align: true`, the auto drop pick prefers the drop whose build starts on the turn; the drop still lands exactly on the payoff, and loop seams stay on downbeats. `mix.json` records the sections and the story alignment.
  - **Automatic risers and impacts** (`cves.sound.accents`, part of `mix.all_cues`):
    - a riser whose peak resolves on the payoff, and one into the hook (or out of it, when the hook opens the video);
    - a downbeat hit on the payoff, and impacts on reveals that have no low hit of their own.

    Only on picture events, never doubled, and limited by the new restraint budget `creative.sound_accents_per_30s` (3). Every decision is logged in `mix.json accents`; turn them off with `edit.yaml sfx.auto: false`.
  - **Voice-envelope ducking** (`mix.duck_mode: envelope`, the new default). The music gain follows the voice-band RMS envelope, with a 40 ms attack, a release from the syllable rate (250-400 ms) and the depth from `sound.duck_*`. `gate` keeps the v0.3 fixed dips.
  - **SFX bank** (`cves.sfx`, `assets/sfx/manifest.yaml`). Every sound has a category (whoosh, impact, riser, ui, pop, transition, ambience), an intensity (soft / medium / hard), a measured duration, peak, loudness and peak time, a licence and a source. Cues can name a role, `@impact:hard`, instead of a file; recordings are preferred over synthesized sounds at the same intensity. There are three banks, later winning: repo, user (`~/.cves/sfx`, `$CVES_SFX`) and project (`Music/sfx`).
  - **`cves sfx list | fetch | add | check`.** `fetch` searches Openverse, plus Freesound when `FREESOUND_API_KEY` is set, keeps CC0 only, decodes downloads as audio only (temp folder, ffmpeg to 48 kHz mono WAV) and records the source URL and licence in the bank's manifest and CREDITS.md.
  - **15 house sounds synthesized by CVES** (CC0; `tools/make_sfx.py`, numpy, deterministic): three risers that resolve on their peak, four impacts, three whooshes, a swish, two pops, a tick and a room tone (1.5 MB). They are judged with earshot; see DECISIONS.
  - **QC gates** SND-32 (an automatic riser peaks within 1 frame of its target) and SND-33 (the drop section starts on the payoff, on a downbeat; loop seams on downbeats), both WARN to start. Automatic risers are judged by SND-32 and SND-07 instead of SND-08. `cves qc` now measures 95 gates (QC-GATES.md: 183 rows).
  - **New style keys:** `sound.accents.*`, `sound.phrase_tolerance_s`, `mix.duck_*`, `music.phrase_align`, `phrase_min_bars`, `build_min_rise_db`, `build_step_db`, `phrase_turn_weight`, `hook_beats`, `turn_beats`, `hook_cut`, `turn_cut`, `creative.sound_accents_per_30s` (default.yaml, docs/STYLE.md).
  - **Docs and tests.** docs/SOUND.md; MUSIC.md, CONTRACTS.md, SFX-METHOD.md, the `video-editor` skill and `/cves:music` updated. `tests/test_sound.py` covers phrases on a synthetic song, the drop on the payoff, the phrase-aligned drop pick, envelope ducking, the riser resolving on its target, the budget, the manifest, and a mocked CC0-only fetch.
- **Treatments** (`cves treatments list|make|render|compare|pick`, workstream G of v0.4, docs/TREATMENTS.md): 2-3 distinct creative takes on one approved edit plan. Built-ins `punchy`, `cinematic` and `minimal` (`engine/cves/styles/treatments/`); `PROJECT/treatments/*.yaml` add or override them. Each is a style overlay (keys of `default.yaml` only) plus structure hints that `make` applies to a copy of the plan in `Edit/treatments/<name>/`: cut density (B-roll shots split into wide + punch-in, or merged into holds within `grammar.max_shot_s`; drawn cutaways capped by information value), a punch-in on a key word (`aroll.snap`, CUT-05-safe), the transition family (cutaways, B-roll entries at sentence starts, explicit transitions, end card), the caption preset (per-video caption look keys give way), roto kept or dropped, the music bed, drawn templates swapped for motion pieces with mapped params (`stat` → `m_stat_counter` in the built-ins; `checklist` → `m_list_build` is mapped but not used by them, since its row slide crosses the PLAT-01 margin on 1080×1920), and slow pushes on B-roll. `plan.json` records every change and the plan metrics (cuts, mean shot, caption style, transitions, punch-ins, graphics, bed, motion energy).
- **Treatment style layer**: `Edit/treatment.yaml` (`style:`) merges after inspire and before Brand and `edit.yaml`, so brand rules still win (docs/CONTRACTS.md §1, docs/STYLE.md). `_sources` shows `treatment:<name>`; `cves validate` checks its keys; `edit.yaml treatment:` names the plan's treatment.
- **Proxy renders**: `cves treatments render` renders each treatment at `treatments.proxy_scale` (0.5) through the normal renderer (`render.render(..., proxy=)`: timeline and exposure planned at full size, then the canvas and face tracks scaled; existing plates and mattes resized as they decode, never re-ingested) and encodes with `encode.proxy_video_args` (x264 `veryfast`, crf 26). Full-quality renders and encodes are unchanged. A treatment folder is a `project.Variant` (its own plan and outputs, the project's ingest artefacts).
- **Comparison**: `cves treatments compare` writes `Edit/treatments/compare/sheet.jpg` (rows = treatments with their label and metrics, columns = the same timecodes, labelled), `compare.mp4` (stacked, or `--sequential` with each treatment's own sound) and `compare.json`.
- **Pick + learning**: `cves treatments pick <name>` promotes the treatment's plan to `Edit/edit.yaml` (backup `edit.yaml.bak-<time>`), its layer to `Edit/treatment.yaml`, and journals a `treatment-pick` event (choice, offered, goal / client / platform, metrics, diff). `cves learn mine` proposes `treatments.prefer` per client or goal from repeated picks; build facts now include the treatment.
- **Style keys** `treatments.offer`, `prefer`, `proxy_scale`, `proxy_preset`, `proxy_crf`, `compare_points`, `compare_thumb`, `compare_max_s`, `compare_layout` (default.yaml, docs/STYLE.md).
- **Plugin**: `/cves:treatments`; the `video-editor` skill offers 2-3 treatments as proxies after the edit plan when the brief is open or creative (step 5b, §2b).
- `tests/test_treatments.py`: built-ins valid, layer order, measurably different plans on the vertical A-roll and landscape voiceover demos, project overrides, pick promotes + journals + mines, proxies at half size, the comparison sheet.
- **Motion craft** (workstream I, docs/MOTION.md "Craft", `engine/cves/craft.py`). Every move is style-driven (`craft.*`), works on any canvas, is deterministic, and counts against the restraint budget (new `creative.craft_per_30s`, reported by `cves critique` and warned by `cves render`).
  - **Text behind the speaker**: the `text_behind` roto template draws big type between the background plate and the subject matte, placed from the smoothed face landmarks (eye midpoint, head top, chin) and following the head by `craft.behind.track`. With no matte for a segment the render degrades gracefully: an empty matte, and the type lifts clear above the head (`craft.behind.no_matte`). Entries `rise` (letters rise out from behind the head) or `slam`; the type fits the tightest view of its shot (a snap punch-in included), so it never re-fits mid-shot or leaves the safe zone. Roto templates now get `face`, `face_at(t)`, `k`, `matte_ok`, `view` and `seg_view` in ctx.
  - **Speed ramps** (`ramp:` on a `broll:` shot or `video_broll` params): an eased speed curve (keys or the presets in `craft.ramp.presets`), normalised to the shot's `in` / `out`, strictly increasing; frame blending (crossfade when slow, a shutter average when fast) or nearest frame; the shot's own sound muted or tape-varispeed (`craft.ramp.audio`).
  - **Camera moves** (`camera:` on a `broll:` shot, and on `image` / `video_broll`): push, pull, pans, handheld drift (seeded smooth noise, with roll) on eased curves; **2.5D parallax** on stills with a `depth:` map or matte (two planes, inpainted background).
  - **Match cuts** (`match: saliency | centroid` on a `broll:` shot): the incoming shot is scaled and offset so its salient shape sits on the outgoing shot's (`craft.match.*`); `craft.find_in` searches a clip for the best-matching in-point.
  - **Transitions library**: `whip_pan`, `zoom_through`, `mask_wipe` (bar / circle / matte), `luma_fade`, `glitch_lite`, `light_leak` (procedural, no media), `dip`, alongside whip / glitch / fade. Durations `transitions.<kind>_s`, looks `craft.transitions.*`, cues in `sound.transition_sfx`. **Rate limit**: a transition within `craft.transitions.min_gap_s` of the previous one, or a kind beyond `creative.transition_kinds_max`, becomes a cut at render (printed).
  - **15 new HTML motion pieces** (30 in total): `m_map_route`, `m_timeline`, `m_before_after`, `m_comment_pop`, `m_notification_stack`, `m_price_tag`, `m_rating_stars`, `m_checklist_tick`, `m_ticker`, `m_countdown`, `m_quote_portrait`, `m_karaoke` (+ `_roto`), `m_spec_callouts`, `m_three_up`, `m_follow_card` (+ `_end`). Seek-safe, one logged element per text block, cues on entry frames, style tokens only, laid out for 9:16 and 16:9.
  - `tools/make_demo.py --craft`: the aroll demo with text behind the hook (slam + snap punch-in) and the CTA, a ramped B-roll shot with a push, a whip pan, a light leak into `m_follow_card_end` and `m_notification_stack`; the voiceover demo with a 2.5D push on a still with a depth matte and a match cut between two drawn orb clips.
  - `edit.yaml` validation knows the new transition kinds and the `broll:` keys `ramp`, `camera`, `match`, `out`, `depth`.
  - `tests/test_craft.py`: occlusion order (type hidden where the matte is 1), the no-matte fallback, ramp monotonicity and endpoints, frame blending, varispeed, deterministic transitions, the rate limit, camera moves, parallax layers, match-cut alignment, the restraint count, schema, and all 30 pieces rendering a frame at 1080x1920 and 1920x1080.

### Fixed (v0.4 integration)
- Captions no longer vanish during a snap punch-in that has no roto type; QC RET-12 only counts caption keywords on frames where the caption is drawn.
- The stock demo (`tools/make_demo.py`) passes QC with 0 FAIL (it failed FRAME-03, GFX-15, RET-09 and RET-12 since v0.2); golden frames regenerated.
- `m_list_build` keeps its slide-in inside the 60 px margin on 9:16 (PLAT-01). `lower_third` card: accent bar aligned to the card edge (GFX-08). `kinetic_caption_emphasis`: long words stay inside the safe zone.

### Changed
- QC's transition windows (MOT-12, the A-roll pass, GFX-08) read `transitions.<kind>_s` from the style, the same window the renderer draws (they were fixed, so `fade` was exempted for 0.12 s while it is drawn for 0.2 s).
### Changed (v0.4 workstream J: weak spots)
- **The v0.2 UI cutaways and roto cards lay out per canvas** (`search_rows`, `card_list`, `stat` / `counter`, `browser_list`, `map_card`, `big_words`, `listing_card`, `top3_card`). They are relative templates now (`DESIGN = True` is gone from `cutaways.py` / `roto.py`); `templates/_layout.py` picks a tall arrangement (9:16: the original 1080×1920 numbers, frames pixel-identical to v0.3), a square one (scaled to fit the safe zone) or a wide one (two-column `card_list` and `browser_list` rows from 4 items, wider rows and panels, type scaled up to fill the zone, roto cards filling the zone height). Every element stays inside the safe zone on square and wide canvases. `browser_list` with 4+ rows grows its card on 9:16 instead of letting the pill cover the 4th row.
- **No 4K softness**: relative templates lay out at a 1080 short side and are rasterised at the canvas's real resolution (`gfx.set_raster`, `G.PW` / `G.PH` / `G.R`, `G.px`): coordinates, type, strokes, icons, shadows and legibility beds scale inside `G.layer`, so 3840×2160 and 2160×3840 graphics are drawn at 4K (edges about 2× sharper than the old scaled path). The picture templates (`image`, `video_broll`, `screen_rec`, `pip`, `split`, `overlay_render`) sample their source into layer-sized buffers too (frames identical at 1080 canvases). A module that can't opts out with `RASTER = False`; in a raster-scaled call `ctx["aroll"]` stays at the real canvas size.
- **HDR B-roll**: PQ / HLG clips in `broll:` and every media template are tonemapped to SDR BT.709 through the A-roll ingest chain (`ingest.sdr_source` → `Edit/conform/<name>-<key>.sdr.mkv`, lossless FFV1, prepared by `cves render` before its workers start). New style key `ingest.hdr.broll` (default `true`).
- **`cves import-edits` maps B-roll and motion tracks**: a B-roll shot moved / trimmed / deleted / re-speeded in Kdenlive or Resolve maps to `broll[k].start/end/in/speed` (V2 on the A-roll spine, V1 on the voiceover / music / broll spines); a trimmed motion piece (`m_*`, in `cutaways:` or `chest:`) re-times its `at` / `duration`. B-roll layers in `layers.json` carry `edit_ref: broll.<id>`.
- **QC GFX-15** samples text contrast only on frames whose bbox is static on both sides (as GFX-08 does), so a word still entering inside a static line is no longer measured by accident of 1 px rounding. No threshold changed.
- `card_list` icons are their own elements (`list.item<k>.icon`, carrying the icon asset), so MOT-14 judges the icon's real size instead of the whole row's (a 4K landscape row looked like a 1.28x upscale of the 512 px icon).
- **QC PLAT-10**: the caption plate margin (26 px) is px at a 1080 short side, like the cap-height line beside it (the caption shadow scales by `U`; on a 4K master every caption measured 29 px). Unchanged at 1080 and below; knowledge-base/DECISIONS.md.
- `browser_list` row checks are their own elements (`browser.row<k>.check`), so their pop cue lands on a logged visual event (SND-07).
- `tools/make_demo.py --edit legacy` (+ `tools/demo_edit_legacy.yaml`): a demo that uses the legacy cutaways and roto cards, to see the three arrangements.

### Added
- `tests/test_weak_spots.py`: legacy layouts on 16:9 / 1:1 / 4:5 / 4K (inside the safe zone, filling it), two columns on landscape, the 9:16 design numbers, 4K edge sharpness vs the scaled path, PQ and HLG B-roll tonemapping (matches the A-roll chain), the import-edits B-roll / motion mapping, and **the full Kdenlive round trip** (export → edit `project.kdenlive` and its subtitles → melt render → `import-edits` → `edit.yaml` → re-render; skipped without melt).
- `docs/RESOLVE-CHECKLIST.md`: the step-by-step verification script for the first person with DaVinci Resolve (not installed on the build machine).

## [0.3.0] - 2026-11-19
CVES becomes a senior editor for any video: motion design, inspirations it can hear and feel, any frame size and spine, viral mode, and a learning loop a person stays in charge of.

### Added
- **Self-learning** (`cves learn`, docs/LEARNING.md): every project keeps an append-only `Edit/journal.jsonl` (build facts, edit.yaml revisions, QC results, deliveries, editor changes from `import-edits`, critiques, plus notes, ratings, approvals and platform results logged with `cves learn note|rate|approve|reject|results`). `cves learn mine` turns all journals into candidate patterns (repeated human corrections, decisions that go with better ratings or results with n ≥ 3, recurring notes); `promote` / `reject` / `forget` keep a person in charge of every change. `cves learn study <folder>` measures great reference videos (ad vs viral) into `~/.cves/taste/study.json`.
- **Learned style layers**: `knowledge-base/taste/learned.yaml` (shared, anonymised, via `--share`) and `~/.cves/taste/learned.yaml` (personal), scoped by goal / platform / client. Merge order is now default → repo learned → personal learned → preset → inspire → Brand → edit.yaml (docs/CONTRACTS.md §1). Shared patterns are listed in `knowledge-base/TASTE.md`; shared rules become `LESSONS.md` rows.
- **`cves critique [vNNN|master]`**: a senior-editor review pack in `Edit/critique/` (contact sheet per shot and key moment, energy / interrupt timeline, measured facts, restraint-budget usage, and a fixed 10-line rubric in `CRITIQUE.md` that Claude scores and logs with `cves learn rate --by claude`).
- **`knowledge-base/CREATIVE.md`**: the creative method: creative direction before the plan (`Edit/DIRECTION.md`), the restraint budget, contrast and rhythm, taste checks.
- **Style keys** `creative.signature_per_30s`, `creative.transition_kinds_max`, `creative.motion_pieces_per_30s`, `creative.accent_colors_max` (advisory budget read by `cves critique`).
- **Plugin**: `/cves:learn` and `/cves:critique`; the `video-editor` skill adds the creative-direction step, the critique pass after QC, and journaling of notes and ratings.
- **Viral mode** (workstream D, docs/VIRAL.md): `edit.yaml goal: ad | viral` (default ad, validated). `goal: viral` layers the new `styles/viral.yaml` preset right after `default.yaml`: faster pacing bands, a hook within 1 s, pattern interrupts at least every 2.5 s, cuts on the beat, punchier `pop` captions, a louder SFX share. Ads keep every existing behaviour.
- **Platform profiles** (`styles/platforms.yaml`, `cves.platforms`): `platform.target: reels | tiktok | shorts | youtube | meta_feed | meta_stories` with UI safe zones as fractions of the frame (right rail, bottom caption area, top bar), the caption line, ideal / maximum duration and loudness. A target fills `platform.safe_zone`, `sound.master_lufs` and `sound.true_peak` unless a style layer sets them; PLAT-02 now computes the zone from the real frame size (any canvas).
- **Retention gates RET-24 to RET-32** (`engine/cves/qc/retention.py`): hook visual change by `structure.hook_change_s`, hook text or strong subject by 1 s (viral), longest pattern-interrupt gap (`rhythm.interrupt_max_s`), effect soup (`rhythm.interrupt_min_s` sustained), loop seam (`structure.loop`), payoff in the last `structure.payoff_window`, platform duration band (FAIL above the platform maximum), dead air (FAIL for viral, WARN for ads), cuts on the guide / music beat. Thresholds in DECISIONS.md; `cves qc` now measures 93 gates (QC-GATES.md: 181 rows).
- **Platform sound slot** (`cves.guide`): `music: {slot: platform, guide: <track | beats.json | tempo>, sound: ...}` for organic posts cut to a trending sound. The mix carries no music, `Edit/stems/guide.wav` holds the guide (laid track or click track), `cves beats` snaps cuts to a reference-track guide, and `cves deliver` adds `<master>.guide.wav` + `POSTING.md` (sound, start point, drop, in-app steps) and a `music_slot` manifest block. Ads can't use the slot (validation error); SND-04 checks the music stem is silent in slot mode.
- New style keys: `platform.target`, `rhythm.*`, `structure.*`, `retention.*` (default.yaml, docs/STYLE.md).
- Knowledge base: `modules/viral-playbook.md` (hook taxonomy, structures, retention devices, platform norms, trending sounds, what not to do), RULEBOOK §12, CHECKLISTS §12, DECISIONS entries for every new threshold. The skill and `/cves:new-edit`, `/cves:story`, `/cves:qc`, `/cves:deliver` describe the `goal: viral` steps.
- `tests/test_viral.py`: goal layer, platform zones at 1080×1920 and 1920×1080, every retention gate on synthetic renders, the slot delivery on the demo.
- **Inspire v2: see, hear, feel, mix and match** (WS B; docs/STYLE.md "How `cves inspire` fills it").
  - **Hear** (`inspire_audio.py`): voice vs music (syllable-rate modulation, no model), bed level under the words, ducking, tempo and beat grid (via `beats.analyse`), SFX density, drop-outs, music energy curve → `sound.bed_lu`, `sound.duck_other_db`, `rhythm.*`.
  - **Feel** (`inspire_feel.py`): cut-on-beat ratio vs chance, cut-rate curve and shape, hook timing, pattern-interrupt gaps, loop seam, energy arc, duration → `rhythm.*`, `structure.*`, and `music.sync: cuts` when the references cut on the beat.
  - **See** (`inspire_see.py`): a contact sheet per reference (`Edit/inspire/<ref>-sheet.jpg`, 12 labelled frames at shot middles) and measured grain, tone curve, saturation, temperature, vignette, letterbox, aspect and motion blur (notes in `_inspire.aesthetics`); `Edit/inspire/aesthetic-review.md` is the rubric Claude fills by looking at the sheets.
  - **Mix and match** (`inspire_mix.py`): every reference is measured on its own; per dimension (grade, palette, captions, pacing, sound, motion, structure) the source is forced (`--mix`), an authority from `Inspirations/refs.yaml` (`rank`, `weight`, `kind`, `use`, `notes`), pooled when the references agree, else the single strongest ranked reference. No more averaging of looks that disagree.
  - `Edit/inspire/REPORT.md`: see / hear / feel per reference and the chosen mix, written for a human editor (also on `--dry-run`).
  - `cves inspire --mix "dim=ref,..." --refresh --min-conf`; `--dry-run` prints a per-dimension table (candidates per ref, chosen value, source, confidence). Per-reference measurements are cached in `Edit/inspire/cache/`.
  - Style sections `rhythm:` and `structure:` (plan-time targets, neutral `null` defaults). Thresholds in knowledge-base/DECISIONS.md "Inspire v2".
- `tests/test_inspire_v2.py` on synthetic references (`tests/_inspire_refs.py`: a click track cut on the beat that loops, the same cut half a beat late, a voice over a bed).
- **Motion layer** (docs/MOTION.md, WS A of v0.3): HTML/CSS motion pieces rendered by headless Chromium (Playwright 1.58.0) to RGBA frames, driven only by `window.__seek(t)` (deterministic: no wall clock). Our own JS runtime (`engine/cves/motion/runtime.js`: easing incl. back / elastic / spring, tween, stagger, word split, timeline, fake motion blur); no third-party JS. Colours, fonts (assets/fonts via `@font-face`, Noto fallbacks for Indic scripts), the type scale, motion tokens and the safe zone come from the style as CSS variables. Frames are cached per (html, runtime, params, style subset, size, fps, duration) in `PROJECT/Edit/motion/<hash>/`; `render.render()` pre-renders every motion piece once before its worker pool starts.
- **15 motion templates** `m_kinetic_title`, `m_glass_card`, `m_stat_counter`, `m_list_build`, `m_lower_third`, `m_quote`, `m_highlight_words`, `m_progress`, `m_callout`, `m_logo_sting`, `m_split_reveal`, `m_compare`, `m_steps`, `m_chart_bars`, `m_cta` (+ `_roto` / `_end` variants where sensible). Usable as full-screen cutaways or as overlays over A-roll (`chest:`, logged with role `chest` so every chest gate applies, with their own exit animation); any aspect ratio. Each logs one element with a stable id, its visible text per frame and its own SFX cues.
- **User motion pieces:** folders with `piece.html` + `meta.yaml` in `~/.cves/motion/` and `PROJECT/Brand/motion/` become `m_<name>` templates.
- **`cves motion list | preview <piece> [--params JSON] [--size WxH] [--out f.png|f.mp4] [--at t]`:** contact sheet, one frame or a clip.
- **Style keys** `motion.ease`, `energy`, `blur_on_fast`, `blur_max_u`, `shutter`, `exit_s`, `type_ratio`, `radius_u`, `glass_alpha`, `safe`, `safe_fallback`, `hero_min_gap_s` (render warns when two hero pieces sit closer than this).
- **Install:** `playwright==1.58.0` in requirements.txt and the `motion` extra; both installers run `python -m playwright install chromium`; `cves doctor` checks Playwright and Chromium; CI installs them (`--with-deps` on Ubuntu). A missing Chromium is a one-line SystemExit with the install command.

- **Any frame size, natively** (docs/FORMATS.md): style `canvas.size` (9:16 default; 4:5, 1:1, 16:9, 2.39:1 or any even size;
  `edit.yaml project.size` wins; `platform.size` becomes a legacy alias) and `canvas.safe_zones` per aspect. `gfx.set_canvas`
  sets `G.W` / `G.H` / `G.U` per process (re-set inside spawned render workers); render, captions, templates, the moodboard,
  control-mode layers, encode, QC, `cves inspire` and the cover follow it. Templates lay out on any canvas: relative templates
  scale by `G.U`, legacy fixed 1080×1920 modules (`DESIGN = True`: cutaways, roto) are fitted into the safe zone, `NATIVE`
  modules draw at the canvas resolution. Identity at 1080×1920 (golden frames unchanged).
- **Timeline spines** (`edit.yaml spine: aroll | voiceover | music | broll`, `engine/cves/spines.py`): a VO (recorded or
  ElevenLabs, `voiceover: {asset | file}`) tightened and transcribed by `cves ingest`; a music-led cut; a shot-led cut with
  the clips' own sound. Face-only stages skip when there is no A-roll.
- **The `broll:` track**: shots in cut time `{src | asset, start, end, in, speed, framing: fill | fit | kenburns, kenburns,
  anchor, after, transition, audio, gain}`, rendered by the new native `broll_shot` media template from any source size,
  rotation and frame rate (fill crops, fit sits on a blurred fill, stills get ken burns). On the aroll spine the same track
  is cutaway footage over the presenter, with captions continuing over it. Style sections `broll:` and `autocut:`.
- **`cves autocut`** `[--every beats|downbeats|bars] [--bars N] [--min-shot S] [--folder DIR] [--apply]`: proposes a
  `broll:` track whose cuts land on the music grid (cut time, from `cves beats`).
- **QC status N/A**: presenter gates (FRAME-*, COL-03..10/12, CUT-03/05, RET-22, GFX-25/26) on voiceover / music / broll
  edits, voice gates on music / broll edits and caption gates on caption-free edits report N/A, never FAIL; `qc.json` gains
  `na`. MOT-14 judges B-roll shots by the scale applied to source pixels (WARN > 1.0×, FAIL > 1.5×).
- `tools/make_demo.py --kind aroll|voiceover|music|broll --size WxH` (drawn clips incl. a rotated phone clip, 25 fps, a still);
  `tests/test_formats.py`, `tests/test_spines.py`.

### Changed
- `sound.bed_lu` from inspire uses the HEAR bed estimate instead of ebur128 p8 vs p60.
- **Reframes from any master** to any aspect (a narrower target crops the width, a wider one the height; decimal aspects
  such as `2.39:1`); the 9:16 → 16:9 blurred-fill path is unchanged.
- QC analysis frames, margins (`platform.margin` × `G.U`) and caption wrap width follow the canvas; the moodboard keeps the
  canvas aspect; `cves inspire` measures on the project canvas (workers get it through their job args).
- The mix reads a video's sound track through ffmpeg when librosa cannot (B-roll `audio: true`, `video_broll` audio).
- Lint L4 points at `canvas.size`.

### Fixed
- Pop / one-word captions are opaque from their first frame (a fading word failed GFX-15 over bright footage).
- The caption legibility bed reaches past an outline stroke (`legible_bed(reach=)`), and captions over B-roll assume the brighter `legibility.video_bg_broll` (#C8C8C8): outlined viral captions over bright B-roll now pass GFX-15 without loosening it.
- `cves critique` counts B-roll footage as shots, not animated graphics (the restraint budget no longer flags B-roll edits).
- `cves inspire` in a project without `Raw/` no longer crashes looking for footage to compare the grade with.

## [0.2.0] - 2026-11-18
The engine becomes a general autonomous editor: no look, client or footage format is hard-coded.

### Added
- **Style profile** (`cves.style`, `styles/default.yaml`, docs/STYLE.md). Merge order: neutral defaults → preset → `Edit/style.yaml` → `Brand/style.yaml` → `edit.yaml style:`. It drives the grade, captions, transitions, framing, pacing, motion, sound levels, delivery settings and every QC threshold. `profitcast-dark` is now just one optional preset.
- **`cves inspire`:** measures the client's reference edits (pacing, cutaway share, grade, palette, captions, transitions, framing, loudness) into `Edit/style.yaml`, with evidence and confidence per key.
- **`cves validate`:** schema checks for `edit.yaml`, `selects.yaml` and style keys, with YAML paths and did-you-mean suggestions; render and build run it first.
- **Any-footage ingest** (docs/INGEST.md): probe; rotation; SAR; VFR → CFR; HDR (PQ/HLG) → SDR tonemap; face-aware crop for landscape sources; multi-source selects; source or explicit frame rate; whisper language setting and auto-detect; chunked transcription for long files; `voice_chain.json`; Noto fonts for 7 Indic scripts.
- **Media layer** (docs/MEDIA.md): `image`, `video_broll`, `screen_rec`, `pip`, `split` and `overlay_render` templates; an `assets:` block; `cves assets add|list|check|todo` with provenance; the Magnific / ElevenLabs connector workflow.
- **Generic templates** (docs/TEMPLATES.md): title_card, stat/counter, checklist/list, comparison, quote/testimonial, steps/timeline, logo_reveal, progress_bar, chart, cta, end_card, lower_third and kinetic emphasis. Templates are auto-discovered, including per-client ones in `Brand/templates/`.
- **Caption styles:** word_reveal, one_word, highlight, box, karaoke, pop and bounce, with outline, emphasis, emoji, script fallback and RTL.
- **Beat sync** (docs/MUSIC.md): `cves beats` covers tempo, downbeats and drops. Sync modes are drop, cuts and full, with bar-aware music fit and loops. Whooshes are placed by their measured peak, and repeated SFX are varied.
- **Delivery** (docs/DELIVERY.md):
  - `cves deliver` writes versioned `Export/vNNN/` folders with the master, SRT/VTT, transcript, cover and manifest;
  - variants: 4:5 / 1:1 / 16:9 face-aware reframes, hook / end-card / music variants, and 15 / 30 s cut-downs;
  - `qc.json` stamp: delivery refuses unless the stamp shows 0 FAIL and its sha256 matches the master;
  - the plugin hook blocks copying or uploading an unapproved file.
- **Control-mode round trip:** `--only` takes cutaway, segment, roto, chest and end-card ids, plus time and frame ranges; `cves control update` re-renders single layers; `cves import-edits` maps Resolve, Kdenlive, FCPXML and OTIO edits back into `edit.yaml` with an import report. Exports follow the project's frame rate and size.
- **QC:** 84 gates on the delivered file (was 36) and 17 stage gates, covering motion, graphics, caption timing, colour, frame, sound sync and asset provenance. `tools/gate_status.py` keeps QC-GATES.md in sync with the code.
- **Synthetic demo** (`tools/make_demo.py`), unit and golden-frame tests (`tests/`), and GitHub Actions on macOS, Windows and Linux. `tools/lint.py` blocks `/tmp`, missing `encoding=`, hard-coded frame rates or canvas sizes, brand names and template colour literals.

### Changed
- **Render streams** frames and element records to disk, so long videos stay flat in memory. The exposure balance meets at cut frames.
- **Halo fix:** the relight now un-mixes matte edges, which fixes the halo.
- **Chest graphics** hold still over a shot; captions clear the face on every frame.
- **Neutral defaults:** project folders default to `~/CVES Projects` (`$CVES_CLIENTS` or config `clients_root`). The marketplace is `cves`, installed with `/plugin install cves@cves`.
- **Docs and knowledge base** are generic: per-client values point to the style keys that set them.

### Removed
- The first test ad's project files, client names and brand logos. The synthetic demo replaces them.

## [0.1.0] - 2026-11-18
First team release: the `edit.yaml`-driven renderer, an edit-plan moodboard, 36 QC gates, control-mode export to DaVinci Resolve / Kdenlive, the Claude Code plugin and the 73-video knowledge base. It was built and tested on one real ad.
