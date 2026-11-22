---
description: Find music for the edit (Openverse search with the licence recorded in CREDITS.md, or a hand-off to the ElevenLabs or Magnific connector) and sync it
argument-hint: "[mood / genre / bpm] or 'generate'"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:music: music
Request: `$ARGUMENTS`. `skills/video-editor/reference/sound.md` (beats, accents, ducking), `docs/MUSIC.md`.

- **A, Openverse (default):** `cves music search "<query>"` (`--license` any Openverse codes, default `cc0,by`; `--help` for filters). Pick from the text (title, licence, duration). `cves music download <id> Music/` → the file + its licence and attribution in `Music/CREDITS.md`. Tell the user the licence and whether it needs a credit line.
- **B, generate (ElevenLabs / Magnific connector):** `cves music generate "<prompt>" --duration N` prints the hand-off. Show prompt + expected cost and generate only after a yes. Save to `PROJECT/Music/`; `cves music credit <file> --provider .. --prompt ".."` records it.

## Sync (when the user wants the music in the edit)
1. `edit.yaml music:` `file`, `bed_lu`, `credits`; `drop_cut` (cut s) if the user names the drop moment.
2. `cves beats` → `Edit/beats.json` (tempo, downbeats, sections, drop candidates).
3. `music.sync` (cumulative): `drop`; `cuts` (+ cutaway edges and graphic entries onto beats ±`music.snap_tolerance_s`; A-roll cuts never move); `full` (+ whoosh / hit / boom / riser peaks onto beats). `cves beats --sync <mode>` prints the moves; `--apply` writes `edit.yaml` (backup `edit.yaml.bak-*`).
4. `cves mix` (bar-line fit, crossfade loop if short, ends on a downbeat + one-bar tail). Describe how it sounds only from a measurement (`Edit/mix.json`, earshot).
- Never commit music files to the repo.

**Show:** track, licence, credit line, tempo, drop (track + cut time), sync mode + moves.
