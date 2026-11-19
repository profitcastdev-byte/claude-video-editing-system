# Architecture

Claude Video Editing System (CVES): an autonomous, Claude-driven editor for talking-head videos and ads.
**Claude makes the decisions; local code does the work; humans tweak in a real editor.**

The engine has no house look. Every visual, pacing and sound choice comes from a **style profile** (§9), normally measured
from the client's own reference edits. The **canvas** is configurable (style `canvas.size`: 9:16, 4:5, 1:1, 16:9, 2.39:1 or any
even size) and edits are designed and rendered natively at it; other aspect ratios can still be delivered as reframes of the
master (`cves deliver --variants`). What drives the timeline is the **spine**: `aroll` (a presenter), `voiceover`, `music` or
`broll` ([FORMATS.md](FORMATS.md), `docs/CONTRACTS.md` §2).

## 1. Repo layout
```
claude-video-editing-system/
  INSTALL.md              one-shot install (Claude Code can follow it end to end)
  TOOLS-REGISTRY.md       living list of plugins, skills, repos, connectors (Magnific, ElevenLabs, Openverse, Resolve/Kdenlive MCP)
  CHANGELOG.md, CONTRIBUTING.md, CLAUDE.md
  engine/cves/            Python package (CLI: `cves ...`)
    cli.py                entry point
    project.py            project folder layout, edit.yaml load/save/validate
    ingest.py             transcribe, pause-tighten, plate extract, matte, faces, voice chain
    gfx.py                drawing kit (2x supersampled, Material icons, fonts) + ELEMENT LOG; the canvas (set_canvas, safe_zone)
    motion/               HTML motion layer: Chromium (Playwright) renderer + frame cache, runtime.js, base.css, pieces/<name>/ (docs/MOTION.md)
    spines.py             timeline spines (aroll | voiceover | music | broll), the broll: track, VO ingest, `cves autocut`
    style.py              loads and merges the style profile (§9); every module reads looks through it
    styles/               default.yaml (neutral defaults, the full schema) + optional named presets
    look.py               A-roll grade (optional edge-accurate relight) + per-shot skin exposure balance, from `grade:`
    captions.py           caption phrasing + rendering, from `captions:`
    assets.py             `cves assets`: media registry + provenance (Edit/assets.json)
    layered.py            control mode: renders the edit as separate layers + layers.json
    templates/            cutaway / roto / chest / end-card templates (one file each, registry in __init__)
    render.py             edit.yaml -> frames (vibe mode) and -> layered clips (control mode)
    rcache.py             the frame cache: per-frame input keys, so a build re-renders only the frames that changed (§6b)
    build.py              `cves build` (render + mix + encode + qc) and `--draft` (Edit/draft/ Variant, half size, never deliverable)
    moodboard.py          the edit plan: timeline + shot-by-shot build frames (same renderer) -> EDIT-PLAN.html/.md + moodboard.jpg
    mix.py                voice + music (drop-synced, frequency-split ducking) + SFX -> master + stems
    music.py              Openverse search/download with licence + credits; ElevenLabs / Magnific notes
    beats.py              `cves beats`: music tempo, beats, downbeats, drops -> Edit/beats.json; beat-sync report
    scripts.py            which bundled font draws a language's script (map in style `font_files`)
    encode.py             single x264 encode with bt709 tags
    learn.py              `cves learn`: project journal (Edit/journal.jsonl) -> mined candidate patterns -> human-approved promotion
                          into the learned style layers; taste study of great videos (docs/LEARNING.md)
    critique.py           `cves critique`: contact sheet + energy timeline + CRITIQUE.md rubric (senior-editor review)
    review.py             `cves review`: watches the render: cut strips, hook, payoff, end card, audio -> findings.json + REVIEW.md; safe patches; sign-off (docs/REVIEW.md)
    treatments.py         `cves treatments`: 2-3 creative treatments of one plan, half-size proxies, comparison sheet, pick (docs/TREATMENTS.md)
    deliver.py, variants.py  `cves deliver`: QC-stamped Export/vNNN/ (master, captions, cover, qc.json, style snapshot) + variants (reframes, cut-downs) that pass their own QC
    qc/                   `cves qc` gates (+ `--stage story|plan`) -> Edit/QC-REPORT.txt
    export/               resolve.py (FCPXML + media + bridge), kdenlive.py (.kdenlive via OTIO), layers.py (shared)
  plugin/                 Claude Code plugin: commands/*.md + skills/video-editor/SKILL.md
  knowledge-base/         RULEBOOK, CREATIVE (senior-editor method), CHECKLISTS, QA-REVIEW, QC-GATES, DECISIONS, TASTE + taste/learned.yaml (shared learned taste), modules/, transcripts/, tools/
  assets/                 fonts (OFL), icons (Material, Apache-2.0), sfx (CC0), logos/
  setup/                  install_mac.sh, install_windows.ps1, requirements*.txt, doctor.py
  examples/               a demo project (edit.yaml, edl.json, notes; no client footage)
```

## 2. Client project layout (outside the repo; one folder per video)
```
~/CVES Projects/<Client>/<YYYY-MM-DD Video Name>/      root: $CVES_CLIENTS, else config `clients_root`, else ~/CVES Projects
  Raw/            the take(s) as shot
  Inspirations/   reference edits for this client (the style spec; `cves inspire` measures them)
  Brand/          logo.png/svg, colours, approved claims (claims.md), wordmarks, optional style.yaml (brand tokens)
  Music/          licensed tracks + CREDITS.md
  Edit/           edit.yaml, style.yaml (from `cves inspire`), edl.json, words.json, faces.json, voice_*.wav, plate/, matte/, frames/, QC-REPORT.txt, qc.json
  Moodboard/      EDIT-PLAN.html, EDIT-PLAN.md, moodboard.jpg, frames/
  Export/         final MP4 + control/ (Resolve / Kdenlive projects, layered media, stems, SRT)
```
`cves new "<Client>" "<Video>" --raw <file>` creates it (`--root` picks another projects folder). The full list of `Edit/` files is in `docs/CONTRACTS.md` §3.

## 3. The workflow (both modes share steps 1-7)
| Step | Command | Who | Output |
|---|---|---|---|
| 1 Setup | `cves new`, then `cves inspire` | Claude + local | project folders; the client's style profile (`Edit/style.yaml`, measured from `Inspirations/`) and `STYLE.md` notes (first video per client) |
| 2 Ingest | `cves ingest` | local | `raw_audio.wav`, `raw_words.json`, `raw_transcript.txt` |
| 3 Story | `cves story` → Claude writes `selects.yaml` → `cves select` → `cves qc --stage story` | Claude (text) + local | `edl.json`, `voice_final.wav` (clean, pauses ≤ 0.25 s); **user approves the cut list** |
| 4a Direction | Claude writes `Edit/DIRECTION.md` | Claude (text) | concept, emotional arc, the one signature moment, motif, what we will not do (knowledge-base/CREATIVE.md); shown with the cut list or the edit plan, not a third approval |
| 4 Plan | `cves prep` → `cves plan` → Claude fills `edit.yaml` → `cves qc --stage plan` | local + Claude (text) | `words.json`, plate/, matte/, `faces.json` (box + landmarks), `edit.yaml` |
| 5 Edit plan | `cves moodboard` | local + Claude reads EDIT-PLAN.md, reviews 1 image | `Moodboard/EDIT-PLAN.html`: multi-track timeline + every shot with rendered build frames, words, sound; **user approves** |
| 5b Treatments (open brief) | `cves treatments make / render / compare / pick` | local + Claude picks 2-3 treatments, reviews 1 sheet | `Edit/treatments/compare/sheet.jpg` + `compare.mp4`; **user picks one** (docs/TREATMENTS.md) |
| 6 Render + mix | `cves build` (or `cves render && cves mix && cves encode`; `cves beats` for beat sync); `cves build --draft` for a fast half-size look (§6b) | local | final MP4 + stems + `elements.jsonl` (incremental: only changed frames re-render, §6b) |
| 7 QC | `cves qc` | local; Claude fixes edit.yaml until it passes | `QC-REPORT.txt` + `qc.json`; thresholds for per-client choices come from the style profile |
| 7b Critique | `cves critique` | local + Claude scores the rubric, fixes anything < 7, logs it (`cves learn rate --by claude`) | `Edit/critique/` contact sheet, energy timeline, `CRITIQUE.md` (knowledge-base/CREATIVE.md) |
| 7c Review loop | `cves review build` → `cves review apply` → re-render → again; `cves review signoff` | local measures; Claude looks at the pack, answers the rubric, fixes; max `review.max_rounds` (3) rounds | `Edit/review/rNNN/` cut strips, hook / payoff / end card strips, `audio.json`, `findings.json`, `REVIEW.md` ([REVIEW.md](REVIEW.md)) |
| 8a Vibe delivery | `cves deliver [--variants 4:5,1:1,cut15]` | local + Claude | a new `Export/vNNN/` (master, SRT/WebVTT, cover, qc.json, style snapshot, variants that passed QC; `docs/DELIVERY.md`); refused unless `qc.json` has 0 FAIL for that exact master; user gives notes in words |
| 8b Control delivery | `cves export resolve` / `cves export kdenlive` | local + Claude via MCP | layered project; Claude drives the editor live (Resolve) or by project file (Kdenlive); user edits by hand |

## 4. edit.yaml (the single source of truth for a video)
```yaml
goal: ad                                     # ad (default) | viral: goal layer, retention QC profile, music slot rules (docs/VIRAL.md)
project: {client: "Client", title: "Video Title", raw: "Raw/take.MP4"}   # fps and size come from the source / style profile (canvas.size)
spine: aroll                                 # aroll (default) | voiceover | music | broll: what drives the timeline (FORMATS.md)
style: {preset: null, captions: {position: lower_third}}   # optional preset + inline per-video overrides (§9)
edl: edl.json                                # segments (raw in/out, frame-snapped) from `cves story`
aroll:
  zoom: {"01_hook_0": 1.0, "05_every_day_0": 1.18}   # every direct cut changes scale by >= style framing.min_step (CUT-05)
  creep: 0.015                                       # slow push per segment (default from style framing.creep)
  snap: {start: 31.13, end: 31.80, zoom: 1.55}       # the one extreme punch-in (FRAME-09)
  exposure_match: true                               # per-shot skin balance (COL-06/07)
captions: {auto: true, hide: [[21.23, 24.57]], fixes: {"web site": "website"}}   # built from words.json; look from style captions:
cutaways:
  - {id: c1, template: search_rows, start: 1.63, end: 7.55,          # in/out omitted = style transitions.in/out
     params: {label: TYPE, pills: ["WHAT YOU SELL", "NEAR ME"], rows: [{q: "best dentist", type: [3.46, 3.95], tag: 3.99, check: 4.28}]}}
roto:   [{segment: "05_every_day_0", template: big_words, params: {words: [["EVERY", 9.98], ["SINGLE", 10.25], ["DAY", 10.58, accent]]}}]   # 3rd item = draw in the accent colour
chest:  [{segment: "08a", template: wordmark, params: {lines: ["Client", "Name"], sub: "TAGLINE", at: 21.80}}]
end_card: {template: logo_end, duration: 1.25, params: {label: "SERVICE NAME", pill: "OFFER"}}
music: {file: "Music/track.wav", drop_track: 38.70, drop_cut: 31.13, credits: "..."}   # bed_lu omitted = style sound.bed_lu
# organic post on a trending sound: music: {slot: platform, guide: 128, sound: "..."}  -> no music in the master (docs/VIRAL.md §4)
sfx: {auto: true, extra: [{t: 31.12, name: boom, gain: -16}]}   # templates emit their own cues
qc: {topic_keywords: [topic, words], brand_tail: [brand, name], duration: [30, 60]}   # duration omitted = style platform.duration
broll:                                       # footage on the timeline (FORMATS.md §5): cutaways over A-roll, or the picture of a
  - {src: Raw/street.mp4, start: 12.4, end: 14.1, in: 3.0, framing: fill}            # voiceover / music / broll edit
  - {asset: hero_img, start: 14.1, end: 15.6, kenburns: {zoom: [1.0, 1.1]}}
# voiceover spine: voiceover: {asset: vo} (an ElevenLabs VO registered with `cves assets add`, or {file: Raw/vo.wav})
# music / broll spines: duration: 20 (else the music track / the end of the broll track); `cves autocut` proposes broll: on the beat
```
Every time is cut time in seconds; the engine snaps edits to frame/segment boundaries. Any look value left out of `edit.yaml`
(transition kinds, accent colour, bed level, caption position, cutaway share band) comes from the style profile.

## 5. Templates
`templates/<name>.py` exposes `render(t, params, ctx) -> list[Layer]` and `cues(params) -> list[SfxCue]`.
`Layer` = PIL RGBA + element records. Every drawn element is logged by `gfx` (see 6). Template kinds:
- cutaway (full screen): `search_rows`, `card_list` (check/cross), `counter`, `browser_list`, `checklist`
- roto (behind the head): `card_behind` (map), `big_words`, `listing_card`, `top3_card`
- chest (replace captions): `wordmark`, `price_card`, `logo_lockup`
- end: `logo_end`
- motion (`m_*`, `templates/motion.py`): HTML/CSS pieces from `engine/cves/motion/pieces/`, `~/.cves/motion/` and `PROJECT/Brand/motion/`, rendered once by headless Chromium (`cves.motion`, pre-rendered by `render.render()` before the worker pool) and read back as cached RGBA frames; cutaway, overlay (chest), `_roto` and `_end` uses. See `docs/MOTION.md`.

New template = new file + registry entry + a moodboard sample in `docs/TEMPLATES.md`. Templates lay out relative to the canvas
(`G.W`, `G.H`, `G.safe()`, px scaled by `G.U` and rasterised at the real canvas; the UI cutaways and roto cards pick a
tall / square / wide arrangement) and read every
colour and font through `gfx` from the style profile, never as literal values (`docs/CONTRACTS.md` §4, FORMATS.md §3).

## 6. Element log (unlocks the remaining QC gates)
`render.py` writes `Edit/elements.jsonl`: one line per element per frame:
`{"f": 123, "id": "c1.row2.tag", "role": "caption|cutaway|roto|chest|end|icon", "bbox": [x0,y0,x1,y1], "alpha": 0.8, "scale": 1.02, "font": "Poppins-Bold", "size": 34, "fill": "#4C8DFF", "text": "near me", "asset": "assets/icons/search.svg", "keyword_t": 3.99}`
QC gates for motion (MOT-*), graphics (GFX-*), captions (PLAT-*), safe zones and spoken-before-shown read it.

## 6b. Incremental render and draft builds
A final render keeps a **frame cache** (`engine/cves/rcache.py`): every frame is keyed by a hash of what decides its
pixels and element records (the engine code, the visual style, the canvas, the frame's segment and its plate / matte /
faces / framing / colour match, the cutaway covering it, its transition state, its caption events, the roto and end-card
entries, the media files). `cves build` / `cves render` re-render only the frames whose key changed and rebuild
`Edit/elements.jsonl` from the records of the untouched frames, so the frames, the element log and the encoded master are
identical to a full render's (tests/test_render_cache.py). One cutaway tweak re-renders that cutaway's frames; a sound or
delivery tweak re-renders nothing. `--no-cache` / style `render.cache: false` render everything.

`cves build --draft` is the fast look while iterating: a `project.Variant` in `Edit/draft/` (own frames, cache, element
log, mix and QC stamp), rendered at `render.draft_scale` (0.5) through the proxy path, encoded with the proxy settings,
tagged `comment=cves-draft` and QC'd with the fast gate set. It never touches the final build, and `cves deliver`
refuses a draft even with `--force-unchecked`.

## 7. Control mode export contract (`Export/control/`)
```
media/aroll/<seg>.mov        graded A-roll per segment (B-roll shot on a non-aroll spine), ProRes 422 HQ, zoom baked, canvas size
media/cutaways/<id>.mov      full-frame cutaway incl. its in/out transition, ProRes 422 HQ
media/overlays/<id>.mov      chest/roto foreground elements with alpha, ProRes 4444 (roto shots: plate+behind+person baked as A-roll)
media/audio/voice.wav  music.wav  sfx.wav   48 kHz stems (mix levels as rendered)
captions.srt                 caption events (editable as text in Resolve subtitles / Kdenlive subtitle track)
timeline.otio                master timeline (V1 A-roll, V2 cutaways, V3 overlays, A1 voice, A2 music, A3 sfx, subtitles)
timeline.fcpxml              for DaVinci Resolve import
project.kdenlive             for Kdenlive (via OTIO kdenlive adapter, or written directly)
CONTROL.md                   what is where, what Claude can change via MCP, what needs a re-render
```
Resolve is driven live through the in-app bridge of `hiteshK03/davinci-resolve-mcp` (Workspace > Scripts > CursorBridge, works on the FREE version).
Kdenlive is driven through `12bijaya/MCP_Server_Kdenlive` (edits the .kdenlive file; reload in the app).
Baked graphics (text inside a cutaway card) change via `edit.yaml` + `cves render --only c3` + relink.
The Kdenlive profile and layer sizes follow the project's canvas and source frame rate.

## 8. Platforms
macOS (Apple Silicon): RVM on MPS. Windows 10/11: RVM on CUDA if an NVIDIA GPU, else CPU; ffmpeg + whisper.cpp from release binaries.
Python 3.12 venv in `~/.cves/venv` (Mac) / `%USERPROFILE%\.cves\venv` (Windows); models in `~/.cves/models`.

## 9. Style profile (no look is hard-coded)
`engine/cves/style.py` merges these layers, later wins:

| # | Source | Written by | Typical content |
|---|---|---|---|
| 1 | `engine/cves/styles/default.yaml` | the repo | neutral defaults for every key the engine reads (the full schema) |
| 2 | `knowledge-base/taste/learned.yaml` | `cves learn promote --share` | team learned taste (scoped: global / goal / platform), shared through git |
| 3 | `~/.cves/taste/learned.yaml` | `cves learn promote` | personal learned taste (may be client-scoped); see `docs/LEARNING.md` |
| 4 | `engine/cves/styles/<preset>.yaml` | the repo | optional named preset, picked with `edit.yaml style: {preset: <name>}` |
| 5 | `PROJECT/Edit/style.yaml` | `cves inspire` | the look measured from the client's reference edits in `Inspirations/` (with `_evidence`) |
| 6 | `PROJECT/Brand/style.yaml` | the client / Claude | brand tokens: logo colours, fonts |
| 7 | `edit.yaml style:` keys | Claude / human | per-video overrides |

The learned layers apply only sections whose scope matches the project, and every entry in them was approved by a person
(`docs/LEARNING.md`).

Sections: `canvas` (size, safe zones per aspect), `platform` (fps, 9:16 safe zone, margin, duration), `broll`, `autocut`, `stage`, `colors`, `font_files`, `grade`, `captions`, `transitions`,
`framing`, `grammar` (cutaway share band, shot lengths, roto count, beat order), `sound` (bed level, ducking, master loudness),
`motion`. The schema is in `docs/STYLE.md`.

The defaults are deliberately plain: a neutral stage, a blue accent, no relight, plain cuts into cutaways, captions under the chin,
a -10 LU music bed, no cutaway-share band. A preset is just data. `profitcast-dark` is one example preset (a dark stage, green
accent, warm moody A-roll, whip in / glitch out, a 40–55% cutaway-share band, a -7 LU bed), measured from the reference edits of
the agency where CVES was first tested.

The QC gates are engine invariants, but their thresholds for per-client choices (cutaway share, bed level, transition kinds,
caption position) are read from the merged profile; a `grammar` key set to `null` means that rule is not enforced for the
client. `docs/CONTRACTS.md` §1 lists what is not style (frame-snapped edits, a single lossless source path, face-smoothed punch-ins).
