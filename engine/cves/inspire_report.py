"""Inspire v2 report: PROJECT/Edit/inspire/REPORT.md (see / hear / feel per reference + the chosen mix) and the
aesthetic-review.md stub Claude fills by looking at the contact sheets. Plain markdown, written for a human editor."""
import os, datetime

RUBRIC = ["Composition", "Typography quality", "Colour mood", "Motion character", "Texture / grain", "Negative space",
          "Premium vs cheap read", "What to steal", "What to avoid"]
BLOCKS = "▁▂▃▄▅▆▇█"


def spark(xs):
    xs = [x for x in (xs or []) if x is not None]
    if not xs: return ""
    lo, hi = min(xs), max(xs)
    return "".join(BLOCKS[int((x - lo) / (hi - lo) * 7) if hi > lo else 3] for x in xs)


def _v(x, unit="", nd=2):
    if x is None: return "n/a"
    if isinstance(x, bool): return "yes" if x else "no"
    if isinstance(x, float): return f"{x:.{nd}f}".rstrip("0").rstrip(".") + unit
    return f"{x}{unit}"


def _see(s):
    from .inspire_see import summary_line
    if not s or "contrast" not in s: return ["- (no frames decoded)"]
    c = s["contrast"]; out = [f"- **Read:** {summary_line(s)}"]
    out.append(f"- Canvas: {s.get('size', ['?', '?'])[0]}x{s.get('size', ['?', '?'])[1]}, {s['orientation']}, display {s['display_aspect']:.2f}, "
               f"content {s['content_aspect']:.2f}" + (f", **{s['letterbox']}** bars" if s.get("letterbox") else ""))
    out.append(f"- Tone curve (luma p2 / p25 / p50 / p75 / p98): {c['p2']:.2f} / {c['p25']:.2f} / {c['p50']:.2f} / {c['p75']:.2f} / {c['p98']:.2f}")
    out.append(f"- Saturation p50 / p90: {s['saturation']['p50']:.2f} / {s['saturation']['p90']:.2f}"
               + (f"; mid-tones a* {s['temperature']['a']:+.1f}, b* {s['temperature']['b']:+.1f} ({s['temperature']['read']})" if s.get("temperature") else ""))
    bits = []
    if s.get("grain"): bits.append(f"noise sigma {s['grain']['sigma']:.1f} ({s['grain']['read']})")
    if s.get("vignette"): bits.append(f"corner/centre {s['vignette']['corner_ratio']:.2f} ({s['vignette']['read']})")
    if s.get("motion_blur"): bits.append(f"{s['motion_blur']['soft_share']:.0%} of frames motion-soft")
    if bits: out.append("- Texture: " + "; ".join(bits))
    return out


def _hear(h):
    from .inspire_audio import summary_line
    if not h or not h.get("has_audio"): return ["- No audio track."]
    out = [f"- **Read:** {summary_line(h)}"]
    out.append(f"- Voice: {'yes' if h['voice']['present'] else 'no (music-led / silent)'}; speech in {h['voice']['share']:.0%} of the audible time")
    m = h["music"]; t = h.get("tempo") or {}
    out.append(f"- Music: {'yes' if m['present'] else 'no'} ({m['share']:.0%} of 1 s windows)" + (f"; {t['bpm']:.1f} BPM, beat salience {t['salience']:.1f}" if t.get("bpm") else ""))
    if h.get("gap_lu") is not None:
        out.append(f"- Balance: bed {h['gap_lu']:+.1f} LU vs the voice while speaking" + (f"; ducked {h['duck_db']:.1f} dB under the words" if h.get("duck_db") is not None else ""))
    out.append(f"- SFX / transients off the beat: {h['sfx']['per_10s']:.1f} per 10 s")
    sl = h["silences"]
    out.append(f"- {'Drop-outs' if sl['kind'] == 'dropout' else 'Pauses'}: {len(sl['events'])} ({sl['per_30s']:.1f} per 30 s)"
               + (" at " + ", ".join(f"{a:.1f} s ({b:.2f})" for a, b in sl["events"][:6]) if sl["events"] else ""))
    e = h.get("energy") or {}
    if e.get("music_shape"): out.append(f"- Music energy: **{e['music_shape']}** `{spark(e.get('music_db'))}`")
    return out


def _feel(f):
    from .inspire_feel import summary_line
    if not f: return ["- (not measured)"]
    out = [f"- **Read:** {summary_line(f)}"]
    cr = f.get("cut_rate")
    if cr: out.append(f"- Cut rate: {cr['mean']:.2f} / s ({cr['mean'] * 60:.0f} / min), shape **{cr['shape']}** `{spark(cr['curve'])}`")
    cb = f.get("cut_on_beat")
    if cb: out.append(f"- Cut on beat: **{cb['ratio']:.0%}** of {cb['n']} cuts within ±{cb['tol_s'] * 1000:.0f} ms of a beat (chance at this tempo {cb['chance']:.0%})")
    h = f.get("hook") or {}
    out.append(f"- Hook: first strong change {_v(h.get('first_change_s'), ' s')}, first cut {_v(h.get('first_cut_s'), ' s')}, first on-screen text {_v(h.get('first_text_s'), ' s')}")
    it = f.get("interrupts") or {}
    if it: out.append(f"- Pattern interrupts: {it['n']} ({it['cuts']} cuts, {it['changes']} other visual changes, {it['zoom_jumps']} zoom jumps); "
                      f"median gap {_v(it.get('median_s'), ' s')}, longest {_v(it.get('max_s'), ' s')}")
    lp = f.get("loop") or {}
    if lp.get("score") is not None: out.append(f"- Loop seam: score {lp['score']:.2f} -> {'**loops** (end flows into the start)' if lp['loop'] else 'no loop'}")
    ea = f.get("energy_arc")
    if ea: out.append(f"- Energy arc (picture + sound): **{ea['shape']}** `{spark(ea['curve'])}`")
    return out


def _headlines(keys):
    g = keys.get; out = []
    pace = []
    if g("grammar.max_shot_s") is not None: pace.append(f"no shot longer than {g('grammar.max_shot_s')} s")
    if g("rhythm.cuts_per_s") is not None: pace.append(f"{g('rhythm.cuts_per_s') * 60:.0f} cuts / min")
    if g("rhythm.cut_curve"): pace.append(f"cut rate {g('rhythm.cut_curve')}")
    if g("rhythm.cut_on_beat") is not None: pace.append(f"{g('rhythm.cut_on_beat'):.0%} of cuts on the beat" + (" (music.sync: cuts)" if g("music.sync") == "cuts" else ""))
    if g("rhythm.interrupt_max_s") is not None: pace.append(f"a pattern interrupt at least every {g('rhythm.interrupt_max_s')} s")
    if pace: out.append("- **Pacing:** " + "; ".join(pace) + ".")
    snd = []
    if g("rhythm.voice") is not None: snd.append("voice-led" if g("rhythm.voice") else "music-only (no voice)")
    if g("rhythm.tempo_bpm"): snd.append(f"music around {g('rhythm.tempo_bpm'):.0f} BPM")
    if g("sound.bed_lu") is not None: snd.append(f"bed {g('sound.bed_lu')} LU under the voice")
    if g("rhythm.sfx_per_10s") is not None: snd.append(f"{g('rhythm.sfx_per_10s')} SFX hits / 10 s")
    if g("rhythm.music_energy"): snd.append(f"music energy {g('rhythm.music_energy')}")
    if snd: out.append("- **Sound:** " + "; ".join(snd) + ".")
    st = []
    if g("structure.hook_change_s") is not None: st.append(f"first visual change by {g('structure.hook_change_s')} s")
    if g("structure.first_text_s") is not None: st.append(f"text on screen by {g('structure.first_text_s')} s")
    if g("structure.loop") is not None: st.append("ends where it starts (loop)" if g("structure.loop") else "no loop")
    if g("structure.energy_arc"): st.append(f"energy arc {g('structure.energy_arc')}")
    if g("structure.duration_s"): st.append(f"about {g('structure.duration_s'):.0f} s long")
    if st: out.append("- **Structure:** " + "; ".join(st) + ".")
    return out


def write(dirp, R, labels, meta, plan, keys, dropped, refs_dir, written, aest=True):
    os.makedirs(dirp, exist_ok=True)
    L = [f"# Inspiration report", "",
         f"Written by `cves inspire` on {datetime.date.today().isoformat()} from {len(R)} reference(s) in `{refs_dir}`.",
         ("The style profile was written to `Edit/style.yaml`." if written else "Dry run: `Edit/style.yaml` was not written."),
         "Claude: open every contact sheet below, fill `aesthetic-review.md`, then summarise the mix for the user.", "",
         "## The mix", "", "| dimension | source | why | consistency |", "|---|---|---|---|"]
    for dim, p in plan.items():
        if dim == "other": continue
        L.append(f"| {dim} | {p['source']} | {p['rule']} | {'-' if p['consistency'] is None else p['consistency']} |")
    L += ["", "### What the edit should feel like", ""] + (_headlines(keys) or ["- Not enough measured to say (see the references)."])
    if dropped: L += ["", f"Below confidence, not written ({len(dropped)}): " + ", ".join(f"`{k}`" for k in dropped)]
    for i, r in enumerate(R, 1):
        lab = labels[i - 1]; m = meta.get(lab, {})
        tag = ", ".join(x for x in [f"rank {m['rank']}" if m.get("rank") else "", m.get("kind", ""), f"authority for {', '.join(m['use'])}" if m.get("use") else ""] if x)
        L += ["", f"## {i}. {lab}" + (f"  ({tag})" if tag else ""), ""]
        if m.get("notes"): L += [f"> {m['notes']}", ""]
        s = r.get("see") or {}
        if s.get("sheet"): L += [f"![contact sheet]({os.path.basename(s['sheet'])})", ""]
        L += ["**See**", ""] + _see(s) + [""]
        if r.get("kind") == "video":
            L += ["**Hear**", ""] + _hear(r.get("hear")) + ["", "**Feel**", ""] + _feel(r.get("feel"))
        else:
            L += ["(still image: look only)"]
    p = os.path.join(dirp, "REPORT.md")
    with open(p, "w", encoding="utf-8") as f: f.write("\n".join(L) + "\n")
    rv = review_stub(dirp, R, labels) if aest else None
    return p, rv


def review_stub(dirp, R, labels):
    """aesthetic-review.md: kept if it exists (Claude's notes are worth more than a fresh stub); missing refs appended"""
    from .inspire_see import summary_line
    p = os.path.join(dirp, "aesthetic-review.md"); old = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    add = []
    for r, lab in zip(R, labels):
        if f"## {lab}\n" in old: continue
        s = r.get("see") or {}
        add += [f"## {lab}", "", f"Sheet: `{os.path.basename(s['sheet'])}`" if s.get("sheet") else "Sheet: none", f"Measured: {summary_line(s)}", ""]
        add += [f"- {k}: " for k in RUBRIC] + [""]
    if not old:
        head = ["# Aesthetic review", "",
                "Claude fills this by LOOKING at each contact sheet (open the jpg). The numbers are in REPORT.md; this is the",
                "taste read they cannot give. One or two concrete lines per item: name what you see, not adjectives.", ""]
        tail = ["## Across the references", "", "- The look in one sentence: ", "- Does the per-dimension mix in REPORT.md match what you see? ",
                "- Change the mix? (`cves inspire --mix \"dim=ref,...\"` or `use:` in Inspirations/refs.yaml): ", ""]
        txt = "\n".join(head + add + tail)
    elif add:
        txt = old.rstrip("\n") + "\n\n" + "\n".join(add)
    else: return p
    with open(p, "w", encoding="utf-8") as f: f.write(txt)
    return p
