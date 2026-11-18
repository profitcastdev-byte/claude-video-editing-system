# Changelog

All notable changes to CVES. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[SemVer](https://semver.org/). Every behaviour or tool change gets an entry (see CONTRIBUTING.md).

## [Unreleased]

### Added
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
- **Reframes from any master** to any aspect (a narrower target crops the width, a wider one the height; decimal aspects
  such as `2.39:1`); the 9:16 → 16:9 blurred-fill path is unchanged.
- QC analysis frames, margins (`platform.margin` × `G.U`) and caption wrap width follow the canvas; the moodboard keeps the
  canvas aspect; `cves inspire` measures on the project canvas (workers get it through their job args).
- The mix reads a video's sound track through ffmpeg when librosa cannot (B-roll `audio: true`, `video_broll` audio).
- Lint L4 points at `canvas.size`.

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
