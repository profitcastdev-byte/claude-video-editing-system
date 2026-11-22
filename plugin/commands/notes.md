---
description: Apply the user's notes in words to edit.yaml and re-render what changed
argument-hint: "<notes in plain words>"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:notes: changes in words
Notes: `$ARGUMENTS`.

1. One item per note → the `edit.yaml` (or `selects.yaml`) change (id, param, from → to), found as text in `edit.yaml` / `elements.jsonl` (`grep` / `jq`); no frames.
2. Change only what the notes say. Ambiguous ("make it punchier") → ask one short question, or state the reading you took in one line if the user prefers you decide.
3. `cves render --only <id>` (full `cves render` if the cut changed), `cves mix && cves encode`; `cves select` first if `selects.yaml` changed.
4. The user wants notes kept for learning → `cves learn note "<their exact words>"` (`/cves:learn`).

**Show:** the MP4 path and one line per note (what changed). Then wait for more notes.
