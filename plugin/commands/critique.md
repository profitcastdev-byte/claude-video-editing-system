---
description: Senior-editor review. Build the critique pack (contact sheet, energy timeline, rubric), score it honestly, fix anything below 7, log the scores
argument-hint: "[vNNN | master]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:critique: the senior-editor pass
Target: `$ARGUMENTS` (default `master`, the file `cves qc` last judged), after 0 FAIL, before the user sees the cut. **Follow `skills/video-editor/reference/review-loop.md` (Critique)**; rules `knowledge-base/CREATIVE.md`, `QA-REVIEW.md`.

- `contact_sheet.jpg`: one frame per shot + frame 0, each graphic settled, the last frame (labelled time + id / template). `timeline.png`: cuts, graphics, SFX hits, music energy, speech on/off, loudness. Look at each once (skill §3); read `CRITIQUE.md` facts + restraint budget (style `creative:`).
- Rubric extras: creativity = ONE memorable moment?; restraint = anything gratuitous? Against `Edit/DIRECTION.md`: signature moment landed, motif paid off, "will NOT do" kept. Strict senior editor, not proud author.
- Say what needs a pickup, proof or a new template.
- Log: `cves learn rate <version> <overall> --by claude --why "<one line>" --scores hook=..,story=..,pacing=..,aesthetics=..,motion=..,sound=..,creativity=..,restraint=..,platform=..,brand=..`.

Next `/cves:review`. **Show:** nothing by default; the MP4 per skill §4 + one line on what the critique changed; `CRITIQUE.md` only if asked why.
