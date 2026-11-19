---
description: Step 8. Deliver the QC'd master and its variants (reframes, cut-downs, hooks, end cards, music) into a versioned Export/vNNN/ folder
argument-hint: "[--variants 4:5,1:1,16:9,cut15,...] [--only master]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:deliver: step 8, delivery

Arguments: `$ARGUMENTS`. The full reference is `docs/DELIVERY.md`.

## Before
- `cves qc` must show **0 FAIL** on the current master. `Edit/qc.json` carries the sha256 of the file QC judged. If you re-encoded after QC, run `cves qc` again: delivery refuses a stale stamp.
- The review loop (`/cves:review`) is signed off for this master: no high findings left, or the sign-off notes say why (`cves review show`).
- Do not copy, move or upload anything out of `Export/` yourself. The plugin hook denies it unless QC is clean, and `cves deliver` is the only supported path.
- Never run `cves deliver --force-unchecked`. The hook blocks it while QC is not clean. Only a human may force an unchecked delivery, from their own terminal. It is marked in the manifest.

## Variants
Put the variants in `edit.yaml` under `variants:`; with no `--variants`, every variant listed there is built.
- `reframes: ["4:5", "1:1", "16:9"]`;
- `cutdowns: [15, 30]`;
- `hooks: [{id, first: [segment or select ids], title_card: {...}}]`;
- `end_cards: [{id, end_card: {...}}]`;
- `music: [{id, file, drop_track, drop_cut, bed_lu}]`.

Optional cover settings:
- `delivery.cover_t` picks the cover frame;
- `delivery.cover_title` adds a title (words in `*stars*` take the accent colour).

## Run
`cves deliver $ARGUMENTS` (default: everything in `variants:`; `--only master` for the master alone). Re-timed variants re-render, so allow a few minutes each.

## Check
- Read `Export/vNNN/manifest.json`: each variant shows `delivered` or `failed` with a reason.
- For each failed variant, read `qc/<id>.QC-REPORT.txt` and fix the cause in `edit.yaml` (a re-timed variant can drop a cutaway whose shots were split up). Then deliver again. A new `vNNN` is created; old versions are never overwritten.
- Look at the cover JPG and one frame of each reframe before telling the user.
- `music.slot: platform` (organic post, trending sound): check `POSTING.md` and `<master>.guide.wav` are in the folder; tell the user the master has no music on purpose and pass on POSTING.md (the sound, its start point, the drop).

## Show the user
Tell the user:
- the `Export/vNNN/` path;
- the delivered files;
- any failed variants and why;
- the WARN list from QC.

Do not attach files.

## After delivery: ask and log
- Ask the user for a 1-10 rating of the delivered version and one line why. Log it: `cves learn rate vNNN <score> --why "<their words>"` (`--by client` for the client's verdict); an explicit sign-off is `cves learn approve vNNN`, a refusal `cves learn reject vNNN --why ".."`.
- When the user later shares platform numbers, log them: `cves learn results vNNN --platform meta --hook-rate .. --hold .. --ctr ..`.
- Every few deliveries, run `cves learn mine` and offer the new candidates (`/cves:learn`); promote only what the user approves.
