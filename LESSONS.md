# Lessons: every correction, and what it became

Each line is a real correction from the reviewer (or a fault the gates or moodboard caught) while building and testing the system
on its first ad, and how the system now prevents it. Lessons are written as general rules; numbers that are per-client choices
now come from the style profile (`docs/STYLE.md`). **Rule:** every new note becomes a rule here plus a gate or default in the engine, so nobody has to say it twice.

## Direction and taste
| # | Correction | Now enforced by |
|---|---|---|
| 1 | "Everything is templated, looks like Claude edited it." Rotoscope the presenter and animate behind them | Roto templates (`map_card`, `big_words`, `listing_card`, `top3_card`) |
| 2 | v1 "looks like someone with no experience did it": the client's inspiration edits had been overridden with a brand book's style | `EDIT-STANDARD.md` §1–2: the client's own inspiration edits are the style spec; `cves inspire` measures them into `Edit/style.yaml` before anything is designed |
| 3 | Rotoscoping everywhere looked sketchy; the reference edits used it as a spice | Roto moments capped by style `grammar.roto_max` (default 4), each ≤ 3 s (GFX-25); clean A-roll alternates with full-screen cutaways, in the cutaway-share band the style profile sets (`grammar.cutaway_share`, RET-22) |
| 4 | A gimmick neck ring, a client name set as plain mono text, and a sudden dark "aura" | Client names use a real wordmark template (or the client's own logo file), never plain text; no gimmick rings; any relight uses an edge-accurate matte (1 px erode, 3 px feather); a wide feather makes the aura |
| 5 | Never put the presenter's face inside graphics (the face-in-pin) | No face compositing into assets |
| 6 | The presenter's body must never be cut off inside the frame | The plate is never scaled below 1.0; punch-ins scale ≥ 1.0 and clamp to cover the frame |
| 7 | Text placement must be aesthetic; the search bar, dialog box and subtitles warped and overlapped | Captions placed by style `captions.position` (chin-aware by default), fixed line breaks, a margin from style `platform.margin` (default 60 px, PLAT-01), a face vs text check on every frame (FRAME-01) |
| 8 | The moodboard must be "perfect replicas" of the final frames | `cves moodboard` renders keyframes with the final renderer; the user approves before the full render |
| 9 | Wants a system that is right without correcting each thing | 84 automatically measured gates (`cves qc`, out of the 172 rules in QC-GATES.md); `cves deliver` and a hook block delivery while any FAIL remains |

## Sound
| # | Correction | Now enforced by |
|---|---|---|
| 10 | The voice must be crystal clear ("Adobe Podcast") | DeepFilterNet + EQ / de-ess / compressor / expander; voice floor ≤ −60 dBFS (SND-19) |
| 11 | Remove unwanted pauses | Pause tightening at selects; no gap > 0.25 s (CUT-02) |
| 12 | Resemble Enhance (generative) rewrote words: "posts" became "course", "rank" became "learn" | Generative voice models banned (SND-30); words gate against the raw (CUT-01) |
| 13 | "No BGM?", then "louder" twice | Music bed level set by the style profile (`sound.bed_lu`; −7 LU was this reviewer's choice, the default is −10), checked by SND-04, with frequency-split ducking and look-ahead (`library/SFX-METHOD.md`) |
| 14 | Use real SFX on the frame (Nick Saraev's method) | Template-emitted cues, CC0 / CC BY only, credits logged; see `library/SFX-METHOD.md` |
| 15 | A "Want, want to" stutter slipped through (Whisper hides disfluencies) | Verbatim per-clip stutter gate (CUT-03) |
| 16 | The video ended on the first word of the brand name and cut off the rest | The sign-off must be complete and the brand the last word (STORY-09/10, checked on the voice stem) |

## Picture
| # | Correction | Now enforced by |
|---|---|---|
| 17 | "Why is it so grainy?" (added grain plus repeated lossy re-encodes) | No grain; one lossless decode → one encode, crf 16, no `tune=film` (DEL-05); dither only on gradient graphics |
| 18 | The "strategies" icon looked wrong (hand-drawn) | Material Design icons only (GFX-23) |
| 19 | (gate) A one-frame flash of the next take before a cutaway | Cutaways and transitions snap to segment boundaries |
| 20 | (gate) Punch-in steps of 1.10–1.14× read as jump cuts | Style `framing.zoom_levels` (default 1.0 / 1.18 / 1.38) and `framing.min_step` (default ≥ 1.15×) at every direct cut, creep counted (CUT-05) |
| 21 | (gate) Skin brightness jumped up to 12 % between takes | Per-shot skin exposure balance from YuNet cheek patches (COL-06/07) |
| 22 | (gate) Face-centred punch-ins shook | Face centre smoothed over ±6 frames |
| 23 | (gate) Colour tags were missing from the delivered file | BT.709 matrix + tags on every encode (COL-01) |
| 24 | (moodboard) Chest graphics landed across the face (a float32 coordinate bug) | Fixed in the `gfx` scaler; FRAME-01 checks every element-frame |
| 25 | (moodboard) Auto "lift" reframing to fit graphics cropped the presenter's head | Lift is opt-in only; key info (price, CTA) goes in a full-screen cutaway, not on the chest |
| 26 | (gate) The price card couldn't fit between chin and safe line | Prices are cutaways (`counter` with a currency `prefix`); PLAT-02 blocks prices, pills and end-card elements outside the Reels zone |
| 27 | Captions split mid-sentence and lacked capitals | The caption builder never crosses a sentence end, breaks before joining words, and uses sentence case |

## Process
| # | Lesson | Now enforced by |
|---|---|---|
| 28 | An AI-written curriculum had invented titles | Every source resolved and logged with reasons (`knowledge-base/resolved.json`); a stale-caption bug fixed in the fetcher |
| 29 | Whisper skips sentences on long files and invents words over music tails | Transcribe in about 8 s chunks; check the sign-off on the voice stem |
| 30 | Third-party transcripts and reels are copyrighted | Kept out of the repo; fetch them locally with the included tools |
| 31 | Paid / unknown-licence skills can't be redistributed | `setup/skills.json` marks them manual (e.g. hadi-got-motion is a per-person licence) |
| 32 | The published Resolve MCP bridge let any web page drive Resolve | The repo ships a hardening patch (`setup/control/patch_cursorbridge.py`); review MCP code before installing |
| 33 | Only published proof may appear (an unpublished "150 calls" claim was excluded) | RULEBOOK §0 #11; claims listed with sources in `Brand/claims.md` (created by `cves new`) |
| 34 | Paid ads need licensed music (the test track was unlicensed) | RULEBOOK §0 #12; `cves music` refuses NC / SA / ND licences and logs credits |
| 35 | The moodboard must be a comprehensive edit plan, not a few frames | `cves moodboard` writes EDIT-PLAN.html: timeline of every track + every shot with build frames, words, framing, transitions and sound |
| 36 | Per-client looks must not need code changes, and the first test client's look must not become everyone's | No look is hard-coded: neutral `styles/default.yaml` → optional preset → `Edit/style.yaml` from `cves inspire` → `Brand/style.yaml` → `edit.yaml style:` (`docs/CONTRACTS.md` §1) |
| 37 | (gate) At 60 fps a third of the SFX landed 1-6 frames off their picture (the onset of the file, 30 fps-tuned offsets) | `mix` syncs every cue's onset onto its logged picture event after render (`sound.cue_sync`); templates log the drawn state a sound belongs to as a part |
| 38 | (gate) Captions flashed for 1-4 frames before / after full-screen cutaways | `captions.schedule()`: no fragment under `captions.min_on_s` round a cover (merge into the next event, hold by the previous, or skip words spoken under the cover) |
| 39 | (gate) The room between words survived a fixed gate (-49.7 dBFS) | Adaptive per-take expander at the end of the voice chain (`voice.gate`, SND-19) |
| 40 | (gate) Takes recorded minutes apart did not match at the cuts (skin / wall dE 15, skin Y +12 %) | Per-shot colour match in linear light before the look, subject by skin and wall by wall (`grade.shot_match`, COL-06 / 07); pose at a cut frame is editorial |
| 41 | (review) The music masked quiet words in the 1-4 kHz band | `mix.vmr_guard`: the bed's speech band is trimmed wherever a word would not clear it by the review's limit + 2 dB |
