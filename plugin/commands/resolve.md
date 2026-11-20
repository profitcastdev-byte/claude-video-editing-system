---
description: Control mode. Export a layered DaVinci Resolve project and drive Resolve live through the davinci-resolve-mcp bridge
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:resolve: control mode in DaVinci Resolve
Project: `$ARGUMENTS`. `skills/video-editor/reference/modes.md`. Must already pass `cves qc`, else `/cves:render`.

1. `cves export resolve` → `Export/control/`: `media/aroll/*.mov` (ProRes 422 HQ), `media/cutaways/*.mov`, `media/overlays/*.mov` (ProRes 4444 + alpha), `media/audio/{voice,music,sfx}.wav`, `captions.srt`, `timeline.otio`, `timeline.fcpxml`, `CONTROL.md` (ARCHITECTURE §7).
2. Bridge: Resolve open (Free works), **Workspace > Scripts > CursorBridge** running (`hiteshK03/davinci-resolve-mcp`; `TOOLS-REGISTRY.md` / `INSTALL.md`). No Resolve MCP tools → tell the user how to start it; step 4 only.
3. Via MCP: project at the source fps, import `timeline.fcpxml` (or build V1 A-roll / V2 cutaways / V3 overlays / A1 voice / A2 music / A3 sfx + subtitles from `captions.srt`), render preset 1080×1920, H.264, bt709. Live changes (trims, order, levels, subtitle text, moves) go through MCP.
4. No bridge: the user File > Import > Timeline `timeline.fcpxml`, relinks to `Export/control/media/`.

**Baked graphics** (card text, roto card): `edit.yaml` → `cves render --only <id>` → `cves control update --only <id>` (that layer, same path, `layers.json` refreshed) → Replace Clip. `--only` takes cutaway / segment ids, `roto.N`, `chest.N`, `end_card`, `captions`, `audio`, `12.5-14.0` (s), `300-420` (frames). Keep `edit.yaml` in step with live changes.

**Show:** each track's content, what's hand-editable, what needs a re-render (`CONTROL.md`), bridge status.

**Their edits back:** they File > Export > Timeline > FCPXML (+ Subtitle > SRT); `cves import-edits --from resolve <file> --captions <edited.srt>` (`--dry-run` if unsure). Walk `Edit/IMPORT-REPORT.md` with them: applied to `edit.yaml` / `selects.yaml` (backups kept), **Not mapped** (effects, new media, transitions, titles: editor-only), next commands (`cves select && cves prep` if the cut changed, then `cves render`, `cves mix`, `cves encode`, `cves qc`). FCPXML export is untested live; check the report the first time (docs/CONTROL-MODE.md §4a).

**Stop:** the user edits by hand; `/cves:qc` their export (same final-file gates) before delivery.
