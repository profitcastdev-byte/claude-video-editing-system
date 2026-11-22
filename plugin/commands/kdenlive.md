---
description: Control mode, fallback. Export a layered Kdenlive project and edit it through the Kdenlive MCP server
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:kdenlive: control mode in Kdenlive
Project: `$ARGUMENTS`. `skills/video-editor/reference/modes.md`; when the Resolve bridge isn't available or the user prefers Kdenlive.

1. `cves export kdenlive` → `Export/control/project.kdenlive` (MLT XML, profile at the project's rate and size) + layered media, stems, `captions.srt`, `CONTROL.md` (ARCHITECTURE §7).
2. Kdenlive MCP (`12bijaya/MCP_Server_Kdenlive`, `TOOLS-REGISTRY.md`) edits the `.kdenlive`: trims, order, levels, subtitles. After each batch the user reloads (File > Revert, or reopen). No MCP: give the path; change by re-export.
3. Baked graphics: `edit.yaml` → `cves render --only <id>` → `cves control update --only <id>` (same path, a reload picks it up; never rewrite `project.kdenlive` over the user's edits). Keep `edit.yaml` in step.

**Show:** project path, track map, what's hand-editable, what needs a re-render, when to reload.

**Their edits back:** they File > Save; `cves import-edits --from kdenlive <file>` (`--dry-run` if unsure). Walk `Edit/IMPORT-REPORT.md` with them: applied to `edit.yaml` / `selects.yaml` (backups kept), **Not mapped** (effects, new media, transitions, titles: editor-only), next commands (`cves select && cves prep` if the cut changed, then `cves render`, `cves mix`, `cves encode`). Resolve's FCPXML export is untested live; check the report the first time (docs/CONTROL-MODE.md §4a).

The user edits by hand from here.
