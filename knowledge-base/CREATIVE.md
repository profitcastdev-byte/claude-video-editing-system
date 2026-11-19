# Creative method: how a senior editor decides

The RULEBOOK says what must never be wrong. This file says how to make an edit *good*: one clear idea, carried with
taste, and nothing extra. It sits under the RULEBOOK in precedence (USER > STYLE > ES > module rules): where a line here
seems to disagree with the RULEBOOK or the client's style profile, they win. Every rule cites its source module or rule.

Use it twice per edit: at **creative direction** (before planning `edit.yaml`) and at **critique** (after QC passes,
`cves critique`, before anything is shown to the user).

## 1. Creative direction comes before the plan
Write `PROJECT/Edit/DIRECTION.md` after the cut list is approved and before `edit.yaml` is planned. Keep it to one screen:

1. **Concept, in one line.** What the viewer should feel and believe by the end: "a calm fix for a stressful chore", not
   "a dentist ad". It comes from the brief's emotion and want + obstacle (RULEBOOK §1). [2.1, 6.1]
2. **Emotional arc.** Three to five words along the beats, e.g. *irritation → recognition → relief → confidence*. The cut,
   the music energy and the colour of the cutaways follow this arc, not the other way round. [6.1, 6.3, 5.1]
3. **The ONE signature moment.** The single beat a viewer would screenshot or rewatch: usually the proof number or the
   turn into the offer (RULEBOOK §3 "the proof boundary gets the strongest visual change"). Everything else is quieter so
   this lands. Name its time and how it is built (the one extreme punch-in, a hero motion piece, a music lift). [6.6, 7.2]
4. **The motif.** One visual or sonic idea that recurs and pays off: a shape, a colour reserved for "the fix", a sound
   that marks every proof point, a framing that returns at the end. It appears at least twice and changes meaning once. [3.1, 8.3, 5.1]
5. **What we will NOT do.** Three to five refusals specific to this video ("no second accent colour", "no whip into the
   CTA", "no music hit before the proof"). Restraint decided up front is cheaper than effects removed later. [4.3, 1.6]
6. **Platform and goal.** Ad (persuade, one CTA) or viral (hold, loop, share), and the target platform. They set the
   pacing band and the hook budget (docs/STYLE.md; `edit.yaml goal:` / `platform.target` when present).

Show DIRECTION.md to the user together with the cut list (approval 1) or the edit plan (approval 2). It is not a third
approval: a change request on it is handled like any other note.

## 2. Restraint budget
Creativity is budgeted (spec anti-goal: "effect soup"). The numbers live in the style profile `creative:` section, so a
client's series can set its own; `cves critique` reports usage against them. Defaults:

| budget | default (style key) | why |
|---|---|---|
| signature moments | 1 per 30 s (`creative.signature_per_30s`) | a moment only lands if it is rare; the one extreme punch-in (`framing.extreme_max`) counts [7.2, 6.6] |
| distinct transition kinds | 2, cut not counted (`creative.transition_kinds_max`) | transitions carry meaning; a new kind must mean something new (RULEBOOK §3) [2.3, 2.4] |
| animated graphics | 6 per 30 s (`creative.motion_pieces_per_30s`) | every graphic illustrates its own line; no wallpaper (RULEBOOK §5) [7.8, 4.3] |
| accent colours | 1 beyond text and stage (`creative.accent_colors_max`) | colour carries meaning: the accent is "the fix" (RULEBOOK §5, §8) [3.1, 8.6] |
| primary movers | 1 at a time | RULEBOOK §5 Motion [1.6, 7.6] |

Going over a budget needs a reason written in DIRECTION.md. "It looked cool" is not a reason.

## 3. Contrast and rhythm
- **Vary shot length on purpose.** Set a baseline, then deviate: build → burst → release. The longest hold of a section
  comes just before its fastest run; the CTA is cut slower than the baseline (RULEBOOK §3). A metronome is a fault even
  when every shot is "in band". [2.5, 2.6, 4.5, 4.8]
- **Let moments breathe.** After the signature moment, hold: no new graphic, no new move for at least a beat, so the
  viewer can feel it. A hold over 1 s still moves gently (slow push or drift, RULEBOOK §5). [1.1, 1.2, 4.8]
- **Silence as a tool.** Within speech, never dead air (RULEBOOK §7: no gap over 0.25 s). The tool is the *music*: a short
  bed dip or drop-out under the line before the payoff, then the lift on the reaction to the proof (RULEBOOK §7). Contrast
  comes from dynamics, never from cutting the voice. [5.7, 6.6]
- **Contrast between sections.** The proof boundary is the strongest change in the cut (framing, colour, sound). The
  problem section and the offer section should look and sound different, so the turn is felt. [6.6, 8.3]
- **Energy follows the arc.** Music energy, SFX density and graphic density rise toward the signature moment and settle
  for the CTA; check it on `Edit/critique/timeline.png`. [5.1, 4.8]

## 4. Taste checks (ask of every element)
Run these on the contact sheet and the energy timeline before showing anything:
1. **Would a senior editor cut this?** If removing it loses nothing the viewer needs, remove it. [4.3]
2. **Is every element motivated?** Each graphic illustrates its line, each transition marks a change of meaning, each SFX
   marks a picture event, each colour has a role. No decorative motion (RULEBOOK "Never do"). [7.8, 2.3, 5.1, 3.1]
3. **Is the signature moment the strongest thing in the cut?** If something else competes with it, calm that down. [6.6]
4. **Does every paused frame look designed?** Hierarchy, one alignment axis, spacing from one scale (RULEBOOK §5). [3.1, 3.4, 4.3]
5. **Does it read sound-off and sound-on?** Picture and captions tell it alone; the mix adds feeling, not information. [2.7, 9.5]
6. **Does the motif pay off?** If the motif appears once, cut it or bring it back.
7. **Would the client recognise their series?** The style profile is the look; creativity works inside it (RULEBOOK §0.1).

## 5. Critique (after QC passes, before the user sees it)
`cves critique` builds `Edit/critique/`: a contact sheet (a frame per shot plus key moments), an energy / interrupt
timeline (cuts, graphics, SFX, music energy, speech, loudness) and `CRITIQUE.md`. Score each rubric line 1–10 with one
reason, honestly: hook, story clarity, pacing, visual aesthetics, motion craft, sound design, creativity, restraint,
platform fit, brand fit. Then write the three changes a senior editor would make next.

- Fix every line scoring **below 7** that can be fixed in `edit.yaml`, re-render what changed, re-run `cves qc`, and
  critique again. Say what could not be fixed (it needs a pickup, proof or a new template).
- Log the scores: `cves learn rate <version> <overall> --by claude --scores hook=..,story=..`. Over time
  `cves learn mine` compares your self-ratings with the user's, so you learn where your eye is too kind.
