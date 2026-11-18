---
description: Start a new CVES edit. Creates the client project, collects the raw take, inspirations and brand, and builds STYLE for a new client
argument-hint: '"<Client>" "<Video name>" [raw file]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:new-edit: step 1, setup (and step 2, ingest)

Arguments: `$ARGUMENTS`

Follow the `video-editor` skill. Resolve `CVES_ROOT`, `cves` and the project (skill §0), then load the RULEBOOK and ES (skill §1).

## Ask first (one message, only for what's missing)
- **Client** and **video name** (from the arguments, if given).
- **Raw file(s)**: the path to the take as shot.
- **Inspirations**: 1-3 reference edits for this client. These are the style spec. For an existing client, reuse `<projects root>/<Client>/STYLE.md` and its style profile, and ask only whether this video should differ.
- **Brand**: logo (png/svg), colours, approved claims (a client name plus a number for the proof), wordmark.
- **Mode**: vibe (default) or control.
- **Format and spine** (skill §2a, `docs/FORMATS.md`): where it runs (sets `canvas.size`: 9:16 default, 4:5, 1:1, 16:9, 2.39:1) and what drives the cut: a presenter (`aroll`, default), a voiceover (`voiceover`: a recorded VO or an ElevenLabs VO the user asked for), the music (`music`) or the shots (`broll`).

Don't continue without a raw file (aroll), a VO (voiceover) or the music / footage (music, broll). Missing inspirations, brand or proof is not a blocker; carry it forward as a flag.

## Run
1. `cves new "<Client>" "<Video>" --raw "<raw file>"`. It creates `~/CVES Projects/<Client>/<YYYY-MM-DD Video>/` (root: `$CVES_CLIENTS`, else config `clients_root`) with `Raw/ Inspirations/ Brand/ Music/ Edit/ Moodboard/ Export/` (ARCHITECTURE §2). Copy the inspirations and brand files the user gave into `Inspirations/` and `Brand/`. Put claims in `Brand/claims.md`.
2. Probe the source: `ffprobe` colour tags, resolution and fps (RULEBOOK §1). Note them in `Edit/NOTES.md`.
3. Set the canvas and spine in `edit.yaml` (`style: {canvas: {size: [w, h]}}`, `spine:`; `voiceover: {asset | file}`; `music.file` + `duration`), then `cves ingest`. This step is local. On the aroll spine: the raw transcript (then the story step). On a voiceover spine: voice_raw / voice_final.wav (pauses tightened), words.json, edl.json. On music / broll: edl.json only. If it fails, read the error text, fix the cause or report it. Don't hand-roll a replacement.

## You decide
- **The brief**, written to `Edit/NOTES.md`: the ad's emotion in one line; the viewer's want plus obstacle; the proof (client name plus number), or "MISSING: ask the client"; the sound moments (hook hit, first cutaway, offer, CTA).
- **STYLE, for a new client only** (`<projects root>/<Client>/STYLE.md` plus the style profile). Run `cves inspire` to measure the inspirations into `PROJECT/Edit/style.yaml`, and put brand tokens (logo colours, fonts) in `PROJECT/Brand/style.yaml`. Study the inspirations as text first: their transcripts and the `ffprobe` facts. Then look at **one** contact sheet of their key frames, not frame by frame. Write the palette, type, card style, transitions, caption style, music feel and pacing in `STYLE.md`, and check each one is reflected in the style profile (docs/STYLE.md). Name a `style.preset` only if one genuinely matches; the default is neutral, and no preset is a house look. Never replace the inspirations' look with your own pick (RULEBOOK §0.1).
- Tick `CHECKLISTS.md` §1.

## Show the user
The project path, the brief, the STYLE summary (new client only), and a list of flags (missing proof, logo or claims).

## Stop?
No approval is needed here. Continue to `/cves:story` unless something blocking is missing.
