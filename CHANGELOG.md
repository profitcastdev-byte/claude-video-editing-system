# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

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
