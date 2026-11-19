# Engine contracts

Every module in `engine/cves` builds on the interfaces below. If you change one of them, update this file in the same commit.

## 1. No look is hard-coded

Every visual, pacing or sound decision is read from the **style profile**:

```python
from cves import style as STY
S = STY.load(pr)                     # merged dict
S.get("captions.style", "word_reveal")   # dotted lookup with a default
```

**Merge order** (later wins):
1. `engine/cves/styles/default.yaml`, the neutral defaults;
   - `engine/cves/styles/viral.yaml` when `edit.yaml goal: viral` (the goal layer, [VIRAL.md](VIRAL.md));
2. `knowledge-base/taste/learned.yaml`, the repo's learned layer (team taste, shared through git);
3. `~/.cves/taste/learned.yaml`, the personal learned layer (`$CVES_TASTE`);
4. the preset named by `edit.yaml style.preset`;
5. `PROJECT/Edit/style.yaml`, written by `cves inspire`;
6. `PROJECT/Brand/style.yaml`;
7. inline keys under `edit.yaml style:`.

The learned layers (2, 3) hold `scopes: {global | goal:<x> | platform:<x> | client:<x>: {style keys}}` and apply only the
sections whose scope matches the project (`edit.yaml goal:`, `platform.target`, `project.client`; absent keys match only
unscoped sections), general before specific. They are written only by `cves learn promote` (a person approves every
entry) and may hold only keys that exist in `default.yaml`. `S["_sources"]` lists `learned:repo` / `learned:personal`
when they applied. See [LEARNING.md](LEARNING.md).

After the merge, `platform.target` fills `platform.safe_zone`, `sound.master_lufs` and `sound.true_peak` from `styles/platforms.yaml` unless a layer set them. Platform boxes are fractions of the frame: compute pixels from the real frame size (`platforms.safe_zone(S, w, h)`), never from a fixed canvas.

Every key the engine reads must exist in `default.yaml`, with a neutral value and a comment. The schema is documented in [STYLE.md](STYLE.md).

**Not style (engine invariants):**
- edits snap to segment boundaries;
- a single lossless source path;
- face-smoothed punch-ins;
- the QC gates themselves. Their *thresholds* do come from the style.

## 2. Timebase and canvas

- **Canvas.** The canvas is configurable: `edit.yaml project.size` > style `canvas.size` > `platform.size` (legacy) > 1080×1920
  (`gfx.canvas_of(S, pr)`). `gfx.set_canvas(w, h)` sets `G.W`, `G.H` and the layout unit `G.U = min(w, h) / 1080` for the
  process. **Every module reads `G.W` / `G.H` / `G.U` at call time** (`from . import gfx as G`); never `from .gfx import W, H`
  and never a literal 1080 / 1920 / 540 / 960 (lint L4). Px constants designed for a 1080 short side scale by `G.U`.
  Multiprocessing uses `spawn`: workers re-import modules with the default canvas, so a pool initializer (or the job args)
  must re-set it (`render._init` does, through `Timeline`). Safe zones: `gfx.safe_zone(S)` / `gfx.safe(S)` (per aspect).
  Templates: see §4 and [FORMATS.md](FORMATS.md) §3. Other aspect ratios can also be delivered as reframes of the master
  (any master to any target).
- **Spine.** `edit.yaml spine:` (`aroll` default, `voiceover`, `music`, `broll`) decides what drives the timeline
  (`spines.spine_of`). On non-aroll spines `Timeline.segs` are the `broll:` shots (+ `gap` pieces), `edl.json` carries
  `spine`, rate, canvas and `duration` with `segments: []`, there are no plates / mattes / faces, and `timeline.json`
  records `spine`, segment `kind` (`aroll` | `broll` | `gap`) and `broll: true` on shot cutaways.
- **Frame rate.** Never write `24000/1001` or `23.976`. The rate is the source's, as probed by ingest:
  - `edl.json` stores `fps` (float) and `fps_rational` ([num, den]);
  - `Timeline.fps_rational`;
  - `timeline.json`'s `fps_rational` and `size`.

  Encoders and exporters read those values.
- **Template times.** Template times are cut-time seconds. Quantise any animation start to a whole frame with `round(t * fps) / fps`.

## 3. Project files (`PROJECT/Edit/`)

| file | written by | content |
|---|---|---|
| `selects.yaml` | Claude / human | source clips (`src` per clip for multi-source), in/out, `beat:` tag |
| `edl.json` | ingest | fps, fps_rational, size, clips, segments (f0, n, in, out, src); non-aroll spines: `spine`, `duration`, `segments: []` (voiceover: `vo_kept`) |
| `ingest.json` | ingest | per source: probe (w, h, fps, rotation, hdr, sar), conform applied, plate_scale; top level: canvas, fps_rational, plate_scale (max), language_detected. See [INGEST.md](INGEST.md) |
| `voice_chain.json` | ingest | `{"steps": [{"name", "generative": bool, "params"}]}` (SND-30 reads it) |
| `words.json` | ingest | `[[t0, t1, word]]` in cut time; language from `edit.yaml project.language` > `captions.language` (`auto` = detect) |
| `style.yaml` | `cves inspire` | measured style profile + `_evidence` |
| `inspire/` | `cves inspire` | `REPORT.md` (see / hear / feel per reference + the per-dimension mix), `<ref>-sheet.jpg` contact sheets, `aesthetic-review.md` (Claude fills it), `cache/` (per-reference measurements) |
| `edit.yaml` | Claude / human | the edit (cutaways, roto, chest, end_card, captions, music, sfx, assets, variants) |
| `assets.json` | `cves assets` | registry: id → path, kind, source (file/magnific/elevenlabs/stock/url), prompt, licence, sha256 |
| `stems/guide.wav` | mix | only with `music.slot: platform`: the guide the edit is cut to (reference track or click track), never mixed into the master ([VIRAL.md](VIRAL.md) §4) |
| `beats.json` | `cves beats` | music analysis in track seconds: tempo, beats, downbeats, bars, sections, energy, drop candidates, last sync plan ([MUSIC.md](MUSIC.md)) |
| `timeline.json` | render | resolved timeline (spine, zoom, cutaways incl. `broll` shots, transitions, fps_rational, size, segments with `kind`) |
| `IMPORT-REPORT.md` | `cves import-edits` | editor changes mapped onto edit.yaml / selects.yaml (backups `*.bak-<time>`), and what could not be mapped. `Export/control/layers.json` (schema in CONTROL-MODE.md §3) is the reference it compares against |
| `elements.jsonl` | render | one record per drawn element per frame (id, role, bbox, text, t_key, asset, font) |
| `QC-REPORT.txt` / `qc.json` | `cves qc` | gate results; `qc.json` is machine-readable and carries the hash of the file it judged |
| `journal.jsonl` | `cves` (build, encode, qc, deliver, import-edits, critique) + `cves learn` | append-only events `{t, event, cves, style_hash, ...}` for self-learning ([LEARNING.md](LEARNING.md)); `journal.last_edit.yaml` is the edit.yaml of the last build |
| `DIRECTION.md` | Claude | creative direction: concept, arc, the one signature moment, motif, what we will not do (knowledge-base/CREATIVE.md) |
| `critique/` | `cves critique` | `contact_sheet.jpg`, `timeline.png`, `critique.json`, `CRITIQUE.md` (rubric Claude fills) |

Client folders live outside the repo. Their root is `$CVES_CLIENTS`, else the `clients_root` config key, else `~/CVES Projects`.

## 4. Templates

A template is a `T = {name: (render, cues)}` dict inside any module:
- in `engine/cves/templates/`;
- in `$CVES_TEMPLATES`;
- in `~/.cves/templates/`;
- in `PROJECT/Brand/templates/`.

Templates are auto-discovered.

- **Layout on any canvas.** Lay out from `G.W` / `G.H` / `G.safe()` and treat px values as px at a 1080 short side. The
  registry wraps every template (`templates.get`): relative templates (default) draw in a same-aspect canvas with a 1080
  short side and are scaled by `G.U`; `NATIVE = True|{names}` modules draw on the canvas and scale px themselves;
  `DESIGN = True` modules (hard-coded 1080×1920) are fitted per instance into the safe zone. Identity at 1080×1920.
- `render(t, params, ctx) -> list[El]`. `ctx` has `start`, `end`, `resolve` (asset id or path resolver: `edit.yaml assets:` / `Edit/assets.json` first, then project- and repo-relative paths), `fps` (quantise animation starts: `round(t * fps) / fps`) and `S` (the style profile). On A-roll it also has `chin`, the smoothed chin y on the canvas. Templates listed in `render.NEEDS_AROLL` (kind `media`, or a module-level `NEEDS_AROLL = {names}` / `True`) also get `aroll = (graded RGB float HxWx3, matte float HxW)`: the A-roll frame under the cutaway, framed as the A-roll shot; no other template pays for it.
- `cves render --only` / `Timeline.frames_for(spec)` accept cutaway, segment, `roto.N`, `chest.N`, `end_card` ids, `12.5-14.0` (seconds), `300-420` (frames, inclusive) and comma lists.
- `cues(params, ctx) -> list[(t, sfx_name, gain_db, kw)]`.
- **Kind.** Set it per module with `KIND = "cutaway"|"roto"|"chest"|"end"|"media"|"overlay"`, or per template with `KINDS = {name: kind}`.
- **El(im, id, role, text=, t_key=, asset=, font=).** The `id` must be stable across frames; the QC gates track elements by `id`.
- **Fonts and colours.** Templates read colours and fonts through `gfx` (`G.MINT` is the accent slot, `G.font(...)`). They never use literal hex values.
- **Timing and cue helpers (gfx).** Use these instead of hand-rolled maths:
  - `G.enter(t, at, dur, G.fps_of(ctx))`: an entry first visible on the frame of `at`;
  - `G.q(at, fps)`: the frame-quantised time (log it as `t_key`);
  - `G.cues_out(cues, ctx)`: clamps cues to `ctx["start"]`, quantises them to frames, varies identical back-to-back cues and pitches template swipes / whooshes off the transition sounds.

  `G.fps_of(ctx)` falls back to `G.FPS` when `ctx` has no `fps`. Chest templates anchor to the optional `ctx["chin_hold"]` (a segment-stable chin) before `ctx["chin"]`.
- **Params (optional).** `cves validate` infers a template's params from its source (`p["x"]` = required, `p.get("x", 200)` = optional number). A module can be exact with `PARAMS = {name: {"price": "number!", "logo": "path"}}` (types: number int str bool list dict time path color asset any; `!` = required).

## 5. CLI

`engine/cves/cli.py` uses argparse with sub-commands. To add a command:
- add a parser **and** a dispatch branch;
- keep the work in its own module;
- return a non-zero exit with a one-line, actionable message on user error (`raise SystemExit("...")`); never show a traceback for user error.
- `cves render` and `cves build` call `schema.require_valid(pr)` first: `schema.validate(pr) -> (errors, warnings)`, each message `yaml.path: problem` (e.g. `cutaways[3].params.price: expected number`).

## 6. QC and delivery

- `cves qc` writes `Edit/qc.json`: `{video, sha256, size, fail, warn, pass, na, gates: [{id, status, summary}], created, cves_version, fast}` (`qc.write_stamp`).
  Status `N/A` = the gate cannot apply to this spine (presenter / voice / caption gates; `qc.NA_NO_AROLL`, `NA_NO_VOICE`,
  `NA_NO_CAPTIONS`); it never blocks delivery.
- `cves deliver` refuses unless `qc.json` exists, has `fail == 0`, and its `sha256` matches the master being delivered.
- `cves deliver` writes a never-overwritten `Export/vNNN/` with `manifest.json` (`qc_verified`, `master_sha256`, files with sha256, variants with status); `--force-unchecked` is recorded as `forced_unchecked` + `WARNING`.
- Encoder settings come from the style `delivery:` section through `encode.video_args(S)` / `audio_args(S)`; fps and size from `encode.stream_params(pr)`.
- The plugin hook (`plugin/hooks/qc_guard.py`, PreToolUse) denies copying / moving / uploading out of `Export/` unless the QC stamp (or the `vNNN` manifest) is clean, and denies `--force-unchecked` while QC is not clean. Details: [DELIVERY.md](DELIVERY.md).

## 7. Portability

- Use `encoding="utf-8"` on every text `open`.
- Use `tempfile`, never `/tmp`.
- Use `os.path` / `pathlib`, never `/` string joins for real paths.
- Binaries come from `config.get(...)`.
- `tools/lint.py` enforces these rules in CI.
