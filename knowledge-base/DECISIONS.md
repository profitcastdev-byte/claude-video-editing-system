# Decisions for the user

These are the open conflicts that need your call, most important first. They were raised while the system was first tested on one ad (versions v1–v3c of that edit are cited below). Where an answer is a per-client choice, it now lives in the client's style profile (`docs/STYLE.md`) rather than in the engine; the gates read the threshold from there. Each one carries a **default**; it applies until you answer. Sources are in square brackets; gate ids point to `QC-GATES.md`.

## Open

1. **Adopt the new gates into ES §4.** ES has no structure, retention, motion, colour or platform gates, so a cut can pass all 14 current gates and still be in "brochure order" or have shaking punch-ins. [2 B.7#11, 4 B.7#14, 6 B.7#3, 1 B.7#10, 8 B.7#6]
   **Default:** the 76 BLOCKING gates in QC-GATES block delivery; WARNING and CALIBRATE gates only report until they are calibrated.

2. **Text safe zone: ES 60 px vs Meta Reels 14/35/6%.** 60 px stops clipping, but it doesn't protect text from the top bar, the bottom CTA panel or the right rail. [9 B.7#2, 3 B.7#2]
   **Default:** CTA, prices, logos and key numbers must sit inside x 65–1015, y 269–1248 (BLOCKING); other text gets a WARNING; 60 px stays as the hard minimum for everything.

3. **Caption position: "mid-chest" vs y ≤ 1248.** On a close selfie, mid-chest falls inside the bottom 35%, under the Reels UI. `cves qc` also requires the chin to stay above y 1290. [9 B.7#1, 3 B.7#2, 7 B.7#9]
   **Default:** amend ES §2 to "just below the chin, bottom edge ≤ y 1248, never over the face", and update the gate to match.

4. **Punch-in step size.** ES says about 1.15×, but `cves qc` passes 8%, and the 1.12–1.14 `ZOOM` table plus the 1.5% creep gives about 1.10 at the real cut. The videos say "slightly different sizes don't read". [7 B.7#1, 2 B.7#5]
   **Default:** enforce ≥ 1.15× measured at the cut frames, use 1.18–1.25× where the source allows, and raise the gate threshold to match.

5. **Proof in the first 3 s vs proof at the midpoint.** 4.6 says front-load the proof; module 6 rations it (proof starts ≤ 50%, price after). [4 B.7#1, 6 B.2.3]
   **Default:** the hook names the topic and the pain, with an optional spoken teaser of the number. The full proof starts ≤ 50% of runtime. RET-14 is a WARNING; STORY-06 is CALIBRATE.

6. **Master loudness window.** ES says −14 ±0.5 LUFS; module 5 says treat −14.0 as a ceiling and pass only −15.0 to −14.0. [5 B.7#9]
   **Default:** keep the ES window as BLOCKING, aim the mix at −14.5 to −14.0, and WARN above −14.0.

7. **One intentional pause beat (≤ 0.4 s, after the proof number or before the offer).** The pause gate caps speech gaps at 0.25 s. [2 B.7#6, 6 B.7#2, 4 B.7#2]
   **Default:** no exception. Make the "breath" with a picture hold (the count-up runs while the voice continues).

8. **A short music dip before the payoff** (0.3–0.5 s, the bed pulled about 6–10 dB, not silence). It was untested on the first test ad, whose reviewer asked for a bigger bed. [4 B.7#3, 5 B.7#4]
   **Default:** off in the delivery; render it as an A/B variant once to compare.

9. **Cutaway entries under whips, and empty containers before their words.** In the code, some cutaway content starts up to 0.15 s before the cut, so its entry is hidden; the c1 search rows appear empty before their queries are spoken. [1 B.7#2, 1 F11–F12]
   **Default:** measure what your inspirations do. Until then, show the full entry after the whip clears, and let containers enter on their own words (literal ES).

10. **Ending format.** The options are a hard cut on the brand word, a short logo end card, or 9.5's 5–6 s card with music fading on black. [9 B.7#5, 6 B.7#6]
    **Default:** the spoken brand is the last word, then a ≤ 2 s end card or a 0.1–0.5 s tail, hard cut, no black, loop-friendly. A/B the end card against a hard cut later.

11. **Per-segment colour correction.** v3c has one segment about 0.15 stop dark (skin ΔE 7.6 into segment `08a`) and a direct cut at ΔE 4.2 (06a→06b). [8 B.7#4]
    **Default:** add an optional per-segment subject gain, driven by COL-06/07, after confirming the 06a→06b reading isn't a sampling artefact.

12. **Eye line, headroom and centring.** In v2 the eye line sits at 36–45% of height (target 30–40%) and faces sit 60–140 px right of centre. Fixing this needs a baseline zoom above 1.0 with a vertical offset. [7 B.2, 7 B.7#9, 7 B.7#12]
    **Default:** re-measure with stored landmarks, calibrate FRAME-04 to 06 on your inspirations, then recentre. Report only until then.

13. **CTA accent colour.** Module 3 suggests a warm complementary accent for the CTA; module 8 says the accent is the "fix" motif and should peak at the CTA. [3 B.7#7, 8 B.7#11]
    **Default:** keep the style accent (`colors.accent`; green in preset `profitcast-dark`) for series consistency, with no warm CTA accent unless your inspirations use one. GFX-21 is a WARNING.

14. **Wardrobe for future shoots.** On the test footage an olive shirt on a warm wall leaves no blue near the skin; a blue, teal or denim top is the cheapest upgrade. [8 B.2, 8 B.7#1]
    **Default:** add it to the shoot brief. Never key or recolour the shirt in post.

15. **Delivery resolution.** The brief said 1080×1920; reportedly, Meta recommends 1440×2560 for Reels ads, and a 1728×3072 source could support it without upscaling. [9 B.7#7]
    **Default:** deliver at style `platform.size` (default 1080×1920; templates are designed in 1080×1920 and other sizes are reframes). A 1440×2560 master only if you ask for one.

16. **Caption details.** The open points are 1 line vs 2, weight (Medium/Semibold vs Regular) and a minimum size (cap height ≥ 40 px, DERIVED). [9 B.7#3–4, 3 B.7#3]
    **Default:** ≤ 2 lines (target 1, ≤ 32 characters), Medium weight, cap height ≥ 40 px. Confirm all three against your inspirations.

17. **Music: one track or a switch at the turn.** [4 B.7#10, 4.5, 4.6]
    **Default:** one track with an energy or arrangement lift at the problem → solution turn; no hard switch.

18. **Rotoscope budget.** ES allows ≤ 4 moments of ≤ 3 s each; the feedback note in memory says 1–2. [ES §1, USER memory]
    **Default:** cap at 4 (GFX-25), aim for 1–2.

19. **Motion tokens and spotlight counts.** The durations, distances, the "≤ 1 mover" count, the hold before a hero and the shake threshold were proposed during the first test (style `motion:` now holds them). [1 B.7#16]
    **Default:** measure them frame by frame on your inspiration renders. Until then, MOT-06/09/10/11 report as CALIBRATE.

20. **Opacity easing.** No source covers it. [1 B.7#3]
    **Default:** alpha follows the same eased progress as position; linear alpha only for fades of 4 f or less.

21. **Louder bed on request.** Module 5's level figures would allow up to about −5/−4 LU under the voice. [5 B.7#1]
    **Default:** stay at the style's `sound.bed_lu`. Go louder only when you ask, and only if the words gate passes and the voice-band carve is deepened.

22. **Client-community colour checks.** 3.7 notes that colour meanings vary by culture (white = mourning in parts of Asia). [3 B.7#8]
    **Default:** ask about colour taboos in each brief; avoid all-white full-frame cards.

23. **Blink-aware cutting.** It needs an eyelid landmark model, which the toolchain doesn't have. [2 B.7, 2 Q16]
    **Default:** skip it; CUT-12 stays as future work.

24. **Visible "authentic" imperfections vs the designed look.** Module 4.8 and 6.9 favour lowercase type, imperfect takes and "not over-produced". [4 B.7#5, 6 B.7#11]
    **Default:** the client's measured look (their inspirations, via the style profile) wins. Keep only one natural delivery moment; never lower technical quality.

25. **Source frame rate and extreme-punch resolution.** 9.5 exports at 30 fps; CVES renders at the source rate. 7 B.7#8 worried that the 1.55× punch would upscale, but the test raws were 1728×3072, which supports up to 1.6×. [9 B.7#8, 7 B.7#8]
    **Default:** keep the source frame rate (style `platform.fps: source`) with no conversion; probe each new shoot and cap zoom at source height ÷ 1920 (FRAME-11).

## Resolved while building viral mode (2026-11-19, builder's call; the owner asked for v0.3 without further questions)
These start as defaults in `styles/default.yaml` / `styles/viral.yaml` and can be re-measured per client (`cves inspire`, retention data). New gates start as WARN unless the fault is objective.
- **Goal switch.** `edit.yaml goal: ad | viral` (default ad). Viral layers `styles/viral.yaml` right after `default.yaml`, so a preset, the client's inspirations, the brand and edit.yaml still win. Ads keep every v0.2 behaviour; RET-25, RET-28 and RET-29 are not run for ads.
- **RET-24 hook change:** first pattern interrupt by `structure.hook_change_s` 1.5 s (ad) / 1.0 s (viral). WARN: RET-09 already blocks the first visual event at 1.0 s on frame difference; RET-24 adds timeline and element-log events.
- **RET-25 hook text or subject:** by `retention.hook_subject_s` 1.0 s (viral). WARN: "strong subject" is a heuristic (the A-roll face, or a centre with ≥ 1.5× the border's Laplacian detail and contrast ≥ 20).
- **RET-26 interrupt gap:** `rhythm.interrupt_max_s` 4.0 s (ad, = `grammar.max_shot_s`) / 2.5 s (viral). WARN.
- **RET-27 effect soup:** gaps under `rhythm.interrupt_min_s` 0.3 s (viral 0.25 s) sustained for `retention.soup_window_s` 1.5 s. A list stagger (< 1 s) never trips it. WARN. Events within `retention.merge_s` 0.05 s are one interrupt; a picture change is a frame step ≥ `retention.scene_diff` 12 (0-255 luma, 96 px decode).
- **RET-28 loop seam:** SSIM ≥ `retention.loop_min_similarity` 0.6 over the last / first `retention.loop_seam_s` 0.3 s and last / first frame; only with `structure.loop: true`. WARN (PLAT-13 is the advisory version for every edit).
- **RET-29 payoff:** a picture step ≥ max(12, body p90), a graphic entry, or an audio peak ≥ body median + `retention.payoff_rise_db` 3 dB in the last `structure.payoff_window` 20 %. WARN.
- **RET-30 platform duration:** FAIL above the platform's maximum (objective: the platform cuts or refuses the post), WARN outside the ideal band. Bands in `styles/platforms.yaml` (ideal bands are HOUSE; maxima are the platforms' published limits as of 2026-11).
- **RET-31 dead air:** no 50 ms window above `retention.dead_air_db` −45 dBFS for more than `retention.dead_air_s` 0.6 s. FAIL for viral (objective: a silent stretch loses the scroll), WARN for ads (SND-13 remains the ad gate, unchanged).
- **RET-32 guide / beat alignment:** ≥ `retention.guide_on_beat_min` 60 % of cuts within `music.snap_tolerance_s` of a beat. WARN; FAIL only when `music.slot: platform` has no usable guide or no guide stem.
- **Platform safe zones** are fractions of the frame in `styles/platforms.yaml`. `reels` equals the v0.2 Meta zone (x 65-1015, y 269-1248 on 1080×1920); TikTok / Shorts clear the right rail and the bottom caption area; values without a published number are the builder's call. With no `platform.target` the v0.2 `platform.safe_zone` applies, scaled to the frame.
- **Platform sound slot:** organic posts may be cut to a trending sound that the app licenses; the master then has no music (SND-04 checks the stem is silent), the delivery adds the guide stem and POSTING.md. Ads may never use it (validation error), which keeps §0.12 intact.
- **RET-08 vs the "wait for it" hook:** the spoken phrase stays banned; the playbook's "wait for it" hook is shown (a visible timer or half-built object), never said.

## Senior sound (2026-11-19, builder's call for v0.4 WS H; the owner approved the v0.4 plan and opted out of questions)
- **SND-32 riser resolve and SND-33 music section on the story beat start as WARN.** Both judge the new automatic layer (accents, phrase alignment) on synthetic demos only; they become BLOCKING after they have been read on real jobs without false alarms. Thresholds: SND-32 = 1 frame (the SND-07 bar); SND-33 = `sound.phrase_tolerance_s` 0.05 s (just over a frame at 25 fps) and every loop seam on a downbeat.
- **SND-33 trusts a hand-set drop.** With `music.sync: off` and `music.drop_track` set, the person's drop counts as the section change when the analysis finds a drop within one bar of it; the difference is reported ("check by ear"). On the synthetic demo bed the tracker puts the drop 274 ms after the real one (the pad's 0.3 s attack makes a second onset per bar), so judging the analysis over the hand-set value would be a false alarm.
- **Automatic risers are judged by SND-32, not SND-08.** SND-08 is about transition whooshes peaking on their cut; an automatic riser (cue kw `accent: riser`) peaks on its story target, which can sit a few frames from a cutaway's transition. SND-07 still judges it (peak within 1 f of a picture event), so nothing is loosened.
- **A riser needs a landing** (a sound already on its target, the music drop, or the impact placed with it). On the demo, earshot heard the riser out of the hook "resolve" into nothing (no onset within 100 ms of 3.47 s), so such a riser is skipped and logged.
- **Accents only on picture events.** An automatic riser / impact is placed only when its target is within 1 frame of a known cut, cutaway edge, end card or punch-in (else it is skipped and logged in `mix.json accents`), so SND-07 holds by construction.
- **Restraint budget for sound:** `creative.sound_accents_per_30s` 3 (payoff riser, payoff downbeat hit, hook riser, then reveal impacts in time order). Never on a moment that already has a riser / low hit of its own.
- **"Riser into the hook"** resolves on the hook's start when there is at least `sound.accents.riser_min_s` before it (a cold open); on the usual ad, where the hook is the first frame, it resolves where the hook hands over to the body (the end of the H clips).
- **Envelope ducking is the default (`mix.duck_mode: envelope`).** Depth is unchanged (`sound.duck_voice_band_db` −8 in the voice band, `duck_other_db` −3 elsewhere) and reached from 6 dB under the voice's loud level; attack 40 ms; release = 1.25 × the measured syllable period, clamped to 250–400 ms. Between phrases the bed comes back instead of holding the dip. `gate` keeps the v0.3 behaviour. SND-04 still corrects the bed to `sound.bed_lu` after the duck, so the bed-vs-voice level is unchanged.
- **The house SFX added in v0.4 are synthesized, not downloaded.** Fifteen sounds (risers, impacts, whooshes, pops, a tick, a room tone) are made by `tools/make_sfx.py` (CC0, synthesized by CVES), so their licence needs no source-page check. earshot reads them as the right kind of sound (impacts as kick / sub drop / drum hit, whooshes as whoosh / whip pan, risers as uplifter sweeps) but "likely code-synthesized" (p_real 0.03-0.3); so SFX-METHOD rule 3 (real over synthetic) is kept by ranking: `sfx.pick` takes a recording over a synthesized sound at the same intensity (the payoff riser is the recorded `riser`). Automatic impacts must be hits: onset to peak within `sound.accents.impact_attack_max_s` 30 ms. earshot heard no hit on the payoff when the recorded `boom` (a 0.45 s swell) was used, so the payoff hit is the synthesized `impact_hit` until a punchy CC0 recording is added, and the synthesized sounds fill the roles the recordings don't cover (a soft riser, short resolving risers, soft impacts). Users grow the bank with real CC0 recordings through `cves sfx fetch`.

## Already resolved by your own feedback (these win over the videos)
- **The bed level is the client's call, stored in the style profile** (`sound.bed_lu`, default −10 LU). The first reviewer rejected −23, −14 and −10 LU as too quiet (−23 read as "no BGM") and settled at −7 LU, now the `profitcast-dark` value. Module 5's own figures support a loud bed; the condition is that the words gate passes. [ES §3, USER]
- **No added grain**, one decode and one encode, no `tune film`. v1 was rejected partly for grain. [ES §2, USER]
- **Every edit snapped to a segment boundary**: a one-frame flash of the next take counts as a jump cut. [ES §2, USER]
- **No generative voice enhancement.** Resemble Enhance changed "posts" → "course" and "rank" → "learn". Connectors are therefore fixed by take choice or re-ordering only. [ES §3, 6 B.7#5]
- **Verbatim stutter check on every clip** after "want, want to show" slipped through. [ES §4, USER]
- **Material icons only**, after the hand-drawn phone icon. [ES §1, USER]
- **Complete sign-off** (the whole brand name), after it was cut short. [ES §4, USER]
- **Colour tags `tv/bt709/bt709/bt709`** on the delivered file, after v3c shipped untagged. [ES §4, 8 F1]
- **Inspirations are the style spec**, even where they overrule a module. Always: hidden jump cuts (no vlog-style visible jumps, [2 B.7#1, 7 B.7#2]); no full-length effects over the face; no "aura". For the first test client the inspirations also meant small sentence-case captions with no CapCut pills (over 4.8's style), a warm, moody A-roll (over 8.8's teal-and-orange) and a black/green series look rather than a literal 60-30-10 [8 B.7#2]; those choices are now preset `profitcast-dark`, and each new client's come from `cves inspire`. [USER, ES §1–2]
- **No pause over 0.25 s** (over the long-form holds in 4.5, 4.8 and 6.6). [ES §3, USER]
- **Nothing appears before it's said**: anticipation stays inside an element's own window; a teaser moves only the spoken line. [ES §1, 1 B.7#1, 6 B.7#1]

## Resolved while building the engine (2026-11-18, tested on the first test ad)
- **Key information goes in cutaways, not on the chest.** On close selfies the chin sits at y 1150–1280, so there is no room for a graphic between the chin and the Reels safe line (y 1248) without covering the face. Prices, CTAs and key numbers are full-screen cutaways (e.g. `counter` with a currency `prefix`). Cutaways may start mid-shot (`snap: false`) when the beat begins on a word. PLAT-02 blocks only prices, pills and end-card elements.
- **Chest brand elements (client wordmark, logo lockup) sit under the chin with natural framing.** Below y 1248 they WARN, not FAIL; the end card carries the in-zone logo.
- **No automatic "lift" reframing.** Anchoring the punch-in at the frame bottom to make room under the chin cropped the head and forehead (rejected on the moodboard). It is opt-in only (`aroll.lift: true`), for loose framings.
- **Punch-in levels** come from style `framing.zoom_levels` (default 1.0 / 1.18 / 1.38). Every direct cut steps ≥ `framing.min_step` (default 1.15×) with creep counted, and stays below the 1.4× "extreme" line (FRAME-09 allows exactly one).
- **Captions** (default `captions.position: chin`) sit just under the chin, inside the Reels zone where the framing allows; when it doesn't, they WARN rather than move over the face.

## Inspire v2 thresholds (2026-11-19, builder's call for v0.3 WS B; measurements only, no gate reads them yet)
The owner asked for v0.3 to be built without further questions, so these are the builder's starting values, checked on
synthetic references (tests/test_inspire_v2.py) and on four real reference reels. Change them here first, then in the code.
- **Cut on the beat** = within ±2 frames of a beat of the reference's own music (`inspire_feel.BEAT_TOL_F`). `music.sync: cuts` is written when the share is ≥ 0.6 **and** ≥ 2× the chance level for that tempo (`SYNC_CUTS_MIN`).
- **Speech** = 1 s windows whose voice-band harmonic envelope has ≥ 2.2 dB of 3–8 Hz modulation (`inspire_audio.VOICE_MOD_DB`); a reference has a voice when that covers ≥ 1.5 s and ≥ 15% of its audible time.
- **Music bed** = median of the 0.5 s window minima under speech + the min-to-mean offset measured on the same reference's music-only stretches, else 6 dB (`BED_BIAS_DB`). Music counts as present under the voice when that bed is within 35 dB of the voice.
- **Silence / drop-out** = ≥ 25 dB under the running 2 s median for ≥ 0.15 s, ignoring the first and last 0.3 s (`SILENCE_DROP_DB`). **SFX** = onsets off the beat and half-beat grid by > 60 ms (`ONBEAT_S`), above p75 of the onsets (p95 of the onset strength inside speech).
- **Loop** = the last-vs-first frame difference (the cut detector's metric) is < 0.15 and ≤ 3× the reference's median frame step (floor 0.03) (`LOOP_*`). **Zoom jump** = face height changes ≥ 8% between samples without a cut (`SCALE_JUMP`).
- **Mix and match**: a dimension whose references agree at consistency ≥ 0.6 is pooled; below that ONE reference is picked (rank × weight × distinctiveness × confidence) instead of an average (`inspire_mix.AGREE`). A pick the person forced (`--mix`, `refs.yaml use:`) is written down to confidence 0.2 (`FORCED_MIN_CONF`).
- **Aesthetics** (grain, tone curve, saturation, temperature, vignette, letterbox, aspect) are notes in `_inspire.aesthetics`, not style keys: no added grain stays the rule (above), and the canvas is the brief's call.


## v0.4 weak spots (2026-11-19, builder's call for WS J)
- **PLAT-10 plate margin** is 26 px **at a 1080 short side** (`26 * max(1, U)`), like the cap-height line next to it. The caption shadow (blur and offset) already scales by `U`, so on a 3840x2160 master the unscaled 26 px flagged every caption (29 px) with no plate. Identical at 1080 and below.
- **GFX-15 sampling**: text contrast is measured on frames whose bbox is static on both sides (as GFX-08), not just against the previous frame. Thresholds unchanged.

## v0.4 integration (2026-11-19, builder's call)
- **Captions during a snap punch-in.** The renderer hid captions for the whole snap window even when nothing replaced them, so a bare punch-in dropped spoken words off screen. Captions now hide in the snap only where the segment has roto type (which takes their place). QC's `cap_allowed` mirrors this, and RET-12 only counts a caption keyword on a frame where the caption is really drawn (before, a keyword hidden by the snap or a chest graphic could pass it).
- **The stock demo passes its own QC** (it failed FRAME-03, GFX-15, RET-09 and RET-12 since v0.2): relight on (dehalo, wall unchanged), a 1.25x punch-in at 0.45 s, and the lower third moved after the topic word as a card on the sweater. Golden frames `roto_word` and `aroll_lower_third` were regenerated for it. No gate threshold changed.
- **`lower_third` card style**: the accent bar sits on the card's left edge (it was 8 px inside, a GFX-08 near-alignment). **`kinetic_caption_emphasis`** fits its word at rest with room for the hold, then scales the entry from there, so a long word no longer ends past the safe zone.

## v0.4 story step (2026-11-19, builder's call from the first real job)
- **Take alignment trusts DTW token times, then the energy.** whisper.cpp `-ml 1` segment times on a short window stretch the first word to the window start and the last to its end (seen on every clip of the first real job), so `cves select` uses `--dtw` token times (flash attention off, which DTW needs) and falls back to segment times only without a DTW preset. Edges then snap to the nearest pause (quieter than the window's p10 + 12 dB, at least 60 ms), preferring a pause before the first word's estimate and after the last word's (DTW onsets run late). Pads 0.04 s before / 0.08 s after, never past the middle of the pause.
- **Three passes, pooled.** Windows of 1.5 s x 1 / 0.8 / 1.2 around the hand times; whisper output changes with the window edge. Agreeing estimates (within 0.3 s) take the median; disagreeing ones take the one nearest the hand time (the hand time says which take was meant). A pass whose matched run jumps over > 1 s of mostly speech (whisper merged two takes of a repeated line) is outvoted by any clean pass; when every pass merged, the report says to check that clip by ear. Match score < 0.8 keeps the hand times. On the first real job, hand times moved 0.4 s into the words came back to the same pauses on all 12 clips; hand times widened by 1 s into the neighbouring takes came back on 11 of 12 (the miss: a clip whose widened in sat on an earlier take of the identical line, flagged as merged,; one out landed in an earlier pause, still after the last word).
- **`selects.yaml` stays the input.** Alignment writes the aligned times to `edl.json` only (with the hand times), so re-running `cves select` re-aligns from the hand times and the cache makes it cheap.
- **STORY-17, not STORY-14.** STORY-14 is the loops gate in QC-GATES.md; the word-recall gate took the next free STORY id. Recall >= 0.85 per clip (BLOCKING): one misheard word in a 10-word clip (whisper hears "aligner" as "Alena") passes, two lost words fail. Recall alone let the first real job's failure through (a lost "We've" = 86 %, a lost final "refund" = 90 %), so a missing first or last word fails on its own (`qc.words_edges: true`): edge words are lost by clipping, mishearings land mid-clip. Each clip is transcribed on its own span with 0.08 s context; a whole-file transcript is never used, since it skipped a sentence that was in the cut.
- **Structures.** `offer` = H M PR R C, `story` = H S T PR C (S setup / before, T turn / the moment it changed). Music turn and drop per structure: problem P/A and PR/O (unchanged), offer M and PR, story T and PR. A custom `grammar.beats` that equals a preset gets that preset's music beats; otherwise hook = H, turn = its P/A/M/S/T beats, drop = its PR/O beats. STORY-07 for `offer` checks the risk reversal after the proof (the ask comes after the evidence); STORY-13 (problem by 25 %) runs only where a P beat exists.
## AV fixes from the first 60 fps job (2026-11-19, builder's call; no gate threshold changed)
The first real client job (40 s, 1080x1920, 60 fps, 12 takes over ~2.5 min while the room light drifted) failed SND-07,
SND-19, COL-06, COL-07, flashed two captions for 1-4 frames (PLAT-06 / 07) and the review found the music masking the voice.
The owner asked for the causes to be fixed in the engine; these are the builder's calls.
- **Cue sync is post-render and event-based, not a tuned offset.** A cue's audible anchor (onset at 10 % of the 10 ms RMS
  peak, the SND-07 measure; a riser's peak) is moved onto the nearest picture event within 6 frames of the template's time.
  Logged elements and cuts win over pixel onsets; a pixel onset counts only at >= 40 quarter-res px (weak 12-20 px onsets
  differ between the rendered PNG and the encoded master, which is what the gate decodes). Templates whose sound belongs
  to an unlogged drawn state should log it as a part (done for `m_list_build`'s mark).
- **Caption fragments: merge, hold or skip, never lose readable words.** `captions.min_on_s` is 0.83 s, PLAT-07's own
  line. Only fragments made by a cover (cutaway, snap with roto, hide window, end card) are resolved; a naturally short
  event that touches no cover is left alone (shortening speech is not the scheduler's job). A merge must fit the style's
  max_chars / measured lines and cross no sentence end; otherwise the fragment is kept (short beats lost words), unless
  every word of it was spoken under the cover (then it is skipped: it was never readable in time).
- **Voice gate: expander, measured on the tightened voice.** The take's long pauses are useless for the floor:
  DeepFilterNet pulls them to -80 dB while the short gaps between words keep the room and reverb tail at -40..-50 dB; that
  residual is what SND-19 hears. Timing (15 ms hold, 40 ms release) is short because the tightened gaps are 20-60 ms; a
  ratio-6 expander instead of a switch keeps word tails continuous. earshot A/B on the test ad: "neither closer to
  'speech with word endings cut off abruptly'", B "cleaner (noise floor -59 vs -49 dBFS)"; AudioSet's "speech
  synthesizer" score rises with any deep gate (0.66 -> 0.77), the price of a -60 dB floor between words.
- **Colour match: per-channel gain, subject and wall separately, no offset.** A gain + offset fit on (skin, wall) was tried
  first: with a pale wall at the skin's level the two anchors are nearly equal, the fit is ill-conditioned, and its offset
  lifts or crushes the blacks (muddy). Skin and wall also drift apart between takes (the presenter moves in the window light,
  the wall does not), so one gain per frame cannot match both. The subject's gain comes from the skin, the wall's from the
  wall, blended through the matte and limited to 0.18 log apart. Reference default `hook` (the first impression; on the
  test ad it also needed the least residual), drift followed at 0.5 with 0.8 s smoothing: the light drift is followed, a
  head turn is not (chasing it pumps the whole frame).
- **What the colour match cannot fix: a head turn on a cut frame.** On the test ad COL-06 still sees the first frames of
  `c_cta_0` (head turned into the window light) and the last of `m_target_0`. That is pose, not colour: correcting it would
  pump the exposure for a third of a second. The fix is editorial (start / end those takes a few frames later), so the
  gate keeps failing until the cut moves.
- **Masking guard targets the review's own measure** (1-4 kHz, 0.4 s Hann windows over words, ffmpeg's `-ac 1` downmix,
  which reads a centred stereo bed 3 dB hotter than an L/R average) with a 2 dB margin, trimming only the bed's speech
  band, at most 12 dB, and only while a word needs it.

