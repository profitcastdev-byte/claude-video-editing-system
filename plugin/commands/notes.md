---
description: Vibe mode. Apply the user's notes in words to edit.yaml, re-render what changed, re-run QC, and turn each note into a rule
argument-hint: "<notes in plain words>"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:notes: vibe-mode revisions
Notes: `$ARGUMENTS`. Skill §5 (vibe), §6 (notes become rules: journal, fix, generalise, PR).

1. **Journal each note verbatim first** (`cves learn note`, skill §6); the next build journals your `edit.yaml` change so `cves learn mine` spots repeats.
2. One item per note → the `edit.yaml` change (id, param, from → to), found as text in `edit.yaml` / `elements.jsonl` (`grep` / `jq`); no frames.
3. Ambiguous ("make it punchier"): likeliest reading consistent with RULEBOOK and STYLE, stated in one line; ask only if two readings give clearly different cuts.
4. Conflicts with a rule or gate: say so in one line; follow it if the user confirms (precedence) and it becomes a DECISIONS entry.
5. Change only what the notes touch (RULEBOOK §11).
6. `cves render --only <id>` (full `cves render` if the cut changed), `cves mix && cves encode`, `cves qc` to 0 FAIL; `/cves:critique` (fix < 7 unless the notes forbid it, log scores); `/cves:review` to no high findings (max 3 rounds), sign off.
7. Future-proof notes → general rules on a branch + PR per skill §6 (no PR → diff in `Edit/NOTES.md`, say it still needs merging).

**Show** (0 FAIL): MP4 path, one line per note, WARNINGs, rules / PR made; offer new `cves learn mine` candidates touching these notes (`/cves:learn`). Then wait for more notes.
