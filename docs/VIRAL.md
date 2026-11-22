# Viral mode: organic posts, platform profiles and the platform sound slot

CVES edits paid ads **and** organic posts for Reels, TikTok, Shorts and YouTube. The two goals share the engine and the style
profile; viral mode adds a goal style layer, platform profiles and a platform sound slot.

## 1. `edit.yaml goal:`

```yaml
goal: viral          # ad (default) | viral
```

| | `goal: ad` (default) | `goal: viral` |
|---|---|---|
| Style layers | default → preset → inspire → brand → edit.yaml | default → **`styles/viral.yaml`** → preset → inspire → brand → edit.yaml |

The goal layer only changes defaults: a named preset, `cves inspire`, the brand and `edit.yaml style:` still win over it.

### The `viral` preset (`engine/cves/styles/viral.yaml`)
Retention-first defaults, all keys from `default.yaml`: faster pacing (`grammar.max_shot_s` 2.5),
a hook within 1 s (`structure.hook_change_s`), pattern interrupts at least every 2.5 s (`rhythm.interrupt_max_s`), cuts on
the beat (`rhythm.cut_on_beat`, `music.sync: cuts`), punchier captions (`pop`, size 60, ≤ 22 characters, outline,
numbers emphasised), faster entries, constant creep, and a louder SFX share (`sound.sfx_offset_db` 0). `structure.loop`
stays off: a loop is a per-video structure choice (set it in `edit.yaml style: {structure: {loop: true}}`).

## 2. Platform profiles (`platform.target`)

```yaml
style: {platform: {target: tiktok}}    # reels | tiktok | shorts | youtube | meta_feed | meta_stories
```

The table is data: [`engine/cves/styles/platforms.yaml`](../engine/cves/styles/platforms.yaml). Every box is a **fraction of the
frame**, so a profile works on any canvas (9:16, 4:5, 1:1, 16:9); pixels are computed from the real frame size at use time.

| target | safe box (x0 y0 x1 y1, fractions) | what it avoids | ideal / max s |
|---|---|---|---|
| `reels` | 0.06 0.14 0.94 0.65 | top bar, right rail, caption + CTA panel (Meta 14 / 35 / 6 %); = the v0.2 default zone | 7-35 / 180 |
| `tiktok` | 0.06 0.08 0.84 0.74 | right action rail, caption + sound line | 9-34 / 600 |
| `shorts` | 0.06 0.08 0.86 0.72 | right rail, title / channel / subscribe | 15-45 / 180 |
| `youtube` | 0.05 0.05 0.95 0.86 | title bar on pause, progress bar and controls (landscape) | 60-1200 / 43200 |
| `meta_feed` | 0.05 0.05 0.95 0.90 | feed controls (4:5 / 1:1) | 6-30 / 14460 |
| `meta_stories` | 0.06 0.14 0.94 0.80 | progress bar + account, reply bar / CTA (14 / 20 %) | 5-15 / 60 |

What a target changes:
- `platform.safe_zone` (used by captions, templates and covers) is filled from the profile in pixels of `platform.size`, unless a style layer sets it.
- captions end above its `caption_bottom` line.
- `sound.master_lufs` / `sound.true_peak` come from the profile unless a layer sets them (every platform plays at about −14 LUFS today).

With no target, the v0.2 behaviour holds: `platform.safe_zone` in pixels of the `platform.size` design space, scaled to the
real frame. `cves validate` errors on an unknown target.

## 3. The platform sound slot (trending sounds)

Organic posts often ride a trending sound that only the app can license. Cut to it without putting it in the file:

```yaml
music:
  slot: platform                      # file (default) | platform
  guide: Music/trend_reference.mp3    # a reference track | a beats.json | a tempo: 128, "128 bpm", {bpm: 128, first_beat: 0.12}
  sound: "Sound name or link in the app"
  drop_cut: 6.4                       # optional: where the drop lands in the video (cut seconds)
```

- **Cutting.** With a reference track, `cves beats` analyses the guide exactly as it would music (`music.sync: cuts` in the
  viral preset suggests beat moves; `--apply` writes them). With a tempo, the grid is `first_beat + k × 60 / bpm` (a downbeat on
  `drop_cut` when given).
- **Mix.** No music in the mix at all (voice + SFX, normalised to the master loudness). The guide is written to
  `Edit/stems/guide.wav` (the reference track laid where the edit expects it, or a click track for a tempo) and never mixed in.
- **Delivery.** `cves deliver` adds `<master>.guide.wav` and **POSTING.md** to `Export/vNNN/`: the sound to add, where to start
  it in the track, where the drop lands, the length vs the platform band, the in-app steps, and the first cuts vs the beat.
  `manifest.json` gets a `music_slot` block.
