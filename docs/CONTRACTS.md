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
2. the preset named by `edit.yaml style.preset`;
3. `PROJECT/Edit/style.yaml`, written by `cves inspire`;
4. `PROJECT/Brand/style.yaml`;
5. inline keys under `edit.yaml style:`.

Every key the engine reads must exist in `default.yaml`, with a neutral value and a comment. The schema is documented in [STYLE.md](STYLE.md).

**Not style (engine invariants):**
- edits snap to segment boundaries;
- a single lossless source path;
- face-smoothed punch-ins;
- the QC gates themselves. Their *thresholds* do come from the style.

## 2. Timebase and canvas

- **Canvas.** Templates draw in a 1080×1920 design space (`gfx.W`, `gfx.H`). The delivery size is `S["platform"]["size"]`. Other aspect ratios come from `cves deliver` reframes.
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
| `edl.json` | ingest | fps, fps_rational, size, clips, segments (f0, n, in, out, src) |
| `ingest.json` | ingest | per source: probe (w, h, fps, rotation, hdr, sar), conform applied, plate_scale; top level: canvas, fps_rational, plate_scale (max), language_detected. See [INGEST.md](INGEST.md) |
| `voice_chain.json` | ingest | `{"steps": [{"name", "generative": bool, "params"}]}` (SND-30 reads it) |
| `words.json` | ingest | `[[t0, t1, word]]` in cut time; language from `edit.yaml project.language` > `captions.language` (`auto` = detect) |
| `style.yaml` | `cves inspire` | measured style profile + `_evidence` |
| `edit.yaml` | Claude / human | the edit (cutaways, roto, chest, end_card, captions, music, sfx, assets, variants) |
| `assets.json` | `cves assets` | registry: id → path, kind, source (file/magnific/elevenlabs/stock/url), prompt, licence, sha256 |
| `beats.json` | `cves beats` | music analysis in track seconds: tempo, beats, downbeats, bars, sections, energy, drop candidates, last sync plan ([MUSIC.md](MUSIC.md)) |
| `timeline.json` | render | resolved timeline (zoom, cutaways, transitions, fps_rational, size) |
| `IMPORT-REPORT.md` | `cves import-edits` | editor changes mapped onto edit.yaml / selects.yaml (backups `*.bak-<time>`), and what could not be mapped. `Export/control/layers.json` (schema in CONTROL-MODE.md §3) is the reference it compares against |
| `elements.jsonl` | render | one record per drawn element per frame (id, role, bbox, text, t_key, asset, font) |
| `QC-REPORT.txt` / `qc.json` | `cves qc` | gate results; `qc.json` is machine-readable and carries the hash of the file it judged |

Client folders live outside the repo. Their root is `$CVES_CLIENTS`, else the `clients_root` config key, else `~/CVES Projects`.

## 4. Templates

A template is a `T = {name: (render, cues)}` dict inside any module:
- in `engine/cves/templates/`;
- in `$CVES_TEMPLATES`;
- in `~/.cves/templates/`;
- in `PROJECT/Brand/templates/`.

Templates are auto-discovered.

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

- `cves qc` writes `Edit/qc.json`: `{video, sha256, size, fail, warn, pass, gates: [{id, status, summary}], created, cves_version, fast}` (`qc.write_stamp`).
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
