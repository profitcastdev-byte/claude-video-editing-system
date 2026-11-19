"""Senior-sound gates (v0.4 WS H, docs/SOUND.md). Both start as WARN-only (knowledge-base/DECISIONS.md).

SND-32  riser resolve: every automatic riser (cves.sound accents, kw `accent: riser`) peaks within 1 frame of its target
        (the payoff / hook moment). The peak is measured on the cue's own clip with the 10 ms RMS envelope SND-08 uses.
SND-33  phrase alignment: the music's drop section starts within `sound.phrase_tolerance_s` of the payoff (the drop
        moment, beats.story_moment) and on a downbeat; loop seams sit on downbeats. With `music.sync: off` the hand-set
        `music.drop_track` is the drop, provided the analysis finds a drop section within one bar of it (the difference
        is reported). The turn vs the build start is reported, not judged."""
import numpy as np


def gates_senior_sound(cx, gate):
    pr, FPS = cx.pr, cx.FPS
    from ..render import Timeline
    from .. import beats as BT
    from ..mix import all_cues, sfx_bank, load_audio
    TL = Timeline(pr)
    # ---- SND-32
    cues = all_cues(TL); find = sfx_bank(TL); SR = 48000
    ris = [c for c in cues if c[3].get("accent") == "riser"]
    if not ris: gate("SND-32", True, "no automatic risers in this edit", status="N/A")
    else:
        bad, rows = [], []
        for t, name, gain, kw in ris:
            y = load_audio(find(name))
            if kw.get("trim"): y = y[int(kw["trim"][0] * SR):int(kw["trim"][1] * SR)]
            env = np.sqrt(np.convolve(y ** 2, np.ones(480) / 480, "same")); pk = t + int(np.argmax(env)) / SR
            d = (pk - float(kw["target"])) * FPS
            rows.append(f"{name} peak {pk:.3f} s vs target {kw['target']:.3f} s ({d:+.2f} f): {kw.get('why', '')}")
            if abs(d) > 1: bad.append(rows[-1])
        gate("SND-32", not bad, f"{len(ris)} automatic riser(s): {len(ris) - len(bad)} resolve within 1 f of their target", "\n".join(bad or rows), status="WARN" if bad else "PASS")
    # ---- SND-33
    if not (TL.E.get("music") or {}).get("file"):
        gate("SND-33", True, "no music file", status="N/A"); return
    P = BT.plan(pr, TL)
    if P is None or not P.get("lay"):
        gate("SND-33", False, "no beat analysis (music.fit: none or the analysis failed): phrase alignment not measured", status="WARN"); return
    tol = float(TL.S.get("sound.phrase_tolerance_s", 0.05)); bar = float(P["lay"]["bar_s"]); st = P.get("story") or {}
    pay = st.get("payoff") or {}; notes = []
    if pay.get("at") is None:
        gate("SND-33", True, f"no payoff moment to align to ({pay.get('why', 'untagged')})", status="N/A"); return
    downs = np.asarray(P["downbeats"])
    seams = [p[0] for p in P["lay"]["pieces"][1:]]
    bad_seam = [f"loop seam at {s:.3f} s is not on a downbeat" for s in seams if not len(downs) or np.min(np.abs(downs - s)) > 2e-3]
    if P["mode"] == "off" and float((TL.E.get("music") or {}).get("drop_track") or 0) > 0:       # hand-set drop
        dc = float(P["drop"]["cut"]); err = dc - pay["at"]
        an = pay.get("section_at"); delta = (an - dc) if an is not None else None
        ok = abs(err) <= tol and delta is not None and abs(delta) <= bar
        summ = (f"hand-set drop at {dc:.3f} s vs payoff {pay['at']:.3f} s ({err * 1000:+.0f} ms); the analysed drop section starts "
                + (f"{delta * 1000:+.0f} ms from it" if delta is not None else "nowhere near it"))
        if delta is not None and abs(delta) > 1 / FPS: notes.append(f"check by ear: beats.json puts the drop {delta * 1000:+.0f} ms from music.drop_track (cves beats --sync drop to use the analysis)")
    else:
        e = pay.get("error_s")
        ok = e is not None and abs(e) <= tol and pay.get("on_downbeat", False)
        summ = (f"drop section at {pay['section_at']:.3f} s vs payoff {pay['at']:.3f} s ({e * 1000:+.0f} ms, tolerance {tol * 1000:.0f} ms)"
                + ("" if pay.get("on_downbeat") else ", not on a downbeat")) if e is not None else f"no drop section near the payoff at {pay['at']:.3f} s"
    tr = st.get("turn") or {}
    if tr.get("error_s") is not None: notes.append(f"turn {tr['at']:.3f} s: {tr['section']} starts {tr['error_s'] * 1000:+.0f} ms ({tr['error_bars']:+.2f} bar) away")
    ok = ok and not bad_seam
    gate("SND-33", ok, summ + (f"; {len(seams)} loop seam(s) on downbeats" if seams and not bad_seam else ""), "\n".join(bad_seam + notes), status="PASS" if ok else "WARN")
