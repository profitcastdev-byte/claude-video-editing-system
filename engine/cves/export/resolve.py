"""DaVinci Resolve export: timeline.fcpxml + captions.srt, and a live import through the CursorBridge.

FCPXML choices (see docs/CONTROL-MODE.md, "Why the FCPXML looks like this", for sources):

* ``version="1.10"``: the newest version every Resolve from 18 up accepts (1.11+ needs Resolve 21).
* The rate is the manifest's (the project's): ``frameDuration`` is one frame as a reduced rational
  (23.976 -> ``1001/24000s``, 25 -> ``1/25s``, 29.97 -> ``1001/30000s``); every time is a whole number
  of frames written the same way (3 frames at 23.976 -> ``3003/24000s``), so Resolve never has to round.
* The sequence format is ``FFVideoFormatRateUndefined`` with explicit width/height (what Resolve-tested
  exporters write; it works for any size, vertical included). Media formats use FCP's own name for a
  standard size (``FFVideoFormat1080p25``) and a custom ``FFVideoFormat<w>x<h>p<rate>`` otherwise
  (``FFVideoFormat1080x1920p2398``), always with explicit width, height and frameDuration.
* One ``<gap>`` spans the spine and every layer is a connected clip on a lane: V1..V3 -> lanes 1..3,
  A1..A3 -> lanes -1..-3. Resolve turns lanes into tracks in that order, so the tracks are fixed
  regardless of gaps on V1.
* ``<media-rep src>`` is an absolute ``file://`` URL with RFC 3986 sub-delimiters percent-encoded
  (Resolve fails to relink when they appear raw or as XML entities); clip names are the file name
  including extension because Resolve relinks by file name.
* Media without embedded timecode starts at ``0s``; media with a ``timecode`` tag starts there, so
  Resolve does not flag a source-timecode mismatch.
* Alpha is not an FCPXML attribute in Resolve: after import the bridge sets the overlays' media pool
  ``Alpha mode`` clip attribute (``drive_import``).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from typing import Any

from .layers import (AUDIO_TRACKS, VIDEO_TRACKS, Clip, Manifest, frames_to_rational, load_manifest, probe,
                     write_otio, write_srt)

FCPXML_VERSION = "1.10"
LANES = {"V1": 1, "V2": 2, "V3": 3, "A1": -1, "A2": -2, "A3": -3}
AUDIO_ROLES = {"A1": "dialogue", "A2": "music", "A3": "effects"}
BRIDGE_URL = os.environ.get("CVES_RESOLVE_BRIDGE", "http://127.0.0.1:9876")
# Straight = unassociated alpha, which is what PIL RGBA -> ffmpeg prores_ks yuva444p10le carries.
OVERLAY_ALPHA_MODE = os.environ.get("CVES_RESOLVE_ALPHA_MODE", "Straight")


# --------------------------------------------------------------------------- FCPXML


def _file_url(path: Path) -> str:
    url = path.resolve().as_uri()
    # as_uri() already percent-encodes spaces and non-ASCII; also encode sub-delims if any survived.
    return "".join(f"%{ord(ch):02X}" if ch in "'!$&()*+,;=" else ch for ch in url)


# FCP's named raster formats (width, height) -> name stem; anything else gets a custom <w>x<h> name.
_NAMED_RASTERS = {(1920, 1080): "1080p", (1280, 720): "720p", (3840, 2160): "3840x2160p", (4096, 2160): "4096x2160p",
                  (2048, 1080): "2048x1080p", (1440, 1080): "1440x1080p", (640, 480): "640x480p", (720, 576): "720x576p"}


def rate_code(fps: tuple[int, int]) -> str:
    """FCP format-name rate suffix: NTSC film rate -> '2398', 30000/1001 -> '2997', 25/1 -> '25', 60000/1001 -> '5994'."""
    r = Fraction(fps[0], fps[1])
    if r.denominator == 1:
        return str(r.numerator)
    return f"{float(r):.2f}".replace(".", "")


def rate_label(fps: tuple[int, int]) -> str:
    """Resolve's project-setting spelling: 3 decimals for the NTSC film rates, '29.97', '59.94', '25', '30'."""
    r = Fraction(fps[0], fps[1])
    if r.denominator == 1:
        return str(r.numerator)
    v = float(r)
    return f"{v:.3f}" if round(v) % 24 == 0 else f"{v:.2f}"      # 23.976 / 47.952, 29.97 / 59.94


def format_name(size: tuple[int, int], fps: tuple[int, int]) -> str:
    stem = _NAMED_RASTERS.get(tuple(size), f"{size[0]}x{size[1]}p")
    return f"FFVideoFormat{stem}{rate_code(fps)}"


def _tc_to_frames(tc: str | None, fps: tuple[int, int]) -> int:
    """'01:00:00:00' (NDF) -> frames at the nominal integer rate (24 for the NTSC film rate, 30 for 29.97)."""
    if not tc:
        return 0
    m = re.match(r"^(\d+):(\d+):(\d+)[:;.](\d+)$", tc.strip())
    if not m:
        return 0
    h, mi, s, f = (int(x) for x in m.groups())
    nominal = round(fps[0] / fps[1])
    return ((h * 60 + mi) * 60 + s) * nominal + f


def _asset_frames(clips: list[Clip], info: dict, fps: tuple[int, int]) -> int:
    need = max(c.source_in_frame + c.duration_frames for c in clips)
    have = int(Fraction(str(info.get("duration") or 0)) * Fraction(fps[0], fps[1]))
    return max(need, have)


def build_fcpxml(manifest: Manifest, *, version: str = FCPXML_VERSION, probe_media: bool = True) -> ET.Element:
    fps = manifest.fps
    w, h = manifest.size
    root = ET.Element("fcpxml", version=version)
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", id="r1", name="FFVideoFormatRateUndefined",
                  frameDuration=frames_to_rational(1, fps), width=str(w), height=str(h),
                  colorSpace="1-1-1 (Rec. 709)")
    ET.SubElement(res, "format", id="r2", name=format_name((w, h), fps),
                  frameDuration=frames_to_rational(1, fps), width=str(w), height=str(h),
                  colorSpace="1-1-1 (Rec. 709)")

    by_file: dict[str, list[Clip]] = {}
    for c in manifest.clips:
        by_file.setdefault(str(c.path), []).append(c)

    asset_ids: dict[str, str] = {}
    asset_tc: dict[str, int] = {}
    next_id = 3
    for key, clips in by_file.items():
        path = clips[0].path
        info = probe(path) if probe_media else {}
        is_video = clips[0].kind == "video"
        aid = f"r{next_id}"
        next_id += 1
        asset_ids[key] = aid
        tc_frames = _tc_to_frames(info.get("timecode"), fps)
        asset_tc[key] = tc_frames
        attrs: dict[str, str] = {
            "id": aid, "name": path.name,
            "start": frames_to_rational(tc_frames, fps),
            "duration": frames_to_rational(_asset_frames(clips, info, fps), fps),
        }
        if is_video:
            attrs.update(hasVideo="1", videoSources="1", format="r2")
            if info.get("has_audio"):
                attrs.update(hasAudio="1", audioSources="1",
                             audioChannels=str(info.get("audio_channels") or 2), audioRate="48000")
        else:
            attrs.update(hasAudio="1", audioSources="1", audioChannels=str(clips[0].channels),
                         audioRate=str(clips[0].sample_rate))
        asset = ET.SubElement(res, "asset", attrs)
        ET.SubElement(asset, "media-rep", kind="original-media", src=_file_url(path))

    lib = ET.SubElement(root, "library")
    event = ET.SubElement(lib, "event", name="CVES")
    project = ET.SubElement(event, "project", name=manifest.name)
    total = frames_to_rational(manifest.duration_frames, fps)
    seq = ET.SubElement(project, "sequence", format="r1", duration=total, tcStart="0s", tcFormat="NDF",
                        audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(seq, "spine")
    gap = ET.SubElement(spine, "gap", name="Timeline", offset="0s", start="0s", duration=total)

    track_order = {t: i for i, t in enumerate((*VIDEO_TRACKS, *AUDIO_TRACKS))}
    ordered = sorted(manifest.clips, key=lambda c: (c.start_frame, track_order[c.track]))
    for c in ordered:
        key = str(c.path)
        attrs = {
            "ref": asset_ids[key],
            "lane": str(LANES[c.track]),
            "offset": frames_to_rational(c.start_frame, fps),
            "name": c.path.name,
            "start": frames_to_rational(asset_tc[key] + c.source_in_frame, fps),
            "duration": frames_to_rational(c.duration_frames, fps),
            "enabled": "1",
            "tcFormat": "NDF",
        }
        if c.kind == "video":
            attrs["format"] = "r2"
        else:
            attrs["audioRole"] = AUDIO_ROLES[c.track]
        ac = ET.SubElement(gap, "asset-clip", attrs)
        # child order follows the FCPXML DTD: note, adjust-conform, adjust-volume
        ET.SubElement(ac, "note").text = f"cves:{c.id}" + (f" edit:{c.edit_ref}" if c.edit_ref else "")
        if c.kind == "video":
            ET.SubElement(ac, "adjust-conform", type="fit")
        if c.gain_db:
            ET.SubElement(ac, "adjust-volume", amount=f"{c.gain_db:g}dB")
    return root


def write_fcpxml(manifest: Manifest, out_path: str | os.PathLike | None = None, **kw) -> Path:
    out = Path(out_path) if out_path else manifest.root / "timeline.fcpxml"
    root = build_fcpxml(manifest, **kw)
    ET.indent(root, space="    ")
    body = ET.tostring(root, encoding="unicode")
    out.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n\n' + body + "\n", encoding="utf-8")
    return out


def check_fcpxml(path: str | os.PathLike, manifest: Manifest) -> list[str]:
    """Structural checks on a written FCPXML against its manifest. Returns problems (empty = pass)."""
    problems: list[str] = []
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "fcpxml" or root.get("version") != FCPXML_VERSION:
        problems.append(f"root must be <fcpxml version=\"{FCPXML_VERSION}\">")
    fps = manifest.fps
    want_fd = frames_to_rational(1, fps)
    want_wh = (str(manifest.size[0]), str(manifest.size[1]))
    fmts = {f.get("id"): f for f in root.iter("format")}
    for f in fmts.values():
        if f.get("frameDuration") != want_fd:
            problems.append(f"format {f.get('id')} frameDuration {f.get('frameDuration')} != {want_fd}")
        if (f.get("width"), f.get("height")) != want_wh:
            problems.append(f"format {f.get('id')} is not {want_wh[0]}x{want_wh[1]}")
    seq = root.find("./library/event/project/sequence")
    if seq is None:
        return problems + ["no library/event/project/sequence"]
    if seq.get("format") not in fmts:
        problems.append("sequence format does not resolve")
    assets = {a.get("id"): a for a in root.iter("asset")}
    for a in assets.values():
        rep = a.find("media-rep")
        if rep is None or not rep.get("src", "").startswith("file:///"):
            problems.append(f"asset {a.get('id')} lacks an absolute file:// media-rep")
        elif re.search(r"[ '!$&()*+,;=]", rep.get("src", "")[7:]):
            problems.append(f"asset {a.get('id')} src has unencoded characters")
        if a.get("format") and a.get("format") not in fmts:
            problems.append(f"asset {a.get('id')} format does not resolve")

    def frames(rational: str) -> Fraction:
        n = rational[:-1]
        t = Fraction(n) if "/" in n else Fraction(int(n))
        f = t * Fraction(fps[0], fps[1])
        if f.denominator != 1:
            problems.append(f"time {rational} is not on the {fps[0]}/{fps[1]} frame grid")
        return f

    seq_frames = frames(seq.get("duration"))
    if seq_frames != manifest.duration_frames:
        problems.append(f"sequence duration {seq_frames} frames != manifest {manifest.duration_frames}")
    by_lane: dict[int, list[tuple[Fraction, Fraction]]] = {}
    count = 0
    for ac in seq.iter("asset-clip"):
        count += 1
        if ac.get("ref") not in assets:
            problems.append(f"asset-clip {ac.get('name')} ref does not resolve")
        lane = int(ac.get("lane", "0"))
        off, dur = frames(ac.get("offset")), frames(ac.get("duration"))
        frames(ac.get("start", "0s"))
        by_lane.setdefault(lane, []).append((off, off + dur))
        if off + dur > seq_frames:
            problems.append(f"asset-clip {ac.get('name')} runs past the sequence end")
        if lane > 0 and ac.find("adjust-conform") is None:
            problems.append(f"video clip {ac.get('name')} lacks adjust-conform")
        if lane < 0 and not ac.get("audioRole"):
            problems.append(f"audio clip {ac.get('name')} lacks audioRole")
    if count != len(manifest.clips):
        problems.append(f"{count} asset-clips != {len(manifest.clips)} manifest clips")
    for lane, spans in by_lane.items():
        spans.sort()
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            if b0 < a1:
                problems.append(f"lane {lane}: clips overlap at frame {b0}")
    want = {LANES[t] for t in (*VIDEO_TRACKS, *AUDIO_TRACKS) if manifest.track(t)}
    if set(by_lane) != want:
        problems.append(f"lanes {sorted(by_lane)} != expected {sorted(want)}")
    return problems


def export(control_dir: str | os.PathLike, *, otio: bool = True) -> dict[str, Path]:
    """Write timeline.fcpxml, captions.srt (and timeline.otio) next to layers.json."""
    manifest = load_manifest(control_dir)
    out = {"fcpxml": write_fcpxml(manifest), "srt": write_srt(manifest)}
    if otio:
        out["otio"] = write_otio(manifest)
    problems = check_fcpxml(out["fcpxml"], manifest)
    if problems:
        raise RuntimeError("timeline.fcpxml failed its own checks:\n  " + "\n  ".join(problems))
    return out


# --------------------------------------------------------------------------- live bridge


class BridgeError(RuntimeError):
    pass


class Bridge:
    """Minimal client for the CursorBridge HTTP API (127.0.0.1:9876) running inside Resolve.

    The MCP server (resolve_mcp_bridge.py) talks to the same endpoints; this client lets the CVES
    engine run the deterministic import without a model in the loop.
    """

    def __init__(self, url: str = BRIDGE_URL, timeout: float = 60.0):
        if not re.match(r"^http://(127\.0\.0\.1|localhost):\d+$", url):
            raise BridgeError("the bridge URL must be http://127.0.0.1:<port> (local only)")
        self.url = url
        self.timeout = timeout

    def _call(self, method: str, endpoint: str, body: dict | None = None) -> dict:
        data = json.dumps(body or {}).encode() if method == "POST" else None
        req = urllib.request.Request(self.url + endpoint, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except Exception:  # noqa: BLE001
                return {"error": f"HTTP {e.code}"}
        except urllib.error.URLError as e:
            raise BridgeError(
                "Cannot reach the CursorBridge. Open Resolve, then Workspace > Scripts > Utility > "
                f"CursorBridge, and retry. ({e.reason})") from None

    def get(self, endpoint: str) -> dict:
        return self._call("GET", endpoint)

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        return self._call("POST", endpoint, body)

    def ok(self, endpoint: str, body: dict | None = None, *, soft: bool = False) -> dict:
        r = self.post(endpoint, body)
        if r.get("error") or r.get("success") is False:
            if soft:
                return r
            raise BridgeError(f"{endpoint} failed: {r.get('error') or r}")
        return r


def snapshot(bridge: Bridge, snap_dir: str | os.PathLike, label: str = "before") -> Path | None:
    """Export the open project as a .drp into Export/control/snapshots/ (restore: File > Import Project)."""
    proj = bridge.get("/project")
    name = proj.get("name") or proj.get("projectName")
    if not name:
        return None
    snap_dir = Path(snap_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{re.sub(r'[^A-Za-z0-9_-]+', '_', label)}.drp"
    bridge.ok("/project/save", soft=True)
    r = bridge.ok("/projects/export", {"projectName": name, "filePath": str(path), "withStillsAndLUTs": False},
                  soft=True)
    return path if r.get("success") else None


def drive_import(control_dir: str | os.PathLike, *, project_name: str | None = None,
                 bridge: Bridge | None = None, log=print) -> dict[str, Any]:
    """create project -> settings -> import media -> import timeline -> alpha -> subtitles -> save.

    Needs Resolve open with the (CVES-hardened) CursorBridge running. Steps that the Resolve API
    cannot guarantee are reported in ``result["manual"]`` instead of failing the whole import.
    """
    manifest = load_manifest(control_dir)
    paths = export(control_dir)
    b = bridge or Bridge()
    status = b.get("/status")
    if status.get("error"):
        raise BridgeError(status["error"])
    name = project_name or manifest.name
    result: dict[str, Any] = {"project": name, "manual": [], "steps": []}

    r = b.post("/projects/create", {"projectName": name})
    if r.get("error"):
        log(f"project '{name}' exists; snapshotting and loading it")
        b.ok("/projects/load", {"projectName": name})
        result["snapshot"] = str(snapshot(b, manifest.root / "snapshots", "before-reimport"))
    result["steps"].append("project")

    # Must happen before any media lands in the pool (Resolve locks the frame rate after that).
    rate = rate_label(manifest.fps)
    for key, value in (("timelineFrameRate", rate), ("timelinePlaybackFrameRate", rate),
                       ("timelineResolutionWidth", str(manifest.size[0])),
                       ("timelineResolutionHeight", str(manifest.size[1]))):
        r = b.ok("/project/setting", {"key": key, "value": value}, soft=True)
        if not r.get("success"):
            result["manual"].append(f"Project Settings: set {key} = {value} (API refused: {r})")
    result["steps"].append("settings")

    media = [str(p) for p in manifest.media_files()]
    b.ok("/media/import", {"filePaths": media})
    result["steps"].append(f"media ({len(media)} files)")

    tl_name = f"{manifest.name} (CVES)"
    r = b.ok("/mediapool/timeline/import", {"filePath": str(paths["fcpxml"]),
                                            "importOptions": {"timelineName": tl_name, "importSourceClips": False}},
             soft=True)
    if not r.get("success"):
        log("timeline import against the pool failed; retrying with importSourceClips")
        b.ok("/mediapool/timeline/import", {"filePath": str(paths["fcpxml"]),
                                            "importOptions": {"timelineName": tl_name, "importSourceClips": True}})
    b.ok("/cves/timeline/current", {"timelineName": tl_name}, soft=True)
    result["steps"].append("timeline")

    for c in manifest.track("V3"):
        r = b.ok("/mediapool/clip/property", {"clipName": c.path.name, "propertyName": "Alpha mode",
                                              "propertyValue": OVERLAY_ALPHA_MODE}, soft=True)
        if not r.get("success"):
            result["manual"].append(f"Media Pool > {c.path.name} > Clip Attributes > Alpha Mode = "
                                    f"{OVERLAY_ALPHA_MODE}")
    for idx, tname in enumerate(("V1", "V2", "V3"), start=1):
        b.ok("/track/rename", {"trackType": "video", "trackIndex": idx, "name": f"{tname} {('A-roll', 'Cutaways', 'Overlays')[idx - 1]}"}, soft=True)
    for idx, label in enumerate(("Voice", "Music", "SFX"), start=1):
        b.ok("/track/rename", {"trackType": "audio", "trackIndex": idx, "name": f"A{idx} {label}"}, soft=True)
    result["steps"].append("alpha + track names")

    if manifest.captions:
        r = b.ok("/cves/subtitles", {"srtPath": str(paths["srt"]), "timelineName": tl_name}, soft=True)
        if r.get("success"):
            result["steps"].append("subtitles")
        else:
            result["manual"].append("Drag captions.srt from the Media Pool onto the timeline start "
                                    f"(bridge: {r.get('error') or r})")
    b.ok("/project/save", soft=True)
    result["steps"].append("saved")
    return result


def push_subtitles(control_dir: str | os.PathLike, *, timeline_name: str | None = None,
                   bridge: Bridge | None = None) -> dict[str, Any]:
    """Snapshot, then replace subtitle track 1 of the open timeline with a fresh captions.srt."""
    manifest = load_manifest(control_dir)
    srt = write_srt(manifest)
    b = bridge or Bridge()
    snap = snapshot(b, manifest.root / "snapshots", "before-captions")
    r = b.ok("/cves/subtitles", {"srtPath": str(srt), "replace": True,
                                 "timelineName": timeline_name or f"{manifest.name} (CVES)"}, soft=True)
    return {"snapshot": str(snap) if snap else None, **r}


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="cves export resolve")
    ap.add_argument("control_dir", nargs="?", default="Export/control")
    ap.add_argument("--push", action="store_true", help="also import into the running Resolve via the bridge")
    ap.add_argument("--project", help="Resolve project name (default: manifest name)")
    ap.add_argument("--push-subtitles", action="store_true",
                    help="snapshot, then replace the open timeline's subtitle track with captions from layers.json")
    ap.add_argument("--snapshot", metavar="LABEL", help="export the open Resolve project to snapshots/<time>-LABEL.drp")
    a = ap.parse_args(argv)
    if a.snapshot:
        m = load_manifest(a.control_dir)
        print(snapshot(Bridge(), m.root / "snapshots", a.snapshot))
    elif a.push_subtitles:
        print(json.dumps(push_subtitles(a.control_dir), indent=2))
    elif a.push:
        print(json.dumps(drive_import(a.control_dir, project_name=a.project), indent=2))
    else:
        for k, v in export(a.control_dir).items():
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
