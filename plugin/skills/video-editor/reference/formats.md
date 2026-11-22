# Format, spine and the `broll:` track (read at setup, and when writing `broll:`)
Reference: `docs/FORMATS.md`. Decide at setup and record in `Edit/NOTES.md`.

- **Canvas.** Ask where the video runs, then set `canvas.size` (style; `edit.yaml style: {canvas: {size: [w, h]}}` for one
  video): 9:16 `[1080, 1920]` Reels / Shorts / TikTok (default), 4:5 `[1080, 1350]` or 1:1 `[1080, 1080]` feed, 16:9
  `[1920, 1080]` YouTube / web, 2.39:1 `[1920, 804]` cinematic. Edit natively at the main placement; deliver other aspects
  as reframes (`cves deliver --variants 9:16,1:1`). Change the canvas of an A-roll project before `cves select`.
- **Story structure** (style `grammar.structure`, from the brief): `problem` (default; H hook, P problem, A agitation, PR proof, O offer, C CTA) when the ad sells relief
  from a pain, `offer` (H M PR R C: promise, mechanism, proof, risk reversal, CTA) when it leads with the result or offer,
  `story` (H S T PR C: setup, turn, proof) for a before/after story, `custom` with `grammar.beats`. It sets the beats you
  tag, the moodboard labels and the music turn / drop. Every `selects.yaml` clip carries `text:` (its exact words):
  `cves select` aligns each take from it.
- **Spine: what drives the cut** (`edit.yaml spine:`).
  - `aroll` (default): a presenter on camera. The workflow unchanged.
  - `voiceover`: no presenter on screen; a recorded VO, or an ElevenLabs VO the user asked for (cost confirmed, registered
    with `cves assets add --source elevenlabs --prompt "<script>"`), set as `voiceover: {asset: <id>}`. `cves ingest`
    tightens and transcribes it; the story step is the script itself.
  - `music`: no voice; a music video, montage or product loop. Set `music.file` (+ `duration`), `cves beats`, then
    `cves autocut` proposes the shots on the beat; you edit them. Text cards are cutaways (`title_card`).
  - `broll`: shot-led (travel, product, event recap): the shots and their own sound (`audio: true`), an optional music bed.
  No presenter means no `cves select` / `cves prep`, no roto or chest, no punch-ins.
- **Writing `broll:`** (cut time, against `words.json` for a VO): one entry per shot, cut where the user wants (a word or
  a beat). `fill` for footage that can be
  cropped to the canvas, `fit` for a picture that must stay whole (a vertical phone clip on 16:9), `kenburns` (default for
  stills) to keep a still alive; `anchor` keeps a subject in a fill crop; `in` picks the best moment of the clip; `speed`
  slows or speeds a shot (constant). Register non-footage files as assets (`cves assets add`). Drawn cutaways
  (title cards, stats) can sit on top and win where they overlap. On the aroll spine the same track is cutaway footage
  over the presenter (the voice and captions continue over it).
