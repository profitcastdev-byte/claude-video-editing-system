---
description: Update CVES. Pulls the latest system from git, updates the plugin, and re-runs the doctor
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:update: pull the latest system
`CVES_ROOT` per skill §0. **Stop** on local changes, a failed pull, or a doctor FAIL you can't fix.

1. `git -C "<CVES_ROOT>" status --short`: changes → show them; never stash / discard without the user's OK.
2. `git -C "<CVES_ROOT>" pull --ff-only`; no fast-forward → report.
3. `git -C "<CVES_ROOT>" log --oneline ORIG_HEAD..HEAD` + new `CHANGELOG.md` entries.
4. `setup/requirements*.txt` changed → INSTALL.md's dependency step (e.g. `pip install -r` in `~/.cves/venv`).
5. `cves doctor` (or `python setup/doctor.py`); fix FAILs per INSTALL.md.
6. Git-marketplace plugin → the user runs `/plugin marketplace update cves`, then restarts Claude Code (or `/reload-plugins`).

**Show:** old → new commit, CHANGELOG highlights (rules, gates, templates), doctor result, restart needed or not.
