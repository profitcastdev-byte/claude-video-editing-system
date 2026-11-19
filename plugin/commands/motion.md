---
description: Preview the HTML motion pieces (m_* templates) as contact sheets, single frames or clips before using them in edit.yaml
argument-hint: "[piece] [params JSON] [WxH]"
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:motion: preview motion pieces
Arguments: `$ARGUMENTS` (piece, optional params JSON, optional size). Choosing: `skills/video-editor/reference/motion.md`, `docs/MOTION.md`.

1. `cves motion list`: pieces, kinds, params (`!` = required), hero or not (`cves templates <name>` for one piece's docs).
2. `cves motion preview <piece> --params '<JSON>' --size <WxH> --out <Moodboard/motion-<piece>.png>` (`--project .` in a project: its style + `Brand/motion/` pieces). Size defaults to the canvas; check delivery and variant aspects (`1080x1920`, `1920x1080`). `--params` times are piece-relative (edit.yaml: cut time). `--at 2.0` one full frame; `--out clip.mp4` the motion; `--bg video` over a mid-tone footage stand-in (legibility worst case).
3. Read the PNG once (one sheet per piece and size): type not cramped / clipped, in the safe zone, readable contrast, build order reads, nothing pops in.

Chromium missing: `python -m playwright install chromium` in the CVES venv (or re-run the installer).

**Show** (only if they asked for options): sheet path(s), one line per piece on why it fits the beat.
