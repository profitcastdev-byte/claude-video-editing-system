"""Moodboard = the complete EDIT PLAN, rendered by the same renderer as the final (true replicas, not mockups).
Outputs in PROJECT/Moodboard/:
  EDIT-PLAN.html   for the user: summary, multi-track timeline, and every shot in order with its build frames, spoken words,
                   on-screen content, framing, transitions, captions and sound cues; pre-render gate results. Approve or mark up.
  EDIT-PLAN.md     the same plan as text (what Claude reads; no images needed)
  moodboard.jpg    contact sheet of every keyframe (Claude's one-image visual review)
  frames/          the keyframes (JPG, 540x960)"""
import os, json, html, shutil, math
from PIL import Image, ImageDraw
from .render import Timeline, render

TRACK_COLORS = {"aroll": "#6b7d74", "zoom1": "#4f8f73", "zoom2": "#2f6f55", "zoom3": "#1d4f3c", "snap": "#e0663a", "cutaway": "#19e6a0",
                "roto": "#b48cff", "chest": "#d6b26c", "caption": "#9fb3ff", "end": "#ffffff", "whip": "#ffcc4d", "glitch": "#ff6b8b"}

def _words(TL, a, b):
    """spoken words in [a, b) with the caption fixes and sentence case applied (from the caption builder)"""
    return " ".join(w for ca, cb, ws in TL.caps for w, t in ws if a - .05 <= t < b)

def _cap_visible(TL, a, b):
    """is a caption event actually on screen (not under a cutaway, chest graphic, extreme punch-in or hide window)?"""
    m = (a + b) / 2
    chest_t = [(s["t0"], s["t1"]) for sid in TL.chest for s in TL.segs if s["id"] == sid]
    return not (TL.in_cut(m) or m >= TL.T_END or any(x <= m < y for x, y in chest_t) or any(x <= m < y for x, y in getattr(TL, "cap_hide", []))
                or (TL.snap and TL.snap[0] <= m < TL.snap[1]))

def _times_in(params):
    """every keyed time inside a template's params (where elements land)"""
    out = []
    def walk(k, v):
        if isinstance(v, dict):
            for kk, vv in v.items(): walk(kk, vv)
        elif isinstance(v, list):
            if k in ("type", "count") and len(v) == 2 and all(isinstance(x, (int, float)) for x in v): out.append(v[0] + v[1] if k == "count" else v[1])
            elif k in ("head", "words") and v and isinstance(v[0], list): out.extend(x[1] for x in v if len(x) > 1 and isinstance(x[1], (int, float)))
            else:
                for x in v: walk(k, x)
        elif isinstance(v, (int, float)) and (k.endswith("_at") or k in ("at", "tag", "check", "state_at")): out.append(v)
    walk("", params or {}); return sorted(set(round(x, 2) for x in out))

def shots(TL):
    """the edit as an ordered list of shots covering the whole runtime"""
    F = TL.FPS; S = []
    cut_iv = sorted((c["start"], c["end"], c) for c in TL.cuts)
    t = 0.0
    def aroll_pieces(a, b):
        for s in TL.segs:
            lo, hi = max(a, s["t0"]), min(b, s["t1"])
            if hi - lo >= .5 / F: S.append({"kind": "aroll", "start": lo, "end": hi, "seg": s})
    for a, b, c in cut_iv:
        if a > t: aroll_pieces(t, a)
        S.append({"kind": "cutaway", "start": a, "end": b, "cut": c}); t = b
    if t < TL.T_END: aroll_pieces(t, TL.T_END)
    if TL.END: S.append({"kind": "end", "start": TL.T_END, "end": TL.N / F})
    for sh in S:
        a, b = sh["start"], sh["end"]
        if sh["kind"] == "aroll":
            sid = sh["seg"]["id"]; z = TL.zoom.get(sid, 1.0); r = TL.roto.get(sid); ch = TL.chest.get(sid, [])
            snap = TL.snap if TL.snap and TL.snap[0] < b and TL.snap[1] > a else None
            keys = [a + min(.4, (b - a) / 2)]
            if r: keys += [x + .5 for x in _times_in(r.get("params")) if a <= x < b] or [(a + b) / 2]
            for c in ch: keys += [x + .7 for x in _times_in(c.get("params")) if a <= x < b]
            if snap: keys.append((max(a, snap[0]) + min(b, snap[1])) / 2)
            sh.update(zoom=z, lift=sid in getattr(TL, "lift", set()), roto=r, chest=ch, snap=snap)
        elif sh["kind"] == "cutaway":
            c = sh["cut"]; inner = [x + .35 for x in _times_in(c.get("params")) if a <= x < b - .1]
            keys = [a + .2] + inner + [b - .15]
        else:
            keys = [b - .1]
        keys = sorted(set(round(min(max(k, a + .02), b - .02) * F) for k in keys))
        if len(keys) > 6:   # keep the build readable: first, last and evenly spaced in between
            idx = sorted(set([0, len(keys) - 1] + [round(i * (len(keys) - 1) / 5) for i in range(6)])); keys = [keys[i] for i in idx]
        sh["frames"] = keys
        sh["words"] = _words(TL, a, b)
        sh["captions"] = [" ".join(w for w, _ in ws) for ca, cb, ws in TL.caps if ca < b and cb > a and _cap_visible(TL, max(ca, a), min(cb, b))] if sh["kind"] == "aroll" else []
        sh["beat"] = ("" if sh["kind"] != "aroll" else (TL.pr.json("edl.json") and next((c.get("beat") or "" for c in TL.pr.json("edl.json")["clips"] if c["id"] == sh["seg"]["clip"]), "")))
        sh["trans_in"] = next((k for tb, k in TL.trans if abs(tb - a) < .02), "cut" if a > 0 else "open")
        sh["trans_out"] = next((k for tb, k in TL.trans if abs(tb - b) < .02), "cut")
    return S

def describe(sh):
    if sh["kind"] == "cutaway":
        c = sh["cut"]; p = c.get("params", {})
        bits = [p.get(k) for k in ("label", "unit", "pill") if p.get(k)]
        items = [f"{i.get('title','')} {i.get('sub') or ''}".strip() for i in p.get("items", [])] + [r.get("q") or r.get("text") for r in p.get("rows", [])]
        head = " ".join(w[0] for w in p.get("head", []))
        val = f"{p.get('prefix','')}{p.get('value','')}{p.get('suffix','')}" if "value" in p else ""
        return f"Cutaway `{c['template']}`: " + " · ".join(x for x in [head, val] + bits + items if x)
    if sh["kind"] == "end": return "End card `logo_end`"
    out = [f"A-roll `{sh['seg']['id']}` at {sh['zoom']:.2f}×" + (" (lifted)" if sh.get("lift") else "")]
    if sh.get("snap"): out.append(f"extreme punch-in {sh['snap'][2]:.2f}× {sh['snap'][0]:.2f}-{sh['snap'][1]:.2f}s")
    if sh.get("roto"): out.append(f"roto `{sh['roto']['template']}` behind the head")
    for c in sh.get("chest", []): out.append(f"chest `{c['template']}`" + (f": {' '.join(c['params'].get('lines', []))}" if c.get("params", {}).get("lines") else ""))
    return "; ".join(out)

def moodboard(pr):
    TL = Timeline(pr); F = TL.FPS; S = shots(TL)
    from .mix import all_cues
    try: cues = sorted(all_cues(TL), key=lambda c: c[0])
    except SystemExit: cues = []
    try:
        from .qc import run_stage; nf, gates = run_stage(pr, "plan")
    except Exception as e: gates = f"plan-stage gates not run: {e}"
    want = sorted(set(f for sh in S for f in sh["frames"]))
    tmp = pr.e("frames_plan"); shutil.rmtree(tmp, ignore_errors=True)
    render(pr, only=want, out_dir=tmp)
    out = pr.p("Moodboard"); fdir = os.path.join(out, "frames"); shutil.rmtree(fdir, ignore_errors=True); os.makedirs(fdir)
    for f in want:
        Image.open(os.path.join(tmp, f"{f:05d}.png")).convert("RGB").resize((540, 960), Image.LANCZOS).save(os.path.join(fdir, f"{f:05d}.jpg"), quality=86)
    shutil.rmtree(tmp, ignore_errors=True)
    E = pr.edit; title = E.get("project", {}).get("title", "Edit"); T = TL.N / F
    cut_share = sum(sh["end"] - sh["start"] for sh in S if sh["kind"] == "cutaway") / max(TL.T_END, 1e-6)
    n_cuts = len(S) - 1; aroll_lens = [sh["end"] - sh["start"] for sh in S if sh["kind"] == "aroll"]
    M = E.get("music") or {}
    stats = [("Runtime", f"{T:.1f} s"), ("Shots", str(len(S))), ("Cuts / min", f"{n_cuts / T * 60:.0f}"), ("Cutaway share", f"{cut_share:.0%}" + (" ({:.0%}–{:.0%})".format(*TL.S.get("grammar.cutaway_share")) if TL.S.get("grammar.cutaway_share") else "")),
             ("Median A-roll shot", f"{sorted(aroll_lens)[len(aroll_lens)//2]:.1f} s" if aroll_lens else "-"), ("Roto moments", f"{len(TL.roto)} (≤ {TL.S.get('grammar.roto_max', 4)})"),
             ("Captions on screen", str(sum(1 for ca, cb, ws in TL.caps if _cap_visible(TL, ca, min(cb, TL.T_END))))), ("SFX cues", str(len(cues))),
             ("Music", (os.path.basename(M.get("file") or "none") + (f", drop at {M.get('drop_cut')} s" if M.get("drop_cut") else "") + f", bed {M.get('bed_lu', TL.S.get('sound.bed_lu', -10))} LU")),
             ("Style", " + ".join(TL.S.get("_sources", ["default"])))]

    # ---------------- EDIT-PLAN.md (text; Claude reads this)
    md = [f"# Edit plan: {title}", "", " | ".join(f"**{k}** {v}" for k, v in stats), "", "## Shots", "",
          "| # | Time | Dur | Shot | Transition in → out | Spoken | Captions | SFX |", "|---|---|---|---|---|---|---|---|"]
    for i, sh in enumerate(S, 1):
        sfx = ", ".join(f"{c[1]}@{c[0]:.2f}" for c in cues if sh["start"] - .3 <= c[0] < sh["end"])
        md.append(f"| {i} | {sh['start']:.2f}–{sh['end']:.2f} | {sh['end'] - sh['start']:.2f} | {describe(sh)} | {sh['trans_in']} → {sh['trans_out']} | {sh['words']} | {' / '.join(sh['captions'])} | {sfx} |")
    md += ["", "## Pre-render gates", "```", gates if isinstance(gates, str) else str(gates), "```"]
    open(os.path.join(out, "EDIT-PLAN.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

    # ---------------- contact sheet (Claude's one-image review)
    cols = 8; tw, th = 180, 320; rows = math.ceil(len(want) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (20, 20, 20)); d = ImageDraw.Draw(sheet)
    shot_of = {f: i for i, sh in enumerate(S, 1) for f in sh["frames"]}
    for k, f in enumerate(want):
        x, y = (k % cols) * tw, (k // cols) * (th + 22)
        sheet.paste(Image.open(os.path.join(fdir, f"{f:05d}.jpg")).resize((tw, th)), (x, y))
        d.text((x + 4, y + th + 4), f"#{shot_of[f]}  {f / F:.2f}s", fill=(255, 230, 120))
    sheet.save(os.path.join(out, "moodboard.jpg"), quality=85)

    # ---------------- EDIT-PLAN.html (the user's plan)
    W_ = 1000; px = lambda t: t / T * W_
    beat_of = {c["id"]: c.get("beat") for c in pr.json("edl.json")["clips"]}
    BEATC = {"H": "#ff9f43", "P": "#ff6b6b", "A": "#c56cf0", "PR": "#19e6a0", "O": "#54a0ff", "C": "#feca57"}
    lanes = [("Beats", "beat"), ("Shots", "shot"), ("Framing", "zoom"), ("Roto", "roto"), ("Chest", "chest"), ("Captions", "caption"), ("Transitions", "trans"), ("SFX", "sfx"), ("Music", "music")]
    lane_y = {name: 22 + i * 26 for i, (name, _) in enumerate(lanes)}; H_ = 22 + len(lanes) * 26 + 24
    svg = [f'<svg viewBox="0 0 {W_ + 90} {H_}" class="tl" role="img" aria-label="timeline">']
    for name, _ in lanes: svg.append(f'<text x="0" y="{lane_y[name] + 14}" class="ln">{name}</text>')
    X = lambda t: 90 + px(t)
    def rect(lane, a, b, color, label="", tip=""):
        y = lane_y[lane]; w = max(1.5, px(b - a))
        svg.append(f'<g><title>{html.escape(tip or label)}</title><rect x="{X(a):.1f}" y="{y}" width="{w:.1f}" height="18" rx="3" fill="{color}"/>'
                   + (f'<text x="{X(a) + 3:.1f}" y="{y + 13}" class="bl">{html.escape(label[:max(0, int(w / 6))])}</text>' if label and w > 24 else "") + "</g>")
    for s_ in TL.segs:
        bt = beat_of.get(s_["clip"])
        if bt: rect("Beats", s_["t0"], s_["t1"], BEATC.get(bt, "#888"), bt, f"{bt}: {s_['clip']}")
    for i, sh in enumerate(S, 1):
        k = sh["kind"]; col = TRACK_COLORS["cutaway" if k == "cutaway" else "end" if k == "end" else "aroll"]
        rect("Shots", sh["start"], sh["end"], col, f"{i}", f"#{i} {describe(sh)}")
        if k == "aroll":
            z = sh["zoom"]; zc = TRACK_COLORS["zoom1" if z < 1.1 else "zoom2" if z < 1.3 else "zoom3"]
            rect("Framing", sh["start"], sh["end"], zc, f"{z:.2f}×", f"zoom {z:.2f}×")
            if sh.get("snap"): rect("Framing", max(sh["start"], sh["snap"][0]), min(sh["end"], sh["snap"][1]), TRACK_COLORS["snap"], "", f"extreme punch-in {sh['snap'][2]}×")
            if sh.get("roto"): rect("Roto", sh["start"], sh["end"], TRACK_COLORS["roto"], sh["roto"]["template"], sh["roto"]["template"])
            for c in sh.get("chest", []): rect("Chest", sh["start"], sh["end"], TRACK_COLORS["chest"], c["template"], c["template"])
    for a, b, ws in TL.caps:
        if _cap_visible(TL, a, min(b, TL.T_END)): rect("Captions", a, min(b, TL.T_END), TRACK_COLORS["caption"], "", " ".join(w for w, _ in ws))
    for tb, k in TL.trans:
        svg.append(f'<g><title>{k} at {tb:.2f}s</title><rect x="{X(tb) - 3:.1f}" y="{lane_y["Transitions"]}" width="6" height="18" fill="{TRACK_COLORS.get(k, "#fff")}"/></g>')
    for t0, name, g, kw in cues:
        svg.append(f'<g><title>{name} {g} dB at {t0:.2f}s</title><line x1="{X(t0):.1f}" x2="{X(t0):.1f}" y1="{lane_y["SFX"]}" y2="{lane_y["SFX"] + 18}" stroke="{"#ffcc4d" if kw.get("reveal") else "#8aa"}" stroke-width="{2 if kw.get("reveal") else 1}"/></g>')
    if M.get("file"):
        rect("Music", 0, T, "#2a3a33", f"bed {M.get('bed_lu', -7)} LU, ducked under the voice", "music bed")
        if M.get("drop_cut"): svg.append(f'<g><title>music drop at {M["drop_cut"]}s</title><polygon points="{X(M["drop_cut"])},{lane_y["Music"]} {X(M["drop_cut"]) - 6},{lane_y["Music"] + 18} {X(M["drop_cut"]) + 6},{lane_y["Music"] + 18}" fill="#e0663a"/></g>')
    for s_ in range(0, int(T) + 1, 5): svg.append(f'<text x="{X(s_):.1f}" y="{H_ - 4}" class="ax">{s_}s</text>')
    svg.append("</svg>")
    cards = []
    for i, sh in enumerate(S, 1):
        frames = "".join(f'<figure><img loading="lazy" src="frames/{f:05d}.jpg" alt="frame {f}"><figcaption>{f / F:.2f}s</figcaption></figure>' for f in sh["frames"])
        sfx = ", ".join(f"{html.escape(c[1])} {c[0]:.2f}s" for c in cues if sh["start"] - .3 <= c[0] < sh["end"]) or "–"
        if sh["kind"] == "cutaway":   # a cutaway sits on the beat of the voice under it
            mid = (sh["start"] + sh["end"]) / 2; sseg = next((x for x in TL.segs if x["t0"] <= mid < x["t1"]), None)
            sh["beat"] = beat_of.get(sseg["clip"], "") if sseg else ""
        rows = [("Beat", {"H": "Hook", "P": "Problem", "A": "Agitation", "PR": "Proof", "O": "Offer", "C": "CTA"}.get(sh.get("beat") or "", "–")),
                ("Spoken", html.escape(sh["words"]) or "–"), ("On screen", html.escape(describe(sh)).replace("`", "")),
                ("Transitions", f"{sh['trans_in']} → {sh['trans_out']}"), ("Captions", html.escape(" / ".join(sh["captions"])) or "–"), ("Sound", sfx)]
        kind = {"aroll": "A-roll", "cutaway": "Cutaway", "end": "End card"}[sh["kind"]]
        cards.append(f'<section class="shot {sh["kind"]}"><header><b>#{i}</b> <span class="tag">{kind}</span> {sh["start"]:.2f}–{sh["end"]:.2f}s '
                     f'<span class="dur">{sh["end"] - sh["start"]:.2f}s</span></header><div class="strip">{frames}</div>'
                     f'<table>{"".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)}</table></section>')
    stat_html = "".join(f"<div><span>{k}</span><b>{html.escape(v)}</b></div>" for k, v in stats)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}: edit plan</title><style>
:root{{--bg:#0e1210;--fg:#e9efec;--mut:#94a39c;--card:#151b18;--line:#26302b;--acc:#19e6a0}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;padding:24px 16px;max-width:1180px;margin:auto}}
h1{{margin:0 0 4px}} .sub{{color:var(--mut);margin:0 0 18px}} h2{{margin:28px 0 10px;font-size:17px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}} .stats div{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}
.stats span{{display:block;color:var(--mut);font-size:12px}} .tl{{width:100%;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 0}}
.ln{{fill:var(--mut);font-size:11px}} .bl{{fill:#0b0f0d;font-size:10px;font-weight:600}} .ax{{fill:var(--mut);font-size:10px}}
.shot{{background:var(--card);border:1px solid var(--line);border-left:4px solid #6b7d74;border-radius:8px;margin:12px 0;padding:10px 12px}}
.shot.cutaway{{border-left-color:var(--acc)}} .shot.end{{border-left-color:#fff}} header{{margin-bottom:8px}} .tag{{background:#26302b;border-radius:10px;padding:1px 8px;font-size:12px}}
.dur{{color:var(--mut)}} .strip{{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px}} figure{{margin:0;flex:0 0 auto}} img{{height:240px;border-radius:6px;display:block}}
figcaption{{color:var(--mut);font-size:11px;text-align:center}} table{{border-collapse:collapse;width:100%;margin-top:6px}} th{{text-align:left;color:var(--mut);font-weight:500;width:110px;vertical-align:top;padding:3px 8px 3px 0}}
td{{padding:3px 0}} pre{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;overflow-x:auto;font-size:12px}}
@media (max-width:640px){{img{{height:180px}} th{{width:80px}}}}</style></head><body>
<h1>{html.escape(title)}: edit plan</h1><p class="sub">Every frame below is rendered by the final renderer, so the edit will look exactly like this.
Approve the plan, or reply with shot numbers and what to change.</p>
<div class="stats">{stat_html}</div>
<h2>Timeline</h2>{"".join(svg)}
<h2>Shot by shot</h2>{"".join(cards)}
<h2>Pre-render checks</h2><pre>{html.escape(gates if isinstance(gates, str) else str(gates))}</pre>
</body></html>"""
    open(os.path.join(out, "EDIT-PLAN.html"), "w", encoding="utf-8").write(page)
    for old in ("moodboard.html",):
        if os.path.exists(os.path.join(out, old)): os.remove(os.path.join(out, old))
    return len(S), len(want)
