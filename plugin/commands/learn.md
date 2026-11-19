---
description: Self-learning. Log notes, ratings and results; mine every project journal for repeated patterns; promote, reject or forget them (only with the user's approval)
argument-hint: "[note \"..\" | rate vNNN 1-10 | results vNNN ... | mine | list | show ID | promote ID [--share] | reject ID --why | forget ID | study FOLDER]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:learn: notes become taste
Arguments: `$ARGUMENTS`. Skill §6, `skills/video-editor/reference/learning.md` (rate, approve / reject, results, mine, promote only on a yes); `docs/LEARNING.md`.

**Logging** (in the project, or `--project`): notes verbatim, never paraphrased (`cves learn note "<exact words>" [--version vNNN]`); `cves learn reject vNNN --why ".."`; results take any `key=value` (e.g. `--platform meta --hook-rate 0.31 --hold 0.18 --ctr 0.012 --roas 2.4`); your critique scores `--by claude --scores hook=..,story=..` (`/cves:critique`). Build, QC, deliver, import-edits and critique journal automatically.

**Mining** (no project needed): `cves learn mine` (or `--root <projects folder>`); the report flags n < 3 and compares your self-ratings with the user's. Show only **new** candidates, one line each: statement, change (`key → value` or the rule), scope, n, effect, confidence. `cves learn show <id>` = evidence: quote it to the user, never to the repo. **Ask** which to promote:
- this user: `cves learn promote <id> [--scope goal:viral|platform:meta|client:<name>|global]`;
- team: `--scope global|goal:..|platform:.. --share` → anonymised lines in `knowledge-base/TASTE.md`, `knowledge-base/taste/learned.yaml`, and for rules `LESSONS.md`; commit on a branch + PR (CONTRIBUTING.md). Client-scoped patterns can't be shared;
- not wanted: `cves learn reject <id> --why "<their words>"` (never proposed again); changed mind: `cves learn forget <id>`.
The next build picks promotions up via the style merge (`S["_sources"]`: `learned:personal` / `learned:repo`).

**Taste study:** `cves learn study "<folder>"` (videos + `notes.txt` lines `file | ad|viral | why it's great`): measurements only, never media; proposes `goal:ad` / `goal:viral` candidates once a kind has ≥ 3 videos; present like mined ones.

**Show:** what was logged, or the candidates and what you promoted / rejected on their say-so, with file paths.
