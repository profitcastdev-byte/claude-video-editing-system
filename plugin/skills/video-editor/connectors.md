# Connectors: generating and sourcing media through MCP

The `cves` engine runs locally and **cannot call MCP tools**. You (Claude) generate or source media through the connectors in this
session, save the file into the project, and register it with `cves assets add`. The engine then renders it through the media
templates in [docs/MEDIA.md](../../../docs/MEDIA.md). Never put API keys in `edit.yaml`, the repo or a command line. The connectors hold
their own auth.

## The loop (run it once per asset)
1. **Read what is needed.** Run `cves assets todo "<PROJECT>"`. It prints every `edit.yaml assets.<id>` that has no file yet, with its `generate:`
   spec (`provider`, `kind`, `prompt`, `aspect`, `duration`), the tool to use, the target filename and the exact register command.
2. **Ask before spending credits.** Tell the user, in one message for the whole batch: each asset, the provider and model, the prompt,
   and the cost. Check the cost with the provider's estimate or balance tool if it has one (Magnific: `simulate_cost` / `account_balance`).
   Wait for a clear yes. Stock *search* is free; stock *download* and every generation are not.
3. **Call the MCP tool** (table below). Find the exact tool names in this session with ToolSearch (e.g. `images_generate`, `audio_tts`);
   connector names differ between installs. Poll long jobs with the provider's wait or status tool. Never loop a generation to "try again"
   without asking: each try costs credits.
4. **Download the result into `PROJECT/Assets/`** with the filename `cves assets todo` printed (`Assets/<id>.<ext>`). Use the connector's
   download tool, or `curl -L -o "<PROJECT>/Assets/<id>.<ext>" "<signed url>"` on the URL the tool returned. Don't put the URL in the edit.
5. **Register it with its provenance**:
   ```bash
   cves assets add "<PROJECT>" --id <id> --file "<PROJECT>/Assets/<id>.<ext>" --source magnific|elevenlabs|stock \
        --prompt "<the exact prompt sent>" --model "<model name>" --licence "<plan / licence the provider states>" [--url "<stock page>"]
   ```
6. **Check it.** `cves assets check "<PROJECT>"` must print 0 problems, then `cves render --only <cutaway id>`. Read the rendered frame
   before showing it to the user.

Provenance is mandatory: QC gate AST-01 fails on an asset with no source or licence, on a generated asset with no prompt, and on a file
that changed after it was registered (sha256). If you edit a file after registering it (crop, upscale, background removal), register the result
as a **new id** with `--source` of the tool that made it and `--notes "from <old id>"`.

## Which tool for which asset
| `generate.kind` | provider | MCP tool (typical name) | notes |
|---|---|---|---|
| `image` | magnific (Freepik) | `images_generate` | Ask for the edit's aspect (`aspect: "9:16"` full bleed, `"1:1"` or `"4:5"` for a card). If the result is smaller than the box it fills, run `images_upscale` (MOT-14 fails above 1.0x raster scale). |
| `rgba` / `cutout` | magnific | `images_remove_background` (stills), `video_remove_background` (clips) | PNG / ProRes with alpha → `overlay_render` or a card with `fit: contain`. |
| `upscale` | magnific | `images_upscale`, `video_upscale` | Register as a new id. |
| `video` | magnific | `video_generate` (image-to-video: generate or pick the still first, then animate it) | 5–10 s clips; set `in`/`out` in the template. Check that people, logos and text in the clip are acceptable for an ad. |
| `image` / `video` (stock) | stock | `stock_search` → `stock_download` (Freepik), or a footage-search connector | Search is free. Record the licence the result states (e.g. "Freepik Premium licence", "Pexels licence") and the item page as `--url`. |
| `voice` | elevenlabs | `audio_tts` / `generate_speech` (`list_voices` to pick the voice) | VO pickups and tags. Store the voice id in `generate.voice`. |
| `sfx` | elevenlabs | `audio_sfx_generate` | Also usable as a named SFX: copy it to `PROJECT/Music/sfx/<name>.wav` and reference it in `sfx.extra`. |
| `music` | elevenlabs (or magnific) | `audio_music_generate` | Follow `/cves:music` for drop placement; the credits go in `Music/CREDITS.md` too. |
| screen recording | – | – | The user records it, or you capture one with a browser connector. Register it with `--source screen --licence "own recording"`. |
| client file | – | – | `--source client --licence client-owned`. |

## Writing prompts
- Describe what the frame must *show* for the spoken line it covers, not the brand look. The look comes from the style (cards,
  radii, colours) and the grade.
- Vertical first: put the subject in the centre 60 % of the frame, so the Ken Burns crop and the platform UI never cut it.
- Never generate a real person, a client's logo, a competitor's brand, or text that makes a claim. Claims come from `Brand/claims.md` and
  are drawn by templates.
- Keep the prompt you sent verbatim. It goes into `--prompt`.

## Example
```yaml
# edit.yaml
assets:
  clinic: {generate: {provider: magnific, kind: image, prompt: "bright modern dental clinic reception, morning light, photoreal, vertical", aspect: "9:16"},
           licence: "Freepik Premium"}
cutaways:
  - {id: c2, template: image, start: 15.43, end: 17.81, params: {asset: clinic, zoom: [1.0, 1.1]}}
```
`cves assets todo` → ask the user ("1 image on Magnific, about N credits. OK?") → yes → `images_generate(prompt=…, aspect_ratio=9:16)` →
download to `Assets/clinic.png` → `cves assets add … --id clinic --source magnific --prompt "…" --model "<model>" --licence "Freepik Premium"` →
`cves assets check` → `cves render --only c2`.
