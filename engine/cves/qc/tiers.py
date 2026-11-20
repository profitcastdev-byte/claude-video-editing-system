"""QC tiers (docs/QC.md "Tiers"). Delivery always needs the full QC: `cves deliver` and the qc_guard hook read only
Edit/qc.json, which the draft tier never writes.

  full   every gate (`cves qc`)
  fast   every gate except the two whisper re-transcriptions CUT-01 / CUT-03 (`cves qc --fast`, `cves build`)
  draft  the cheap gates for iteration (`cves qc --draft`): file format, loudness, the timeline, the element log, word
         timings, the stems and the SFX cue list. No frame decode, no face detection, no whisper, no retention pass.
         Each gate it runs is measured exactly as in the full run. It writes Edit/QC-DRAFT.txt + Edit/qc_draft.json,
         says DRAFT on every line that matters and can never stamp a master deliverable.

A draft PASS is not a delivery PASS: it skips the picture gates (faces, mattes, halos, skin, caption pixels, text
contrast, black frames, luma range), the speech re-checks and the retention gates."""

TIERS = ("full", "fast", "draft")

# the gates the draft tier runs (all others are skipped, and listed as skipped in the report)
DRAFT = frozenset([
    # delivery: probe + container
    "DEL-01", "DEL-02", "DEL-03", "DEL-04", "DEL-05", "COL-01",
    # timeline + element log
    "CUT-05", "FRAME-09", "FRAME-11", "FRAME-01", "PLAT-01", "PLAT-02", "GFX-01", "GFX-23", "ELEMENT-LOG", "ELEMENT-LOG-X",
    "CUT-04", "RET-12",
    # loudness, stems, voice timing
    "SND-01", "SND-02", "SND-03", "SND-04", "SND-19", "RET-03", "PLAT-11", "CUT-02", "SND-30",
    "SND-08", "SND-09", "SND-11", "SND-13", "SND-22", "SND-23", "SND-32", "SND-33",
    # words, hook text
    "RET-01", "RET-08",
    # motion + graphics from the element log
    "MOT-01", "MOT-02", "MOT-03", "MOT-04", "MOT-05", "MOT-07", "MOT-12", "MOT-14",
    "GFX-05", "GFX-08", "GFX-17", "GFX-24", "GFX-26", "COL-12",
    # assets
    "AST-01",
])


def resolve(tier=None, fast=False):
    t = tier or ("fast" if fast else "full")
    if t not in TIERS: raise ValueError(f"QC tier {t!r}: one of {', '.join(TIERS)}")
    return t
