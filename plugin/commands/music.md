---
description: Find licensed music for the edit. Openverse search with licence and credits, or a hand-off to the ElevenLabs or Magnific connector
argument-hint: "[mood / genre / bpm] or 'generate'"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:music: licensed music
Request: `$ARGUMENTS`. Read RULEBOOK §7, the client's `STYLE.md` (music feel), `skills/video-editor/reference/sound.md` (beats, accents, ducking, SND-32/33), `docs/MUSIC.md`.

**Brief (one line):** mood, energy, bpm range, instruments, drop target (`music.drop_cut`: usually the snap punch-in or proof reaction; default the first proof / offer beat), length ≥ runtime + tail (shorter loops on bar lines; a clear build + drop is best). One track, an energy lift, no mood change in the section used.

- **A, Openverse (default):** `cves music search "<query>"` (`--help` for filters). Prefer CC0 / CC BY, no NC/ND (paid Meta ads are commercial). Pick 2-3 from the text (title, licence, duration, bpm); judge sound with an audio tool, never guess. `cves music download <id>` → `PROJECT/Music/` + licence and attribution in `Music/CREDITS.md`.
- **B, generate (ElevenLabs / Magnific connector):** show prompt + expected cost; generate only after a yes (**stop**). Save to `PROJECT/Music/`; tool, prompt, date, terms in `Music/CREDITS.md`. No connector: give the user the prompt; they drop the file in `PROJECT/Music/`.

## Sync
1. `edit.yaml music:` `file`, `bed_lu`, `credits`; `drop_cut` (cut s) only if not the first proof / offer beat (`music.drop_beats`).
2. `cves beats` → `Edit/beats.json` (tempo, downbeats, sections, phrases, energy, drop candidates). Check the drop by ear (earshot) before trusting it.
3. `music.sync` (cumulative): `drop` (`drop_track` computed, don't measure); `cuts` (+ cutaway in/out and graphic entries onto beats ±`music.snap_tolerance_s`; A-roll cuts never move; GFX-01 respected); `full` (+ whoosh / hit / boom / riser peaks onto beats, ≤ 1 frame). `cves beats --sync <mode>` prints moves; `--apply` writes `edit.yaml` (backup `edit.yaml.bak-*`, comments kept).
4. `cves mix` (bar-line fit, crossfade loop if short, ends on a downbeat + one-bar tail). `cves qc` (SND gates) and `ebur128` on `Edit/mix.wav` (-14 LUFS, TP ≤ -1). Earshot the start, drop, ending and any loop seam in `mix.json` before describing it.
- **Never** a track without a recorded licence; never commit music files.

**Show:** track, licence, credit line, tempo, drop (track + cut time), sync mode + moves, what you heard at drop and ending. Then back to the step that asked.
