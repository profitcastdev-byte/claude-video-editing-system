# CVES v0.4: the senior eye

## Intent
v0.3 can edit any video type and any frame size, but it ships its first cut. A senior editor:
- watches their own cut before anyone else does;
- explores more than one idea;
- cuts sound as carefully as picture;
- has deep motion craft;
- has no known rough edges.

v0.4 closes those gaps, which are everything that doesn't need the owner's real footage.

The owner approved this plan ("Yes, start") and opted out of questions. Every choice below is the builder's call.

What v0.4 deliberately leaves for v0.5: the taste folder, real-job benchmarks against a human editor, and pulling ad/retention results from Meta and YouTube.

## Measurable target
9/10 means two things, measured on 10 real jobs:
- the owner rates the first cut 8 or higher on average;
- CVES wins or ties at least 40% of blind A/B tests against a human senior editor on the same footage.

v0.4 builds the tools that make that measurable (`cves review` sign-off records) but cannot claim the score.

## Workstreams
| WS | Name | Delivers |
|---|---|---|
| F | Review loop (`cves review`) | Watches the render, not the plan. A **review pack** per render (`Edit/review/rNNN/`): a frame strip around every cut (−2/0/+2 frames), the hook at 10 fps for its first 3 s, the payoff and the end card; audio checks (vocal intelligibility under music, transient clicks at cuts, loudness per section, silence gaps, and `earshot` when installed). Detected issues become `findings.json`, each with a severity, a timecode and, where possible, a machine-applicable `edit.yaml` patch. `cves review apply` applies the safe patches. `cves review signoff` records Claude's verdict and notes in the journal. A loop recipe in the editor skill: render → qc → critique → review → fix → re-render, until there are 0 FAILs and no high findings, max 3 rounds, before showing the owner. |
| G | Treatments (`cves treatments`) | 2–3 distinct creative treatments per job (built-in: `punchy`, `cinematic`, `minimal`; plus any user-defined `treatments/*.yaml`). Each is a style + structure overlay that produces its own `Edit/treatments/<name>/edit.yaml`. Fast proxy renders (`--proxy`: half resolution, fast encode, cached plates reused), a side-by-side comparison sheet + a short comparison MP4, and `cves treatments pick <name>`, which promotes the chosen one to `Edit/edit.yaml` and journals the choice (feeding `cves learn`). |
| H | Senior sound | Builds on `beats.py`, which already does the bar layout and seams; this WS closes its gaps. Phrase alignment: music sections (intro/build/drop) aligned to story beats (hook, turn, payoff). Automatic risers into the hook/payoff and impacts on reveals, rate-limited by the restraint budget. Ducking that follows the voice envelope (attack/release from syllable rhythm), not fixed dips. An SFX bank: a manifest-driven library under `assets/sfx/` with categories (whoosh, impact, riser, ui, pop, transition, ambience), CC0 only, every file recorded in `assets/sfx/CREDITS.md` with source URL + licence; `cves sfx fetch` (Openverse/Freesound, CC0 filter) for users to grow it locally. Plus a sound QC gate or two. |
| I | Motion craft | Text **behind** the speaker (uses the existing subject matte), tracked to the face. Speed ramps on B-roll (time remap with eased curves, frame blending). Match cuts (shape or position continuity between shots). Camera moves on B-roll and stills (push, pull, parallax from depth when available, handheld drift). A transitions library (whip, zoom-through, mask wipe, luma fade, glitch-lite, light leak), style-driven and rate-limited. 15 more HTML motion pieces, to 30. |
| J | Weak spots | v0.2 UI cutaways (`search_rows`, `card_list`, `stat`, `browser_list`) and roto cards laid out natively per canvas (no more small on landscape). Relative templates drawn at the canvas's real resolution (no 4K softness). HDR (PQ/HLG) B-roll tonemapped to SDR the same way as A-roll. `import-edits` maps B-roll and motion tracks. Control-mode round trip: full Kdenlive round trip tested; DaVinci Resolve is not installed on the build machine, so its import stays documented as untested and gets a scripted checklist for the first person who has it. |

## Non-goals
- Generative models inside the engine (unchanged from v0.3).
- Claude-in-the-engine: the engine never calls an LLM. `cves review` produces the pack and machine findings; Claude does the looking, judging and patching, as directed by the skill.
- Non-CC0 SFX in the repo.
- Any loosening of existing QC gates.

## Anti-goals
- **Effect soup.** Every new transition, ramp, riser and piece counts against the `creative.*` restraint budget.
- **A review loop that never ends or always passes.** It is capped at 3 rounds, and every sign-off records what was still wrong.
- **Regressions on the v0.3 paths.** Golden tests and the landscape viral VO demo must still pass with 0 FAIL.

## Constraints
The v0.3 constraints still apply (`docs/CONTRACTS.md`):
- every new style key goes in `default.yaml` and `docs/STYLE.md`;
- lint portability;
- synthetic test media only;
- each WS adds CLI commands in its own commented block in `cli.py`;
- new dependencies are pinned and added to both installers, `doctor.py`, `TOOLS-REGISTRY.md` and `CHANGELOG.md`.

## Done means
- Each WS ships tests.
- Full `pytest`, `tools/lint.py`, `tools/gate_status.py --check` and `cves export selftest --no-gui` pass.
- Both demo kinds build with 0 FAIL: the vertical talking-head and the landscape viral VO.
- A review pack is generated for each demo and checked by eye.
- Docs: new `REVIEW.md`, `TREATMENTS.md` and `SOUND.md`; MOTION, FORMATS and CONTROL-MODE updated.
- The editor skill and plugin commands describe the loop.
