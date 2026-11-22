---
description: Start a new CVES edit. Creates the client project, copies the raw take, inspirations and brand files, and transcribes the take
argument-hint: '"<Client>" "<Video name>" [raw file]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:new-edit: create the project
Arguments: `$ARGUMENTS`. Skill §0 first; `skills/video-editor/reference/formats.md` for canvas and spine.

Needed: **client**, **video name**, the **raw file(s)** (aroll), the VO (voiceover) or the music / footage (music, broll). Missing one of these → ask, in one message. Inspirations, brand files, goal (`ad` default or `viral`), canvas and spine: use what the user gave; don't ask for what they didn't mention.

## Run
1. `cves new "<Client>" "<Video>" --raw "<raw file>"` → `Raw/ Inspirations/ Brand/ Music/ Edit/ Moodboard/ Export/`. Copy the user's files into `Inspirations/` and `Brand/` (claims into `Brand/claims.md`).
2. Set in `edit.yaml` only what the user specified: `style: {canvas: {size: [w, h]}}`, `spine:`, `goal:`, `voiceover: {asset | file}`, `music.file` + `duration`.
3. `cves ingest`: aroll → raw transcript; voiceover → voice_final.wav (pauses tightened), words.json, edl.json; music / broll → edl.json. On failure report the error line.
4. Inspirations given and the user wants their look → `/cves:inspire`.

**Show:** the project path and what was created; what is still missing for the job the user asked for.
