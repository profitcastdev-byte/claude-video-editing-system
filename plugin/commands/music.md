---
description: Find licensed music for the edit. Openverse search with licence and credits, or a hand-off to the ElevenLabs or Magnific connector
argument-hint: "[mood / genre / bpm] or 'generate'"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:music: licensed music

Request: `$ARGUMENTS`. Follow the `video-editor` skill. Read RULEBOOK §7 (music) and the client's `STYLE.md` (music feel).

## You decide: the brief
One line: mood, energy, bpm range, instruments, where the drop should land (`music.drop_cut`, usually the snap punch-in or the proof reaction; by default the first proof / offer beat), and length ≥ the runtime plus a tail. A shorter track is looped on bar lines, but one with a clear build and drop works best. One track, with an energy lift, no mood change inside the section used.

## Option A: Openverse (default)
- `cves music search "<query>"` (check `cves music --help` for the exact subcommands and filters). Prefer licences that allow commercial use without NC/ND restrictions (CC0, CC BY). Paid Meta ads are commercial.
- Pick 2-3 candidates from the text results (title, licence, duration, bpm). To judge how they sound, use an audio-listening tool if you have one. Don't guess.
- Download the chosen track with the engine (`cves music download <id>`). It saves to `PROJECT/Music/` and appends the licence and attribution to `Music/CREDITS.md`.

## Option B: generate through a connector (ElevenLabs or Magnific)
- If an ElevenLabs or Magnific music tool is connected in this session, show the user the prompt and the expected cost or credits, and generate only after they say yes. Save the file to `PROJECT/Music/`, and record the tool, prompt, date and terms in `Music/CREDITS.md`.
- If no connector is available: give the user the ready-made prompt to paste into ElevenLabs Music (or Magnific), and ask them to drop the file into `PROJECT/Music/`.

## Then: sync the music to the edit (docs/MUSIC.md)
1. Set `music:` in `edit.yaml`: `file`, `bed_lu`, `credits`. Set `drop_cut` (cut seconds) only if the drop must land somewhere other than the first proof / offer beat (`music.drop_beats`).
2. `cves beats` analyses the track: tempo, beats, downbeats, sections, energy, drop candidates -> `Edit/beats.json`. Check the drop candidate by ear (earshot on a clip around it) before trusting it.
3. Pick a sync mode (`music.sync` in edit.yaml or the style; the modes are cumulative):
   - `drop`: the strongest drop lands on the story moment. `drop_track` is computed, so don't measure it by hand;
   - `cuts`: also moves cutaway in/out points and graphic entries onto beats (±`music.snap_tolerance_s`). A-roll cuts never move, and GFX-01 is respected;
   - `full`: also nudges whoosh / hit / boom / riser peaks onto beats in the mix (≤ 1 frame).
4. `cves beats --sync <mode>` prints the plan and the moves. Read it, then `cves beats --sync <mode> --apply` writes `edit.yaml` (a backup `edit.yaml.bak-*` is kept, along with the comments).
5. `cves mix`. The bed is fitted on bar lines (looped with a crossfade if the track is short) and ends on a downbeat with a one-bar tail. Then run the SND gates (`cves qc`), and `ebur128` on `Edit/mix.wav` (-14 LUFS, TP ≤ -1).
6. Listen with earshot to the start, the drop region and the ending (and any loop seam `mix.json` reports) before telling the user how it sounds.
- **Never** use a track without a recorded licence. Never commit music files to the repo.

## Show the user
The chosen track, its licence, the credit line, the tempo, where the drop lands (track and cut time), the sync mode and the moves applied, and what you heard at the drop and the ending. For generation, ask for consent and cost approval first.

## Stop?
Only for the generation consent (option B). Otherwise go back to the step that asked for music.
