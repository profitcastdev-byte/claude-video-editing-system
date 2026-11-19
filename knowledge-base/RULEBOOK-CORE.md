# CVES Rulebook: core (loaded every session)

The hard rules, short. The full rules, with their sources and numbers, are in [`RULEBOOK.md`](RULEBOOK.md); this file never
overrides it. When the two read differently, `RULEBOOK.md` wins: fix this file in the same PR.

**Read the full `RULEBOOK.md`:** all of it for a new client's first edit, and before changing a rule, gate, threshold or
template. Otherwise read the section for the step you are on, when you reach it:

| Step | Read |
|---|---|
| 1 Setup (brief, probe, shoot brief, instrumenting) | §1 |
| 3 Story (takes, structure, beats, hook, information order, setup→payoff) | §2 |
| 4 Plan (`edit.yaml`: rhythm, jump cuts, transitions, roto) | §3, §5 (graphics + motion), §6 (framing) |
| 5 Moodboard | §4 |
| Music, SFX, voice chain, mix levels | §7 |
| Grade, skin, palette | §8 |
| Captions, safe zone, frame 0, ending | §9 |
| Delivery, final checks | §10 |
| A user note | §11 |
| `goal: viral` (organic post) | §12 + `modules/viral-playbook.md` |

**Precedence.** (1) USER-confirmed corrections > (2) the client's style profile (every per-client choice: palette, grade,
captions, transition kinds, pacing bands, bed level; the QC gates read their thresholds from it) > (3) EDIT-STANDARD >
(4) module rules. Open conflicts are **(D)** in `RULEBOOK.md` and listed in `DECISIONS.md`; their default applies until
the user answers. Gate ids (`CUT-05`) refer to `QC-GATES.md` (grep the id).

## Non-negotiables (RULEBOOK §0, USER-confirmed)
1. The user's own inspiration edits are the style spec: measure them (`cves inspire`), study them before designing, never replace their look with your pick or a preset.
2. The music bed level is the client's choice (`sound.bed_lu`, default −10 LU); never lower it to make a gate pass.
3. No added grain. One decode, one encode.
4. Snap every edit, cutaway and transition to an exact segment boundary; a one-frame flash of the next take is a jump cut.
5. No generative voice enhancement; every voice process passes the words gate.
6. Check every kept clip for stutters, verbatim (CUT-03); Whisper hides disfluencies.
7. Icons from the Material set only; never draw icons by hand.
8. Keep the complete sign-off (the whole brand name, `qc.brand_tail`).
9. Tag the delivered file `tv / bt709 / bt709 / bt709`.
10. Objective faults never reach the user: run every gate before sending anything.
11. Only published, verifiable proof on screen (names, numbers, prices), each claim with its source in `Brand/claims.md`.
12. Paid ads use only licensed music (CC0 / CC BY with credit, or ElevenLabs / Magnific generation).
13. Never put the presenter's face inside a graphic, never cut the body off inside the frame (no plate shrink), never text over the face.
14. Prices, CTAs and key numbers go in full-screen cutaways, not on the chest.

## Hard rules by stage (one line each; numbers are style defaults, the client's profile wins)
- **Story:** keep the last complete take that passes CUT-03; label every sentence with the structure's beats or X and work backwards (sign-off, offer, problems, proof, hook last); join beats with *therefore* / *but*, never *and then*; hook: first word ≤ 0.25 s, topic by 2 s, done by ~5-6 s, no greeting / credentials / vague suspense; proof starts by 50 % of runtime; price after proof; brand last; every loop closed before the CTA; honest stakes only; the user approves the cut list.
- **Plan:** every element tied to a word time; A-roll shots ≤ `grammar.max_shot_s`, never longer than `grammar.max_cutaway_s` without the face; a visual event at least every 4 s (2.5 s in the first 6 s); hide every A-roll jump cut with a framing step ≥ `framing.min_step` or a cutaway; cut on the completed thought; the hard cut is the default, transitions carry meaning, no dissolves / wipes / irises; roto ≤ `grammar.roto_max` moments, each ≤ 3 s; speech outranks music.
- **Graphics + motion:** nothing appears before it is said (0 to +6 f after its keyword); every cutaway illustrates its own line; one L1 element per frame; one alignment axis per card; contrast ≥ 4.5:1 (3:1 large); one idea per cutaway; eased entries / exits, overshoot ≤ 10 %; one primary mover at a time; holds > 1 s keep moving; no shake; check face clearance and safe zones on every frame.
- **Framing + colour:** the face is L1 and the brightest large region; never rotate or mirror the A-roll; edge-accurate matte (no aura); skin stable across segments (ΔE ≤ 3 on a cut); no global-saturation fixes, no crushed blacks, no teal A-roll unless the inspirations use it; no print LUT, no `tune film`.
- **Sound:** the voice first (podcast-mic chain, dry, centred); no speech gap > 0.25 s; the bed at `sound.bed_lu` over speech; one music track, no hard stop, no music on black; SFX on their event frame, ≤ 2 hero accents; master at `sound.master_lufs`, true peak ≤ `sound.true_peak`.
- **Captions + platform:** always on (unless the style says none), clear of the face, inside `platform.safe_zone`; frame 0 is the face or the hook text, never black or a logo sting; sound-off readable; end on the brand + a short tail or an end card ≤ 3 s, no fade, no black; native aspect, no letterbox.
- **Delivery:** decode once, encode once (x264 crf 16, no `tune film`, constant source frame rate, `+faststart`); every blocking gate passes and every WARNING is listed.
- **Feedback:** every note becomes a rule (here / ES / the style profile) plus a gate; look for the cause upstream first; don't re-cut what passed.
- **Viral:** never loosens a gate; visual change and text by 1.0 s; payoff in the last 20 %; interrupts budgeted (no effect soup); no dead air > 0.6 s; a trending sound is never baked in, and ads never use the platform slot.

## Never do (RULEBOOK "Never do")
Show anything before its word; wallpaper cutaways, decorative motion or two primary movers; effects over the face for the
whole video or a wide matte feather; plain mono text for client names, CapCut pills or bouncing one-word captions unless
the style asks; dissolves, wipes, irises (or fades the style doesn't use); end on black or with anything after the
brand; text over the face or under the Reels UI; music masking a word; reverb or pan on the voice; linear starts and
stops, rubbery overshoot, shaking punch-ins, rotated or mirrored A-roll; skin fixed with global saturation, teal shadows on
the A-roll, crushed blacks; invented stakes, scarcity or "watch till the end" hooks.
