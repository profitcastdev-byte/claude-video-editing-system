# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

### Added
- **Inspire v2: see, hear, feel, mix and match** (WS B; docs/STYLE.md "How `cves inspire` fills it").
  - **Hear** (`inspire_audio.py`): voice vs music (syllable-rate modulation, no model), bed level under the words, ducking, tempo and beat grid (via `beats.analyse`), SFX density, drop-outs, music energy curve → `sound.bed_lu`, `sound.duck_other_db`, `rhythm.*`.
  - **Feel** (`inspire_feel.py`): cut-on-beat ratio vs chance, cut-rate curve and shape, hook timing, pattern-interrupt gaps, loop seam, energy arc, duration → `rhythm.*`, `structure.*`, and `music.sync: cuts` when the references cut on the beat.
  - **See** (`inspire_see.py`): a contact sheet per reference (`Edit/inspire/<ref>-sheet.jpg`, 12 labelled frames at shot middles) and measured grain, tone curve, saturation, temperature, vignette, letterbox, aspect and motion blur (notes in `_inspire.aesthetics`); `Edit/inspire/aesthetic-review.md` is the rubric Claude fills by looking at the sheets.
  - **Mix and match** (`inspire_mix.py`): every reference is measured on its own; per dimension (grade, palette, captions, pacing, sound, motion, structure) the source is forced (`--mix`), an authority from `Inspirations/refs.yaml` (`rank`, `weight`, `kind`, `use`, `notes`), pooled when the references agree, else the single strongest ranked reference. No more averaging of looks that disagree.
  - `Edit/inspire/REPORT.md`: see / hear / feel per reference and the chosen mix, written for a human editor (also on `--dry-run`).
  - `cves inspire --mix "dim=ref,..." --refresh --min-conf`; `--dry-run` prints a per-dimension table (candidates per ref, chosen value, source, confidence). Per-reference measurements are cached in `Edit/inspire/cache/`.
  - Style sections `rhythm:` and `structure:` (plan-time targets, neutral `null` defaults). Thresholds in knowledge-base/DECISIONS.md "Inspire v2".
- `tests/test_inspire_v2.py` on synthetic references (`tests/_inspire_refs.py`: a click track cut on the beat that loops, the same cut half a beat late, a voice over a bed).

### Changed
- `sound.bed_lu` from inspire uses the HEAR bed estimate instead of ebur128 p8 vs p60.

### Fixed
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
