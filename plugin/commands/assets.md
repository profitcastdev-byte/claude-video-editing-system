---
description: Media assets for the edit. Declare, generate (Magnific / ElevenLabs / stock, through MCP, with cost consent), register with provenance, and check
argument-hint: "[project folder] [todo | add <id> <file> | check | list]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:assets: images, B-roll, screen recordings, overlays, voice
Request: `$ARGUMENTS`. [connectors.md](../skills/video-editor/connectors.md) for generating / downloading; `docs/MEDIA.md`.

**Decide:** where a real picture explains a beat better than a drawn card (shop, app, before/after, product), add an `edit.yaml assets:` entry + a cutaway: `path:` (client file, copied to `PROJECT/Assets/`), `url:` (stock), or `generate: {provider, kind, prompt, aspect, duration}`. Templates: `image` (Ken Burns still), `video_broll`, `screen_rec` (phone / browser frame), `pip` (presenter over B-roll), `split` (before/after), `overlay_render` (RGBA export).

## Run
1. `cves assets todo "<PROJECT>"`: what's missing, as ready-to-run steps.
2. Each `generate:`: provider, model, prompt, cost **in one message**; **stop** for a clear yes.
3. MCP tool → save to the path `todo` printed (`PROJECT/Assets/<id>.<ext>`) →
   `cves assets add "<PROJECT>" --id <id> --file "<PROJECT>/Assets/<file>" --source <magnific|elevenlabs|stock|client|screen|file|url> --prompt "<prompt sent>" --model "<model>" --licence "<licence / plan>" [--url "<stock page>"]` (client / stock: `--source client|stock|file` + licence).
4. `cves assets check "<PROJECT>"` to 0 problems (= AST-01); `cves render --only <cutaway id>`, read the frame before showing it.

**Rules:** no credits without a yes; no API key in a file or command. Every asset: source + licence (+ prompt if generated); a changed file is a new id. No real people, client logos or claims in generated pictures (claims come from `Brand/claims.md` via templates). Vertical: subject in the centre 60 %; upscale anything shown above 1.0x (MOT-14).

**Show:** `cves assets list`, what each covers, credits spent, one frame per new cutaway; then back to the step that asked.
