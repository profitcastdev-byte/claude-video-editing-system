---
description: Step 8. Deliver the QC'd master and its variants (reframes, cut-downs, hooks, end cards, music) into a versioned Export/vNNN/ folder
argument-hint: "[--variants 4:5,1:1,16:9,cut15,...] [--only master]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:deliver: step 8, delivery
Arguments: `$ARGUMENTS`. `docs/DELIVERY.md`.

**Before:** `cves qc` **0 FAIL** on the current master (`Edit/qc.json` holds the judged sha256; re-encoded since → `cves qc` again, a stale stamp is refused). Review loop signed off: no high findings, or the notes say why (`cves review show`). Never copy, move or upload out of `Export/` yourself (the hook denies it unless QC is clean); `cves deliver` is the only path. Never run `--force-unchecked` (hook-blocked); only a human may, from their own terminal (marked in the manifest).

**Variants** (`edit.yaml variants:`; no `--variants` = all): `reframes: ["4:5", "1:1", "16:9"]`, `cutdowns: [15, 30]`, `hooks: [{id, first: [segment or select ids], title_card: {...}}]`, `end_cards: [{id, end_card: {...}}]`, `music: [{id, file, drop_track, drop_cut, bed_lu}]`. Cover: `delivery.cover_t`, `delivery.cover_title` (`*stars*` words take the accent colour).

## Run and check
- `cves deliver $ARGUMENTS` (`--only master` for the master alone); re-timed variants re-render, minutes each.
- `Export/vNNN/manifest.json`: `delivered` / `failed` + reason. Failed → `qc/<id>.QC-REPORT.txt`, fix `edit.yaml` (a re-timed variant can drop a cutaway whose shots were split), deliver again (new `vNNN`; never overwritten).
- Look at the cover JPG and one frame per reframe first.
- `music.slot: platform`: `POSTING.md` and `<master>.guide.wav` present; tell the user the master has no music on purpose and pass on POSTING.md (sound, start point, drop).

**Show:** `Export/vNNN/` path, delivered files, failed variants and why, QC WARNs. Don't attach files. **After:** rating + why, later platform numbers (`--platform meta --hook-rate .. --hold .. --ctr ..`), `cves learn mine` every few deliveries: `skills/video-editor/reference/learning.md`, `/cves:learn`.
