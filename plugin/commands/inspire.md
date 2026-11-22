---
description: Measure the client's look, sound and rhythm from their reference edits and write the style profile (Edit/style.yaml)
---
With reference edits (videos or screenshots) in `PROJECT/Inspirations/`. `cves inspire` measures them and picks a source per dimension.

1. Empty → ask for the reference edits.
2. User said which reference rules what ("colour of A, pacing of B") → first write `Inspirations/refs.yaml`: per file `rank` (1 = best), `weight`, `kind: ad|viral`, `use: [grade, palette, captions, pacing, sound, motion, structure]`, `notes` (docs/STYLE.md).
3. `cves inspire --dry-run`: per-dimension table (candidates, chosen value, source, confidence) → `Edit/inspire/REPORT.md`, `<ref>-sheet.jpg` each, `aesthetic-review.md`.
4. Read `REPORT.md`. If the user wants the look described, open the sheets and fill `aesthetic-review.md` with what you see.
5. Tell the user in a few lines: per dimension, which reference and why; the feel (pacing, cut on the beat, hook timing, sound balance, tempo).
6. Adjust: `cves inspire --dry-run --mix "grade=refA,captions=refB,pacing=refC"` (cached, fast), edit `refs.yaml`, or `edit.yaml style:` later.
7. `cves inspire` (same `--mix`) → `Edit/style.yaml`; keys below confidence 0.5 aren't written.
8. Render, captions, mix and beat sync follow the profile (merge order: skill §4). The `rhythm.*` / `structure.*` values describe the references' feel (cut rate, hook timing, loop, tempo).

Never copy a reference's footage, music or text: measure only. Sheets stay in the client's project folder.
