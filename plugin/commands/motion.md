---
description: Preview the HTML motion pieces (m_* templates) as contact sheets, single frames or clips before using them in edit.yaml
argument-hint: "[piece] [params JSON] [WxH]"
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:motion: preview motion pieces

Arguments: `$ARGUMENTS` (a piece name, optional params JSON, optional size). Follow the `video-editor` skill (section "Motion pieces") and `docs/MOTION.md`.

## Run
1. `cves motion list` (inside a project, add `--project .` to `preview` to use its style and `Brand/motion/` pieces): every piece, its kinds, params (`!` = required) and whether it is a hero piece.
2. `cves motion preview <piece> --params '<JSON>' --size <WxH> --out <Moodboard/motion-<piece>.png>`:
   - the size defaults to the style's canvas; check both the delivery aspect and any variant aspect (e.g. `1080x1920` and `1920x1080`);
   - times in `--params` are piece-relative seconds (in edit.yaml they are cut-time seconds);
   - `--at 2.0` writes one full-size frame instead of the contact sheet; `--out clip.mp4` writes the motion (ffmpeg from the CVES config);
   - `--bg video` previews an overlay over a mid-tone stand-in for footage (the legibility worst case).
3. Read the PNG once (images are expensive: one contact sheet per piece and size). Check: type not cramped or clipped, inside the safe zone, readable contrast, the build order reads, nothing pops in.

If Chromium is missing the command says so: run `python -m playwright install chromium` in the CVES venv (or re-run the installer).

## Show the user
Only when they asked to see options: the contact sheet path(s) and one line per piece on why it fits the beat.
