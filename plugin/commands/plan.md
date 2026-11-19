---
description: Step 4. Fill edit.yaml from templates for the approved cut (cutaways, roto, chest, end card, zoom, captions, music, SFX)
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:plan: step 4, the edit plan
Project: `$ARGUMENTS`. Needs approval 1 in `Edit/NOTES.md`, else `/cves:story`. RULEBOOK §3, §5, §6, §7; read `skills/video-editor/reference/` `formats.md` (`broll:`), `motion.md`, `sound.md`, `viral.md` as relevant.

## Run
- **voiceover / music / broll spine:** no `cves prep`, no `aroll` / `roto` / `chest` keys. Write `broll:` (`cves autocut [--every beats|downbeats|bars] --apply` proposes one on the music grid), cutaways on top, captions (voiceover only), music, SFX, then steps 2-4.
1. **`cves prep`** (aroll, local, minutes): `Edit/words.json` (all keyword times come from it), plate, roto matte, face landmarks.
2. **`cves plan`**: first run writes a skeleton `Edit/edit.yaml` (`docs/ARCHITECTURE.md` §4); validates every run.
3. **`cves templates`** (`--kinds` one-line summary; `<name>` one template's params + docs; `--json`). `docs/TEMPLATES.md`; example: demo project in `examples/`.
4. `cves plan`, then **`cves qc --stage plan`** (CUT-05 punch-in steps, FRAME-09, roto budget, cutaway share + length, early keys).

## You decide: template choices and params only, no code (skill §3)
- `broll`: `{src | asset, start, end, in, framing: fill | fit | kenburns, speed, audio}`; on aroll it counts as cutaways.
- `cutaways`: one per idea on its keyword, own line; 3-8 s; 40-55 % of runtime; never > 8 s without the face.
- `aroll.zoom`: alternate ≥ 1.15× across every uncovered direct cut (at the cut frame, creep included); one `snap` extreme punch-in on the key line.
- `roto` ≤ 4 moments, ≤ 3 s each; `chest`: wordmark or price card; `end_card`.
- `captions`: auto, `hide` under full-screen cutaways, `fixes` for mis-heard words.
- `music` / `sfx`: drop sync; `bed_lu` only to override style `sound.bed_lu`; templates emit their SFX, `extra` only for ≤ 2 hero hits (`/cves:music`).
- Items land 0 to +6 f after their keyword. Tick `CHECKLISTS.md` §3.

**Show:** 5-10 lines, no images: beat → visual map (time, template, what it shows), cutaway %, roto count, music. No approval: fix pre-render FAILs, then `/cves:moodboard`.
