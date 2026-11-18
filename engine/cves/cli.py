"""cves: the Claude Video Editing System CLI. Run any command inside a client project folder (or pass --project).
  cves new "<Client>" "<Video title>" --raw <file>     create the project folders + edit.yaml
  cves ingest [--steps transcribe_raw]                  raw transcript for the story step (Claude writes Edit/selects.yaml)
  cves select                                           selects.yaml -> tightened edl.json + clean voice (DeepFilterNet + chain)
  cves prep                                             words + plate + matte + faces (after select)
  cves story                                            print the raw transcript (Claude writes Edit/selects.yaml from it) and the current segments
  cves inspire [--refs DIR] [--dry-run]                 reference edits (Inspirations/) -> measured style profile Edit/style.yaml
  cves validate                                         check edit.yaml / selects.yaml / style keys (render and build run it first)
  cves assets add|list|check|todo ...                   images, B-roll, overlays, generated media -> Assets/ + provenance (docs/MEDIA.md)
  cves plan                                             first run: write a skeleton edit.yaml; then validate it (`cves templates` lists params)
  cves moodboard                                        true-replica keyframes -> Moodboard/ (user approves)
  cves render [--only c3,12.5-14.0,300-420] [--mode final|aroll|overlay]  frames + Edit/elements.jsonl
  cves control update [PROJECT] --only c3               control mode: re-render just those layers + refresh layers.json
  cves import-edits [PROJECT] [--from resolve|kdenlive|fcpxml|otio] FILE   editor changes -> edit.yaml + IMPORT-REPORT.md
  cves beats [--sync drop|cuts|full] [--apply]          music beats / downbeats / drops -> Edit/beats.json + beat-sync report
  cves mix                                              voice + music + SFX -> Edit/mix.wav + stems
  cves encode                                           single final encode -> Export/<title>.mp4
  cves qc [--fast] [--video X]                          all measurable gates -> Edit/QC-REPORT.txt (exit 1 on FAIL)
  cves qc --stage story|plan                            early gates: after `cves select` (pauses, stutters, sign-off) / after planning
  cves build                                            render + mix + encode + qc
  cves deliver [--variants 4:5,1:1,cut15] [--only master] [--force-unchecked]   QC-stamped Export/vNNN/ (docs/DELIVERY.md)
  cves export resolve [--push] | kdenlive | all          control mode: layered media + layers.json + Resolve / Kdenlive project
  cves music search|download|generate|credit ...        Openverse (licence-checked, credits logged) + ElevenLabs/Magnific hand-off
  cves doctor                                           check tools, models, GPU backend, fonts
  -- formats + spines (docs/FORMATS.md) --
  cves ingest                                           on a voiceover spine: tighten + transcribe the VO; music / broll: edl.json (rate, canvas)
  cves autocut [--every beats|downbeats|bars] [--bars 2] [--min-shot S] [--folder Raw] [--apply]   a broll: track cut on the music grid"""
import argparse, os, sys, json, subprocess

def _project(a):
    from .project import Project
    return Project(a.project or os.getcwd())

def main(argv=None):
    ap = argparse.ArgumentParser(prog="cves", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="client project folder (default: current folder)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("new"); n.add_argument("client"); n.add_argument("title"); n.add_argument("--raw"); n.add_argument("--root")
    i = sp.add_parser("ingest"); i.add_argument("--steps", default="transcribe_raw")
    sp.add_parser("select"); sp.add_parser("prep"); sp.add_parser("story"); sp.add_parser("plan"); sp.add_parser("moodboard")
    r = sp.add_parser("render"); r.add_argument("--only", help="comma list: cutaway / segment / roto.N / chest.N / end_card ids, 12.5-14.0 (s), 300-420 (frames)"); r.add_argument("--mode", default="final"); r.add_argument("--out")
    ctl = sp.add_parser("control", help="update [PROJECT] --only <ids>: re-render just those control-mode layers + refresh layers.json")
    ctl.add_argument("action", choices=["update"]); ctl.add_argument("dir", nargs="?"); ctl.add_argument("--only", required=True)
    ie = sp.add_parser("import-edits", help="[PROJECT] FILE: map a human's Resolve/Kdenlive edits back onto edit.yaml (docs/CONTROL-MODE.md)")
    ie.add_argument("paths", nargs="+", metavar="[PROJECT] FILE"); ie.add_argument("--from", dest="src", choices=["resolve", "kdenlive", "fcpxml", "otio"])
    ie.add_argument("--captions", help="edited subtitles (.srt / .ass) when FILE has none"); ie.add_argument("--dry-run", action="store_true")
    sp.add_parser("mix"); e = sp.add_parser("encode"); e.add_argument("--out")
    q = sp.add_parser("qc"); q.add_argument("--fast", action="store_true"); q.add_argument("--video"); q.add_argument("--stage", choices=["story", "plan"], help="early gates before rendering")
    sp.add_parser("build")
    dv = sp.add_parser("deliver"); dv.add_argument("--variants", help="comma list: ids from edit.yaml variants:, 4:5 / 1:1 / 16:9, cut15, or reframes|hooks|cutdowns|music|end_cards|all"); dv.add_argument("--only", choices=["master"]); dv.add_argument("--force-unchecked", action="store_true"); dv.add_argument("--video"); dv.add_argument("--keep-temp", action="store_true")
    x = sp.add_parser("export", help="resolve|kdenlive|all|selftest [--push] [--no-build] (see docs/CONTROL-MODE.md)"); x.add_argument("target", choices=["resolve", "kdenlive", "all", "selftest"]); x.add_argument("rest", nargs=argparse.REMAINDER)
    m = sp.add_parser("music", help="search | download | generate | credit (see `cves music -h`)", add_help=False); m.add_argument("rest", nargs=argparse.REMAINDER)
    bt = sp.add_parser("beats", help="music tempo / beats / downbeats / drops -> Edit/beats.json; beat sync report (docs/MUSIC.md)")
    bt.add_argument("dir", nargs="?", help="project folder (default: --project or the current folder)"); bt.add_argument("--file", help="analyse this music file instead of edit.yaml music.file")
    bt.add_argument("--sync", choices=["off", "drop", "cuts", "full"], help="sync mode for this run (default: music.sync)"); bt.add_argument("--apply", action="store_true", help="write the drop placement + beat moves into edit.yaml (backup kept)")
    bt.add_argument("--refresh", action="store_true", help="re-analyse even if beats.json is current"); bt.add_argument("--json", action="store_true")
    dr = sp.add_parser("doctor"); dr.add_argument("rest", nargs=argparse.REMAINDER); sp.add_parser("templates")
    vl = sp.add_parser("validate", help="[PROJECT]: check edit.yaml, selects.yaml and style keys (types, templates, times, ids, paths)"); vl.add_argument("dir", nargs="?"); vl.add_argument("--json", action="store_true")
    isp = sp.add_parser("inspire", help="[PROJECT] [--refs DIR] [--dry-run]: measure reference edits -> Edit/style.yaml (docs/STYLE.md)"); isp.add_argument("dir", nargs="?"); isp.add_argument("--refs"); isp.add_argument("--dry-run", action="store_true"); isp.add_argument("--max-s", type=float, default=90, help="seconds analysed per reference video")
    asx = sp.add_parser("assets", help="add | list | check | todo | resolve (media assets + provenance, docs/MEDIA.md)", add_help=False); asx.add_argument("rest", nargs=argparse.REMAINDER)
    # ---- formats + spines (WS C, docs/FORMATS.md) ----
    ac = sp.add_parser("autocut", help="[PROJECT]: propose a broll: track whose cuts land on the music grid (Edit/beats.json)")
    ac.add_argument("dir", nargs="?"); ac.add_argument("--every", choices=["beats", "downbeats", "bars"], help="grid (default: style autocut.every)")
    ac.add_argument("--bars", type=int, help="with --every bars: cut every N bars (default: style autocut.bars)")
    ac.add_argument("--min-shot", type=float, help="skip grid points closer than this to the previous cut (s; default: style autocut.min_shot_s)")
    ac.add_argument("--folder", default="Raw", help="clips to cycle through (project-relative, default Raw)")
    ac.add_argument("--apply", action="store_true", help="write the track into edit.yaml broll: (backup kept); else print it")
    ac.add_argument("--json", action="store_true")
    # ---- end formats + spines ----
    a, extra = ap.parse_known_args(argv)
    if extra:   # flags meant for the tool behind doctor / music / export pass straight through
        if a.cmd in ("doctor", "music", "export", "assets"): a.rest = list(getattr(a, "rest", [])) + extra
        else: ap.error("unrecognized arguments: " + " ".join(extra))

    if a.cmd == "new":
        from .project import new
        d = new(a.client, a.title, a.raw, a.root); print(d); return
    if a.cmd == "doctor":
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        sys.exit(subprocess.call([sys.executable, os.path.join(root, "setup", "doctor.py")] + a.rest))   # --deep, --json
    if a.cmd == "templates":
        from . import templates as T
        for k in sorted(T.REGISTRY): print(f"{T.KIND[k]:8s} {k:14s} {(T.REGISTRY[k][0].__doc__ or '').strip()}")
        return
    if a.cmd == "assets":    # media registry: copy into Assets/, provenance in Edit/assets.json
        from . import assets; sys.exit(assets.main(a.rest, a.project))
    if a.cmd == "music":     # Openverse search/download (licence-checked, credits logged); ElevenLabs / Magnific hand-off
        from . import music; sys.exit(music.main(a.rest))
    if a.cmd == "export" and a.target == "selftest":     # synthetic layers, no project needed
        from .export.__main__ import main as xmain; sys.exit(xmain(["selftest"] + list(a.rest)))
    if a.cmd == "beats" and a.dir: a.project = a.dir
    if a.cmd == "control" and a.dir: a.project = a.dir
    if a.cmd in ("validate", "inspire", "autocut") and a.dir: a.project = a.dir
    if a.cmd == "import-edits" and len(a.paths) > 1: a.project = a.paths[0]
    pr = _project(a)
    if a.cmd == "control":       # control mode: re-render named layers in Export/control + refresh layers.json
        from .layered import update
        for line in update(pr, a.only): print(line)
        print("relink in the editor (same paths), or rebuild the project file: `cves export resolve|kdenlive --no-build`"); return
    if a.cmd == "import-edits":  # human edits in Resolve / Kdenlive -> edit.yaml / selects.yaml + Edit/IMPORT-REPORT.md
        from .importer import import_edits
        rep = import_edits(pr, a.paths[-1], a.src, captions=a.captions, dry_run=a.dry_run); print(rep["summary"]); return
    if a.cmd == "validate":
        from . import schema; e_, w_ = schema.validate(pr)
        print(json.dumps({"errors": e_, "warnings": w_}, indent=1) if a.json else schema.report(e_, w_)); sys.exit(1 if e_ else 0)
    if a.cmd == "inspire":
        from . import inspire; inspire.run(pr, refs=a.refs, dry_run=a.dry_run, max_s=a.max_s); return
    if a.cmd == "beats":
        from . import beats; sys.exit(beats.report(pr, a.sync, a.apply, a.file, a.json, a.refresh))
    # ---- formats + spines (WS C, docs/FORMATS.md) ----
    if a.cmd in ("ingest", "select", "prep"):
        from . import spines as SP
        sp_ = SP.spine_of(pr.edit)
        if sp_ != "aroll":
            if a.cmd != "ingest": raise SystemExit(f"`cves {a.cmd}` is for A-roll: the {sp_} spine needs only `cves ingest`")
            print(json.dumps(SP.ingest_spine(pr), indent=1)); return
    if a.cmd == "autocut":
        from . import spines as SP, style as STY
        S_ = STY.load(pr)
        track, info = SP.autocut(pr, every=a.every or S_.get("autocut.every", "downbeats"), min_shot=a.min_shot if a.min_shot is not None else S_.get("autocut.min_shot_s"),
                                 folder=a.folder, bars=a.bars or S_.get("autocut.bars", 2))
        if a.apply: SP.write_broll(pr, track)
        if a.json: print(json.dumps({"broll": track, "info": info}, indent=1))
        else:
            import yaml
            print(yaml.safe_dump({"broll": track}, sort_keys=False).rstrip())
            print(f"# {info['shots']} shots on {info['every']} ({info['grid']} grid points, min shot {info['min_shot']} s)" + (" -> written to edit.yaml" if a.apply else " (--apply writes it to edit.yaml)"))
        return
    # ---- end formats + spines ----
    if a.cmd == "ingest":
        from . import ingest; ingest.run_all(pr, a.steps.split(",")); print(f"read {pr.e('raw_transcript.txt')} and write {pr.e('selects.yaml')}")
    elif a.cmd == "select":
        from . import ingest; n_, t_ = ingest.select(pr); print(f"{n_} segments, {t_:.2f} s; voice -> Edit/voice_final.wav")
    elif a.cmd == "prep":
        from . import ingest; ingest.run_all(pr, ["words", "plate", "matte", "faces"])
    elif a.cmd == "story":
        print(open(pr.e("raw_transcript.txt"), encoding="utf-8").read() if os.path.exists(pr.e("raw_transcript.txt")) else "run `cves ingest` first")
        if os.path.exists(pr.e("edl.json")):
            for s in pr.json("edl.json")["segments"]: print(f"  {s['id']:20s} {s['in']:8.2f} - {s['out']:8.2f}")
    elif a.cmd == "plan":
        from . import templates as T
        E = pr.edit
        from . import spines as SP
        if SP.spine_of(E) != "aroll" and not any(k in E for k in ("cutaways", "broll", "end_card")):   # voiceover / music / broll: no A-roll keys
            E.update({"broll": [], "captions": {"auto": True, "hide": [], "fixes": {}}, "cutaways": [], "sfx": {"auto": True, "extra": []}})
            pr.save_edit(E); print("wrote skeleton Edit/edit.yaml: fill broll: (docs/FORMATS.md; `cves autocut` on a music spine) and cutaways from `cves templates`")
        if not any(k in E for k in ("cutaways", "roto", "chest", "end_card", "broll")):      # first run: skeleton to fill in
            E.update({"edl": "edl.json", "aroll": {"zoom": {}, "creep": 0.015, "snap": None, "exposure_match": True},
                      "captions": {"auto": True, "max_chars": 34, "hide": [], "fixes": {}},
                      "cutaways": [], "roto": [], "chest": [],
                      "end_card": {"template": "logo_end", "duration": 1.25, "params": {"logo": "Brand/logo-white.png", "label": "", "pill": ""}},
                      "music": {"file": None, "drop_track": 0, "drop_cut": 0, "bed_lu": -7, "credits": ""}, "sfx": {"auto": True, "extra": []}})
            pr.save_edit(E); print("wrote skeleton Edit/edit.yaml: fill cutaways / roto / chest / end_card / music from `cves templates` (times from Edit/words.json)")
        errs = []
        for c in E.get("cutaways", []):
            if c.get("template") not in T.REGISTRY: errs.append(f"cutaway {c.get('id')}: unknown template {c.get('template')}")
        for k in ("roto", "chest"):
            for c in E.get(k, []):
                if c.get("template") not in T.REGISTRY: errs.append(f"{k} {c.get('segment')}: unknown template {c.get('template')}")
        segs = {s["id"] for s in (pr.json("edl.json", {}) or {}).get("segments", [])}
        for k in ("roto", "chest"):
            for c in E.get(k, []):
                for sid in ([c["segment"]] if isinstance(c["segment"], str) else c["segment"]):
                    if sid not in segs: errs.append(f"{k}: segment {sid} not in edl.json")
        if len(E.get("roto", [])) > 4: errs.append(f"{len(E['roto'])} roto moments (house max 4, GFX-25)")
        print("\n".join(errs) or "edit.yaml OK"); sys.exit(1 if errs else 0)
    elif a.cmd == "moodboard":
        from .moodboard import moodboard; s, k = moodboard(pr); print(f"edit plan: {s} shots, {k} keyframes -> {pr.p('Moodboard', 'EDIT-PLAN.html')}")
    elif a.cmd == "render":
        from .render import render; from . import schema; schema.require_valid(pr)     # stop on edit.yaml errors
        only = a.only or None     # ids / time ranges / frame ranges, resolved by Timeline.frames_for
        n_, N = render(pr, only=only, out_dir=a.out, mode=a.mode); print(f"rendered {n_} of {N} frames")
    elif a.cmd == "mix":
        from .mix import mix; print(f"mix {mix(pr):.2f} s -> {pr.e('mix.wav')}")
    elif a.cmd == "encode":
        from .encode import encode; print(encode(pr, a.out))
    elif a.cmd == "qc":
        from . import qc
        if a.stage in ("story", "plan"):
            nf, rep = qc.run_stage(pr, a.stage); print(rep); sys.exit(1 if nf else 0)
        v = a.video or _latest_export(pr); nf, rep = qc.run(pr, v, fast=a.fast); print(rep); sys.exit(1 if nf else 0)
    elif a.cmd == "deliver":
        from .deliver import deliver
        d, m = deliver(pr, a.variants, a.only, a.force_unchecked, a.video, a.keep_temp)
        for v in m["variants"]: print(f"  {v['status']:9s} {v['id']:10s} {v.get('file') or v.get('reason', '')[:160]}")
        print(("UNCHECKED (forced) " if m.get("forced_unchecked") else "") + f"delivered {m['version']} -> {d}")
    elif a.cmd == "build":
        from .render import render; from .mix import mix; from .encode import encode; from . import qc, schema
        schema.require_valid(pr); render(pr); mix(pr); v = encode(pr); nf, rep = qc.run(pr, v, fast=True); print(rep); sys.exit(1 if nf else 0)
    elif a.cmd == "export":     # control mode: layered media + layers.json, then the Resolve / Kdenlive project
        if a.target != "selftest" and "--no-build" not in a.rest:
            from .layered import build; print("layers ->", build(pr))
        from .export.__main__ import main as xmain
        rest = [r for r in a.rest if r != "--no-build"]
        if not any(not r.startswith("-") for r in rest): rest = [pr.p("Export", "control")] + rest   # the project's, not the cwd's
        sys.exit(xmain([a.target] + rest))

def _latest_export(pr):
    vids = sorted([os.path.join(pr.p("Export"), f) for f in os.listdir(pr.p("Export")) if f.endswith(".mp4")], key=os.path.getmtime)
    if not vids: raise SystemExit("no Export/*.mp4: run `cves encode` or pass --video")
    return vids[-1]

if __name__ == "__main__":
    main()
