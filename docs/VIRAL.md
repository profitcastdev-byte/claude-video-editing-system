# Viral mode: organic posts, platform profiles and retention QC

CVES edits paid ads **and** organic posts for Reels, TikTok, Shorts and YouTube. The two goals share the engine, the style
profile and every v0.2 gate; viral mode adds a goal layer, platform profiles, retention gates and a platform sound slot.
The craft rules Claude applies are in [knowledge-base/modules/viral-playbook.md](../knowledge-base/modules/viral-playbook.md).

## 1. `edit.yaml goal:`

```yaml
goal: viral          # ad (default) | viral
```

| | `goal: ad` (default) | `goal: viral` |
|---|---|---|
| Style layers | default → preset → inspire → brand → edit.yaml | default → **`styles/viral.yaml`** → preset → inspire → brand → edit.yaml |
| Hook change (RET-24) | `structure.hook_change_s` 1.5 s, WARN | 1.0 s, WARN |
| Hook text / subject by 1 s (RET-25) | n/a | WARN |
| Interrupt gaps (RET-26 / RET-27) | 4.0 s max, WARN | 2.5 s max, WARN |
| Loop seam (RET-28), payoff (RET-29) | n/a | WARN (RET-28 only with `structure.loop: true`) |
| Dead air (RET-31) | WARN (SND-13 stays the ad gate) | **FAIL** |
| `music.slot: platform` | **refused** (`cves validate` error): an ad carries licensed music | allowed |

Everything an ad already had (story gates, cutaway share, PLAT-*, SND-*) keeps working unchanged. The goal layer only
changes defaults: a named preset, `cves inspire`, the brand and `edit.yaml style:` still win over it.

### The `viral` preset (`engine/cves/styles/viral.yaml`)
Retention-first defaults, all keys from `default.yaml`: faster pacing bands (`grammar.max_shot_s` 2.5, `topic_by_s` 1.0),
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
- PLAT-02 judges text against the profile's box on the real frame, plus its `caption_bottom` line for captions.
- RET-30 checks the duration: FAIL above the platform's maximum, WARN outside the ideal band. DEL-04 still checks the brief.
- `sound.master_lufs` / `sound.true_peak` come from the profile unless a layer sets them (every platform plays at about −14 LUFS today).

With no target, the v0.2 behaviour holds: `platform.safe_zone` in pixels of the `platform.size` design space, scaled to the
real frame. `cves validate` errors on an unknown target.

## 3. Retention gates (RET-24 to RET-32)

`cves qc` runs them from `engine/cves/qc/retention.py` on the rendered master (luma decoded at 96 px wide, mono audio),
`Edit/timeline.json`, `Edit/elements.jsonl`, `Edit/faces.json` and the guide stem. A **pattern interrupt** is any of: an
A-roll cut (with its zoom step), a cutaway in or out, a transition, the snap, a graphic entering (element log, captions
excluded), or a picture change in the master (frame step ≥ `retention.scene_diff`). Events closer than `retention.merge_s`
are one interrupt.

| id | checks | threshold (style key) | status |
|---|---|---|---|
| RET-24 | first visual change after frame 0 | `structure.hook_change_s` (1.5; viral 1.0) | WARN |
| RET-25 | on-screen text or a strong subject (presenter face, detailed centre) | by `retention.hook_subject_s` (1.0), viral only | WARN |
| RET-26 | longest gap between interrupts | `rhythm.interrupt_max_s` (4.0; viral 2.5) | WARN |
| RET-27 | effect soup: gaps under `rhythm.interrupt_min_s` sustained | for `retention.soup_window_s` (1.5 s) | WARN |
| RET-28 | loop seam: last 0.3 s vs first 0.3 s, last vs first frame (SSIM) | `retention.loop_min_similarity` (0.6), viral + `structure.loop` | WARN |
| RET-29 | payoff: a picture / audio peak or a graphic entry in the last `structure.payoff_window` | 20 %, viral only | WARN |
| RET-30 | duration in the platform band | `platform.target` | FAIL above max, WARN outside ideal |
| RET-31 | dead air: no speech, music or SFX (the guide counts in slot mode) | `retention.dead_air_s` (0.6) below `retention.dead_air_db` (−45 dBFS) | FAIL viral, WARN ad |
| RET-32 | cuts on the guide beat (slot) or the music beat (`rhythm.cut_on_beat`) | `retention.guide_on_beat_min` (60 %) within `music.snap_tolerance_s` | WARN; FAIL if the slot has no usable guide |

Every threshold is recorded in [DECISIONS.md](../knowledge-base/DECISIONS.md); the rows are in
[QC-GATES.md](../knowledge-base/QC-GATES.md). New gates start as WARN unless the fault is objective.

## 4. The platform sound slot (trending sounds)

Organic posts often ride a trending sound that only the app can license. Cut to it, but never put it in the file:

```yaml
goal: viral
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
- **QC.** SND-04 (bed level) becomes "the music stem is silent" (FAIL if any music is in the master); RET-32 checks the cuts
  against the guide; RET-31 treats the guide as sound (the in-app sound will play there).
- **Delivery.** `cves deliver` adds `<master>.guide.wav` and **POSTING.md** to `Export/vNNN/`: the sound to add, where to start
  it in the track, where the drop lands, the length vs the platform band, the in-app steps, and the first cuts vs the beat.
  `manifest.json` gets a `music_slot` block.
- **Ads never use it.** `cves validate` errors on `music.slot: platform` without `goal: viral` (RULEBOOK §0.12).

## 5. The workflow with `goal: viral`

The skill (`plugin/skills/video-editor/SKILL.md`, "goal: viral") adds three things to the normal steps:
1. **Brief:** ask the hook type and the structure (playbook §1-2), the platform and whether it loops; record the trending sound if any.
2. **Story:** design the hook first (the first second, picture and words), then the payoff, then the middle.
3. **Plan:** budget the interrupts (one every ≤ `rhythm.interrupt_max_s`, never a run under `rhythm.interrupt_min_s` for
   longer than `retention.soup_window_s`) before placing graphics; set `structure.loop` when the end should flow into the start.
