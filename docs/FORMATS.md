# Formats: any frame size, any timeline spine

CVES edits natively at the frame size the brief asks for (9:16, 4:5, 1:1, 16:9, 2.39:1 or any even size) and from whatever
drives the cut: a presenter (A-roll), a voiceover, a music track or the shots themselves. This page is the reference for
the canvas, safe zones, the four spines, the `broll:` track and `cves autocut`.

## 1. The canvas

```yaml
# Brand/style.yaml, Edit/style.yaml, a preset or edit.yaml style:
canvas:
  size: [1920, 1080]           # [w, h], even numbers
```

| aspect | size | typical use |
|---|---|---|
| 9:16 | `[1080, 1920]` (default) | Reels, Shorts, TikTok, Stories |
| 4:5 | `[1080, 1350]` | feed posts |
| 1:1 | `[1080, 1080]` | feed posts, carousels |
| 16:9 | `[1920, 1080]` (or `[3840, 2160]`) | YouTube, web, presentations |
| 2.39:1 | `[1920, 804]` | cinematic / letterbox look |

Order of precedence: `edit.yaml project.size` > style `canvas.size` > style `platform.size` (legacy alias, `null` by
default) > 1080×1920. The renderer, the encoder, QC, control-mode layers, the moodboard, `cves inspire` and the reframes all
follow it. Changing the canvas of an A-roll project after `cves select` needs `cves select` + `cves prep` again (the plates
are conformed to the canvas); a voiceover / music / broll project needs nothing (B-roll is framed at render time).

**How the engine reads it (CONTRACTS §2).** `gfx.set_canvas(w, h)` sets `G.W`, `G.H` and `G.U = min(w, h) / 1080` for the
process. Every consumer reads them at call time, never imports them by value. Render workers use the `spawn` start method,
which re-imports every module, so each worker re-sets the canvas in its initializer (`render._init` builds a `Timeline`,
which applies the style and the canvas). Any new pool must do the same (pass the canvas, or the project, in the job args).

**Px values in the style** (caption size, gaps, `platform.margin`, `broll.fit_blur`, template params) are designed for a
1080-px short side and are scaled by `G.U`. On 1080×1920, 1920×1080, 1080×1080 and 1080×1350, `U = 1`.

**Landscape A-roll.** Ingest crops a source to the canvas aspect (face-aware) and never squashes. Landscape footage on a
landscape canvas is not cropped at all; landscape footage on a vertical canvas gets the existing face-steered crop.

## 2. Safe zones

`gfx.safe_zone()` is the text-safe box on the current canvas:
- a **9:16** canvas uses `platform.safe_zone` (px at 1080×1920, scaled to other 9:16 sizes; the Meta Reels norm);
- every other aspect uses `canvas.safe_zones` (fractions `x0 y0 x1 y1` per aspect; the nearest aspect wins). Defaults:
  4:5 `[.06, .08, .94, .86]`, 1:1 `[.06, .07, .94, .88]`, 16:9 `[.05, .07, .95, .88]`, 2.39:1 `[.05, .08, .95, .88]`;
- `platform.safe_zone: null` disables it (the canvas inset by `platform.margin` is used for layout).

Captions wrap inside it, sit under the chin when a presenter is on screen and low in it (a lower third) when not. QC
PLAT-01 / PLAT-02 measure against the same box.

## 3. Templates on any canvas

`templates.get(name)` wraps every template so it lays out on the current canvas (`docs/TEMPLATES.md`):

| layout | who | how |
|---|---|---|
| native | modules with `NATIVE = True` / `{names}` (e.g. `broll_shot`, the motion pieces) | draw on the canvas itself, scale their own px by `G.U` |
| relative (default) | `cutaways`, `roto`, `generic`, `chest`, `overlays`, `end`, `media`, user templates | lay out from `G.W` / `G.H` / `G.safe()` on a same-aspect layout canvas with a 1080 short side, and are **rasterised at the canvas's real resolution**: `G.layer` draws every coordinate, font size, stroke, icon, shadow and legibility bed `G.R` (= `G.U`) times larger, so a 3840×2160 or 2160×3840 graphic is drawn at 4K, not drawn at 1080 and scaled up. The picture templates (`media`) sample their source straight into layer-sized buffers, so a 4K card shows the photo at 4K. A module that can't be rasterised sets `RASTER = False` and is drawn at the layout size, then scaled by `G.U` |
| fixed | third-party modules with `DESIGN = True` (hard-coded 1080×1920 coordinates) | drawn in 1080×1920 and fitted per instance into the canvas safe zone: the union of what they draw over their span (sampled) is scaled uniformly (never up) and centred. No built-in module uses it any more |

**The v0.2 UI cutaways and roto cards** (`search_rows`, `card_list`, `stat` / `counter`, `browser_list`, `map_card`,
`big_words`, `listing_card`, `top3_card`) lay out per canvas shape (`templates/_layout.py`):

| shape | aspect (W/H) | arrangement |
|---|---|---|
| tall | ≤ 2/3 (9:16, 2:3) | the original vertical layout. On a 9:16 canvas it uses the 1080×1920 numbers exactly (frames are pixel-identical to v0.3); on a shorter tall canvas the block follows the safe-zone centre |
| square | 2/3 – 1.3 (1:1, 4:5, 3:4) | the vertical block scaled to fit the safe zone, centred; the `stat` number grows (up to 1.5×) to fill it |
| wide | ≥ 1.3 (16:9, 2.39:1) | a landscape arrangement: `card_list` in two columns from 4 items (column-major), `browser_list` rows in two columns from 4 rows, wider rows and panels, type scaled up (up to 1.3×) to fill the safe-zone height; roto cards fill the zone height, 1.35:1 wide, top edge high |

Every inner size is `value × s` (s = 1 on 9:16), and every element stays inside the safe zone on square and wide
canvases (`tests/test_weak_spots.py`). Template params given in px (`top`, `y`, `ys`) are 1080×1920 design px and
apply on tall canvases; square and wide canvases place the block themselves.

At 1080×1920 every path is the identity, so the v0.2 golden frames are unchanged.

## 4. Spines: what drives the timeline

```yaml
spine: aroll            # aroll (default) | voiceover | music | broll
```

| spine | length and cut points | picture | sound | captions |
|---|---|---|---|---|
| `aroll` | the presenter's selects (`selects.yaml` → `edl.json`) | A-roll + cutaways + roto / chest; `broll:` shots are cutaways over it | voice + music + SFX | from the voice |
| `voiceover` | the VO, pause-tightened (`voice_final.wav`) | the `broll:` track (+ cutaways) | VO + music bed + SFX + clip sound | from the VO words |
| `music` | `duration`, else the music track; cuts from `Edit/beats.json` (`cves autocut`) | the `broll:` track (+ text cards) | music (leads, no ducking) + SFX + clip sound | off (text cards are cutaways) |
| `broll` | `duration`, else the end of the track | the `broll:` track (+ cutaways) | clip sound (`audio: true`) + optional music bed + SFX | off |

**Voiceover.** Record a VO, or generate one with ElevenLabs (Claude, via the connector) and register it:

```
cves assets add --id vo --file ~/Downloads/vo.mp3 --source elevenlabs --prompt "<script>" --licence "ElevenLabs paid plan"
```

```yaml
spine: voiceover
voiceover: {asset: vo}          # or {file: Raw/vo.wav}; denoise: false, tighten: true, chain: true
```

`cves ingest` extracts it (48 kHz mono, `Edit/voice_raw.wav`), optionally runs DeepFilterNet (`denoise: true`), tightens
pauses with the A-roll rules (gaps ≤ 0.22 s, 0.11 s breaths), applies the voice chain, writes `voice_final.wav`,
`voice_chain.json`, `edl.json` (`spine: voiceover`, rate, canvas, duration) and transcribes it into `words.json` (cut time,
whisper). Claude then writes the `broll:` track against the words.

**Music.** Set `music.file` (and `duration` to trim), run `cves beats`, then `cves autocut` to propose the track.

**Face-only stages skip.** With no A-roll there are no plates, mattes, faces, punch-ins, exposure balance, roto or chest
graphics (`cves select` / `cves prep` refuse with a one-line hint; `roto:` / `chest:` are validation warnings). QC reports
the presenter gates (FRAME-*, COL-03..10/12, CUT-03/05, RET-22, GFX-25/26) as **N/A**, the voice gates (SND-04/11/19/22/30,
CUT-01/02, RET-01/03, PLAT-11, STORY-09/10) as N/A on music / broll edits, and the caption gates as N/A when there are no
captions. N/A never blocks delivery; it is counted separately in `qc.json` (`na`).

## 5. The `broll:` track

Cut-time seconds. On the non-aroll spines the shots tile the timeline (gaps show the stage; validation warns); on the aroll
spine each shot is a cutaway over the presenter (snapped to segment boundaries unless `snap: false`), and the voice and
its captions continue over it. Drawn cutaways (title cards, stats) win where they overlap a shot.

```yaml
broll:
  - {src: Raw/city.mp4, start: 0.0, end: 2.4, in: 3.0}
  - {asset: hero_img, start: 2.4, end: 4.0, kenburns: {zoom: [1.0, 1.12], pan: [0.3, 0]}}
  - {src: Raw/phone.mov, start: 4.0, end: 6.2, in: 12.5, framing: fit, speed: 0.5, audio: true, gain: -14}
```

| key | default | |
|---|---|---|
| `src` \| `asset` | required (one) | footage path (project-relative) or an asset id (`assets:` / `Edit/assets.json`, provenance gate AST-01) |
| `start`, `end` | required | cut time; frame-snapped |
| `in` | `0` | source seconds where the shot starts |
| `speed` | `1` | constant source speed for the shot (0.5 = half speed); the clip's sound is time-stretched to match |
| `framing` | `broll.framing` (`fill`); stills `kenburns` | `fill` crops to the canvas aspect (never stretches); `fit` shows the whole picture on a blurred, dimmed fill of itself; `kenburns` = fill + a slow zoom |
| `kenburns` | `{zoom: broll.ken_burns}` | `{zoom: [from, to], pan: [x, y] or [[x0, y0], [x1, y1]] (−1..1 of the overflow), ease: io}` |
| `anchor` | `[0.5, 0.5]` | the source point a fill crop keeps centred (e.g. `[0.5, 0.3]` for a face high in a portrait clip) |
| `after` | `hold` | `hold` the last frame or `loop` when the source is shorter than the shot |
| `transition` | `cut` | `cut` \| `whip` \| `glitch` \| `fade` into this shot |
| `audio`, `gain` | `false`, `broll.audio_gain` | the clip's own sound in the mix (SFX stem), trimmed to the shot |
| `id`, `snap`, `note` | `b01`, … | element id `broll.<id>`; snap (aroll spine only) |

Any source works: size, rotation (phone clips stored on their side), SAR and frame rate. Shots are decoded with PyAV (the
same reader as the media templates), rotation applied, and sampled by time at the timeline rate. QC MOT-14 checks the scale
a shot applies to source pixels (WARN above 1.0×, FAIL above 1.5×, as FRAME-11 does for A-roll).

**HDR B-roll.** A PQ (`smpte2084`) or HLG (`arib-std-b67`) clip, in `broll:` or in any media template (`video_broll`,
`screen_rec`, `pip` / `split` panes, `overlay_render`), goes through the same HDR → SDR BT.709 chain as A-roll ingest
(`ingest._tonemap_chain`: zscale + `ingest.hdr.tonemap` at `ingest.hdr.npl` nits). `ingest.sdr_source` writes it once to a
lossless 10-bit FFV1 proxy `Edit/conform/<name>-<key>.sdr.mkv` (BT.709-tagged, rotation applied, timestamps kept; the key
covers the file, its mtime and size, and the filter), and `cves render` does that for every referenced clip before its
workers start. The clip's own sound is still read from the original. `ingest.hdr.broll: false` turns it off. HDR stills
(PQ AVIF / HEIC) are not tonemapped.

## 6. `cves autocut`

```
cves autocut [PROJECT] [--every beats|downbeats|bars] [--bars 2] [--min-shot 0.5] [--folder Raw] [--apply] [--json]
```

Proposes a `broll:` track whose cuts land on the music grid in cut time (`beats.plan`: the track as placed under the edit,
loops and drop alignment included). `beats` = every beat, `downbeats` = every bar, `bars` = every `--bars` bars; grid points
closer than `--min-shot` to the previous cut are skipped. Clips from `--folder` are used in name order, round-robin; a clip
used again continues where it left off; stills get `kenburns`. Without `--apply` it prints the YAML (Claude edits it);
`--apply` writes it into `edit.yaml` (a timestamped backup is kept). Defaults come from the style `autocut:` section.

## 7. Demos

`tools/make_demo.py OUT --kind aroll|voiceover|music|broll --size WxH [--small] [--edit legacy]` builds a synthetic project of each spine
at any canvas: drawn B-roll clips that cover what real footage throws at the engine (16:9, 9:16, a phone clip with a 90°
rotation flag, 25 fps next to 30 fps, a 3:2 still), a synthetic VO, a 100 BPM track. `tests/test_formats.py` and
`tests/test_spines.py` build them at 480×270 and run the full render → mix → encode → QC path. `--edit legacy` (aroll, full
script) uses `tools/demo_edit_legacy.yaml`: the v0.2 UI cutaways and roto cards, to see the tall / square / wide arrangements.
