---
description: Render, mix and encode the edit into the master MP4 (or a fast half-size draft)
argument-hint: "[project folder] [--only <id>] [--draft]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:render: render, mix, encode
Project / options: `$ARGUMENTS`.

- `cves build`: render (incremental: only frames whose inputs changed) + mix + encode → `Export/<title>.mp4`. Or `cves render && cves mix && cves encode`.
- `cves build --draft`: half size, fast encode, its own `Edit/draft/` (the final build's frames are untouched).
- One element: `cves render --only <id>` (cutaway / segment ids, `roto.N`, `chest.N`, `end_card`, `12.5-14.0` s, `300-420` frames), then `cves mix && cves encode`.
- `cves validate` reports edit.yaml errors first (`cves render` / `cves build` stop on them).
- Long jobs: run in the background; read the text output, not frames.

**Show:** the MP4 path, duration and what changed. Then wait for the user.
