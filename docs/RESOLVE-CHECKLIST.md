# DaVinci Resolve: first live verification

DaVinci Resolve was not installed on the machine CVES was built on. Everything Resolve-side in control mode was
checked without it: the FCPXML structure (and once against Apple's FCPXML 1.10 DTD), the hardened bridge outside
Resolve, and the import call order against a mock of Resolve's API ([CONTROL-MODE.md](CONTROL-MODE.md) §9). The
Kdenlive side is tested end to end on every test run.

This page is the script for the **first person who has Resolve**. Work through it in order, tick each box, and note
anything that differs from "expected". It takes about 45 minutes. When you are done, send the filled-in copy (or open
a PR that pastes it into CONTROL-MODE.md §9 and updates README "Known limits").

Use a scratch copy of a project, never a client's only copy.

## 0. What you need

- [ ] DaVinci Resolve **Free** 19 or 20 (Studio also works; write down which). Version: ______  OS: ______
- [ ] Python 3 from python.org (Windows: "for all users"), so Workspace > Scripts can run `.py` files.
- [ ] The CVES repo with its venv (`INSTALL.md`), and `cves doctor` passing.
- [ ] Resolve opened once, then closed.

## 1. Install the bridge

```bash
setup/control/install_resolve_bridge_mac.sh --register        # Windows: powershell -ExecutionPolicy Bypass -File setup\control\install_resolve_bridge_windows.ps1 -Register
```

- [ ] The script finishes with no error and prints the `claude mcp add` line (and runs it with `--register`).
- [ ] `CursorBridge.py` exists in Resolve's Scripts folder:
      macOS `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/`,
      Windows `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\`.

## 2. Start the bridge inside Resolve

Open Resolve, any project. Workspace > Scripts > Utility > **CursorBridge**.

- [ ] Workspace > Console prints `Bridge is running (read + write)`.
- [ ] The status shows version `2.0.0+cves1`.
- [ ] In a terminal: `curl -s http://127.0.0.1:9876/status` answers (9876 is CVES's default, `CVES_RESOLVE_BRIDGE`
      overrides it; use the port the console prints), and the same request with an `Origin: https://example.com` header
      gets **403**.
- [ ] Nothing listens on a non-loopback address (macOS `lsof -iTCP -sTCP:LISTEN | grep -i resolve`).

If CursorBridge is missing from the menu or nothing happens: Python 3 is not found by Resolve (see §0).

## 3. Build a test project

```bash
python tools/make_demo.py ~/cves-resolve-check --size 1080x1920          # 30 fps, synthetic, no client media
cves --project ~/cves-resolve-check build
cves --project ~/cves-resolve-check export resolve                       # timeline.fcpxml, captions.srt, timeline.otio
```

- [ ] `Export/control/timeline.fcpxml`, `captions.srt` and `layers.json` exist, and the command reports the FCPXML check as OK.

Repeat §4-§7 once more later with `--size 1920x1080` (landscape) and once with a 23.976 project if you have one
(`--fps 24` is not 23.976: use a real 23.976 project copy for that run).

## 4. Push the timeline into Resolve

With the bridge running:

```bash
cves --project ~/cves-resolve-check export resolve --push
```

Expected (CONTROL-MODE.md §2, the `--push` order), then check each in Resolve:

- [ ] A new project exists; Project Settings > Master Settings show the project's **frame rate** (30 here) and **size**
      (1080x1920). These are set before any media is imported; write down if Resolve kept them: ______
- [ ] The media pool holds every file under `Export/control/media/`.
- [ ] The timeline has **V1 A-roll, V2 Cutaways, V3 Overlays** and **A1 Voice, A2 Music, A3 SFX**, with those names,
      and **no empty V1** made from the FCPXML gap spine.
- [ ] Clips are relinked from the pool (no duplicate pool items from `importSourceClips: false`).
- [ ] Positions are frame exact. Pick three clips and compare their timeline in/out with `layers.json` `start` / `end`
      (seconds × fps): c1 ______ c2 ______ end_card ______.
- [ ] Source-ins are right: scrub into a cutaway; its first frame is the cutaway's first rendered frame.
- [ ] V3 overlays composite with clean edges. Their Inspector > Composite / Alpha mode reads **Straight**. If edges look
      dark or haloed, set `CVES_RESOLVE_ALPHA_MODE=Premultiplied`, push again, and note which looked right: ______
- [ ] Subtitle track 1 holds the captions from `captions.srt`, starting at the timeline start (not at the playhead).
      The output of `--push` lists which `AppendToTimeline` form placed them: ______. If none worked, the manual step is
      dragging `captions.srt` onto the timeline; note that here.
- [ ] Anything the API refused is listed under `manual` in the command output (copy it here): ______

## 5. Snapshots

```bash
cves --project ~/cves-resolve-check export resolve --snapshot "before-trim"
```

- [ ] `snapshots/<time>-before-trim.drp` is written (Resolve Free allows project export).
- [ ] File > Import Project on that `.drp` restores the timeline as it was.

## 6. Edit in Resolve, then import the edits

Make exactly these edits on the pushed timeline (the same ones the automated Kdenlive round trip makes):

1. Move cutaway **c2** on V2 **6 frames later** (there is room after it on the demo).
2. Trim the **head** of A-roll clip `05_cta` on V1 by **6 frames** (outer edge of that clip).
3. Move the **first subtitle** 6 frames earlier.
4. Lower the **music** clip on A2 by **2 dB** (Inspector > Volume).

Export: File > Export > Timeline > **FCPXML 1.10** (`edited.fcpxml`), and File > Export > Subtitle > **SRT** (`edited.srt`).

```bash
cves --project ~/cves-resolve-check import-edits --from resolve edited.fcpxml --captions edited.srt --dry-run
cves --project ~/cves-resolve-check import-edits --from resolve edited.fcpxml --captions edited.srt
```

Expected in `Edit/IMPORT-REPORT.md` and `Edit/edit.yaml`:

- [ ] `cutaway c2` moved +6 frames (+0.2 s at 30 fps), `snap: false`, its animation times shifted by the same amount.
- [ ] `selects.yaml` `05_cta` `in` later by 6 frames (0.2 s).
- [ ] The caption in `captions.events` 0.2 s earlier.
- [ ] `music.bed_lu` 2 lower.
- [ ] **Not mapped** lists nothing you did not do. Copy anything unexpected (Resolve-specific FCPXML structures such as
      `ref-clip`, `sync-clip`, `mc-clip`, extra `adjust-*` effects): ______
- [ ] The rate check passes (the importer refuses a timeline whose rate changed).

Then rebuild and confirm:

```bash
cves --project ~/cves-resolve-check select && cves --project ~/cves-resolve-check prep
cves --project ~/cves-resolve-check build
```

- [ ] The new master shows c2 0.2 s later, the shorter CTA head, the moved caption and a quieter bed.

If you have B-roll in a real project, also move and head-trim one B-roll shot on V2 and check `broll[k].start` / `in`.

## 7. Baked-layer relink

```bash
cves --project ~/cves-resolve-check control update --only c2
```

- [ ] In Resolve, right-click the c2 clip > Replace Clip (or `replace_clip` through the bridge) picks up the re-rendered
      file at the same path with no offset.

## 8. Windows only

- [ ] `install_resolve_bridge_windows.ps1` and `install_kdenlive_mcp_windows.ps1` run without error (they were written
      but never run: the build machine has no PowerShell).
- [ ] The Kdenlive `melt.exe` path the installer detects: ______

## 9. Report back

Paste the ticked list, every "______" filled in, the `--push` output and `IMPORT-REPORT.md` into an issue or a PR. When
everything passes, update README "Known limits" (the Resolve line) and CONTROL-MODE.md §9 ("Still needs a live Resolve test").
