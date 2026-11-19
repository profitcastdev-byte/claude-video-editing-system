# Learning: your notes become taste

CVES gets better with every edit without ever changing the look behind your back. It **journals** what happens on each
video, **mines** the journals for repeated patterns, and **proposes** them. A person **promotes** a pattern, and only
then does it become part of the style (a learned layer) or a rule. Every promotion is recorded and can be reverted.

```
journal (per project)  ->  cves learn mine  ->  candidates  ->  promote (a person)  ->  learned.yaml / rules
   build qc deliver          corrections         list / show      personal (local)        merged into the
   import-edits revisions    correlations        reject --why     or --share (repo,        style profile
   notes ratings results     note clusters                         anonymised)             (docs/STYLE.md)
```

## 1. Where the data lives (and what is shared)

| file | where | shared? | holds |
|---|---|---|---|
| `PROJECT/Edit/journal.jsonl` | client project | **no** (client folder) | append-only events: time, cves version, style hash + the event |
| `PROJECT/Edit/journal.last_edit.yaml` | client project | no | edit.yaml as of the last build (for revision diffs) |
| `PROJECT/Edit/critique/` | client project | no | contact sheet, energy timeline, `critique.json`, `CRITIQUE.md` |
| `PROJECT/Edit/review/` | client project | no | review packs per round, `findings.json`, `REVIEW.md`, sign-offs ([REVIEW.md](REVIEW.md)) |
| `~/.cves/taste/candidates.jsonl` | your machine | **no** | proposed patterns with evidence (project / version refs, quoted notes) |
| `~/.cves/taste/learned.yaml` | your machine | no | your personal learned layer; may hold `client:<name>` sections |
| `~/.cves/taste/rules.md` | your machine | no | personal learned rules |
| `~/.cves/taste/promotions.jsonl`, `rejected.jsonl` | your machine | no | who promoted / rejected what, and why |
| `~/.cves/taste/study.json` | your machine | no | measurements of studied videos (no media, file names only) |
| `knowledge-base/taste/learned.yaml` | the repo | **yes** (git) | the team's learned layer: global / goal / platform sections only |
| `knowledge-base/TASTE.md` | the repo | yes | one anonymised line per shared pattern: pattern, scope, n, effect, date |
| `LESSONS.md` (section "Learned by `cves learn`") | the repo | yes | shared rule-type patterns, anonymised |

**Privacy rules.** The repo is public. Shared entries carry no client names, no project names, no file paths and no
quoted notes: only the pattern, its scope, the sample size and the effect. `client:` scopes can never be shared
(`--share` refuses them). Before writing, `cves learn promote --share` replaces every client name it knows (from the
journals under the projects root) and anything path-like, and refuses to write if a name is still there.
`$CVES_TASTE` moves the personal folder (default `~/.cves/taste`); `$CVES_KB_DIR` moves the repo knowledge base (tests).

## 2. The journal
`cves` writes these events itself (a journal failure prints one line and never breaks the command):

| event | written by | content |
|---|---|---|
| `revision` | `cves build` / `cves encode` | edit.yaml diff since the previous build (`changes: [{path, old, new}]`), `after_notes` = a note came in between |
| `build` | `cves build` / `cves encode` | the decisions: goal, platform, spine (when present), caption style / size / position, transition kinds, bed level, pacing, templates and motion pieces used, style sources |
| `qc` | `cves qc` / `cves build` | fail / warn counts and the gate ids |
| `deliver` | `cves deliver` | version, variants and their status, forced or not, the decisions (as `build`) |
| `import-edits` | `cves import-edits` | what the human changed in Resolve / Kdenlive, as an edit.yaml diff + the importer's applied list |
| `critique` | `cves critique` | which version was reviewed |
| `review` | `cves review build` | round, loop, pack folder, finding counts, QC FAIL count, the kinds of the high findings |
| `review-apply` | `cves review apply` | the safe patches applied (`[{id, kind, changes: [{path, old, new}]}]`) |
| `review-signoff` | `cves review signoff` | verdict (`ship` / `revise`), Claude's notes, the high / med findings still open, rounds used, cap reached ([REVIEW.md](REVIEW.md)) |
| `treatments-make` / `-render` / `-compare` | `cves treatments` | the treatments built, rendered or compared, with their plan metrics ([TREATMENTS.md](TREATMENTS.md)) |
| `treatment-pick` | `cves treatments pick` | the treatment chosen, the ones offered, goal / client / platform, its metrics and the edit.yaml diff it brought |

And these by hand (Claude runs them during the workflow, `plugin/skills/video-editor/SKILL.md`):

```
cves learn note "the user's words, verbatim" [--version v002]
cves learn rate v002 8 --why "hook is great, CTA rushed" [--by owner|client|claude] [--scores hook=8,story=7,...]
cves learn approve v002 [--why ".."]        cves learn reject v002 --why ".."
cves learn results v002 --platform meta --hook-rate 0.31 --hold 0.18 --ctr 0.012 --roas 2.4 [any_key=value ...]
cves learn journal [--tail 20]
```
Run them inside the project folder or pass `--project`. A note or rating without `--version` belongs to the last
delivered version.

## 3. Mining
`cves learn mine [--root DIR]` reads every `Edit/journal.jsonl` under the projects root (`$CVES_CLIENTS`, config
`clients_root`, else `~/CVES Projects`) and proposes candidates of four kinds:

- **Repeated corrections**: the same kind of change made by people at least twice (in the editor, or in edit.yaml after a
  note): a style key raised or lowered, a value switched (transition kind, caption style), a template deleted. A style key
  becomes a style change (the median of the values people chose); anything else becomes a rule.
- **Outcome correlations**: decisions that went with better ratings (human ratings; approvals count as 8, rejections as 3)
  or better results (any metric logged with `results`). Needs **n ≥ 3** versions with that outcome; below that the
  report says so and proposes nothing. Effect thresholds: +1 rating point, or +15% on a result metric.
- **Note clusters**: notes grouped by topic (captions, music, SFX, pace, transitions, colour, zoom, hook, brand, motion)
  and direction (more / less, faster / slower) that recur. Some map to a style nudge (louder music = `sound.bed_lu` +2
  LU, bigger captions = `captions.size` +10%, faster = `grammar.max_shot_s` −0.5 s); the rest become rules.
- **Treatment preferences**: `treatment-pick` events per client and per goal. The same treatment picked at least twice and
  in at least 60% of that scope's picks becomes a `treatments.prefer` style change for that scope (`client:<name>` or
  `goal:<ad|viral>`); once promoted, `cves treatments list / make` offer it first.

Each candidate has an id, a plain-words statement, a proposed style change (`key → value`) or rule text, a scope
(`global`, `client:<name>` (local only), `goal:ad|viral`, `platform:<name>`, joinable with `+`), evidence (project /
version refs: local only), n, effect and a confidence. The report also compares Claude's self-ratings with human ratings.

## 4. Promotion (always a person)
```
cves learn list [--all]                       candidates (new; --all includes promoted)
cves learn show L1a2b3c4                      full candidate with its evidence
cves learn promote L1a2b3c4 [--scope goal:viral]           -> ~/.cves/taste/learned.yaml (or rules.md)
cves learn promote L1a2b3c4 --scope global --share         -> knowledge-base/taste/learned.yaml + TASTE.md (+ LESSONS.md for rules)
cves learn reject L1a2b3c4 --why "only for that one client"   never proposed again
cves learn forget L1a2b3c4                    revert a promotion (restores the previous value, removes the shared lines)
```
Only keys that exist in `engine/cves/styles/default.yaml` can be learned; `promote` refuses any other. Shared changes
reach teammates with the next `git pull` (open a PR as for any repo change; `CONTRIBUTING.md`).

## 5. How learned taste is applied
`style.load()` merges `default → repo learned → personal learned → preset → inspire (Edit/style.yaml) → treatment
(Edit/treatment.yaml) → Brand → edit.yaml style:` (docs/CONTRACTS.md §1). A learned file holds `scopes: {<scope>: {style keys}}`; only sections whose scope matches
the project apply (goal from `edit.yaml goal:`, platform from `edit.yaml platform.target`, client from `project.client`;
a project without a goal matches only `global` and its client / platform sections). General sections merge first,
specific ones last. `S["_sources"]` lists `learned:repo` / `learned:personal` when they applied. Because the preset, the
measured inspirations, the brand and the edit come later, learned taste is a better *default*, never an override of a
client's look.

## 6. Taste study
`cves learn study <folder>` (e.g. `~/CVES Projects/_Taste`) measures great videos you collected. Put a `notes.txt` beside
them, one line per video: `file.mp4 | ad|viral | why it's great` (without it, sub-folders `ad/` and `viral/` set the kind).
Each video goes through `cves inspire`'s analysis (pacing, shot lengths, first cut, face share, loudness; a plain
frame-difference pass if that is unavailable). Per kind it writes medians to `~/.cves/taste/study.json` and proposes
`goal:ad` / `goal:viral` candidates when n ≥ 3. Media is never copied; only measurements and file names are stored.

## 7. The senior-editor loop
1. Creative direction before the plan (`Edit/DIRECTION.md`, knowledge-base/CREATIVE.md §1).
2. After QC passes: `cves critique`, fill `CRITIQUE.md`, fix anything below 7 that is fixable, log the scores with
   `cves learn rate ... --by claude`.
2b. Then the review loop ([REVIEW.md](REVIEW.md)): `cves review build`, look at the pack, fix, re-render, until 0 FAIL and no high
   findings (max 3 rounds), and `cves review signoff` records the verdict and what was still wrong.
3. After every user note: `cves learn note "<their words>"`. After delivery: ask for a 1–10 rating and log it; log
   platform results when the user has them.
4. Every few deliveries: `cves learn mine`, show the user the new candidates, and promote only what they approve.
