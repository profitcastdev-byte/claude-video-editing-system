"""Layer manifest for control mode: ``Export/control/layers.json``.

The renderer (render.py, control mode) writes the manifest; the exporters
(resolve.py, kdenlive.py) only read it. The schema is documented in
docs/CONTROL-MODE.md ("layers.json"); this module is its reference
implementation: anything ``load_manifest`` accepts is a valid manifest.

All times in the manifest are seconds on the cut timeline. They are snapped
to the timeline frame grid (the manifest's own ``fps``, which the renderer takes
from the project) here, once, so every exporter places clips on the same frames.
There is no default rate or size: ``fps`` and ``size`` must be in the manifest.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

SCHEMA = "cves.layers/1"
AUDIO_RATE = 48000

# track -> (kind, role). Fixed by ARCHITECTURE.md section 7.
TRACKS: dict[str, tuple[str, str]] = {
    "V1": ("video", "aroll"),
    "V2": ("video", "cutaway"),
    "V3": ("video", "overlay"),
    "A1": ("audio", "voice"),
    "A2": ("audio", "music"),
    "A3": ("audio", "sfx"),
}
VIDEO_TRACKS = ("V1", "V2", "V3")
AUDIO_TRACKS = ("A1", "A2", "A3")


class LayersError(ValueError):
    """The manifest is invalid. ``problems`` lists every problem found."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("invalid layers.json:\n  - " + "\n  - ".join(problems))


@dataclass
class Clip:
    id: str
    track: str
    path: Path                 # absolute
    start: float               # timeline seconds (as written)
    end: float
    source_in: float
    start_frame: int           # snapped
    end_frame: int             # exclusive
    source_in_frame: int
    alpha: bool = False
    gain_db: float = 0.0
    name: str = ""
    edit_ref: str = ""         # e.g. "cutaways.c3": where this layer comes from in edit.yaml
    fps: tuple[int, int] | None = None     # video: the timeline's (checked equal)
    size: tuple[int, int] | None = None
    channels: int = 2
    sample_rate: int = AUDIO_RATE

    @property
    def kind(self) -> str:
        return TRACKS[self.track][0]

    @property
    def role(self) -> str:
        return TRACKS[self.track][1]

    @property
    def duration_frames(self) -> int:
        return self.end_frame - self.start_frame


@dataclass
class Caption:
    index: int
    start: float
    end: float
    text: str
    start_frame: int
    end_frame: int


@dataclass
class Manifest:
    path: Path                 # the layers.json file
    name: str
    fps: tuple[int, int]
    size: tuple[int, int]
    audio_rate: int
    duration: float
    duration_frames: int
    clips: list[Clip] = field(default_factory=list)
    captions: list[Caption] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self.path.parent

    @property
    def fps_fraction(self) -> Fraction:
        return Fraction(self.fps[0], self.fps[1])

    def track(self, name: str) -> list[Clip]:
        return sorted((c for c in self.clips if c.track == name), key=lambda c: c.start_frame)

    def media_files(self) -> list[Path]:
        seen: dict[str, Path] = {}
        for c in sorted(self.clips, key=lambda c: (c.track, c.start_frame)):
            seen.setdefault(str(c.path), c.path)
        return list(seen.values())

    def frames_to_seconds(self, frames: int) -> float:
        return float(Fraction(frames) / self.fps_fraction)


# --------------------------------------------------------------------------- time


def seconds_to_frames(seconds: float, fps: tuple[int, int]) -> int:
    """Nearest frame on the fps grid (half away from zero, so 0.5 frames -> 1)."""
    exact = Fraction(str(seconds)) * Fraction(fps[0], fps[1])
    whole = int(exact)
    return whole + (1 if exact - whole >= Fraction(1, 2) else 0)


def frames_to_rational(frames: int, fps: tuple[int, int]) -> str:
    """FCPXML rational time, reduced: 3 frames at 25/1 -> '3/25s', 3 frames at 30000/1001 -> '1001/10000s'."""
    if frames == 0:
        return "0s"
    t = Fraction(frames * fps[1], fps[0])
    return f"{t.numerator}s" if t.denominator == 1 else f"{t.numerator}/{t.denominator}s"


def frames_to_srt_time(frames: int, fps: tuple[int, int]) -> str:
    ms_total = int(Fraction(frames * fps[1] * 1000, fps[0]) + Fraction(1, 2))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# --------------------------------------------------------------------------- load


def _pair(value: Any, label: str, problems: list[str]) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(v, int) for v in value):
        return int(value[0]), int(value[1])
    problems.append(f"{label} must be a [int, int] pair, got {value!r}")
    return None


def _num(obj: dict, key: str, label: str, problems: list[str], default: float | None = None) -> float | None:
    if key not in obj:
        if default is None:
            problems.append(f"{label}: missing '{key}'")
        return default
    v = obj[key]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        problems.append(f"{label}: '{key}' must be a number, got {v!r}")
        return default
    return float(v)


def load_manifest(path: str | os.PathLike, *, check_files: bool = True) -> Manifest:
    """Read and validate ``layers.json``. Raises LayersError listing every problem."""
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path / "layers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise LayersError([f"{path} not found"]) from None
    except json.JSONDecodeError as exc:
        raise LayersError([f"{path} is not valid JSON: {exc}"]) from None
    return parse_manifest(data, path, check_files=check_files)


def parse_manifest(data: dict, path: Path, *, check_files: bool = True) -> Manifest:
    problems: list[str] = []
    if not isinstance(data, dict):
        raise LayersError(["top level must be a JSON object"])
    if data.get("schema") != SCHEMA:
        problems.append(f"'schema' must be \"{SCHEMA}\", got {data.get('schema')!r}")

    fps = _pair(data.get("fps"), "fps", problems)
    if fps and (fps[0] <= 0 or fps[1] <= 0 or not 1 <= fps[0] / fps[1] <= 240):
        problems.append(f"fps must be a positive [num, den] rate between 1 and 240 fps, got {list(fps)}")
        fps = None
    size = _pair(data.get("size"), "size", problems)
    if size and (size[0] <= 0 or size[1] <= 0 or size[0] % 2 or size[1] % 2):
        problems.append(f"size must be positive even [width, height] (4:2:2 media), got {list(size)}")
    if fps is None or size is None:
        raise LayersError(problems)
    audio_rate = int(data.get("audio_rate", AUDIO_RATE))
    if audio_rate <= 0:
        problems.append(f"audio_rate must be positive, got {audio_rate}")
    name = str(data.get("name") or path.parent.parent.name or "CVES timeline")
    duration = _num(data, "duration", "top level", problems, default=0.0) or 0.0

    root = path.parent
    clips: list[Clip] = []
    ids: set[str] = set()
    raw_clips = data.get("clips")
    if not isinstance(raw_clips, list) or not raw_clips:
        problems.append("'clips' must be a non-empty list")
        raw_clips = []

    for i, rc in enumerate(raw_clips):
        label = f"clips[{i}]"
        if not isinstance(rc, dict):
            problems.append(f"{label} must be an object")
            continue
        cid = str(rc.get("id") or "")
        label = f"clips[{i}] ({cid or 'no id'})"
        if not cid:
            problems.append(f"{label}: missing 'id'")
        elif cid in ids:
            problems.append(f"{label}: duplicate id")
        ids.add(cid)
        track = rc.get("track")
        if track not in TRACKS:
            problems.append(f"{label}: 'track' must be one of {list(TRACKS)}, got {track!r}")
            continue
        kind, role = TRACKS[track]
        if "role" in rc and rc["role"] != role:
            problems.append(f"{label}: track {track} carries role '{role}', got role {rc['role']!r}")
        raw_path = rc.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            problems.append(f"{label}: missing 'path'")
            continue
        p = Path(raw_path).expanduser()
        p = (p if p.is_absolute() else root / p).resolve()
        if check_files and not p.is_file():
            problems.append(f"{label}: file not found: {p}")
        start = _num(rc, "start", label, problems)
        end = _num(rc, "end", label, problems)
        source_in = _num(rc, "source_in", label, problems, default=0.0)
        if start is None or end is None:
            continue
        sf, ef = seconds_to_frames(start, fps), seconds_to_frames(end, fps)
        si = seconds_to_frames(source_in or 0.0, fps)
        if start < 0 or (source_in or 0) < 0:
            problems.append(f"{label}: start and source_in must be >= 0")
        if ef <= sf:
            problems.append(f"{label}: end ({end}) must be at least one frame after start ({start})")

        clip = Clip(id=cid, track=track, path=p, start=start, end=end, source_in=source_in or 0.0,
                    start_frame=sf, end_frame=ef, source_in_frame=si,
                    alpha=bool(rc.get("alpha", track == "V3")),
                    gain_db=float(rc.get("gain_db", 0.0)),
                    name=str(rc.get("name") or p.name),
                    edit_ref=str(rc.get("edit_ref") or ""))
        if kind == "video":
            vfps = _pair(rc.get("fps", list(fps)), f"{label}.fps", problems) or fps
            vsize = _pair(rc.get("size", list(size)), f"{label}.size", problems) or size
            if vfps != fps:
                problems.append(f"{label}: clip fps {list(vfps)} differs from timeline fps {list(fps)}")
            if vsize != size:
                problems.append(f"{label}: clip size {list(vsize)} differs from timeline size {list(size)}")
            clip.fps, clip.size = vfps, vsize
            if track == "V3" and not clip.alpha:
                problems.append(f"{label}: V3 overlays must have alpha (ProRes 4444)")
            if p.suffix.lower() not in (".mov", ".mxf", ".mp4"):
                problems.append(f"{label}: video layers must be .mov ProRes, got {p.suffix}")
        else:
            clip.channels = int(rc.get("channels", 2))
            clip.sample_rate = int(rc.get("sample_rate", audio_rate))
            if clip.sample_rate != audio_rate:
                problems.append(f"{label}: sample_rate {clip.sample_rate} differs from {audio_rate}")
            if p.suffix.lower() not in (".wav", ".aif", ".aiff"):
                problems.append(f"{label}: audio stems must be .wav, got {p.suffix}")
        clips.append(clip)

    # overlaps per track (on snapped frames)
    for t in TRACKS:
        on_track = sorted((c for c in clips if c.track == t), key=lambda c: c.start_frame)
        for a, b in zip(on_track, on_track[1:]):
            if b.start_frame < a.end_frame:
                problems.append(f"track {t}: '{a.id}' (to frame {a.end_frame}) overlaps '{b.id}' "
                                f"(from frame {b.start_frame})")

    last = max((c.end_frame for c in clips), default=0)
    duration_frames = seconds_to_frames(duration, fps) if duration else last
    if duration_frames < last:
        problems.append(f"'duration' ({duration}s = {duration_frames} frames) is shorter than the last "
                        f"clip end ({last} frames)")

    captions: list[Caption] = []
    raw_caps = data.get("captions", [])
    if not isinstance(raw_caps, list):
        problems.append("'captions' must be a list")
        raw_caps = []
    for i, cap in enumerate(raw_caps):
        label = f"captions[{i}]"
        if not isinstance(cap, dict):
            problems.append(f"{label} must be an object")
            continue
        s = _num(cap, "start", label, problems)
        e = _num(cap, "end", label, problems)
        text = cap.get("text")
        if not isinstance(text, str) or not text.strip():
            problems.append(f"{label}: 'text' must be a non-empty string")
            continue
        if s is None or e is None:
            continue
        sf, ef = seconds_to_frames(s, fps), seconds_to_frames(e, fps)
        if ef <= sf:
            problems.append(f"{label}: end must be at least one frame after start")
        if ef > duration_frames:
            problems.append(f"{label}: ends after the timeline ({e}s)")
        captions.append(Caption(index=int(cap.get("index", i + 1)), start=s, end=e, text=text.strip(),
                                start_frame=sf, end_frame=ef))
    captions.sort(key=lambda c: c.start_frame)
    for a, b in zip(captions, captions[1:]):
        if b.start_frame < a.end_frame:
            problems.append(f"captions {a.index} and {b.index} overlap")

    if problems:
        raise LayersError(problems)
    return Manifest(path=path, name=name, fps=fps, size=size, audio_rate=audio_rate,
                    duration=duration or float(Fraction(last * fps[1], fps[0])),
                    duration_frames=duration_frames, clips=clips, captions=captions, raw=data)


# --------------------------------------------------------------------------- shared outputs


def write_srt(manifest: Manifest, out_path: str | os.PathLike | None = None) -> Path:
    """captions.srt, cue times on the same frame grid as the timeline, renumbered 1..n."""
    out = Path(out_path) if out_path else manifest.root / "captions.srt"
    lines: list[str] = []
    for n, cap in enumerate(manifest.captions, start=1):
        lines += [str(n),
                  f"{frames_to_srt_time(cap.start_frame, manifest.fps)} --> "
                  f"{frames_to_srt_time(cap.end_frame, manifest.fps)}",
                  cap.text, ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_otio(manifest: Manifest):
    """The master timeline as an OpenTimelineIO object (timeline.otio)."""
    import opentimelineio as otio

    rate = float(manifest.fps_fraction)

    def rt(frames: int):
        return otio.opentime.RationalTime(frames, rate)

    tl = otio.schema.Timeline(name=manifest.name, global_start_time=rt(0))
    tl.metadata["cves"] = {"schema": SCHEMA, "size": list(manifest.size), "fps": list(manifest.fps)}
    for tname in (*VIDEO_TRACKS, *AUDIO_TRACKS):
        kind = otio.schema.TrackKind.Video if tname.startswith("V") else otio.schema.TrackKind.Audio
        track = otio.schema.Track(name=f"{tname} {TRACKS[tname][1]}", kind=kind)
        cursor = 0
        for c in manifest.track(tname):
            if c.start_frame > cursor:
                track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(rt(0), rt(c.start_frame - cursor))))
            ref = otio.schema.ExternalReference(target_url=c.path.as_uri())
            clip = otio.schema.Clip(
                name=c.name, media_reference=ref,
                source_range=otio.opentime.TimeRange(rt(c.source_in_frame), rt(c.duration_frames)))
            clip.metadata["cves"] = {"id": c.id, "role": c.role, "alpha": c.alpha,
                                     "gain_db": c.gain_db, "edit_ref": c.edit_ref}
            track.append(clip)
            cursor = c.end_frame
        if cursor < manifest.duration_frames:
            track.append(otio.schema.Gap(
                source_range=otio.opentime.TimeRange(rt(0), rt(manifest.duration_frames - cursor))))
        tl.tracks.append(track)
    for cap in manifest.captions:
        tl.tracks[0].markers.append(otio.schema.Marker(
            name=cap.text, marked_range=otio.opentime.TimeRange(rt(cap.start_frame), rt(cap.end_frame - cap.start_frame)),
            metadata={"cves": {"caption": cap.index}}))
    return tl


def write_otio(manifest: Manifest, out_path: str | os.PathLike | None = None) -> Path:
    import opentimelineio as otio

    out = Path(out_path) if out_path else manifest.root / "timeline.otio"
    otio.adapters.write_to_file(build_otio(manifest), str(out))
    return out


def probe(path: Path) -> dict:
    """ffprobe summary (duration seconds, timecode, has_video/has_audio). Empty dict if ffprobe is missing."""
    import shutil
    import subprocess

    exe = shutil.which("ffprobe")
    if not exe:
        return {}
    try:
        out = subprocess.run([exe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                             capture_output=True, text=True, timeout=60, check=True).stdout
        info = json.loads(out)
    except Exception:  # noqa: BLE001 - probing is best effort
        return {}
    streams = info.get("streams", [])
    tc = (info.get("format", {}).get("tags", {}) or {}).get("timecode")
    for s in streams:
        tc = tc or (s.get("tags", {}) or {}).get("timecode")
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    return {
        "duration": float(info.get("format", {}).get("duration", 0) or 0),
        "timecode": tc,
        "has_video": v is not None,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "pix_fmt": v.get("pix_fmt") if v else None,
        "codec": v.get("codec_name") if v else None,
        "width": v.get("width") if v else None,
        "height": v.get("height") if v else None,
        "audio_channels": next((s.get("channels") for s in streams if s.get("codec_type") == "audio"), None),
    }
