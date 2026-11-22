---
description: Offer 2-3 creative treatments of the approved edit plan as fast proxies, compare them side by side, and promote the one the user picks
argument-hint: "[make|render|compare|pick <name>] [names]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:treatments: more than one idea
Arguments: `$ARGUMENTS` (default the whole loop). `skills/video-editor/reference/treatments.md`, `docs/TREATMENTS.md`.

Command detail beyond the reference:
- `make` writes one folder per treatment in `Edit/treatments/<name>/` (`edit.yaml`, `treatment.yaml`, `plan.json`) and prints the changes + a metrics table.
- `render`: proxies at half size, fast encode; plates and mattes reused, nothing re-ingested.
- `compare` (`--sequential` to hear each one) → `Edit/treatments/compare/sheet.jpg` + `compare.mp4`.
- `pick <name>` backs up `Edit/edit.yaml`, sets `Edit/treatment.yaml` as the treatment style layer, journals the choice; then `cves build`.

**Show:** the sheet + `compare.mp4`, one line per treatment (label + summary). `pick` the one the user chooses.
