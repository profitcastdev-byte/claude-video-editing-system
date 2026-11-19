---
description: Self-learning. Log notes, ratings and results; mine every project journal for repeated patterns; promote, reject or forget them (only with the user's approval)
argument-hint: "[note \"..\" | rate vNNN 1-10 | results vNNN ... | mine | list | show ID | promote ID [--share] | reject ID --why | forget ID | study FOLDER]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:learn: notes become taste

Arguments: `$ARGUMENTS`. The full reference is `docs/LEARNING.md`. Follow the `video-editor` skill (§6).

## Logging (inside the project, or with `--project`)
- Every user note, verbatim: `cves learn note "<their exact words>" [--version vNNN]`. Don't paraphrase it.
- After a delivery, ask the user for a 1-10 rating and why: `cves learn rate vNNN <score> --why "<their words>"` (`--by client` when it is the client's verdict).
- Approvals: `cves learn approve vNNN` / `cves learn reject vNNN --why ".."`.
- Platform results when the user has them: `cves learn results vNNN --platform meta --hook-rate 0.31 --hold 0.18 --ctr 0.012 --roas 2.4` (any `key=value` works).
- Your own critique scores: `cves learn rate vNNN <overall> --by claude --scores hook=..,story=..` (see `/cves:critique`).
Build, QC, deliver, import-edits and critique are journaled automatically.

## Mining (no project needed)
1. `cves learn mine` (or `--root <projects folder>`). Read the report: it says when a pattern has too little data (n < 3) and how your self-ratings compare with the user's.
2. Show the user the **new** candidates in plain words: one line each with the statement, the proposed change (`key → value` or the rule), the scope, n, the effect and the confidence. `cves learn show <id>` has the evidence; quote it to the user, never to the repo.
3. **Ask** which to promote. Never promote on your own.
   - Approved for this user only: `cves learn promote <id> [--scope goal:viral|platform:meta|client:<name>|global]`.
   - Approved for the team: `cves learn promote <id> --scope global|goal:..|platform:.. --share`. This writes anonymised lines into `knowledge-base/TASTE.md`, `knowledge-base/taste/learned.yaml` and, for rules, `LESSONS.md`. Commit them on a branch and open a PR (CONTRIBUTING.md). Client-scoped patterns can't be shared.
   - Not wanted: `cves learn reject <id> --why "<their words>"`. It is never proposed again.
   - Changed their mind: `cves learn forget <id>` reverts it.
4. After a promotion, the next build picks it up through the style merge (`S["_sources"]` shows `learned:personal` / `learned:repo`).

## Taste study
`cves learn study "<folder>"`: a folder of great videos with `notes.txt` lines `file | ad|viral | why it's great`. It stores measurements only (never media) and proposes `goal:ad` / `goal:viral` candidates once a kind has 3 or more videos. Present them like mined candidates.

## Show the user
What was logged, or the candidate list and what you promoted / rejected on their say-so, with file paths.
