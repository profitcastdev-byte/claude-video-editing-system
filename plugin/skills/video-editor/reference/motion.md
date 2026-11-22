# Motion pieces and craft moves (read when planning `m_*` pieces, roto, ramps, camera moves or transitions)
The motion layer (`docs/MOTION.md`) has 30 pieces: kinetic titles, glass cards, stat counters,
list builds, lower thirds, quotes, highlight sweeps, progress bars, map-pin callouts, logo stings, split reveals, compare,
steps, bar charts, CTAs, plus map routes, timelines, before/after sliders, comment pops, notification stacks, price tags,
rating stars, checklist ticks, tickers, countdowns, quote-with-portrait cards, karaoke word reveals, spec callouts,
three-up grids and a follow / subscribe end card (`m_follow_card_end`). `cves motion list` lists them; `/cves:motion`
previews one; `cves templates <name>` prints one piece's params.
- **Which piece for what:** a number (`m_stat_counter`), a list or steps, a contrast (`m_compare`, `m_split_reveal`), a
  name (`m_lower_third` in `chest:`), a place (`m_callout`), the offer (`m_cta`), the brand (`m_logo_sting` as
  `end_card`). Copy from `words.json`, `at` on the keyword. Over A-roll use `chest:` (it exits by itself before the shot ends); full-screen
  use `cutaways:`; behind the presenter use the `_roto` variant.
- **Craft moves** (`docs/MOTION.md` "Craft"): text behind the speaker (`roto:` `text_behind`, tracked to the face,
  occluded by the head); a speed ramp (`ramp:` on a `broll:` shot); a camera move (`camera:` push / pull / pan / handheld
  drift, 2.5D with `depth:` on a still); a match cut (`match:` on the incoming shot); transition kinds (`whip_pan`,
  `zoom_through`, `mask_wipe`, `luma_fade`, `glitch_lite`, `light_leak`, `dip`) as `in` / `out` of a cutaway or in
  `transitions:`. The style's `motion.energy` sets the pace of every piece.
