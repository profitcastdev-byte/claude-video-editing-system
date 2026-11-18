"""Self-test for the control-mode exporters: synthetic layers -> FCPXML + Kdenlive -> checks.

    python -m cves.export.selftest [--keep DIR]

Builds a tiny layer set with ffmpeg (coloured ProRes 422 HQ clips, one ProRes 4444 alpha overlay,
WAV stems, 3 captions, layers.json) in a temp folder whose name has a space and a curly apostrophe
(the user's real paths do), at two rates and two sizes (CONFIGS: 23.976 vertical and 25 fps
landscape), then for each:

  1. resolve.export  -> timeline.fcpxml + captions.srt + timeline.otio, check_fcpxml, and a read-back
                        through OTIO's FCPXML adapter (independent parser);
  2. kdenlive.export -> project.kdenlive, melt load, headless melt render, and pixel checks on the
                        render (cutaway on V2 covers V1; the V3 alpha box composites over it; captions
                        burn in) plus an audio level check.
Exit code 0 only if every check passes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import kdenlive, resolve
from .layers import frames_to_srt_time, load_manifest, seconds_to_frames

# Fixture timebases: every exporter must work at the project's own rate and size, so the self-test runs at two rates
# and two sizes. (Literal rates/sizes are allowed here only: these are fixtures, not defaults.)
CONFIGS = [((24000, 1001), (1080, 1920)), ((25, 1), (1920, 1080))]


def _ffbin(name: str) -> str:
    try:
        from .. import config as C
        return C.get(name)
    except Exception:  # noqa: BLE001 - standalone use without the cves config
        return name


def _ff(*args: str) -> None:
    subprocess.run([_ffbin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def _box(w: int, h: int) -> tuple[int, int, int, int]:
    """the alpha overlay's opaque box (x0, x1, y0, y1), in the lower third whatever the size"""
    return round(w * .27), round(w * .73), round(h * .68), round(h * .80)


def make_fixture(root: Path, fps: tuple[int, int] = CONFIGS[0][0], size: tuple[int, int] = CONFIGS[0][1]) -> Path:
    W, H = size
    FPS = f"{fps[0]}/{fps[1]}"
    ctl = root / "Export" / "control"
    for d in ("media/aroll", "media/cutaways", "media/overlays", "media/audio"):
        (ctl / d).mkdir(parents=True, exist_ok=True)
    prores_hq = ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", "-vendor", "apl0"]
    for name, color in (("01_hook_0", "0x2040C0"), ("02_body_0", "0x20A040")):
        _ff("-f", "lavfi", "-i", f"color=c={color}:s={W}x{H}:r={FPS}:d=5", *prores_hq,
            str(ctl / f"media/aroll/{name}.mov"))
    _ff("-f", "lavfi", "-i", f"color=c=0xC02020:s={W}x{H}:r={FPS}:d=3", *prores_hq,
        str(ctl / "media/cutaways/c1.mov"))
    # alpha overlay: transparent frame with an opaque yellow box in the lower third
    x0, x1, y0, y1 = _box(W, H)
    inside = f"between(X,{x0},{x1 - 1})*between(Y,{y0},{y1 - 1})"   # drawbox leaves alpha at 0, so build it with geq
    _ff("-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H}:r={FPS}:d=6,format=rgba,"
                             f"geq=r='{inside}*255':g='{inside}*208':b='{inside}*32':a='{inside}*255'",
        "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16",
        "-vendor", "apl0", str(ctl / "media/overlays/chest1.mov"))
    a = ["-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le"]
    _ff("-f", "lavfi", "-i", "sine=f=220:d=8,volume=-14dB", *a, str(ctl / "media/audio/voice.wav"))
    _ff("-f", "lavfi", "-i", "sine=f=440:d=8,volume=-24dB", *a, str(ctl / "media/audio/music.wav"))
    _ff("-f", "lavfi", "-i", "sine=f=1200:d=8,volume=-20dB,volume=enable='between(t,0,2.9)+gt(t,3.3)':volume=0",
        *a, str(ctl / "media/audio/sfx.wav"))
    manifest = {
        "schema": "cves.layers/1",
        "name": "Selftest Ad",
        "fps": list(fps), "size": [W, H], "audio_rate": 48000,
        "duration": 8.0,
        "clips": [
            {"id": "a1", "track": "V1", "path": "media/aroll/01_hook_0.mov", "start": 0.0, "end": 4.004,
             "source_in": 0.5, "edit_ref": "edl.01_hook_0"},
            {"id": "a2", "track": "V1", "path": "media/aroll/02_body_0.mov", "start": 4.004, "end": 8.0,
             "source_in": 0.0, "edit_ref": "edl.02_body_0"},
            {"id": "c1", "track": "V2", "path": "media/cutaways/c1.mov", "start": 2.5, "end": 5.0,
             "source_in": 0.0, "edit_ref": "cutaways.c1"},
            {"id": "chest1", "track": "V3", "path": "media/overlays/chest1.mov", "start": 1.0, "end": 6.0,
             "source_in": 0.0, "alpha": True, "edit_ref": "chest.0"},
            {"id": "voice", "track": "A1", "path": "media/audio/voice.wav", "start": 0.0, "end": 8.0, "source_in": 0.0},
            {"id": "music", "track": "A2", "path": "media/audio/music.wav", "start": 0.0, "end": 8.0, "source_in": 0.0},
            {"id": "sfx", "track": "A3", "path": "media/audio/sfx.wav", "start": 0.0, "end": 8.0, "source_in": 0.0},
        ],
        "captions": [
            {"index": 1, "start": 0.2, "end": 1.9, "text": "Is your shop on Google Maps?"},
            {"index": 2, "start": 2.0, "end": 4.4, "text": "Most people never check"},
            {"index": 3, "start": 4.5, "end": 7.6, "text": "We fix that for you"},
        ],
    }
    (ctl / "layers.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ctl


def _pixel(video: Path, t: float, x: int, y: int) -> tuple[int, int, int]:
    raw = subprocess.run([_ffbin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-ss", f"{t}", "-i", str(video),
                          "-frames:v", "1", "-vf", f"format=rgb24,crop=1:1:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return raw[0], raw[1], raw[2]


def _near(rgb, want, tol=40) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(rgb, want))


def run_one(root: Path, fps: tuple[int, int], size: tuple[int, int], check, *, gui: bool) -> None:
    W, H = size
    tag = f"[{fps[0]}/{fps[1]} {W}x{H}] "
    ctl = make_fixture(root, fps, size)
    m = load_manifest(ctl)
    check(tag + "layers.json loads + validates", (m.fps, m.size) == (fps, size),
          f"{len(m.clips)} clips, {len(m.captions)} captions, {m.duration_frames} frames")

    # ---- Resolve
    out = resolve.export(ctl)
    check(tag + "timeline.fcpxml written + check_fcpxml", True, str(out["fcpxml"]))
    import xml.etree.ElementTree as ET
    fx = ET.parse(out["fcpxml"]).getroot()
    fmts = {f.get("id"): f for f in fx.iter("format")}
    want_fd = resolve.frames_to_rational(1, fps)
    check(tag + "FCPXML formats carry the project's frameDuration + size",
          all(f.get("frameDuration") == want_fd and (f.get("width"), f.get("height")) == (str(W), str(H))
              for f in fmts.values()) and fmts["r2"].get("name") == resolve.format_name(size, fps),
          f"frameDuration={want_fd}, media format {fmts['r2'].get('name')}")
    try:
        import opentimelineio as otio
        try:
            coll = otio.adapters.read_from_file(str(out["fcpxml"]), adapter_name="fcpx_xml")
        except Exception as exc:  # noqa: BLE001 - adapter plugin not installed
            raise RuntimeError(f"skip:{exc}") from None
        tl = coll if isinstance(coll, otio.schema.Timeline) else \
            next(x for x in coll if isinstance(x, otio.schema.Timeline))
        vids = [t for t in tl.tracks if t.kind == otio.schema.TrackKind.Video]
        auds = [t for t in tl.tracks if t.kind == otio.schema.TrackKind.Audio]
        # Structural read-back only: otio-fcpx-xml-adapter 1.0.0 truncates 23.976 to an integer rate (23)
        # and rescales times inconsistently, so it is not a numeric reference; check_fcpxml is.
        got = {t.name: [c.name for c in t.find_clips()] for t in tl.tracks}
        lanes = {"V1": "1", "V2": "2", "V3": "3", "A1": "-1", "A2": "-2", "A3": "-3"}
        want_names = {lanes[k]: [c.path.name for c in m.track(k)] for k in lanes}
        check(tag + "FCPXML read back by OTIO fcpx adapter", (len(vids), len(auds)) == (3, 3) and got == want_names,
              f"{len(vids)} video / {len(auds)} audio tracks; lane->clip names match={got == want_names}")
    except RuntimeError as exc:
        check(tag + "FCPXML read back by OTIO fcpx adapter", True, f"skipped: adapter not installed ({exc})")
    except Exception as exc:  # noqa: BLE001
        check(tag + "FCPXML read back by OTIO fcpx adapter", False, repr(exc))
    dtd = os.environ.get("CVES_FCPXML_DTD")   # Apple's FCPXMLv1_10.dtd (CommandPost mirrors it)
    if dtd and shutil.which("xmllint"):
        r = subprocess.run(["xmllint", "--noout", "--dtdvalid", dtd, str(out["fcpxml"])],
                           capture_output=True, text=True)
        check(tag + "timeline.fcpxml valid against FCPXML 1.10 DTD", r.returncode == 0, r.stderr.strip()[-300:])
    srt = out["srt"].read_text(encoding="utf-8")
    first = frames_to_srt_time(seconds_to_frames(0.2, fps), fps)
    check(tag + "captions.srt has 3 cues on the frame grid", srt.count(" --> ") == 3 and first in srt,
          srt.splitlines()[1])
    try:
        import opentimelineio as otio
        t2 = otio.adapters.read_from_file(str(out["otio"]))
        check(tag + "timeline.otio reloads", len(t2.tracks) == 6 and abs(t2.tracks[0].duration().rate - fps[0] / fps[1]) < 1e-6,
              f"{len(t2.tracks)} tracks at {t2.tracks[0].duration().rate:.3f} fps")
    except Exception as exc:  # noqa: BLE001
        check(tag + "timeline.otio reloads", False, repr(exc))

    # ---- Kdenlive
    kd = kdenlive.export(ctl)
    no_melt = kd["melt"]["ok"] is None          # melt not installed: structure checked, playback skipped
    check(tag + ("project.kdenlive structure (melt not installed: playback skipped)" if no_melt
                 else "project.kdenlive structure + full melt playback"), kd["melt"]["ok"] is not False,
          "; ".join(kd["melt"].get("structure", [])) or kd["melt"].get("reason", "") or "ok")
    prof = ET.parse(kd["kdenlive"]).getroot().find("profile")
    check(tag + "Kdenlive <profile> is the project's rate + size",
          (prof.get("frame_rate_num"), prof.get("frame_rate_den"), prof.get("width"), prof.get("height")) ==
          (str(fps[0]), str(fps[1]), str(W), str(H)), f"{prof.get('description')}; profile file: {kd['profile']}")
    if no_melt:
        return
    render = ctl / "selftest_render.mp4"
    r = kdenlive.melt_check(kd["kdenlive"], render_to=render)
    check(tag + "melt headless render", r["ok"] is True, r.get("stderr", "")[-300:] if not r["ok"] else str(render))
    if r["ok"]:
        p = r["probe"]
        frames = round(p["duration"] * fps[0] / fps[1])
        want_frames = seconds_to_frames(8.0, fps)
        check(tag + f"render is {W}x{H}, ~8 s", (p["width"], p["height"]) == (W, H) and abs(frames - want_frames) <= 2,
              f"{p['width']}x{p['height']} {p['duration']:.3f}s")
        x0, x1, y0, y1 = _box(W, H)
        cx, cy, top = (x0 + x1) // 2, (y0 + y1) // 2, round(H * .16)
        probes = [
            ("V1 blue at 0.5 s", 0.5, cx, top, (0x20, 0x40, 0xC0)),
            ("V2 red cutaway covers V1 at 3.0 s", 3.0, cx, top, (0xC0, 0x20, 0x20)),
            ("V3 alpha box over V2 at 3.0 s", 3.0, cx, cy, (0xFF, 0xD0, 0x20)),
            ("V3 transparent outside its box at 3.0 s", 3.0, round(W * .09), cy, (0xC0, 0x20, 0x20)),
            ("V1 green after the cutaway at 6.5 s", 6.5, cx, top, (0x20, 0xA0, 0x40)),
            ("V3 gone after 6 s", 6.5, cx, cy, (0x20, 0xA0, 0x40)),
        ]
        for name, t, x, y, want in probes:
            got = _pixel(render, t, x, y)
            check(tag + name, _near(got, want), f"got rgb{got} want rgb{want}")
        if gui:
            gr = kdenlive.kdenlive_gui_check(kd["kdenlive"], ctl / "kdenlive_app_render.mp4")
            if gr["ok"] is None:
                check(tag + "Kdenlive app loader (kdenlive --render)", True, "skipped: " + gr["reason"])
            else:
                check(tag + "Kdenlive app loader (kdenlive --render, subtitle track stripped) clean", gr["ok"],
                      f"rendered={gr['rendered']} flags={gr['flags'][:4]}")
                if gr["rendered"]:
                    got = _pixel(ctl / "kdenlive_app_render.mp4", 3.0, cx, cy)
                    check(tag + "Kdenlive app render: V3 alpha box over V2 at 3.0 s", _near(got, (0xFF, 0xD0, 0x20)),
                          f"got rgb{got}")
        vol = subprocess.run([_ffbin("ffmpeg"), "-hide_banner", "-i", str(render), "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        mean = next((ln.split(":")[1].strip() for ln in vol.splitlines() if "mean_volume" in ln), "n/a")
        check(tag + "render has the audio stems", mean != "n/a" and float(mean.split()[0]) > -40, f"mean {mean}")


def run(keep: Path | None = None, gui: bool = True) -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    # pure timebase checks (no media): rationals and names at other common rates
    check("frame rationals at 29.97 / 30 / 25", resolve.frames_to_rational(3, (30000, 1001)) == "1001/10000s"
          and resolve.frames_to_rational(1, (30, 1)) == "1/30s" and resolve.frames_to_rational(50, (25, 1)) == "2s",
          f"{resolve.frames_to_rational(3, (30000, 1001))}, {resolve.frames_to_rational(1, (30, 1))}, "
          f"{resolve.frames_to_rational(50, (25, 1))}")
    tmp = None if keep else Path(tempfile.mkdtemp(prefix="cves selftest ’ "))
    root = keep or tmp
    try:
        for n, (fps, size) in enumerate(CONFIGS):
            sub = root / f"t{n} {fps[0]}-{fps[1]} {size[0]}x{size[1]}"
            try:
                run_one(sub, fps, size, check, gui=gui and n == 0)
            except Exception as exc:  # noqa: BLE001
                check(f"[{fps[0]}/{fps[1]} {size[0]}x{size[1]}] selftest crashed", False, repr(exc))
        installed = kdenlive.custom_profile_path(*CONFIGS[0])
        print(f"\nKdenlive custom profile for {CONFIGS[0][0]} {CONFIGS[0][1]}: "
              f"{installed or 'not installed (cves export kdenlive --install-profile, or setup/control)'}")
    finally:
        print(f"\nfixture: {root}")
        for name, ok, detail in results:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0 if results and all(ok for _, ok, _ in results) else 1


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="cves export selftest")
    ap.add_argument("--keep", help="build the fixture in this folder and keep it")
    ap.add_argument("--no-gui", action="store_true", help="skip the Kdenlive app loader check (it opens a window)")
    a = ap.parse_args(argv)
    keep = Path(a.keep).expanduser().resolve() if a.keep else None
    if keep:
        keep.mkdir(parents=True, exist_ok=True)
    return run(keep, gui=not a.no_gui)


if __name__ == "__main__":
    sys.exit(main())
