# Delivery

`cves deliver` is the only way a video leaves a project. It writes a new, versioned, never-overwritten folder `Export/vNNN/`, and it refuses to run unless the master passed QC.

```
cves encode                      # Export/<title>.mp4 (settings: style `delivery:`)
cves qc                          # Edit/QC-REPORT.txt + Edit/qc.json (the QC stamp)
cves deliver                     # Export/v001/ with the master + every variant in edit.yaml `variants:`
cves deliver --only master       # master only
cves deliver --variants 4:5,cut15,music_b
```

## 1. Encoding (`cves encode`)

- **Frame rate.** From `Edit/timeline.json` `fps_rational`, else from `edl.json` `fps_rational`, else from `fps` (rationalised with denominator 1001). Nothing is hard-coded.
- **Size.** From `timeline.json` `size`. The encode refuses if the frames on disk have a different size.
- **Settings.** From the style `delivery:` section (`styles/default.yaml`):

| key | default | |
|---|---|---|
| `delivery.video.codec` | `libx264` | |
| `delivery.video.crf` | `16` | QC DEL-05 expects crf 16 |
| `delivery.video.preset` | `slow` | |
| `delivery.video.profile` | `high` | |
| `delivery.video.pix_fmt` | `yuv420p` | |
| `delivery.video.tune` | `null` | never `film` (DEL-05) |
| `delivery.video.x264_params` | `null` | appended to the colour params |
| `delivery.audio` | `aac`, `48000`, `256k` | |
| `delivery.faststart` | `true` | |
| `delivery.color` | `bt709` | matrix conversion and stream tags |

`encode.video_args(S)`, `audio_args(S)` and `stream_params(pr)` are shared by the reframe and music variants, so every delivered file is encoded the same way.

## 2. The QC stamp (`Edit/qc.json`)

`cves qc` writes `Edit/QC-REPORT.txt` and `Edit/qc.json`:

```json
{"video": "/abs/path/Export/Title.mp4", "sha256": "…", "size": 59714665,
 "fail": 0, "warn": 15, "pass": 66,
 "gates": [{"id": "DEL-01", "status": "PASS", "summary": "1080x1920"}, …],
 "created": "2026-11-18T12:02:37+00:00", "cves_version": "0.1.0", "fast": true}
```

`cves deliver` refuses unless:
1. `Edit/qc.json` exists;
2. it has `fail == 0`;
3. its `sha256` equals the master's sha256.

So re-encoding without re-running QC blocks the delivery. The error names the exact reason and the fix.

`--force-unchecked` delivers anyway. It prints a banner and writes `"WARNING"`, `"forced_unchecked": true` and the reasons at the top of `manifest.json`. The plugin hook denies `--force-unchecked` to Claude while QC is not clean, so only a human can force a delivery, from their own terminal.

## 3. The delivery folder (`Export/vNNN/`)

NNN auto-increments. The folder is built in `Export/.staging-*` and renamed at the end, so a failed delivery leaves nothing behind and an existing version is never touched.

| file | what |
|---|---|
| `<title>.mp4` | the master, byte-identical to the file QC judged (sha256 checked after the copy) |
| `<title>.srt`, `<title>.vtt` | caption events from the renderer's own caption builder (`render.Timeline(pr).caps`, cut-time phrases, fixes applied) |
| `<title>.transcript.txt` | plain transcript, one sentence per line |
| `<title>.cover.jpg` | cover / thumbnail (see below) |
| `qc.json`, `QC-REPORT.txt` | the master's QC stamp and report |
| `edit.yaml` | the edit as delivered |
| `style.yaml` | snapshot of the merged style profile (the sources are in the header comment) |
| `<title>_<variant>.mp4` | each variant that passed its QC (+ `.srt` / `.vtt` for re-timed variants) |
| `qc/<variant>.qc.json`, `qc/<variant>.QC-REPORT.txt` | each variant's QC, delivered or not |
| `manifest.json` | see below |

`manifest.json`: `version`, `created`, `cves_version`, `qc_verified`, `master`, `master_sha256`, `qc` (the master stamp summary), `fps_rational`, `size`, `cover` (`t`, `how`, `title`), `style_sources`, `variants` (`id`, `kind`, `definition`, `status` (delivered | failed), `reason`, `qc`, `notes`, `file`) and `files` (`path`, `bytes`, `sha256`, and for media `duration`, `width`, `height`, `fps`, `frames`).

### Cover

- `edit.yaml delivery.cover_t: <seconds>` picks the frame.
- Otherwise the cover is the frame in the first `delivery.cover.window_s` (3 s) with the best score for face (YuNet confidence and size) plus sharpness (Laplacian variance of the face and of the frame). Cutaway frames are penalised.
- `edit.yaml delivery.cover_title: "Rank in the *Google* map pack"` adds a title.
  - The font is `delivery.cover.title_font` (a `font_files` key). Colours are `title_color` and `title_accent` (words wrapped in `*stars*`). There is a soft shadow.
  - The title is centred in the platform safe zone at `title_y`. It moves above or below the face and the burned-in text (from `elements.jsonl`) so it never covers them.

```yaml
# edit.yaml
delivery: {cover_t: null, cover_title: "Rank in the *Google* map pack"}
```

## 4. Variants (`edit.yaml variants:`)

```yaml
variants:
  reframes: ["4:5", "1:1", "16:9"]
  hooks:     [{id: hook_b, first: [04_competitors_0], title_card: {template: <cutaway template>, duration: 1.5, params: {...}}}]
  end_cards: [{id: end_b, end_card: {params: {pill: "BOOK A CALL"}}}]
  music:     [{id: music_b, file: Music/other.wav, drop_track: 12.0, bed_lu: -8}]
  cutdowns:  [15, 30]          # or {id: cut15, seconds: 15, segments: [ids…]} to choose the shots yourself
```

`--variants` takes a comma list of variant ids, the kinds `reframes|hooks|end_cards|music|cutdowns|all`, or ad-hoc `4:5`, `1:1`, `16:9`, `cut15`, `cut30`. With no `--variants`, every variant in `edit.yaml` is built. `--only master` builds none.

**Every variant goes through QC.** A variant that fails is not copied into the delivery. The manifest lists it as `failed` with the failing gates, and its QC report is kept under `qc/`. A variant cannot pass a gate the master failed, so fix the master first.

### Reframes (any master to any aspect: 4:5, 1:1, 16:9, 9:16, 2.39:1 …)

Prefer a native canvas (`canvas.size`, [FORMATS.md](FORMATS.md)) when the edit is designed for one aspect; reframes are the
fast way to more aspects from one QC'd master, whatever its own aspect:
- **narrower target** (e.g. a 16:9 master to 9:16 or 1:1): the crop keeps the full height and moves horizontally
  (`axis: x`), the face centred, captions and chest text kept whole;
- **wider target** (e.g. 9:16 to 4:5, or 16:9 to 2.39:1): the crop keeps the full width and moves vertically (`axis: y`);
- **portrait master to a landscape target** (9:16 to 16:9): a foreground crop on a blurred fill (below);
- the same aspect as the master is refused.
Ad-hoc aspects may be decimal (`--variants 2.39:1`).

Reframes are cut from the QC'd master. The source is the lossless `Edit/frames` when they are exactly the master's frames (same count, none newer than the master); otherwise it is the decoded master. The audio is copied from the master.

- **Crop.** Along one axis (above); the rules below are written for the vertical case and apply the same way horizontally.
  - On A-roll shots it follows the face: YuNet is run on every A-roll frame of the master, so zooms, snaps and lifts are already baked in. The face centre sits at `delivery.reframe.face_y` (0.40) of the new frame.
  - **Smoothing.** A shot gets one static crop whenever a single crop can hold the face and the captions for the whole shot. Otherwise the crop follows a smoothed path (`smooth_s`, Gaussian, clamped to the constraints).
  - The crop never moves across a cut. Shots are split at segment starts, cutaway in/out points, snap in/out points and the end card.
- **Captions.** Caption and chest text boxes from `elements.jsonl` are hard constraints: the crop shifts to keep them whole. If the text and the face cannot both fit, the text wins. The face frames this costs are counted (`RF-FACECUT` WARN, `notes.face_frames_cropped_for_captions`).
- **Graphics.** On cutaway and end-card shots, one crop per shot is centred on everything drawn in that shot. Elements taller than the frame are listed in `notes.graphics_cropped` (`RF-GFX` WARN).
- **16:9 from a portrait master.** A `delivery.reframe.wide_fg` (4:5) crop on the same path is placed in the centre, over a blurred (`fill_blur`), dimmed (`fill_dim`) and scaled copy of the frame.
- **Reframe QC** (`qc/<id>.qc.json`):
  - `RF-00`: the master stamp is clean;
  - `DEL-01/02/03`, `COL-01`: size, constant frame rate equal to the master's, codec/profile/pix_fmt/AAC/faststart, bt709 tags;
  - `RF-LEN`: the frame count matches the master;
  - `RF-AUD`: the audio is copied;
  - `RF-CAP`: no caption frame cropped (FAIL);
  - `RF-FACE`: a face is detected in the encoded reframe on at least 95 % of the sampled A-roll frames where the master had one (WARN from 80 %, FAIL below);
  - `RF-FACECUT`, `RF-GFX`: WARNs.

### Re-timed variants (hooks, cut-downs) and end cards

These variants build a variant project in a temp folder:
- the top-level folders and the large `Edit/` inputs (plates, mattes, faces) are symlinked;
- the small inputs are copied;
- outputs (`frames/`, `stems/`, `mix*.wav`, `timeline.json`, `elements.jsonl`, `qc.json`) are never linked, so nothing writes back into the real project.

The variant project then runs `render → mix → encode → qc --fast` and gets its own SRT and VTT.

**Re-timing.** `edl.json` gets the new segment order. Then:
- `words.json` and `voice_final.wav` are rebuilt from the segment slices, with 4 ms fades only at new joins;
- `edit.yaml` times are shifted per segment: cutaways, roto, chest, `aroll.snap`, `captions.hide`, `sfx.extra`, `transitions` and `music.drop_cut`.

Cutaways, roto and chest graphics are rigid: they move with their shots. One whose shots are not all kept together is dropped, and the manifest notes it. Template params shift when they are numbers within 1.5 s of the item's span and are not a known non-time key (`value`, `size`, `y`, `width`, …).

- **Hooks.** `first:` takes segment ids or select (clip) ids; those shots open the video and the rest follow in order. `title_card:` places a cutaway template over the first `duration` seconds and replaces any cutaway there. Its params are cut-time seconds of the variant.
- **Cut-downs.**
  - Beat tags drive the selection. `delivery.cutdown.keep` (H, C) is kept whole; `compress` (P, A, PR, O) is filled by word-importance density until the target length minus the end card.
  - Word importance counts non-stopwords, with bonuses for `qc.topic_keywords` and `brand_tail` words, numbers and prices, and long words.
  - Shots tied together by a cutaway or chest graphic move as one unit.
  - **Sentence coherence.** The fill uses only units that open on a sentence start and can end on a sentence end. A kept shot followed by a dropped one is tail-trimmed back to its last sentence or clause end, cut in the gap before the next word (`edl.json` `out`). Plates decode from their first frame, so heads cannot be trimmed. A shot that opens or ends mid-sentence anyway (usually inside the kept H/C beats) is listed in the variant `notes`. The cut can therefore come in under the target length.
  - Without beat tags, the first and last units are kept and the rest is greedy by word importance. If H plus C alone are too long, they are trimmed by importance too.
  - QC uses `qc.duration = [0.6 × target, target + tolerance_s]`.
- **End cards.** `end_card:` is deep-merged over the master's end card, then the variant is re-rendered (no re-timing).
- **Music.** The keys are deep-merged over `music:`. The variant is re-mixed and re-muxed only: the picture is stream-copied from the master. It is QC'd as a full project.

## 5. The blocking hook (`plugin/hooks/qc_guard.py`)

The hook is registered for `PreToolUse` and `PostToolUse` on Bash. It needs only the standard library and runs under `python3` or `python`.

**PreToolUse** denies (`permissionDecision: deny`, with the reason) when:
- a command copies, moves or uploads something out of a project's `Export/` and QC is not clean for it;
  - commands covered: `cp`, `mv`, `rsync`, `scp`, `rclone`, `ditto`, `robocopy`, `xcopy`, `copy`, `move`, `install`, `gsutil`, `aws s3`, `gh release create|upload`, `curl -T|--upload-file|-F x=@file|--data-binary @file`;
  - "clean" means one of these:
    - inside `Export/vNNN/`, the folder's `manifest.json` has `qc_verified: true`, no `forced_unchecked`, and the master still matches `master_sha256`;
    - elsewhere in `Export/`, `Edit/qc.json` exists, has `fail == 0`, and its sha256 matches (the file itself, if it is a master in `Export/`);
- the command is `cves deliver --force-unchecked` while `Edit/qc.json` is missing, failing or stale.

Copies from `Export/` to `Export/` in the same project are allowed. A bug inside the guard lets the command through rather than blocking the session.

**PostToolUse** keeps the reminder after `cves render|mix|encode`, and the FAIL count after `cves qc|build`.

Test it by piping sample JSON:
```sh
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","cwd":"<project>","tool_input":{"command":"cp Export/Title.mp4 ~/Desktop/"}}' \
  | python3 plugin/hooks/qc_guard.py
```
