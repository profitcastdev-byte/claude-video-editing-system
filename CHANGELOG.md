# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

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
