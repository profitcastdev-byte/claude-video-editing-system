# Motion layer

CVES's motion design is HTML/CSS: every *piece* is a small web page that headless Chromium (Playwright) renders to
transparent RGBA frames. CSS gives the full aesthetic range (blur, gradients, masks, real type), and a seek-driven
runtime keeps every frame deterministic. The pieces are templates named `m_<piece>` (list: [TEMPLATES.md](TEMPLATES.md), "Motion pieces").

Code: `engine/cves/motion/` (`__init__.py` renderer + cache + CLI, `runtime.js`, `base.css`, `pieces/<name>/`) and
`engine/cves/templates/motion.py` (the template wrapper).

## How a frame is made
1. **Page.** The engine wraps `piece.html` in a page with, in this order:
   - `@font-face` rules for the style's fonts (from `assets/fonts`, as `file://` URLs);
   - the CSS variables below;
   - `base.css`;
   - `window.__CVES_BOOT` (params, motion tokens, ctx);
   - `runtime.js`;
   - the piece.
2. **Load.** Chromium opens the page at the canvas size (`device_scale_factor` 1, transparent background). `CVES.__ready()` waits for the fonts and images, runs the piece's `setup`, then collects its `cues`.
3. **Frames.** For frame k the engine calls `window.__seek(k / fps)` and screenshots with `omit_background`. `__seek` returns the text that is visible on that frame; it goes into the element log.
4. **Cache.** The frames, plus `manifest.json` (visible text per frame, cues, params), are written to `PROJECT/Edit/motion/<hash>/`. The hash covers the piece folder, the runtime, `base.css`, the params, the style subset the page sees, the size, fps, frame count and exit flag. A new render goes to a temporary folder and is renamed into place, so two processes racing on the same piece never corrupt it.
5. **Render.** `render.render()` calls `motion.prerender(pr, timeline)` before its spawn pool starts: every motion piece the timeline uses is rendered once, in one browser. The workers only read PNGs; a worker that finds no cache (moodboard, a single-frame call) renders it itself.

Missing Playwright or Chromium is a one-line error with the fix: `python -m playwright install chromium` (inside the CVES venv).

## Timeline semantics
A motion template's clock starts at `at` (a cut-time second; default: the slot's start), quantised to a whole frame, and runs for `duration` (default: to the slot's end). Frame index = `round((t - start) * fps)`.

| slot | role in the element log | exit animation |
|---|---|---|
| `cutaways:` | `cutaway` (drawn on the style's stage) | off (the cutaway's transition cuts it) |
| `chest:` | `chest` | on: plays during the last `motion.exit_s` |
| `roto:` (`m_<piece>_roto`) | `roto` (composited behind the presenter) | on |
| `end_card:` (`m_<piece>_end`) | `end` | off |

`exit: true|false` overrides the default. A `chest:` entry listing several segments is called once per segment: give it `at` and `duration` so it plays once across them.

Every other param named `at` or `*_at`, at any depth (e.g. `items[2].at`), is a cut-time second. The engine passes it to the page piece-relative, so a piece that moves on the timeline keeps its cache. Path params (`type: path`, `asset` or `icon`) are resolved like other template assets and passed as `file://` URIs. An `icon` given as a bare name means `assets/icons/<name>.svg`.

Sound: a piece declares its cues in JS (`CVES.cue(t, sfx, gain_db, kw)`), so they land on the frame of the visual event. `cues()` reads them from the cache, or from a frame-less page load. If Chromium is missing it falls back to `meta.yaml cues:`. Names come from `assets/sfx` (`whoosh`, `swipe`, `pop`, `card`, `ding`, `lowhit`, `boom`, `riser`, `button`, ...). `gfx.cues_out` clamps, quantises and varies them like every other template's cues.

## Authoring a piece
A piece is a folder:
- built-in: `engine/cves/motion/pieces/<name>/`;
- per user: `~/.cves/motion/<name>/`;
- per client: `PROJECT/Brand/motion/<name>/`.

Later folders override earlier ones. A folder name `foo` becomes the template `m_foo`.

### `meta.yaml`
```yaml
title: Glass card
description: One sentence: what moves and how (shown by `cves templates <name>` and `-v`, and in TEMPLATES.md).
kinds: [cutaway, overlay]      # cutaway | overlay | roto | end. The first is the main kind; roto / end add m_<name>_roto / _end
hero: false                    # marks a hero piece (`cves motion list` shows [hero])
duration: 3.0                  # default length for previews / slots without an end
params:                        # types: str number int bool list dict time path asset icon color any; required: true
  title: {type: str, required: true, help: "*stars* mark accent words"}
  icon: {type: icon, default: ""}
preview: {duration: 3.0, params: {title: "Show up when they *search*"}}
cues: [[0.0, swipe, -20]]      # fallback only (no Chromium); real cues come from the piece's JS
```
`cves validate` checks edit.yaml params against these types.

### `piece.html`
Markup, a `<style>` and a `<script>`. The script registers the piece:
```html
<div class="safe center"><h1 class="display" id="hd"></h1></div>
<script>
(() => {
  const C = CVES, D = C.D; let W, tl;
  C.piece({
    setup(P, ctx) {                       // once: build the DOM, measure, fit (fonts are loaded)
      W = C.words(document.getElementById('hd'), P.text);
      tl = C.timeline().at('words', 0, D(0.7));
    },
    seek(t, P, ctx) {                     // every frame: set EVERY animated property from t alone
      W.inners.forEach((wi, i) => C.rise(wi, t, i * D(0.05), D(0.7), wi.offsetHeight));
      if (ctx.exit) { const ex = C.exitP(t); /* ... */ }
    },
    cues(P, ctx) { C.cue(0, 'whoosh', -20); },
  });
})();
</script>
```

**The seek contract.**
- `seek(t)` must be pure: the frame depends on `t` only, never on the previous call.
- Nothing may run on the wall clock: no `requestAnimationFrame` timing, no `setTimeout`, no `Date`, no `Math.random` (use `CVES.rand(seed)`). CSS transitions and animations are switched off by `base.css`.
- Anything visible must be set in `seek`: start from the hidden state for small t.

**Text in the element log.** Put `data-text="..."` on each text block (`CVES.words` does it for you). A block counts as visible when its opacity chain is above 0.15 and it is on the canvas.

### Runtime (`window.CVES`)
| helper | what |
|---|---|
| `D(s)` | a choreography duration or offset scaled by `motion.energy` (calm = longer) |
| `IN`, `OUT`, `MOVE` | the house curves from `motion.ease`: entry (decelerate), exit (accelerate), move (both) |
| `easings` | `linear`, `in/out/inOut` `Quad`, `Cubic`, `Quint`, `Expo`; `outBack` / `inBack` / `inOutBack` (overshoot from the style × energy); `outElastic`; `spring(zeta)` (a damped spring that settles exactly at p = 1) |
| `ease(name)` | name → function (`'in'`, `'out'`, `'move'`, `'spring(0.6)'`, any easing name) |
| `prog(t, t0, dur)`, `tween(t, t0, dur, from, to, ease)` | progress 0..1, an eased value |
| `stagger(i, n, each, from)` | the delay of item i (`start` / `center` / `end`) |
| `timeline()` | named spans: `.at(name, t0, dur)`, `.then(name, dur, gap)`, `.p(name, t, ease)`, `.raw`, `.t0`, `.end`, `.last` |
| `words(el, text, chars)` | split into masked word spans (`.w` > `.wi`), `*accent*` words get `.accent` + `.acc` |
| `lines(wordEls)`, `fit(el, maxW, maxH, maxLines)` | group words into laid-out lines; shrink type to fit |
| `rise(el, t, t0, dur, dist, {axis, fade, ease})` | the standard entry: travel + fade + velocity blur |
| `set(el, {x, y, s, sx, sy, r, o, blur, clip})` | transform / opacity / filter in one call |
| `mblur(fn, t)` | fake motion blur (px) from the speed of `fn(t)`, as a `motion.shutter` shutter would smear it; 0 on slow frames, capped at `motion.blur_max_u` |
| `exitP(t, dur)` | exit progress over the last `motion.exit_s` (0 when the slot has no exit) |
| `icon(parent, uri)`, `svg(parent, inner)`, `draw(path, p)`, `CHECK`, `CROSS` | tinted icons, inline SVG, stroke draw-on |
| `fmt(v, decimals, grouping)` | numbers: `intl` / `indian` / `none` grouping |
| `cue(t, sfx, gain_db, kw)`, `rand(seed)`, `ctx` | sound cues; a seeded PRNG; `{w, h, fps, dur, exit, u, motion}` |

### CSS variables (from the style)
| variable | from |
|---|---|
| `--accent`, `--accent-dark`, `--text`, `--card`, `--card-border`, `--icon-well`, `--gold`, `--star`, `--negative`, `--muted`, `--surface`, `--line`, `--bg` (+ `-rgb` triplets: `rgb(var(--accent-rgb) / .3)`) | `colors.*` (derived tones as in gfx), `stage.background` |
| `--font-sans` (weights 500 / 600 / 700 / 800), `--font-serif` | `font_files.*`; Noto fallbacks for Devanagari, Bengali, Gujarati, Tamil, Telugu, Kannada, Malayalam |
| `--u` (1 % of the shorter canvas side), `--w`, `--h`, `--landscape` | the canvas |
| `--t-0` … `--t-9` | modular type scale: `2.2u × motion.type_ratio^k` |
| `--s-1` … `--s-6` | spacing: 1, 2, 3, 4.5, 6, 9 u |
| `--r`, `--r-s` | `motion.radius_u` |
| `--glass-alpha` | `motion.glass_alpha` |
| `--safe-l`, `--safe-t`, `--safe-r`, `--safe-b` (insets), `--safe-w`, `--safe-h` | `motion.safe`, else `platform.safe_zone` when its aspect matches the canvas, else `motion.safe_fallback` |

`base.css` classes:
- `.safe` (the safe-zone box) and `.center`;
- type: `.display`, `.title`, `.body`, `.eyebrow`, `.num`, `.serif`, `.on-video`;
- surfaces: `.glass`, `.solid`, `.chip`, `.rule`, `.sheen` (sweep it with `--sheen-x`);
- `.ic` (masked icon).

**Rules for pieces:**
- Never write a literal colour or font: use the variables.
- Size everything in `u` / the type scale, never px, and lay out inside `.safe`. Test at 9:16 and 16:9; use `@media (min-aspect-ratio: 1/1)` for a landscape layout.
- Leave the background transparent: the stage or the video is composited later. "Glass" is a translucent tinted fill with a lit edge, because `backdrop-filter` cannot see the video.

### Previewing
```
cves motion list
cves motion preview m_glass_card --params '{"title": "Hello *world*"}' --size 1080x1920 --out sheet.png
cves motion preview m_glass_card --at 2.0 --out frame.png         # one full-size frame
cves motion preview m_lower_third --bg video --out clip.mp4        # a clip over a footage stand-in (ffmpeg from the config)
```
Inside a project, `--project .` previews with its style and its `Brand/motion/` pieces. Previews cache in the system temp folder (`cves-motion-preview`).

## Quality bar
Every built-in piece follows these rules:
- **Motion:** eased on the house curves; staggered (never all at once); overshoot used once per piece at most; velocity blur only on fast frames; entries fade with their travel, so nothing pops in.
- **Layout:** type from the scale, shrunk to fit rather than clipped; inside the safe zone; legible over video (plates or shadows on overlay pieces).

## Craft (motion moves between and inside shots)
Code: `engine/cves/craft.py` (pure functions: the same inputs give the same pixels in every worker) and
`engine/cves/templates/craft.py` (`text_behind`). Every look comes from the style (`craft.*`,
`transitions.<kind>_s`; [STYLE.md](STYLE.md)).

### Text behind the speaker
`roto: [{segment: 01_hook_0, template: text_behind, params: {text: "2 *SECONDS*", at: 0.45}}]`

The type is drawn on the background plate and the subject is composited back on top through its matte, so the head
occludes the letters (the roto slot's order: plate -> type -> subject). It is placed from the presenter's face landmarks
(eye midpoint, head top, chin), smoothed with a zero-phase Gaussian whose sigma is in seconds (`craft.behind.smooth_s`, so
60 fps is as calm as 30), and follows the head by `craft.behind.track` of its motion (0 = locked where it entered, 1 =
glued; default 0.4, subtle). The path is kept in the safe zone and the clamped path is smoothed again, so the type never
stops dead on the safe edge. `position: above` (default) sets the
last line's baseline so the head covers its lower `craft.behind.overlap`; `behind` centres it on the eyes; `low` puts it
behind the shoulders. The letters rise out from behind the head (`entry_s`), breathe in their tracking and hold with a
slow 2.5 % push. One element per block (`behind.text`, role `roto`).

**Colour.** `craft.behind.color: auto` (default) measures the graded plate behind the type's box over its hold (the person
masked out) and picks the light or dark token (`craft.behind.light` / `dark`) that reaches the legibility target; an accent
that fails becomes its darker (on a light wall) or lighter variant, and when neither token reads a soft bed is added
(`auto_bed`). A `color` param or a fixed style colour skips the measurement.

**One size.** Every `text_behind` without its own `size` uses one size per video: the smallest size any instance fits at
(each fitted once, at its shot's tightest zoom), so two moments never read as two styles (GFX-20).

**No matte.** A segment without `Edit/matte/<seg>.mkv` renders with an empty matte (the roto layer lands in front), and
`text_behind` lifts the type clear above the head (`craft.behind.no_matte: above`) or keeps it with a legibility bed
(`front`): it never prints across the face.

### Speed ramps
On a `broll:` shot (or a `video_broll` cutaway's params):
```yaml
broll:
  - {asset: city, start: 6.6, end: 8.2, in: 0.6, ramp: {preset: slam}}                       # style presets
  - {asset: run, start: 8.2, end: 10, in: 2, out: 6.5, ramp: {keys: [[0, 2], [0.5, 0.25], [1, 1]], ease: inOutExpo, blend: blend, audio: pitch}}
```
`keys` are `[shot fraction, speed]`, eased between (`craft.ramp.ease`), floored at `craft.ramp.min_speed`. Source time is the
running integral of the speed curve, so it is strictly increasing; with `out` the curve is normalised so the shot's first
frame is `in` and its last is `out` exactly, else it consumes `speed x duration x mean ramp speed`. Frames: `blend` (default)
crossfades the two neighbouring source frames on slow sections (no stutter) and averages a shutter's worth
(`craft.ramp.shutter`) on fast ones (motion blur); `nearest` takes the nearest frame. The shot's own sound (`audio: true`)
is muted (`craft.ramp.audio: mute`) or played tape-style, pitch following speed (`pitch`).

### Camera moves
`camera: {move: push | pull | pan_left | pan_right | pan_up | pan_down | drift | none, amount, ease, handheld: true}` on a
`broll:` shot (also `image` / `video_broll` params, without the roll). Eased curves (`craft.camera.ease`); `handheld` (or
`move: drift`) adds a seeded smooth wobble (`drift_u`, `drift_hz`, `drift_rot`): the same shot always wobbles the same way.
Pans and drift zoom in just enough never to show an edge.

**2.5D parallax.** A still with `depth: <asset>` (a grayscale depth map, white = near, or an image whose alpha is the
subject) is split into two planes at `craft.camera.depth_split`: the background has the subject area inpainted, and the
foreground moves `(1 + parallax)` times as much as the background (`camera.parallax`, default `craft.camera.parallax`).

### Match cuts
`match: saliency | centroid | {mode, scale_range}` on a `broll:` shot that starts where the previous shot ends. The engine
finds the salient shape of the outgoing shot's last frame and of this shot's first frame (`saliency`: spectral residual;
`centroid`: the bright, high-contrast shape), then scales this shot about its shape (clamped to `craft.match.scale_range`,
>= 1 so the fill crop never shows an edge) and moves it so the shapes coincide. `craft.match.settle_s` > 0 eases back to
the shot's own framing. `craft.find_in(a, frame_at, t0, t1)` searches a clip for the in-point whose shape lines up best.

### Transitions
`cutaways[].in / out`, `broll[].transition`, `end_card.in`, `transitions: [{t, kind}]` take, besides cut / whip / glitch /
fade:

| kind | what | look keys |
|---|---|---|
| `whip_pan` | the frame slides out with a directional smear, the next slides in from the other side | `craft.transitions.whip_dir` |
| `zoom_through` | the outgoing shot rushes in to the centre with radial blur, the incoming one lands from slightly in | |
| `mask_wipe` | a feathered shape covers the outgoing shot and uncovers the incoming one, with a lit leading edge | `wipe_shape` (bar / circle / matte), `wipe_color` |
| `luma_fade` | dip to colour by brightness: shadows go first, highlights come back first | `dip_color` |
| `glitch_lite` | a short RGB split and a few slipped slices, no scanlines | |
| `light_leak` | a procedural warm leak (seeded blobs + a streak, screen-blended), no third-party media | `leak_color`, `leak_strength` |
| `dip` | a soft dip to a style colour | `dip_color` |

Each lasts `transitions.<kind>_s` either side of the cut and is seeded by its cut time (deterministic). Every transition
the plan asks for is rendered.
