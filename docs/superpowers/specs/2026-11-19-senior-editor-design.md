# CVES v0.3: senior editor, any video

## Intent
v0.2 is a careful junior: it edits vertical talking-head ads and refuses to ship mistakes.
The goal for v0.3 is a senior editor for any video, ads **and** viral organic content. It should:
- study the inspirations, seeing the aesthetics, hearing the audio and feeling the edit;
- make bold, tasteful creative choices with real motion design;
- edit A-roll, B-roll-only, voiceover-led, music-led and cinematic videos;
- work in any frame size: 9:16, 4:5, 1:1, 16:9 or 2.39:1;
- get better with every edit.

The owner asked for this to be built without further questions. Every choice below is the builder's call, recorded as such.

## Goals → workstreams
| WS | Name | Delivers |
|---|---|---|
| A | Motion layer | Animated HTML/CSS compositions rendered headless to RGBA frames, used as templates; a library of parameterised senior-grade motion pieces; style-driven |
| B | Inspire v2 | Hear (music tempo and energy, SFX density, voice/music balance, silence), feel (cut-on-beat ratio, energy curve, hook timing, loop seam, pattern-interrupt rate), aesthetics (contact sheet per ref + rubric for Claude), mix and match (per-dimension pick from ranked references instead of averaging) |
| C | Any format + spines | Canvas size from the style (`canvas.size`) instead of fixed 1080×1920; timeline spines `aroll` (today), `voiceover`, `music` and `broll`; face-only stages skip when there is no A-roll |
| D | Viral mode | `viral` preset; platform profiles (reels, tiktok, shorts, youtube, meta_feed) with safe zones; retention QC gates; a trending-sound slot for organic posts; viral playbook in the knowledge base |
| E | Self-learning + senior brain | `cves learn` journal → candidate patterns → owner-approved promotion into a learned style layer; `cves critique` aesthetic review pack; a creative-direction step and restraint budget in the editor skill |

## Non-goals
- Generative video models inside the engine. Magnific and ElevenLabs stay Claude-driven connectors, as today.
- Redistributing third-party skills (motionmaxxing, effects, hadi-got-motion) in the public repo. Their unknown or paid licences forbid it. CVES ships its own motion runtime. Skills installed on a machine may be used by Claude at plan time, but never vendored.
- Any loosening of existing QC gates.

## Anti-goals
- "Effect soup". Creativity is budgeted (E: restraint budget, D: pattern-interrupt *max* rate as well as min).
- Self-learning that silently changes the look. Every promotion is approved by a person and recorded.
- Regressions on the v0.2 talking-head path. Golden tests must still pass, or golden updates must be justified in the commit.

## Constraints (all workstreams)
- `docs/CONTRACTS.md` holds:
  - every new style key goes in `engine/cves/styles/default.yaml` (neutral value + comment) and `docs/STYLE.md` (a test enforces this);
  - portability rules (`tools/lint.py`);
  - utf-8 opens, `tempfile`, `pathlib`.
- No client names, footage or third-party media in the repo. Test media is synthetic (`tools/make_demo.py`).
- CI matrix: macOS, Windows and Ubuntu, Python 3.12. New dependencies need pinning, both installers, `doctor.py`, `TOOLS-REGISTRY.md` and `CHANGELOG.md`.
- Each WS adds its CLI sub-commands in `cli.py` in its own clearly commented block, to keep merges easy.
- Each WS adds its style keys as its own top-level section in `default.yaml` where possible.

## Approaches considered (builder's call)
1. **Motion: own HTML runtime rendered by headless Chromium (Playwright)** ✅
   - Gives CSS's full aesthetic range: blur, backdrop-filter glass, gradients, variable fonts, masks.
   - Seek-safe: `window.__seek(t)` per frame.
   - No GSAP: its licence isn't ours to vendor, and a small easing library is enough.

   *Rejected:*
   - more PIL templates, which have a low aesthetic ceiling;
   - Remotion, which needs a Node project per render and has a company licence;
   - vendoring the motionmaxxing or effects skills, which have unknown licences.
2. **Formats: canvas from style, read at runtime** ✅
   - `gfx.W/H` become a configured canvas (`gfx.set_canvas(w, h)`), and templates read `G.W`/`G.H` at call time.
   - Layout constants become fractions of the canvas.

   *Rejected:*
   - render vertical then reframe, which is today's approach and isn't native;
   - a separate landscape engine, which would mean two code paths.
3. **Learning: journal + mined patterns + approved promotion into a style layer** ✅
   - Merge order becomes `default → learned (~/.cves/taste/learned.yaml, then repo knowledge-base/taste/learned.yaml) → preset → inspire → brand → edit.yaml`.

   *Rejected:*
   - fine-tuning a model, which is impossible locally and opaque;
   - auto-applying rules, which breaks the anti-goal.

## Done means
- Each WS ships tests on synthetic media. Full `pytest`, `tools/lint.py` and `tools/gate_status.py --check` pass, and `cves export selftest --no-gui` passes.
- `tools/make_demo.py` gains `--kind aroll|voiceover|music|broll` and `--size WxH`. A landscape VO + B-roll demo builds end to end and passes QC.
- Docs updated: ARCHITECTURE, CONTRACTS, STYLE, and new MOTION.md, FORMATS.md, VIRAL.md and LEARNING.md.
- The skill and plugin commands describe the new steps.

## Left to the builders
- Exact metric definitions and thresholds: start as `warn`, recorded in `knowledge-base/DECISIONS.md`.
- Motion piece designs, within the style profile.
- File layout inside each WS's new modules.
