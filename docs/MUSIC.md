# Music: beat analysis, beat sync and music fit

Code: `engine/cves/beats.py` (analysis, placement, fit, sync report) and `engine/cves/mix.py` (renders the bed, places SFX).
Sourcing and licences are in `engine/cves/music.py` and [library/SFX-METHOD.md](../library/SFX-METHOD.md).

## 1. `cves beats`

```
cves beats [PROJECT] [--file Music/x.mp3] [--sync off|drop|cuts|full] [--apply] [--refresh] [--json]
```

This command analyses `edit.yaml music.file`, or the file you pass with `--file`, using librosa, and writes `Edit/beats.json`. All times in that file are **track** seconds.

| field | what it holds |
|---|---|
| `tempo`, `beats` | The tempo and the beat times. The tempo is folded by octaves into `music.tempo_range`, because trackers often lock onto double or half time. Each beat is refined to its onset peak. The grid is extended at the median period over the start and end of the track, where trackers drop weak beats (`extrapolated_beats` gives the count). |
| `downbeats`, `downbeat_phase`, `downbeat_confidence` | The bar phase. Each of the `music.beats_per_bar` phases is scored on three things: low-band (kick) onsets, beat-synchronous chroma change, and a squared vote from big energy rises. Drops and section starts land on downbeats. |
| `sections` | Agglomerative segments over beat-synced MFCC + chroma, snapped to downbeats, each labelled `low` / `mid` / `high` energy. |
| `energy` | An energy curve, 4 values per second, in dB relative to the median bar. |
| `bars` | Per bar: start time, full-band dB, low-band dB and a 12-bin chroma. Drop and loop matching use these. |
| `drops` | Drop candidates: bars whose next 2 bars are at least `music.drop_min_rise_db` louder than the median of the 4 before. Each has a score (rise + low-band rise + a bonus when it comes after a quiet stretch). They are ranked, at least 4 bars apart. |
| `phrases` | Music sections on bar lines, labelled `intro` / `build` / `drop` / `body` / `break` / `outro` from the bar energy and a novelty curve (energy step + chroma change). Derived from the cached bars on every load. See [SOUND.md](SOUND.md) §1. |
| `plan` | The last placement `cves beats` printed: mode, offset, drop, layout, moves. |

The cache is reused while the file, its size and mtime, the analysis version and the analysis keys stay the same. `--refresh` forces a new analysis.

## 2. Sync modes (`music.sync`)

Set the mode in the style (`music.sync`, default `"off"`) or per video in `edit.yaml music.sync`. Any `edit.yaml music:` key overrides the style key of the same name. The modes are cumulative: each one does everything the one before it does.

| mode | what happens |
|---|---|
| `off` | Legacy placement: the manual `music.drop_track` (track s) lines up with `music.drop_cut` (cut s). |
| `drop` | The drop is chosen automatically. `music.drop_pick: auto` takes the strongest candidate that needs no silent lead-in; with `music.phrase_align: true` (the default) it prefers, among those, the drop whose build starts on the story turn ([SOUND.md](SOUND.md) §1). An integer picks that index from `beats.json drops`. It is aligned to the story moment (the payoff): `music.drop_cut` if it is above 0, else the start of the first clip in `edl.json` whose `beat:` tag is in `music.drop_beats` (default `[PR, O]`, the first proof or offer), else the reveal (the `aroll.snap` punch-in). |
| `cuts` | `drop`, plus a report that moves **cutaway in/out points** and **graphic entry times** onto the nearest beat within `music.snap_tolerance_s` (default 0.12 s). The rules are listed below the table. `--apply` writes the moves. |
| `full` | `cuts`, plus at mix time every transition-type cue (name contains one of `music.sfx_snap`: whoosh, hit, boom, riser) is nudged so its **peak** lands on the beat. The nudge is at most `music.sfx_snap_max_f` frames (default 1), which keeps every SFX within 1 frame of its picture event (SND-07). |

Rules for the `cuts` moves:
- A-roll cuts are never moved. The engine invariant is that edits snap to segment boundaries.
- A cutaway edge that sits on a segment boundary may only move *outward*: its start earlier, its end later. Moving it inward would flash a sliver of the next or previous shot.
- No move leaves an A-roll piece shorter than `music.min_aroll_s`, or overlaps a neighbouring cutaway or the end card.
- A move never crosses an A-roll cut.
- **GFX-01:** no move shows a graphic more than `music.gfx_lead_s` (0.25 s) before its word. The check uses the first word after the cut from `words.json`, and the elements' `t_key` from `elements.jsonl` when a render exists.
- Graphic entries are the params `at`, `*_at` and `enter`. `out*` keys are exits and are never moved. An entry only moves inside its cutaway or segment span, and never past a sibling time in the same item, so its order is kept.
- New times are whole frames: the frame next to the beat that stays inside the tolerance.

`--apply` (needs a mode) does the following:
- copies `edit.yaml` to `edit.yaml.bak-<timestamp>`;
- writes `music.sync`, `music.drop_track` / `drop_cut` and the moves;
- pins a moved cutaway with `snap: false`, and writes its other edge's resolved (snapped) time.

The file is patched as text, so comments are kept. The patch is verified by re-parsing; if verification fails, the file is re-dumped and the command says so. Running `cves beats` again after `--apply` is idempotent: it suggests no further moves.

## 3. Music fit (`music.fit: bars`, the default)

`beats.layout()` lays the track under the whole video, end card included, in cut seconds:
- **Trim.** The track starts at the placement offset. A negative offset means the drop is earlier in the track than the moment: the bed then enters late, after a 50 ms fade-in.
- **Loop.** When the track runs out, it jumps back from one of its last 8 downbeats to a downbeat at least `music.loop_min_bars` earlier. The pair whose surrounding bars match best (chroma cosine, minus the energy difference) is chosen, and joined with an equal-power crossfade of `music.loop_xfade_s` centred on the downbeat. It loops as often as needed. Loop seams are always whole bars.
- **End.** If the track's own ending falls within the last 1.5 bars of the video, the track ends naturally. Otherwise the bed plays at full level up to the last downbeat. That is the latest one leaving at least `music.end_min_tail_s` before the end, preferably one at or after the end-card start minus one bar. From there it fades over `music.end_tail_bars` bars (cos² curve), never past the last sample. There is no hard 0.9 s fade.

`music.fit: none` keeps the legacy behaviour: a plain offset, zero padding and a 0.9 s fade.

## 4. SFX placement in the mix (`mix.all_cues`, used by `cves mix` and by QC)

- **SND-08, peak on the cut.** Transition whooshes (style `sound.transition_sfx`: whip → whoosh, glitch → swipe, cut / fade → none) carry `peak_at: <cut>`. Each SFX file's peak offset is measured with the same 10 ms RMS envelope the gate uses, and cached in memory and in `Edit/sfx_peaks.json` (keyed by file, mtime and trim). The cue is then placed so the peak, not the start, is on the cut. Before this fix the whoosh started 0.30 s early and peaked 5.5 frames before the cut.
- **SND-09, no identical repeats.** A cue identical to the one before it (same file, trim and pitch) gets `±sound.repeat_pitch_st` semitones, alternating, and `∓sound.repeat_gain_db`. This is deterministic, so a re-mix sounds the same.
- **Beat nudge** (`full` only; see section 2). Per cue, `beat_snap: false` opts out. The run is listed in `mix.json beat_nudged`.
- **Media audio.** Cues named `asset:<id>` (a `video_broll` with `audio: true`) resolve through `cves.assets.resolve`. `speed` time-stretches them and `raw: true` keeps their own level (no peak-normalise). They are never beat-nudged or varied.

`mix.json` records the music placement (`sync`, `fit`, `offset_s`, `drop`, `loops`, `end`, `sections`, `story`), the cue count, `peak_placed`, `beat_nudged`, the automatic `accents` and the `duck` settings.

- **Automatic accents** ([SOUND.md](SOUND.md) §2): a riser whose peak lands on the payoff and one into the hook, plus a downbeat hit on the payoff, within the `creative.sound_accents_per_30s` budget. They carry `beat_snap: false`: their target is already the picture event and, with phrase alignment, the drop.
- **Ducking** follows the voice envelope by default (`mix.duck_mode: envelope`; `gate` = the fixed dips described in SFX-METHOD.md); see [SOUND.md](SOUND.md) §3.

## 4b. Platform sound slot (`music.slot: platform`, organic posts)

For a post that will use a trending sound added in the app, `edit.yaml music:` takes `slot: platform` and a `guide`
instead of a `file` (full description in [VIRAL.md](VIRAL.md) §4):

| key | value |
|---|---|
| `music.slot` | `file` (default: the music is in the file) or `platform` (no music in the file; `goal: viral` only) |
| `music.guide` | what the edit is cut to: a reference track (`Music/trend.mp3`), a `beats.json`, or a tempo (`128`, `"128 bpm"`, `{bpm: 128, first_beat: 0.12}`) |
| `music.sound` | the sound's name or link in the app (written into POSTING.md) |
| `music.drop_cut`, `music.drop_track`, `music.offset` | as for music: where the drop lands (cut s), the drop in the track, the track time at cut 0 |

- `cves beats` treats a reference-track guide like music: `--sync cuts --apply` moves cut points onto its beat.
- `cves mix` mixes **no music** and writes `Edit/stems/guide.wav` (the track laid by `beats.plan`, or a click track on the
  tempo grid, accented on downbeats) next to the other stems. `mix.json` records it under `guide`.
- QC: SND-04 checks the music stem is silent; RET-32 measures the share of cuts within `music.snap_tolerance_s` of a guide beat.
- `cves deliver` ships the guide stem and POSTING.md ([DELIVERY.md](DELIVERY.md) §3).
- `cves validate` refuses the slot for ads (`goal: ad`, the default), a slot without a guide, and a slot with `music.file`.

## 5. Style keys

`music.sync, fit, beats_per_bar, tempo_range, snap_tolerance_s, drop_beats, drop_pick, drop_min_rise_db, loop_xfade_s, loop_min_bars, end_min_tail_s, end_tail_bars, gfx_lead_s, min_aroll_s, sfx_snap, sfx_snap_max_f`, the phrase keys `music.phrase_align, phrase_min_bars, build_min_rise_db, build_step_db, phrase_turn_weight, hook_beats, turn_beats, hook_cut, turn_cut` and `sound.transition_sfx, repeat_pitch_st, repeat_gain_db` (accents, ducking and the bank: [SOUND.md](SOUND.md)). They are all in `styles/default.yaml` with neutral values and comments.

YAML reads a bare `off` as `false`, and `false` is accepted as off.

## 6. Checking it

```
cves beats --sync full            # report: tempo, drops, placement, ending, moves, SFX nudges
cves beats --sync full --apply    # write it (backup kept)
cves mix && ffmpeg -i Edit/mix.wav -af ebur128=peak=true -f null -   # -14 LUFS, TP <= -1
earshot timeline <clip of the drop / the loop seam / the end>.wav    # listen before you claim how it sounds
```

On the example project, the analysis found the following:
- the track at 87.6 BPM (the tracker's first answer was 172, double time);
- the drop at 38.72 s in the track, where earshot hears an orchestral stab with heavy bass (the hand-set value was 38.70);
- 3 of 12 cut points and 8 of 26 graphic entries on the beat after `--apply`;
- all 7 transition whoosh peaks within 0.03 frames of their cut (they were 5.5 frames early);
- 0 identical repeats (there were 6 identical counter pops and 3 identical low hits);
- `mix.wav` at -14.1 LUFS with a -1.6 dBTP true peak.
