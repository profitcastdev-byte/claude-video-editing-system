---
description: Vibe mode. Apply the user's notes in words to edit.yaml, re-render what changed, re-run QC, and turn each note into a rule
argument-hint: "<notes in plain words>"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:notes: vibe-mode revisions

Notes: `$ARGUMENTS`. Follow the `video-editor` skill (§5 vibe mode, §6 notes become rules).

## You decide
1. Split the notes into separate items. For each one, write the `edit.yaml` change it needs: which id, which param, from what to what. Read `edit.yaml` and `elements.jsonl` (with `grep`/`jq`) as text to find the right element and time. Don't open frames.
2. If a note is ambiguous ("make it punchier"), choose the most likely reading that agrees with the RULEBOOK and STYLE. State it in one line. Ask only if two readings would give clearly different cuts.
3. If a note conflicts with a RULEBOOK rule or a gate, say so in one line, and follow the note if the user confirms. A confirmed user correction outranks the RULEBOOK (precedence); it then becomes a DECISIONS entry.
4. Don't re-cut what already passed (RULEBOOK §11). Change only what the notes touch.

## Run
- Edit `edit.yaml`. Re-render only what changed: `cves render --only <id>` (or a full `cves render` if the cut changed), then `cves mix && cves encode`.
- `cves qc`, and fix until there are 0 FAILs (as in `/cves:qc`).

## Feedback → rules
For each note that would apply to future videos, write it as a general rule and open a PR on a branch (never `main`):
- An open call settled → `knowledge-base/DECISIONS.md`.
- A new rule → `knowledge-base/RULEBOOK.md` `[USER]`, plus a proposed gate row in `QC-GATES.md` if it's measurable, or a `CHECKLISTS.md` line if it isn't.
- Taste for this client only → the client's `STYLE.md`.
If you can't open a PR, put the diff in `Edit/NOTES.md` and say it still needs merging.

## Show the user
The new MP4 path (after 0 FAILs), one line per note (what you changed), the WARNINGs, and the rules or PR you created.

## Stop?
Wait for more notes.
