---
description: Control mode. Export a layered DaVinci Resolve project and drive Resolve live through the davinci-resolve-mcp bridge
argument-hint: "[project folder]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:resolve: control mode in DaVinci Resolve

Project: `$ARGUMENTS`. Follow the `video-editor` skill (§5 control mode). The edit should already have passed `cves qc`. If it hasn't, run `/cves:render` first.

## Run
1. `cves export resolve` → `Export/control/`: `media/aroll/*.mov` (ProRes 422 HQ), `media/cutaways/*.mov`, `media/overlays/*.mov` (ProRes 4444 with alpha), `media/audio/{voice,music,sfx}.wav`, `captions.srt`, `timeline.otio`, `timeline.fcpxml` and `CONTROL.md` (ARCHITECTURE §7).
2. Check the bridge. Resolve must be open (the Free version works), with **Workspace > Scripts > CursorBridge** running (`hiteshK03/davinci-resolve-mcp`; setup in `TOOLS-REGISTRY.md` / `INSTALL.md`). Look for the Resolve MCP tools in this session. If they're missing, tell the user how to start the bridge and continue with step 4 alone.
3. Drive it live through the MCP tools: create or open the project at the source fps, import `timeline.fcpxml` (or build V1 A-roll / V2 cutaways / V3 overlays / A1 voice / A2 music / A3 sfx, plus subtitles from `captions.srt`), and set the render preset to 1080×1920, H.264, bt709.
4. Without the bridge: tell the user to import `timeline.fcpxml` via File > Import > Timeline and relink to `Export/control/media/`.

## You decide
- Live changes (trims, order, levels, subtitle text, moves) go through MCP.
- **Baked graphics** (text inside a cutaway card, a roto card) can't change in Resolve: change `edit.yaml`, run `cves render --only <id>` (final frames) and `cves control update --only <id>` (just that layer, same path, `layers.json` refreshed), then relink that clip (Replace Clip). `--only` takes cutaway / segment ids, `roto.N`, `chest.N`, `end_card`, `captions`, `audio`, time ranges `12.5-14.0` and frame ranges `300-420`.
- Keep `edit.yaml` in step with whatever you change live, so the vibe path stays valid.

## Show the user
What is on each track, what they can change by hand, what needs a re-render (from `CONTROL.md`), and the bridge status.

## Bring the user's edits back
When the user has edited by hand and wants the vibe path to follow: have them save (File > Export > Timeline > FCPXML (and File > Export > Subtitle > SRT)), then run `cves import-edits --from resolve <file> --captions <edited.srt>`. Read `Edit/IMPORT-REPORT.md` with the user: what was applied to `edit.yaml` / `selects.yaml` (backups are kept), the **Not mapped** list (effects, new media, transitions, titles: these stay editor-only), and the next commands (`cves select && cves prep` if the cut changed, then `cves render`, `cves mix`, `cves encode`, `cves qc`). Use `--dry-run` first if unsure. Resolve's FCPXML export was not tested live; check the report the first time (docs/CONTROL-MODE.md §4a).

## Stop?
The user now edits by hand. When they export from Resolve, run `/cves:qc` on that file before it's delivered. It must pass the same final-file gates.
