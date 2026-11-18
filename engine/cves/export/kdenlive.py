"""Kdenlive export: project.kdenlive written directly as MLT XML (Kdenlive document version 1.1).

Why not the OTIO kdenlive adapter: otio-kdenlive-adapter 0.0.3 writes the pre-2023 layout (tracks
straight in the main tractor, no sequence UUIDs, no per-placement chains). Kdenlive 23.04+ upgrades
such files on open, but silently drops clips whose bin reference it cannot resolve. The layout here
follows what Kdenlive 24-26 itself writes (cross-checked against the 12bijaya Kdenlive MCP writer,
whose structure is taken from real Kdenlive 26.04 files and Kdenlive's loader source):

* every timeline track is a ``<tractor>`` holding two ``<playlist>`` (clips + empty companion);
* audio tracks carry ``kdenlive:audio_track=1`` and ``hide="video"``; the master (sequence)
  tractor lists black ``producer0``, then audio tracks A3..A1, then video V1..V3;
* compositing: one always-active ``qtblend`` per video track and ``mix`` per audio track, each
  against track 0, so V3's alpha composites over V2 over V1;
* each media file has one bin ``<chain>`` plus one dedicated ``<chain>`` per timeline placement,
  all sharing a ``kdenlive:control_uuid`` (Kdenlive drops placements without one);
* the sequence tractor is itself a bin clip (``kdenlive:producer_type=17``, an entry in
  ``main_bin``), else Kdenlive's DocumentChecker reports it as an "Unreferenced clip" and rebuilds it;
* ``main_bin`` carries ``xml_retain=1`` and the last top-level element is a
  ``kdenlive:projectTractor`` wrapper (that is how Kdenlive finds the bin);
* subtitles: written in the SRT layout, ``project.kdenlive.srt`` next to the project, listed in the
  sequence property ``subtitlesList`` and shown through an ``avfilter.subtitles`` filter on the
  sequence tractor. Kdenlive 24.08+ stores ASS (``project.kdenlive.ass``) and converts this layout on
  open (DocumentValidator::convertSubtitles, keeping the .srt); the Kdenlive MCP server reads only the
  SRT layout, so SRT is the form both can open;
* the profile: the ``<profile>`` element carries the manifest's own rate and size (any rate, any size).
  Kdenlive ships no profile for most vertical rasters, and its fallback path flags 24000/1001 as
  "non standard" (ProfileInfo::hasValidFps compares against 23.98 exactly). ``profile_text`` builds a
  matching custom profile; it is written next to the project as ``<profile name>`` and, with
  ``--install-profile``, copied into Kdenlive's custom profile folder (setup/control does this for the
  default vertical profile). When an installed profile matches the rate and size, the project
  references it by path.

Times are written the way Kdenlive writes them, ``HH:MM:SS.mmm`` (MLT rounds back to the exact frame;
a millisecond is far below the 41.7 ms frame). Bare integers would also be valid MLT, but the Kdenlive
MCP server's parser reads bare in/out values as seconds.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from .layers import AUDIO_TRACKS, TRACKS, VIDEO_TRACKS, Clip, Manifest, load_manifest, probe, write_srt

KDENLIVE_DOC_VERSION = "1.1"
KDENLIVE_VERSION_HINT = "26.04.3"
MLT_VERSION = "7.30.0"
PROFILE_KEYS = ("frame_rate_num", "frame_rate_den", "width", "height")


def _aspect(size: tuple[int, int]) -> tuple[int, int]:
    from math import gcd
    g = gcd(size[0], size[1]) or 1
    return size[0] // g, size[1] // g


def profile_name(fps: tuple[int, int], size: tuple[int, int]) -> str:
    from .resolve import rate_code
    return f"cves_{size[0]}x{size[1]}_{rate_code(fps)}"


def profile_values(fps: tuple[int, int], size: tuple[int, int]) -> dict[str, str]:
    from .resolve import rate_label
    da = _aspect(size)
    return {"description": f"CVES {size[0]}x{size[1]} {rate_label(fps)} fps",
            "frame_rate_num": str(fps[0]), "frame_rate_den": str(fps[1]), "width": str(size[0]), "height": str(size[1]),
            "progressive": "1", "sample_aspect_num": "1", "sample_aspect_den": "1",
            "display_aspect_num": str(da[0]), "display_aspect_den": str(da[1]), "colorspace": "709"}


def profile_text(fps: tuple[int, int], size: tuple[int, int]) -> str:
    """An MLT / Kdenlive custom profile for this exact rate and size."""
    return "".join(f"{k}={v}\n" for k, v in profile_values(fps, size).items())
TRACK_LABELS = {"V1": "V1 A-roll", "V2": "V2 Cutaways", "V3": "V3 Overlays",
                "A1": "A1 Voice", "A2": "A2 Music", "A3": "A3 SFX"}
_NS = uuid.UUID("6d0c7a3e-4b8e-4d1a-9a59-6b1f0c8e2a10")


def find_melt() -> str | None:
    for cand in (os.environ.get("CVES_MELT"), os.environ.get("KDENLIVE_MCP_MELT"),
                 shutil.which("melt"), shutil.which("melt-7"),
                 "/Applications/kdenlive.app/Contents/MacOS/melt",
                 r"C:\Program Files\kdenlive\bin\melt.exe"):
        if cand and Path(cand).is_file():
            return cand
    return None


def kdenlive_profile_dir() -> Path:
    """Kdenlive's custom profile folder (QStandardPaths::AppDataLocation + /profiles)."""
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "kdenlive" / "profiles"
    if os.uname().sysname == "Darwin":
        return Path.home() / "Library" / "Application Support" / "kdenlive" / "profiles"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "kdenlive" / "profiles"


def _read_profile(p: Path) -> dict[str, str]:
    try:
        return dict(ln.split("=", 1) for ln in p.read_text(encoding="utf-8").splitlines() if "=" in ln)
    except (OSError, UnicodeDecodeError, ValueError):
        return {}


def custom_profile_path(fps: tuple[int, int], size: tuple[int, int]) -> Path | None:
    """An installed Kdenlive custom profile (any file name) with this exact rate and size, else None."""
    d = kdenlive_profile_dir()
    if not d.is_dir():
        return None
    want = {k: v for k, v in profile_values(fps, size).items() if k in PROFILE_KEYS}
    named = d / profile_name(fps, size)
    for p in ([named] if named.is_file() else []) + sorted(x for x in d.iterdir() if x.is_file() and x != named):
        vals = _read_profile(p)
        if all(vals.get(k, "").strip() == v for k, v in want.items()):
            return p
    return None


def install_profile(fps: tuple[int, int], size: tuple[int, int]) -> Path:
    """Copy the matching custom profile into Kdenlive's profile folder (only when asked: --install-profile)."""
    have = custom_profile_path(fps, size)
    if have:
        return have
    d = kdenlive_profile_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / profile_name(fps, size)
    p.write_text(profile_text(fps, size), encoding="utf-8")
    return p


def _tc(frames: int, fps: tuple[int, int]) -> str:
    """Frames -> Kdenlive's HH:MM:SS.mmm clock string."""
    ms = (frames * fps[1] * 1000 * 2 + fps[0]) // (2 * fps[0])
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _sub(parent: ET.Element, tag: str, **attrs) -> ET.Element:
    el = ET.SubElement(parent, tag)
    for k, v in attrs.items():
        if v is not None:
            el.set(k.rstrip("_"), str(v))
    return el


def _prop(parent: ET.Element, name: str, value=None) -> ET.Element:
    el = ET.SubElement(parent, "property", name=name)
    if value is not None:
        el.text = str(value)
    return el


def _uuid(*parts: str) -> str:
    return "{%s}" % uuid.uuid5(_NS, "/".join(parts))


def build_kdenlive(manifest: Manifest, target: Path) -> ET.Element:
    fps = manifest.fps
    w, h = manifest.size
    total = manifest.duration_frames
    seq_uuid = _uuid(str(manifest.path), "sequence")

    mlt = ET.Element("mlt", LC_NUMERIC="C", producer="main_bin", root=str(target.parent), version=MLT_VERSION)
    pv = profile_values(fps, (w, h))
    _sub(mlt, "profile", colorspace="709", description=pv["description"],
         display_aspect_den=pv["display_aspect_den"], display_aspect_num=pv["display_aspect_num"],
         frame_rate_den=fps[1], frame_rate_num=fps[0],
         height=h, progressive="1", sample_aspect_den="1", sample_aspect_num="1", width=w)

    black = _sub(mlt, "producer", id="producer0", in_=_tc(0, fps), out=_tc(max(total, 1) - 1, fps))
    for k, v in (("length", "2147483647"), ("eof", "continue"), ("resource", "black"), ("aspect_ratio", "1"),
                 ("mlt_service", "color"), ("kdenlive:playlistid", "black_track"), ("mlt_image_format", "rgba")):
        _prop(black, k, v)

    # ---- bin: one chain per media file
    files: dict[str, dict] = {}
    for i, path in enumerate(manifest.media_files()):
        clips = [c for c in manifest.clips if c.path == path]
        info = probe(path)
        need = max(c.source_in_frame + c.duration_frames for c in clips)
        have = int((info.get("duration") or 0) * fps[0] / fps[1])
        files[str(path)] = {"bin_id": i + 2, "uuid": _uuid(str(path)), "length": max(need, have, 1),
                            "kind": clips[0].kind, "has_audio": info.get("has_audio", clips[0].kind == "audio"),
                            "has_video": clips[0].kind == "video", "folder": "-1"}

    def chain(path: Path, chain_id: str) -> ET.Element:
        f = files[str(path)]
        el = _sub(mlt, "chain", id=chain_id, out=_tc(f["length"] - 1, fps))
        _prop(el, "length", f["length"])
        _prop(el, "eof", "pause")
        _prop(el, "resource", str(path))
        _prop(el, "mlt_service", "avformat-novalidate")
        _prop(el, "seekable", "1")
        _prop(el, "video_index", "0" if f["has_video"] else "-1")
        _prop(el, "audio_index", ("1" if f["has_video"] else "0") if f["has_audio"] else "-1")
        _prop(el, "kdenlive:id", f["bin_id"])
        _prop(el, "kdenlive:control_uuid", f["uuid"])
        _prop(el, "kdenlive:folderid", f["folder"])
        _prop(el, "kdenlive:clipname", path.name)
        if path.is_file():
            _prop(el, "kdenlive:file_size", path.stat().st_size)
        return el

    bin_chain: dict[str, str] = {}
    for n, key in enumerate(files):
        bin_chain[key] = f"chain{n}"
        chain(Path(key), bin_chain[key])

    placement: dict[str, str] = {}
    n_place = 0
    for c in sorted(manifest.clips, key=lambda c: (c.track, c.start_frame)):
        placement[c.id] = f"chain{len(files) + n_place}"
        n_place += 1
        chain(c.path, placement[c.id])

    # ---- tracks
    order = [*reversed(AUDIO_TRACKS), *VIDEO_TRACKS]          # A3 A2 A1 V1 V2 V3
    track_ids: dict[str, str] = {}
    for n, tname in enumerate(order):
        kind = TRACKS[tname][0]
        pl_main = _sub(mlt, "playlist", id=f"playlist{2 * n}")
        cursor = 0
        for c in manifest.track(tname):
            if c.start_frame > cursor:
                _sub(pl_main, "blank", length=_tc(c.start_frame - cursor, fps))
            entry = _sub(pl_main, "entry", producer=placement[c.id], in_=_tc(c.source_in_frame, fps),
                         out=_tc(c.source_in_frame + c.duration_frames - 1, fps))
            _prop(entry, "kdenlive:id", files[str(c.path)]["bin_id"])
            if c.gain_db:
                flt = _sub(entry, "filter", id=f"filter_gain_{c.id}")
                _prop(flt, "window", "75")
                _prop(flt, "max_gain", "20dB")
                _prop(flt, "level", f"{c.gain_db:g}")
                _prop(flt, "mlt_service", "volume")
                _prop(flt, "kdenlive_id", "volume")
            cursor = c.end_frame
        pl_comp = _sub(mlt, "playlist", id=f"playlist{2 * n + 1}")
        tr = _sub(mlt, "tractor", id=f"tractor{n}", in_=_tc(0, fps), out=_tc(max(total, 1) - 1, fps))
        if kind == "audio":
            _prop(tr, "kdenlive:audio_track", "1")
        _prop(tr, "kdenlive:track_name", TRACK_LABELS[tname])
        _prop(tr, "kdenlive:trackheight", "67")
        _prop(tr, "kdenlive:timeline_active", "1")
        _prop(tr, "kdenlive:collapsed", "0")
        _prop(tr, "kdenlive:thumbs_format")
        _prop(tr, "kdenlive:audio_rec")
        hide = "video" if kind == "audio" else None
        _sub(tr, "track", hide=hide, producer=pl_main.get("id"))
        _sub(tr, "track", hide=hide, producer=pl_comp.get("id"))
        if kind == "audio":
            for svc, props in (("volume", {"window": "75", "max_gain": "20dB", "channel_mask": "-1", "disable": "1"}),
                               ("panner", {"channel": "-1", "start": "0.5", "disable": "1"}),
                               ("audiolevel", {"iec_scale": "0", "dbpeak": "1", "disable": "1"})):
                f = _sub(tr, "filter", id=f"filter_{svc}_{tname}")
                for k, v in props.items():
                    _prop(f, k, v)
                _prop(f, "mlt_service", svc)
                _prop(f, "internal_added", "237")
        track_ids[tname] = tr.get("id")

    master = _sub(mlt, "tractor", id=seq_uuid, in_=_tc(0, fps), out=_tc(max(total, 1) - 1, fps))
    srt = Path(str(target) + ".srt")
    subs_list = json.dumps([{"name": "Subtitles", "id": 0, "file": str(srt)}]) if manifest.captions else None
    for k, v in (("kdenlive:uuid", seq_uuid), ("kdenlive:clipname", manifest.name),
                 ("kdenlive:id", "1"), ("kdenlive:producer_type", "17"),
                 ("kdenlive:control_uuid", _uuid(seq_uuid, "control")), ("kdenlive:folderid", "-1"),
                 ("length", str(max(total, 1))),
                 ("kdenlive:sequenceproperties.hasAudio", "1"), ("kdenlive:sequenceproperties.hasVideo", "1"),
                 ("kdenlive:sequenceproperties.tracksCount", str(len(order))),
                 ("kdenlive:sequenceproperties.documentuuid", seq_uuid),
                 ("kdenlive:duration", _tc(total, fps)),
                 ("kdenlive:sequenceproperties.activeSubtitleIndex", "0"),
                 ("kdenlive:sequenceproperties.subtitlesList", subs_list)):
        if v is not None:
            _prop(master, k, v)
    _sub(master, "track", producer="producer0")
    for tname in order:
        _sub(master, "track", producer=track_ids[tname])
    for pos, tname in enumerate(order, start=1):
        t = _sub(master, "transition", id=f"transition_{tname}")
        _prop(t, "a_track", "0")
        _prop(t, "b_track", str(pos))
        if TRACKS[tname][0] == "audio":
            for k, v in (("mlt_service", "mix"), ("kdenlive_id", "mix"), ("always_active", "1"),
                         ("accepts_blanks", "1"), ("sum", "1")):
                _prop(t, k, v)
        else:
            for k, v in (("compositing", "0"), ("distort", "0"), ("rotate_center", "0"),
                         ("mlt_service", "qtblend"), ("kdenlive_id", "qtblend"), ("always_active", "1")):
                _prop(t, k, v)
    if manifest.captions:
        flt = _sub(master, "filter", id="filter_subtitles")
        _prop(flt, "mlt_service", "avfilter.subtitles")
        _prop(flt, "internal_added", "237")
        _prop(flt, "av.filename", str(srt))
        _prop(flt, "av.alpha", "1")
        _prop(flt, "kdenlive:locked", "0")

    seq_len = max(total, 1)
    main_bin = _sub(mlt, "playlist", id="main_bin")
    profile = custom_profile_path(fps, (w, h)) or target.parent / profile_name(fps, (w, h))
    docprops = {
        "audioChannels": "2", "documentid": str(uuid.uuid5(_NS, seq_uuid).int % 10**13),
        "kdenliveversion": KDENLIVE_VERSION_HINT, "profile": str(profile) if profile else None,
        "version": KDENLIVE_DOC_VERSION, "patchversion": "1", "uuid": seq_uuid, "opensequences": seq_uuid,
        "activetimeline": seq_uuid, "seekOffset": "30000",
    }
    _prop(main_bin, "xml", "was here")
    for k, v in docprops.items():
        if v is not None:
            _prop(main_bin, f"kdenlive:docproperties.{k}", v)
    _prop(main_bin, "xml_retain", "1")
    for key in files:
        _sub(main_bin, "entry", producer=bin_chain[key], in_=_tc(0, fps), out=_tc(files[key]["length"] - 1, fps))
    _sub(main_bin, "entry", producer=seq_uuid, in_=_tc(0, fps), out=_tc(seq_len - 1, fps))

    proj = _sub(mlt, "tractor", id="tractor_project", in_=_tc(0, fps), out=_tc(max(total, 1) - 1, fps))
    _prop(proj, "kdenlive:projectTractor", "1")
    _sub(proj, "track", in_=_tc(0, fps), out=_tc(max(total, 1) - 1, fps), producer=seq_uuid)
    return mlt


def write_kdenlive(manifest: Manifest, out_path: str | os.PathLike | None = None) -> Path:
    out = Path(out_path) if out_path else manifest.root / "project.kdenlive"
    (out.parent / profile_name(manifest.fps, manifest.size)).write_text(profile_text(manifest.fps, manifest.size),
                                                                       encoding="utf-8")
    root = build_kdenlive(manifest, out)
    ET.indent(root, space=" ")
    out.write_text("<?xml version='1.0' encoding='utf-8'?>\n" + ET.tostring(root, encoding="unicode") + "\n",
                   encoding="utf-8")
    if manifest.captions:
        write_srt(manifest, Path(str(out) + ".srt"))
    return out


def structural_check(project: Path) -> list[str]:
    """Reference integrity of a written .kdenlive: every reference resolves to an element defined
    earlier (MLT XML requirement), every media file exists, the last element is the project tractor."""
    problems: list[str] = []
    root = ET.parse(project).getroot()
    defined: set[str] = set()
    for el in root:
        if el.tag in ("producer", "chain", "playlist", "tractor"):
            for ref in el.iter():
                p = ref.get("producer")
                if ref is not el and ref.tag in ("entry", "track") and p not in defined:
                    problems.append(f"{el.tag} {el.get('id')} references {p} before it is defined")
            defined.add(el.get("id"))
        if el.tag == "chain":
            res = next((q.text for q in el.findall("property") if q.get("name") == "resource"), None)
            if not res or not Path(res).is_file():
                problems.append(f"chain {el.get('id')}: media missing: {res}")
    last = root[-1]
    if not (last.tag == "tractor" and any(q.get("name") == "kdenlive:projectTractor" for q in last.findall("property"))):
        problems.append("last element is not the kdenlive:projectTractor wrapper")
    main_bin = root.find("./playlist[@id='main_bin']")
    if main_bin is None or not any(q.get("name") == "xml_retain" for q in main_bin.findall("property")):
        problems.append("main_bin missing or lacks xml_retain")
    return problems


def melt_check(project: Path, *, render_to: Path | None = None, timeout: int = 900) -> dict:
    """Structural check + play the whole project through melt (Kdenlive's engine) to a null consumer.
    With render_to, render it headless to H.264 instead. (melt alone does not report missing media,
    hence the structural check.)"""
    problems = structural_check(project)
    melt = find_melt()
    if not melt:
        return {"ok": None if not problems else False, "structure": problems,
                "reason": "melt not found (install Kdenlive or set CVES_MELT)"}
    if render_to is None:
        cmd = [melt, "-quiet", str(project), "-consumer", "null", "real_time=-1", "terminate_on_pause=1"]
    else:
        cmd = [melt, "-quiet", str(project), "-consumer", f"avformat:{render_to}", "vcodec=libx264", "crf=20",
               "preset=veryfast", "acodec=aac", "ab=192k", "pix_fmt=yuv420p", "real_time=-1"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    noise = ("QPainter",)
    err = "\n".join(ln for ln in r.stderr.splitlines() if not ln.startswith(noise))[-2000:]
    ok = r.returncode == 0 and not problems
    out = {"ok": ok, "returncode": r.returncode, "structure": problems, "stderr": err}
    if render_to is not None:
        ok = ok and render_to.is_file() and render_to.stat().st_size > 0
        out.update(ok=ok, output=str(render_to), probe=probe(render_to) if ok else {})
    return out


def kdenlive_gui_check(project: Path, render_to: Path, timeout: int = 300) -> dict:
    """Open the project with Kdenlive's own document loader (``kdenlive --render``) and report what its
    DocumentChecker / profile / sequence loader said. Needs the Kdenlive app (opens a window briefly)."""
    exe = next((c for c in (os.environ.get("CVES_KDENLIVE"), shutil.which("kdenlive"),
                            "/Applications/kdenlive.app/Contents/MacOS/kdenlive",
                            r"C:\Program Files\kdenlive\bin\kdenlive.exe") if c and Path(c).is_file()), None)
    if not exe:
        return {"ok": None, "reason": "kdenlive app not found"}
    # Kdenlive 26.08's command-line render segfaults on any project that has a subtitle track (also with
    # subtitle files Kdenlive wrote itself), so the loader check runs on a copy without it. The subtitle
    # track is checked by opening the project in the app (docs/CONTROL-MODE.md, "Tested").
    root = ET.parse(project).getroot()
    for tr in root.iter("tractor"):
        for f in [f for f in tr.findall("filter")
                  if any(p.get("name") == "mlt_service" and p.text == "avfilter.subtitles" for p in f)]:
            tr.remove(f)
        for p in [p for p in tr.findall("property") if p.get("name", "").endswith(("subtitlesList", "activeSubtitleIndex"))]:
            tr.remove(p)
    probe_copy = project.with_name(project.stem + ".loadercheck.kdenlive")
    ET.ElementTree(root).write(probe_copy, encoding="utf-8", xml_declaration=True)
    try:
        r = subprocess.run([exe, "--render", str(probe_copy), str(render_to)], capture_output=True, text=True,
                           timeout=timeout)
        log = r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        log = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    probe_copy.unlink(missing_ok=True)
    flags = [ln.strip() for ln in log.splitlines()
             if any(k in ln for k in ("DocumentChecker found", "Type: ", "non standard", "Recovering corrupted",
                                      "COULD NOT FIND", "INVALID SUBTITLE"))]
    rendered = render_to.is_file() and render_to.stat().st_size > 0
    return {"ok": rendered and not flags, "rendered": rendered, "flags": flags,
            "probe": probe(render_to) if rendered else {}}


def export(control_dir: str | os.PathLike, *, validate: bool = True) -> dict:
    manifest = load_manifest(control_dir)
    out = write_kdenlive(manifest)
    result: dict = {"kdenlive": out, "srt": write_srt(manifest),
                    "profile": str(custom_profile_path(manifest.fps, manifest.size)
                                   or f"{out.parent / profile_name(manifest.fps, manifest.size)} (not installed in "
                                      f"Kdenlive: add --install-profile)")}
    if validate:
        result["melt"] = melt_check(out)
        if result["melt"]["ok"] is False:
            raise RuntimeError(f"melt could not load {out}:\n{result['melt']['stderr']}")
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="cves export kdenlive")
    ap.add_argument("control_dir", nargs="?", default="Export/control")
    ap.add_argument("--render", help="also render headless with melt to this .mp4 (proof it plays)")
    ap.add_argument("--install-profile", action="store_true",
                    help="copy the project's rate/size profile into Kdenlive's custom profile folder")
    a = ap.parse_args(argv)
    if a.install_profile:
        m = load_manifest(a.control_dir)
        print(f"profile: {install_profile(m.fps, m.size)}")
    res = export(a.control_dir)
    if a.render:
        res["render"] = melt_check(Path(res["kdenlive"]), render_to=Path(a.render))
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
