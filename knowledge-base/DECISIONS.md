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

