---
description: Install CVES on this machine (macOS or Windows) by following INSTALL.md step by step, then run the doctor
argument-hint: "[--check-only]"
allowed-tools: Bash, Read, Glob, Grep
---

# /cves:install: set up the system

Options: `$ARGUMENTS`. Follow the `video-editor` skill §0 to find `CVES_ROOT`. If there's no clone, ask the user where to clone the repo (suggest `~/claude-video-editing-system`), clone it, and suggest setting `CVES_HOME`.

## Run
1. Read `CVES_ROOT/INSTALL.md`. It is the source of truth. Follow its steps for this OS, in order. Don't improvise steps that aren't in it.
   - macOS: `setup/install_mac.sh` (Python 3.12 venv in `~/.cves/venv`, models in `~/.cves/models`, RVM on MPS).
   - Windows: `setup/install_windows.ps1` (venv in `%USERPROFILE%\.cves\venv`; CUDA if there's an NVIDIA GPU, otherwise CPU; ffmpeg and whisper.cpp release binaries).
2. Before each step that downloads or installs something system-wide (Homebrew, winget, model weights, apps such as DaVinci Resolve or Kdenlive), say what it is, where it comes from and roughly how big it is, and get the user's OK. The user enters any password or `sudo` prompt themselves.
3. Connectors and MCP servers (Resolve bridge, Kdenlive MCP, ElevenLabs, Magnific, Openverse) are listed in `TOOLS-REGISTRY.md`. Set up only the ones the user wants, and leave API keys for the user to enter.
4. The installers also run `setup/install_skills.py`: Claude Code plugins (superpowers, lemo-opuscar) and skills (effects, motionmaxxing, three.js, hypit, Remotion) from `setup/skills.json`. Report the manual ones it lists (hadi-got-motion is a paid per-person licence; real-sfx, real-sound, business-motion-film and the earshot skill need their source from the repo maintainer). Tell the user to restart Claude Code afterwards.
5. Run the doctor: `cves doctor` (or `python setup/doctor.py` inside the venv). Every line must be OK. Fix the FAILs by following INSTALL.md.

With `--check-only`, run only step 4.

## Show the user
What was installed, the doctor output summary, and anything left for them to do (a key to enter, an app to open, the Resolve bridge to enable).

## Stop?
Wait for the user's OK before each download or system-wide install, and for any password or key.
