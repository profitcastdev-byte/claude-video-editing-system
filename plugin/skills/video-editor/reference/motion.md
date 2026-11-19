# Motion pieces and craft moves (read when planning `m_*` pieces, roto, ramps, camera moves or transitions)
The motion layer (`docs/MOTION.md`) gives senior-grade animation (30 pieces): kinetic titles, glass cards, stat counters,
list builds, lower thirds, quotes, highlight sweeps, progress bars, map-pin callouts, logo stings, split reveals, compare,
steps, bar charts, CTAs, plus map routes, timelines, before/after sliders, comment pops, notification stacks, price tags,
rating stars, checklist ticks, tickers, countdowns, quote-with-portrait cards, karaoke word reveals, spec callouts,
three-up grids and a follow / subscribe end card (`m_follow_card_end`). `cves motion list` lists them; `/cves:motion`
previews one; `cves templates <name>` prints one piece's params.
- **When:** the beat carries one idea that motion explains better than the face: a number (`m_stat_counter`), a list or
  steps, a contrast (`m_compare`, `m_split_reveal`), a name (`m_lower_third` in `chest:`), a place (`m_callout`), the
  offer (`m_cta`), the brand (`m_logo_sting` as `end_card`).
- **How to pick:** the piece whose structure matches the line (one number, one list, one quote...), its copy taken from
  `words.json`, its `at` on the keyword. Over A-roll use `chest:` (it exits by itself before the shot ends); full-screen
  use `cutaways:`; behind the presenter use the `_roto` variant.
- **Craft moves** (`docs/MOTION.md` "Craft"): text behind the speaker (`roto:` `text_behind`, tracked to the face,
  occluded by the head) for the hook's one punch word; a speed ramp (`ramp:` on a `broll:` shot) to land a reveal; a
  camera move (`camera:` push / pull / pan / handheld drift, 2.5D with `depth:` on a still) so a still or a static clip
  breathes; a match cut (`match:` on the incoming shot) when two shots share a shape; one or two transition kinds
  (`whip_pan`, `zoom_through`, `mask_wipe`, `luma_fade`, `glitch_lite`, `light_leak`, `dip`) where the story turns, never
  on every cut. Each has a reason in `DIRECTION.md`; they count against `creative.craft_per_30s` and
  `creative.transition_kinds_max`, and render downgrades transitions closer than `craft.transitions.min_gap_s` to cuts (it
  prints each one: fix the plan rather than fight it).
- **Restraint:** at most one hero motion moment (meta `hero: true`: kinetic title, stat, logo sting, split reveal, CTA)
  per ~8-10 s unless the style says more (`motion.hero_min_gap_s`; render warns). Supporting pieces stay quiet. Never
  stack two pieces on one frame. The style's `motion.energy` sets the pace; don't fight it per piece.
