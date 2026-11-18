---
description: Measure the client's look from their reference edits and write the style profile (Edit/style.yaml)
---
Run this after `/cves:new-edit`, once the client's reference edits (videos or screenshots of edits they like) are in `PROJECT/Inspirations/`.

1. Check that `Inspirations/` has at least one reference. If it is empty, ask the user for 2–5 reference reels. Without them the edit uses the neutral defaults (or a preset they name).
2. Run `cves inspire --dry-run` and show the user the summary: pacing, cutaway share, grade, palette, captions, transitions and framing, each with its confidence.
3. Ask the user whether this is the look they want. Adjust as they ask, by editing `Edit/style.yaml` after it is written, or with inline keys under `style:` in `edit.yaml`.
4. Run `cves inspire` to write `Edit/style.yaml`. Keys below confidence 0.5 are not written; the defaults or the preset stay in force for them.
5. From here on, render, captions, mix and the QC thresholds all follow this profile. The merge order is in `docs/STYLE.md`: defaults → preset → `Edit/style.yaml` → `Brand/style.yaml` → `edit.yaml style:`.

Never copy a reference's copyrighted footage, music or text into the edit: inspire measures the look only.
