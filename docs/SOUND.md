# Sound: phrases, accents, ducking and the SFX bank

v0.4 cuts sound as carefully as picture. The music's sections line up with the story, a riser resolves on the payoff, the
bed breathes with the voice, and every sound effect is chosen from a catalogued, CC0-only bank.

Code:
- `engine/cves/beats.py`: phrases, story moments and alignment (it extends the beat analysis in [MUSIC.md](MUSIC.md));
- `engine/cves/sound.py`: automatic accents and ducking;
- `engine/cves/sfx.py`: the bank and `cves sfx`;
- `engine/cves/qc/sound_gates.py`: SND-32 and SND-33;
- `tools/make_sfx.py`: the house sounds.

Method and cue map: [library/SFX-METHOD.md](../library/SFX-METHOD.md).

## 1. Music phrases and the story

`cves beats` now also prints and stores `phrases` in `Edit/beats.json` (track seconds). These are music sections on bar lines:

| label | what it is |
|---|---|
| `intro` | the first section |
| `build` | the bars rising into a drop. Each bar is at least `music.build_step_db` (1 dB) over the one before, there are at least 2 of them, and they rise at least `music.build_min_rise_db` (2 dB) in all. The build starts on the first bar that rose. |
| `drop` | starts on a drop candidate whose next bars sit at or above the median bar |
| `body` | within 3 dB of the loudest section |
| `break` | under the median |
| `outro` | a last section that falls at least 1.5 dB under the one before it, or that sits under the median |

Boundaries are:
- bar 0;
- every drop candidate;
- novelty peaks: the energy step plus the chroma change between bars, z ≥ 1.5, at least `music.phrase_min_bars` apart.

**Story moments** (`beats.story_moments`) come from the clip `beat:` tags in `edl.json`. Each one can also be set by hand.

| moment | default | set it by hand |
|---|---|---|
| hook | the first `music.hook_beats` clip (`[H]`) | `music.hook_cut` |
| turn | the first `music.turn_beats` clip (`[P, A]`); without one, the end of the hook | `music.turn_cut` |
| payoff | the drop moment: `music.drop_cut`, else the first `music.drop_beats` clip (`[PR, O]`), else the reveal (the `aroll.snap` punch-in) | `music.drop_cut` |

**Phrase alignment** (`music.phrase_align: true`) applies in the `drop` / `cuts` / `full` sync modes when `drop_pick` is `auto`. Among the drops that need no silent lead-in, `plan()` prefers the one whose build starts on the turn. The score is the candidate's own score minus `music.phrase_turn_weight` per bar of distance.

Alignment rules:
- The drop always lands exactly on the payoff: the offset is the drop minus the payoff.
- Loop seams stay on downbeats (MUSIC.md §3).
- `cves beats` reports, in cut seconds, where the hook, turn and payoff fall against the sections.
- `mix.json music.sections` and `music.story` record the same information.

## 2. Automatic risers and impacts (`sound.accents`)

`mix.all_cues` adds accents to the template cues. Because the gates rebuild the cue list the same way, `cves mix` and QC always see the same list.

| accent | where | sound |
|---|---|---|
| riser into the payoff | its **peak** on the payoff | `@riser`, `sound.accents.payoff_riser` (medium) |
| impact on the payoff | on the payoff (the downbeat hit, layered with the drop) | `@impact`, `payoff_impact` (hard), a tagged hero (no offset) |
| riser into the hook | its peak on the hook when the hook starts at least `riser_min_s` in (a cold open); otherwise where the hook hands over to the body | `hook_riser` (soft) |
| impact on a reveal | a reveal cue (`reveal: true`) with no low hit of its own | `reveal_impact` (medium) |

Rules:
- **Restraint.** At most `creative.sound_accents_per_30s` accents (default 3; a video under 30 s still gets the full 3). They are taken in priority order: payoff riser, payoff impact, hook riser, then reveals in time order. The rest are logged as `skipped: restraint budget`.
- **A riser needs a landing.** Its target must already have a sound on it (within 2 frames), the music drop, or an impact placed with it. A riser that resolves into nothing sounds unfinished, so it is skipped.
- **Never doubled.** A moment that already has a riser (peak within 0.5 s) or a low hit (lowhit, boom, impact or hit within 2 frames) gets no extra one.
- **Only on picture.** A target must be within 1 frame of a known picture event: a cut, a cutaway edge, the end card or the punch-in. Otherwise the accent is skipped, so SND-07 holds.
- **Risers that resolve.** A riser is picked only if its peak is within `riser_tail_max_s` (0.1 s) of its end. It is placed by that peak, so the sound ends on the target. It must also fit the room before its target (`riser_min_s` to `riser_max_s`, starting at least `min_gap_s` after the previous accent).
- **Logged.** Each accent is an ordinary cue (`kw: accent, target, why`). `Edit/mix.json` `accents` lists every decision, whether placed or skipped, with the reason.
- **Off switch.** Set `edit.yaml sfx: {auto: false}` or `sound.accents.enabled: false`.

## 3. Ducking that follows the voice (`mix.duck_mode`)

| mode | behaviour |
|---|---|
| `envelope` (default) | The music gain follows the voice-band (250 Hz–5 kHz) RMS envelope (20 ms windows, 5 ms hop). It is 0 at `mix.duck_range_db` (30 dB) under the voice's loud level (p95) and reaches full depth 6 dB under it. Attack is `mix.duck_attack_ms` (40). Release is `mix.duck_release_ms`: `auto` = 1.25 × the measured syllable period (the 2–9 Hz modulation peak of the envelope), clamped to `mix.duck_release_range_ms` [250, 400]. The look-ahead is `sound.duck_lookahead_s`. |
| `gate` | The v0.3 fixed dips: a near-binary speech gate (100 ms average of \|voice\|) with a 30 ms attack and a 400 ms release. |

In both modes:
- **Depth comes from the style.** The voice band dips by `sound.duck_voice_band_db` (−8) × the control, and the lows and highs by `sound.duck_other_db` (−3) × the control.
- **The bed level is unchanged.** After ducking, the bed is still corrected to `sound.bed_lu` (SND-04), and the master is still set to −14 LUFS / −1 dBTP (SND-01/02).

What changes in envelope mode: the bed comes back between phrases instead of holding the dip, and stays down through the syllables.

`mix.json duck` records the mode, attack, release, syllable rate and look-ahead.

## 4. The SFX bank (`cves sfx`)

Banks are listed in precedence order; a later bank wins on the same id:

| bank | where |
|---|---|
| repo | `assets/sfx/manifest.yaml` |
| user | `~/.cves/sfx/manifest.yaml` (`$CVES_SFX` overrides the folder) |
| project | `PROJECT/Music/sfx/manifest.yaml` |

Each entry has:
- `id`, `file`;
- `category`: whoosh, impact, riser, ui, pop, transition or ambience;
- `intensity`: soft, medium or hard;
- measured `duration_s`, `peak_db`, `loudness_lufs` (BS.1770; null under 0.4 s) and `peak_at_s`;
- `licence`: `CC0 1.0`, `CC0, synthesized by CVES` or `own recording`;
- `source`, `title`, `creator`.

How cues use the bank:
- **By category.** A cue can be named `@category[:intensity]` instead of a file, in `edit.yaml sfx.extra`, in templates or in accents. It resolves deterministically to the closest intensity, never to the same id twice in a row.
- **By name.** Plain names still work: `sfx_bank` searches the project, user and repo folders.

```
cves sfx list [--category impact] [--json]
cves sfx fetch "<query>" --category whoosh [--n 3] [--to user|project|DIR] [--intensity medium] [--max-s 6]
cves sfx add FILE --category impact [--intensity hard] [--id impact_door] --source URL [--licence cc0|own] [--to user|project|DIR]
cves sfx check
```

`fetch` searches Openverse (Freesound's recordings), plus the Freesound API when `FREESOUND_API_KEY` is set. It keeps **CC0 only** (BY, BY-SA, NC and ND are refused) and skips sources already in the bank. Each download:
- goes to its own fresh temp folder over https, capped at 25 MB, and is treated as untrusted data;
- is decoded by ffmpeg as audio only: first audio stream, at most `max_s + 1` s, converted to 48 kHz mono 16-bit WAV;
- is measured, then recorded in the bank's `manifest.yaml` and `CREDITS.md` with its source URL and licence.

`add` refuses any licence other than CC0 (which needs `--source`) or your own recording.

**The repo bank** holds:
- 13 recorded Freesound CC0 sounds;
- 15 sounds synthesized by `tools/make_sfx.py`: three risers, four impacts, three whooshes, a swish, two pops, a tick and a room tone. These are CC0, synthesized by CVES. They are deterministic and made of numpy noise and tones.

Every file is listed in `assets/sfx/CREDITS.md`.

Listening notes (`earshot`, 2026-11-19):
- The synthesized sounds read as the right kind of sound: the impacts as a kick, sub drop or drum hit, the whooshes as a whoosh or whip pan, and the risers as uplifter / downlifter sweeps.
- earshot rates them "likely code-synthesized".

So:
- for hero moments in a client ad, prefer real CC0 recordings: `cves sfx fetch`, then listen with `earshot describe` / `earshot realness` before using them;
- `sfx.pick` takes a recording over a synthesized sound at the same intensity (SFX-METHOD rule 3), so the payoff riser is the recorded `riser`. Automatic impacts must be hits (onset to peak within `sound.accents.impact_attack_max_s`, 30 ms); the recorded `boom` is a slow swell, so the payoff hit is the synthesized `impact_hit`; the synthesized sounds fill the roles the recordings don't cover (a soft riser, short resolving risers, soft impacts).

## 5. QC

| gate | what | status |
|---|---|---|
| SND-32 | every automatic riser peaks within 1 frame of its target | WARN (new) |
| SND-33 | the drop section starts within `sound.phrase_tolerance_s` (0.05 s) of the payoff, on a downbeat; loop seams on downbeats. With `music.sync: off` and a hand-set `music.drop_track`, that drop counts when the analysis finds one within a bar (the difference is reported) | WARN (new) |

Automatic risers are judged by SND-32 and SND-07, not by SND-08 (transition whooshes). The reasons are in `knowledge-base/DECISIONS.md` ("Senior sound").

## 6. Checking it

```
cves beats --sync drop                 # sections, story alignment, the drop on the payoff
cves mix && jq '.accents, .duck, .music.story' Edit/mix.json
cves qc --fast | grep SND-3            # SND-32 / SND-33
earshot timeline Edit/mix.wav          # listen: the riser resolves on the drop, the bed breathes under the voice
```
