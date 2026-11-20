---
description: Measure the client's look, sound and rhythm from their reference edits and write the style profile (Edit/style.yaml)
---
After `/cves:new-edit`, with reference edits (videos or screenshots) in `PROJECT/Inspirations/`. They are the taste spec: pick a source per dimension, never average.

1. Empty → ask for 2–5 reference reels; without them: neutral defaults (or a preset they name).
2. User said which reference rules what ("colour of A, pacing of B") → first write `Inspirations/refs.yaml`: per file `rank` (1 = best), `weight`, `kind: ad|viral`, `use: [grade, palette, captions, pacing, sound, motion, structure]`, `notes` (docs/STYLE.md).
3. `cves inspire --dry-run`: per-dimension table (candidates, chosen value, source, confidence) → `Edit/inspire/REPORT.md`, `<ref>-sheet.jpg` each, `aesthetic-review.md`.
4. **Look before you summarise:** read `REPORT.md`, open every sheet, fill `aesthetic-review.md` (composition, typography quality, colour mood, motion character, texture / grain, negative space, premium vs cheap, what to steal, what to avoid, one sentence for the look). Name what you see, not adjectives.
5. Tell the user in a few lines: per dimension, which reference and why (agreement, rank, authority, strongest look); the feel (pacing, cut on the beat, hook timing, loop, sound balance, tempo); what the numbers missed. Ask if this is the look.
6. Adjust: `cves inspire --dry-run --mix "grade=refA,captions=refB,pacing=refC"` (cached, fast), edit `refs.yaml`, or `edit.yaml style:` later.
7. `cves inspire` (same `--mix`) → `Edit/style.yaml`; keys below confidence 0.5 aren't written.
8. Everything downstream (render, captions, mix, beat sync, QC thresholds) follows the profile (merge order skill §1). Plan with the `rhythm.*` / `structure.*` targets (cut rate + curve, interrupt gaps, hook timing, loop, energy arc, tempo, voice-led or music-only) and the aesthetic review.

Never copy a reference's footage, music or text: measure only. Sheets stay in the client's project folder.
