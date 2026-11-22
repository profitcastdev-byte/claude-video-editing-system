---
description: Media assets for the edit. Declare, generate (Magnific / ElevenLabs / stock, through MCP, with cost consent), register with provenance, and check
argument-hint: "[project folder] [todo | add <id> <file> | check | list]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:assets: images, B-roll, screen recordings, overlays, voice
Request: `$ARGUMENTS`. [connectors.md](../skills/video-editor/connectors.md) for generating / downloading; `docs/MEDIA.md`.

**What the user asks for** becomes an `edit.yaml assets:` entry + a cutaway: `path:` (client file, copied to `PROJECT/Assets/`), `url:` (stock), or `generate: {provider, kind, prompt, aspect, duration}`. Templates: `image` (Ken Burns still), `video_broll`, `screen_rec` (phone / browser frame), `pip` (presenter over B-roll), `split` (before/after), `overlay_render` (RGBA export).

## Run
1. `cves assets todo "<PROJECT>"`: what's missing, as ready-to-run steps.
2. Each `generate:`: provider, model, prompt, cost **in one message**; **stop** for a clear yes.
3. MCP tool → save to the path `todo` printed (`PROJECT/Assets/<id>.<ext>`) →
   `cves assets add "<PROJECT>" --id <id> --file "<PROJECT>/Assets/<file>" --source <magnific|elevenlabs|stock|client|screen|file|url> --prompt "<prompt sent>" --model "<model>" --licence "<licence / plan>" [--url "<stock page>"]` (client / stock: `--source client|stock|file` + licence).
4. `cves assets check "<PROJECT>"` (file, sha256, source, licence per asset); `cves render --only <cutaway id>`.

**Always:** no credits without a yes; no API key in a file or command. Record source + licence (+ prompt if generated); a changed file is a new id.

**Show:** `cves assets list`, what each covers, credits spent.
