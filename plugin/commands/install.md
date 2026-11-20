---
description: Install CVES on this machine (macOS or Windows) by following INSTALL.md step by step, then run the doctor
argument-hint: "[--check-only]"
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:install: set up the system
Options: `$ARGUMENTS`. `CVES_ROOT` per skill §0; no clone → ask where (suggest `~/claude-video-editing-system`), clone, suggest `CVES_HOME`.

1. `CVES_ROOT/INSTALL.md` is the source of truth: its steps for this OS, in order, nothing improvised. macOS `setup/install_mac.sh` (Python 3.12 venv `~/.cves/venv`, models `~/.cves/models`, RVM on MPS); Windows `setup/install_windows.ps1` (venv `%USERPROFILE%\.cves\venv`; CUDA with an NVIDIA GPU else CPU; ffmpeg + whisper.cpp release binaries).
2. **Stop** before each download / system-wide install (Homebrew, winget, model weights, Resolve, Kdenlive): what, from where, rough size; wait for OK. The user types any password / `sudo`.
3. Connectors / MCP (Resolve bridge, Kdenlive MCP, ElevenLabs, Magnific, Openverse): `TOOLS-REGISTRY.md`, only those wanted; the user enters API keys.
4. Installers run `setup/install_skills.py` (plugins superpowers, lemo-opuscar; skills effects, motionmaxxing, three.js, hypit, Remotion; `setup/skills.json`). Report the manual ones (hadi-got-motion: paid per-person licence; real-sfx, real-sound, business-motion-film, earshot: source from the repo maintainer); tell the user to restart Claude Code.
5. `cves doctor` (or `python setup/doctor.py` in the venv): all OK; fix FAILs per INSTALL.md.

`--check-only`: step 4 only.

**Show:** what was installed, doctor summary, what's left for the user (a key, an app, the Resolve bridge).
