---
description: Measure the client's look, sound and rhythm from their reference edits and write the style profile (Edit/style.yaml)
---
Run this after `/cves:new-edit`, once the client's reference edits (videos or screenshots of edits they like) are in `PROJECT/Inspirations/`. The references are the client's taste spec: inspire sees, hears and feels each one, then picks a source per dimension instead of averaging them.

1. Check that `Inspirations/` has at least one reference. If it is empty, ask the user for 2–5 reference reels. Without them the edit uses the neutral defaults (or a preset they name).
2. If the user has said which reference matters most or for what ("the colour of A, the pacing of B"), write `Inspirations/refs.yaml` first: per file `rank` (1 = best), `weight`, `kind: ad|viral`, `use: [grade, palette, captions, pacing, sound, motion, structure]` (what this reference is the authority for) and `notes`. See docs/STYLE.md.
3. Run `cves inspire --dry-run`. It prints the measured keys and a per-dimension table (candidates per reference, chosen value, source, confidence), and writes `Edit/inspire/REPORT.md`, a contact sheet per reference (`Edit/inspire/<ref>-sheet.jpg`) and `Edit/inspire/aesthetic-review.md`.
4. **Look before you summarise.** Read `Edit/inspire/REPORT.md`, then open every contact sheet image and fill `Edit/inspire/aesthetic-review.md`: composition, typography quality, colour mood, motion character, texture / grain, negative space, premium vs cheap read, what to steal, what to avoid, and one sentence for the look across the references. Name what you see, not adjectives.
5. Summarise the mix for the user in a few lines: per dimension, which reference it comes from and why (agreement, rank, authority or strongest look), what the edit should feel like (pacing, cut on the beat, hook timing, loop, sound balance, music tempo), and anything in the sheets that the numbers missed. Ask whether this is the look and feel they want.
6. Adjust as they ask: force sources with `cves inspire --dry-run --mix "grade=refA,captions=refB,pacing=refC"` (re-runs are fast: measurements are cached), edit `refs.yaml`, or set keys under `style:` in `edit.yaml` later.
7. Run `cves inspire` (with the same `--mix`, if any) to write `Edit/style.yaml`. Keys below confidence 0.5 are not written; the defaults or the preset stay in force for them.
8. From here on, render, captions, mix, beat sync and the QC thresholds follow this profile. When planning, use the `rhythm.*` and `structure.*` targets (cut rate and curve, interrupt gaps, hook timing, loop, energy arc, music tempo, voice-led or music-only) and the aesthetic review. The merge order is in `docs/STYLE.md`: defaults → preset → `Edit/style.yaml` → `Brand/style.yaml` → `edit.yaml style:`.

Never copy a reference's copyrighted footage, music or text into the edit: inspire measures the look, sound and rhythm only. The contact sheets stay in the client's project folder.
