# CVES editing knowledge base

This is the training base for CVES, the Claude-driven editor of talking-head selfie videos and ads (designed at 1080×1920 for 9:16, typically 30–60 s paid social ads such as Meta Reels). It was distilled from 73 curriculum videos in 9 modules and ranked below the user's own corrections, the client's style profile and the edit standard (`EDIT-STANDARD.md`). The research rules are universal; per-client choices (palette, grade, captions, transition kinds, cutaway share, bed level) come from the style profile (`docs/STYLE.md`), and the gates read those thresholds from it.

## How to use it
1. **Every session loads `RULEBOOK.md` plus `EDIT-STANDARD.md`** and the client's style (`STYLE.md`, `Edit/style.yaml`), and nothing else by default.
2. **`QC-GATES.md` drives the scripts.** Every automatable check has an id, a metric, a threshold, a status and an implementation state. Build gates from it; never invent thresholds outside it.
3. **`CHECKLISTS.md`** is ticked stage by stage. **`QA-REVIEW.md`** is the human review sheet used on the one contact-sheet pass before delivery.
4. **`DECISIONS.md`** lists open calls. Its defaults apply until the user answers; record answers there and in the RULEBOOK.
5. **Open the `modules/` files only when you need detail**: per-video rules with timestamps (section A), the code audits (for example the `gfx.py` findings F1–F13 in module 1, the v3c colour calibration of the first test edit in module 8), and worked examples (the module 6 beat map of the first test ad).

**Precedence.** User-confirmed corrections > the client's style profile > EDIT-STANDARD > module rules. **Labels**: HOUSE (proposed during the first test; for per-client choices now a style default), DERIVED, NORM (industry norm), CALIBRATE (measure on the inspirations before it can block), VIDEO (number stated in a transcript).

## Folders and files
| Path | What it is |
|---|---|
| `RULEBOOK.md` | The loadable core (about 3,000 words): imperatives by edit stage, each cited |
| `CHECKLISTS.md` | Binary yes/no checklists for the 11 stages |
| `QA-REVIEW.md` | Senior-editor judgement sheet: first frame → hook → body → CTA → whole-ad passes |
| `CREATIVE.md` | The senior-editor creative method: creative direction (`Edit/DIRECTION.md`), restraint budget, contrast and rhythm, taste checks, the critique pass |
| `TASTE.md`, `taste/learned.yaml` | Taste the team approved with `cves learn promote --share` (anonymised); the learned style layer merged after the defaults (docs/LEARNING.md) |
| `QC-GATES.md` | 185 gate rules, 96 of them measured automatically by `cves qc` (namespaces STORY, RET, CUT, MOT, GFX, FRAME, SND, COL, PLAT, DEL) with an old-id → new-id index |
| `DECISIONS.md` | 25 open calls with defaults, plus the calls already resolved by the user's feedback |
| `modules/` | 9 module files, each with A (per-video dissection) and B (best practices, ad translation, checklist, QA, QC, anti-patterns, conflicts), plus `viral-playbook.md` (organic posts, `goal: viral`: hooks, structures, retention devices, platform norms, trending sounds) |
| `transcripts/` | One folder per module with the source transcripts (YouTube captions, or local Whisper where captions failed) |
| `tools/` | `DISSECTION-BRIEF.md` (the dissection template), `fetch_transcripts.py`, `whisper_fallback.py` |
| `CURRICULUM.md` | The original curriculum list (72 videos with links) |
| `manifest.json` | The curriculum as data (module → video ids, titles, URLs, channels) |
| `resolved.json` | What each id actually resolved to (URL, method, score, notes) |

## How sources were resolved (`resolved.json`)
There are 73 ids: the 72 curriculum videos plus one addition (6.9). By method: **26 direct**, **26 search matches**, **20 manual replacements**, **1 added**. That makes 21 replacements and additions:

| Id | Now | Why |
|---|---|---|
| 1.3 | Alex Grigg, "The Secret Science of Spacing in Animation" | The Plugin Play spacing/timing title wasn't found; same topic |
| 1.5 | Ben Marriott, "The #1 Skill All Animators Need" | The original was a 56 s course trailer (4 rules) |
| 1.7 | Ag Motion Designs, "5 Logo Animation Principles" | The original video id was unavailable |
| 2.5 | John Tindell, "Rhythm in Film Editing" | The link resolved to an InVideo video with garbled machine captions |
| 3.7 | Satori Graphics, "The ONLY Colour Theory Video…" | The search hit a Portuguese course |
| 5.4 | Herman Huang, "3 Sound Design Secrets That Feel Like CHEATING" | The Nerdwriter title wasn't found (the hit was SNES music) |
| 5.5 | Jason Yadlovski, "Proper Audio Levels for Video Editors" | The Thomas Flight hit ("The Real Villain of Nope") had no sound content; transcript body re-fetched 2026-11-18 |
| 6.9 | Paddy Galloway, "How MrBeast Made YouTube's Greatest Video" | **Added**: 6.8 resolved to a strategy podcast, not the MrBeast structure breakdown |
| 7.3 | StudioBinder, "Ultimate Guide to Camera Angles" | The search hit a lenses video |
| 7.5 | "The 30-Degree Rule \| Continuity & Jump Cuts" | The Filmmaker IQ title wasn't found |
| 7.6 | StudioBinder, "How to Use Walter Murch's Eye Trace" | The search hit junk |
| 7.7 | Liam S., "Learn 42 Composition Techniques in 8 Minutes" | The Wolfcrow title wasn't found |
| 7.8 | Inside The Edit, "How Pro Editors Use B-Roll" | The search hit a template ad |
| 8.3 | It's Just Cinema, "The Power of Colour in Cinema" | The House of Tabula transcript was title cards only (0 rules) |
| 8.6 | "The 60-30-10 Color Rule Explained" | The first hit had no captions |
| 8.7 | Graded by Oscar, "Why Your Videos Look Flat" | The Avery Peck title wasn't found |
| 8.8 | Matti Haapoja, "Why Teal & Orange is Scientifically More Cinematic" | The search hit Technicolor history |
| 9.5 | Joe Sbiti, "How To Make VIRAL Podcast Clip Videos!" | The Jay Clouse title wasn't found |
| 9.6 | Javier Mercedes, "Pro Tips to Reframe Horizontal Videos…" | The search hit an audiobook |
| 9.7 | Ryan Herrick, "MASTER Short Form Content Editing" | The search hit something unrelated |
| 9.8 | The Editing Podcast, "Paddy Galloway Tells Us How To Edit YouTube" | The search hit a film explainer |

**Weak or off-topic matches kept, with caveats** (see each module's header):
- Flagged low-score search matches: 6.3 (0.45, a re-presentation of the Parker/Stone clip), 6.5 (0.52, the real Vonnegut lecture), 8.2 (0.33), 9.1 (0.28), 9.4 (0.44, a 3-minute sponsor spot with no pixel numbers).
- Low-score, unflagged: 4.4 (0.57, headings only), 6.8 (0.61, a machine back-translated transcript), 5.8 (0.62, dialogue EQ rather than SFX), 5.7 (0.64).
- Off the stated topic: 6.7 (catharsis, not information rationing, so the rationing rules are DERIVED), 6.4 (a zombie-story essay), 1.4 (about 85% an After Effects interface tour), 3.8 (thin).
- Duplicates: 2.7 and 5.3 are the same StudioBinder video, dissected from two angles.
- Local Whisper transcripts: 1.4, 1.7, 1.8, 6.1, 6.2.

## Rules per module (section A, per-video rules)
| Module | Rules |
|---|---|
| 1 Motion Design | 231 |
| 2 Video Editing | 231 |
| 3 Graphic Design | 235 |
| 4 Retention Editing | 212 |
| 5 Sound Design & Audio Mixing | 237 |
| 6 Narrative Structure & Script-to-Timeline Arc | 197 |
| 7 Shot Composition, Framing & Camera Language | 234 |
| 8 Color Theory & Visual Continuity | 202 |
| 9 Format & Platform Adaptation | 196 (counted from section A; the module states no total) |
| **Total** | **1,975** |

The B.1 sections de-duplicate these into 239 best-practice rules (22 / 27 / 30 / 28 / 32 / 36 / 25 / 17 / 22 by module). The RULEBOOK keeps the highest-impact ones. QC-GATES merges the 193 module gate proposals (20 / 18 / 25 / 27 / 25 / 19 / 18 / 15 / 26), the 14 ES gates and 9 gateable ES rules into 172 rows (181 since viral mode added RET-24 to RET-32); the index at the bottom of QC-GATES maps every old id.

## Planned workflow
1. **Setup.** Load RULEBOOK + ES. Read the brief; review the inspirations frame by frame; probe the source (tags, resolution, fps); make sure the element log, landmark storage and stems are in place. (Checklist §1.)
2. **Ingest.** Decode the raw once to 10-bit FFV1, take word timings from whisper.cpp, run RVM mattes and YuNet faces with landmarks, then `cves select` (voice chain in `engine/cves/ingest.py`) (no generative step).
3. **Story.** Segment sentences, group re-takes, run `cves qc` (CUT-03), label H/P/A/PR/O/C/X, work backwards from the sign-off, write the connector chain and the setup→payoff table, then run the STORY gates on `beats.json`. **The user approves the cut list.**
4. **Edit plan in `edit.yaml`.** Every element tied to a word, with tags (role, intent, hero, problem/solution, proof, loops), motion tokens, the punch-in plan, transitions, roto moments, SFX and music cues. Pre-render gates run on the plan itself: GFX-01 timing, RET-16/22 rhythm, CUT-05 framing, FRAME-09.
5. **Moodboard.** True-replica keyframes from the same renderer (`engine/cves/render.py` / `gfx.py` / `look.py`): frame 0, hook, each cutaway type at settle, one roto moment, CTA. They are shown next to the inspiration frames. **The user approves.**
6. **Render.** Lossless frames, `cves mix` stems, one x264 encode (crf 16, bt709 tags, `range=tv`).
7. **Automatic gates.** Run every QC-GATES row that is built. BLOCKING failures go back to step 4 or 6. Warnings go into the report.
8. **One-contact-sheet QA.** A single sheet covering every transition (first visible, overshoot and settle frames) plus a face crop per segment, reviewed with `QA-REVIEW.md` and the phone passes (sound on, sound off, UI overlay, loop).
9. **Delivery, in one of two modes:**
   - **Vibe mode (prompt only):** the user describes changes in chat. Claude edits `edit.yaml`, re-renders, re-runs the gates, and sends the file plus the gate report.
   - **Control mode:** Claude drives **DaVinci Resolve Free live** through the **hiteshK03/davinci-resolve-mcp** in-app bridge, building the timeline from `edit.yaml` so the user can adjust it in Resolve themselves. **Kdenlive** is the fallback if the bridge is unavailable. Whatever leaves Resolve or Kdenlive still has to pass the same final-file gates (SND-01/02, COL-01, DEL-01 to DEL-05, CUT-01 to CUT-03).
10. **Notes become rules.** Every note the user gives is written into the RULEBOOK (or proposed for ES), gets a gate or checklist line, and is logged in DECISIONS if it settles a conflict. CALIBRATE gates are re-measured on the inspirations and later on Meta retention and hold-rate data.


## Transcripts (not in the repo)
The full transcripts of the 73 curriculum videos are other creators' copyrighted text, so they are not committed.
Rebuild them locally (about 10 minutes):
```
cd knowledge-base
python tools/fetch_transcripts.py            # captions via yt-dlp; reads manifest.json + resolved.json
python tools/whisper_fallback.py <ids...>    # for any video whose captions are rate-limited (HTTP 429)
```
They land in `knowledge-base/transcripts/` (git-ignored). The modules, rulebook, checklists and gates are original write-ups
with short attributed quotes, and every rule cites its video id and timestamp, so it can be checked against the source.
