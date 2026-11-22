# Control mode

Control mode hands the finished edit to a real editor so Claude and you can keep working on the same
project: **prompt → Claude → MCP → editor → output**. Claude drives the editor locally through an MCP
server, and you can edit by hand in the same project at any time.

| | Primary: DaVinci Resolve **Free** | Fallback: Kdenlive |
|---|---|---|
| MCP server | [hiteshK03/davinci-resolve-mcp](https://github.com/hiteshK03/davinci-resolve-mcp) (162 tools) | [12bijaya/MCP_Server_Kdenlive](https://github.com/12bijaya/MCP_Server_Kdenlive) (136 tools; on glama.ai as "kdenlive-mcp-server") |
| How it reaches the editor | An in-app bridge script (Workspace > Scripts > Utility > CursorBridge) opens `http://127.0.0.1:9876`. This works around Resolve's Studio-only external scripting. | Reads and writes the `.kdenlive` file and renders with `melt`. There is no live connection: reload the project in Kdenlive to see Claude's edits. |
| Project CVES writes | `timeline.fcpxml` + `captions.srt`, imported live by `cves export resolve --push` | `project.kdenlive` (+ `project.kdenlive.srt`) |
| Pinned commit | `f812df7ab5d376592a24fb94611473fdf3a1acb2` | `4733141efd1679fee29bfe0be481ab191eaf5f8f` |

Everything lives in the video's `Export/control/` folder (ARCHITECTURE.md §7).

---

## 1. Setup

You only need to do this once per machine. Resolve itself is not installed by the scripts: download it from
blackmagicdesign.com yourself (it asks for a registration form), run it once, then run the scripts.

### macOS

```bash
cd claude-video-editing-system
setup/control/install_resolve_bridge_mac.sh            # add --register to run the claude mcp add for you
setup/control/install_kdenlive_mcp_mac.sh              # installs Kdenlive with brew if missing; add --register
```

### Windows 10/11 (PowerShell)

```powershell
cd claude-video-editing-system
powershell -ExecutionPolicy Bypass -File setup\control\install_resolve_bridge_windows.ps1   # -Register
powershell -ExecutionPolicy Bypass -File setup\control\install_kdenlive_mcp_windows.ps1     # winget installs Kdenlive; -Register
```

What the scripts do:

1. Clone each MCP server into `~/.cves/mcp/` (Windows: `%USERPROFILE%\.cves\mcp\`) and check out the
   **pinned, reviewed commit**.
2. Apply the CVES hardening patch (section 8). Each patch refuses to run if the upstream file is not
   byte-for-byte the reviewed one, so a changed upstream fails loudly instead of being patched blindly.
3. Create a venv per server. The MCP SDK is held at `mcp>=1.26,<2` (`setup/control/constraints-mcp.txt`).
   The Resolve server's local-AI extras (Whisper, Demucs, rembg: several GB, and they download models on
   first use) are only installed with `--with-ai` / `-WithAI`.
4. Resolve: write the hardened `CursorBridge.py` into Resolve's Scripts folder:
   - macOS: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`
   - Windows: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\`
5. Kdenlive: install the custom profile `cves_vertical_hd_2398` (1080x1920, 24000/1001, the common case) into Kdenlive's
   profile folder (macOS `~/Library/Application Support/kdenlive/profiles/`, Windows
   `%APPDATA%\kdenlive\profiles\`). Kdenlive ships no vertical 23.976 profile, and without one it shows a
   "non standard framerate" error on open (its check compares against 23.98 exactly). Projects at any other
   rate or size get their own profile: `cves export kdenlive` writes it next to the project
   (`Export/control/cves_<w>x<h>_<rate>`), and `cves export kdenlive --install-profile` copies it into that folder.
   An installed profile is found by its values, whatever its file name.
6. Print the registration command.

### Claude Code registration (the exact commands)

macOS (the scripts print these with your real paths):

```bash
claude mcp add --scope user davinci-resolve -- \
  ~/.cves/mcp/davinci-resolve-mcp/venv/bin/python ~/.cves/mcp/davinci-resolve-mcp/src/resolve_mcp_bridge.py

claude mcp add --scope user kdenlive \
  -e "KDENLIVE_MCP_WORKSPACE=$HOME/CVES Projects" \
  -e "KDENLIVE_MCP_MELT=/Applications/kdenlive.app/Contents/MacOS/melt" \
  -e "KDENLIVE_MCP_EFFECTS_DIR=/Applications/kdenlive.app/Contents/Resources/effects" \
  -e "KDENLIVE_MCP_CUSTOM_PROFILE=$HOME/Library/Application Support/kdenlive/profiles/cves_vertical_hd_2398" \
  -- ~/.cves/mcp/kdenlive-mcp/.venv/bin/kdenlive-mcp
```

Windows:

```powershell
claude mcp add --scope user davinci-resolve -- "$env:USERPROFILE\.cves\mcp\davinci-resolve-mcp\venv\Scripts\python.exe" "$env:USERPROFILE\.cves\mcp\davinci-resolve-mcp\src\resolve_mcp_bridge.py"

claude mcp add --scope user kdenlive -e "KDENLIVE_MCP_WORKSPACE=$env:USERPROFILE\CVES Projects" -e "KDENLIVE_MCP_MELT=C:\Program Files\kdenlive\bin\melt.exe" -e "KDENLIVE_MCP_EFFECTS_DIR=<printed by the script>" -e "KDENLIVE_MCP_CUSTOM_PROFILE=$env:APPDATA\kdenlive\profiles\cves_vertical_hd_2398" -- "$env:USERPROFILE\.cves\mcp\kdenlive-mcp\.venv\Scripts\kdenlive-mcp.exe"
```

`KDENLIVE_MCP_WORKSPACE` is the only tree the Kdenlive server may write in. CVES points it at the
clients root, so every `Export/control/project.kdenlive` is writable and nothing else is. Start a new
Claude Code session after registering, then run `claude mcp list` to check both servers are connected.

Exporter dependencies (into the CVES venv): `pip install -r setup/control/requirements-control.txt`.

---

## 2. What `cves export` writes

```
cves export resolve  [Export/control]           timeline.fcpxml, captions.srt, timeline.otio (checked after writing)
cves export resolve --push                      ...then imports it into the running Resolve through the bridge
cves export resolve --push-subtitles            snapshot, then replace the subtitle track from layers.json
cves export resolve --snapshot "before-trim"    save the open Resolve project as snapshots/<time>-before-trim.drp
cves export kdenlive [Export/control]           project.kdenlive + project.kdenlive.srt, checked with melt
cves export kdenlive --render check.mp4         ...and render it headless with melt as proof it plays
cves export kdenlive --install-profile          ...and copy the project's rate/size profile into Kdenlive's profile folder
cves export all --no-build                      rewrite the project files from the current layers.json (no re-render)
cves export selftest [--no-gui]                 synthetic layers at two rates and two sizes -> both exporters -> checks (section 9)
cves control update [PROJECT] --only c3         re-render just those layers into Export/control/media + refresh layers.json
cves import-edits [PROJECT] [--from resolve|kdenlive|fcpxml|otio] FILE [--captions edited.srt] [--dry-run]
                                                map the human's edits back onto edit.yaml / selects.yaml (section 4a)
```

The same exporters run as `python -m cves.export <target> ...` from `engine/`.

**Frame rate and size come from the project.** `layers.json` carries the project's `fps` (`timeline.json`
`fps_rational`, else `edl.json`) and `size` (`timeline.json`, else `edl.json`, else the renderer's frame size).
Every exporter reads them from there: the FCPXML `frameDuration` and format, Resolve's project settings, the
Kdenlive `<profile>` and the SRT grid. Nothing in the exporters assumes 23.976 or 1080x1920.

`--push` runs, in order: create the project (or snapshot and load it if it exists) → set 23.976 and
1080x1920 **before** any media lands in the pool (Resolve locks the frame rate after that) → import all
media → import `timeline.fcpxml` against the pool (or let Resolve import the clips itself if that fails)
→ set `Alpha mode = Straight` on every V3 overlay → name the tracks → put `captions.srt` on subtitle
track 1 at the timeline start → save. Any step the API refuses is listed under `manual` in the output
instead of failing the import.

### Why the FCPXML looks like this

Checked against Apple's FCPXML 1.10 DTD and against what Resolve-tested exporters write, not against memory:

- **`version="1.10"`**: the newest version every Resolve from 18 up accepts; 1.11+ needs Resolve 21.
- **`frameDuration` is one frame at the project's rate**: 23.976 → `1001/24000s`, 25 → `1/25s`,
  29.97 → `1001/30000s`. Every time is a whole frame written as a reduced rational (frame 96 at 23.976 →
  `1001/250s`). The checker rejects any time off the project's frame grid.
- **Any size:** the sequence uses `name="FFVideoFormatRateUndefined"` with explicit `width`/`height`
  (vertical sizes have no named FCP format). Media formats use FCP's name for a standard raster
  (`FFVideoFormat1080p25`) and a custom `FFVideoFormat<w>x<h>p<rate>` otherwise (`FFVideoFormat1080x1920p2398`),
  always with explicit width, height and frameDuration. Resolve takes the timeline size from these attributes.
- **Tracks:** the spine is a single `<gap>` the length of the timeline, and every layer is a
  connected `<asset-clip>` on a lane: V1/V2/V3 → lanes 1/2/3, A1/A2/A3 → lanes -1/-2/-3. Resolve maps lanes to
  tracks in order, so tracks stay put even where V1 has gaps. Audio clips carry `audioRole`
  (dialogue/music/effects), and video clips carry `<adjust-conform type="fit"/>`.
- **Media paths:** absolute `file://` URLs with spaces, non-ASCII (the `’` in this Mac's folder names) and RFC 3986
  sub-delimiters percent-encoded. Resolve fails to relink raw sub-delimiters. Clip names are the file
  name *with* extension, because Resolve relinks by file name.
- **Timecode:** `tcStart="0s"`. Media without embedded timecode starts at `0s`. Media with a
  `timecode` tag starts there, so Resolve does not flag a mismatch.
- **Alpha** is a media-pool clip attribute in Resolve, not an FCPXML field, so the bridge sets it after import.
- Each clip carries `<note>cves:<id> edit:<edit.yaml ref></note>`, so a clip in Resolve can be traced back to `edit.yaml`.

Sources: Apple FCPXML 1.10 DTD (mirrored by CommandPost); palmier-pro's FCPXMLExporter (encoding facts
"reverse-engineered from Resolve round-trips": version allow-list, `FFVideoFormatRateUndefined`,
single-gap + lanes, sub-delimiter encoding, relink by file name); Resolve-exported FCPXML samples
(ltcsync issue #26); the Resolve scripting README (ImportTimelineFromFile options, AppendToTimeline
clipInfo, SetClipProperty); the Blackmagic forum on ProRes 4444 Alpha Mode.

### Why the .kdenlive looks like this

The file is written directly as MLT XML in Kdenlive's current format (document version 1.1, Kdenlive
23.04+). otio-kdenlive-adapter 0.0.3 writes the pre-2023 layout, which current Kdenlive silently loses
clips from. The structure follows Kdenlive's `dev-docs/fileformat.md` and source (DocumentChecker,
ProjectItemModel::loadBinPlaylist, DocumentValidator, SubtitleModel), cross-checked with the Kdenlive
MCP writer:

- Each track is a tractor holding two playlists. The sequence tractor lists black, then A3 A2 A1 V1 V2 V3.
- There is one always-on `qtblend` per video track and one `mix` per audio track, so V3's alpha composites over V2 over V1.
- Each media file has a bin `<chain>` plus a dedicated chain per placement, sharing `kdenlive:control_uuid`.
- The sequence is itself a bin clip (`kdenlive:producer_type=17`, an entry in `main_bin`). The last element is the `kdenlive:projectTractor` wrapper.
- Times are written as `HH:MM:SS.mmm`, as Kdenlive writes them. The Kdenlive MCP parser reads bare numbers as seconds.
- **Subtitles** are written in the SRT layout: `project.kdenlive.srt`, a `subtitlesList` sequence
  property and an `avfilter.subtitles` filter. Kdenlive 24.08+ converts this to its `.ass` storage on open.
  The Kdenlive MCP server reads only the SRT layout.

---

## 3. `layers.json` (schema `cves.layers/1`)

The renderer writes `Export/control/layers.json`, and the exporters only read it. The reference
implementation is `engine/cves/export/layers.py` (`load_manifest`): anything it accepts is valid, and it
reports every problem at once.

```json
{
  "schema": "cves.layers/1",
  "name": "Demo",
  "fps": [24000, 1001],
  "size": [1080, 1920],
  "audio_rate": 48000,
  "duration": 31.53,
  "source": {"exported": "2026-11-18 18:02:11", "edit_sha256": "…",
             "segments": [{"id": "01_hook_0", "clip": "01_hook", "in": 0.20854, "out": 1.83517, "f0": 0, "n": 39}],
             "a_frames": 1225, "frames": 1255},
  "clips": [
    {"id": "a_01_hook_0", "track": "V1", "path": "media/aroll/01_hook_0.mov",
     "start": 0.0, "end": 1.63, "source_in": 0.0,
     "fps": [24000, 1001], "size": [1080, 1920], "alpha": false, "edit_ref": "edl.01_hook_0"},
    {"id": "c1", "track": "V2", "path": "media/cutaways/c1.mov", "start": 1.63, "end": 7.55, "source_in": 0.0,
     "fps": [24000, 1001], "size": [1080, 1920], "edit_ref": "cutaways.c1", "frames": 142, "hash": "<sha256>"},
    {"id": "chest_0", "track": "V3", "path": "media/overlays/chest_0.mov", "start": 21.80, "end": 24.57,
     "source_in": 0.0, "fps": [24000, 1001], "size": [1080, 1920], "alpha": true, "edit_ref": "chest.0"},
    {"id": "voice", "track": "A1", "path": "media/audio/voice.wav", "start": 0.0, "end": 31.53, "source_in": 0.0,
     "channels": 2, "sample_rate": 48000},
    {"id": "music", "track": "A2", "path": "media/audio/music.wav", "start": 0.0, "end": 31.53, "source_in": 0.0,
     "gain_db": 0},
    {"id": "sfx", "track": "A3", "path": "media/audio/sfx.wav", "start": 0.0, "end": 31.53, "source_in": 0.0}
  ],
  "captions": [
    {"index": 1, "ref": 0, "start": 0.21, "end": 1.62, "text": "Is your business on Google Maps?"}
  ]
}
```

| Field | Type | Rule |
|---|---|---|
| `schema` | string | exactly `"cves.layers/1"` |
| `name` | string | timeline / project name (default: the video folder name) |
| `fps` | `[int, int]` | required: the project's rate as a rational (`[24000, 1001]`, `[25, 1]`, `[30000, 1001]`), 1-240 fps |
| `size` | `[int, int]` | required: the frame size, positive and even (`[1080, 1920]`, `[1920, 1080]`) |
| `audio_rate` | int | `48000` (default) |
| `source` | object, optional | the cut at export: `segments` (id, clip, source in/out, first frame, length), `edit_sha256`. `cves import-edits` measures changes against it |
| `duration` | seconds | timeline length; at least the last clip end (default: last clip end) |
| `clips[].id` | string | unique |
| `clips[].track` | string | `V1` A-roll · `V2` cutaways · `V3` overlays with alpha · `A1` voice · `A2` music · `A3` sfx |
| `clips[].role` | string, optional | if present must match the track (`aroll`, `cutaway`, `overlay`, `voice`, `music`, `sfx`) |
| `clips[].path` | string | relative to the `layers.json` folder, or absolute; must exist. Video: `.mov` ProRes (422 HQ; 4444 with alpha on V3). Audio: `.wav` 48 kHz |
| `clips[].start`, `end` | seconds | timeline in/out (end exclusive); at least 1 frame long; no overlaps on the same track |
| `clips[].source_in` | seconds | where in the media file the clip starts (default 0) |
| `clips[].fps`, `size` | pairs | video only; must equal the timeline's (defaults to it) |
| `clips[].alpha` | bool | default `true` on V3, else `false`; V3 must be `true` |
| `clips[].gain_db` | number, optional | static gain written into the FCPXML (`adjust-volume`) and Kdenlive (`volume` filter); default 0 because stems are mixed as rendered |
| `clips[].channels`, `sample_rate` | int, optional | audio only; default 2 and 48000 |
| `clips[].edit_ref` | string, optional | where this layer comes from in `edit.yaml` (`cutaways.c3`, `broll.b02` for a `broll:` shot (V2 on the A-roll spine, V1 on the others), `chest.0`, `chest.0+1` for chest entries sharing a layer, `edl.<segment>`, `gap.<id>`, `end_card`, `stems.music`); used for round trips |
| `clips[].frames`, `hash` | int / string, optional | frame count and sha256 of the media as rendered; `cves control update` refreshes both |
| `captions[]` | list | `{index, ref, start, end, text}`, seconds, non-overlapping, inside the timeline; `ref` is the caption's index in the renderer's caption events (round trips); `\n` in `text` makes a line break |

All times are cut-timeline seconds. They are snapped to the nearest frame of the manifest's own `fps` **once**,
in `layers.py`, so the FCPXML, the Kdenlive project and the SRT all agree to the frame.

**Stable ids.** Every layer keeps the same id, file name and path across exports: `a_<segment>` →
`media/aroll/<segment>.mov`, cutaway `<id>` → `media/cutaways/<id>.mov`, `end_card`, `chest_<first entry>` →
`media/overlays/chest_<k>.mov`, `voice` / `music` / `sfx` → `media/audio/<id>.wav`. The FCPXML clip note is
`cves:<id> edit:<edit_ref>`. The importer matches by note, then path, then unique file name.

---

## 4. Daily use

1. **Export.** `cves render` (control mode) writes the layers and `layers.json`. Then:
   - Resolve: `cves export resolve --push`. Resolve must be open with the bridge started (step 2).
   - Kdenlive: `cves export kdenlive`, then open `Export/control/project.kdenlive` in Kdenlive.
2. **Start the bridge** (Resolve only, once per Resolve session): Workspace > Scripts > Utility >
   **CursorBridge**. Workspace > Console should print `Bridge is running (read + write)` and the status
   should show version `2.0.0+cves1`. Running it again restarts it.
3. **Save in the editor, then ask Claude.** For example:

| You say | Resolve (live, via bridge) | Kdenlive (via project file) |
|---|---|---|
| "music −2 dB" | Resolve's scripting API has no clip-volume control. Claude changes the music level in `edit.yaml`, runs `cves mix`, and swaps the stem in with `replace_clip` (the timeline position is kept). You can also drag the A2 fader yourself. | `set_clip_volume(music clip, -2)`, then save. Reload the project in Kdenlive. |
| "move caption 3" | Subtitle text and timing are not editable through the API. Claude edits the caption in `edit.yaml` (captions), re-renders control mode, then runs `cves export resolve --push-subtitles`, which snapshots and replaces the subtitle track. | `move_subtitle(id, start, end)`, then save. Reload. |
| "trim the hook" | Clip trimming is not reliably scriptable through the bridge (it can delete with ripple, insert and append, but not move in/out points). Claude changes the cut in `edl.json`/`edit.yaml`, re-renders, and re-imports as a **new** timeline version. Your old timeline is left untouched, so carry over your hand edits or trim on the timeline yourself. | `trim_clip` / `ripple_delete` on V1 (and the matching layers), then save. Reload. |
| "make cutaway 2 start a beat later" | Same as trim: through the cut list, then a new timeline version | `move_clip` |
| "add a marker where the price appears" | `add_marker` | `add_marker` |
| "render a review copy" | `quick_export` / `add_render_job` + `start_rendering` | `start_render` (output must be inside the workspace) |

### What Claude can and cannot do live in Resolve

**Can** (bridge tools; these work on Free): read the timeline, clips and markers; markers and flags;
import media; append and insert clips; delete clips (with ripple); enable or disable clips;
static clip properties (opacity, zoom, pan, tilt, rotation, crop, composite mode); clip colour;
tracks (add, delete, rename, lock, enable); LUTs and CDL; grade copy and reset; Fusion comp
add/import/export; Text+ and generator insertion; replacing a clip's media; render settings and jobs;
save; project export (snapshots).

**Cannot**, per the bridge README and the Resolve API:
- keyframes: the API sets static values only;
- the text and parameters inside Fusion titles and effects, which need the Fusion page;
- transitions, which you add from the Effects Library by hand;
- clip or track audio volume (not in the scripting API);
- editing subtitle text or timing (CVES replaces the whole subtitle track instead);
- trimming or moving existing clips' in/out points;
- Smart Reframe and Stabilization (Studio only).

Anything in this list is either done by hand or goes through `edit.yaml` and a re-render.

### Baked graphics round trip

Text inside a cutaway card, a chest wordmark or a roto layer is **baked** into its ProRes layer. No
editor can retype it. To change one:

1. Find the layer's `edit_ref`: match the clip's file name (the same in both editors) against
   `layers.json`. It is also in the clip's `<note>` in `timeline.fcpxml`. Example: `cutaways.c3`.
2. Claude edits that entry in `edit.yaml`, then runs `cves render --only c3` (the final frames, for the vibe
   master) and `cves control update --only c3`. That re-renders just that layer to the **same path** and
   updates its `frames` and `hash` (and its start/end if the cutaway was re-timed) plus the captions in
   `layers.json`. Nothing else is re-rendered or re-encoded. It refuses, with a one-line message, when the cut
   itself changed (A-roll segments moved), because then every later layer moved too: rebuild with `cves export`.
   `--only` takes cutaway ids, segment ids, `roto.N` / `roto:<segment>` (re-renders that A-roll segment),
   `chest.N` / `chest_N`, `end_card`, `captions`, `audio` (copies the stems again after `cves mix`).
3. Relink:
   - Resolve: `replace_clip` on the media pool item, or right-click the clip > Replace Clip. If the length
     changed, re-import the timeline instead.
   - Kdenlive: reload the project. The file path is unchanged, so the new frames are picked up. If the
     length changed, Claude runs `replace_clip` / `trim_clip` with the Kdenlive MCP.

### 4a. Importing the human's edits (`cves import-edits`)

The full cycle is **export → the human edits → import → re-render**:

```bash
cves export all                                  # layers + timeline.fcpxml + project.kdenlive
#   ... the human edits in Resolve (then File > Export > Timeline > FCPXML, and File > Export > Subtitle > SRT)
#   ... or in Kdenlive (File > Save: project.kdenlive and its subtitle file)
cves import-edits --from resolve  ~/Desktop/edited.fcpxml --captions ~/Desktop/edited.srt
cves import-edits --from kdenlive Export/control/project.kdenlive
cves import-edits ... --dry-run                  # report only, nothing written
# then the steps the report lists, e.g. cves select && cves prep (if selects.yaml changed), cves render, cves mix, cves encode
```

`engine/cves/importer.py` reads the edited timeline directly (FCPXML 1.8–1.11 and Kdenlive MLT XML with
`xml.etree`; `.otio` through OpenTimelineIO, which is installed but has no FCPXML / Kdenlive adapters in
the CVES venv). It flattens the timeline (spine, gaps, connected clips, secondary storylines; Kdenlive
track tractors and playlists, with `HH:MM:SS.mmm`, SMPTE or frame times), matches every placed clip to
the layer it came from, and compares it with `layers.json` as exported. For each layer, the *content
shift* is how far its pictures moved on the timeline (`(start − source_in)` after minus before), so a
move and a trim are told apart.

| Edit in the editor | Written to |
|---|---|
| cutaway moved | `cutaways[id].start/end`; `snap: false` when it no longer sits on a segment boundary; the template's animation times move with it (every number inside the old window, except known non-time keys such as `value` / `size`, and the duration in a `[t, d]` pair). Each shifted parameter is listed in the report |
| cutaway trimmed (in or out) | `start` / `end` only (animation times stay: a trim reveals or hides frames) |
| cutaway deleted | removed from `cutaways` |
| end card trimmed / deleted | `end_card.duration` / `end_card` removed |
| chest overlay moved / deleted | chest params shifted / the chest entry removed (a trim of a drawn chest graphic is reported, not mapped) |
| B-roll shot moved / trimmed / deleted | `broll[k].start/end` (`snap: false` when it leaves a segment boundary on the A-roll spine); a head trim moves `broll[k].in` by the trimmed frames at the shot's speed; deleted → removed from `broll:`. Works for V2 shots (A-roll spine) and V1 shots (voiceover / music / broll spines, where they do not touch `selects.yaml`) |
| B-roll speed changed in the editor | `broll[k].speed` multiplied by the editor's speed |
| motion piece (`m_*`) trimmed, in `cutaways:` or `chest:` | the piece re-times: `at` moves to the new in point when the head was trimmed past its clock start, `duration` fits the new out point, so the entry and exit both still play (a move shifts `at` like any animation time) |
| A-roll head or tail trimmed at a clip's outer edge | `selects.yaml` clip `in` / `out` (then `cves select` + `cves prep` re-tighten) |
| a whole clip's A-roll deleted / clips reordered | `selects.yaml` clip removed (with its roto/chest) / clips reordered |
| ripple (later shots moved) | roto params, `captions.hide`, `sfx.extra`, `aroll.snap`, `music.drop_cut`, `transitions` follow their shot |
| music / SFX / voice volume | `music.bed_lu` / `style.sound.sfx_offset_db` / both, relative, for the voice |
| music moved | `music.drop_cut` |
| caption moved, retimed, retyped, deleted or added | `captions.events` (word times scaled into the new span). Captions are then frozen; delete `captions.events` to go back to auto captions |

It writes `Edit/edit.yaml` (backup `Edit/edit.yaml.bak-<timestamp>`), `Edit/selects.yaml` when the cut
changed (backup alongside) and **`Edit/IMPORT-REPORT.md`**: what was applied, a diff, the next commands,
and a **Not mapped** list. Nothing is dropped silently; these are listed instead: new third-party media,
effects, transitions, titles and generators, compositions, speed changes, compound / multicam clips,
volume keyframes (only the static level is read), a layer split into pieces with a gap, trims between
two tightened segments of one clip, moves of the voice or SFX stems, and trims of drawn (non-motion) chest overlays.

Limits: the rewrite of `edit.yaml` keeps a leading comment block only (the backup has every comment). The
editor's timeline must stay at the exported rate (the importer refuses otherwise). Re-tightening after a
`selects.yaml` change can move later shots by a few frames; the report says when that applies.

---

## 5. Handoff rules (you and Claude in one project)

1. **Save before you ask Claude.** In Kdenlive, Claude edits the file on disk, so unsaved changes in the app
   are lost when you reload. In Resolve, Claude snapshots the saved project.
2. **Claude snapshots before every change.**
   - Resolve: `cves export resolve --snapshot <label>` exports a `.drp` to `Export/control/snapshots/`.
     To restore, use File > Import Project. `--push` and `--push-subtitles` snapshot automatically.
   - Kdenlive: `create_snapshot` (MCP), plus `backup_project`, which writes a sibling `.backup_<time>.kdenlive`.
     Undo and redo also work per tool call within one Claude session.
3. **Your edits win.** If Claude's plan conflicts with something you changed by hand, Claude keeps your
   change and tells you. Claude never re-imports or regenerates a timeline over your work. A rebuilt timeline is
   always a new timeline version or file.
4. **Editor-only changes** are noted in `CONTROL.md`.
5. **Kdenlive: reload after Claude saves.** Kdenlive does not watch the file. Use File > Revert, or close
   and reopen the project.

---

## 6. Security review (done 2026-11-18, before recommending either server)

The full source of both servers was read at the pinned commits.

### davinci-resolve-mcp (hiteshK03) @ f812df7

| Area | Finding |
|---|---|
| Network | `CursorBridge.py` (inside Resolve) binds `HTTPServer(("127.0.0.1", 9876))`, which is **localhost only** (verified with `lsof`). The MCP server talks to it over `http://127.0.0.1:9876` with urllib, and to Claude over stdio. It opens no other listeners and makes no outbound calls, except that the optional AI tools download models (Whisper / Demucs / rembg via Hugging Face and GitHub) on first use. |
| **HIGH: browser access** | Every bridge response sends `Access-Control-Allow-Origin: *`, the OPTIONS preflight allows any origin, there is no `Host` check (DNS rebinding) and there is no authentication. JSON bodies are parsed whatever the Content-Type. So **any web page open in your browser while the bridge runs can read and drive Resolve**: list and delete projects (`/projects/delete`), export projects, LUTs, stills or frames to arbitrary paths, import arbitrary files, start renders. Reproduced against the upstream file: the preflight returns `204` with `ACAO: *`, a cross-origin GET returns data, and a `text/plain` POST reaches `/projects/delete`. |
| Execution | Bridge: Resolve API calls only, with no `eval`/`exec`/shell. MCP server: `subprocess.run` with list arguments (no shell) for `ffmpeg`/`ffprobe` in the background-removal tools only. |
| File deletion | `shutil.rmtree` only on its own temporary frames folder. Destructive Resolve operations are exposed as tools: `delete_project`, `delete_media_pool_clips`, `delete_timeline_clips`, `delete_track`, `delete_stills`, `delete_render_job`. |
| File writes | AI tools write next to source media (`davinci-mcp-output/`). Export tools write wherever the caller asks (Resolve does the writing). The log file is `logs/bridge_mcp.log` in the clone. |
| Other | `_get` builds query strings without URL-encoding (cosmetic). The bridge handles requests on one thread inside Resolve's script runner. `/bridge/shutdown` is unauthenticated (a local denial of service only after hardening). |

**CVES hardening** (`setup/control/patch_cursorbridge.py`, verified by test):
1. Removes the CORS headers and refuses preflights (403).
2. Refuses requests that carry an `Origin` header or a cross-site `Sec-Fetch-Site`. Browsers send these; the MCP server and CVES do not.
3. Refuses any `Host` other than `127.0.0.1:9876` / `localhost:9876`.
4. Requires `Content-Type: application/json` on POST.
5. Asserts the 127.0.0.1 bind.
6. Adds `/cves/timeline/current`, `/cves/append` and `/cves/subtitles`.

The patch only accepts the reviewed file (sha256 `ed8f7e1e…f48e`), and the installer pins the commit. The patched version reports `2.0.0+cves1`.
Remaining risk: any process running as your user can still drive Resolve while the bridge runs, which is
true of any local automation. Stop the bridge by quitting Resolve when you are not using it. Claude Code asks
before each MCP tool call unless you allow it, so allow read tools freely and keep `delete_*` / `projects_*`
on ask.

### MCP_Server_Kdenlive (12bijaya) @ 4733141

| Area | Finding |
|---|---|
| Network | None: stdio MCP only. There is no socket, HTTP or `urllib` in the source. |
| Execution | `media/ffmpeg/runner.py` is an allow-list (`ffmpeg`, `ffprobe`, `melt`, `kdenlive`). Binaries are resolved from config or env, never from model input. Arguments are list form, `shell=False`. Renders run as a background `Popen` in their own process group. (On a Linux snap install it calls `snap run --shell kdenlive -c <shlex-joined command>`, which is quoted. This does not apply on Mac or Windows.) |
| File deletion | Only its own scratch files, plus a cancelled render's partial output (`unlink`). |
| **MEDIUM: write confinement bypass** | Model-supplied write paths go through `resolve_workspace_path` only when *relative*. **Absolute paths are accepted as is** in `save_project`/`save_project_as` (any `.kdenlive` anywhere), `restore_project` (copies any readable file over any path), `export_subtitles` (any path, any extension) and `start_render` (any path). That gives a prompt injection a write-anywhere primitive. |
| **Broken upstream** | `storage/snapshots/manager.py` is imported but was never committed (the repo's own `.gitignore` excludes `snapshots/`), so the pinned commit fails at import and the server cannot start. |
| Parsing | `xml.etree` (no external entities). Paths read through `resolve_source_path` refuse `/proc`, `/sys` and `/dev`. |

**CVES hardening** (`setup/control/patch_kdenlive_mcp.py`):
- Routes all four write paths through the workspace check, so absolute paths must be inside `KDENLIVE_MCP_WORKSPACE`.
- Limits render outputs to `.mp4/.mov/.mkv/.webm` and subtitle exports to `.srt`.
- Adds the missing snapshot manager, as JSON snapshots in `~/.kdenlive-mcp/snapshots`.
- Points saved projects at the CVES vertical 23.976 profile.

Each edited file is accepted only at its reviewed sha256. Verified: `restore_project` to `/tmp`, `export_subtitles` to `~` and `start_render` to `/tmp` all return `INVALID_PATH`. Upstream's test suite gives 75 passed and 1 failed. The failure is `test_import_export_srt_files`, which exports to a temp folder outside the workspace and is now refused by design.

**Pinning policy:** never `git pull` either server. To update, read the diff since the pin, rerun this
review, update `PIN` in the installer and the sha256 values in the patch script together, then rerun
`cves export selftest`.

---

## 7. Known limits and gotchas

- **Kdenlive MCP and subtitles.** After you save the project in Kdenlive 24.08+, subtitles are stored as
  `.ass`, which the Kdenlive MCP cannot read, so Claude cannot list or move them after that. Edit them in
  Kdenlive's subtitle panel, or through `edit.yaml` and a re-export.
- **Kdenlive MCP saves restructure the file.** Its writer omits the sequence's bin entry, and Kdenlive repairs
  that silently on open ("Unreferenced clip … Fixed"). Track names revert to defaults.
- **Kdenlive 26.08 `kdenlive --render` crashes on any project with a subtitle track.** The same happens with subtitle
  files Kdenlive wrote itself. The GUI is unaffected. CVES's loader check therefore strips the subtitle track,
  and the subtitle path is checked separately (section 9).
- **Resolve and Python:** Workspace > Scripts runs `.py` scripts only if Resolve finds a system Python 3.
  If CursorBridge is missing from the menu or nothing happens, install Python 3 from python.org
  (Windows: "for all users") and restart Resolve.
- **Media pool duplicates:** each `--push-subtitles` imports `captions.srt` again. The old pool item stays
  unused; delete it by hand if the pool gets cluttered.
- **Re-import is never in place.** A changed cut becomes a new timeline (Resolve) or file (Kdenlive). That is
  deliberate (handoff rule 3). `cves control update` only replaces media files at their existing paths;
  it never rewrites `project.kdenlive` or the Resolve timeline over your work.
- **Resolve's FCPXML export was not tested live.** The importer's FCPXML reader handles the structures FCPXML
  1.8–1.11 defines (spine items, connected clips, secondary storylines, `clip`/`video` wrappers, `tcStart`), and
  was checked against CVES's own `timeline.fcpxml` with simulated edits. A real Resolve export may carry
  structures that are only reported as "Not mapped"; check the report the first time.

---

## 8. Files

```
engine/cves/export/__init__.py     package entry (load_manifest, Manifest, LayersError)
engine/cves/export/__main__.py     python -m cves.export {resolve,kdenlive,all,selftest}
engine/cves/export/layers.py       layers.json schema + validation, frame snapping, captions.srt, timeline.otio
engine/cves/export/resolve.py      timeline.fcpxml writer + checker, Bridge client, drive_import, push_subtitles, snapshot
engine/cves/export/kdenlive.py     project.kdenlive writer, structural + melt check, Kdenlive app loader check
engine/cves/export/selftest.py     synthetic fixture at two rates / two sizes + end-to-end checks
engine/cves/layered.py             control-mode layer render: build (everything), update (named layers), timebase
engine/cves/importer.py            cves import-edits: FCPXML / Kdenlive / OTIO reader + mapping onto edit.yaml / selects.yaml
setup/control/install_resolve_bridge_mac.sh / _windows.ps1
setup/control/install_kdenlive_mcp_mac.sh   / _windows.ps1
setup/control/patch_cursorbridge.py         bridge hardening (pinned sha256)
setup/control/patch_kdenlive_mcp.py         Kdenlive MCP hardening + missing snapshot manager (pinned sha256)
setup/control/constraints-mcp.txt           mcp>=1.26,<2 for both servers
setup/control/requirements-control.txt      exporter deps (OpenTimelineIO + FCPXML adapter)
```

---

## 9. Tested (2026-11-18, macOS, Kdenlive 26.08.3, melt 7.43.0; Resolve not installed)

`python -m cves.export selftest` builds a synthetic set in a folder whose name contains a space and a `’`:
two coloured ProRes 422 HQ A-roll clips, a ProRes 4444 overlay with a real alpha box, a ProRes cutaway,
three 48 kHz WAV stems and three captions, **at two rates and two sizes** (23.976 1080x1920 and 25 fps
1920x1080), plus rational checks at 29.97 / 30 / 25. Re-run 2026-11-18 after the timebase change: **all 37
checks pass** with `--no-gui` (both configs: FCPXML `frameDuration` `1001/24000s` / `1/25s`, media formats
`FFVideoFormat1080x1920p2398` / `FFVideoFormat1080p25`, Kdenlive `<profile>` at the fixture's rate and size,
melt render at the right size and length, the same pixel and audio probes). The OTIO FCPXML adapter is not
installed in the CVES venv, so that read-back is reported as skipped. The earlier single-config run, with the
FCPXML DTD check when `CVES_FCPXML_DTD` points at Apple's `FCPXMLv1_10.dtd`, found:

- `layers.json` validates. `timeline.fcpxml` passes `check_fcpxml` (every time on the 23.976 grid, 1080x1920
  formats, lanes 1..3 / -1..-3, no overlaps, encoded absolute URLs) and **`xmllint --dtdvalid` against
  the FCPXML 1.10 DTD**. OTIO's FCPXML adapter reads it back with 3 video and 3 audio tracks, each
  holding the right clips. (That adapter truncates 23.976 to 23 fps, so it is not used for timing.)
- `project.kdenlive` passes the structural check and plays end to end in melt. In the headless melt render
  (1080x1920, 8.02 s): V2 covers V1, the V3 alpha box composites over V2 and is transparent outside the box,
  V3 ends on time, captions burn in, and the audio stems are present.
- **Kdenlive's own loader** (`kdenlive --render`) opens it with no DocumentChecker, profile or sequence
  warnings and renders it, alpha box included. The subtitle track is stripped for this check because of the crash
  described in section 7. With the subtitle track in place, Kdenlive's loader parsed the SRT and converted it to its
  `.ass` storage with all three cues and correct times.
- **Kdenlive MCP round trip** over stdio, as Claude Code drives it: open the exported project; list the 3
  subtitles; snapshot; `set_clip_volume(music, -2)`; `move_subtitle(3)`; `validate_project` (melt);
  `save_project`. The saved project renders correctly, the 440 Hz music band measures **exactly 2.0 dB
  lower** (-47.9 → -49.9 dB), caption 3 moved to 4.796 s, and Kdenlive loads it. Writes outside the
  workspace are refused.
- **Resolve bridge**: the hardened `CursorBridge.py` was run outside Resolve. It binds 127.0.0.1 only, and the
  MCP server and the CVES client work through it (162 tools listed, `get_resolve_status` round-trips).
  Browser-origin, preflight, `text/plain`, rebinding-Host and cross-site requests all get 403, where the
  unpatched file allows them.
- **`drive_import` / `push_subtitles` against a mock Resolve API** (scratch only): the call order and
  arguments are right. That is CreateProject → SetSetting ×4 before ImportMedia → ImportTimelineFromFile
  (`importSourceClips: false`) → Alpha mode → track names → AddTrack(subtitle) → ImportMedia(srt) →
  AppendToTimeline(recordFrame = timeline start) → SaveProject, with an ExportProject snapshot before captions are replaced.

### Round trip on the real ad (2026-11-18, a copy of the first test ad)

`cves export all` (new layered build: per-entry chest layers, `source` snapshot, caption `ref`s, hashes),
then a scripted "human edit" of both project files (`timeline.fcpxml` and `project.kdenlive` + its `.srt`):
cutaway **c2 moved +12 frames (0.5 s)**, **c4 deleted**, **caption 3 retimed** (+6 frames start, +12 end),
the **last A-roll segment trimmed** 12 frames at the tail, **music −2 dB**. The edited Kdenlive file still
plays in melt. `cves import-edits` gave the same result from the FCPXML (with `--captions edited.srt`) and
from the Kdenlive project (subtitles read from the project's own subtitle file), 7 changes, nothing unmapped:

- `selects.yaml` `14_brand` out 218.66 → 218.16;
- `c2` 15.43–21.23 → 15.9326–21.73 s, `snap: false`, item `at` times 15.30/16.25/17.20/20.30 each +0.5;
- `c4` removed; `music.bed_lu` −7 → −9;
- caption 3 7.466–8.258 → 7.716–8.759 s in `captions.events` (overlap with caption 4 noted in the report);
- backups `Edit/edit.yaml.bak-<time>` / `Edit/selects.yaml.bak-<time>` and `Edit/IMPORT-REPORT.md` with the diff.

The unchanged `timeline.otio` imports as "no changes". A Resolve-shaped FCPXML (V1 in the spine with gaps,
other layers connected to the spine item under them, `tcStart` 01:00:00:00) built from the export with c2
moved gave exactly that one change. A second import of the same edit leaves the cutaway alone and warns that
edit.yaml changed since the export. Then `cves control update --only c2,c4,captions` re-rendered only c2
(139 frames, new hash, new 15.933–21.730 s timing), dropped c4 and refreshed the captions (14 → 18 cues now
that c4 no longer hides them) in 2 m 50 s on a heavily loaded machine; `cves export kdenlive --no-build`
loads the result in melt.

### Kdenlive round trip, automated (2026-11-19, macOS, melt from Kdenlive.app)

`tests/test_weak_spots.py::test_kdenlive_round_trip` runs the whole cycle on every test run where melt is found (skipped
otherwise): `make_demo` (540x960) plus a B-roll shot → render / mix / encode → `cves export kdenlive` → the test edits
`project.kdenlive` the way Kdenlive saves it (cutaway `c2` moved 6 frames later through the playlist blanks, the B-roll
layer's head trimmed 6 frames) and its `project.kdenlive.srt` (the first caption 6 frames earlier) → melt renders the edited
project → `cves import-edits --from kdenlive` → `edit.yaml` has `broll[0].start` +0.2 s and `in` 0.5 → 0.7, `c2` +0.2 s with
`snap: false`, the caption in `captions.events` → `cves render` places the shot and the cutaway at their new times.

### Still needs a live Resolve test (Resolve is not installed on this Mac)

The step-by-step script for the first person with Resolve is [RESOLVE-CHECKLIST.md](RESOLVE-CHECKLIST.md).

1. The bridge runs from Workspace > Scripts on Resolve **Free** 19/20 on Mac and Windows, with the hardened file,
   and the Python 3 requirement holds.
2. `ImportTimelineFromFile` accepts `timeline.fcpxml`, and the result has:
   - a 1080x1920 23.976 timeline;
   - V1/V2/V3 and A1/A2/A3 on the expected tracks (no empty V1 from the gap spine);
   - clips relinked from the pool with `importSourceClips: false`;
   - frame-exact positions and source-ins.
3. `SetClipProperty("Alpha mode", "Straight")` is the right key and value for ProRes 4444 from
   ffmpeg (if edges look dark or haloed, try `Premultiplied`; `CVES_RESOLVE_ALPHA_MODE` overrides it).
4. `/cves/subtitles`: which `AppendToTimeline` form places an SRT media-pool item on subtitle track 1 at the
   timeline start. The endpoint tries three forms and reports where the cues landed. If none works, the manual step is
   dragging `captions.srt` onto the timeline.
5. Project settings applied through the bridge before import (`timelineFrameRate` etc.) stick on Free.
6. `/projects/export` snapshots on Free, and restoring one with File > Import Project.
7. A timeline exported **by Resolve** (File > Export > Timeline > FCPXML 1.10) and its subtitle SRT read by
   `cves import-edits`: only CVES's own FCPXML and a hand-built Resolve-shaped one were tested.
8. Windows: both PowerShell installers (written but not run, because this Mac has no PowerShell) and the Kdenlive
   `melt.exe` / effects paths they detect.

## 10. Verified on a real ad (2026-11-18)
`cves export all` on the first test ad (52 s, 24 A-roll segments, 6 cutaways, 2 chest overlays, end card) wrote
1.5 GB of ProRes layers + `layers.json` + `timeline.fcpxml` + `project.kdenlive` in 3 m 43 s. melt loaded and played the
Kdenlive project with no errors, and its render matched the vibe-mode final: 1,255 frames each, a mean difference of about 1 level
out of 255 on cutaways, overlays and the end card (compression only).

**Caption styling:** in both editors, captions are an editable subtitle track in the editor's own subtitle style, not the
burned-in house caption style (Poppins SemiBold, soft shadow, chin-aware position). For a control-mode delivery, either
set the editor's subtitle style to match, or keep captions editable for the tweak pass and render the final through `cves`
(edit `edit.yaml` captions), which burns the house style in.
