"""`cves deliver`: the only way a file leaves the project (docs/DELIVERY.md).

Writes a new, never-overwritten Export/vNNN/ folder: the QC'd master, SRT + WebVTT + plain transcript, a cover JPG,
qc.json + QC-REPORT.txt, edit.yaml + the merged style snapshot, every variant that passed its own QC, and manifest.json
(files, sha256, durations, sizes, fps, cves version, variant definitions and results).

Refuses unless Edit/qc.json exists, has fail == 0 and its sha256 equals the master's: re-encoding without re-running QC
blocks. `--force-unchecked` delivers anyway and writes a loud warning into the manifest."""
import os, re, sys, json, shutil, tempfile, datetime, subprocess
import numpy as np
from fractions import Fraction
from . import config as C, style as STY, __version__
from .qc import sha256

FORCE_WARNING = ("UNCHECKED DELIVERY: --force-unchecked was used. This master did NOT pass `cves qc` (or the QC stamp does not "
                 "match it). Objective faults may reach the viewer. Do not publish before a human has reviewed it.")


# ------------------------------------------------------------------ the QC stamp
def master_path(pr, video=None):
    if video: return os.path.abspath(video)
    st = pr.json("qc.json")
    if st and os.path.exists(st.get("video", "")) and os.path.dirname(os.path.abspath(st["video"])) == os.path.abspath(pr.p("Export")):
        return st["video"]
    ex = pr.p("Export")
    vids = sorted([os.path.join(ex, f) for f in os.listdir(ex) if f.endswith(".mp4")], key=os.path.getmtime) if os.path.isdir(ex) else []
    if not vids: raise SystemExit("no Export/*.mp4 master: run `cves encode` (or `cves build`) first, or pass --video")
    return vids[-1]

def check_stamp(pr, master):
    """-> (stamp or None, master sha256, [problems]). No problems = deliverable."""
    st = pr.json("qc.json"); sha = sha256(master); probs = []
    if st is None: probs.append("Edit/qc.json missing: run `cves qc`")
    else:
        if st.get("fail", 1) != 0: probs.append(f"QC has {st.get('fail')} FAIL (Edit/QC-REPORT.txt): fix them and re-run `cves qc`")
        if st.get("sha256") != sha: probs.append(f"Edit/qc.json judged a different file (sha {str(st.get('sha256'))[:12]}..., master {sha[:12]}...): "
                                                 "the master changed since QC (re-encoded?); re-run `cves qc`")
    return st, sha, probs


# ------------------------------------------------------------------ captions
def _ts(t, sep): t = max(0.0, t); h, r = divmod(int(round(t * 1000)), 3600000); m, r = divmod(r, 60000); s, ms = divmod(r, 1000); return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

def caption_events(pr):
    """cut-time caption phrases from the renderer's own caption builder: [(start, end, text)]"""
    from .render import Timeline
    TL = Timeline(pr); T = TL.N / TL.FPS; out = []
    for a, b, words in TL.caps:
        a, b = max(0.0, a), min(T, b); txt = " ".join(w for w, _ in words).strip()
        if b - a > .05 and txt: out.append((a, b, txt))
    for k in range(len(out) - 1):     # no overlaps
        if out[k][1] > out[k + 1][0]: out[k] = (out[k][0], out[k + 1][0], out[k][2])
    return out

def write_captions(ev, base):
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for k, (a, b, t) in enumerate(ev, 1): f.write(f"{k}\n{_ts(a, ',')} --> {_ts(b, ',')}\n{t}\n\n")
    with open(base + ".vtt", "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for k, (a, b, t) in enumerate(ev, 1): f.write(f"{k}\n{_ts(a, '.')} --> {_ts(b, '.')}\n{t}\n\n")
    para, lines = [], []
    for _, _, t in ev:
        para.append(t)
        if t.endswith((".", "?", "!")): lines.append(" ".join(para)); para = []
    if para: lines.append(" ".join(para))
    with open(base + ".transcript.txt", "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    return [base + ".srt", base + ".vtt", base + ".transcript.txt"]


# ------------------------------------------------------------------ cover
def _decode_window(master, fr, size, t0, t1):
    W, H = size
    p = subprocess.run([C.get("ffmpeg"), "-v", "error", "-ss", f"{t0:.3f}", "-i", master, "-t", f"{max(t1 - t0, 1 / float(Fraction(fr))):.3f}",
                        "-vf", "scale=in_color_matrix=bt709:in_range=tv:flags=accurate_rnd+full_chroma_int,format=bgr24",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"], capture_output=True)
    b = np.frombuffer(p.stdout, np.uint8); n = len(b) // (W * H * 3)
    return [b[i * W * H * 3:(i + 1) * W * H * 3].reshape(H, W, 3) for i in range(n)]

def pick_cover(pr, S, master):
    """-> (BGR frame, t, how). edit.yaml delivery.cover_t wins; else the best face x sharpness frame in the first window_s."""
    import cv2
    from .encode import stream_params
    fr, size = stream_params(pr); fps = float(Fraction(fr)); D = pr.edit.get("delivery") or {}
    if D.get("cover_t") is not None:
        t = float(D["cover_t"]); fs = _decode_window(master, fr, size, t, t + 1 / fps)
        if not fs: raise SystemExit(f"delivery.cover_t {t} is past the end of the master")
        return fs[0], t, "edit.yaml delivery.cover_t", _face_y(fs[0], size)
    win = float(S.get("delivery.cover.window_s", 3.0)); fs = _decode_window(master, fr, size, 0, win)
    tl = pr.json("timeline.json", {}) or {}; cuts = tl.get("cutaways", [])
    det = cv2.FaceDetectorYN.create(C.get("yunet"), "", (size[0] // 4, size[1] // 4), .7, .3, 5000); best = None
    for i, f in enumerate(fs):
        t = i / fps; g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
        _, d = det.detect(cv2.resize(f, (size[0] // 4, size[1] // 4), interpolation=cv2.INTER_AREA)); fs_ = 0.0
        if d is not None and len(d):
            x, y, w, h = (int(v * 4) for v in d[0][:4]); conf = float(d[0][14])
            roi = g[max(0, y):y + h, max(0, x):x + w]; fsharp = float(cv2.Laplacian(roi, cv2.CV_64F).var()) if roi.size else 0
            fs_ = conf * (1 + min(1.0, w / size[0] * 3)) * np.log1p(fsharp)
        score = fs_ * 10 + np.log1p(sharp) - (5 if any(c["start"] <= t < c["end"] for c in cuts) else 0)
        if best is None or score > best[0]: best = (score, i, fs_ > 0, (y - int(.35 * h), y + h) if fs_ > 0 else None)
    if best is None: raise SystemExit("could not decode the master's first seconds for the cover")
    return fs[best[1]], best[1] / fps, f"best {'face + ' if best[2] else ''}sharpness frame in the first {win:g} s", best[3]

def _face_y(img, size):
    import cv2
    det = cv2.FaceDetectorYN.create(C.get("yunet"), "", (size[0] // 4, size[1] // 4), .7, .3, 5000)
    _, d = det.detect(cv2.resize(img, (size[0] // 4, size[1] // 4), interpolation=cv2.INTER_AREA))
    return (int((d[0][1] - .35 * d[0][3]) * 4), int((d[0][1] + d[0][3]) * 4)) if d is not None and len(d) else None

def draw_cover(pr, S, img, title, out, avoid=()):
    """optional title overlay from edit.yaml delivery.cover_title, in the style's fonts and colours; *word* = accent."""
    import cv2
    from PIL import Image, ImageDraw, ImageFilter
    from . import gfx as G
    G.apply_style(S); CV = S.get("delivery.cover") or {}
    im = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert("RGBA")
    if title:
        W, H = im.size; k = min(W, H) / 1080            # px keys are at a 1080 short side, on any canvas (docs/FORMATS.md)
        short = {"medium": "m", "semibold": "sb", "bold": "b", "extrabold": "xb", "serif": "serif"}.get(CV.get("title_font", "extrabold"), "xb")
        f = G.font(short, int(CV.get("title_size", 104) * k))
        col = lambda v: STY.rgb((S.get("colors") or {}).get(v, v))
        text_c, acc_c = col(CV.get("title_color", "text")), col(CV.get("title_accent", "accent"))
        words = str(title).split(); lines, cur = [], []
        for w in words:
            if cur and len(" ".join(x.strip("*") for x in cur + [w])) > CV.get("title_max_chars", 16): lines.append(cur); cur = []
            cur.append(w)
        if cur: lines.append(cur)
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); y = int(CV.get("title_y", .16) * H); lh = int(f.size * 1.12)
        sz = G.safe_zone(S, (W, H)); x0z, x1z = (sz[0], sz[2]) if sz else (0, W)
        top = sz[1] if sz else S.get("platform.margin", 60) * k; bh = lh * len(lines); gap = 24 * k
        av = sorted(a for a in avoid if a)       # never over the face or burned-in text: preferred y, else above / below each
        hit = lambda y_: any(y_ < b + gap and y_ + bh > a - gap for a, b in av)
        cands = [y] + [int(a - gap - bh) for a, _ in av] + [int(b + gap) for _, b in av]
        y = next((c for c in cands if c >= top * .5 and c + bh <= H - top * .25 and not hit(c)), y)
        for ln in lines:
            parts = [(w.strip("*"), acc_c if w.startswith("*") and w.endswith("*") else text_c) for w in ln]
            tw = sum(f.getlength(p + " ") for p, _ in parts) - f.getlength(" "); x = (x0z + x1z) / 2 - tw / 2
            for p, c in parts: d.text((x, y + f.getmetrics()[0]), p, font=f, fill=c + (255,), anchor="ls"); x += f.getlength(p + " ")
            y += lh
        if CV.get("title_shadow", True):
            a = lay.split()[3].filter(ImageFilter.GaussianBlur(max(2, int(10 * k))))
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: int(v * .75))); im = Image.alpha_composite(im, sh)
        im = Image.alpha_composite(im, lay)
    im.convert("RGB").save(out, "JPEG", quality=int(CV.get("quality", 92)))
    return out


# ------------------------------------------------------------------ manifest helpers
def file_info(path, root):
    info = {"path": os.path.relpath(path, root).replace(os.sep, "/"), "bytes": os.path.getsize(path), "sha256": sha256(path)}
    if path.endswith((".mp4", ".mov", ".m4a", ".wav")):
        from .variants import probe
        p = probe(path); v = next((s for s in p.get("streams", []) if s["codec_type"] == "video"), None)
        info["duration"] = round(float(p.get("format", {}).get("duration", 0)), 3)
        if v: info.update(width=v["width"], height=v["height"], fps=v.get("r_frame_rate"), frames=int(v.get("nb_frames") or 0))
    elif path.endswith(".jpg"):
        from PIL import Image
        with Image.open(path) as im: info.update(width=im.width, height=im.height)
    return info

def next_version(export):
    os.makedirs(export, exist_ok=True)
    ns = [int(m.group(1)) for d in os.listdir(export) for m in [re.fullmatch(r"v(\d{3,})", d)] if m]
    return max(ns, default=0) + 1

def _jsonable(o):
    if isinstance(o, dict): return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_jsonable(x) for x in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    return o


# ------------------------------------------------------------------ deliver
def deliver(pr, variants=None, only=None, force_unchecked=False, video=None, keep_temp=False):
    import yaml
    from . import variants as VAR
    from .qc import write_stamp
    from .encode import stream_params
    S = STY.load(pr); E = pr.edit
    master = master_path(pr, video)
    stamp, msha, probs = check_stamp(pr, master)
    if probs and not force_unchecked:
        raise SystemExit("delivery refused: " + " | ".join(probs) + "   (override only with --force-unchecked, which is written into the manifest)")
    if probs: print("\n" + "!" * 100 + f"\n{FORCE_WARNING}\nreasons: " + " | ".join(probs) + "\n" + "!" * 100 + "\n", file=sys.stderr)
    if only and only != "master": raise SystemExit("--only takes `master` (deliver the master without variants)")
    specs = [] if only == "master" else VAR.plan(pr, None if variants is None else [v for v in variants.split(",")])
    title = (E.get("project", {}) or {}).get("title", "edit").replace(" ", "_")
    export = pr.p("Export"); n = next_version(export)
    stage = tempfile.mkdtemp(prefix=".staging-", dir=export); work = tempfile.mkdtemp(prefix="cves_variants_")
    created = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    try:
        mfile = os.path.join(stage, os.path.basename(master)); shutil.copy2(master, mfile)
        if sha256(mfile) != msha: raise SystemExit("copy of the master does not match its sha256: disk problem? nothing delivered")
        if os.path.exists(pr.e("qc.json")): shutil.copy2(pr.e("qc.json"), os.path.join(stage, "qc.json"))
        if os.path.exists(pr.e("QC-REPORT.txt")): shutil.copy2(pr.e("QC-REPORT.txt"), os.path.join(stage, "QC-REPORT.txt"))
        base = os.path.join(stage, os.path.splitext(os.path.basename(master))[0])
        written = write_captions(caption_events(pr), base)
        img, ct, how, fbox = pick_cover(pr, S, master); fi = int(round(ct * float(Fraction(stream_params(pr)[0])))); txt = []
        if os.path.exists(pr.e("elements.jsonl")):
            with open(pr.e("elements.jsonl"), encoding="utf-8") as f:
                txt = [(e["bbox"][1], e["bbox"][3]) for e in map(json.loads, f) if e["f"] == fi and e["role"] in ("caption", "chest", "cutaway")]
        draw_cover(pr, S, img, (E.get("delivery") or {}).get("cover_title"), base + ".cover.jpg", [fbox] + txt)
        shutil.copy2(pr.e("edit.yaml"), os.path.join(stage, "edit.yaml"))
        with open(os.path.join(stage, "style.yaml"), "w", encoding="utf-8") as f:
            f.write(f"# merged style profile used for this delivery; sources (later wins): {', '.join(S.get('_sources') or [])}\n")
            yaml.safe_dump({k: v for k, v in S.items() if k != "_sources"}, f, sort_keys=False, allow_unicode=True, width=140)
        results = []
        qdir = os.path.join(stage, "qc")
        rf = [s for s in specs if s["kind"] == "reframe"]
        if rf:
            os.makedirs(qdir, exist_ok=True)
            res = VAR.reframe_all(pr, S, master, rf, work, title)
            for sp in rf:
                r = res[sp["id"]]
                if r.get("status") == "failed": results.append({"id": sp["id"], "kind": "reframe", "definition": sp, "status": "failed", "reason": r["reason"]}); continue
                R = VAR.qc_reframe(pr, S, master, r, sp["aspect"], stamp if not probs else dict(stamp or {}, fail=max(1, (stamp or {}).get("fail", 1))))
                st = write_stamp(pr, r["file"], R, fast=True, out=os.path.join(qdir, f"{sp['id']}.qc.json"))
                rep = [f"QC REPORT (reframe {sp['aspect']})  {os.path.basename(r['file'])}", f"{st['fail']} FAIL   {st['warn']} WARN   {st['pass']} PASS", ""]
                for gid, s_, m_, d_ in R:
                    rep.append(f"[{s_:4s}] {gid:10s} {m_}")
                    if s_ != "PASS" and d_: rep.append("             " + d_)
                open(os.path.join(qdir, f"{sp['id']}.QC-REPORT.txt"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
                nt = r["notes"]; ok = st["fail"] == 0
                ent = {"id": sp["id"], "kind": "reframe", "definition": sp, "status": "delivered" if ok else "failed",
                       "qc": {k: st[k] for k in ("fail", "warn", "pass", "sha256")},
                       "notes": {"caption_frames_cropped": len(nt["caption_cut"]), "face_frames_cropped_for_captions": len(nt["face_cut"]),
                                 "graphics_cropped": nt["gfx_cut"], "moving_crop_shots": nt["moving_shots"], "source": r["source_frames"],
                                 "geometry": {"out": list(r["geometry"]["out"]), "crop_h": r["crop_h"], "axis": r["geometry"].get("axis", "y"), "fill": bool(r["geometry"]["wide"])}}}
                if ok: shutil.copy2(r["file"], os.path.join(stage, os.path.basename(r["file"]))); ent["file"] = os.path.basename(r["file"])
                else: ent["reason"] = "QC FAIL: " + "; ".join(f"{g} {m}" for g, s_, m, _ in R if s_ == "FAIL")
                results.append(ent)
        for sp in [s for s in specs if s["kind"] != "reframe"]:
            os.makedirs(qdir, exist_ok=True)
            out = os.path.join(work, f"{title}_{sp['id']}.mp4"); print(f"variant {sp['id']} ({sp['kind']}) ...", file=sys.stderr)
            try: r = VAR.render_variant(pr, S, sp, work, out, master)
            except SystemExit as e: r = {"status": "failed", "reason": str(e)}
            except Exception as e: r = {"status": "failed", "reason": f"{type(e).__name__}: {e}"}
            ent = {"id": sp["id"], "kind": sp["kind"], "definition": sp, "status": "delivered" if r["status"] == "passed" else "failed", "notes": r.get("notes", [])}
            if r.get("qc"):
                ent["qc"] = {k: r["qc"][k] for k in ("fail", "warn", "pass", "sha256")}
                json.dump(r["qc"], open(os.path.join(qdir, f"{sp['id']}.qc.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
                open(os.path.join(qdir, f"{sp['id']}.QC-REPORT.txt"), "w", encoding="utf-8").write(r["report"] + "\n")
            if r["status"] == "passed":
                dst = os.path.join(stage, os.path.basename(out)); shutil.copy2(out, dst); ent["file"] = os.path.basename(out)
                if sp["kind"] in ("hook", "cutdown", "end_card"):
                    written += write_captions(caption_events(r["project"]), os.path.splitext(dst)[0])
            else: ent["reason"] = r.get("reason")
            results.append(ent)
        man = {"project": (E.get("project") or {}), "version": None, "created": created, "cves_version": __version__,
               "qc_verified": not probs, "master": os.path.basename(master), "master_sha256": msha,
               "qc": {k: (stamp or {}).get(k) for k in ("fail", "warn", "pass", "sha256", "created", "fast")},
               "fps_rational": None, "cover": {"t": round(ct, 3), "how": how, "title": (E.get("delivery") or {}).get("cover_title")},
               "style_sources": S.get("_sources"), "variants": results}
        from .encode import stream_params
        fr, size = stream_params(pr); man["fps_rational"] = fr; man["size"] = list(size)
        if probs: man = {"WARNING": FORCE_WARNING, "forced_unchecked": True, "unchecked_reasons": probs, **man}
        # pick the final name last: never overwrite an existing version, even if another delivery ran meanwhile
        while True:
            vname = f"v{n:03d}"; final = os.path.join(export, vname)
            if not os.path.exists(final): break
            n += 1
        man["version"] = vname
        man["files"] = [file_info(os.path.join(dp, f), stage) for dp, _, fs in os.walk(stage) for f in sorted(fs)]
        with open(os.path.join(stage, "manifest.json"), "w", encoding="utf-8") as f: json.dump(_jsonable(man), f, indent=1, ensure_ascii=False)
        os.rename(stage, final)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True); raise
    finally:
        if not keep_temp: shutil.rmtree(work, ignore_errors=True)
        else: print(f"variant work folders kept in {work}", file=sys.stderr)
    return final, man
