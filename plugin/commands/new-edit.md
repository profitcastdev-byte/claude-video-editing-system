---
description: Start a new CVES edit. Creates the client project, collects the raw take, inspirations and brand, and builds STYLE for a new client
argument-hint: '"<Client>" "<Video name>" [raw file]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:new-edit: step 1, setup (and step 2, ingest)
Arguments: `$ARGUMENTS`. Skill §0-§1 first; read `skills/video-editor/reference/formats.md` (canvas, spine), and `reference/viral.md` for an organic post.

## Ask first (one message, only what's missing)
**Client**, **video name** (from the arguments if given), **raw file(s)** as shot; **inspirations** (1-3 reference edits = the style spec; existing client: reuse `<projects root>/<Client>/STYLE.md` + profile, ask only whether this video differs); **brand** (logo png/svg, colours, approved claims = client name + a number for the proof, wordmark); **mode** (vibe default, or control); **goal** (paid **ad** default, or organic **viral** + the viral brief questions, `knowledge-base/modules/viral-playbook.md`); **format and spine** (where it runs → `canvas.size`; `aroll` default / `voiceover` / `music` / `broll`; `docs/FORMATS.md`).
Blocking: no raw file (aroll), VO (voiceover) or music / footage (music, broll). Missing inspirations, brand or proof: carry as a flag.

## Run
1. `cves new "<Client>" "<Video>" --raw "<raw file>"` → the project with `Raw/ Inspirations/ Brand/ Music/ Edit/ Moodboard/ Export/` (ARCHITECTURE §2). Copy the user's files into `Inspirations/`, `Brand/`; claims into `Brand/claims.md`.
2. `ffprobe` colour tags, resolution, fps (RULEBOOK §1) → `Edit/NOTES.md`.
3. `edit.yaml`: `style: {canvas: {size: [w, h]}}`, `spine:`, `voiceover: {asset | file}`, `music.file` + `duration`; then `cves ingest` (local): aroll → raw transcript; voiceover → voice_raw / voice_final.wav (pauses tightened), words.json, edl.json; music / broll → edl.json. On failure fix the cause or report it; never hand-roll a replacement.

## You decide
- **Brief** → `Edit/NOTES.md`: emotion in one line; viewer's want + obstacle; proof (client name + number) or "MISSING: ask the client"; sound moments (hook hit, first cutaway, offer, CTA).
- **STYLE (new client only):** `cves inspire` (`/cves:inspire`) → `PROJECT/Edit/style.yaml`; brand tokens (logo colours, fonts) → `PROJECT/Brand/style.yaml`. Study inspirations as text first (transcripts, `ffprobe`), then **one** contact sheet. Write palette, type, card style, transitions, caption style, music feel, pacing in `STYLE.md`; check each is in the profile (docs/STYLE.md). A `style.preset` only if one genuinely matches (no house look); never your pick over the inspirations (RULEBOOK §0.1).
- **Goal / platform:** `goal: viral` for organic posts; `style: {platform: {target: <platform>}}`; viral brief also records hook type, structure, loop, trending sound (`music: {slot: platform, guide: ..., sound: ...}`; never for ads).
- Tick `CHECKLISTS.md` §1.

**Show:** project path, brief, STYLE summary (new client), flags. No approval: continue to `/cves:story` unless something blocking is missing.
