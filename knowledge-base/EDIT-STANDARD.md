# Edit standard

The written spec for every talking-head edit CVES makes. It was first written from a reviewer's own reference edits while the system was tested on its first ad, then split in two: **rules that hold for every client** (kept here as rules), and **per-client choices** (cutaway share, transition kinds, palette, grade, caption position, bed level), which now come from the client's **style profile** (`docs/STYLE.md`: `styles/default.yaml` → optional preset → `Edit/style.yaml` from `cves inspire` → `Brand/style.yaml` → `edit.yaml style:`). Where this file gives a number for a per-client choice, it is an example from preset `profitcast-dark`, not the default. Nothing is delivered until every **gate** at the bottom passes.

## 1. Edit grammar (from the inspirations)
- **A-roll / B-roll rhythm.** Clean talking head alternates with **full-screen motion-graphic cutaways**. The voice continues under the cutaways, which hide jump cuts and pauses. The share of runtime on cutaways is a per-client choice: style `grammar.cutaway_share` (e.g. preset `profitcast-dark`: 40–55%; default: not enforced). Cutaways last at most `grammar.max_cutaway_s` (default 8 s), A-roll shots at most `grammar.max_shot_s` (default 4 s).
- **Cutaways build with the words.** Lists appear line by line on the spoken item (search list, problem list, services list). Numbers count up. Nothing appears before it's said.
- **Rotoscoping is a spice, not the meal.** A few short moments (≤ `grammar.roto_max`, default 4, each ≤ 3 s): a card or big word behind the head. Never a full-length effect.
- **Transitions are motivated.** The kinds come from the style (`transitions.in` / `transitions.out`: cut, whip, glitch or fade; default cut; e.g. `profitcast-dark` uses a zoom-blur whip in and glitch lines out), plus at most `framing.extreme_max` extreme punch-ins for emphasis. Never a hard switch of world or lighting.
- **Hiding cuts on the A-roll.** Every jump cut between A-roll takes either changes framing by at least style `framing.min_step` (default 1.15×) or is covered by a cutaway. No visible jump between two similar frames.
- **Icons:** Material Design set in `Assets/Icons/` only, never hand-drawn shapes.
- **Real assets.** Client logos and real names in proper typography (the client's own logo file, or the `wordmark` template in the client's brand fonts), never plain mono text.

## 2. Look
The look is whatever the client's inspirations show, measured into the style profile. The rules below hold for every look.
- **Series look.** Stage, palette and card style come from style `stage:` and `colors:`. Keep them consistent across the whole video and the client's series. (Example, preset `profitcast-dark`: black background, green dot grid, a green glow rising from the bottom, green and white type, UI cards with icon wells and check/✕ states, corner brackets. The default is a neutral dark stage with a blue accent.)
- **A-roll grade** comes from style `grade:` (e.g. `profitcast-dark`: warm, dark and moody, soft vignette; default: no relight, neutral). Always natural skin; no sudden dims, no desaturation jumps.
- **Captions** come from style `captions:` (style, size, case, position, max lines). Defaults: small, white, sentence case, up to 2 lines, just under the chin, soft shadow. Never over the face (FRAME-01 wins over every other placement).
- No added grain. Highest-quality source path: decode the raw once (10-bit FFV1), render frames losslessly, encode once (x264 crf 16, no `tune film`). Dither only on gradient graphics.
- Background darkening (style `grade.relight`) uses an edge-accurate matte (1 px erode, 3 px feather). A wide feather makes a glowing ring round the head (the v1 "aura").
- Every cutaway and transition is snapped to an exact segment boundary (a 1-frame flash of the next take is a jump cut).

## 3. Sound
- Voice: DeepFilterNet3 denoise, then EQ, de-ess, compressor, gentle expander (`cves select`, voice chain in `engine/cves/ingest.py`). It should sound like a podcast mic.
- **Never use generative enhancement (Resemble Enhance full mode)**: it rewrote words in tests ("posts" → "course", "rank" → "learn"). Every voice process must pass the words gate.
- Pauses: no gap over 0.25 s inside speech; breath gaps trimmed to 0.08–0.15 s.
- Music bed level under the voice is a per-client choice: style `sound.bed_lu` (default −10 LU; preset `profitcast-dark` uses −7 LU, after the first reviewer asked three times for louder: −23, −14 and −10 were too quiet for them). Frequency-split ducking (style `sound.duck_voice_band_db`, default −8 dB; `sound.duck_other_db`, default −3 dB) keeps it big without masking words; real sound effects on the frame; master at style `sound.master_lufs` / `sound.true_peak` (default −14 LUFS, −1 dBTP).

## 4. Quality gates (automated, must pass before delivery)
The master list is `knowledge-base/QC-GATES.md` (183 rules: 78 blocking, 70 warning, 35 to calibrate). `cves qc` measures 95 of them automatically today; the rest are checked by eye (contact sheets, the moodboard) or are not measurable yet. It writes `Edit/QC-REPORT.txt` (failures only in detail) and `Edit/qc.json`. Thresholds for per-client choices are read from the style profile. Load `knowledge-base/RULEBOOK.md` and `LESSONS.md` before editing. The table below is the original core subset.
| Gate | Check | Pass |
|---|---|---|
| Words | Re-transcribe the cut and compare with the script | No missing, clipped or duplicated words |
| Pauses | Speech-gap scan of the final mix | No gap > 0.25 s |
| Stutters | Verbatim per-clip transcription of every kept segment (`cves qc`, CUT-03) | No repeated word or false start |
| Ending | Last kept words vs the raw's last words | The sign-off is complete (the whole brand name, as `qc.brand_tail` lists it) |
| Voice | Noise floor and reverb estimate on the voice stem | Floor ≤ −60 dBFS between words, no audible room tail |
| Loudness | EBU R128 | Style `sound.master_lufs` ±0.5 LU (default −14 LUFS), TP ≤ `sound.true_peak` (default −1 dBTP) |
| Jump cuts | Framing difference across every A-roll cut | Every cut changes framing by ≥ `framing.min_step` or is covered |
| Face | YuNet face box vs every text/graphic layer | Zero overlap |
| Frame edges | Person matte touching the frame | Body only exits through frame edges |
| Matte | Edge-ring brightness vs background | No halo or wall leak (rotoscoped shots only) |
| Text | Bounds and safe margins for every text element | Inside the style safe area (`platform.margin`, default 60 px; `platform.safe_zone`), no clipping |
| Image | Noise, banding and blockiness metrics vs the raw | No added grain, single encode |
| Colour tags | `ffprobe` colour range, space, transfer and primaries on the delivered file | `tv / bt709 / bt709 / bt709`. Encode with `-x264-params colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv` and `scale=out_color_matrix=bt709:out_range=tv` (an early test version shipped without the tags) |
| Visual QC | Contact sheet at every transition, checked frame by frame | Reviewed before sending |

## 5. Pipeline (the `cves` engine; see docs/ARCHITECTURE.md §3)
`cves new` → `cves inspire` (first video per client: style profile from `Inspirations/`) → `cves ingest` (raw transcript) → Claude writes `selects.yaml` → `cves select` (DeepFilterNet voice + podcast chain, pause tightening,
frame-snapped `edl.json`) → `cves qc --stage story` → **cut-list approval** → `cves prep` (word timings, one lossless 10-bit decode,
RVM resnet50 matte, YuNet faces + landmarks) → `cves plan` + `edit.yaml` → `cves qc --stage plan` → `cves moodboard` → **moodboard approval**
→ `cves build` (render with `gfx.py` / `look.py` / templates, mix, single encode) → `cves qc` (all measured gates; 0 FAIL before anything is shown)
→ `cves deliver` (vibe mode), or `cves export resolve|kdenlive` (control mode). Plus earshot critique and a contact sheet at every transition.
earshot's "salient hit density" flags speech rhythm on talking heads (the voice alone scores ~2/s): a false flag, so check the voice stem.
