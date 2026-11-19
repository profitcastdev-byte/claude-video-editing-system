# QC: tiers, speed and the measurement cache

`cves qc` judges the delivered master against every measurable gate in `knowledge-base/QC-GATES.md` and writes
`Edit/QC-REPORT.txt` + the delivery stamp `Edit/qc.json` (docs/DELIVERY.md). This page covers how to run it cheaply while
iterating and why the full run is fast without measuring anything differently.

## Tiers

| Tier | Command | What it runs | Writes | Deliverable |
|---|---|---|---|---|
| full | `cves qc` / `qc.run(pr, video)` | every gate | `QC-REPORT.txt`, `qc.json` | yes, when 0 FAIL |
| fast | `cves qc --fast`, `cves build` / `qc.run(..., fast=True)` | every gate except the CUT-01 / CUT-03 whisper re-checks | `QC-REPORT.txt`, `qc.json` | yes, when 0 FAIL |
| draft | `cves qc --draft` / `qc.run(..., tier="draft")` | the cheap gates (`engine/cves/qc/tiers.py` `DRAFT`): file format, loudness, timeline, element log, word timings, stems, SFX cue list, motion curves | `QC-DRAFT.txt`, `qc_draft.json` (`"tier": "draft", "deliverable": false`) | **never** |

The draft tier decodes no frames, detects no faces, runs no whisper and skips the retention pass, so it misses every
picture gate (faces, mattes, halos, skin, caption pixels, text contrast, black frames, luma range), the speech re-checks
and RET-*. Each gate it does run is measured by the same code as the full run (a test holds them equal). It never writes
`Edit/qc.json` (`write_stamp` refuses), so `cves deliver` and the `qc_guard` hook cannot mistake it for the delivery QC.
Every report line that matters says DRAFT. Use it between edits; run `cves qc` before delivery.

## How the full run is fast

- **Families run side by side.** The extra gates (`qc/extra.py`: captions, motion, graphics, frame, colour, sound) run in
  a worker process (`qc/_worker.py`); ffmpeg probes, the whisper re-checks and the retention decode run on threads; the
  OpenCV picture pass streams in the main process with YuNet on a worker thread. Rows are joined in the order the serial
  run emitted them, so the report and the stamp are byte-identical to a serial run (`CVES_QC_PROCS=0 CVES_QC_JOBS=1`).
- **Fewer decodes.** blackdetect, the COL-02 luma sample and the retention grey frames come from one ffmpeg split graph
  (byte-identical to three commands). The master's loudness is measured with `-vn`. FFV1 plates / mattes decode per GOP
  up to the last wanted frame, on threads, while the master decodes. PyAV decodes the master with frame threads.
- **No frame lists in memory**, vectorised loops (FRAME-02 longest run), low-res luma only where SND-07 reads it.
- **Whisper** calls (CUT-01 chunks, CUT-03 segments, STORY-10 tail) run 3 at a time (`CVES_QC_WHISPER_JOBS`).

## The measurement cache (`Edit/qc_cache/`)

Keyed by the master's sha256 (a new render is a new key; the last 4 masters are kept):

| Entry | Holds | Read by |
|---|---|---|
| `picture.npz` | frame steps, face flags, frame-0 luma, frame count | `cves qc` re-runs |
| `media.npz` | black runs, COL-02 counts, retention grey frames | `cves qc` re-runs |
| `extra-<key>.json` + mattes | the extra gates' frame measurements; `<key>` hashes every input (element log, timeline, faces, words, edit.yaml, resolved style, plate / matte files, `extra.py` itself) | `cves qc` re-runs |
| `review_gray.npz` | the small grey frames `cves review build` detects on | review re-runs (frames are then only grabbed) |
| `earshot.json` | `earshot measure` of the master, keyed by the earshot install | review re-runs |
| `whisper/<hash>.txt` | whisper transcripts keyed by the audio bytes + model + language + prompt | every QC run |

So `cves build` (fast QC) followed by `cves qc` (full) on the same master re-measures nothing but what the full tier
adds. `CVES_QC_CACHE=off` disables the cache. `CVES_QC_TIMING=1` prints wall-clock / CPU checkpoints per family.

The parity proof (benchmark ad and demo projects, before vs after, gate by gate) is in `knowledge-base/DECISIONS.md`
"QC speed"; `python tools/qc_parity.py BEFORE/qc.json AFTER/qc.json` compares two stamps.
