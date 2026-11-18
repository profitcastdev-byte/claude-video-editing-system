# Sound effects and music: the method

Where this comes from: Nick Saraev's reel on fixing AI-picked sound ([De4XVvXPTWY](https://www.instagram.com/reel/De4XVvXPTWY/)), the sound module of the
knowledge base (`knowledge-base/modules/5 Sound Design & Audio Mixing.md`) and the user's own corrections on the first ad (`LESSONS.md`).
The engine implements all of it in `engine/cves/mix.py`. Every template emits its own cues, so sound is never an afterthought.

## The core idea (Nick Saraev)
AI-built motion graphics look good, but the sounds an AI picks sound cheap. The fix is **real recordings, placed on the exact frame, at the right level**.

## Where sounds come from
| Source | Use | How |
|---|---|---|
| **Openverse** (openverse.org, free API) | Real recordings under Creative Commons (CC0 / CC BY only; NC, SA and ND are refused). Includes Freesound | `cves music search "whoosh" --kind sfx`, then `cves music download <id>` (credits are written to `Music/CREDITS.md` automatically) |
| `assets/sfx/` (in this repo) | 13 CC0 house sounds: lowhit, swipe, whoosh, keyboard, card, pop, switch, riser, boom, ring, ding, scribble, button | Used by the templates' cues; see `assets/sfx/CREDITS.md` |
| **ElevenLabs** / **Magnific** (Claude connectors) | Custom SFX or music when nothing in a library fits | `cves music generate` prints the hand-off; `cves music credit <file>` records it |
| **Real SFX** skill (github.com/Clipwing/skills) | Reads a timeline and places real recordings on the frame | Optional; see TOOLS-REGISTRY |
| **earshot** (github.com/Leonxlnx/earshot) | Gives Claude "ears": describe, compare, A/B, realness, critique, loudness | Installed by the installers; run before judging any sound |
| sound-effects (Barty-Bart), video-sound (varg) | Alternative CC0 kits and mix graders | Evaluated, not installed |

## Rules for every edit
1. **One sound per visual event.** Never a bed of random whooshes. Never the same file back to back (cut variants, or pitch-shift each repeat).
2. **On the frame.** The sound starts on the frame where the motion *starts* (for a whoosh, the mixer measures each file's peak offset and places it so the PEAK lands on the cut; SND-08). Gate SND-07 checks ±1 frame.
3. **Real over synthetic.** Foley, UI clicks, paper, glass. No beeps from code unless earshot rates them as real.
4. **Reveals hit full; everything else sits 3 dB back.** Reveals are the big words, the extreme punch-in, the number landing and TOP 3 (`reveal: true` in a cue).
5. **Silence is a sound.** A short dip before the payoff makes it land. This is an A/B option; it isn't on by default.
6. **Style fit.** Keep one sound family per video. Gritty bass hits don't belong in a corporate piece, and glassy dings don't belong in a streetwear promo.

## Music
- **The bed sits about −7 LU under the voice while he speaks.** The user rejected −23, −14 and −10 LU as too quiet. Gate SND-04 measures the real music+SFX bed against the voice, and `mix.py` corrects to the target instead of guessing.
- **Ducking is frequency-split.** The voice band (250 Hz–5 kHz) dips 8 dB while he speaks; lows and highs dip only 3 dB. The bed stays big without masking consonants.
- **The duck looks ahead 120 ms,** so the music is already down when a soft word starts.
- **Sync the drop to the biggest visual beat.** In the example, the drums land on the extreme punch-in at "your turn" (`music.drop_track` / `drop_cut` in edit.yaml).
- **Licensing:** paid ads need licensed music. Use Openverse (CC0 / CC BY with credit), or generate with ElevenLabs or Magnific. Never ship a commercial track you don't hold rights to.

## Master
- −14 LUFS integrated (gate window −14.5 to −13.5), true peak ≤ −1 dBTP, no clipped samples, AAC 256 kb/s at 48 kHz.
- Stems are written to `Edit/stems/`, scaled to match the premaster, so faders in Resolve or Kdenlive behave as rendered.

## Cue map (effect → sound)
| Effect type | Sound |
|---|---|
| Snap zoom, punch-in | Short whoosh or air swish (80–150 ms) |
| Whip into a cutaway | Whoosh placed by its measured peak, peak on the cut |
| Glitch out of a cutaway | 0.18 s swipe |
| Chips, checklist pop, notifications | Soft UI pop or tick, pitched up slightly for each item |
| Card landing | Card / paper slide, then a pop on its ✓ or ✕ |
| Typing, prompt bar, search row | Real keyboard clicks, for exactly the typing duration |
| Counter ticking | 6 soft pitched ticks, then a low hit on the final number |
| Big word slam (roto) | Low hit, full level |
| Extreme punch-in | Low hit + boom, full level (and the music drop) |
| Frame break, shatter | Glass crack, then a debris tail |
| Paper cutout or tear | Paper rip or rustle |
| Impact frame | Bass hit or boom with a short sub drop |
| Studio reveal | Two light-switch clunks, then a low hum |
| Blow away | Wind gust plus a granular sand hiss |
| Letter dive, zoom-through | Riser into a whoosh |
| Growth curve | Rising tone (pitch follows the line) |
| Price or brand chest graphic | Button, then a ding |
| End card | Whoosh in, low hit on the logo, pop on the pill |

## Checking by ear (earshot)
`earshot critique mix.wav` scores a mix against professional references. Two of its flags are false on talking-head ads:
- **"Salient hit density" high:** the voice alone scores about 2 hits/s, so it's measuring speech rhythm. Check the voice stem before trimming SFX.
- **"Music presence" low:** the references are music-led launch films. Voice-led ads sit lower by design.
