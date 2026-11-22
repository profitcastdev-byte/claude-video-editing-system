# Edit plan review

The editor reviews the edit plan (`Moodboard/EDIT-PLAN.html`, step 5) and leaves suggestions for Claude under each shot.
The plan shows everything it always did (summary, timeline, every shot with its build frames, words, captions, sound cues,
pre-render checks); the review controls sit on top. The aim is fewer Claude tokens per plan round:

- mechanical fixes cost zero tokens: `cves plan apply-notes` turns them into exact `edit.yaml` edits;
- Claude reads one small file (`Edit/plan_notes.pending.md`), not the page or the images;
- approved shots are locked: never re-checked, never changed, never re-rendered.

Design: `docs/superpowers/specs/2026-11-19-edit-plan-review-design.md`. Code: `engine/cves/planreview.py`.

## The loop

1. `cves moodboard` builds the plan (only the shots that changed since the last round re-render; `--full` renders all).
2. `cves review-plan [--port 8765] [--no-open] [--keep]` rebuilds the plan if it is stale, serves `Moodboard/` on
   **127.0.0.1 only** and opens the browser. It stops after the editor presses **Send** (`--keep` serves on).
3. The editor, per shot:
   - **Approve** (locks the shot);
   - **quick actions**: Bigger / Smaller, Earlier / Later (0.25 s), Swap template (only the templates valid for that
     slot), Remove, Fix caption (word → replacement);
   - a free-text **note**.

   Page level: an overall note, **Send to Claude** (writes `Edit/plan_notes.json`), **Approve all** (the plan approved, with the
   date in `Edit/NOTES.md`, then Send), **Copy notes** (the same JSON as text).
4. `cves plan apply-notes` applies the quick actions (backup `edit.yaml.bak-<time>`, comments kept when the text patch
   verifies), locks approved shots, and writes `Edit/plan_notes.pending.md`.
5. Claude reads `plan_notes.pending.md` only, makes the changes the notes ask for, and opens a shot's frames only if its
   note is visual. Then `cves moodboard` and `cves review-plan` again.

Opened as a plain file (no server), the page is read-only: Send is disabled and Copy notes still works. The editor pastes
the text to Claude, who saves it as `Edit/plan_notes.json`. Nothing leaves the machine either way: the page loads no CDN
and the server binds to 127.0.0.1, rejects other `Host` headers (DNS rebinding) and other `Origin`s, accepts only
`application/json` up to 4 MB, and serves nothing outside `Moodboard/`.

## Shots and their edit.yaml entries

Every shot carries `refs`: the `edit.yaml` entries it came from, so `apply-notes` is exact.

| shot kind | refs | key |
|---|---|---|
| cutaway | `{slot: cutaways, index, id}` | `cutaways:<id>` |
| B-roll | `{slot: broll, index, id}` (id = `id:` or `b01`, `b02`, ...) | `broll:<id>` |
| A-roll | each `roto` / `chest` entry on the segment `{slot, index, segment}`, then `{slot: zoom, segment, zoom}` | `aroll:<segment>` (`#2`... when a segment is split) |
| end card | `{slot: end_card}` | `end_card` |
| any shot with captions | `{slot: captions}` (Fix caption) | |

Entries are found by id (cutaways, broll) or segment (+ template) for roto / chest, so a ref stays exact when the list
moves. When a shot has several targets (an A-roll shot with a roto moment and a chest graphic), the page has a target
picker; each quick action records its `target` (an index into `refs`).

## Quick actions

| action | edit |
|---|---|
| Bigger / Smaller | the template's `scale` param, else its `size` param, × or ÷ 1.1 (from the template default when unset; the default is read from the template source). On an A-roll target: `aroll.zoom.<segment>` ± 0.05. A template with neither param, or a B-roll shot: **a note for Claude** (the page marks the button dashed and says so) |
| Earlier / Later | `start`, `end`, `at` and every `at` / `*_at` / `enter` / `count[0]` in `params` move by the step; `{start:clip+0.25}` placeholders keep their form. A cutaway or B-roll shot gets `snap: false` (the boundary snap would undo the move). A-roll shots and the end card: a note (their cuts are segment boundaries) |
| Swap template | `template` changes to one valid for the slot (`schema` slot kinds: cutaways = cutaway / media / overlay, roto = roto, chest = chest / overlay, end_card = end); params the new template does not take are dropped (kept when the template passes params on) |
| Remove | deletes the entry (`end_card:` key for the end card). On an A-roll shot: a note (removing speech is a `selects.yaml` change) |
| Fix caption | adds `from: to` to `captions.fixes` |

## Locks

`Edit/plan_lock.json`: `{shots: {key: {entries: {"<slot>:<id|segment>": entry hash}, approved_at, n}}}`. The hash is of
the shot's `edit.yaml` entry (`planreview.entry_hash`), so a lock follows the entry, not the shot number. `apply-notes`
refuses a quick action on a locked entry unless the shot is unlocked in the same round (the editor unticks Approve on a
locked shot, `unlock: true`, or a note that starts with "unlock"). The refusal is listed in `plan_notes.pending.md`.
A locked shot whose entry changed anyway (a hand edit) gets an "approved, then changed" badge and a moodboard warning.

## Changed shots

`Moodboard/plan_state.json` keeps, per shot key, a hash (its entries, times, captions, transitions) and its keyframes,
plus a global signature (style profile, canvas, `edl.json`, the non-shot `edit.yaml` keys, the engine version and the
template sources). The next `cves moodboard` reuses the jpgs of unchanged shots, renders only the rest (everything when
the global signature changed or with `--full`), and badges changed shots "changed since last round".

## Files

| file | written by | content |
|---|---|---|
| `Edit/plan_notes.json` | the page (Send) via `cves review-plan` | `{version, title, round, plan_sig, created, overall, approve_all, shots: [{n, key, kind, start, end, label, refs, target, frames, approved, unlock, note, actions: [{op, target, step?, template?, from?, to?}]}]}`; `applied_at` once applied |
| `Edit/plan_notes.pending.md` | `cves plan apply-notes` | the overall note and, per shot with a note or an action left over, the note, the actions that need Claude, refusals, and the frame paths |
| `Edit/plan_lock.json` | `cves plan apply-notes` | approved shots and their entry hashes |
| `Moodboard/plan_state.json` | `cves moodboard` | round, global signature, per shot hash + frames |
