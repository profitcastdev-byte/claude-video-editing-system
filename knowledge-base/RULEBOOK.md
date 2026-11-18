# CVES Rulebook

Read this file first in every editing session, together with `knowledge-base/EDIT-STANDARD.md` (ES) and the client's style profile (`STYLE.md`, `Edit/style.yaml`; schema in `docs/STYLE.md`). It covers talking-head selfie videos and ads (typically 30–60 s paid social ads such as Meta Reels), designed at 1080×1920 for 9:16; other ratios are reframes of that master.

**Precedence.** (1) **USER**: corrections the user has confirmed (ES, plus the auto-memory feedback notes). (2) **STYLE**: the client's style profile, for every per-client choice (palette, grade, captions, transition kinds, pacing bands, bed level). (3) **ES**: the edit standard. (4) Module rules from the curriculum videos, cited by video id `[x.y]` or module section `[5 B.7]`. When sources conflict, the higher one wins. Open conflicts are in `DECISIONS.md` (marked **(D)** here); their recommended default applies until the user answers.

**Measured rules vs per-client choices.** Most rules below are universal best practice distilled from the curriculum and stay rules. Where a rule names a number that is a per-client choice, the value comes from the style profile and the QC gate reads its threshold from there; the number given here is the default from `engine/cves/styles/default.yaml` or, where marked, the example preset `profitcast-dark`.

**Labels** carried from the modules: **HOUSE** (a number proposed while the system was first tested; now a style default or preset value), **DERIVED** (a number translated from a qualitative rule), **NORM** (a named industry norm), **CALIBRATE** (measure it on the user's inspiration edits before it can block). Gate ids such as `CUT-05` refer to `QC-GATES.md`.

---

## 0. Non-negotiables (USER-confirmed)
1. The user's own inspiration edits are the style spec. Measure them (`cves inspire` → `Edit/style.yaml`), study them frame by frame before designing, and never replace their look with your own pick or with a preset. [USER, ES]
2. The music bed level is the client's choice: style `sound.bed_lu` (default −10 LU). Set it from the inspirations or the user's notes and never lower it to make a gate pass. (The first reviewer rejected −23, −14 and −10 LU as too quiet and settled at −7 LU, the `profitcast-dark` value.) [USER, ES §3]
3. No added grain. One decode and one encode. [USER, ES §2]
4. Snap every edit, cutaway and transition to an exact segment boundary. A one-frame flash of the next take is a jump cut. [USER, ES §2]
5. No generative voice enhancement (Resemble Enhance full mode rewrote words). Every voice process must pass the words gate. [USER, ES §3]
6. Check every kept clip for stutters, verbatim (`cves qc` (CUT-03)). Whisper hides disfluencies. [USER, ES §4]
7. Icons come from the Material set in `Assets/Icons/` only. Never draw icons by hand. [USER, ES §1]
8. Keep the complete sign-off (the whole brand name, listed in `qc.brand_tail`). Never cut it short. [USER, ES §4]
9. Tag the delivered file's colour as `tv / bt709 / bt709 / bt709` (an early test version shipped without the tags). [USER, ES §4]
10. Objective faults must never reach the user. Run every gate before sending anything. [USER]
11. Only **published, verifiable** proof goes on screen (client names, numbers, prices). List each claim and its source in `Brand/claims.md`; anything unpublished stays off screen. [USER, brand book]
12. Paid ads use only **licensed** music: CC0 / CC BY with credit (Openverse), or ElevenLabs / Magnific generation. Never a commercial track without rights. [USER]
13. Never put the presenter's face inside a graphic, never cut the body off inside the frame (no plate shrink), and never put text over the face. [USER, LESSONS 5–7]
14. Prices, CTAs and key numbers go in full-screen cutaways, not on the chest. On close selfies there is no room between chin and the Reels safe line. [LESSONS 25–26]

## 1. Brief and setup
- Write down the ad's emotion in one line, and the viewer's **want plus obstacle** (for example, "calls go to competitors"). [2.1, 6.1]
- Confirm a real, specific proof exists: a client name and a number. If it doesn't, flag it to the client before cutting. [6.8, 6.7, 4.6]
- Mark the sound moments in the brief: the hook hit, the first cutaway, the offer reveal and the CTA. [5.7, 5.1]
- Shoot brief: phone at eye level; white balance and exposure locked; a blue, teal or denim top (or a blue object behind the speaker) to complement skin; a known neutral in frame. [7.3, 8.8, 8.5, 8.4]
- Probe the source with ffprobe (colour tags, resolution, fps). iPhone raws are often HEVC 1728×3072 at 23.976 fps with extra metadata tracks; map only `v:0` and `a:0`. Render at the source frame rate and never convert it. [8.4, 9 B.7#8, USER memory]
- Per client: check for colour taboos in the target community, and confirm any scarcity or bonus is real. [3.7, 6.9, 4.7]
- Instrument before editing: store YuNet landmarks as well as boxes, and make the renderer write a per-frame element log (bbox, transform, alpha, font, role, tags). Most gates read it. [1 B.5.3, 3 B.5, 7 B.5]

## 2. Story and selects
- Transcribe with whisper word timings. Segment into sentences, group re-takes, and keep the **last complete take that passes `cves qc` (CUT-03)**. [6 B.2.4, 6.2, ES]
- Pick takes for warmth and energy (smile, enthusiasm) as well as word accuracy. [4.2, 4.6]
- Label every sentence H / P / A / PR / O / C / X (hook, problem, agitation, proof, offer, CTA, cut). **Work backwards**: lock the complete sign-off first, then the offer, then the problems the offer pays off, then the proof, and choose the hook last. [6.1, 6.7]
- Order the beats H→P→A→PR→O→C. Join every boundary with *therefore* or *but*, never *and then*. Fix a weak connector only by choosing another take or re-ordering, never by synthesising speech. [6.3, 6 B.7#5, ES §3]
- Hook: first word within 0.25 s; the topic named within 2 s; a "you/your" pain; a contrast (A vs B); finished by about 5–6 s. No greeting, no credentials and no vague suspense ("watch till the end"). [4.1, 9.8, 9.5, 4.6]
- Nothing that is background sits before the problem beat. [6.9]
- Ration information: reveal the mechanism after the problem; start the proof by 50% of runtime with its number landing by 55%; put the price after the proof; say the brand last. A teaser of the proof number may open the ad only as a spoken line moved up. **(D)** [6 B.2.3, 6.1, 4 B.7#1]
- Write a setup→payoff table: every problem item is answered by an offer item, and vice versa. Cut orphans. [6.7, 6.6]
- Every sentence adds a new idea. Keep one-kind lists to 4 items or fewer per beat; prefer 3. [4.6, 6.3, 3.2]
- Close every loop you open before the CTA. End on the most positive line plus the brand, not on the fear. [4.2, 6.5, 6.9]
- Use only honest stakes. No fake urgency or invented scarcity. [4.7, 6.9]
- The user approves the cut list. The words-gate reference is the **re-ordered selects script**, not the raw order. [6 B.7#4]

## 3. Edit plan (`edit.yaml`)
- Tie every element to a word timestamp and tag it: beat, role, intent (primary / secondary / context), hero, problem / solution, proof, loop open / close. [6 B.5, 4 B.5, 7.8, 8.3]
- Rhythm: A-roll shots 2–4 s (style `grammar.max_shot_s`, default 4), cutaways 3–8 s (`grammar.max_cutaway_s`, default 8). The share of runtime on cutaways is the client's: `grammar.cutaway_share` (e.g. 40–55% in `profitcast-dark`; not enforced by default). Never more than `grammar.max_cutaway_s` without the face. [ES §1, 2.8]
- Shape the pace: set a baseline average shot length, then deviate on purpose. Build → burst → release: the longest hold of a section comes just before the fastest run (usually the list), and the CTA is cut slower than the baseline. At least one tempo change; never a metronome. [2.5, 2.6, 4.5, 4.8]
- Put a visual event at least every 4 s (every 2.5 s in the first 6 s). In the hook, something changes about every 1.5 s: a cut, a punch step, a caption page or a build step. CALIBRATE. [4 R7, 6.9]
- Hide every A-roll jump cut: alternate framing by **≥ style `framing.min_step` (default 1.15×), measured at the cut frames** (zoom creep included), or cover the cut with a cutaway. Cut on head or hand motion, never on a still pose. **(D)** [ES §1, 2.1, 2.4, 7.5]
- Cut on the completed thought at word boundaries. The voice continues under cutaways (L/J). Audio may lead picture by 2–4 f on A-roll joins; picture never flashes the next take. [2.1, 2.2, 9.7, ES §2]
- Transitions carry meaning. The hard cut is the default. The kinds into and out of cutaways come from style `transitions.in` / `transitions.out` (cut, whip, glitch, fade; e.g. `profitcast-dark` uses a zoom-blur whip for momentum into a cutaway and glitch lines out). One extreme punch-in (`framing.extreme_max`) marks the key line or turn. No dissolves, wipes or irises inside the ad, and no fades unless the client's style uses them. [2.3, 2.4, 7.2, ES §1]
- Give the proof boundary the strongest visual change in the cut. [6.6]
- Rotoscoping is a spice: at most `grammar.roto_max` moments (default 4), each 3 s or shorter (aim for 1–2). **(D)** [ES §1, USER memory]
- Speech outranks music. Sync to the beat only for cutaway entries and graphic hits, and only when a word boundary allows it. [2.1, 2.5, 9.2]

## 4. Moodboard
- Render **true-replica keyframes with the production renderer** (`cves render`, `gfx.py`, `look.py`) at full resolution: frame 0, a hook frame, each cutaway type at its settle frame, one roto moment, and the CTA or end card. No mock-ups in other tools. [workflow; 1 B.1#18]
- Put them side by side with the inspiration frames. Match the client's series look as the style profile records it (`stage:`, `colors:`, cards; e.g. `profitcast-dark`: black stage, green dot grid, glow rising from the bottom, green and white type, UI cards with icon wells, check / ✕ states, corner brackets). [ES §2, 3.1, 4.2]
- Every paused frame must look designed. [4.3, 1.8]
- The user approves the keyframes before the full render.

## 5. Graphics and motion
**Graphics**
- Nothing appears before it is said. Each item lands 0 to +6 f after its keyword, and the number of items shown matches the number spoken. Numbers count up; lists build line by line. [ES §1, 2.8, 7.8, 4.5]
- Every cutaway illustrates its own line. No "wallpaper" cutaways that exist only to hide a cut. [7.8, 2.2, 4.3]
- Hierarchy: exactly one L1 element per frame and no more than 3 levels. Step type size ×2 (×3–4 for a hero word) and skip a weight. Use one sans family; the client's wordmark is an image, not a second font. [3.1, 3.4, 3.3, 3 B.7#4]
- One alignment axis per card, measured on ink bounds: left for multi-line cards, centre for captions. [3.4, 3.5]
- Gaps inside a group are smaller than gaps between groups. Take every gap from one spacing scale (8/16/32/64 px, DERIVED). [3.5, 3.6]
- Colour carries meaning: the style accent (`colors.accent`; green in `profitcast-dark`) is "the fix" and marks the spoken item or CTA only; a ✕ in the text colour is the problem; `colors.gold` (or the client's brand colour) is the client wordmark. Keep the roles fixed for the whole video. [3.1, 7.6, 8.6, 8.3]
- Use real client logos and wordmarks in proper typography. [ES §1]
- Text contrast is at least 4.5:1 (3:1 for large display type), measured on final frames (NORM, WCAG). No widows, no double spaces, no justified text. [3.1, 3.4]
- One idea per cutaway. The CTA frame is the most spacious. [3.6, 3.1]

**Motion**
- Ease by the force story. Entries use `ease_out`; exits use `ease_in` and are no longer than the entry; repositions use `ease_io`; pops use `back` with ≤ 10% overshoot (NORM, Penner) that settles in 3 f or fewer. Linear motion only for typewriter, line draw-on, drift and sweep. [1.1–1.8]
- Use the motion tokens (style `motion:`; frame counts below are at 23.976 fps, scale them to the source rate) (HOUSE, CALIBRATE): card 7 f / 50 px, panel 8–9 f, pop 5–7 f, slam 3–4 f, exit 5 f, count-up 18 f, sibling stagger 3 f. Snap starts and durations to whole frames. [1 B.5.1, 1 F2]
- One primary mover at a time (one graphic on A-roll). Siblings share a token and are offset in time. [1.6, 1.2, 7.6]
- Every element has an origin (it grows, slides or is revealed) and a defined exit. [1.6]
- Give hero beats (price, the big number, the logo) a calm hold first. Anticipation is for heroes only, and only inside the element's own word window. [1.1, 1.5, 1 B.7#1]
- Any hold longer than 1 s keeps moving (slow push or drift). [1.2, 4.8]
- Moves faster than 4 px/frame get motion blur along their velocity, at about 0.5× the per-frame displacement. Zoom whips get radial blur, never a vertical smear. [1.7, NORM 180° shutter]
- No shake: give the punch-in centre one fixed point per segment (or a zero-phase smoothing filter). Render scaled text once and then transform it. [1.3, 1 F1, F13]
- Number + unit and other compound text move as one parent. [1.6]
- Check face clearance and safe zones on every animation frame, including start offsets and overshoot peaks. [1 B.7#11]
- After a whip, either show the full entry or make sure something visibly settles in the first 6 f. **(D)** [1 F12]

## 6. Framing
- The face is the L1 element and the brightest large region on A-roll. Overlays are dimmer or smaller than the face, and no more than one non-caption overlay sits on A-roll at a time. [7.1, 7.7]
- Centre the eye midpoint (45–55% of width) unless a graphic balances the other side. Eye line at 30–40% of height; headroom 4–12% of height. DERIVED, CALIBRATE. **(D)** [7.1, 7.7, 7 B.2]
- Shot size is the emphasis dial (style `framing.zoom_levels`, default 1.0 / 1.18 / 1.38): base framing for setup, a step up for claims, one extreme punch-in for the key line. Check the source supports the zoom (e.g. a 1728×3072 source gives up to 1.6× on a 1080×1920 master without upscaling). [7.2, 7.5, 7 B.7#8]
- Never rotate or mirror the A-roll. [7.1, 7.4]
- Eye trace: start the cutaway's first mover where the eyes were, and answer a glance or point with a graphic entering from that side. [7.6, 2.1, 7.5]
- When the style relights (`grade.relight`), darken the background with an edge-accurate matte (1 px erode, 3 px feather). A wide feather makes the "aura". The body leaves the frame only through its edges. [ES §2, USER]
- Open on the hook, and establish the business in the first cutaway. [7.2, 7 B.7#7]

## 7. Sound
- The voice is the priority. Use the podcast-mic chain: DeepFilterNet3, then EQ (high-pass about 80–100 Hz, cut resonances, keep the fundamental), de-ess, compressor, gentle expander. Keep the voice dry and centred: no reverb, no panning, no location ambience under it. [ES §3, 5.8, 5.6, 5 B.2]
- Keep dialogue level even: no sentence 5 LU or more off the median. [5.5]
- No gap over 0.25 s inside speech; trim breaths to 0.08–0.15 s. [ES §3, USER]
- Music sits at the style's bed level under the voice (`sound.bed_lu`: default −10 LU, −7 LU in `profitcast-dark`), measured over speech only. More than 2.5 LU quieter than the target fails, and more than 3 LU louder fails (SND-04); a louder bed also needs the words gate to pass plus a review. Duck by frequency split: voice band `sound.duck_voice_band_db` (default −8 dB, centred about 1–1.5 kHz, covering about 150 Hz–5 kHz), lows and highs `sound.duck_other_db` (default −3 dB), applied only while the voice is present. [USER, ES §3, 5.6, 5.5, 5.4]
- Let the bed swell toward voice level in no-speech spans of 1 s or more. CALIBRATE. [5.5]
- Music edit: enter with a reversed riser into a downbeat; edit on beats; no mood change inside the section used; end on a tail or an impact on the sign-off. No hard stop and no music on black. Use one track, with an energy lift rather than a hard switch. **(D)** [5.1, 5.4, 9.8, 4 B.7#10]
- SFX: real recordings in one clean UI/digital palette. Each transient lands on its event frame (±1 f), and risers peak on the cut. Every graphic event gets low-level sound. No more than 2 hero accents, layered low, mid and high. Use variants, never the same sample twice in a row. [5.1, 5.4, 5.2, ES §3]
- Land the music lift on the reaction to the proof number (0.2–1.0 s after it), not on the cut frame. CALIBRATE. [6.6]
- Make contrast with dynamics, never with silence: an optional short bed dip before the payoff. **(D)** [5.7, 4 B.7#3]
- Master at style `sound.master_lufs` (default −14 LUFS integrated; ES ±0.5; aim for −14.5 to −14.0 so it never goes over, **(D)**) and true peak ≤ `sound.true_peak` (default −1 dBTP), with the limiter as a safety net. Pre-limiter peaks ≤ −2 dBFS; master EQ boosts ≤ +5 dB. [ES §4, 5.5]
- Meters set the levels and ears finish the mix. Listen on a phone speaker and on headphones, run an earshot critique, and check stereo whooshes in mono. [5.5, 5.2, 5 B.7#6]

## 8. Colour
- Correct before grading: balance each segment on neutrals (wall, whites of the eyes), with any white-balance multiply in linear light. Never use global saturation as a fix. [8.5, 8.4]
- Skin is the reference: hue about 123° ± 8° (BT.709 Cb/Cr), stable across segments. Match on a face-core patch, never on whole-frame statistics. [8.5, 8.8, 8.4]
- No sudden dims and no desaturation jumps: skin ΔE ≤ 3 on a direct cut and ≤ 5 across a cutaway; exposure within ±6% / ±10%. Fix with a per-segment gain on the subject. **(D)** [ES §2, 8.4, NORM ΔE]
- The A-roll grade follows style `grade:` (e.g. `profitcast-dark` is warm, dark and moody; the default is neutral), always with natural skin. Use a monotonic S-curve; keep blacks lifted (16–24), never crushed; re-check saturation after any contrast change; apply the vignette last and softly. [ES §2, 8.7, 8.4]
- No teal split-tone on the A-roll unless the client's inspirations use one. Complementary contrast comes from the accent-coloured cutaways and from wardrobe. [8.8, 8 B.7#1]
- Cutaway palette (roles from style `stage:` / `colors:`): dominant stage/card areas ≥ 60%, accent ≤ 20%, white ≤ 10%, off-palette ≤ 2%, and at most one deliberate palette break (bounds HOUSE, CALIBRATE per client). The accent becomes more present toward the CTA. [8.6, 8.2, 8.3]
- No print LUT, no `tune film`; dither only gradient graphics. [ES §2, 8 B.7#8]
- Run the colour gates on decoded frames of the final encode, not on PNGs. [8 B.5]

## 9. Captions and platform
- Captions are always on (unless the style sets `captions.style: none` and the platform burns its own). Their look comes from style `captions:` (default: small, white, sentence case, up to 2 lines, soft shadow, words revealed as spoken). Aim for 1 line ≤ 32 characters, phrase-level chunks, and no pills unless the client's style uses a box. Synced within ±2 f, ≤ 20 characters/s, shown ≥ 0.83 s (NORM, Netflix). [ES §2, 9.5, 9.7, 4.8]
- Captions sit where style `captions.position` puts them (default just below the chin), always clear of the face, with their bottom edge inside the safe zone (y 1248 in the default Reels zone). **(D)** [9.5, 9 B.7#1, 3 B.7#2]
- All text, logos, prices and CTAs stay inside style `platform.safe_zone` (default the Meta Reels safe zone: x 65–1015, y 269–1248; NORM, Meta's 14/35/6%). `platform.margin` (default 60 px) is the minimum for everything. **(D)** [9.4, ES §4]
- Frame 0 shows the face or the hook text, already in motion. It is never black and never a logo sting, and it carries the look's brightest element so it stands out in the feed. [4.2, 9.8, 4 B.7#4]
- Design for sound off: the story must read from picture and captions alone. [2.7, 9.5]
- Ending: the brand is the last word, followed by a 0.1–0.5 s tail, or an end card of 3 s or less. No fade and no black, so the loop restarts cleanly. **(D)** [6.8, 9.8, 9.1]
- Native aspect for the platform, full bleed, no letterbox. Other ratios are reframes of the 1080×1920 master, never letterboxed copies. [9.1, 9.2]

## 10. Delivery
- Quality path: decode the raw once (10-bit FFV1), render lossless frames, encode once with x264 crf 16 and no `tune film`. Output at style `platform.size` (default 1080×1920), SAR 1:1, the source frame rate (constant), H.264 High yuv420p, AAC 48 kHz ≥ 128 kb/s, `+faststart`, within the brief's duration (`qc.duration`, else `platform.duration`). **(D)** [ES §2, 9.6, NORM Meta]
- Every BLOCKING gate passes, and every WARNING is listed in the report. [ES §4, QC-GATES]
- Make one contact sheet covering every transition and one face crop per segment, and check them frame by frame. [ES §4, 8.4]
- Watch four times on a phone: sound on, sound off, with the Reels UI overlay, and with fresh eyes. Render a review copy with a click on every cut (never in the delivery file). [2.1, 9.4, 6.2, 2.5]

## 11. Feedback loop
- Every note from the user becomes a rule here or in ES, or a value in the client's style profile, plus a gate, so the same mistake cannot recur. [USER]
- When a section feels wrong, look for the cause upstream first. [2.1]
- Don't re-cut what already passed. Change only failed gates or noted items. [6.6]
- Recalibrate the CALIBRATE gates on the inspiration edits, then on Meta retention and hold-rate data. Re-baseline the colour gates whenever a client's look is re-approved. [4.4, 6 B.7#8, 9 B.7#9, 8 B.5]

---

## Never do
(Beyond the non-negotiables in §0.)
- Show anything before its word, or a wallpaper cutaway, decorative motion or two primary movers. [ES §1, 7.8, 4.3, 1.6]
- Run effects over the face for the whole video, or widen the matte feather (aura). [USER, ES §2]
- Use plain mono text for client names, or CapCut pills and bouncing one-word captions unless the client's style asks for them. [USER, ES §2, 4.8]
- Use dissolves, wipes or irises inside the ad (or fades the client's style doesn't use), or end on black or with anything after the brand. [2.3, 9.8, 6.8]
- Overlap text with the face, or put text under the Reels UI. [ES §4, 9.4]
- Let music mask a word, or reverb or pan the voice. [5.6, 5 B.2]
- Use linear starts and stops, rubbery overshoot, shaking punch-ins, or rotated or mirrored A-roll. [1.3, 1.6, 7.4]
- Fix skin with global saturation, put teal shadows on the A-roll, or crush the blacks. [8.5, 8.7, 8.4]
- Invent stakes, scarcity or "watch till the end" hooks. [4.7, 4.1, 6.9]
