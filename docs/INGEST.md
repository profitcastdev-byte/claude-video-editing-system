# Ingest

`engine/cves/ingest.py` turns any footage into what the rest of the engine expects: a cut list on a single frame grid,
a clean voice, one lossless plate per segment at the master canvas, mattes, faces and word timings.
Nothing about size, rate, language or look is fixed in the code: it comes from the style profile (`S = style.load(pr)`)
or from probing the sources.

## Steps

| step | command | reads | writes |
|---|---|---|---|
| `probe` | `cves ingest --steps probe` | every source | `ingest.json` `probes` |
| `transcribe_raw` | `cves ingest` | every source's audio | `raw_audio.wav`, `raw_words.json`, `raw_transcript.txt`, `sources/<slug>.*` |
| `select` | `cves select` (`--align-only`: the alignment report alone) | `selects.yaml` | `align/` (window transcripts), `ingest.json` (conform plans), `edl.json`, `voice/`, `voice_{raw,df,final}.wav`, `voice_chain.json` |
| `conform` | `cves ingest --steps conform` | `selects.yaml` | `ingest.json` (also run by `select` and `plate`) |
| `words` | `cves prep` | `voice_final.wav` | `words.json`, `ingest.json` `language_detected` |
| `plate` | `cves prep` | `edl.json`, `ingest.json` | `plate/<segment>.mkv` (FFV1 10-bit, canvas size, project rate) |
| `matte` | `cves prep` | `plate/` | `matte/<segment>.mkv` (gray FFV1, project rate) |
| `faces` | `cves prep` | `plate/` | `faces.json` |

## Sources

- The **primary** source is `edit.yaml project.raw` (else the first video in `Raw/`). It keeps the historic layout:
  `Edit/raw_audio.wav`, `raw16.wav`, `raw_words.json`.
- **Other sources** are `edit.yaml project.sources` (a list of project-relative paths) when given, else every other video in `Raw/`,
  plus anything a clip names with `src:`. Their audio and transcripts go to `Edit/sources/<slug>.wav`, `<slug>.16k.wav`, `<slug>.words.json`.
- With more than one source, `raw_transcript.txt` has one section per source headed `# src: Raw/<file>`: copy that path into the clip's `src:`.

```yaml
# Edit/selects.yaml
clips:
- {id: 01_hook, in: 0.20, out: 1.82, beat: H}                             # primary source
- {id: 02_broll_take, src: Raw/take2.mov, in: 12.4, out: 15.0, beat: P}   # another source
```

Clip ids must be unique across all sources. Every `edl.json` segment carries `src` (project-relative). Plates, mattes and
faces are built per segment, so they work unchanged; the speech gates read each segment's own source audio (`ingest.source_audio(pr, src)`).

## Probe

`ingest.probe_file(path)` records, per source (first video stream that is not cover art):

| key | meaning |
|---|---|
| `w`, `h`, `sar` | coded size and sample aspect ratio |
| `rotation` | display-matrix rotation (degrees, ffprobe convention), else the legacy `rotate` tag; normalised to 0..359 |
| `display` | the frame size our filters see: after ffmpeg's autorotate and the SAR fix (square pixels) |
| `r_frame_rate`, `avg_frame_rate`, `vfr` | VFR when the two differ by more than 0.5 % |
| `color_transfer`, `color_primaries`, `color_space`, `color_range`, `hdr` | HDR = transfer `smpte2084` (PQ) or `arib-std-b67` (HLG) |
| `pix_fmt`, `bit_depth` | depth from the pixel format (`yuv420p10le` → 10) |
| `audio` | codec, channels, rate of the first audio stream (`null` = none: ingest stops with an actionable message) |

## Conform

All conform work happens inside the single lossless plate decode (engine invariant: one lossless source path, no
intermediate re-encode). The *plan* is computed once per source and cached in `Edit/ingest.json` under `sources`,
keyed by path, mtime, size, canvas, rate and the `ingest.*` style keys. Change any of them and the plan is rebuilt;
delete `Edit/plate/` to rebuild plates (existing plate files are never overwritten).

Filter order per segment: `[SAR fix] [HDR→SDR] [fps] [crop] scale=W:H:lanczos [setsar=1]`.

- **Canvas**: `edit.yaml project.size` if set, else style `canvas.size` (default `[1080, 1920]`; `platform.size` is a legacy
  alias). Landscape footage on a landscape canvas is not cropped; a different aspect gets the face-steered crop below.
- **Spines** ([FORMATS.md](FORMATS.md)): this page is the `aroll` spine. On a `voiceover` spine `cves ingest` takes the VO
  (`edit.yaml voiceover: {asset | file}`) through extract → optional DeepFilterNet (`denoise`) → pause tightening (the
  rules below) → the voice chain → `voice_final.wav`, `voice_chain.json`, `edl.json` and `words.json`; `music` and
  `broll` spines only write `edl.json` (rate, canvas, duration). B-roll is never plated: it is framed at render time.
- **Frame rate**: style `platform.fps`. `source` (default) = the primary source's rate: its `r_frame_rate` when CFR,
  the nearest standard rate (23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60) to `avg_frame_rate` when VFR.
  An explicit rate (`[30000, 1001]`, `"30000/1001"`, `25`, `29.97`) overrides it. Sources at another rate, and every VFR
  source, get `fps=num/den`. Segment in/out points are snapped to the project frame grid. `edl.json` stores `fps` and
  `fps_rational`; `matte` writes at the same rate.
- **Rotation**: ffmpeg applies the display matrix automatically; probe swaps the display size so crop and scale are computed on the upright frame.
- **SAR**: non-square pixels are scaled to square first (`scale=trunc(iw*sar/2)*2:ih,setsar=1`).
- **HDR → SDR BT.709**: `zscale` (linearise at `ingest.hdr.npl` nits) → `tonemap=<ingest.hdr.tonemap>` → `zscale` to BT.709
  limited range, 10-bit, plates tagged BT.709. ffmpeg-full has `zscale` and `tonemap`. **Fallback** when they are missing:
  a matrix-only conversion (`scale=in_color_matrix=bt2020:out_color_matrix=bt709`): colours are re-matrixed but highlights
  are not tone-mapped, so the image looks flat and dim. `ingest.json` records which path ran (`tonemap: zscale | fallback-matrix-only`).
  **B-roll and media clips** are not plated, but they get the same chain: `ingest.sdr_source(path, S, cache)` runs an HDR
  clip through `_tonemap_chain` once into a lossless 10-bit FFV1 proxy (`Edit/conform/<name>-<key>.sdr.mkv`, BT.709-tagged,
  video only, rotation applied, timestamps kept) that the media templates decode instead (`cves render` prepares every
  referenced clip before its workers start). SDR clips are used as they are. Style `ingest.hdr.broll: false` turns it off.
- **Aspect**: when the upright source aspect differs from the canvas (by > 0.2 %), the source is **cropped** to the canvas aspect,
  then scaled. It is never squashed or letterboxed.
  - `ingest.reframe: face` (default): YuNet runs on the source at `ingest.face_crop.sample_fps` (frames are streamed through an
    ffmpeg pipe at ~640 px), the largest face's centre is interpolated over misses, median-filtered and Gaussian-smoothed
    (`smooth_s`), and placed at `anchor` (x for wide sources, y for tall ones). A path that moves less than
    `static_tolerance` × crop size is locked to a static crop (no micro-pans). Per segment the path becomes a piecewise-linear
    `crop` x/y expression (≤ 48 keypoints). No face anywhere → centre crop (`mode: center`).
  - `ingest.reframe: center`: always a centre crop.
- **plate_scale** = canvas px per source px (canvas width / crop width). Per source in `sources.<src>.plate_scale`; the top-level
  `plate_scale` is the largest over the sources in the edit (QC FRAME-11 reads it: > 1 means the plate is upscaled).

### Edit/ingest.json

```json
{"version": 2, "canvas": [1080, 1920], "fps": 23.976, "fps_rational": [24000, 1001], "primary": "Raw/take.MP4",
 "plate_scale": 0.625, "language": "en", "language_detected": "en",
 "probes": {"Raw/take.MP4": {"...": "probe_file() output"}},
 "sources": {"Raw/take.MP4": {"mtime": 0, "bytes": 0, "probe": {}, "canvas": [1080, 1920], "fps_rational": [24000, 1001],
             "sar_fix": false, "fps_convert": false, "tonemap": null, "tonemap_filter": null,
             "crop": null, "plate_scale": 0.625, "cfg": "..."}}}
```

`crop` when present: `{"axis": "x"|"y", "w", "h", "mode": "face"|"center", "offset", "path": [[t_s, px], ...] | null, "faces_found", "samples"}`.

## Whisper

- **Language**: `edit.yaml project.language` > style `captions.language` > `auto`. `auto` is whisper auto-detect; the detected code is
  stored as `ingest.json language_detected` (captions use it to pick a script font). `ingest.whisper_language(pr)` returns the setting.
- **Long files**: audio longer than `ingest.whisper.chunk_over_s` (600 s) is split into chunks of at most `ingest.whisper.chunk_s`
  (300 s). Each cut sits at the quietest 0.5 s within the last 60 s (or half a chunk) before the limit; energy is computed by
  streaming the wav in 50 ms blocks. Each chunk is transcribed alone, its timestamps offset, and the results merged;
  `<out>.json` then holds `{chunks, language, words}`.
- **QC**: `qc/audio_gates.py` takes the same setting: `_whisper(path, prompt=None, lang=None)`, `transcribe_chunked(path, lang=None)`,
  `words(processed, reference, lang=None)`, `stutters(pr, lang=None)` (defaults to `ingest.whisper_language(pr)`). The English
  verbatim prompt is only sent when the language is English. Word normalisation keeps letters and combining marks of any script.

## Take alignment

Long-form whisper word times drift by 1-3 s around retakes and long pauses (a pause is absorbed into a word:
`your [32.86-36.29]`), so in/out points read off `raw_words.json` clip words. `cves select` therefore re-times every
`selects.yaml` clip that has a `text:` field before it cuts anything (`cves.align`):

1. **Windows.** `story.align_passes` (3) windows of the source's 16 kHz audio, `in - w .. out + w` with
   w = `story.align_window_s` (1.5 s) x 1 / 0.8 / 1.2, clamped to the file. Each is transcribed with whisper.cpp
   (`config whisper` / `whisper_model`, the project language) using **DTW token times** (`-ojf --dtw <preset> -nfa`; the
   preset comes from the model file name, `config whisper_dtw` overrides it or turns it `off`). Plain `-ml 1` segment
   times stretch the first and last word to the window edges, so they are only the fallback. Transcripts are cached in
   `Edit/align/cache/` (keyed by file, window, model and language).
2. **Match.** The clip's `text:` is fuzzy-matched to the best contiguous word run (case and punctuation ignored, numbers
   normalised: "300 plus" = "300+", "a hundred percent" = "100%", "four to six" = "4-6"; near spellings and plurals count).
   With several takes in the window, the run that matches the text best wins, then the one nearest the hand times.
3. **Pool.** The passes whose score is at least `story.align_min_score` (0.8) give a first-word start and a last-word end:
   their median when they agree within 0.3 s; otherwise the estimate nearest the hand time. A pass whose run jumps over
   more than 1 s of speech (whisper merged two takes of a repeated line) is outvoted by any clean pass.
4. **Snap.** Each edge moves to the nearest pause in the speech energy (quieter than the window's 10th-percentile level +
   `story.align_quiet_db`), looking up to `story.align_search_s` (0.5 s) outward: `in` to just before the first word,
   `out` to just after the last, with the pads `story.align_pad_s` ([0.04, 0.08] s) kept inside the pause. It never
   cuts inside speech; with no pause in reach it takes the quietest 10 ms (and says so).

A score below the minimum keeps the hand times and prints a warning with what was heard. Opt out per clip with
`align: false`, or for a style with `story.align: false`. Every clip in `edl.json` records
`aligned: {in, out, score, status (moved / unchanged / kept_low_score / off / no_text), hand: [in, out], est, pause}`,
and `cves select` prints one line per clip (`align <id>: in 114.02 -> 113.99 (-0.03) out 115.62 -> 115.84 (+0.22) score 1.00`).
`selects.yaml` itself is never rewritten: the hand times stay the input, the aligned ones are in `edl.json`.

**STORY-17** (`cves qc --stage story`) closes the loop: each clip's own span of `voice_final.wav` (from the `edl.json`
segments) is transcribed separately, never the whole file (whisper skips whole sentences on long files), and the
recall of the clip's `text:` words is compared with style `qc.words_recall_min` (0.85), fillers ignored and numbers
normalised the same way. A clip whose first or last word is not heard fails whatever its recall (`qc.words_edges`):
that is a clipped take, the failure of the first real job ("We've" heard as "I've", a lost final "refund"). A FAIL lists the missing words per clip; clips without `text:` are skipped and named.

## Voice chain

`select` runs, in order: ffmpeg extract (48 kHz mono) → DeepFilterNet (per clip, ±0.5 s pad) → pause tightening →
8 ms crossfades → ffmpeg polish (`ingest.VOICE_CHAIN`: high-pass, 3-band EQ, high shelf, de-esser, compressor) → the
adaptive gate (`cves.voicegate`, style `voice.gate`; `ingest.polish_voice`, shared with the voiceover spine).
None is generative.

The gate is measured per take, not fixed: a fixed `agate` threshold left a real room at -50 dBFS between words (SND-19
wants the voice floor's p5 at -60 or lower). For each take it reads a 10 ms voice-band envelope of the tightened voice (the
room the viewer actually hears between words; DeepFilterNet pulls long pauses far lower), takes the floor (10th
percentile) and the speech level (90th), puts the threshold between them (floor + 0.3 x the gap, 6-14 dB over the floor)
and sets the depth that takes the room to -72 dBFS (10-40 dB). It is a downward expander (ratio 6) with an 8 ms
look-ahead, a 15 ms hold and 2 / 40 ms ramps in dB, so consonants are never clipped and word tails fade instead of
switching off. `voice_chain.json` records the step `adaptive_gate` with every take's floor, speech level, threshold
and depth. `Edit/voice_chain.json` records exactly these steps and their parameters from the same list the
filter string is built from (`{"steps": [{"name", "generative": false, "params"}], "output": "voice_final.wav"}`).
QC SND-30 fails if any step is generative.

## Long formats

Nothing loads a whole video. Audio clips for DeepFilterNet are read as windows of the source wav; whisper chunks are windowed
reads; face sampling, plates, mattes and faces stream frames. Face-crop analysis decodes the full source once at
`sample_fps` (cached), so a 1-hour landscape source costs one low-rate decode.

## Fonts for Indic scripts

`assets/fonts/` ships Noto Sans Devanagari, Tamil, Telugu, Kannada, Malayalam, Bengali and Gujarati in Medium, SemiBold,
Bold and ExtraBold (OFL; sources and licences in `assets/fonts/LICENSES/`). Style key
`font_files.script_fallback: {hi: NotoSansDevanagari-SemiBold.ttf, ta: NotoSansTamil-SemiBold.ttf, ...}` maps a language
code to a file; `cves.scripts.font_for_language(lang, weight="semibold", S=None)` returns the absolute file in the requested
weight (or `None` for Latin), `scripts.font_for_text(text, weight, S)` picks by the text's script.

**Shaping**: Indic text needs PIL built with libraqm (`scripts.shaping_available()`). Pillow's wheel loads libraqm/fribidi at
runtime; on macOS Homebrew's `/opt/homebrew/lib` is not on the default search path, so run with
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (or install `fribidi` where dyld looks) or vowel signs and conjuncts render unshaped.

## Tested (2026-11-18)

- 2026-11-19: synthetic 10-bit PQ and HLG B-roll clips (H.264, BT.2020 VUI tags): the SDR proxy is BT.709, not HDR, keeps
  the frame count, and decodes within 1 level (mean) of the original passed through `_tonemap_chain`
  (`tests/test_weak_spots.py`).

- Example project copy: `transcribe_raw, select, words, plate, faces` give byte-identical `raw_words.json`, `edl.json` segments
  (plus `src`), `words.json`, voice stems and transcript compared with the previous ingest code, and frame-identical plates
  (framemd5) for every segment whose boundaries match the stored originals.
- Synthetic clips: 1920×1080 30 fps (centre crop, plate_scale 1.78), 25 fps with rotation 90 (upright 1080×1920, no crop),
  VFR 30/22.5 fps (→ 23.976 CFR, exact frame count), 10-bit HLG and PQ (zscale tonemap, BT.709-tagged plates), SAR 4:3 anamorphic.
- Face crop: the vertical take padded into 16:9 at two offsets: the crop follows the speaker (offsets 286–452 and 1109–1267 px).
- Two sources (23.976 + 30 fps) in one selects.yaml: segments carry `src`, the 30 fps source is converted, plates have exact frame counts.
- Chunked whisper on the 220 s take with `chunk_over_s: 60, chunk_s: 90` and `language: auto`: 4 chunks, monotonic timestamps, `en` detected.
