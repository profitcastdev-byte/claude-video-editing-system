---
description: Fill edit.yaml from templates for the cut (cutaways, roto, chest, end card, zoom, captions, music, SFX)
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:plan: the edit plan
Project: `$ARGUMENTS`. Read `skills/video-editor/reference/` `formats.md` (`broll:`), `motion.md`, `sound.md` as relevant.

## Run
- **voiceover / music / broll spine:** no `cves prep`, no `aroll` / `roto` / `chest` keys. Write `broll:` (`cves autocut [--every beats|downbeats|bars] --apply` proposes one on the music grid), cutaways on top, captions (voiceover only), music, SFX, then steps 2-3.
1. **`cves prep`** (aroll, local, minutes): `Edit/words.json` (keyword times come from it), plate, matte, face landmarks.
2. **`cves plan`**: the first run writes a skeleton `Edit/edit.yaml` (`docs/ARCHITECTURE.md` §4); every run validates it (template names, segment ids).
3. **`cves templates`** (`--kinds` one line; `<name>` one template's params + docs; `--json`), `docs/TEMPLATES.md`. Fill only what the user asked for: templates and params, no code. Then `cves plan` (or `cves validate`) until it reports OK.

Slots: `broll` `{src | asset, start, end, in, framing: fill | fit | kenburns, speed, audio}`; `cutaways` `{id, template, start, end, in, out, snap, params}` (snapped to segment boundaries unless `snap: false`); `aroll.zoom` per segment, `aroll.snap` for a punch-in; `roto` (one per segment), `chest`, `end_card`; `captions` (`auto`, `hide`, `fixes`); `music` / `sfx` (`/cves:music`).

**Show:** a short beat → visual map (time, template, what it shows) and the music.
