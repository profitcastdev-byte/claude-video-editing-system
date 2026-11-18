# Style profile

A **style profile** is the only place a look lives. The engine hard-codes no client, brand, colour, font, pacing, caption
look, grade, frame size, frame rate or language: every module reads them with

```python
from cves import style as STY
S = STY.load(pr)                          # the merged profile (a dict)
S.get("captions.position", "chin")        # dotted lookup with a default
```

Every key the engine reads exists in `engine/cves/styles/default.yaml` with a neutral value and a comment. The full list is
in the [key reference](#key-reference) below.

## Merge order

`style.load(pr)` merges seven layers. A later layer wins, key by key (nested mappings merge; lists and scalars replace):

| # | layer | written by | typical content |
|---|---|---|---|
| 1 | `engine/cves/styles/default.yaml` | the engine | neutral defaults, no brand, no house look |
| 2 | `knowledge-base/taste/learned.yaml` (repo learned) | `cves learn promote --share` (a person approves) | team taste, shared through git; global / goal / platform sections |
| 3 | `~/.cves/taste/learned.yaml` (personal learned) | `cves learn promote` (a person approves) | your taste; may hold `client:<name>` sections |
| 4 | `engine/cves/styles/<preset>.yaml`, named by `edit.yaml style: {preset: <name>}` | a person | a reusable house look, e.g. `profitcast-dark` |
| 5 | `PROJECT/Edit/style.yaml` | `cves inspire` | the look measured from the client's reference edits, with `_evidence` |
| 6 | `PROJECT/Brand/style.yaml` | the client / a person | brand tokens: logo colours, fonts |
| 7 | `edit.yaml style:` (keys other than `preset`) | Claude / a person | per-video overrides |

The learned layers apply only their sections whose scope matches the project: `global`, `goal:<ad|viral>` (from
`edit.yaml goal:`), `platform:<name>` (from `edit.yaml platform.target`), `client:<name>` (from `project.client`), joined
with `+` for several conditions. General sections merge first, specific ones last. Learned layers may hold only keys of
`default.yaml` (`cves learn promote` checks). Details: [LEARNING.md](LEARNING.md).

`S["_sources"]` lists the layers that were found, e.g. `["default", "learned:personal", "preset:profitcast-dark", "inspire", "edit.yaml"]`.
Keys that start with `_` (`_evidence`, `_inspire`) are notes: the engine never reads them.

So the measured look (3) beats the house preset (2), and the brand (4) and the edit (5) beat the measurement. To keep a
preset value that inspire measured differently, set it again in `Brand/style.yaml` or `edit.yaml style:`, or delete the key
from `Edit/style.yaml`.

## Presets

A preset is a style file in `engine/cves/styles/`. It holds only the keys it changes. `profitcast-dark.yaml` is an example:
the look one agency measured from its own reference edits (dark stage, mint accent, moody relit A-roll). It is data like
any other layer: nothing in the engine knows its name. To make a new preset, copy it, change the values, and name it in
`edit.yaml`: `style: {preset: <file name without .yaml>}`. `cves validate` errors on a preset that does not exist.

## How `cves inspire` fills it

```
cves inspire [PROJECT] [--refs DIR] [--dry-run] [--max-s 90]
```

It reads every video (`.mp4 .mov .m4v .mkv .webm .avi`) and image (`.png .jpg .jpeg .webp .bmp`) in `PROJECT/Inspirations/`
(or `--refs DIR`, searched recursively), measures what can be measured from pixels and audio, prints a summary and writes
`PROJECT/Edit/style.yaml` (the previous one is kept as `style.yaml.bak`). `--dry-run` prints the summary only. Each video is
analysed for its first `--max-s` seconds: every frame (at up to 30 fps) for cuts and transitions, 6 samples per second
for faces, grade, captions and palette.

Every key it writes carries evidence: `_evidence: {key: "how it was measured; n=<samples>; confidence <0..1>"}`. Keys
below confidence 0.5 are **not** written; their evidence is still printed (marked `x`) and stored, and `_inspire.dropped`
lists them. `_inspire` also records the reference files, the date and which project footage the grade was compared to.

| area | keys | how |
|---|---|---|
| pacing | `grammar.max_shot_s` | cuts = frame-difference peaks (pixel + colour-histogram distance, local maximum, well above the local median); p90 of the shot lengths, rounded up to 0.5 s. Cuts per minute go in the evidence. |
| | `grammar.cutaway_share` | share of time with no presenter face (YuNet, `config.get("yunet")`), per reference; the band is min..max of the references widened by 0.05 (0.07 for a single reference). |
| | `grammar.max_cutaway_s` | p90 of the no-face runs, rounded up to 0.5 s (the longest run, usually the end card, is in the evidence). |
| | `grammar.face_on_first_frame` | true only if every reference opens on the presenter's face. |
| framing | `framing.min_step`, `framing.zoom_levels` | face height of each A-roll shot; the ratio across direct A-roll cuts (p25 of the cuts that changed scale) and the levels clustered from each reference's widest shot. |
| grade | `grade.relight`, `grade.background_stops` | wall (beside and above the head, away from the body, white text removed) vs skin (two cheek patches from YuNet landmarks), as linear luminance, compared with the same ratio in **this project's own footage** (`Edit/plate/*.mkv`, else `Raw/`). `look.grade` scales display RGB, so stops = log2(ratio change) / 2.2. Relight is on below -0.2 stops. |
| | `grade.gamma` | skin display level, reference vs footage (clamped 0.8..1.3; a clamped value drops below confidence). It also carries the references' own lighting. |
| | `grade.subject_tint` | skin RGB balance, reference vs footage (each channel 0.9..1.1). Written only when small (<= 3%): a bigger shift is usually another presenter or another light, and pushes skin hue off COL-03. |
| | `grade.background_saturation`, `grade.background_tint` | the same for the wall. Scene-dependent (another room has another wall), so confidence stays below 0.5 and they are normally not written. |
| | `grade.vignette` | top-corner vs near-wall luminance, reference vs footage, solved through the `look._vignette` falloff. Rough: punch-ins hide the corners. |
| | `grade.black_lift` | per-channel p0.5, reference minus footage (0..0.06). |
| palette | `stage.background`, `stage.glow`, `stage.glow_bottom` | k-means (Lab) on the no-face (graphics) frames: the largest cluster is the stage; the bottom band's median is the glow when it differs from the stage by dE > 6. |
| | `colors.accent`, `colors.accent_dark` | k-means on saturated graphics pixels: the cluster with the largest share x saturation; the dark accent is the same hue at 55% value. |
| captions | `captions.position` (+ `lower_third_y` / `chin_gap`), `size`, `case`, `color`, `highlight_color`, `box_color`, `max_lines`, `max_chars`, `style` | burned-in text lines on A-roll frames: bright top-hat glyph components on a shared baseline, below the mouth; the most frequent text size is the caption (titles and graphics differ). Position: chin-anchored if the gap to the chin varies less than the absolute height, else center / lower_third / `y:<px>` (design space). Size = cap height / 0.72. Case = share of glyphs reaching cap height. Box = a flat surround that differs from the frame further out. Style: one_word (about one word on screen), word_reveal (the word count grows inside a caption), highlight (a second glyph colour), box, else pop. OCR is not needed. |
| transitions | `transitions.in`, `transitions.out`, `transitions.whip_s / glitch_s / fade_s` | at each face <-> no-face cut: an RGB-split spike is a glitch, a luma dip below both sides is a fade, a sharpness collapse (motion / zoom blur) is a whip, else a cut. The most common kind per direction; the median duration per kind. |
| sound | `sound.bed_lu` | ebur128 momentary loudness: the quiet gaps between words (p8) vs speech (p60). Rough: it assumes the gaps hold the music bed. Integrated loudness is reported, not written (downloads are platform-normalised). |

Anything that cannot be measured (fonts, motion timing, SFX choice, the safe zone) keeps the preset / default value.
Screenshots count as single frames: they feed the palette (no face) or the grade and captions (face).

Measured on test material (`cves inspire --dry-run`):
- a synthetic reference built from this engine with a known look (relight -1.0 stops, 2 s A-roll at zoom 1.0 / 1.25,
  3 s cutaways on `#102030` with `#FF7A00` bars, fade in / cut out, white sentence-case word_reveal captions 64 px under the
  chin) came back as background_stops -1.02, max_shot_s 3.0, cutaway_share 33-47% (truth 40%), max_cutaway_s 3.0, zoom
  levels [1.0, 1.3], accent `#FD7800`, stage `#0F1F2E`, transitions fade / cut, captions chin / word_reveal / sentence /
  white / size 66. The vignette is under-read (0.14 for 0.3).
- four real reference reels of the `profitcast-dark` look came back close to that hand-made preset: accent `#02FCA8`
  (preset `#19E6A0`), stage `#000000` (`#040706`), glow `#023520` (`#105C3C`), cutaway share 42-63% (preset 40-55%),
  relight on at -0.66 stops (preset -1.32, tuned by eye), vignette 0.69 (0.55), transitions in whip, whip_s 0.14 (0.15),
  captions white / sentence case / word_reveal / 2 lines. Their walls differ from this footage's wall, which is why the
  wall-dependent keys stay below confidence.

## QC thresholds come from the style

The QC gates are engine invariants; their thresholds are style keys, so a client whose references cut slower or use more
graphics gets gates that match:

| key | gate |
|---|---|
| `grammar.max_shot_s` | RET-16 longest visual hold |
| `grammar.cutaway_share` | RET-22 cutaway share band (null = not enforced) |
| `grammar.max_cutaway_s` | RET-22 / RET-22b longest stretch without the face |
| `grammar.face_on_first_frame` | RET-13 face on frame 0 (only when true) |
| `grammar.roto_max` | GFX-25 behind-the-head moments |
| `grammar.beats` | story-stage beat order |
| `framing.min_step` | CUT-05 scale change at every direct A-roll cut |
| `framing.extreme_max` | FRAME-09 extreme punch-ins |
| `sound.master_lufs`, `sound.true_peak` | SND-01, SND-02 |
| `sound.bed_lu` (or `edit.yaml music.bed_lu`) | SND-04 music + SFX bed vs voice |
| `platform.size`, `platform.safe_zone`, `platform.margin`, `platform.duration` | DEL-01, PLAT-01/02, DEL-04 |
| `captions.*` (style, size, color, shadow, case, highlight_color) | PLAT-10 caption style |
| `legibility.*` | GFX-15 text contrast |

## Validation

`cves validate [PROJECT]` (also run first by `cves render` and `cves build`, which stop on errors) checks every style layer
against `default.yaml`: an unknown key is a warning with a did-you-mean suggestion (`captions.postion: unknown style key
(did you mean 'position'?)`), and a value whose type clearly differs from the default (a string where the default is a
number) is a warning. Maps whose keys are data (`colors`, `font_files`, `captions.per_style`, `sound.transition_sfx`,
`media.device_box`) accept any key.

## Adding a key

1. Read it with `S.get("section.key", default)` where it is used.
2. Add it to `default.yaml` with a neutral value and a comment (the comment is the documentation).
3. Add a row to the reference below (it is generated from `default.yaml`; regenerate or edit by hand).
4. If `cves inspire` can measure it, add the measurement with evidence in `engine/cves/inspire.py`.

## Grade notes

- **Relight edge** (`grade.edge_*`): the matte edge is composited by decontamination, not a feather. Each edge pixel of the
  plate is `a * subject + (1 - a) * wall`; the wall behind it is estimated from nearby pure-wall pixels
  (`edge_wall_sigma`), the subject colour is un-mixed and re-composited over the darkened wall. Matte alpha below / above
  `edge_alpha_range` is treated as wall / subject, so RVM's soft tails do not spread graded subject light over the wall.
  Phone cameras sharpen dark-on-bright edges: the wall within `edge_dehalo_px` of the silhouette is clamped to the wall
  level just beyond it. Never widen a feather to hide an edge: it reads as an aura (LESSONS #4).
- **Exposure balance** (`grade.exposure_*`): one gain per shot, fitted so that consecutive shots meet at their cut
  frames and at their shot medians (COL-06 / COL-07), weakly anchored to the common median. Cached in
  `Edit/exposure.json` with the timeline it was solved for (any segment or cutaway change re-solves it).

## Key reference

Generated from `engine/cves/styles/default.yaml` (comments there are the source of truth).

#### `platform`

| key | default | meaning |
|---|---|---|
| `platform.size` | `[1080, 1920]` | master canvas (design space for templates is 1080x1920; other ratios via `cves deliver` reframes) |
| `platform.fps` | `source` | "source" = keep the footage rate; or e.g. [30000, 1001], 25, 30 |
| `platform.safe_zone` | `[65, 269, 1015, 1248]` | x0 y0 x1 y1 kept free of platform UI (Meta Reels norm); null to disable |
| `platform.margin` | `60` | px kept clear at every frame edge for text (PLAT-01) |
| `platform.duration` | `[15, 90]` | seconds the brief allows |

#### `stage`

| key | default | meaning |
|---|---|---|
| `stage.background` | `#0B0B0D` | cutaway / end-card stage colour |
| `stage.glow_bottom` | `#2A2A33` | colour of the soft glow rising from the stage bottom |
| `stage.dot_grid` | `#8A8A99` | dot-grid colour on the stage |
| `stage.dots` | `true` | draw the dot grid |
| `stage.glow` | `true` | draw the bottom glow |

#### `colors`

| key | default | meaning |
|---|---|---|
| `colors.accent` | `#4C8DFF` | brand accent: highlights, ticks, counters (templates read it as `G.MINT`) |
| `colors.accent_dark` | `#2A5BB8` | darker accent for fills and shadows |
| `colors.text` | `#FFFFFF` | main text colour on graphics |
| `colors.card` | `#16161B` | card body colour |
| `colors.card_border` | `#34343F` | card outline colour |
| `colors.icon_well` | `#24243A` | circle behind icons |
| `colors.gold` | `#D6B26C` | secondary accent (wordmarks, premium marks) |
| `colors.star` | `#FFC446` | rating stars; negative marks (comparison crosses). muted / surface / line are derived unless set |
| `colors.negative` | `#E5484D` | negative marks (crosses) |

#### `font_files`

| key | default | meaning |
|---|---|---|
| `font_files.medium` | `Poppins-Medium.ttf` | font file for the medium weight (assets/fonts or absolute path) |
| `font_files.semibold` | `Poppins-SemiBold.ttf` | semibold weight |
| `font_files.bold` | `Poppins-Bold.ttf` | bold weight |
| `font_files.extrabold` | `Poppins-ExtraBold.ttf` | extrabold weight |
| `font_files.serif` | `CormorantGaramond.ttf` | serif face (wordmarks) |
| `font_files.script_fallback` | `{"hi": "NotoSansDevanagari-SemiBold.ttf", "mr...` | language code -> font for scripts the brand font lacks |

#### `grade`

| key | default | meaning |
|---|---|---|
| `grade.relight` | `false` | subject-matte background darkening (needs a presenter) |
| `grade.background_stops` | `0.0` | how far the wall is pulled down when relight is on (negative = darker) |
| `grade.background_saturation` | `1.0` | wall saturation when relight is on (1 = unchanged) |
| `grade.background_tint` | `[1.0, 1.0, 1.0]` | RGB multipliers on the wall when relight is on |
| `grade.subject_tint` | `[1.0, 1.0, 1.0]` | RGB multipliers on the presenter (skin warmth) |
| `grade.gamma` | `1.0` | presenter display gamma (> 1 = darker mids) |
| `grade.gain` | `1.0` | presenter gain after gamma |
| `grade.vignette` | `0.0` | 0..1 |
| `grade.shoulder` | `0.0` | filmic highlight roll-off |
| `grade.shoulder_gain` | `1.0` | output scale after the shoulder (keeps white below clip when shoulder > 0) |
| `grade.black_lift` | `[0.0, 0.0, 0.0]` | RGB lift of the blacks (matte / faded look), 0..0.06 |
| `grade.exposure_match` | `true` | per-shot skin balance across cuts |
| `grade.exposure_mode` | `rgb` | `rgb`: luminance gain plus a small per-channel trim so skin colour matches across cuts (COL-06); `luma`: luminance only |
| `grade.exposure_chroma_max` | `0.06` | cap on that per-channel trim (log units, about 6 %) |
| `grade.exposure_gain_range` | `[0.85, 1.18]` | clamp on the per-shot balance gain |
| `grade.exposure_anchor_weight` | `0.15` | pull of each shot median to the common median vs matching neighbours at the cut (0..1) |
| `grade.edge_alpha_range` | `[0.2, 0.8]` | relight edge: matte alpha <= lo is wall, >= hi is subject (narrower = crisper edge, no ring) |
| `grade.edge_decontaminate` | `true` | relight edge: un-mix the wall from edge pixels before re-compositing over the darkened wall |
| `grade.edge_wall_sigma` | `6.0` | px: neighbourhood the wall colour behind an edge pixel is estimated from |
| `grade.edge_dehalo_px` | `10.0` | px: wall this close to the subject is clamped to the wall level just beyond (camera sharpening ring); 0 = off |

#### `captions`

| key | default | meaning |
|---|---|---|
| `captions.style` | `word_reveal` | word_reveal / one_word / highlight / box / karaoke / pop / bounce / none |
| `captions.font` | `semibold` | `font_files` weight name for captions |
| `captions.size` | `50` | caption font size px (design space) |
| `captions.color` | `#FFFFFF` | caption text colour |
| `captions.highlight_color` | `accent` | colour name from `colors` or hex |
| `captions.box_color` | `#000000B0` | box colour (#RRGGBBAA) for style box |
| `captions.case` | `sentence` | sentence / upper / lower / as_spoken |
| `captions.max_lines` | `2` | lines per caption event |
| `captions.max_chars` | `34` | characters per line before wrapping |
| `captions.position` | `chin` | chin (just under the face) / lower_third / center / y:<px> |
| `captions.shadow` | `true` | soft drop shadow (+ a legibility bed when the colour needs it, see `legibility`) |
| `captions.legible` | `true` | add the auto-darkened bed under captions when contrast vs `legibility.video_bg` is short |
| `captions.outline` | `0` | stroke width in px (0 = off); a stroke instead of / with the shadow |
| `captions.outline_color` | `#000000` | stroke colour when `outline` > 0 |
| `captions.language` | `en` | also picks `font_files.script_fallback` for non-Latin captions |
| `captions.emoji` | `true` | colour emoji when a colour-emoji font exists (emoji_font or a system one), else skipped |
| `captions.emoji_font` |  | path to a colour-emoji font; null = auto-detect |
| `captions.emphasis` |  | keyword emphasis; numbers auto-emphasised |
| `captions.emphasis.words` | `[]` | words always emphasised |
| `captions.emphasis.color` | `accent` | emphasis colour (name or hex) |
| `captions.emphasis.scale` | `1.15` | emphasis size multiplier |
| `captions.emphasis.numbers` | `true` | keyword emphasis; numbers auto-emphasised |
| `captions.highlight_mode` | `text` | highlight style: text (colour the word) / pill (accent pill behind the word) |
| `captions.pad_x` | `85` | side padding inside platform.safe_zone (line wrap width = safe width - 2 * pad_x) |
| `captions.pad_bottom` | `20` | gap kept above the safe zone bottom |
| `captions.chin_gap` | `70` | preferred gap under the chin (position chin) |
| `captions.chin_min_gap` | `40` | never closer to the chin than this |
| `captions.lower_third_y` | `0.68` | position lower_third: top as a fraction of the canvas height |
| `captions.line_height` | `1.32` | line spacing as a multiple of the size |
| `captions.lead_s` | `0.03` | a word shows this long before its spoken start |
| `captions.reveal_s` | `0.06` | word_reveal fade-in per word |
| `captions.pop_s` | `0.16` | pop / bounce / one_word entry duration per word |
| `captions.karaoke_dim` | `0.55` | unspoken words in karaoke, as a fraction of the text colour |
| `captions.per_style` |  | max_chars / max_lines / size_scale per caption style (override the values above) |
| `captions.per_style.one_word` | `{"max_chars": 1, "max_lines": 1, "size_scale"...` | overrides used when style = one_word |
| `captions.per_style.pop` | `{"max_chars": 24, "max_lines": 2}` | overrides used when style = pop |
| `captions.per_style.bounce` | `{"max_chars": 24, "max_lines": 2}` | overrides used when style = bounce |

#### `transitions`

| key | default | meaning |
|---|---|---|
| `transitions.in` | `cut` | default transition into a cutaway: cut / whip / glitch / fade |
| `transitions.out` | `cut` | default transition out of a cutaway |
| `transitions.whip_s` | `0.15` | whip half-duration either side of the cut, s |
| `transitions.glitch_s` | `0.1` | glitch half-duration, s |
| `transitions.fade_s` | `0.2` | fade (dip to black) half-duration, s |

#### `framing`

| key | default | meaning |
|---|---|---|
| `framing.zoom_levels` | `[1.0, 1.18, 1.38]` | A-roll scale levels the auto-framing alternates between |
| `framing.min_step` | `1.15` | every direct A-roll cut changes scale by at least this (hides jump cuts) |
| `framing.creep` | `0.0` | slow push per shot |
| `framing.extreme_max` | `1` | extreme punch-ins (>= 1.4x) allowed per video |
| `framing.lift` | `false` | punch in and anchor low on shots carrying a chest graphic (crops the head on close selfies) |

#### `grammar`

pacing rules the QC gates enforce; null = not enforced for this client

| key | default | meaning |
|---|---|---|
| `grammar.cutaway_share` |  | e.g. [0.40, 0.55] |
| `grammar.max_cutaway_s` | `8` | longest stretch without the presenter's face, s (RET-22) |
| `grammar.max_shot_s` | `4` | longest visual hold, s (RET-16) |
| `grammar.roto_max` | `4` | behind-the-head moments per video (GFX-25) |
| `grammar.face_on_first_frame` | `false` | frame 0 must show the presenter (RET-13) |
| `grammar.topic_by_s` | `2.0` | topic keyword spoken / shown by this time, s (RET-01/12) |
| `grammar.beats` | `["H", "P", "A", "PR", "O", "C"]` | story beat order the story gates expect (hook problem agitate proof offer cta) |

#### `sound`

| key | default | meaning |
|---|---|---|
| `sound.bed_lu` | `-10` | music+SFX bed vs voice while speaking |
| `sound.duck_voice_band_db` | `-8` | music cut in the voice band while speaking, dB |
| `sound.duck_other_db` | `-3` | music cut outside the voice band while speaking, dB |
| `sound.duck_lookahead_s` | `0.12` | ducking starts this early, s |
| `sound.sfx_offset_db` | `-3` | non-reveal cues sit this far back |
| `sound.master_lufs` | `-14` | integrated loudness of the master (SND-01) |
| `sound.true_peak` | `-1.0` | true-peak ceiling, dBTP (SND-02) |
| `sound.transition_sfx` |  | sound per transition kind (null = none); a whoosh is placed by its peak on the cut (SND-08) |
| `sound.transition_sfx.whip` | `whoosh` | cue for a whip |
| `sound.transition_sfx.glitch` | `swipe` | cue for a glitch |
| `sound.transition_sfx.cut` |  | cue for a hard cut (null = none) |
| `sound.transition_sfx.fade` |  | sound per transition kind (null = none); a whoosh is placed by its peak on the cut (SND-08) |
| `sound.repeat_pitch_st` | `1` | SND-09: an identical back-to-back cue is pitched +/- this many semitones (alternating, deterministic) |
| `sound.repeat_gain_db` | `1.5` | ... and its gain moved by -/+ this much |

#### `music`

beat sync + music fit (docs/MUSIC.md); edit.yaml `music:` keys override these per video

| key | default | meaning |
|---|---|---|
| `music.sync` | `off` | off / drop / cuts / full (cumulative: cuts = drop + cut points on the beat; full = cuts + SFX peaks on the beat) |
| `music.fit` | `bars` | bars (trim / loop on bar lines, end on a downbeat with a one-bar tail) / none (legacy: offset + 0.9 s fade) |
| `music.beats_per_bar` | `4` | bar length for bar-line edits |
| `music.tempo_range` | `[60, 150]` | BPM range the detected tempo is folded into (double/half-time fix); e.g. [120, 190] for drum & bass |
| `music.snap_tolerance_s` | `0.12` | cuts mode: a cut point / graphic entry moves only to a beat this close |
| `music.drop_beats` | `["PR", "O"]` | default drop moment: first clip tagged with one of these story beats (music.drop_cut > 0 wins) |
| `music.drop_pick` | `auto` | auto (strongest drop candidate that needs no silent lead-in) / an index into beats.json drops |
| `music.drop_min_rise_db` | `3.0` | a drop candidate's next 2 bars are this much louder than the 4 before |
| `music.loop_xfade_s` | `0.08` | equal-power crossfade on a loop seam (seams sit on downbeats) |
| `music.loop_min_bars` | `4` | a loop jumps back at least this many bars |
| `music.end_min_tail_s` | `0.5` | the last downbeat leaves at least this much tail before the video ends |
| `music.end_tail_bars` | `1` | the tail fades over this many bars after the last downbeat |
| `music.gfx_lead_s` | `0.25` | GFX-01: a beat move never shows a graphic more than this before its word |
| `music.min_aroll_s` | `0.5` | a moved cutaway edge never leaves an A-roll piece shorter than this |
| `music.sfx_snap` | `["whoosh", "hit", "boom", "riser"]` | full mode: cues whose name contains one of these are nudged to the beat |
| `music.sfx_snap_max_f` | `1` | full mode: max nudge in frames (SND-07 keeps every SFX within 1 frame of its picture event) |

#### `motion`

| key | default | meaning |
|---|---|---|
| `motion.entry_s` | `0.28` | graphic entry duration, s |
| `motion.overshoot` | `1.6` | back-ease overshoot of entries |
| `motion.slide_px` | `50` | entry slide distance px |
| `motion.stagger_s` | `0.12` | delay between items of a list, s |
| `motion.drift` | `0.025` | slow push on cutaway stages (fraction over 6 s) |

#### `delivery`

`cves encode` / `cves deliver` (docs/DELIVERY.md). Encoder settings for every delivered file

| key | default | meaning |
|---|---|---|
| `delivery.video` |  | no tune=film (DEL-05) |
| `delivery.video.codec` | `libx264` | video encoder |
| `delivery.video.crf` | `16` | x264 quality (DEL-05 expects 16) |
| `delivery.video.preset` | `slow` | x264 preset |
| `delivery.video.profile` | `high` | H.264 profile |
| `delivery.video.pix_fmt` | `yuv420p` | pixel format |
| `delivery.video.tune` |  | x264 tune (never film, DEL-05) |
| `delivery.video.x264_params` |  | no tune=film (DEL-05) |
| `delivery.audio` |  | audio encoder settings |
| `delivery.audio.codec` | `aac` | audio codec |
| `delivery.audio.sample_rate` | `48000` | Hz |
| `delivery.audio.bitrate` | `256k` | audio bitrate |
| `delivery.faststart` | `true` | moov atom before mdat (DEL-03) |
| `delivery.color` | `bt709` | matrix conversion AND stream tags (COL-01) |
| `delivery.cover` |  | thumbnail: best face + sharpness frame in the first window_s (edit.yaml delivery.cover_t overrides) |
| `delivery.cover.window_s` | `3.0` | cover frame searched in the first N s |
| `delivery.cover.quality` | `92` | JPEG quality |
| `delivery.cover.title_font` | `extrabold` | font_files key; title text comes from edit.yaml delivery.cover_title |
| `delivery.cover.title_size` | `104` | cover title px |
| `delivery.cover.title_color` | `text` | colour name from `colors` or hex |
| `delivery.cover.title_accent` | `accent` | colour of words wrapped in *stars* |
| `delivery.cover.title_y` | `0.16` | top of the title block, fraction of the frame height |
| `delivery.cover.title_max_chars` | `16` | per line |
| `delivery.cover.title_shadow` | `true` | shadow under the cover title |
| `delivery.reframe` |  | 4:5 / 1:1 / 16:9 variants from the 9:16 master |
| `delivery.reframe.face_y` | `0.4` | face centre sits this far down the new frame |
| `delivery.reframe.margin` | `24` | px kept around the face box and the caption box |
| `delivery.reframe.smooth_s` | `0.4` | crop-path smoothing (only on shots where one static crop cannot hold face + captions) |
| `delivery.reframe.wide_fg` | `4:5` | 16:9: the foreground crop placed on the blurred fill |
| `delivery.reframe.fill_blur` | `40` | px (at output size) Gaussian blur of the 16:9 fill |
| `delivery.reframe.fill_dim` | `0.55` | fill brightness multiplier |
| `delivery.cutdown` |  | beat tags kept whole / compressed first |
| `delivery.cutdown.keep` | `["H", "C"]` | story beats kept whole in cut-downs |
| `delivery.cutdown.compress` | `["P", "A", "PR", "O"]` | story beats shortened first |
| `delivery.cutdown.tolerance_s` | `0.5` | beat tags kept whole / compressed first |

#### `media`

image / video_broll / screen_rec / pip / split / overlay_render templates (docs/MEDIA.md)

| key | default | meaning |
|---|---|---|
| `media.frame` | `bleed` | default framing of a picture: bleed (full screen) / card (rounded card on the stage) |
| `media.card_box` | `[100, 300, 980, 1200]` | card rect x0 y0 x1 y1 in the 1080x1920 design space (inside platform.safe_zone) |
| `media.radius` | `36` | card / pane / bubble corner radius px |
| `media.border` | `3` | card outline px (colour = colors.card_border); 0 = none |
| `media.shadow` | `0.5` | drop-shadow opacity under cards and the pip bubble; 0 = none |
| `media.entry` | `rise` | card entry when it lands after the cutaway starts: rise / scale / fade / none (timing: motion.*) |
| `media.ken_burns` | `[1.0, 1.08]` | image zoom from -> to over the shot when `zoom` is not given ([1, 1] = static) |
| `media.zoom_s` | `0.6` | screen_rec zoom-to-region ease time, s |
| `media.cursor_size` | `26` | screen_rec cursor-highlight radius px (colour = colors.accent) |
| `media.device_box` |  | screen_rec frames x0 y0 x1 y1 |
| `media.device_box.phone` | `[300, 330, 780, 1250]` | phone screen rect x0 y0 x1 y1 |
| `media.device_box.browser` | `[60, 420, 1020, 1060]` | screen_rec frames x0 y0 x1 y1 |
| `media.pip` |  | presenter bubble |
| `media.pip.corner` | `br` | presenter bubble corner (tl/tr/bl/br) |
| `media.pip.size` | `360` | bubble diameter px |
| `media.pip.shape` | `circle` | circle / rounded |
| `media.pip.margin` | `60` | bubble distance from the edges px |
| `media.pip.ring` | `6` | ring width px |
| `media.pip.face_zoom` | `2.4` | zoom on the face inside the bubble |
| `media.pip.cutout_scale` | `0.55` | presenter bubble |
| `media.split` |  | two-pane layout |
| `media.split.gap` | `12` | gap between panes px |
| `media.split.ratio` | `0.5` | first pane share |
| `media.split.radius` | `0` | two-pane layout |
| `media.sfx_in` | `swipe` | cue for a card / pane / bubble that enters after the cutaway starts ("" = none) |
| `media.sfx_click` | `button` | screen_rec cursor click cue ("" = none) |

#### `ingest`

how any footage is conformed to the master canvas (docs/INGEST.md)

| key | default | meaning |
|---|---|---|
| `ingest.reframe` | `face` | source aspect != canvas: face = YuNet-steered crop (centre when no face) / center |
| `ingest.face_crop` |  | face-steered reframe of off-aspect footage |
| `ingest.face_crop.sample_fps` | `2` | face detections per second of source that steer the crop |
| `ingest.face_crop.smooth_s` | `1.0` | gaussian smoothing of the crop path, seconds |
| `ingest.face_crop.anchor` | `[0.5, 0.4]` | where the face centre sits inside the crop (x, y fractions) |
| `ingest.face_crop.static_tolerance` | `0.04` | crop path moving less than this fraction of the crop is locked (no micro-pans) |
| `ingest.hdr` |  | HDR -> SDR tone mapping |
| `ingest.hdr.tonemap` | `hable` | HDR (PQ / HLG) -> SDR BT.709 operator: hable / mobius / reinhard / clip |
| `ingest.hdr.npl` | `100` | nominal peak luminance (nits) used to linearise |
| `ingest.whisper` |  | long-audio transcription chunking |
| `ingest.whisper.chunk_over_s` | `600` | audio longer than this is transcribed in chunks split on silences |
| `ingest.whisper.chunk_s` | `300` | longest chunk, seconds |

#### `legibility`

text over video (captions, chest, roto): WCAG targets and the auto bed (GFX-15)

| key | default | meaning |
|---|---|---|
| `legibility.min_contrast` | `4.5` | small text |
| `legibility.large_contrast` | `3.0` | text >= large_px |
| `legibility.large_px` | `48` | text this size or larger uses `large_contrast` |
| `legibility.video_bg` | `#B4B4B4` | assumed worst-case background behind text on video |
| `legibility.plate_max` | `0.85` | strongest bed opacity |
| `legibility.bed_spread` | `0.18` | bed reach around glyphs, as a fraction of the type size |
| `legibility.wordmark_bed` | `0.72` | darkness of the soft bed behind a chest wordmark |
| `legibility.margin` | `1.15` | aim this much above the contrast target (anti-aliasing, the grade and entry fades eat into it) |

#### `type`

| key | default | meaning |
|---|---|---|
| `type.sep_gap_em` | `0.32` | drawn spacing either side of a separator (" · ", " / "): never repeated spaces (GFX-17) |

#### `locale`

| key | default | meaning |
|---|---|---|
| `locale.grouping` | `intl` | number grouping in stat / counter / chart: intl (1,234,567) / indian (12,34,567) / none |
| `locale.thousands` | `,` | thousands separator |
| `locale.decimal` | `.` | decimal separator |

#### `creative`

The restraint budget of `knowledge-base/CREATIVE.md` §2. `cves critique` reports usage against it in `CRITIQUE.md`; it is
advisory (not a QC gate). Per-30 s budgets give a video shorter than 30 s one full allowance.

| key | default | meaning |
|---|---|---|
| `creative.signature_per_30s` | `1` | signature moments (the extreme punch-in, a motion piece marked `signature: true`, a hard music hit) per 30 s |
| `creative.transition_kinds_max` | `2` | distinct transition kinds in one video, cut not counted |
| `creative.motion_pieces_per_30s` | `6` | animated graphics (cutaways, roto, chest, motion pieces, end card) per 30 s |
| `creative.accent_colors_max` | `1` | accent colours beyond the text colour and the stage |
