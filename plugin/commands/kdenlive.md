---
description: Control mode, fallback. Export a layered Kdenlive project and edit it through the Kdenlive MCP server
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:kdenlive: control mode in Kdenlive

Project: `$ARGUMENTS`. Follow the `video-editor` skill (§5). Use this when the Resolve bridge isn't available, or when the user prefers Kdenlive. The edit should already have passed `cves qc`.

## Run
1. `cves export kdenlive` → `Export/control/project.kdenlive` (MLT XML written directly, with a profile at the project's own rate and size), plus the shared layered media, stems, `captions.srt` and `CONTROL.md` (ARCHITECTURE §7).
2. Look for the Kdenlive MCP tools in this session (`12bijaya/MCP_Server_Kdenlive`, setup in `TOOLS-REGISTRY.md`). They edit the `.kdenlive` file. After each batch of changes, tell the user to reload the project in Kdenlive (File > Revert, or reopen it).
3. Without the MCP server: give the user the path to `project.kdenlive`, and make any changes by re-exporting.

## You decide
- Timeline changes (trims, order, levels, subtitles) go through the MCP or a re-export.
- Baked graphics change only through `edit.yaml` → `cves render --only <id>` → `cves control update --only <id>` (same media path, so a reload in Kdenlive picks it up; never rewrite `project.kdenlive` over the user's edits).
- Keep `edit.yaml` in step with what you change.

## Show the user
The project path, the track map, what they can change by hand, what needs a re-render, and when to reload.

## Bring the user's edits back
When the user has edited by hand and wants the vibe path to follow: have them save (File > Save), then run `cves import-edits --from kdenlive <file>`. Read `Edit/IMPORT-REPORT.md` with the user: what was applied to `edit.yaml` / `selects.yaml` (backups are kept), the **Not mapped** list (effects, new media, transitions, titles: these stay editor-only), and the next commands (`cves select && cves prep` if the cut changed, then `cves render`, `cves mix`, `cves encode`, `cves qc`). Use `--dry-run` first if unsure. Resolve's FCPXML export was not tested live; check the report the first time (docs/CONTROL-MODE.md §4a).

## Stop?
The user edits by hand. Run `/cves:qc` on their export before delivery.
