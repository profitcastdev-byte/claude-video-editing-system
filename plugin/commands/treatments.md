---
description: Offer 2-3 creative treatments of the approved edit plan as fast proxies, compare them side by side, and promote the one the user picks
argument-hint: "[make|render|compare|pick <name>] [names]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:treatments: more than one idea

Arguments: `$ARGUMENTS` (default: the whole loop). Reference: `docs/TREATMENTS.md`. Run it after the edit plan (skill step 5) when the brief is open or creative; skip it when the brief, the inspirations or the brand already fix the look.

## Run
1. `cves treatments list`: built-ins `punchy`, `cinematic`, `minimal` + `PROJECT/treatments/*.yaml` (the learned `treatments.prefer` first).
2. `cves treatments make [a,b,c]`: one folder per treatment in `Edit/treatments/<name>/` (`edit.yaml`, `treatment.yaml`, `plan.json`). Read the printed changes and the metrics table.
3. `cves treatments render`: proxies at half size with a fast encode; plates and mattes are reused, nothing is re-ingested.
4. `cves treatments compare` (`--sequential` to hear each one): `Edit/treatments/compare/sheet.jpg` and `compare.mp4`.

## You decide
- Which 2-3 treatments serve `Edit/DIRECTION.md`. A client-specific take is a `PROJECT/treatments/<name>.yaml` (style keys of `default.yaml` only, plus `structure:` hints).
- Look at `sheet.jpg` once: the rows must read as clearly different, and each must be tasteful (legible captions, nothing cramped, no effect soup). Fix a weak one and make / render it again.

## Show the user
The sheet and `compare.mp4`, one line per treatment (label + summary). Wait for their choice, then `cves treatments pick <name>` (backs up `Edit/edit.yaml`, sets `Edit/treatment.yaml` as the treatment style layer, journals the choice for `cves learn`) and continue with `cves build`.
