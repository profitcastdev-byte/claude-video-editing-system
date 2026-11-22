# Treatments: more than one idea per job

A senior editor explores before committing. `cves treatments` turns one approved edit plan into 2-3 distinct creative
takes, renders each as a fast proxy, puts them side by side, and promotes the one the user picks. The engine does the
work; Claude judges the sheet; the user chooses. Nothing here calls a model.

```
cves treatments list                          built-in + project treatments (the preferred one first)
cves treatments make [punchy,cinematic]       Edit/treatments/<name>/: edit.yaml, treatment.yaml, plan.json
cves treatments render [NAMES] [--proxy]      proxies (default): half size, fast x264, plates + mattes reused
cves treatments render NAME --full            the same at full size with delivery settings (rarely needed)
cves treatments compare [NAMES] [--sequential]   Edit/treatments/compare/: sheet.jpg, compare.mp4, compare.json
cves treatments pick NAME                     -> Edit/edit.yaml (backup kept) + Edit/treatment.yaml, journaled
```

Then `cves build` renders the picked plan in full, and delivery goes on as usual.

## 1. What a treatment is
A YAML file with:

| key | meaning |
|---|---|
| `name`, `label`, `summary` | its id, display name and one line for the user |
| `style:` | a **style overlay**: only keys of `engine/cves/styles/default.yaml` (checked on load) |
| `structure:` | **plan hints** that `make` applies to a copy of `Edit/edit.yaml` (below) |

Built-ins live in `engine/cves/styles/treatments/`: `punchy`, `cinematic`, `minimal`. A project can add its own or
override a built-in by name in `PROJECT/treatments/<name>.yaml`; style `treatments.offer` sets which ones `make` builds
by default (the project's own are always added).

### Where the style overlay sits
The treatment layer goes **after inspire and before Brand and `edit.yaml`** (docs/CONTRACTS.md §1):

```
default → goal → learned (repo, personal) → preset → inspire (Edit/style.yaml) → TREATMENT → Brand → edit.yaml style:
```

So a treatment beats the measured look (it is a deliberate creative choice for this video) but the client's brand rules
and per-video overrides still win. `S["_sources"]` shows `treatment:<name>`. In a treatment folder the layer is that
folder's `treatment.yaml`; after `pick` it is `Edit/treatment.yaml`.

### Structure hints (`structure:`)

| hint | values | what `make` does to the plan |
|---|---|---|
| `pace` | `fast` / `medium` / `slow` | a label for the cut density the hints below produce |
| `max_shot_s` | seconds or null | broll spines: a video shot (fill or fit) longer than this, not under a drawn cutaway, is split on a word near its middle into a wide shot and a punched-in shot (kenburns from 1.22x) |
| `min_shot_s` | seconds or null | broll spines: a shot shorter than this absorbs the next one into a longer hold, never past `grammar.max_shot_s`, never past the clip's end, and never the opening cut inside the first second (RET-09) |
| `cutaways_per_30s` | number or null | caps drawn cutaways; the ones that carry a number, then a list, then the longest stay |
| `punch_ins` | `add` / `keep` / `gentle` | `add`: an `aroll.snap` punch-in from the strongest word (a number first, else the longest word) of the first A-roll shot seen whole (no cutaway over it; shots under a chest graphic only as a fallback) to the end of that shot, at the scale `Timeline._auto_zoom` will give it stepped up by `framing.min_step`, at a scale level that still changes by `framing.min_step` at the next cut (CUT-05) and stays under 1.4x. `gentle`: removes a snap (pair it with smaller `framing.zoom_levels` in `style:`) |
| `transitions` | `whip` / `glitch` / `fade` / `cut` / `keep` | the transition family: every cutaway's `in` / `out`, broll shot entries that start a sentence (others stay cuts, so it never becomes effect soup), explicit `transitions:`, the end card |
| `roto` | `keep` / `drop` | `drop` removes the behind-the-speaker moments |
| `music.bed_lu_offset` | LU | added to `edit.yaml music.bed_lu` when the edit sets one (otherwise the overlay's `sound.bed_lu` applies) |
| `motion.swap` | `{drawn template: m_piece}` | swaps drawn templates for HTML motion pieces with mapped params (`stat` → `m_stat_counter`, `checklist`/`list` → `m_list_build`, which the built-ins leave out: its row slide crosses the PLAT-01 margin on 1080×1920); unknown mappings are left alone |
| `broll_move` | `[from, to]` or null | broll spines: a slow kenburns push on fill shots that do not move yet |

Per-video caption look keys in `edit.yaml captions:` (size, max_chars, style...) that the treatment's caption preset sets
are removed from the treatment's copy, so the preset shows; content keys (`hide`, `fixes`, `events`, `auto`) stay. A
per-video `aroll.creep` follows the treatment's `framing.creep`. Inline `edit.yaml style:` keys are never touched: they
still win, as the merge order says.

## 2. The built-ins

| | punchy | cinematic | minimal |
|---|---|---|---|
| idea | retention-first energy for feeds | slow, filmic, warm | restraint, clean information |
| captions | `pop`, bigger, outlined, keywords and numbers popped | `word_reveal`, small and low (`lower_third`), sentence case, no emphasis | `box`: one plain subtitle line on a dark box |
| transitions | whips into and out of cutaways, on sentence starts | dips to black | straight cuts, no transition sounds |
| punch-ins | a punch-in on a key word; every shot creeps (2%) | slow push (1.2%), long holds | gentle reframes (`zoom_levels [1.0, 1.16]`), no creep |
| B-roll pace | long shots split into wide + punch-in | short shots merged into holds with slow pushes | as planned |
| graphics | drawn `stat` → `m_stat_counter` at energy 0.85, roto kept | the same piece at energy 0.3, cubic ease, no roto | only the most informative cutaways (2 per 30 s), no roto |
| grade + stage | a touch of contrast, light vignette; dotted stage | relit (darker, desaturated) background, highlight roll-off, vignette, warm skin / cool wall, lifted blacks; plain glowing stage | neutral, a little roll-off; flat stage |
| sound | bed −8 LU, SFX at full share, `music.sync: cuts` | bed −12 LU, SFX −6 dB, `music.sync: drop` | bed −13 LU, SFX −6 dB, `music.sync: drop` |

Punchy's B-roll splits and cinematic's holds stay inside the style's `grammar.max_shot_s` and `rhythm.interrupt_max_s`.

## 3. Proxies
`render` (with or without `--proxy`) renders each treatment at `treatments.proxy_scale` (0.5) of the canvas through the
normal renderer: the timeline is planned and the exposure solved at full size, then the canvas and face tracks are scaled,
and the existing plates and mattes are resized as they decode (`render.render(..., proxy=0.5)`). Nothing is re-ingested.
The mix is the real mix of that plan; the encode uses `encode.proxy_video_args` (x264 `treatments.proxy_preset`
`veryfast`, crf `treatments.proxy_crf` 26, the delivery colour tags). Full-quality output is unchanged: proxies never go
to `Export/`, and the `delivery:` settings are not used for them.

Each treatment folder is a `project.Variant`: `edit.yaml`, `treatment.yaml`, `frames/`, `timeline.json`, `elements.jsonl`,
`exposure.json`, `beats.json`, `mix*.wav`, `stems/` and its journal live in `Edit/treatments/<name>/`; everything ingest
made is read from `Edit/`.

## 4. Comparing
`compare` grabs the same timecodes (`treatments.compare_points`, evenly through the shortest proxy) from every treatment and
lays them out as `sheet.jpg`: one row per treatment with its label and metrics (cuts, mean shot, caption style,
transitions, punch-ins, graphics, bed, motion energy), one column per timecode. `compare.mp4` is the first
`treatments.compare_max_s` seconds, `stacked` (side by side on portrait canvases, one above the other on landscape; the
audio is the first treatment's, marked in its label) or `--sequential` (one after another, each with its own sound).

Claude looks at the sheet before offering it: the treatments must read as clearly different and each must be tasteful.
If two look alike, adjust the project's treatment files and `make` again.

## 5. Picking
`pick <name>` copies the treatment's `edit.yaml` to `Edit/edit.yaml` and its `treatment.yaml` to `Edit/treatment.yaml`
(the old ones are kept as `*.bak-<time>`), and journals a `treatment-pick` event (the choice, what was offered, goal /
client / platform, the plan metrics, the edit.yaml diff). `cves learn mine` turns repeated picks into a
`treatments.prefer` candidate per client or goal (docs/LEARNING.md §3); once a person promotes it, that treatment is
offered first.

To drop a treatment later, delete `Edit/treatment.yaml` (and the `treatment:` key in `edit.yaml`); the plan keeps its
adapted structure.

## 6. When to offer treatments
The editor skill offers 2-3 treatments as proxies after the edit plan when the brief is open or creative ("make it
pop", "something different", a new client with no references, a launch). With a tight brief, a measured inspiration
style or a brand that fixes the look, skip it: one plan, built well.
