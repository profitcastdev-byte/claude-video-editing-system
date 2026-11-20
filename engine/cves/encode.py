"""Single final encode from lossless frames + master mix. Every encoder setting comes from the style `delivery:` section
(default: H.264 High, crf 16, preset slow, no tune=film, BT.709 matrix AND tags, AAC 48 kHz, faststart). Frame rate and size
come from Edit/timeline.json (written by render), falling back to edl.json, then to the style. Nothing is hard-coded here.
`video_args()` / `audio_args()` / `stream_params()` are shared with `cves deliver` (reframes, re-muxes) so every file
delivered is encoded the same way."""
import os, subprocess
from fractions import Fraction
from . import config as C, style as STY


def stream_params(pr):
    """(fps_rational "num/den", (w, h)) of the master, from timeline.json > edl.json > style. Raises SystemExit if unknown."""
    tl = pr.json("timeline.json", {}) or {}; edl = pr.json("edl.json", {}) or {}
    fr = tl.get("fps_rational") or edl.get("fps_rational")
    if not fr:
        fps = tl.get("fps") or edl.get("fps")
        if not fps: raise SystemExit("no frame rate in Edit/timeline.json or Edit/edl.json: run `cves select` and `cves render` first")
        q = Fraction(fps).limit_denominator(1001); fr = [q.numerator, q.denominator]
    size = tl.get("size")
    if not size:
        first = pr.e("frames", "00000.png")
        if os.path.exists(first):
            import cv2
            im = cv2.imread(first, cv2.IMREAD_UNCHANGED); size = [im.shape[1], im.shape[0]]
        else:
            from . import gfx as G
            size = G.canvas_of(STY.load(pr), pr)
    return f"{int(fr[0])}/{int(fr[1])}", (int(size[0]), int(size[1]))


def video_args(S):
    """ffmpeg output args for the video stream, from style `delivery.video` + `delivery.color` (input is full-range RGB)."""
    D = S.get("delivery") or {}; V = D.get("video") or {}
    color = D.get("color", "bt709"); codec = V.get("codec", "libx264")
    vf = f"scale=out_color_matrix={color}:out_range=tv:flags=accurate_rnd+full_chroma_int,format={V.get('pix_fmt', 'yuv420p')}"
    a = ["-vf", vf, "-c:v", codec, "-preset", str(V.get("preset", "slow")), "-crf", str(V.get("crf", 16)), "-profile:v", str(V.get("profile", "high"))]
    if V.get("tune"): a += ["-tune", str(V["tune"])]
    if codec == "libx264":
        xp = f"colorprim={color}:transfer={color}:colormatrix={color}:range=tv"
        if V.get("x264_params"): xp += ":" + str(V["x264_params"])
        a += ["-x264-params", xp]
    a += ["-color_primaries", color, "-color_trc", color, "-colorspace", color, "-color_range", "tv"]
    if D.get("faststart", True): a += ["-movflags", "+faststart"]
    return a


def proxy_video_args(S):
    """ffmpeg args for a proxy (treatment previews, docs/TREATMENTS.md): the delivery colour tags, but a fast x264 preset
    and a lighter crf from style `treatments.proxy_preset` / `proxy_crf`. Never used for a delivered file."""
    D = S.get("delivery") or {}; color = D.get("color", "bt709")
    vf = f"scale=out_color_matrix={color}:out_range=tv,format=yuv420p"
    return ["-vf", vf, "-c:v", "libx264", "-preset", str(S.get("treatments.proxy_preset", "veryfast")), "-crf", str(S.get("treatments.proxy_crf", 26)),
            "-x264-params", f"colorprim={color}:transfer={color}:colormatrix={color}:range=tv",
            "-color_primaries", color, "-color_trc", color, "-colorspace", color, "-color_range", "tv", "-movflags", "+faststart"]


def audio_args(S):
    A = (S.get("delivery") or {}).get("audio") or {}
    return ["-c:a", str(A.get("codec", "aac")), "-ar", str(A.get("sample_rate", 48000)), "-b:a", str(A.get("bitrate", "256k"))]


DRAFT_TAG = "cves-draft"          # container comment of a `cves build --draft` master: delivery refuses it


def encode(pr, out=None, frames="frames", audio=None, proxy=False, draft=False):
    """proxy=True: fast preview video settings (proxy_video_args); the full-quality path is unchanged.
    draft=True: proxy settings + the container tagged `comment=cves-draft` (deliver.is_draft refuses it)"""
    proxy = proxy or draft
    S = STY.load(pr); fr, (w, h) = stream_params(pr)
    title = (pr.edit.get("project", {}) or {}).get("title", "edit").replace(" ", "_")
    out = out or pr.p("Export", f"{title}.mp4"); os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    src = pr.e(frames, "%05d.png")
    if not os.path.exists(pr.e(frames, "00000.png")): raise SystemExit(f"no frames in {pr.e(frames)}: run `cves render` first")
    mixf = audio or pr.e("mix.wav")
    if not os.path.exists(mixf): raise SystemExit(f"no {mixf}: run `cves mix` first")
    import cv2
    im = cv2.imread(pr.e(frames, "00000.png"), cv2.IMREAD_UNCHANGED)
    if (im.shape[1], im.shape[0]) != (w, h):
        raise SystemExit(f"frames are {im.shape[1]}x{im.shape[0]} but timeline.json says {w}x{h}: re-run `cves render`")
    subprocess.run([C.get("ffmpeg"), "-v", "error", "-y", "-framerate", fr, "-i", src, "-i", mixf,
                    "-map", "0:v", "-map", "1:a"] + (proxy_video_args(S) if proxy else video_args(S))
                   + audio_args(S) + (["-metadata", f"comment={DRAFT_TAG}"] if draft else []) + ["-shortest", out], check=True)
    return out
