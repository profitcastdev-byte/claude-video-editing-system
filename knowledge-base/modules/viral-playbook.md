# Viral playbook (organic short-form: Reels, TikTok, Shorts, YouTube)

Rules Claude applies when `edit.yaml goal: viral`. They sit under RULEBOOK §0 (non-negotiables still win) and §12, and next
to the curriculum modules (4 Retention, 6 Narrative, 9 Platform), which they adapt from paid ads to organic posts. Gate ids
point to `QC-GATES.md`; style keys to `docs/STYLE.md`; the engine side is `docs/VIRAL.md`.

**Label:** **[VIRAL]** = a builder's rule for organic posts (v0.3, 2026-11-19), distilled from modules 4, 6 and 9 and the
platforms' public creator guidance. Numbers marked **CALIBRATE** are starting points to re-measure on the client's own
reference posts (`cves inspire`) and their retention graphs.

**What changes from an ad.** An ad is paid to be shown; it must earn the click. An organic post is shown only while people
keep watching; it must earn **the next second**, every second, and ideally the replay. So: the hook is the edit, the middle
is a chain of small promises kept, the ending pays off and (often) loops, and there is usually no hard CTA.

---

## 1. Hooks: pick one type before cutting anything

Decide the hook in the brief (the skill asks for it). The first second is picture first: the viewer decides with the sound
off. Every hook below must show a **visual change by 1.0 s** (RET-24, `structure.hook_change_s`) and **text or a strong
subject by 1.0 s** (RET-25).

| type | what the first second does | build it with | avoid |
|---|---|---|---|
| **Curiosity gap** | states a specific result and withholds the how ("This one setting doubled our views") | a title card / kinetic line on frame 0, the payoff object half-shown | vague teases ("you won't believe…": RET-08 bans them) |
| **Pattern break** | something the feed doesn't look like: a snap zoom, a hard colour change, an object entering the frame, a whip | `aroll.snap`, a cutaway with `in: whip`, a punch-in on the first word | a logo sting or black frame (RET-13, PLAT-12) |
| **Bold claim** | a strong, checkable statement as the first line, on screen and spoken | captions + a big-word roto or title card with the number | claims without published proof (RULEBOOK §0.11) |
| **Visual question** | shows the end state or a puzzle and makes the viewer guess ("Which one is real?") | split / comparison / two-pane templates, a counter frozen mid-count | answering it before the payoff window |
| **In media res** | starts in the middle of the action, the context comes later | open on the most kinetic shot; move the setup sentence after it (selects re-order) | a "hi guys" intro (RET-08) |
| **"Wait for it"** | promises a moment the viewer can see coming (a progress bar, a countdown, a half-built object) | a visible timer / progress element in the first second; the moment itself in the payoff window (RET-29) | saying "wait for it": the spoken phrase stays banned by RET-08; show it instead |

Rules:
- One hook type per video, stated in `Edit/NOTES.md`. If two compete, the stronger one goes first and the other becomes the first re-hook.
- The hook's words are the shortest line in the take (≤ 8 words, ≤ 2.5 s). Re-order takes to put it first; never synthesise it.
- Frame 0 is already moving (RET-10) and holds the brightest element of the look.
- The topic is on screen by 1 s (`grammar.topic_by_s` 1.0 in the viral preset; RET-01/12).

## 2. Structures: pick one, then design the hook first, the payoff second, the middle last

| structure | shape | payoff | loop fit |
|---|---|---|---|
| **Loop** | the last line / shot leads straight back into the first (the first line completes the last sentence, or the last shot is the first shot) | the realisation that it loops | native: set `structure.loop: true` (RET-28) |
| **List** | "3 things…": item count on screen, each item one interrupt, the best item **last** | the strongest item | good: cut the last item straight into item 1 |
| **Story arc** | setup → turn → result in under 30 s; the turn lands at 50-70 % | the result, shown | weak: end on the result, no tail |
| **Before / after** | the after first (1 s flash), then before → process → after | the full after | good: the last frame matches the first flash |
| **Tutorial** | result first, then steps at one interrupt per step, then the result again | the result | good |

Rules:
- **Payoff in the last 20 %** (`structure.payoff_window`, RET-29): a visual or audio peak, a graphic entry, the reveal. Nothing after the payoff except the loop seam or a ≤ 1 s button.
- **Open loops**: open one in the hook, close it in the payoff window; a list opens one per item (STORY-14 discipline).
- **No outro**: no "follow for more" card, no end card unless the client's style has one. A CTA, if any, is spoken over the payoff, not after it.
- **Length is a result, not a target**: cut until every second earns its place, then check the platform band (RET-30). Most organic posts land at 7-35 s.

## 3. Retention devices (the middle)

- **Pattern interrupts**: one every ≤ `rhythm.interrupt_max_s` (2.5 s in the viral preset; RET-26). An interrupt is a cut with a zoom step, a cutaway, a transition, a graphic entering, a snap, or a b-roll change. Captions changing pages are **not** interrupts.
- **Budget, not soup**: never a run of interrupts closer than `rhythm.interrupt_min_s` (0.25 s) for longer than `retention.soup_window_s` (1.5 s; RET-27). Burst then rest: build → burst → release (RET-21) still applies.
- **Re-hooks** every 5-8 s: a new question, a number, a "but". The re-hook is the next promise; keep each one before the CTA.
- **Captions**: always on, punchier than an ad (viral preset: `pop`, larger, ≤ 22 characters, numbers emphasised), inside the platform's caption line (`platform.target`, PLAT-02).
- **Sound**: a beat under the cuts (`rhythm.cut_on_beat`, RET-32), SFX on every interrupt that moves (louder share: `sound.sfx_offset_db` 0), no dead air over 0.6 s (RET-31 FAILs for viral).
- **Speed**: pauses ≤ 0.25 s as always (CUT-02); speed ramps only on b-roll, never on the voice.
- **Faces**: a face or a strong subject in most frames; text-only stretches ≤ 2.5 s.

## 4. Platform norms (`platform.target`)

| platform | safe area (text) | length that performs | sound | notes |
|---|---|---|---|---|
| Reels | 6 % sides, 14 % top, 35 % bottom | 7-35 s | trending sound in-app, or original audio | cover frame matters on the grid; 9:16 |
| TikTok | right rail ~16 %, bottom ~26 % | 9-34 s; a qualified view is 5 s, so the first 5 s carry the post | in-app sound at low volume over the voice | the caption line sits low: keep burned captions above 72 % |
| Shorts | right rail ~14 %, bottom ~28 % | 15-45 s | the loop is automatic: endings must cut cleanly | no clickable links: no hard CTA |
| YouTube (landscape) | title bar, controls | 1-20 min | licensed music in the file | retention graph per chapter; not short-form |
| Meta feed / Stories | feed controls / 14 % top + 20 % bottom | 6-30 s / 5-15 s | sound-off first | Stories: one idea per card |

Make one master per aspect; never letterbox. Pick `platform.target` in the brief; the zone, duration band and loudness follow.

## 5. Trending sounds (`music.slot: platform`)

- Cut to the sound, never ship it: `music: {slot: platform, guide: <reference track or tempo>, sound: "<name>"}`. The master is voice + SFX; the poster adds the sound in the app from POSTING.md.
- Put the drop on the payoff or the first re-hook (`music.drop_cut`), and the cuts on its beat (`cves beats --sync cuts --apply`; RET-32).
- Leave room for the sound: voice clear and steady, no music-like SFX beds.
- **Ads never use the slot** (RULEBOOK §0.12): an ad carries licensed music in the file.

## 6. What NOT to do

- No vague-suspense openers, greetings or "watch till the end" (RET-08); no logo sting or black frame first (RET-13, PLAT-12).
- No effect soup: effects that don't carry information are cut (RET-27; the spec's anti-goal).
- No fake stakes, fake numbers or invented scarcity (RULEBOOK §2, §0.11). Organic reach does not excuse unpublished claims.
- No text under the platform UI (PLAT-02 with `platform.target`).
- No outro, end slate or fade to black; no music tail after the payoff.
- No trending sound baked into the file; no unlicensed music in any file (RULEBOOK §0.12, CONTRIBUTING).
- No repurposed landscape cut with captions on top: re-cut natively for the feed (module 9.1).
- Never loosen a gate to make a post pass; thresholds change by decision (DECISIONS.md).
