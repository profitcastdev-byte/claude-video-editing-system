---
description: Media assets for the edit. Declare, generate (Magnific / ElevenLabs / stock, through MCP, with cost consent), register with provenance, and check
argument-hint: "[project folder] [todo | add <id> <file> | check | list]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /cves:assets: images, B-roll, screen recordings, overlays, voice

Request: `$ARGUMENTS`. Follow the `video-editor` skill, plus [connectors.md](../skills/video-editor/connectors.md) for anything that needs
generating or downloading. Templates and parameters: `docs/MEDIA.md`.

## You decide: what the edit needs
For each spoken beat that a real picture explains better than a drawn card (the client's shop, the app, a before/after, a product), add an
entry under `edit.yaml assets:` and a cutaway that uses it:
- `path:` for files the client gave you (copy them into `PROJECT/Assets/` first);
- `url:` for stock you found;
- `generate: {provider, kind, prompt, aspect, duration}` for anything to be made.

The template choice:
- `image`: a still with Ken Burns;
- `video_broll`: a clip;
- `screen_rec`: a recording in a phone or browser frame;
- `pip`: the presenter over B-roll;
- `split`: before/after;
- `overlay_render`: an RGBA motion-graphic export.

## Run
```bash
cves assets todo "<PROJECT>"      # what is still missing, as ready-to-run steps
```
1. For every `generate:` item: show the user the provider, the model, the prompt and the cost, **in one message**. Generate only after a clear yes.
2. Call the MCP tool, save the file to the path `todo` printed (`PROJECT/Assets/<id>.<ext>`), then:
   ```bash
   cves assets add "<PROJECT>" --id <id> --file "<PROJECT>/Assets/<file>" --source <magnific|elevenlabs|stock|client|screen|file|url> \
        --prompt "<prompt sent>" --model "<model>" --licence "<licence / plan>" [--url "<stock page>"]
   ```
3. For client files and stock: run the same `add` with `--source client|stock|file` and the licence.
4. Then:
   ```bash
   cves assets check "<PROJECT>"     # 0 problems before rendering (QC gate AST-01 enforces the same)
   cves render --only <cutaway id>   # read the frame before you show it
   ```

## Rules
- Never spend credits without the user's yes; never put an API key in a file or a command.
- Every asset needs a source and a licence. A generated one also needs its prompt. If you change a registered file, register the result as a new id.
- No real people, client logos or claims in generated pictures. Claims are drawn by templates from `Brand/claims.md`.
- Vertical framing: keep the subject in the centre 60 %. Upscale anything shown above 1.0x its size (MOT-14).

## Show the user
The asset list (`cves assets list`), what each one covers in the edit, the credits spent, and one rendered frame per new cutaway.

## Stop?
For the cost consent before any generation or paid download. Otherwise go back to the step that asked for the assets.
