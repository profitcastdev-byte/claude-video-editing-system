# Style profile

A **style profile** is the only place a look lives. The engine hard-codes no client, brand, colour, font, pacing, caption
look, grade, frame size (`canvas.size`), frame rate or language: every module reads them with

```python
from cves import style as STY
S = STY.load(pr)                          # the merged profile (a dict)
S.get("captions.position", "chin")        # dotted lookup with a default
```

Every key the engine reads exists in `engine/cves/styles/default.yaml` with a neutral value and a comment. The full list is
in the [key reference](#key-reference) below.

## Merge order

`style.load(pr)` merges up to nine layers. A later layer wins, key by key (nested mappings merge; lists and scalars replace):

| # | layer | written by | typical content |
|---|---|---|---|
| 1 | `engine/cves/styles/default.yaml` | the engine | neutral defaults, no brand, no house look |
| 1b | `engine/cves/styles/viral.yaml`, only when `edit.yaml goal: viral` | the engine | retention-first defaults for organic posts ([VIRAL.md](VIRAL.md)); `_sources` shows `goal:viral` |
| 2 | `knowledge-base/taste/learned.yaml` (repo learned) | `cves learn promote --share` (a person approves) | team taste, shared through git; global / goal / platform sections |
| 3 | `~/.cves/taste/learned.yaml` (personal learned) | `cves learn promote` (a person approves) | your taste; may hold `client:<name>` sections |
| 4 | `engine/cves/styles/<preset>.yaml`, named by `edit.yaml style: {preset: <name>}` | a person | a reusable house look, e.g. `profitcast-dark` |
| 5 | `PROJECT/Edit/style.yaml` | `cves inspire` | the look measured from the client's reference edits, with `_evidence` |
| 5b | `PROJECT/Edit/treatment.yaml` (its `style:` mapping) | `cves treatments pick` (in a treatment folder: `make`) | the creative treatment: caption preset, transition family, grade, energy, bed ([TREATMENTS.md](TREATMENTS.md)); `_sources` shows `treatment:<name>` |
| 6 | `PROJECT/Brand/style.yaml` | the client / a person | brand tokens: logo colours, fonts |
| 7 | `edit.yaml style:` (keys other than `preset`) | Claude / a person | per-video overrides |

The learned layers apply only their sections whose scope matches the project: `global`, `goal:<ad|viral>` (from
`edit.yaml goal:`), `platform:<name>` (from `edit.yaml platform.target`), `client:<name>` (from `project.client`), joined
with `+` for several conditions. General sections merge first, specific ones last. Learned layers may hold only keys of
`default.yaml` (`cves learn promote` checks). Details: [LEARNING.md](LEARNING.md).

After the merge, `platform.target` fills `platform.safe_zone` (pixels of `platform.size`), `sound.master_lufs` and
`sound.true_peak` from [platforms.yaml](../engine/cves/styles/platforms.yaml) unless a layer above `default.yaml` sets them.
QC recomputes the zone from the profile's fractions on the real frame size.

`S["_sources"]` lists the layers that were found, e.g. `["default", "learned:personal", "preset:profitcast-dark", "inspire", "edit.yaml"]`.
Keys that start with `_` (`_evidence`, `_inspire`) are notes: the engine never reads them.

So the measured look (5) beats the house preset (4), a treatment (5b) beats the measurement, and the brand (6) and the edit
(7) beat both: brand rules always win over a treatment. To keep a
preset value that inspire measured differently, set it again in `Brand/style.yaml` or `edit.yaml style:`, or delete the key
from `Edit/style.yaml`.

## Presets

A preset is a style file in `engine/cves/styles/`. It holds only the keys it changes. `profitcast-dark.yaml` is an example:
the look one agency measured from its own reference edits (dark stage, mint accent, moody relit A-roll). It is data like
any other layer: nothing in the engine knows its name. To make a new preset, copy it, change the values, and name it in
`edit.yaml`: `style: {preset: <file name without .yaml>}`. `cves validate` errors on a preset that does not exist.

## How `cves inspire` fills it

```
cves inspire [PROJECT] [--refs DIR] [--dry-run] [--max-s 90] [--mix "grade=refA,captions=refB,pacing=refC"] [--refresh] [--min-conf 0.5]
```

It reads every video (`.mp4 .mov .m4v .mkv .webm .avi`) and image (`.png .jpg .jpeg .webp .bmp`) in `PROJECT/Inspirations/`
(or `--refs DIR`, searched recursively), measures what can be measured from pixels and audio, prints a summary and writes
`PROJECT/Edit/style.yaml` (the previous one is kept as `style.yaml.bak`). `--dry-run` prints the summary only. Each video is
analysed for its first `--max-s` seconds: every frame (at up to 30 fps) for cuts and transitions, 6 samples per second
for faces, grade, captions and palette.

Every key it writes carries evidence: `_evidence: {key: "how it was measured; n=<samples>; confidence <0..1>"}`. Keys
below confidence 0.5 are **not** written; their evidence is still printed (marked `x`) and stored, and `_inspire.dropped`
lists them. `_inspire` also records the reference files, the date and which project footage the grade was compared to.

### Inspire v2: see, hear, feel, then mix and match

The references are the client's taste spec, so inspire measures each one on its own and does **not** average looks that
disagree. Per reference it writes, to `PROJECT/Edit/inspire/` (also on `--dry-run`; only `Edit/style.yaml` is skipped):

| file | what |
|---|---|
| `REPORT.md` | the human read: the chosen mix (dimension, source ref, why, consistency), what the edit should feel like, then **see / hear / feel** per reference with sparklines of the cut rate, music energy and energy arc. Claude reads this to feel the edit. |
| `<ref>-sheet.jpg` | contact sheet: 12 frames at shot middles, labelled with their time |
| `aesthetic-review.md` | rubric Claude fills by looking at the sheets: composition, typography quality, colour mood, motion character, texture / grain, negative space, premium vs cheap read, what to steal, what to avoid. Kept when it exists (new refs are appended). |
| `cache/` | the per-reference measurements (re-used until the file, `--max-s` or the analysis version changes; `--refresh` re-measures) |

**Hear** (`engine/cves/inspire_audio.py`, no new model or dependency): speech = 1 s windows whose voice-band (250-3500 Hz)
harmonic envelope swings at the syllable rate (3-8 Hz modulation >= 2.2 dB); the music bed = the median of the 0.5 s
window minima of 23 ms frames inside speech (the bed shows through the gaps between words) plus its min-to-mean offset,
measured on the reference's own music-only stretches (6 dB when there are none); tempo and beat grid = `beats.analyse()`
on the soundtrack (only when music is present), with beat salience as confidence; SFX = strong percussive onsets off the
beat and half-beat grid (inside speech only the strongest 5%, so plosives do not count); silences = >= 25 dB under the
running 2 s median for >= 0.15 s (drop-outs with music, pauses without).

**Feel** (`inspire_feel.py`): cut-on-beat = share of cuts within +-2 frames of a beat of the reference's own music, shown
next to the chance level for that tempo; the cut-rate curve (per second, 3 s smoothing) and its shape; hook timing (first
cut, first strong visual change, first burned-in text); pattern interrupts = cuts + frame-difference peaks that are not
cuts + face-scale jumps >= 8%, and the gaps between them; the loop seam = the last frame vs the first, measured like a cut,
against the reference's normal frame step (<= 3x, and < 0.15); the energy arc = per-second visual change + mix level,
classified rising / peak_end / wave / flat / falling; the container duration.

**See** (`inspire_see.py`): from the sheet frames, display and content aspect, orientation, letterbox / pillarbox bars
(2.2-2.5 content = scope 2.39:1), the tone curve (luma p2 / p25 / p50 / p75 / p98), saturation p50 / p90, mid-tone Lab
a* / b* (warm / cool / magenta / green), grain (high-pass noise sigma in flat areas), vignette (corner / centre) and the
share of motion-soft frames. These are notes in `_inspire.aesthetics`, not keys: the engine has no grain, curve or
aspect key to fill (no added grain is a recorded decision; the canvas is the brief's call).

**Mix and match** (`inspire_mix.py`). Keys belong to dimensions: `grade` (grade.\*), `palette` (stage.\*, colors.\*),
`captions`, `motion` (transitions.\*, framing.\*), `pacing` (grammar.max_shot_s / cutaway_share / max_cutaway_s,
rhythm.cut_\* / cuts_per_s / interrupt_\*, music.sync), `sound` (sound.\*, the other rhythm.\* keys) and `structure`
(structure.\*, grammar.face_on_first_frame). Every key is derived per reference and pooled. Per dimension the source is
the first rule that applies:
1. `--mix "dim=ref,..."` (ref = file name, stem or unique prefix);
2. `Inspirations/refs.yaml`: the ref whose `use:` lists the dimension (best `rank`, then `weight`);
3. the refs agree (consistency >= 0.6) or only one measured it: pooled (refs with `weight: 0` are left out);
4. they disagree: ONE ref, the highest `1/rank x weight x (0.5 + distinctiveness) x confidence`; distinctiveness is how far
   its values sit from the neutral defaults (a deliberate look beats a near-default one).

Consistency per key: numbers `1 - (max - min) / max(|median|, 0.5)`, colours `1 - max dE / 40`, labels the share agreeing
with the most common value; a dimension's is the mean of its keys. A picked ref's look is kept whole: keys it did not set
keep the default (the pooled value is used only when it measured nothing in that dimension). Forced and authority picks
are written down to confidence 0.2. `--dry-run` prints the per-dimension table (candidates per ref, chosen value, source,
confidence); `_inspire.mix` and the `[ref]` prefix in `_evidence` record where every key came from.

```yaml
# Inspirations/refs.yaml (optional)
refs:
  hook-reel.mp4: {rank: 1, weight: 1.0, kind: viral, use: [pacing, structure], notes: "the energy we want"}
  brand-ad.mov:  {rank: 2, kind: ad, use: [grade, captions]}
```

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
| sound | `sound.bed_lu` | HEAR: the bed under the words (window minima + min-to-mean offset) vs the speech level. Confidence 0.55 when the offset was measured on the reference's own music-only stretch, else 0.42 (not written). Integrated loudness is reported, not written (downloads are platform-normalised). |
| | `sound.duck_other_db` | HEAR: music level between phrases minus under the words (whole spectrum, so confidence 0.45: evidence only unless forced). |
| rhythm | `rhythm.voice`, `music_share`, `tempo_bpm`, `sfx_per_10s`, `dropouts_per_30s`, `music_energy` | HEAR, per reference (above): mode / median across the refs, or the picked ref's. |
| | `rhythm.cut_on_beat`, `cuts_per_s`, `cut_curve`, `interrupt_max_s`, `interrupt_median_s`; `music.sync` | FEEL. `music.sync: cuts` is written when cut-on-beat >= 0.6 and >= 2x the chance level. |
| structure | `structure.hook_change_s`, `first_cut_s`, `first_text_s`, `loop`, `energy_arc`, `duration_s` | FEEL (above). |

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
| `grammar.structure`, `grammar.beats` | STORY-01 beat order (STORY-07 / STORY-13 apply only where their beats exist), the beat labels, the music hook / turn / drop beats |
| `qc.words_recall_min` (or `edit.yaml qc.words_recall_min`) | STORY-17 word recall of each clip's `text:` |
| `story.align*` | take alignment in `cves select` (not a gate; its result is in `edl.json` clips `aligned:`) |
| `framing.min_step` | CUT-05 scale change at every direct A-roll cut |
| `framing.extreme_max` | FRAME-09 extreme punch-ins |
| `sound.master_lufs`, `sound.true_peak` | SND-01, SND-02 |
| `sound.bed_lu` (or `edit.yaml music.bed_lu`) | SND-04 music + SFX bed vs voice |
| `sound.phrase_tolerance_s` | SND-33 drop section vs the payoff (WARN-only) |
| `canvas.size` (or `platform.size`), `platform.safe_zone` / `canvas.safe_zones`, `platform.margin`, `platform.duration` | DEL-01, PLAT-01/02, DEL-04 |
| `platform.target` (styles/platforms.yaml) | PLAT-02 safe zone and caption line, RET-30 duration band, SND-01/02 loudness |
| `structure.hook_change_s`, `retention.hook_subject_s` | RET-24 hook change, RET-25 hook text / subject (viral) |
| `rhythm.interrupt_max_s`, `rhythm.interrupt_min_s`, `retention.soup_window_s` | RET-26 interrupt gap, RET-27 effect soup |
| `structure.loop`, `structure.payoff_window` | RET-28 loop seam, RET-29 payoff (viral) |
| `retention.dead_air_*`, `retention.guide_on_beat_min`, `rhythm.cut_on_beat` | RET-31 dead air, RET-32 cuts on the guide / music beat |
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

#### `canvas`

The frame the edit is designed, rendered and delivered at: native, not reframed ([FORMATS.md](FORMATS.md)). `edit.yaml
project.size` wins over it.

| key | default | meaning |
|---|---|---|
| `canvas.size` | `[1080, 1920]` | `[w, h]`, even numbers. 9:16 `[1080, 1920]`, 4:5 `[1080, 1350]`, 1:1 `[1080, 1080]`, 16:9 `[1920, 1080]`, 2.39:1 `[1920, 804]`. px values elsewhere in the profile (caption size, margins, gaps) are for a 1080 short side and scale by `min(w, h) / 1080` |
| `canvas.safe_zones` | 9:16 / 4:5 / 1:1 / 16:9 / 2.39:1 boxes | text-safe box per aspect, `x0 y0 x1 y1` as fractions of the canvas; the nearest aspect is used. A 9:16 canvas uses `platform.safe_zone` (px) instead |
| `canvas.safe_zones.9:16` | `[0.06, 0.14, 0.94, 0.65]` | the fraction form of `platform.safe_zone` (a 9:16 canvas uses `platform.safe_zone` itself) |
| `canvas.safe_zones.4:5` | `[0.06, 0.08, 0.94, 0.86]` | feed posts |
| `canvas.safe_zones.1:1` | `[0.06, 0.07, 0.94, 0.88]` | square |
| `canvas.safe_zones.16:9` | `[0.05, 0.07, 0.95, 0.88]` | landscape (player controls at the bottom) |
| `canvas.safe_zones.2.39:1` | `[0.05, 0.08, 0.95, 0.88]` | cinematic |
| (any `w:h`) | | add an aspect as a new key; the nearest aspect (log ratio) wins |

#### `platform`

| key | default | meaning |
|---|---|---|
| `platform.size` | `null` | legacy alias of `canvas.size`, used only when `canvas.size` is null |
| `platform.fps` | `source` | "source" = keep the footage rate; or e.g. [30000, 1001], 25, 30 |
| `platform.safe_zone` | `[65, 269, 1015, 1248]` | x0 y0 x1 y1 kept free of platform UI on a 9:16 canvas, in 1080x1920 px (Meta Reels norm; scaled on other 9:16 sizes; other aspects use `canvas.safe_zones`); null to disable |
| `platform.margin` | `60` | px kept clear at every frame edge for text (PLAT-01), scaled by `min(w, h) / 1080` |
| `platform.duration` | `[15, 90]` | seconds the brief allows |
| `platform.target` |  | reels / tiktok / shorts / youtube / meta_feed / meta_stories ([platforms.yaml](../engine/cves/styles/platforms.yaml), [VIRAL.md](VIRAL.md)): the platform's UI safe zone as fractions of the frame (PLAT-02), its caption line, duration band (RET-30) and loudness. With a target, `platform.safe_zone`, `sound.master_lufs` and `sound.true_peak` come from the profile unless a style layer sets them; null = the `platform.safe_zone` box above, scaled from `platform.size` to the real frame |

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
| `transitions.in` | `cut` | default transition into a cutaway: cut / whip / glitch / fade, or a craft kind (whip_pan / zoom_through / mask_wipe / luma_fade / glitch_lite / light_leak / dip; look in `craft.transitions`) |
| `transitions.out` | `cut` | default transition out of a cutaway |
| `transitions.whip_s` | `0.15` | whip half-duration either side of the cut, s |
| `transitions.glitch_s` | `0.1` | glitch half-duration, s |
| `transitions.fade_s` | `0.2` | fade (dip to black) half-duration, s |
| `transitions.whip_pan_s` | `0.2` | whip pan (directional smear) half-duration, s |
| `transitions.zoom_through_s` | `0.22` | zoom-through half-duration, s |
| `transitions.mask_wipe_s` | `0.3` | mask wipe half-duration, s |
| `transitions.luma_fade_s` | `0.3` | luma fade (shadows out first, highlights in first) half-duration, s |
| `transitions.glitch_lite_s` | `0.07` | glitch-lite (RGB split + a few slices, no scanlines) half-duration, s |
| `transitions.light_leak_s` | `0.35` | procedural light leak half-duration, s |
| `transitions.dip_s` | `0.25` | dip to colour (`craft.transitions.dip_color`) half-duration, s |

QC reads the same `transitions.<kind>_s` windows to exempt transition frames (MOT-12, the A-roll pass), so the window it
skips is the one the renderer drew.

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
| `grammar.structure` | `problem` | the story structure, `cves.structure`: `problem` H P A PR O C (hook, problem, agitation, proof, offer, CTA), `offer` H M PR R C (hook / promise, mechanism, proof, risk reversal, CTA), `story` H S T PR C (hook, setup, turn, proof, CTA), `custom` (= `grammar.beats`). Sets the STORY-01 order, the labels and the music beats |
| `grammar.beats` | `null` | an explicit beat order; overrides the structure's (e.g. `[H, M, PR, R, C]`). null = from `grammar.structure` |

#### `story`

the story step: take alignment in `cves select` (`cves.align`, [INGEST.md](INGEST.md) "Take alignment")

| key | default | meaning |
|---|---|---|
| `story.align` | `true` | re-time every `selects.yaml` clip that has `text:` from a local word-level transcript (per clip: `align: false`) |
| `story.align_window_s` | `1.5` | transcribe `in` - this .. `out` + this around each clip (narrowed / widened per pass) |
| `story.align_passes` | `3` | windows per clip; their edge estimates are pooled (median, or the one nearest the hand time when they disagree) |
| `story.align_min_score` | `0.8` | a fuzzy match of `text:` to the heard words below this keeps the hand times (and warns) |
| `story.align_pad_s` | `[0.04, 0.08]` | pad before the first word / after the last word, kept inside the pause |
| `story.align_search_s` | `0.5` | how far an edge looks for a pause beyond the word estimate, s |
| `story.align_quiet_db` | `12` | a pause is quieter than the window's noise floor (10th percentile) + this, dB |

#### `qc`

story-stage thresholds (an `edit.yaml qc:` key of the same name wins for one video)

| key | default | meaning |
|---|---|---|
| `qc.words_recall_min` | `0.85` | STORY-17: share of each clip's `text:` words heard in its own span of `voice_final.wav` |

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
| `sound.transition_sfx.whip_pan` | `whoosh` | cue for a whip pan (craft) |
| `sound.transition_sfx.zoom_through` | `whoosh` | cue for a zoom-through |
| `sound.transition_sfx.mask_wipe` | `swipe` | cue for a mask wipe |
| `sound.transition_sfx.glitch_lite` |  | cue for a glitch-lite (null = none) |
| `sound.transition_sfx.luma_fade` |  | cue for a luma fade (null = none) |
| `sound.transition_sfx.light_leak` |  | cue for a light leak (null = none) |
| `sound.transition_sfx.dip` |  | cue for a dip to colour (null = none) |
| `sound.repeat_pitch_st` | `1` | SND-09: an identical back-to-back cue is pitched +/- this many semitones (alternating, deterministic) |
| `sound.repeat_gain_db` | `1.5` | ... and its gain moved by -/+ this much |
| `sound.phrase_tolerance_s` | `0.05` | SND-33: the drop section must start this close to the payoff, s |
| `sound.accents` |  | automatic risers / impacts on the story moments ([SOUND.md](SOUND.md)); budget `creative.sound_accents_per_30s` |
| `sound.accents.enabled` | `true` | false (or edit.yaml `sfx.auto: false`) = no automatic accents |
| `sound.accents.reveals` | `true` | also an impact on reveal cues that carry no low hit of their own |
| `sound.accents.riser_gain_db` | `-14` | riser level, dB (`sound.sfx_offset_db` applies on top) |
| `sound.accents.impact_gain_db` | `-11` | impact level, dB (a tagged hero: no offset) |
| `sound.accents.riser_min_s` | `0.8` | shortest riser; a target with less room before it gets none |
| `sound.accents.riser_max_s` | `2.2` | longest riser picked from the bank |
| `sound.accents.riser_tail_max_s` | `0.1` | only risers that resolve: their peak is at most this far from their end |
| `sound.accents.impact_max_s` | `2.0` | an impact longer than this is trimmed to it, s |
| `sound.accents.impact_attack_max_s` | `0.03` | only punchy impacts: onset to peak within this, s (a slow swell is not a hit) |
| `sound.accents.min_gap_s` | `0.3` | a riser starts at least this long after the accent before it |
| `sound.accents.payoff_riser` | `medium` | intensity (soft / medium / hard) of the riser into the payoff |
| `sound.accents.payoff_impact` | `hard` | intensity of the downbeat hit on the payoff |
| `sound.accents.hook_riser` | `soft` | intensity of the riser into / out of the hook |
| `sound.accents.reveal_impact` | `medium` | intensity of the impact on other reveals |

#### `mix`

how the music sits under the voice ([SOUND.md](SOUND.md))

| key | default | meaning |
|---|---|---|
| `mix.duck_mode` | `envelope` | envelope (the music gain follows the voice RMS envelope) / gate (the v0.3 fixed dips) |
| `mix.duck_attack_ms` | `40` | envelope: how fast the music dips when a syllable starts |
| `mix.duck_release_ms` | `auto` | envelope: how fast it comes back; auto = 1.25 x the measured syllable period, within `mix.duck_release_range_ms` |
| `mix.duck_release_range_ms` | `[250, 400]` | clamp for the auto release, ms |
| `mix.duck_range_db` | `30` | envelope: voice this far under its loud level does not duck; full depth (`sound.duck_voice_band_db` / `duck_other_db`) from 6 dB under it |

#### `music`

beat sync + music fit (docs/MUSIC.md); edit.yaml `music:` keys override these per video

| key | default | meaning |
|---|---|---|
| `music.sync` | `off` | off / drop / cuts / full (cumulative: cuts = drop + cut points on the beat; full = cuts + SFX peaks on the beat) |
| `music.fit` | `bars` | bars (trim / loop on bar lines, end on a downbeat with a one-bar tail) / none (legacy: offset + 0.9 s fade) |
| `music.beats_per_bar` | `4` | bar length for bar-line edits |
| `music.tempo_range` | `[60, 150]` | BPM range the detected tempo is folded into (double/half-time fix); e.g. [120, 190] for drum & bass |
| `music.snap_tolerance_s` | `0.12` | cuts mode: a cut point / graphic entry moves only to a beat this close |
| `music.drop_beats` | `null` | drop moment: first clip tagged with one of these story beats (music.drop_cut > 0 wins); null = from `grammar.structure` (problem `[PR, O]`, offer and story `[PR]`) |
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
| `music.phrase_align` | `true` | drop / cuts / full: prefer the drop whose build starts on the story turn (sections: intro / build / drop / body / break / outro) |
| `music.phrase_min_bars` | `2` | a music section is at least this many bars |
| `music.build_min_rise_db` | `2.0` | a build rises at least this much into its drop |
| `music.build_step_db` | `1.0` | ... and each of its bars at least this much over the bar before |
| `music.phrase_turn_weight` | `1.0` | drop pick: score points lost per bar between the build start and the turn |
| `music.hook_beats` | `null` | story beats of the hook (riser into / out of it); null = from `grammar.structure` (`[H]`) |
| `music.turn_beats` | `null` | story beats of the turn (the build should start here); null = from `grammar.structure` (problem `[P, A]`, offer `[M]`, story `[T]`); none tagged: the end of the hook |
| `music.hook_cut` | `0` | cut s of the hook when > 0 (else from `music.hook_beats`) |
| `music.turn_cut` | `0` | cut s of the turn when > 0 (else from `music.turn_beats`) |

#### `rhythm`

How the edit moves. `cves inspire` measures these from the references (HEAR / FEEL, `Edit/inspire/REPORT.md`); the retention
gates (RET-26 / RET-27 / RET-32) check the ones with defaults, the rest are plan-time targets Claude reads when cutting
and choosing music. null = no target.

| key | default | meaning |
|---|---|---|
| `rhythm.interrupt_max_s` | `4.0` | longest gap between pattern interrupts (A-roll cut and zoom step, cutaway in/out, transition, graphic entry, picture change), s (RET-26); preset viral 2.5 |
| `rhythm.interrupt_min_s` | `0.3` | interrupts closer than this, sustained for `retention.soup_window_s`, read as effect soup (RET-27); preset viral 0.25 |
| `rhythm.interrupt_median_s` |  | typical gap between pattern interrupts, s |
| `rhythm.cut_on_beat` | `false` | cuts should land on the beat: `true`, or the share inspire measured (0..1; >= 0.6 counts as on-beat and also sets music.sync: cuts). RET-32 reports the share on the beat (preset viral: true) |
| `rhythm.cuts_per_s` |  | target mean cut rate (cuts per second) |
| `rhythm.cut_curve` |  | how the cut rate moves over the video: rising (builds up) / flat / wave / peak_end / falling |
| `rhythm.tempo_bpm` |  | music tempo the references use; pick or generate music near it |
| `rhythm.voice` |  | true = voice-led (presenter / VO); false = music-only edit (no voice in the references) |
| `rhythm.music_share` |  | share of the runtime with music under it (0..1) |
| `rhythm.sfx_per_10s` |  | transient SFX hits (off the beat, not speech) per 10 s |
| `rhythm.dropouts_per_30s` |  | deliberate music drop-outs / silences per 30 s |
| `rhythm.music_energy` |  | music level over the video: rising / flat / wave / peak_end / falling |

#### `structure`

The shape of the piece ([VIRAL.md](VIRAL.md)); `cves inspire` (FEEL) measures it.

| key | default | meaning |
|---|---|---|
| `structure.hook_change_s` | `1.5` | first visual change (pattern interrupt) by this time, s (RET-24); preset viral 1.0 |
| `structure.first_cut_s` |  | first cut by this time, s |
| `structure.first_text_s` |  | first on-screen text by this time, s |
| `structure.loop` | `false` | the end flows back into the start for a seamless replay; RET-28 checks the seam (goal viral) |
| `structure.payoff_window` | `0.2` | the payoff (a visual or audio peak) lands in this last fraction of the runtime (RET-29, goal viral) |
| `structure.energy_arc` |  | picture + sound energy over the video: rising / peak_end / wave / flat / falling |
| `structure.duration_s` |  | typical reference duration, s (the brief's platform.duration still rules) |

#### `retention`

measurement settings of the retention gates RET-24 to RET-32 ([QC-GATES.md](../knowledge-base/QC-GATES.md))

| key | default | meaning |
|---|---|---|
| `retention.hook_subject_s` | `1.0` | goal viral: on-screen text or a strong subject (face / high-contrast centre) by this time, s (RET-25) |
| `retention.soup_window_s` | `1.5` | RET-27: a run of interrupt gaps under `rhythm.interrupt_min_s` longer than this is effect soup, s |
| `retention.merge_s` | `0.05` | events this close count as one interrupt (one graphic entering with its parts), s |
| `retention.scene_diff` | `12.0` | mean abs luma step (0-255, on a 96 px wide decode) that counts as a picture change in the master |
| `retention.loop_seam_s` | `0.3` | RET-28: span compared at each end of the video, s |
| `retention.loop_min_similarity` | `0.6` | RET-28: SSIM of the last span vs the first span (0..1) a seamless loop reaches |
| `retention.payoff_rise_db` | `3.0` | RET-29: an audio peak this much above the body median counts as a payoff, dB |
| `retention.dead_air_s` | `0.6` | RET-31: longest stretch with no speech, music or SFX, s (FAIL for goal viral, WARN for ads) |
| `retention.dead_air_db` | `-45` | RET-31: a 50 ms window of the master quieter than this (dBFS) is silent |
| `retention.guide_on_beat_min` | `0.6` | RET-32: share of cuts within `music.snap_tolerance_s` of a beat (music guide / slot: platform) |

#### `motion`

| key | default | meaning |
|---|---|---|
| `motion.entry_s` | `0.28` | graphic entry duration, s |
| `motion.overshoot` | `1.6` | back-ease overshoot of entries |
| `motion.slide_px` | `50` | entry slide distance px |
| `motion.stagger_s` | `0.12` | delay between items of a list, s |
| `motion.drift` | `0.025` | slow push on cutaway stages (fraction over 6 s) |

The keys below drive the HTML motion pieces (`m_*` templates, [MOTION.md](MOTION.md)); pieces receive them as `CVES.motion` and as CSS variables.

| key | default | meaning |
|---|---|---|
| `motion.ease` | `expo` | house curve family (`cubic` / `quint` / `expo`): entries decelerate on it, exits accelerate, moves do both |
| `motion.energy` | `0.5` | 0 calm .. 1 punchy: scales every choreography duration (x1.3 .. x0.7) and the overshoot (x0.4 .. x1.6) |
| `motion.blur_on_fast` | `true` | fake motion blur (a CSS blur) on frames where an element moves fast |
| `motion.blur_max_u` | `1.6` | cap of that blur, in u (1 % of the shorter canvas side) |
| `motion.shutter` | `0.5` | simulated shutter as a fraction of a frame (0.5 = 180°): how long the blur is for a given speed |
| `motion.exit_s` | `0.32` | exit animation length when a piece leaves on its own (overlays on A-roll; cutaways cut out) |
| `motion.type_ratio` | `1.25` | ratio of the modular type scale `--t-0` .. `--t-9` (`--t-0` = 2.2 u) |
| `motion.radius_u` | `2.6` | card corner radius, in u (`--r`) |
| `motion.glass_alpha` | `0.72` | opacity of the card colour under `.glass` surfaces (`--glass-alpha`) |
| `motion.safe` | `null` | `[x0, y0, x1, y1]` canvas fractions pieces stay inside; `null` = `platform.safe_zone` when its design space has the canvas's aspect |
| `motion.safe_fallback` | `[0.06, 0.07, 0.94, 0.93]` | safe fractions used when `platform.safe_zone` does not fit the canvas aspect (e.g. a 16:9 render with a 9:16 safe zone) |
| `motion.hero_min_gap_s` | `8.0` | `cves render` warns when two hero pieces (meta `hero: true`) start closer than this: restraint, one hero moment per ~8-10 s |

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
| `media.card_box` | `[100, 300, 980, 1200]` | card rect x0 y0 x1 y1 in the 1080x1920 design space (inside platform.safe_zone); fitted into the safe zone on other canvases (also `media.device_box`) |
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

#### `broll`

The `edit.yaml broll:` track ([FORMATS.md](FORMATS.md)); a shot's own keys win.

| key | default | meaning |
|---|---|---|
| `broll.framing` | `fill` | default framing of a video shot: `fill` (crop to the canvas aspect) \| `fit` (the whole picture on a blurred, dimmed fill of itself) \| `kenburns` |
| `broll.ken_burns` | `[1.0, 1.08]` | zoom from → to over a `kenburns` shot (stills default to kenburns) |
| `broll.fit_blur` | `40` | px (at a 1080 short side) Gaussian blur of the fill behind a `fit` shot |
| `broll.fit_dim` | `0.55` | brightness multiplier of that fill |
| `broll.audio_gain` | `-14` | dB of a shot's own sound (`audio: true`) when the shot sets no `gain` |

#### `autocut`

`cves autocut` defaults: a broll: track cut on the music grid.

| key | default | meaning |
|---|---|---|
| `autocut.every` | `downbeats` | `beats` \| `downbeats` (every bar) \| `bars` (every `autocut.bars` bars) |
| `autocut.bars` | `2` | bars per shot with `every: bars` |
| `autocut.min_shot_s` | `0.5` | grid points closer than this to the previous cut are skipped |

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
| `ingest.hdr.broll` | `true` | HDR B-roll and media clips (`broll:`, `video_broll`, `screen_rec`, `pip` / `split` panes, `overlay_render`) go through the same tonemap once, into `Edit/conform/<name>-<key>.sdr.mkv` (FORMATS.md §5); `false` = decode them as they are |
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
| `legibility.video_bg_broll` | `#C8C8C8` | the same for captions over B-roll / footage with no presenter on screen (full-bleed footage runs brighter and varies more) |
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
| `creative.sound_accents_per_30s` | `3` | automatic risers + impacts (`sound.accents`) per 30 s of runtime (a shorter video still gets one 30 s allowance) |
| `creative.craft_per_30s` | `4` | craft moves (speed ramps, camera moves, match cuts, text behind the speaker) per 30 s; `cves render` warns and `cves critique` reports it |

#### `review`

`cves review` ([REVIEW.md](REVIEW.md)): what goes into the render review pack and the thresholds of its machine findings.
The review reads QC and the critique, it never re-runs a gate; these keys only tune the cut-local and sound detectors that
no gate covers, and the loop cap.

| key | default | meaning |
|---|---|---|
| `review.max_rounds` | `3` | review rounds per loop; at the cap `cves review build` says so and refuses a 4th round until Claude signs off (`ship` / `revise`) and records what is still wrong |
| `review.cut_offsets` | `[-2, -1, 0, 1, 2]` | frames shown around every cut in `cuts/cut_NN.jpg` (0 = first frame of the incoming shot) |
| `review.hook_s` | `3.0` | length of the hook strip (`hook.jpg`), s; also the hook section of the loudness report |
| `review.hook_fps` | `10` | frames per second sampled into the hook strip |
| `review.payoff_frames` | `6` | frames sampled across the payoff window (`structure.payoff_window`) before the end card |
| `review.black_luma` | `18` | a frame within 2 of a cut darker than this (mean luma 0-255) between brighter shots is a black flash (high) |
| `review.flash_delta` | `60` | a frame within 2 of a cut this much brighter than both shots is a white flash (high) |
| `review.glitch_ratio` | `0.35` | one-frame glitch: frames -1 and +1 differ by less than this share of the steps into and out of the frame (high) |
| `review.freeze_ratio` | `0.15` | a frame step at a cut below this share of the local motion is a duplicate frame / freeze (med) |
| `review.freeze_motion` | `1.0` | local mean abs frame step (0-255) below which a shot counts as static (no freeze check) |
| `review.luma_jump` | `45` | mean-luma step across a hard cut that reads as a flash (low; med above 1.5x between footage shots); a transition covers it |
| `review.caption_near_f` | `2` | a caption that changes 1..this many frames from a cut (not on it) is flagged (med at 1 frame, low at 2) |
| `review.min_shot_f` | `3` | a shot shorter than this many frames reads as a glitch (med) |
| `review.click_ratio` | `4.0` | audio pop: sharpest sample step (2nd difference) within a frame of a cut vs the p99.5 in the 0.3 s around it (med; high above 2x) |
| `review.click_floor_db` | `-45` | ... unless the audio there peaks below this (dBFS) |
| `review.vmr_min_db` | `6.0` | vocal-to-music ratio in the 1-4 kHz speech band (400 ms windows over speech, from the stems) under which music masks the voice |
| `review.mask_share` | `0.1` | share of speech windows under `vmr_min_db` that makes a finding (high when the p10 is below 0 dB) |
| `review.bed_step_max_db` | `6.0` | largest `music.bed_lu` cut the safe masking patch makes |
| `review.silence_db` | `-50` | master 50 ms windows quieter than this (dBFS) count as silence |
| `review.silence_s` | `0.6` | a silent gap inside the body longer than this is reported (low; skipped when QC RET-31 already reports dead air) |
| `review.section_jump_lu` | `6.0` | hook / body / payoff loudness differing by more than this (LU) is flagged (low) |
| `review.end_card_min_s` | `1.0` | an end card shorter than this cannot be read; safe patch: `end_card.duration` = this (PLAT-11 caps it at 3 s) |
| `review.end_tail_db` | `-30` | master level in its last 50 ms above this (dBFS) = audio cut off at the end, not faded or ended on a hit (low) |
| `review.earshot` | `auto` | `auto` runs `earshot measure --json --light` on the master when earshot is installed (`audio.json` `earshot`); `off` skips it |
| `review.earshot_timeout_s` | `180` | give up on earshot after this long; the pack is written without it |

#### `treatments`

`cves treatments` ([TREATMENTS.md](TREATMENTS.md)): 2-3 creative takes on one plan, rendered as fast proxies and compared.

| key | default | meaning |
|---|---|---|
| `treatments.offer` | `[punchy, cinematic, minimal]` | treatments `make` builds when none are named; the project's own `treatments/*.yaml` are added |
| `treatments.prefer` | `null` | the treatment offered first; `cves learn mine` proposes it per goal / client from past `pick`s |
| `treatments.proxy_scale` | `0.5` | proxy renders at this fraction of the canvas (even-rounded); plates and mattes are resized as they decode, never re-ingested |
| `treatments.proxy_preset` | `veryfast` | x264 preset of proxy encodes (delivered files keep `delivery.video`) |
| `treatments.proxy_crf` | `26` | x264 crf of proxy encodes |
| `treatments.compare_points` | `6` | timecodes on the comparison sheet, the same in every treatment |
| `treatments.compare_thumb` | `360` | sheet thumbnail height (portrait) or width (landscape), px |
| `treatments.compare_max_s` | `12` | seconds of each treatment in the comparison MP4 |
| `treatments.compare_layout` | `stacked` | `stacked` (side by side, or one above the other on landscape; audio of the first) or `sequential` (one after another, each with its own sound) |

#### `craft`

Motion craft (docs/MOTION.md "Craft"): text behind the speaker, speed ramps, camera moves, match cuts and the transition
library. Every move counts against the `creative` budget; transitions are also rate-limited at render.

| key | default | meaning |
|---|---|---|
| `craft.behind.size` | `300` | `text_behind` type size, px at a 1080 short side (shrinks to fit `max_width`) |
| `craft.behind.weight` | `xb` | font weight slot (m / sb / b / xb) |
| `craft.behind.tracking` | `-4` | tracking, px at a 1080 short side |
| `craft.behind.case` | `upper` | upper / as_is |
| `craft.behind.max_width` | `0.92` | widest line, fraction of the safe-zone width |
| `craft.behind.max_lines` | `2` | lines the text may wrap to |
| `craft.behind.position` | `above` | above (the head covers the lower `overlap` of the type) / behind (centred on the eyes) / low (behind the shoulders) |
| `craft.behind.overlap` | `0.42` | fraction of the cap height the head covers in `above` |
| `craft.behind.one_line_min` | `0.42` | keep the text on one line when it fits at >= this fraction of `size` (no orphan word on its own line), else wrap |
| `craft.behind.track` | `0.6` | how much of the head's motion the type follows: 0 locked at its entry, 1 glued |
| `craft.behind.smooth_frames` | `9` | face-landmark smoothing radius, frames (triangular window) |
| `craft.behind.color` | `text` | type colour (palette slot or hex) |
| `craft.behind.accent` | `accent` | colour of `*starred*` words |
| `craft.behind.entry` | `rise` | rise (the letters rise out from behind the head) / slam (whole on its first frame, oversized, settling: a hard visual event) |
| `craft.behind.entry_s` | `0.5` | entry length, s |
| `craft.behind.exit_s` | `0.25` | exit length (ends 0.25 s before the shot by default) |
| `craft.behind.no_matte` | `above` | no subject matte: above (lift the type clear above the head) / front (keep it, with a legibility bed) |
| `craft.behind.sfx` | `lowhit` | entry cue (null = none) |
| `craft.behind.bed` | `false` | draw a legibility bed under the type (always on with no matte and `no_matte: front`); prefer a colour that reads on the wall |
| `craft.ramp.default` | `slam` | preset used by `ramp: {}` |
| `craft.ramp.presets` |  | `[shot fraction, speed]` keys per preset, eased between (add your own) |
| `craft.ramp.presets.slam` | `[[0, 1], [0.35, 1], [0.5, 0.22], [0.82, 0.22], [1, 1]]` | real time, a hard slow-down through the middle, back to real time |
| `craft.ramp.presets.punch_in` | `[[0, 2.4], [0.4, 2.4], [0.6, 0.35], [1, 0.35]]` | fast in, then slow-motion to the end |
| `craft.ramp.presets.ease_out` | `[[0, 1], [1, 0.3]]` | a gentle slow-down |
| `craft.ramp.presets.speed_up` | `[[0, 0.5], [0.6, 0.5], [1, 2.5]]` | slow, then a speed-up into the next cut |
| `craft.ramp.presets.hold` | `[[0, 1], [0.4, 0.08], [0.75, 0.08], [1, 1]]` | a near freeze in the middle |
| `craft.ramp.ease` | `inOutCubic` | the curve between keys (motion-runtime names) |
| `craft.ramp.blend` | `auto` | auto (= blend) / blend (crossfade neighbours when slow, shutter average when fast) / nearest |
| `craft.ramp.shutter` | `0.5` | blend window on fast sections, fraction of an output frame |
| `craft.ramp.min_speed` | `0.08` | floor of the speed curve (the remap stays strictly increasing) |
| `craft.ramp.audio` | `mute` | a ramped shot's own sound: mute / pitch (tape varispeed) |
| `craft.camera.move` | `none` | default move: none / push / pull / pan_left / pan_right / pan_up / pan_down / drift |
| `craft.camera.amount` | `0.08` | zoom change (push / pull) or travel zoom (pans) |
| `craft.camera.ease` | `inOutSine` | move curve |
| `craft.camera.drift_u` | `0.5` | handheld drift amplitude, u (1 % of the short side) |
| `craft.camera.drift_hz` | `0.3` | handheld drift speed |
| `craft.camera.drift_rot` | `0.25` | handheld roll, degrees |
| `craft.camera.parallax` | `0.5` | 2.5D: the foreground moves (1 + parallax) x the background (stills with `depth:`) |
| `craft.camera.depth_split` | `0.5` | depth / matte value above which a pixel is foreground |
| `craft.match.mode` | `saliency` | match-cut shape: saliency (spectral residual) / centroid (the bright, high-contrast shape) |
| `craft.match.scale_range` | `[1.0, 1.6]` | scale applied to the incoming shot (>= 1: the fill crop never shows an edge) |
| `craft.match.settle_s` | `0.0` | 0 holds the alignment; > 0 eases back to the shot's own framing over this long |
| `craft.transitions.min_gap_s` | `1.5` | a non-cut transition this close to the previous kept one becomes a cut |
| `craft.transitions.enforce` | `true` | apply that rate limit and `creative.transition_kinds_max` at render |
| `craft.transitions.whip_dir` | `left` | whip_pan direction: left / right / up / down |
| `craft.transitions.wipe_shape` | `bar` | mask_wipe shape: bar (diagonal) / circle / matte (A-roll: the background goes first, the subject last) |
| `craft.transitions.wipe_color` | `accent` | mask_wipe fill: palette slot, stage, black, white or hex |
| `craft.transitions.dip_color` | `stage` | dip / luma_fade colour |
| `craft.transitions.leak_color` | `gold` | light_leak tint (procedural, no media) |
| `craft.transitions.leak_strength` | `0.55` | light_leak screen-blend strength at the cut |
