---
description: Update CVES. Pulls the latest system from git, updates the plugin, and re-runs the doctor
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:update: pull the latest system

Follow the `video-editor` skill §0 to find `CVES_ROOT`.

## Run
1. `git -C "<CVES_ROOT>" status --short`. If there are local changes, stop and show them. Don't stash or discard them without the user's OK.
2. `git -C "<CVES_ROOT>" pull --ff-only`. If it can't fast-forward, report it and stop.
3. Show what changed: `git -C "<CVES_ROOT>" log --oneline ORIG_HEAD..HEAD`, plus the new `CHANGELOG.md` entries.
4. If `setup/requirements*.txt` changed, re-run the dependency step from `INSTALL.md` (for example, `pip install -r` inside `~/.cves/venv`).
5. Re-run the doctor: `cves doctor` (or `python setup/doctor.py`). Fix the FAILs by following INSTALL.md.
6. Plugin: if the plugin was installed from the git marketplace, tell the user to run `/plugin marketplace update cves`, then restart Claude Code (or run `/reload-plugins`). Plugin changes load after a restart.

## Show the user
The old → new commit, the CHANGELOG highlights (especially new rules, gates or templates), the doctor result, and whether a restart is needed.

## Stop?
Only on local changes, a failed pull, or a doctor FAIL you can't fix.
