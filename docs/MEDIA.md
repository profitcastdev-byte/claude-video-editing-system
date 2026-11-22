# Media: images, B-roll, screen recordings, picture-in-picture, split screens, pre-rendered overlays

Drawn graphics (search rows, card lists, counters) are one kind of cutaway. Real edits also cut to photos, stock or
client B-roll, app and website recordings, the presenter in a corner bubble, before/after splits, and motion graphics
pre-rendered in Remotion, HyperFrames or After Effects. This page covers:

- the `assets:` block in `edit.yaml` and the provenance registry in `Edit/assets.json`;
- the `cves assets` command;
- the six media templates in `engine/cves/templates/media.py`, with an `edit.yaml` example for each;
- how the engine hooks into render and the mix.

Generation itself (Magnific / Freepik, ElevenLabs, stock) is done by Claude through MCP connectors, never by the engine. See
[plugin/skills/video-editor/connectors.md](../plugin/skills/video-editor/connectors.md) and `/cves:assets`.

## 1. Assets

### Declare them in `edit.yaml`
```yaml
assets:
  hero_img:    {path: Assets/hero.jpg, licence: client-owned}             # a file the client supplied
  city_broll:  {url: "https://www.pexels.com/video/...", licence: "Pexels licence"}   # Claude downloads it
  clinic:      {generate: {provider: magnific, kind: image, prompt: "bright dental clinic reception, morning light, photoreal", aspect: "9:16"},
                licence: "Freepik Premium"}
  vo_tag:      {generate: {provider: elevenlabs, kind: voice, prompt: "Call us today.", voice: "<voice id>"}}
  sparkle_fx:  {path: Assets/sparkle_4444.mov, licence: "own render"}   # ProRes 4444 with alpha
```
Each entry has one of these:
- `path`: a project-relative file or folder (a PNG sequence is a folder);
- `url`: a page or file Claude downloads;
- `generate`: `{provider, kind, prompt, aspect?, duration?, model?, voice?}`. `kind` is one of `image`, `video`, `rgba`, `upscale`, `cutout`, `voice`, `sfx` or `music`.

An entry can also carry a `licence`, which `cves assets add` copies into the registry.

Templates refer to assets **by id**: `params: {asset: hero_img}`. `Timeline.resolve` resolves ids through
`assets.resolve(pr, id)`, so `ctx["resolve"]("hero_img")` returns the absolute path. Every template that takes an `asset:` also
accepts a plain project path, but `cves assets check` flags a path that isn't declared.

### Register them: `cves assets`
| command | what it does |
|---|---|
| `cves assets add PROJECT --id X --file PATH [--source file\|stock\|magnific\|elevenlabs\|url\|client\|screen\|render] [--prompt ".."] [--model ".."] [--licence ".."] [--url ..] [--notes ..] [--move]` | copies the file or folder into `PROJECT/Assets/` (to the `path` edit.yaml declares, if it declares one) and writes its provenance to `Edit/assets.json` |
| `cves assets list PROJECT` | registered assets (kind, size, duration, source, licence, path) plus the declared assets still to generate, download or register |
| `cves assets check PROJECT` | exit 1 if any asset that is declared or used is missing, has changed since it was registered (sha256), has no source or licence, or was generated with no prompt recorded |
| `cves assets todo PROJECT` | prints the declared assets that have no file yet, as ready-to-run steps: ask about cost, the MCP tool to call, the prompt, where to save the file, and the exact `cves assets add` line |
| `cves assets resolve PROJECT ID` | prints the absolute path an id resolves to |

`PROJECT` may be omitted (current folder), or given as `cves --project P assets ...` or `cves assets ... --project P`.

A registry record (`Edit/assets.json` → `assets.<id>`):
```json
{"id": "sparkle", "path": "Assets/fx_4444.mov", "kind": "rgba", "sha256": "d688…", "source": "render",
 "prompt": null, "model": null, "provider": null, "licence": "own render", "url": null, "created": "2026-11-18T17:33:21",
 "probe": {"w": 540, "h": 960, "duration": 2.0, "fps": 24.0, "has_alpha": true, "pix_fmt": "yuva444p12le"}}
```
`kind` is one of `image`, `video`, `rgba` (a video, PNG or PNG sequence with alpha), `audio` or `font`. The probe reads stills with PIL and
video and audio with `ffprobe` (`config.get("ffprobe")`). A phone clip's rotation is applied to `w`/`h`.

**Provenance.** `cves assets check` lists every asset with no file, no source or licence, no prompt (generated), or a file that changed since it was registered.

## 2. Media templates

Common rules:
- **Times.** All times are cut-time seconds. `at` (default: the cutaway start) is when the media starts. Frame `i` of the cut maps to source time
  `in + (i - round(at * fps)) / fps * speed`, at the timeline fps (`ctx["fps"]`). After `out`, the clip either loops (`after: loop`), holds its last frame (`after: hold`), or disappears (`after: hide`, the overlay default).
- **Look.** Colours (`colors.accent`, `colors.card`, `colors.card_border`, `colors.icon_well`), radii, shadows, entry motion and SFX names all come from the style: `media.*` and `motion.*` in `styles/default.yaml`. Nothing is hard-coded.
- **Element log.** Every element has a stable id and logs `asset=` (the registered project path, e.g. `Assets/hero.jpg`). The picture's role is `media`; labels and captions have role `cutaway`, carry their text, and have a `t_key` so GFX-01 can check "shown before it is said".
- **SFX.** The cutaway transition already carries the entry whoosh or swipe (mix). A card, pane or bubble that enters *after* the cutaway starts adds `media.sfx_in`. `screen_rec` clicks add `media.sfx_click`. `sfx: ""` on any template silences its cue.
- **Sources.** Clips are decoded with PyAV, kept open per process, and read forward. A seek only happens on a jump back or more than 2 s ahead, and a 6-frame LRU serves repeat reads. A big downscale is area-averaged before the warp. Edges with alpha are premultiplied, so they don't fringe.

### `image`: still with Ken Burns
| param | default | |
|---|---|---|
| `asset` | required | image id |
| `fit` | `cover` | `cover` \| `contain` (on a card, contain is matted with `colors.card`) |
| `zoom` | `media.ken_burns` | `[from, to]` over the shot (or one number) |
| `pan` | `[0, 0]` | end offset `[x, y]`, or `[[x0, y0], [x1, y1]]`. Range −1..1 of the overflow, so the view never leaves the picture |
| `kb_s`, `ease` | to the cutaway end, `linear` | duration and `io` easing of the Ken Burns move |
| `frame` | `media.frame` | `bleed` (full screen) \| `card` (rounded card at `media.card_box`, with a shadow and outline) |
| `box`, `radius` | style | custom rect `[x0, y0, x1, y1]` / corner radius |
| `enter`, `out_at` | `media.entry` for a card that lands after the cut | `rise` \| `scale` \| `fade` \| `none`, timed by `motion.entry_s`, `motion.slide_px` and `motion.overshoot` |
| `label`, `label_at`, `caption`, `caption_at` | – | small label above the picture, and an accent caption pill over its lower edge |
```yaml
- {id: c1, template: image, start: 1.63, end: 7.55, in: whip, out: glitch,
   params: {asset: hero_img, frame: card, zoom: [1.0, 1.15], pan: [[0, 0], [0.6, -0.3]], at: 1.9,
            label: YOUR LISTING, label_at: 2.0, caption: MAP PACK, caption_at: 2.6}}
```

### `video_broll`: B-roll clip
Takes every `image` param (`zoom` defaults to `[1, 1]`), plus:
- `in`, `out`: source seconds;
- `speed`;
- `after: loop | hold`;
- `audio: true`, which routes the clip's own sound into the mix (see §3), at `gain` dB.
```yaml
- {id: c2, template: video_broll, start: 15.43, end: 17.81, in: glitch, out: cut,
   params: {asset: city_broll, in: 0.5, after: loop, audio: true, gain: -14, label: B-ROLL, label_at: 15.6}}
```

### `screen_rec`: a recording inside a phone or browser frame
| param | default | |
|---|---|---|
| `device` | `phone` | `phone` (bezel and island) \| `browser` (traffic lights and a URL bar with `url`) \| `none` |
| `box` | `media.device_box.<device>` | device rect |
| `zoom` | – | `[{t, rect: [x0, y0, x1, y1], dur?}]`. `rect` is in 0..1 of the source. From `t` the view eases into the rect over `dur` (default `media.zoom_s`); `[0, 0, 1, 1]` zooms back out |
| `cursor` | – | `[{t, x, y, click?}]` in 0..1 of the source. The highlight (`colors.accent`, `media.cursor_size`) glides into each key over `cursor_move_s` (0.4 s) and pulses on a `click` |
| `fit` | `cover` | for the un-zoomed view (`contain` letterboxes in black) |

`screen_rec` also takes `in`, `out`, `speed`, `after`, `at`, `enter`, `label`, `caption` and `audio`.
```yaml
- {id: c3, template: screen_rec, start: 24.57, end: 30.32, in: whip, out: glitch,
   params: {asset: app_rec, device: phone, at: 24.9, label: THE APP, label_at: 25.0,
            zoom: [{t: 26.0, rect: [0.05, 0.25, 0.65, 0.55]}, {t: 28.5, rect: [0, 0, 1, 1]}],
            cursor: [{t: 25.3, x: 0.5, y: 0.5}, {t: 26.6, x: 0.3, y: 0.42, click: true}, {t: 27.8, x: 0.7, y: 0.8, click: true}]}}
- {id: c2b, template: screen_rec, start: 17.81, end: 21.23,
   params: {asset: site_rec, device: browser, url: maps.example.com/search, fit: contain,
            zoom: [{t: 18.6, rect: [0.5, 0.0, 1.0, 0.5]}], cursor: [{t: 18.2, x: 0.3, y: 0.6}, {t: 19.4, x: 0.75, y: 0.25, click: true}]}}
```

### `pip`: the presenter over B-roll
| param | default | |
|---|---|---|
| `bg` | – | `{asset, in, out, speed, after, zoom, pan, audio}` (full-bleed image or clip), or `{template, params}` (any template, e.g. a `card_list`) |
| `shape` | `media.pip.shape` | `circle` \| `rounded` \| `cutout`. `cutout` is the presenter cut out by the matte, anchored to the bottom corner, at `scale` (`media.pip.cutout_scale`) |
| `corner`, `size`, `margin`, `ring` | `media.pip.*` | `br` \| `bl` \| `tr` \| `tl`. The bubble sits on the platform safe-zone edge; `ring` is an accent outline width in px |
| `face_zoom` | `media.pip.face_zoom` | how many face-heights the bubble shows |
| `at`, `out_at`, `caption`, `label` | | the bubble pops in with `motion.overshoot` |
```yaml
- {id: c4, template: pip, start: 35.37, end: 40.87, in: whip, out: glitch,
   params: {bg: {asset: city_broll, after: loop}, at: 35.8, shape: circle, corner: br, caption: "THAT'S ME", caption_at: 36.2}}
```

### `split`: two panes
- `layout: tb | lr`;
- `ratio` and `gap` (defaults `media.split.ratio` and `media.split.gap`);
- `radius`;
- `panes: [pane, pane]`, where each pane is either `{asset, in, out, speed, after, fit, zoom, pan, audio, label, at}` or `{aroll: true, zoom, label, at}`.

A pane with a later `at` slides in from its own edge. Labels are accent pills by the divider, kept inside the safe zone.
```yaml
- {id: c5, template: split, start: 42.50, end: 46.17,
   params: {layout: tb, panes: [{asset: city_broll, label: BEFORE}, {aroll: true, label: AFTER, at: 43.0}]}}
```

### `overlay_render`: pre-rendered RGBA
- `asset`: a ProRes 4444 / QuickTime-with-alpha `.mov`, a `.webm` with alpha, a PNG, or a PNG-sequence folder (give it `fps`; the default is the timeline fps);
- `at`, `in`, `out`, `speed`, `after` (default `hide`: one-shot);
- `box` and `fit` (default: full canvas, `contain`);
- `opacity`;
- `blend: normal | screen | add | multiply`;
- `base: {asset, ...} | {template, params}`, drawn under it when it is used as a cutaway;
- `sfx`, `audio`.

Where to put it:
- in `cutaways:`, over a picture or graphic via `base`;
- in `chest:`, over the A-roll in front of the presenter (captions hide while it shows);
- in `roto:`, behind the presenter.

Blend modes are expressed as straight-alpha "over", so they pass through `El` like everything else:
- `screen` / `add` un-multiply by luminance (alpha = max(rgb)). This is exact for light FX rendered on black, the usual case;
- `multiply` darkens by 1 − luminance.

Export real alpha (ProRes 4444) when you can.
```yaml
- {id: c_price, template: overlay_render, start: 32.80, end: 33.90, snap: false,
   params: {base: {asset: hero_img, zoom: [1.1, 1.2]}, asset: sparkle, blend: screen, at: 32.85, fit: cover, opacity: 0.95}}
chest:
  - {segment: 06a_not_better_0, template: overlay_render, params: {asset: sparkle_seq, at: 11.6, fps: 24, after: hide}}
```
Making a test RGBA clip with ffmpeg:
`ffmpeg -f lavfi -i "color=c=black@0:s=540x960:r=24:d=2,format=rgba,geq=r=255:g=190:b=40:a='255*clip(1.4-hypot(X-(80+T*190),Y-480)/90,0,1)'" -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le fx.mov`

## 3. Hooks into render and the mix

**Render.** `render.py` provides these:
- `ctx["fps"]` and `ctx["S"]` (the style) through `Timeline.ctx()`;
- `Timeline.resolve` resolves asset ids through `assets.resolve(pr, id, strict=False)`;
- `ctx["aroll"] = (rgb float HxWx3, matte float HxW)`, framed like the A-roll shot, for the templates in `NEEDS_AROLL`.

`media.py` declares `NEEDS_AROLL = {"pip", "split"}` and gives only those two the kind `media`. The full-screen picture templates have the kind
`cutaway`, so they never pay for an A-roll decode or grade. The head position comes from `ctx["aroll_face"] = (cx, cy, h)` when render
provides it; otherwise it is found from the matte (top of the person plus the head band's centroid). If `ctx["aroll"]` is missing (for example in a
moodboard frame), pip and split draw a placeholder well and warn once.

**Mix.** `video_broll`, `screen_rec`, `split` panes and `pip` backgrounds with `audio: true` emit this cue:
`(at, "asset:<id>", gain, {"asset": id, "trim": (in, in + dur), "speed": s, "reveal": True})`. The mix resolves
`asset:<id>` through `assets.resolve(TL.pr, id)` instead of the SFX bank. Speed other than 1 is applied with `librosa.effects.time_stretch`.
