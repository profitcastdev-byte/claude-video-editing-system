"""`cves critique [vNNN|master]`: the senior-editor review pack (docs/LEARNING.md, knowledge-base/CREATIVE.md).

Writes PROJECT/Edit/critique/:
  contact_sheet.jpg   one frame per shot + key moments (frame 0, each graphic settled, the end), labelled time + id/template
  timeline.png        energy / interrupt timeline: cuts, graphics in, SFX hits, music energy, speech on/off, loudness
  critique.json       the measured facts and the restraint-budget usage
  CRITIQUE.md         the facts + a fixed rubric Claude scores 1-10 with reasons, and the 3 changes a senior editor makes next
Claude fills CRITIQUE.md and journals the scores: `cves learn rate <ver> <mean> --by claude --scores hook=..,story=..`.
The engine measures; it never scores taste itself."""
import json, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config as C, style as STY

RUBRIC = [
    ("hook", "Hook strength", "Does frame 0 / the first 2 s stop the scroll? Topic named, tension, motion from frame 0"),
    ("story", "Story clarity", "Can a stranger retell it after one watch, sound off? One idea per beat, loops closed"),
    ("pacing", "Pacing / rhythm", "Shot lengths vary on purpose (build, burst, release); no metronome, no drag"),
    ("aesthetics", "Visual aesthetics", "Composition, type hierarchy, colour discipline; every paused frame looks designed"),
    ("motion", "Motion craft", "Easing, origins and exits, one primary mover, holds that breathe"),
    ("sound", "Sound design", "Voice first; bed level, SFX on the frame, music lift on the payoff"),
    ("creativity", "Creativity", "Is there ONE memorable moment someone would screenshot or rewatch?"),
    ("restraint", "Restraint", "Anything gratuitous? Every element motivated; within the restraint budget"),
    ("platform", "Platform fit", "Safe zones, native pacing and length for the target platform, loop seam"),
    ("brand", "Brand fit", "Looks like this client's series (style profile), claims only from Brand/claims.md"),
]

def _font(size):
    from .gfx import FONTS
    for n in ("Poppins-SemiBold.ttf", "Poppins-Medium.ttf"):
        p = os.path.join(FONTS, n)
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def _probe(video):
    r = subprocess.run([C.get("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                        "-of", "json", video], capture_output=True, text=True)
    if r.returncode: raise SystemExit(f"cannot read {video}: {r.stderr.strip()[:200]}")
    d = json.loads(r.stdout); st = d["streams"][0]; n, _, m = st["r_frame_rate"].partition("/")
    return float(d["format"]["duration"]), int(st["width"]), int(st["height"]), float(n) / float(m or 1)

def resolve_video(pr, which=None):
    which = which or "master"
    if which != "master":
        d = pr.p("Export", which)
        if not os.path.isdir(d): raise SystemExit(f"no Export/{which}: deliver first, or critique `master`")
        man = os.path.join(d, "manifest.json")
        if os.path.exists(man):
            with open(man, encoding="utf-8") as f: m = json.load(f).get("master")
            if m and os.path.exists(os.path.join(d, m)): return os.path.join(d, m)
        vids = sorted(f for f in os.listdir(d) if f.endswith(".mp4"))
        if not vids: raise SystemExit(f"no .mp4 in Export/{which}")
        return os.path.join(d, vids[0])
    st = pr.json("qc.json") or {}
    if st.get("video") and os.path.exists(st["video"]): return st["video"]
    ex = pr.p("Export")
    vids = sorted((os.path.join(ex, f) for f in os.listdir(ex) if f.endswith(".mp4")), key=os.path.getmtime) if os.path.isdir(ex) else []
    if not vids: raise SystemExit("no Export/*.mp4: run `cves build` (or pass vNNN)")
    return vids[-1]

def _frame(video, t, w, h):
    r = subprocess.run([C.get("ffmpeg"), "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={w}:{h}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if len(r.stdout) < w * h * 3: return Image.new("RGB", (w, h), (40, 40, 40))
    return Image.fromarray(np.frombuffer(r.stdout[:w * h * 3], np.uint8).reshape(h, w, 3))

def _audio(path, sr=8000):
    r = subprocess.run([C.get("ffmpeg"), "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32) if r.returncode == 0 else np.zeros(0, np.float32)

def _env_db(y, sr=8000, hop=0.05):
    n = int(sr * hop)
    if len(y) < n: return np.zeros(0)
    k = len(y) // n; rms = np.sqrt((y[:k * n].reshape(k, n) ** 2).mean(1) + 1e-12)
    return 20 * np.log10(rms + 1e-9)

FOOTAGE = {"broll_shot", "video_broll", "image", "screen_rec"}   # media templates that show footage, not designed graphics

def structure(pr, dur, video=None):
    """shots [(t0, t1, label)], graphics [(t0, t1, id, template)], transitions [(t, kind)] from timeline.json / edit.yaml"""
    tl = pr.json("timeline.json") or {}; E = pr.edit or {}
    cuts_ = tl.get("cutaways") or []
    # footage (B-roll shots, clips, stills, screen recordings) are shots, not animated graphics: they count as cuts
    foot = [(float(c["start"]), float(c["end"])) for c in cuts_ if c.get("template") in FOOTAGE]
    gfx = [(float(c["start"]), float(c["end"]), c["id"], c["template"]) for c in cuts_ if c.get("template") not in FOOTAGE]
    segs = {s["id"]: (float(s.get("t0", 0)), float(s.get("t1", 0))) for s in tl.get("segments") or [] if "t0" in s}
    for k in ("roto", "chest"):
        for i, r in enumerate(E.get(k) or []):
            ids = r.get("segment") if isinstance(r.get("segment"), list) else [r.get("segment")]
            span = [segs[x] for x in ids if x in segs]
            if span: gfx.append((min(a for a, _ in span), max(b for _, b in span), f"{k}.{i}", r.get("template", "?")))
    ec = E.get("end_card") if isinstance(E.get("end_card"), dict) else None
    if ec and ec.get("duration"): gfx.append((max(0.0, dur - float(ec["duration"])), dur, "end_card", ec.get("template", "end")))
    for m in E.get("motion") or []:
        if isinstance(m, dict) and m.get("start") is not None:
            try: gfx.append((float(m["start"]), float(m.get("end", m["start"])), str(m.get("id", "motion")), str(m.get("piece") or m.get("template") or "motion")))
            except (TypeError, ValueError): pass
    trans = [(float(t), str(k)) for t, k in tl.get("transitions") or [] if isinstance(t, (int, float))]
    bounds = sorted({0.0, dur} | {round(b[0], 3) for b in segs.values()} | {round(g[0], 3) for g in gfx if g[2].startswith("c") or g[2] == "end_card"}
                    | {round(g[1], 3) for g in gfx if g[2].startswith("c")} | {round(a, 3) for a, _ in foot} | {round(b, 3) for _, b in foot})
    bounds = [b for b in bounds if 0 <= b <= dur]
    if len(bounds) <= 2:          # no timeline: detect cuts on the picture
        from .learn import _fallback_analyse
        if not video: return [(0.0, dur, "shot 1")], gfx, trans
        bounds = sorted({0.0, dur} | {float(c) for c in _fallback_analyse(video, 600)["cuts"]})
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        if b - a < 1 / 30: continue
        mid = (a + b) / 2; lab = None
        for g in gfx:
            if g[0] <= mid < g[1] and (g[2].startswith("c") or g[2] == "end_card"): lab = f"{g[2]} {g[3]}"; break
        if lab is None:
            lab = next((sid for sid, (s0, s1) in segs.items() if s0 <= mid < s1), f"shot {len(shots) + 1}")
        shots.append((a, b, lab))
    return shots, gfx, trans

def critique(pr, which=None):
    video = resolve_video(pr, which)
    version = which or "master"
    dur, W, H, fps = _probe(video); S = STY.load(pr)
    out = pr.e("critique"); os.makedirs(out, exist_ok=True)
    shots, gfx, trans = structure(pr, dur, video)

    # ---- contact sheet: one frame per shot (its middle) + key moments
    tiles = [(0.0, "frame 0", "first frame")]
    for a, b, lab in shots: tiles.append(((a + b) / 2, lab, "shot"))
    for g in gfx: tiles.append((min(g[1] - 0.05, g[0] + min(0.6, (g[1] - g[0]) / 2)), f"{g[2]} {g[3]} settled", "moment"))
    tiles.append((max(0.0, dur - 0.1), "last frame", "end"))
    tiles = sorted(tiles, key=lambda x: x[0]); ded = []
    for t in tiles:
        if not ded or t[0] - ded[-1][0] > 0.2 or t[2] in ("first frame", "end"): ded.append(t)
    if len(ded) > 48: ded = [ded[int(i * (len(ded) - 1) / 47)] for i in range(48)]
    tw = 200 if H >= W else 320; th = int(round(tw * H / W / 2) * 2); lh = 40; cols = 6 if H >= W else 4
    rows = (len(ded) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + lh + 8) + 8), (18, 18, 20)); dr = ImageDraw.Draw(sheet)
    f1, f2 = _font(15), _font(12)
    for i, (t, lab, kind) in enumerate(ded):
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + lh + 8)
        sheet.paste(_frame(video, t, tw, th), (x, y))
        dr.text((x + 2, y + th + 3), f"{t:6.2f}s  {kind}", font=f1, fill=(230, 230, 230)); dr.text((x + 2, y + th + 21), lab[:30], font=f2, fill=(160, 170, 255))
    sheet_p = os.path.join(out, "contact_sheet.jpg"); sheet.save(sheet_p, quality=88)

    # ---- energy / interrupt timeline
    sr = 8000; hop = 0.05
    master = _env_db(_audio(video, sr), sr, hop)
    stem = lambda n: _env_db(_audio(pr.e("stems", f"{n}.wav"), sr), sr, hop) if os.path.exists(pr.e("stems", f"{n}.wav")) else np.zeros(0)
    music, sfx, voice = stem("music"), stem("sfx"), stem("voice")
    words = pr.json("words.json") or []
    speech = [(float(w[0]), float(w[1])) for w in words if isinstance(w, (list, tuple)) and len(w) >= 2]
    if not speech and len(voice):
        on = voice > (voice.max() - 30); speech = [(i * hop, (i + 1) * hop) for i in np.flatnonzero(on)]
    hits = []
    if len(sfx) > 2:
        thr = max(sfx.max() - 24, -45)
        for i in range(1, len(sfx) - 1):
            if sfx[i] > thr and sfx[i] >= sfx[i - 1] and sfx[i] > sfx[i + 1] and (not hits or i * hop - hits[-1] > .15): hits.append(i * hop)
    TW_, LM, RH = 1600, 120, 46
    labels = ["cuts", "graphics", "sfx", "music", "speech", "loudness"]
    img = Image.new("RGB", (TW_, RH * len(labels) + 40), (18, 18, 20)); d = ImageDraw.Draw(img)
    X = lambda t: LM + (TW_ - LM - 10) * max(0.0, min(1.0, t / dur if dur else 0))
    for i, lab in enumerate(labels):
        y = 30 + i * RH; d.text((8, y + 14), lab, font=_font(15), fill=(220, 220, 220)); d.line([(LM, y + RH - 2), (TW_ - 10, y + RH - 2)], fill=(45, 45, 52))
    for s in range(int(dur) + 1):
        d.line([(X(s), 24), (X(s), 30 + RH * len(labels))], fill=(34, 34, 40)); d.text((X(s) + 2, 6), f"{s}s", font=_font(11), fill=(140, 140, 150))
    y = 30
    for a, _, _ in shots[1:]: d.line([(X(a), y + 4), (X(a), y + RH - 6)], fill=(255, 255, 255), width=2)
    for t, k in trans:
        if k != "cut": d.text((X(t) + 3, y + 26), k[:6], font=_font(11), fill=(255, 200, 90))
    y += RH
    for j, g in enumerate(gfx):
        yy = y + 4 + (j % 3) * 13; d.rectangle([X(g[0]), yy, max(X(g[0]) + 2, X(g[1])), yy + 10], fill=(76, 141, 255)); d.text((X(g[0]) + 2, yy - 2), g[2][:10], font=_font(10), fill=(255, 255, 255))
    y += RH
    for t in hits: d.line([(X(t), y + 6), (X(t), y + RH - 6)], fill=(255, 120, 90), width=2)
    y += RH
    def curve(env, yy, col):
        if not len(env): d.text((LM + 4, yy + 14), "n/a", font=_font(12), fill=(120, 120, 120)); return
        lo, hi = max(env.max() - 40, env.min()), env.max()
        pts = [(X(i * hop), yy + RH - 6 - (RH - 12) * (min(max(v, lo), hi) - lo) / max(1e-6, hi - lo)) for i, v in enumerate(env)]
        d.line(pts, fill=col, width=2)
    curve(music, y, (120, 220, 160)); y += RH
    for a, b in speech: d.rectangle([X(a), y + 12, max(X(a) + 1, X(b)), y + RH - 12], fill=(220, 220, 220))
    y += RH
    curve(master, y, (200, 160, 255))
    tl_p = os.path.join(out, "timeline.png"); img.save(tl_p)

    # ---- facts + restraint budget
    lens = [b - a for a, b, _ in shots] or [dur]
    sp = sorted(speech); gaps = [b2[0] - a1[1] for a1, b2 in zip(sp, sp[1:])]
    E = pr.edit or {}; per30 = 1.0 / max(1.0, dur / 30.0) if dur else 0     # budgets are per 30 s; a shorter video still gets one 30 s allowance
    kinds = sorted({k for _, k in trans if k != "cut"} | {str(t.get("kind")) for t in E.get("transitions") or [] if isinstance(t, dict) and t.get("kind") not in (None, "cut")})
    sig = (1 if (E.get("aroll") or {}).get("snap") else 0) + sum(1 for m in E.get("motion") or [] if isinstance(m, dict) and m.get("signature"))
    facts = {"video": os.path.basename(video), "version": version, "duration_s": round(dur, 2), "size": [W, H], "fps": round(fps, 3),
             "shots": len(shots), "avg_shot_s": round(float(np.mean(lens)), 2), "longest_shot_s": round(max(lens), 2),
             "longest_shot_at": round(shots[int(np.argmax(lens))][0], 2) if shots else 0.0, "cuts_per_min": round((len(shots) - 1) / dur * 60, 1) if dur else 0,
             "first_change_s": round(shots[1][0], 2) if len(shots) > 1 else None, "graphics": len(gfx), "sfx_hits": len(hits),
             "speech_share": round(sum(b - a for a, b in speech) / dur, 2) if dur else None, "pauses_over_0.6s": sum(1 for g in gaps if g > .6),
             "transition_kinds": kinds, "signature_moments": sig, "style_sources": S.get("_sources")}
    B = lambda k, dflt: S.get(f"creative.{k}", dflt)
    budget = [("signature moments", sig, round(B("signature_per_30s", 1) / per30, 1) if per30 else None),
              ("transition kinds (not cut)", len(kinds), B("transition_kinds_max", 2)),
              ("animated graphics", len(gfx), round(B("motion_pieces_per_30s", 6) / per30, 1) if per30 else None),
              ("accent colours", "check by eye", B("accent_colors_max", 1))]
    from . import craft as CR                   # craft moves: ramps, camera moves, match cuts, text behind (docs/MOTION.md "Craft")
    cu, ca = CR.budget(E, S, dur or 30.0); budget.insert(3, ("craft moves", cu, ca if per30 else None))
    facts["craft_moves"] = sorted(f"{k} ({w})" for k, w in CR.usage(E))
    budget = [(n, u, b, "OVER" if isinstance(u, (int, float)) and b is not None and u > b else "ok") for n, u, b in budget]
    with open(os.path.join(out, "critique.json"), "w", encoding="utf-8") as f:
        json.dump({"facts": facts, "budget": [{"item": n, "used": u, "budget": b, "status": s} for n, u, b, s in budget]}, f, indent=1, ensure_ascii=False)

    L = [f"# Critique: {facts['video']} ({version})", "",
         "Fill this in honestly as a senior editor would, from `contact_sheet.jpg` + `timeline.png` (one look each) and the facts below.",
         "Fix anything that scores below 7 and can be fixed in edit.yaml, re-run QC, then critique again. Rules: knowledge-base/CREATIVE.md.", "",
         "## Facts (measured)", "", "| fact | value |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in facts.items()]
    L += ["", "## Restraint budget (style `creative:`)", "", "| item | used | budget | |", "|---|---|---|---|"]
    L += [f"| {n} | {u} | {b} | {s} |" for n, u, b, s in budget]
    L += ["", "## Rubric (score 1-10, one line of reason each)", "", "| # | criterion | what to judge | score | reason |", "|---|---|---|---|---|"]
    L += [f"| {i + 1} | {name} (`{k}`) | {q} | _ /10 | |" for i, (k, name, q) in enumerate(RUBRIC)]
    L += ["", "**Overall:** _ /10", "", "## The 3 changes a senior editor would make next", "", "1. ", "2. ", "3. ", "",
          "## Log it", "", "```", f"cves learn rate {version} <overall> --by claude --why \"<one line>\" \\",
          "  --scores " + ",".join(f"{k}=_" for k, _, _ in RUBRIC), "```", ""]
    md = os.path.join(out, "CRITIQUE.md")
    with open(md, "w", encoding="utf-8") as f: f.write("\n".join(L))
    from . import learn; learn.on_critique(pr, version, video)
    return {"dir": out, "sheet": sheet_p, "timeline": tl_p, "md": md, "facts": facts, "budget": budget}
