# Edit plan review page (approved 2026-11-19)

## Intent
Editors review the edit plan (`Moodboard/EDIT-PLAN.html`) and leave suggestions for Claude under each shot. The plan stays fully comprehensive; the review controls are added on top. The goal is to cut Claude tokens per plan round:
- mechanical fixes cost zero tokens;
- Claude reads one small notes file instead of the page or the images;
- approved shots are never re-checked or re-rendered.

## Unchanged
EDIT-PLAN.html keeps everything it shows today:
- the summary header;
- the multi-track timeline;
- every shot with every build frame, words, on-screen content, framing, transitions, captions and sound cues;
- the pre-render check results.

EDIT-PLAN.md and moodboard.jpg are still written.

## New
- **Per shot:**
  - an **Approve** checkbox, which locks the shot;
  - **quick actions**: Bigger / Smaller, Earlier / Later (±0.25 s, a step in style), Swap template (a dropdown of the templates valid for that slot), Remove, and Fix caption word (from → to);
  - a free-text **note** box.
- **Page level:**
  - an overall note box;
  - **Send to Claude**, which saves `Edit/plan_notes.json`;
  - **Approve all**, which records approval 2 in `Edit/NOTES.md` with the date;
  - **Copy notes**, which copies the same JSON as text, for when the page is opened away from the Mac.

## How it runs (approach A, chosen by the owner)
- `cves review-plan [--port N] [--no-open]` builds the plan if it is stale, serves `Moodboard/` on 127.0.0.1 only, and opens the browser. The page POSTs to the local server, which writes `Edit/plan_notes.json` atomically. No data leaves the machine.
- Opened as a plain file, the page still works read-only, with Copy notes as the fallback.
- `cves plan apply-notes` applies the quick actions as exact `edit.yaml` edits (comment-preserving where possible, with a backup) and writes `Edit/plan_notes.pending.md` listing only the free-text notes and the shots they concern. That file is what Claude reads.
- **Locks:** approved shots are recorded in `Edit/plan_lock.json`. A later round:
  - must not change a locked shot's `edit.yaml` entries unless a note on that shot unlocks it;
  - re-renders only the changed shots (the moodboard frames of changed shots; the final build uses the incremental render cache when present);
  - shows "changed since last round" badges.
- The `plugin/commands/moodboard.md` step and the editor skill switch to:
  1. run `cves review-plan`;
  2. wait for the editor's Send;
  3. run `cves plan apply-notes`;
  4. read `plan_notes.pending.md` only;
  5. open the frames of a shot only if its note is visual.

## Out of scope
- Online or client review (option C).
- Several people editing one plan at the same time.

## Done means
- Tests:
  - each quick action changes exactly the right `edit.yaml` key;
  - locks are respected;
  - notes JSON round-trips;
  - the server binds to localhost only;
  - the page renders with and without the server.
- Lint, gate check and full suite pass.
- `docs/` and the plugin are updated, with a CHANGELOG entry.
