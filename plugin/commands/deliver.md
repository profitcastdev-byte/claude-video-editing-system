---
description: Deliver the master and its variants (reframes, cut-downs, hooks, end cards, music) into a versioned Export/vNNN/ folder with captions and a cover
argument-hint: "[--variants 4:5,1:1,16:9,cut15,...] [--only master] [--video FILE]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:deliver: delivery
Arguments: `$ARGUMENTS`. `docs/DELIVERY.md`.

`cves deliver` delivers the newest `Export/*.mp4` (or `--video FILE`, a `cves build --draft` master included) into a new, never-overwritten `Export/vNNN/`: the master, SRT + WebVTT + transcript, a cover JPG, `edit.yaml` + the merged style, the variants, `manifest.json` (files, sha256, durations, sizes).

**Variants** (`edit.yaml variants:`; no `--variants` = all): `reframes: ["4:5", "1:1", "16:9"]`, `cutdowns: [15, 30]`, `hooks: [{id, first: [segment or select ids], title_card: {...}}]`, `end_cards: [{id, end_card: {...}}]`, `music: [{id, file, drop_track, drop_cut, bed_lu}]`. Cover: `delivery.cover_t`, `delivery.cover_title` (`*stars*` words take the accent colour).

## Run
- `cves deliver $ARGUMENTS` (`--only master` for the master alone); re-timed variants re-render, minutes each.
- `Export/vNNN/manifest.json`: each variant `delivered`, or `failed` + the reason it did not render.
- `music.slot: platform`: `POSTING.md` and `<master>.guide.wav` are in the folder (the master has no music by design).

**Show:** the `Export/vNNN/` path, delivered files, failed variants and why. Don't attach files.
