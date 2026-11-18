# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

### Added
- **Motion layer** (docs/MOTION.md, WS A of v0.3): HTML/CSS motion pieces rendered by headless Chromium (Playwright 1.58.0) to RGBA frames, driven only by `window.__seek(t)` (deterministic: no wall clock). Our own JS runtime (`engine/cves/motion/runtime.js`: easing incl. back / elastic / spring, tween, stagger, word split, timeline, fake motion blur); no third-party JS. Colours, fonts (assets/fonts via `@font-face`, Noto fallbacks for Indic scripts), the type scale, motion tokens and the safe zone come from the style as CSS variables. Frames are cached per (html, runtime, params, style subset, size, fps, duration) in `PROJECT/Edit/motion/<hash>/`; `render.render()` pre-renders every motion piece once before its worker pool starts.
- **15 motion templates** `m_kinetic_title`, `m_glass_card`, `m_stat_counter`, `m_list_build`, `m_lower_third`, `m_quote`, `m_highlight_words`, `m_progress`, `m_callout`, `m_logo_sting`, `m_split_reveal`, `m_compare`, `m_steps`, `m_chart_bars`, `m_cta` (+ `_roto` / `_end` variants where sensible). Usable as full-screen cutaways or as overlays over A-roll (`chest:`, logged with role `chest` so every chest gate applies, with their own exit animation); any aspect ratio. Each logs one element with a stable id, its visible text per frame and its own SFX cues.
- **User motion pieces:** folders with `piece.html` + `meta.yaml` in `~/.cves/motion/` and `PROJECT/Brand/motion/` become `m_<name>` templates.
- **`cves motion list | preview <piece> [--params JSON] [--size WxH] [--out f.png|f.mp4] [--at t]`:** contact sheet, one frame or a clip.
- **Style keys** `motion.ease`, `energy`, `blur_on_fast`, `blur_max_u`, `shutter`, `exit_s`, `type_ratio`, `radius_u`, `glass_alpha`, `safe`, `safe_fallback`, `hero_min_gap_s` (render warns when two hero pieces sit closer than this).
- **Install:** `playwright==1.58.0` in requirements.txt and the `motion` extra; both installers run `python -m playwright install chromium`; `cves doctor` checks Playwright and Chromium; CI installs them (`--with-deps` on Ubuntu). A missing Chromium is a one-line SystemExit with the install command.

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
