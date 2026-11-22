---
description: Pick the takes and beats from the raw transcript (Edit/selects.yaml) and build the tightened cut with `cves select`
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:story: selects and the cut
Project: `$ARGUMENTS` (or the current one). Text only: open no image. Structures: `skills/video-editor/reference/formats.md`.

`cves story` prints `Edit/raw_transcript.txt` (raw timestamps from `cves ingest`) and the structure + beats in force (style `grammar.structure`: problem H P A PR O C, offer H M PR R C, story H S T PR C, or `custom` with `grammar.beats`). Raw times drift 1-3 s around retakes: `cves select` re-times each clip from its `text:`.

## Run
- Write **`Edit/selects.yaml`**: `clips: [{id, in, out, beat, text}]`, raw seconds, in the order the user wants (re-ordering allowed), `text:` = the take's exact words (alignment needs it). The takes, order and beats are the ones the user asked for; where they gave no choice, pick the clean take. Example: `examples/`.
- **`cves select`** aligns each take (re-transcribes a window, finds `text:`, snaps `in` / `out` into the pauses; one line per clip: moved, match score). `WARNING` = not found, hand times kept: fix `text:` (as spoken) or the times. `align: false` on a clip keeps hand times; `--align-only` reports without cutting. Then the voice chain (DeepFilterNet + podcast chain), pause tightening, frame snap → `Edit/edl.json`, `voice_final.wav`.

**Show:** the cut list as text: `# | beat | in-out (s) | take | text` (from `edl.json`), runtime, alignment moves > 0.3 s and clips kept at hand times.
