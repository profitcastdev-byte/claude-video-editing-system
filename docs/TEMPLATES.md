# Templates

Every visual moment in an edit comes from a template. Claude fills in `edit.yaml`; it never writes new drawing code for a video.
Run `cves templates` to see the live list by kind, `cves templates <name>` for one template's params and its section here (`--json` for both). All times are cut-time seconds (from `Edit/words.json`). Elements must land on or just after their spoken word (gate GFX-01). Each template also emits its own sound-effect cues.

**What every template guarantees**
- **No copy in code.** Every string comes from `params`. Defaults are empty: leave a param out and that element is not drawn.
- **Look from the style.** Colours come from palette slots (`accent`, `accent_dark`, `text`, `card`, `card_border`, `icon_well`, `gold`, `star`, `negative`, plus the derived `muted`, `surface`, `line`). Fonts come through `gfx`, and motion from `motion.*` (`entry_s`, `stagger_s`, `slide_px`, `overshoot`). A `color:` param takes a slot name or a hex value.
- **Frame-accurate.** Every animation start is quantised to a whole frame (`gfx.q`). An element is first visible on the frame of its word (`gfx.enter`), and its logged `t_key` is that frame (MOT-07).
- **No pop-ins.** Every element enters with a fade, a rise / slide, or a scale from its own centre (MOT-12).
- **Sound on the picture.** Cues are clamped to the template's start, quantised to the frame of their visual event, and identical back-to-back cues get a small pitch / gain variation (SND-07 / SND-09). A cue is only emitted when its element exists: for example, there is no suffix hit without a suffix.
- **Typesetting.** Whitespace is collapsed. Separators (` · `, ` | `, ` / `) get drawn spacing (`type.sep_gap_em`), never repeated spaces (GFX-17). Centring uses the drawn ink, not the advance width (GFX-08). Long text shrinks to fit the safe zone.
- **Legible over video.** Small text on A-roll gets an auto-darkened bed when its colour misses the WCAG target against `legibility.video_bg` (GFX-15).
- **Script fallback.** Non-Latin text picks its font from `font_files.script_fallback`.

Layout is relative to the canvas (`G.W`, `G.H`, `G.safe()`; px at a 1080 short side, see "Layout on any canvas" below), inside the safe zone. Most generic templates take `align: center|left`, `y` (block position), `pad` and `out_at` (fade out).

**Common cutaway keys:** `id`, `start`, `end` (snapped to segment boundaries; `snap: false` to start mid-shot), `in: whip|glitch|cut|fade`, `out: …`. Any template can be used in any section. `KIND` only says where it is designed to sit.

---

## Generic templates (any talking-head or short-form edit)

### `title_card`: big kinetic type (cutaway)
Params:
- `lines`: 1–3 items, each a string or `{text, at, color, size, words_at}`;
- `at`;
- `reveal`: `words` | `lines` | `none`;
- `stagger`;
- `size` (120), `font` (`xb`);
- `color`, `accent` (words drawn in `accent_color`);
- `eyebrow`, `eyebrow_at`;
- `align`, `y` (block centre), `line_gap`;
- `sfx`: `lines` | `words` | `none`.

```yaml
- {id: t1, template: title_card, start: 3.20, end: 5.10, in: whip, out: cut,
   params: {at: 3.25, eyebrow: "THE FIX", lines: ["Stop guessing.", {text: "Start growing", color: accent}], reveal: words}}
```

### `stat` / `counter`: a number counting up (cutaway)
Params:
- `value`, `count: [start, dur]`, `start_value`;
- `prefix`, `suffix`, `suffix_at`, `decimals`;
- `grouping`: `intl` | `indian` (lakh / crore: 12,50,000) | `none`. The default comes from `locale.grouping`; the separators come from `locale.thousands` and `locale.decimal`;
- `size`, `color`;
- `icon`, `icon_at`;
- `label`, `label_at`, `label_mode` (`type` | `fade`);
- `unit`, `unit_at` (the line under the number);
- `pill`, `pill_at`;
- `align`, `y`;
- `ticks` (most count-up pops; default 6).

The count-up pops land on the frames where the eased digits change.
```yaml
- {id: s1, template: stat, start: 24.57, end: 30.32, in: whip, out: glitch,
   params: {label: "REVENUE IN 90 DAYS", label_at: 25.07, prefix: "₹", value: 1250000, grouping: indian, count: [26.75, 0.9],
            unit: "AFTER THE RELAUNCH", unit_at: 27.85, pill: "VERIFIED", pill_at: 29.0}}
```

### `checklist` / `list`: items with check, cross, number or bullet marks (cutaway)
Params:
- `items`: each a string or `{text, sub, at, mark, mark_at}`;
- `title`, `title_at`;
- `mark`: `check` | `cross` | `xfill` | `number` | `bullet` | `none`;
- `style`: `card` | `plain`;
- `align` (plain style only);
- `at` / `items_at` (base time), `item_spacing`;
- `size` (40), `y`.

Each mark is its own element, so its cue has a visual event.
```yaml
- {id: l1, template: checklist, start: 35.37, end: 40.87,
   params: {title: "What you get", at: 35.3, items: [{text: "Weekly posts", at: 35.5}, {text: "Review replies", sub: "within 24 hours", at: 36.8}, {text: "Monthly report", at: 38.4}]}}
```

### `comparison`: two columns, before / after or us vs them (cutaway)
Params:
- `left` / `right`: each `{title, items: [str | {text, at}], mark}`. Default marks: left `xfill` (the `negative` colour), right `check`;
- `at`, `rows_at: [t, …]`;
- `highlight`: `right` | `left` | `none`;
- `vs` (a small pill between the heads);
- `layout`: `columns` | `stacked`;
- `size` (38), `y`.

```yaml
- {id: v1, template: comparison, start: 12.0, end: 16.5,
   params: {at: 12.05, vs: "VS", left: {title: "BEFORE", items: ["Buried on page 2", "No reviews"]},
            right: {title: "AFTER", items: ["Top 3 on the map", "120 new reviews"]}, rows_at: [12.9, 14.1]}}
```

### `quote` / `testimonial` (cutaway)
Params:
- `text`;
- `name`, `role`;
- `avatar` (an asset, cropped to a circle);
- `stars` (0–5, halves allowed);
- `at`, `text_at`, `stars_at`, `name_at`;
- `font` (`b` | `serif`), `size` (52), `max_lines` (6);
- `card` (true), `quote_mark` (true);
- `align`.

```yaml
- {id: q1, template: quote, start: 41.0, end: 45.0,
   params: {at: 41.05, text: "Our calls doubled in a month.", name: "Asha Rao", role: "Owner, Café Nila", avatar: Brand/asha.jpg, stars: 5}}
```

### `steps` / `timeline`: 1–5 steps joined by a line that draws from node to node (cutaway)
Params:
- `steps`: each a string or `{title, sub, at}`;
- `layout`: `vertical` | `horizontal`;
- `at`, `step_spacing`;
- `title`, `title_at`;
- `number` (true; false gives check nodes);
- `size` (46), `y`.

More than 5 steps is refused with a one-line message.
```yaml
- {id: h1, template: steps, start: 50.0, end: 54.0, params: {title: "How it works", at: 50.05,
   steps: [{title: Audit, sub: "We check 40 signals", at: 50.4}, {title: Fix, at: 51.5}, {title: Grow, at: 52.6}]}}
```

### `logo_reveal`: a logo from an asset (cutaway or end)
Params:
- `logo`, `at`;
- `mode`: `scale` | `wipe` | `fade`;
- `width` (560), `y` (centre);
- `glow` (true), `glow_color`;
- `tagline`, `tagline_at`, `tagline_color`.

```yaml
- {id: lg, template: logo_reveal, start: 55.0, end: 57.0, params: {logo: Brand/logo-white.png, at: 55.0, tagline: "MARKET DIGITAL", tagline_at: 55.6}}
```

### `progress_bar` (cutaway)
Params:
- `value` (0–1, or 0–`max`), `max`, `from`;
- `at`, `dur`, `enter`;
- `label`, `label_at`;
- `show_value`, `prefix`, `suffix` (`%`), `decimals`;
- `color`, `y`, `height`, `ticks`.

```yaml
- {id: p1, template: progress_bar, start: 18.0, end: 20.5, params: {label: "Profile completeness", value: 0.92, at: 18.3, dur: 1.0}}
```

### `chart`: a simple bar or line chart (cutaway)
Params:
- `kind`: `bar` | `line`;
- `data`: each `[label, value]` or `{label, value}`;
- `at`, `stagger`, `dur`;
- `title`, `title_at`;
- `prefix`, `suffix`, `decimals`, `grouping`;
- `max` (auto);
- `highlight` (an index or a label; otherwise every bar is accent);
- `show_values`, `y`, `height`.

```yaml
- {id: ch, template: chart, start: 30.0, end: 33.5, params: {title: "Calls per week", at: 30.05, highlight: 3, data: [[W1, 12], [W2, 18], [W3, 31], [W4, 44]]}}
```

### `cta` (cutaway) and `end_card` (end card): a call to action
Params:
- `headline` (a string or lines);
- `button`, `press_at` (a press dip with the `button` sound);
- `handle` (a handle or URL), `icon` (to the left of the handle, e.g. `link`);
- `qr`: data to encode. Needs `pip install qrcode` (or `segno`); if neither is installed, the QR is skipped with a one-line notice;
- `logo`;
- `at` and the per-element times `logo_at`, `headline_at`, `button_at`, `handle_at`, `qr_at`;
- `button_color`, `size`, `y` (`y`: `cta` only).

`end_card` lays out from the canvas: the headline at display size (about 12 % of the safe-zone width; `size` = px at a
1080 short side overrides it), wrapped to two balanced lines when one does not fit; the button, handle, optional `logo`
(above the headline) and `qr` scale with it; the block is centred in the safe zone and shrinks to fit it, on any canvas.
Every element is centred on one axis, measured from the ink the layer really draws (GFX-08).

```yaml
end_card: {template: end_card, duration: 2.5, params: {headline: "Get found on Google Maps", button: "BOOK A FREE AUDIT", handle: "yourbrand.com/audit", icon: link, press_at: 52.3}}
```

### `lower_third`: name + role over A-roll (chest; replaces captions while visible)
Params:
- `name`, `role`;
- `at`, `role_at`, `out_at`;
- `align`: `left` | `center`;
- `style`: `bar` (an accent bar, with an auto bed) | `card` (a plate);
- `color`, `role_color`;
- `size` (54), `y` (by default just under the chin, inside the safe zone).

```yaml
chest: [{segment: 02_intro_0, template: lower_third, params: {name: "Dr. Vikram Shah", role: "Dentist · 12 years", at: 2.1}}]
```

### `kinetic_caption_emphasis` / `emphasis_word`: one emphasised word, big (roto: behind the presenter; or chest: in front)
Params:
- `word`;
- `at`, `out_at`;
- `size` (260), `color` (accent);
- `y` (baseline), `scale_from` (1.35), `tracking`.

```yaml
roto: [{segment: 05_every_day_0, template: kinetic_caption_emphasis, params: {word: "FREE", at: 9.98}}]
```

---

## Cutaways built for UI moments (full screen; they hide jump cuts; 40–55 % of runtime)
Laid out per canvas shape (FORMATS.md §3): the original layout on 9:16, a scaled block on square canvases, a landscape
arrangement on wide ones (`card_list` in two columns from 4 items, `browser_list` rows in two columns from 4 rows).
`top` and other px params are 1080×1920 design px and apply on tall canvases. `stat` (= `counter`) is documented with the
generic templates.
| Template | Use for | Key params |
|---|---|---|
| `search_rows` | searches typed out row by row | `label`, `pills [left, right]`, `pill_times {left:[t,dur], plus, right}`, `rows [{q, type:[a,b], tag, check, stars?}]`, `tag_text`, `enter`, `rows_in` |
| `card_list` | problems (✕) or services (✓) building one by one | `label?`, `label_at`, `items [{icon?, title, sub?, at, state: cross\|check\|xfill, state_at?}]`, `top?` |
| `browser_list` | website / content deliverables on a page card | `head [[word, at, accent?]]`, `enter`, `hero_at`, `hero_icon`, `rows [{text, at, icon?}]`, `row_icon`, `pill`, `pill_at` |

## Roto (behind the presenter; at most 4 moments, each ≤ 3 s)
**Free-space placement.** `map_card`, `listing_card` and `top3_card` place themselves (style `roto.place: auto`, or a
`place: auto | fixed` param): from the subject matte over the card's slot they take the largest scale (down to
`roto.min_scale`) at which the presenter covers at most `roto.max_cover` of the card, inside the shot's safe zone, on the
brightest free wall. On a tight selfie that is a smaller card beside the head instead of a dark rectangle behind it.
When nothing fits they keep the designed position, and QC GFX-27 flags a card the subject covers (warn > 40 %, fail >
65 %). Card entries move by whole pixels with steps that never grow (MOT-01 at any frame rate).
The cards are laid out in fractions of their own box: the 1080×1920 box on 9:16, a box filling the safe-zone height
(1.35:1 on wide canvases) elsewhere. `big_words` `ys` are 1080×1920 baselines (tall canvases); square and wide canvases
spread the lines down the safe zone.
| Template | Use for | Params |
|---|---|---|
| `map_card` | a map card behind the head: roads drawing in, pins popping (each pin is its own element) | `at`, `draw_at`, `pins_at`, `pins` (≤ 6), `pin_stagger`, `place` |
| `big_words` | one huge phrase behind the head | `words [[WORD, at, accent?]]`, `out_at`, `ys?`, `size`, `accent_size`, `color`, `accent_color` |
| `listing_card` | a listing / profile card rising behind the head | `at`, `stars` (0 for none), `stars_at` |
| `top3_card` | a ranked-results card and a badge | `at`, `badge`, `badge_at`, `rows`, `rows_at`, `row_stagger` |
| `kinetic_caption_emphasis` | one word, big (see above) | `word`, `at` |
| `text_behind` | big type tracked to the presenter's smoothed face landmarks, between the plate and the subject matte, so the head occludes it; lifts clear above the head when the segment has no matte; `color: auto` picks the light or dark token from the wall behind it; one size for every instance in a video unless `size` is set (`craft.behind.*`, MOTION.md "Craft"). Counts against `creative.craft_per_30s` | `text`! (`*stars*` = accent), `at`, `out_at`, `position` (above / behind / low), `size`, `track`, `color`, `accent`, `lines` |

## Chest (replaces captions while visible; placed just under the chin, never over the face)
| Template | Use for | Params |
|---|---|---|
| `wordmark` | a name as a display-serif wordmark (wipes in from its first letter) | `lines`, `sub`, `at`, `sub_at`, `out_at`, `size?`, `y?`, `color?`, `sub_color?` |
| `price_card` | a price line | `label`, `price`, `unit`, `at`, `color?` |
| `logo_lockup` | brand logo on the brand word + tagline | `logo`, `at`, `tagline`, `tagline_at`, `width?` |
| `lower_third` | name + role (see above) | `name`, `role`, `at` |

Chest templates anchor to `ctx["chin_hold"]` (a segment-stable chin) when the renderer provides it, else to `ctx["chin"]`.

## End card
| Template | Params |
|---|---|
| `logo_end` | `logo`, `label`, `pill`, `width?`, `y?` (in `end_card.params`; `end_card.duration` ≤ 3 s) |
| `end_card` | the generic CTA card (see `cta` above) |

## Captions (not a template; `captions:` in the style or edit.yaml)
Styles:
- `word_reveal`;
- `one_word`;
- `highlight` (with `highlight_mode: text|pill`);
- `box`;
- `karaoke`;
- `pop` (a per-word scale pop);
- `bounce` (a per-word drop-in bounce);
- `none`.

Flags:
- `outline` (stroke px) / `outline_color`;
- `shadow` (+ the auto legibility bed, `legible`);
- `emphasis: {words: [...], color: accent, scale: 1.15, numbers: true}`;
- `emoji` (colour emoji when a colour-emoji font exists, else skipped), `emoji_font`;
- `per_style: {<style>: {max_chars, max_lines, size_scale}}`;
- `language` (script fallback font).

Layout:
- lines wrap by measured width inside `platform.safe_zone` minus `pad_x`;
- the `chin` position sits under the chin (`chin_gap`, `chin_min_gap`) and above the safe-zone bottom (`pad_bottom`);
- RTL text never crashes. Without libraqm it is drawn in visual order, unshaped.

## Motion pieces (`m_*`, HTML rendered by headless Chromium)

Senior-grade motion design: HTML/CSS compositions in `engine/cves/motion/pieces/`, rendered to RGBA frames once and cached (authoring contract, runtime and CSS variables: [MOTION.md](MOTION.md)). They lay out in `u` units (1 % of the shorter canvas side) inside the safe zone, so the same params work at 9:16, 1:1 and 16:9. Preview any piece: `cves motion preview <piece> --size 1080x1920 --out sheet.png`.

**Where they go.** Kind `overlay` = usable in `cutaways:` (full screen on the stage, role `cutaway`) and in `chest:` (over the A-roll, role `chest`, plays its exit before the segment ends). `<name>_roto` sits behind the presenter, `<name>_end` is an end card.

**Common params:** `at` (cut-time second the piece's clock starts; default the slot start), `duration` (default: to the slot end; give it when a `chest:` entry spans several segments), `exit` (default on in `chest:` / roto). Every other `at` / `*_at` param is a cut-time second too. Text params take `*stars*` around accent words.

| template | kinds | hero | what it does | params (`!` = required) |
|---|---|---|---|---|
| `m_before_after` | cutaway/overlay |  | A framed picture opens on the "before", a slider handle sweeps across wiping in the "after", overshoots past the middle and settles on the split, with BEFORE / AFTER chips riding each side. | `before`, `after`, `before_text`, `after_text`, `before_label`, `after_label`, `split_at`, `sweep_at` |
| `m_callout` | overlay/cutaway |  | A pin drops onto a point with a squash and two sonar rings, a leader line draws out from it and a glass label card slides off the end of the line. | `label`!, `sub`, `x`, `y`, `side`, `icon` |
| `m_chart_bars` | cutaway |  | Bars grow from a baseline on a stagger with their values counting above them; the highlighted bar is in the accent, the rest stay quiet. | `title`, `bars`!, `prefix`, `suffix`, `decimals`, `highlight` |
| `m_checklist_tick` | cutaway/overlay |  | Rows settle in as an empty checklist, then each square box is ticked in turn with a drawn stroke, done rows strike through (or light up) and a progress counter climbs to the total. | `items`!, `title`, `strike`, `counter`, `stagger` |
| `m_comment_pop` | overlay/cutaway |  | A social comment bubble springs up from its avatar corner, the handle and text settle in, then the heart pops filled and the like count ticks up. | `handle`!, `text`!, `likes`, `verified`, `time`, `avatar`, `position` |
| `m_compare` | cutaway |  | Two cards build side by side (stacked on a tall canvas), the "before" muted with crosses, the "after" lit in the accent with checks, a VS chip pops on the seam. | `left_title`, `right_title`, `left`!, `right`!, `vs` |
| `m_countdown` | cutaway/overlay | yes | Each number rolls out of a mask as the next rolls in while an accent ring drains once per number, then the end word lands; clock mode ticks HH:MM:SS (only changing digits roll) over a draining bar. | `mode`, `from`, `to`, `step_s`, `end_text`, `seconds_left`, `label`, `caption` |
| `m_cta` + `m_cta_end` | cutaway/overlay/end | yes | A headline settles, an accent button springs in, a cursor glides to it on a curve and clicks; the button presses, a ripple rings out and the label confirms. | `text`!, `title`, `sub`, `done`, `cursor` |
| `m_follow_card` + `m_follow_card_end` | cutaway/overlay/end | yes | A profile card rises in (avatar or monogram, name, handle, chip), a cursor clicks Follow, the button flips to its done state with a drawn tick and a bell rings with a badge. | `name`!, `handle`, `button`, `done`, `logo`, `platform`, `bell`, `cursor` |
| `m_glass_card` | cutaway/overlay |  | A frosted card focus-pulls in (blur to sharp, slight scale), a sheen sweeps across, then icon, tag, title and body build inside it. | `title`!, `body`, `eyebrow`, `icon`, `chip`, `align` |
| `m_highlight_words` + `m_highlight_words_roto` | cutaway/overlay/roto |  | A sentence settles in, then marker strokes sweep behind the key words one after another and the words knock out of the marker. | `text`!, `style`, `highlight_at`, `plate` |
| `m_karaoke` + `m_karaoke_roto` | overlay/cutaway/roto |  | The line settles in dim and each word lights on its own time with a small lift; a pill (or underline) glides from word to word and re-forms on the next line. | `text`, `words` ([{word, at}]), `wps`, `style`, `align`, `position` |
| `m_kinetic_title` + `m_kinetic_title_roto` | cutaway/overlay/roto | yes | Headline words rise out of masks on a tight stagger, accent words get an underline sweep, eyebrow and sub settle in around them. | `text`!, `eyebrow`, `sub`, `align`, `scale`, `underline` |
| `m_list_build` | cutaway/overlay |  | Rows slide in one by one on a stagger (or on their own `at`), each mark draws itself on (check, cross, number or dot), the latest row is lit. | `title`, `items`!, `mark`, `stagger` |
| `m_logo_sting` + `m_logo_sting_end` | cutaway/overlay/end | yes | An accent pill outline draws itself around the mark and breathes out, the logo (or wordmark) focus-pulls in with a light sweep across it, the tagline tracks in underneath. | `logo`, `text`, `tagline`, `ring` |
| `m_lower_third` | overlay/cutaway |  | An accent bar grows, a solid plate wipes open from it, the name rises inside and the role tracks in; it wipes back out before the shot ends. | `name`!, `role`, `align`, `position` |
| `m_map_route` | cutaway/overlay |  | A stylised street map (drawn from the style's tones, no tiles) pushes in while the start pin lands, a glowing route draws with a travelling head, the destination pin drops and the place label and ETA chip rise. | `to`!, `from`, `eta`, `points`, `seed`, `draw_s` |
| `m_notification_stack` | overlay/cutaway |  | Phone-style notification banners slide down one after another; each new one lands on top while the older ones compress behind it into a dimmer, smaller stack. | `items`!, `time`, `position`, `stagger` |
| `m_price_tag` | cutaway/overlay | yes | The old price settles and an accent line strikes it through, the new price lands with weight under it, a starburst badge spins in and settles, an optional deadline chip slides in. | `price`!, `old_price`, `currency`, `badge`, `label`, `note` |
| `m_progress` | cutaway/overlay |  | A track draws in, the fill runs to the value with a glowing head and a counting percentage, milestone dots light as the fill passes them. | `label`, `value`, `milestones`, `show_value`, `fill_s` |
| `m_quote` | cutaway/overlay |  | An oversized accent quotation mark settles, the quote fades up word by word in the serif, a rule draws and the attribution slides in. | `quote`!, `author`, `role`, `serif` |
| `m_quote_portrait` | cutaway/overlay |  | A portrait (or an initials monogram) opens out of a circle or arch mask with a slow push-in while an accent ring draws round it; the quote fades up word by word, then a rule, the name and role slide in. | `quote`!, `author`, `role`, `portrait`, `shape`, `serif` |
| `m_rating_stars` | cutaway/overlay |  | The score counts up in big type while five stars fill left to right (the last one fractionally), then the review count and its source settle in underneath. | `score`!, `count`, `source`, `decimals`, `label` |
| `m_spec_callouts` | overlay/cutaway |  | Points light up with a pulse, an elbow leader line draws out and a glass spec card slides off its end; each side's cards share a column that clears every point. | `callouts`! ([{x, y, title, value, side, at}]), `image`, `stagger` |
| `m_split_reveal` + `m_split_reveal_roto` | cutaway/overlay/roto | yes | A word slams in, splits horizontally along its middle, the halves slide apart and a second word rises out of the gap in the accent colour. | `text`!, `reveal`!, `eyebrow`, `split_at` |
| `m_stat_counter` | cutaway/overlay | yes | One big number counts up on an expo curve with a soft accent glow, its suffix lands with the final digit, a meter fills underneath and the label and caption frame it. | `value`!, `from`, `prefix`, `suffix`, `decimals`, `grouping`, `label`, `caption`, `max`, `count_s` |
| `m_steps` | cutaway/overlay |  | Numbered nodes on a line that draws itself from step to step; each node fills and its label rises as the line reaches it. Vertical on tall canvases, horizontal on wide ones. | `title`, `steps`!, `stagger` |
| `m_three_up` | cutaway/overlay |  | Three cards cascade in (a row on wide canvases, a stack on tall ones), each with a picture, an icon or a number; the highlighted card lifts with an accent edge. | `items`!, `title`, `image_1..3`, `icon_1..3`, `highlight`, `stagger` |
| `m_ticker` | overlay/cutaway |  | One or two marquee bands wipe open across the safe zone and scroll at a constant speed after an eased start; the second band runs the other way, items split by accent marks, edges faded. | `items`!, `rows`, `speed`, `tilt`, `position`, `mark` |
| `m_timeline` | cutaway/overlay |  | A time axis draws on (down a tall canvas, across a wide one) and reaches each dated event in turn: its dot lands, the date and label rise beside it, the latest event stays lit. | `events`!, `title`, `stagger`, `current` |

```yaml
cutaways:
- {id: c2, template: m_stat_counter, start: 6.94, end: 10.26,
   params: {label: "Calls from Google", value: 312, prefix: "+", suffix: "%", caption: "in the first 90 days", max: 400}}
chest:
- {segment: 01_hook_0, template: m_lower_third, params: {name: "Alex Morgan", role: "Owner · Morgan Roofing", at: 0.4}}
roto:
- {segment: 05_cta_0, template: m_kinetic_title_roto, params: {text: "*TODAY*", at: 11.0}}
end_card: {template: m_logo_sting_end, duration: 2.0, params: {logo: Brand/logo-white.png, tagline: "Built for storms"}}
```

## Icons
Icons are Material Design (Apache-2.0), in `assets/icons/`:
- `post` (calendar);
- `link`;
- `chat`;
- `star`;
- `search`;
- `pin`;
- `phone`.

Any `<name>_512.png` dropped in `assets/icons/` is usable by its name. An unknown icon name draws nothing. Never draw icons by hand.

To add an icon:
1. Put the SVG in `assets/icons/`.
2. Render it with `rsvg-convert -w 512 -h 512` to `<name>_512.png`.
3. Map an alias in `gfx.MAT` if you want one.

## Layout on any canvas
The canvas is configurable (style `canvas.size`, [FORMATS.md](FORMATS.md)). Template authors:
- read the frame as `G.W`, `G.H` and the safe zone as `G.safe()` **at call time** (never `from ..gfx import W, H`);
- place things relative to them (centre `G.W / 2`, blocks centred in the safe zone, fractions of `G.H`), and write px sizes
  (fonts, radii, gaps) as px at a 1080 short side. The registry lays the template out on a canvas with a 1080 short side and
  **rasterises it at the real canvas**: inside `G.layer` every coordinate, font size, stroke and icon is multiplied by the
  raster scale `G.R` (= `G.U`), so 4K graphics are drawn at 4K. Layers come back `G.PW × G.PH` (the real canvas);
- if a template touches layer pixels itself (a blur radius, `np.arange` over a layer, `Image.new` for a glow), it sizes
  them from the layer (`im.size`, `a.shape`) and converts layout px with `G.px(v)`; a module that can't sets
  `RASTER = False` (or `{names that are raster-safe}`) and is drawn at the layout size, then scaled. `media.py` keeps
  boxes in layout px and every picture buffer (`view`, masks, `canvas_layer`) in layer px; `ctx["aroll"]` arrives at the
  real canvas size in a raster-scaled call;
- a module that draws its own picture at the canvas resolution (e.g. `broll_shot`) sets `NATIVE = True` (or `{names}`) and
  scales its own px by `G.U`;
- a third-party module with hard-coded 1080×1920 coordinates can set `DESIGN = True`: it keeps drawing in 1080×1920 and is
  fitted, per instance, into the canvas safe zone (uniform scale, never up, centred). No built-in module does any more: the
  UI cutaways and roto cards pick a tall / square / wide arrangement (`templates/_layout.py`, FORMATS.md §3).
Everything is the identity at 1080×1920.

### `broll_shot` (internal: the `broll:` track)
One B-roll shot, full frame (`media.py`, native). The `broll:` track in `edit.yaml` compiles to it; you rarely name it
yourself. Params: `asset` (id or footage path), `in`, `speed`, `after`, `framing` (`fill` | `fit`), `kenburns`, `anchor`,
`audio`, `gain`, and the craft moves (MOTION.md "Craft"): `ramp` (speed ramp), `out` (source end a ramp lands on),
`camera` (push / pull / pan / drift, `handheld`), `depth` (2.5D parallax on a still), `match` (match cut onto the previous
shot). See FORMATS.md §5.

## Adding a template
1. Write `render(t, p, ctx) -> [El]` and `cues(p, ctx) -> [(t, sfx, gain_db, kw)]` in any module under `engine/cves/templates/` (or `$CVES_TEMPLATES`, `~/.cves/templates`, `PROJECT/Brand/templates`). Use these gfx helpers:
   - `G.enter(t, at, dur, G.fps_of(ctx))` for entries;
   - `G.q(at, fps)` for `t_key`;
   - `G.cues_out(cues, ctx)` for cues;
   - `G.col(...)`, `G.tidy(...)`, and `G.draw_text(..., anchor="ms"|"li"|"rs")` for colours and type.

   Log every element with a stable `id`, its `text`, `t_key` and `asset`.
2. Register it in that module's `T` dict. Set `KIND` / `KINDS`.
3. Add a section here and a CHANGELOG entry, and put a moodboard frame of it in the PR.
