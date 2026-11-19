"""cves: the Claude Video Editing System CLI. Run any command inside a client project folder (or pass --project).
  cves new "<Client>" "<Video title>" --raw <file>     create the project folders + edit.yaml
  cves ingest [--steps transcribe_raw]                  raw transcript for the story step (Claude writes Edit/selects.yaml)
  cves select [--align-only]                            selects.yaml -> take alignment, tightened edl.json + clean voice (DeepFilterNet + chain)
  cves prep                                             words + plate + matte + faces (after select)
  cves story                                            print the raw transcript (Claude writes Edit/selects.yaml from it) and the current segments
  cves inspire [--refs DIR] [--dry-run] [--mix grade=refA,pacing=refB]   reference edits (Inspirations/) -> Edit/style.yaml + Edit/inspire/REPORT.md
  cves validate                                         check edit.yaml / selects.yaml / style keys (render and build run it first)
  cves assets add|list|check|todo ...                   images, B-roll, overlays, generated media -> Assets/ + provenance (docs/MEDIA.md)
  cves plan                                             first run: write a skeleton edit.yaml; then validate it (`cves templates NAME` prints its params)
  cves moodboard                                        true-replica keyframes -> Moodboard/ (user approves)
  cves render [--only c3,12.5-14.0,300-420] [--mode final|aroll|overlay]  frames + Edit/elements.jsonl
  cves control update [PROJECT] --only c3               control mode: re-render just those layers + refresh layers.json
  cves import-edits [PROJECT] [--from resolve|kdenlive|fcpxml|otio] FILE   editor changes -> edit.yaml + IMPORT-REPORT.md
  cves beats [--sync drop|cuts|full] [--apply]          music beats / downbeats / drops -> Edit/beats.json + beat-sync report
  cves mix                                              voice + music + SFX -> Edit/mix.wav + stems
  cves encode                                           single final encode -> Export/<title>.mp4
  cves qc [--fast] [--video X]                          all measurable gates -> Edit/QC-REPORT.txt (exit 1 on FAIL)
  cves qc --stage story|plan                            early gates: after `cves select` (pauses, stutters, sign-off) / after planning
  cves build [--draft] [--no-cache]                     render (incremental) + mix + encode + qc (short summary; -v for the full report);
                                                        --draft: half size, fast, not deliverable
  cves status [--json]                                  where this project is: stage, last QC, open FAILs, next command
  cves templates [NAME] [--kinds] [--json] [-v]         templates by kind; NAME: one template's doc + params
  cves deliver [--variants 4:5,1:1,cut15] [--only master] [--force-unchecked]   QC-stamped Export/vNNN/ (docs/DELIVERY.md)
  cves export resolve [--push] | kdenlive | all          control mode: layered media + layers.json + Resolve / Kdenlive project
  cves music search|download|generate|credit ...        Openverse (licence-checked, credits logged) + ElevenLabs/Magnific hand-off
  cves doctor                                           check tools, models, GPU backend, fonts
  cves learn note|rate|approve|reject|results|mine|list|show|promote|forget|study ...   self-learning (docs/LEARNING.md)
  cves critique [vNNN|master]                           review pack: contact sheet + energy timeline + CRITIQUE.md rubric
  cves review build [vNNN|master] | apply [--only F01,F03] | signoff --verdict ship|revise --notes "..." | show
                                                        render review loop: cut strips, hook, payoff, end card, audio -> findings + REVIEW.md (docs/REVIEW.md)

  cves treatments list|make|render|compare|pick ...      creative treatments as fast proxies, compared, one picked (docs/TREATMENTS.md)

  cves motion list | preview <piece> [--params JSON] [--size WxH] [--out f.png|f.mp4]   HTML motion pieces (docs/MOTION.md)

  cves sfx list|fetch|add|check ...                     the SFX bank: by category + intensity; fetch = CC0 from Openverse / Freesound (docs/SOUND.md)

  -- formats + spines (docs/FORMATS.md) --
  cves ingest                                           on a voiceover spine: tighten + transcribe the VO; music / broll: edl.json (rate, canvas)
  cves autocut [--every beats|downbeats|bars] [--bars 2] [--min-shot S] [--folder Raw] [--apply]   a broll: track cut on the music grid"""
import argparse, os, sys, json, subprocess
from . import out as OUT
OUT.quiet_env()     # before cv2 / numba load; spawned workers re-import this module and inherit the env vars

PASSTHROUGH = ("doctor", "music", "export", "assets", "learn", "motion", "sfx", "treatments")

def _project(a):
    from .project import Project
    return Project(a.project or os.getcwd())

def _peek(args):
    """(subcommand, verbose) before argparse runs: -v / --verbose belongs to cves unless the command passes flags through"""
    cmd, i = None, 0
    while i < len(args):
        x = args[i]
        if x == "--project": i += 2; continue
        if not x.startswith("-"): cmd = x; break
        i += 1
    pre = args[:i]
    v = os.environ.get("CVES_VERBOSE", "").strip() not in ("", "0") or any(x in ("-v", "--verbose") for x in pre) \
        or (cmd not in PASSTHROUGH and any(x in ("-v", "--verbose") for x in args[i + 1:]))
    return cmd, v

def _log_path(args):
    """Edit/logs/cves.log of the project this command runs in (else ~/.cves/logs/cves.log); the previous run's is kept as .prev"""
    proj = next((args[k + 1] for k, x in enumerate(args[:-1]) if x == "--project"), None) or os.getcwd()
    d = os.path.join(proj, "Edit", "logs") if os.path.isdir(os.path.join(proj, "Edit")) else os.path.join(os.path.expanduser("~"), ".cves", "logs")
    log = os.path.join(d, "cves.log")
    try:
        os.makedirs(d, exist_ok=True)
        if os.path.exists(log): os.replace(log, log + ".prev")
    except OSError: pass
    return log

def main(argv=None):
    """the CLI. Run as a program (argv None): third-party stderr noise is filtered and an exception prints one line + the
    log path (-v: everything, with tracebacks). Called with argv (tests, other code): exceptions propagate as before."""
    real = argv is None; args = list(sys.argv[1:] if real else argv)
    cmd, verbose = _peek(args)
    if not real: return _main(args, verbose)
    log = _log_path(args); filt = OUT.StderrFilter(log, verbose).start()
    try: return _main(args, verbose)
    except KeyboardInterrupt:
        print("cves: interrupted", file=sys.stderr); sys.exit(130)
    except Exception as e:
        if verbose: raise
        OUT.write_traceback(log); print(OUT.error_line(cmd, e, log), file=sys.stderr); sys.exit(2)
    finally: filt.stop()

def _main(argv, verbose=False):
    ap = argparse.ArgumentParser(prog="cves", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="client project folder (default: current folder)")
    ap.add_argument("-v", "--verbose", action="store_true", help="full reports, third-party warnings and tracebacks (also CVES_VERBOSE=1)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    _v = argparse.ArgumentParser(add_help=False); _v.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS, help="full output")
    n = sp.add_parser("new"); n.add_argument("client"); n.add_argument("title"); n.add_argument("--raw"); n.add_argument("--root")
    i = sp.add_parser("ingest"); i.add_argument("--steps", default="transcribe_raw")
    sl = sp.add_parser("select"); sl.add_argument("--align-only", action="store_true", help="print the take alignment of selects.yaml and stop (no voice, no edl.json)"); sp.add_parser("prep"); sp.add_parser("story"); sp.add_parser("plan"); sp.add_parser("moodboard")
    r = sp.add_parser("render"); r.add_argument("--only", help="comma list: cutaway / segment / roto.N / chest.N / end_card ids, 12.5-14.0 (s), 300-420 (frames)"); r.add_argument("--mode", default="final"); r.add_argument("--out")
    r.add_argument("--no-cache", action="store_true", help="re-render every frame (ignore the incremental frame cache)")
    ctl = sp.add_parser("control", help="update [PROJECT] --only <ids>: re-render just those control-mode layers + refresh layers.json")
    ctl.add_argument("action", choices=["update"]); ctl.add_argument("dir", nargs="?"); ctl.add_argument("--only", required=True)
    ie = sp.add_parser("import-edits", help="[PROJECT] FILE: map a human's Resolve/Kdenlive edits back onto edit.yaml (docs/CONTROL-MODE.md)")
    ie.add_argument("paths", nargs="+", metavar="[PROJECT] FILE"); ie.add_argument("--from", dest="src", choices=["resolve", "kdenlive", "fcpxml", "otio"])
    ie.add_argument("--captions", help="edited subtitles (.srt / .ass) when FILE has none"); ie.add_argument("--dry-run", action="store_true")
    sp.add_parser("mix"); e = sp.add_parser("encode"); e.add_argument("--out")
    q = sp.add_parser("qc", parents=[_v]); q.add_argument("--json", action="store_true", help="counts + every gate (details for FAIL / WARN) as JSON"); q.add_argument("--fast", action="store_true"); q.add_argument("--video"); q.add_argument("--stage", choices=["story", "plan"], help="early gates before rendering")
    b = sp.add_parser("build", parents=[_v]); b.add_argument("--draft", action="store_true", help="half size, fast encode, fast QC into Edit/draft/ (never deliverable)")
    b.add_argument("--no-cache", action="store_true", help="re-render every frame (ignore the incremental frame cache)")
    stt = sp.add_parser("status", parents=[_v], help="[PROJECT]: stage reached, last QC counts, open FAILs, the next command"); stt.add_argument("dir", nargs="?"); stt.add_argument("--json", action="store_true")
    dv = sp.add_parser("deliver"); dv.add_argument("--variants", help="comma list: ids from edit.yaml variants:, 4:5 / 1:1 / 16:9, cut15, or reframes|hooks|cutdowns|music|end_cards|all"); dv.add_argument("--only", choices=["master"]); dv.add_argument("--force-unchecked", action="store_true"); dv.add_argument("--video"); dv.add_argument("--keep-temp", action="store_true")
    x = sp.add_parser("export", help="resolve|kdenlive|all|selftest [--push] [--no-build] (see docs/CONTROL-MODE.md)"); x.add_argument("target", choices=["resolve", "kdenlive", "all", "selftest"]); x.add_argument("rest", nargs=argparse.REMAINDER)
    m = sp.add_parser("music", help="search | download | generate | credit (see `cves music -h`)", add_help=False); m.add_argument("rest", nargs=argparse.REMAINDER)
    bt = sp.add_parser("beats", help="music tempo / beats / downbeats / drops -> Edit/beats.json; beat sync report (docs/MUSIC.md)")
    bt.add_argument("dir", nargs="?", help="project folder (default: --project or the current folder)"); bt.add_argument("--file", help="analyse this music file instead of edit.yaml music.file")
    bt.add_argument("--sync", choices=["off", "drop", "cuts", "full"], help="sync mode for this run (default: music.sync)"); bt.add_argument("--apply", action="store_true", help="write the drop placement + beat moves into edit.yaml (backup kept)")
    bt.add_argument("--refresh", action="store_true", help="re-analyse even if beats.json is current"); bt.add_argument("--json", action="store_true")
    dr = sp.add_parser("doctor"); dr.add_argument("rest", nargs=argparse.REMAINDER); tp = sp.add_parser("templates", parents=[_v], help="[NAME] [--kinds] [--json]: templates by kind; NAME prints one template's doc + params")
    tp.add_argument("name", nargs="?"); tp.add_argument("--kinds", action="store_true", help="one line: each kind and its count"); tp.add_argument("--json", action="store_true")
    vl = sp.add_parser("validate", help="[PROJECT]: check edit.yaml, selects.yaml and style keys (types, templates, times, ids, paths)"); vl.add_argument("dir", nargs="?"); vl.add_argument("--json", action="store_true")
    isp = sp.add_parser("inspire", help="[PROJECT] [--refs DIR] [--dry-run]: measure reference edits -> Edit/style.yaml (docs/STYLE.md)"); isp.add_argument("dir", nargs="?"); isp.add_argument("--refs"); isp.add_argument("--dry-run", action="store_true"); isp.add_argument("--max-s", type=float, default=90, help="seconds analysed per reference video")
    # ---- WS B (Inspire v2): mix-and-match flags for `cves inspire` (docs/STYLE.md "How cves inspire fills it")
    isp.add_argument("--mix", help='force the source per dimension, e.g. "grade=refA,captions=refB,pacing=refC" (grade palette captions pacing sound motion structure)')
    isp.add_argument("--refresh", action="store_true", help="re-measure every reference (ignore Edit/inspire/cache)")
    isp.add_argument("--min-conf", type=float, default=.5, help="keys below this confidence are not written (default 0.5)")
    # ---- end WS B
    # ---- motion layer (WS A, docs/MOTION.md): list / preview HTML motion pieces; no project needed
    mo = sp.add_parser("motion", help="list | preview <piece> (HTML motion pieces, docs/MOTION.md)", add_help=False); mo.add_argument("rest", nargs=argparse.REMAINDER)
    # ---- end motion layer
    asx = sp.add_parser("assets", help="add | list | check | todo | resolve (media assets + provenance, docs/MEDIA.md)", add_help=False); asx.add_argument("rest", nargs=argparse.REMAINDER)
    # ---- WS E: self-learning + senior-editor review (docs/LEARNING.md) ----
    lrn = sp.add_parser("learn", help="note | rate | approve | reject | results | journal | mine | list | show | promote | forget | study (docs/LEARNING.md)", add_help=False); lrn.add_argument("rest", nargs=argparse.REMAINDER)
    crq = sp.add_parser("critique", help="[vNNN|master]: contact sheet + energy timeline + CRITIQUE.md rubric -> Edit/critique/"); crq.add_argument("which", nargs="?", default="master")
    # ---- end WS E ----
    # ---- WS F: review loop (docs/REVIEW.md) ----
    rv = sp.add_parser("review", parents=[_v], help="build [vNNN|master] | apply | signoff --verdict ship|revise --notes ... | show (render review pack + findings)")
    rv.add_argument("action", choices=["build", "apply", "signoff", "show"]); rv.add_argument("which", nargs="?", default=None, help="build: vNNN or master (default)")
    rv.add_argument("--only", help="apply: comma list of finding ids (default: every safe patch)"); rv.add_argument("--dry-run", action="store_true")
    rv.add_argument("--verdict", choices=["ship", "revise"]); rv.add_argument("--notes", default=""); rv.add_argument("--json", action="store_true")
    # ---- end WS F ----
    # ---- formats + spines (WS C, docs/FORMATS.md) ----
    ac = sp.add_parser("autocut", help="[PROJECT]: propose a broll: track whose cuts land on the music grid (Edit/beats.json)")
    ac.add_argument("dir", nargs="?"); ac.add_argument("--every", choices=["beats", "downbeats", "bars"], help="grid (default: style autocut.every)")
    ac.add_argument("--bars", type=int, help="with --every bars: cut every N bars (default: style autocut.bars)")
    ac.add_argument("--min-shot", type=float, help="skip grid points closer than this to the previous cut (s; default: style autocut.min_shot_s)")
    ac.add_argument("--folder", default="Raw", help="clips to cycle through (project-relative, default Raw)")
    ac.add_argument("--apply", action="store_true", help="write the track into edit.yaml broll: (backup kept); else print it")
    ac.add_argument("--json", action="store_true")
    # ---- end formats + spines ----
    # ---- WS G: treatments (docs/TREATMENTS.md) ----
    trt = sp.add_parser("treatments", help="list | make [NAMES] | render [NAMES] [--proxy|--full] | compare [NAMES] | pick NAME (docs/TREATMENTS.md)", add_help=False)
    trt.add_argument("rest", nargs=argparse.REMAINDER)
    # ---- end WS G ----
    # ---- WS H (senior sound, docs/SOUND.md): the SFX bank ----
    sfx_ = sp.add_parser("sfx", help="list | fetch | add | check: the SFX bank (manifest, CC0 only; docs/SOUND.md)", add_help=False); sfx_.add_argument("rest", nargs=argparse.REMAINDER)
    # ---- end WS H ----
    # ---- WS6 plan review (docs/PLAN-REVIEW.md): review-plan serves EDIT-PLAN.html; plan apply-notes; moodboard --full ----
    rpl = sp.add_parser("review-plan", help="[--port N] [--no-open] [--keep]: serve Moodboard/EDIT-PLAN.html on 127.0.0.1; Send saves Edit/plan_notes.json")
    rpl.add_argument("--port", type=int, default=8765); rpl.add_argument("--no-open", action="store_true", help="do not open the browser")
    rpl.add_argument("--keep", action="store_true", help="keep serving after Send (default: stop after the first Send)")
    sp.choices["plan"].add_argument("action", nargs="?", choices=["apply-notes"], help="apply-notes: Edit/plan_notes.json -> edit.yaml + plan_notes.pending.md")
    sp.choices["plan"].add_argument("--force", action="store_true", help="apply-notes: apply notes that were already applied")
    sp.choices["plan"].add_argument("--dry-run", action="store_true", help="apply-notes: report only")
    sp.choices["moodboard"].add_argument("--full", action="store_true", help="re-render every keyframe (default: only shots changed since the last round)")
    # ---- end WS6 plan review ----
    a, extra = ap.parse_known_args(argv)
    if extra:   # flags meant for the tool behind doctor / music / export pass straight through
        if a.cmd in PASSTHROUGH: a.rest = list(getattr(a, "rest", [])) + extra
        else: ap.error("unrecognized arguments: " + " ".join(extra))
    a.verbose = bool(getattr(a, "verbose", False) or verbose)

    if a.cmd == "new":
        from .project import new
        d = new(a.client, a.title, a.raw, a.root); print(d); return
    if a.cmd == "doctor":
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        sys.exit(subprocess.call([sys.executable, os.path.join(root, "setup", "doctor.py")] + a.rest))   # --deep, --json
    if a.cmd == "templates":
        from . import tlist; print(tlist.show(a.name, kinds=a.kinds, as_json=a.json, verbose=a.verbose)); return
    if a.cmd == "assets":    # media registry: copy into Assets/, provenance in Edit/assets.json
        from . import assets; sys.exit(assets.main(a.rest, a.project))
    if a.cmd == "motion":    # motion layer (WS A): `cves motion list | preview ...`; --project picks the style + Brand/motion
        from . import motion; sys.exit(motion.main(list(a.rest) + (["--project", a.project] if a.project and a.rest and a.rest[0] == "preview" else [])))
    if a.cmd == "music":     # Openverse search/download (licence-checked, credits logged); ElevenLabs / Magnific hand-off
        from . import music; sys.exit(music.main(a.rest))
    if a.cmd == "sfx":       # WS H: SFX bank list / fetch (Openverse, Freesound; CC0 only) / add / check
        from . import sfx; sys.exit(sfx.main(a.rest, a.project))
    if a.cmd == "learn":     # WS E: journal notes / ratings / results; mine, promote, study (no project needed for mine/list/promote)
        from . import learn; sys.exit(learn.main(a.rest, a.project))
    if a.cmd == "treatments":    # WS G: creative treatments (proxies, comparison sheet, pick -> edit.yaml + journal)
        from . import treatments; sys.exit(treatments.main(a.rest, a.project))
    if a.cmd == "export" and a.target == "selftest":     # synthetic layers, no project needed
        from .export.__main__ import main as xmain; sys.exit(xmain(["selftest"] + list(a.rest)))
    if a.cmd == "beats" and a.dir: a.project = a.dir
    if a.cmd == "control" and a.dir: a.project = a.dir
    if a.cmd in ("validate", "inspire", "autocut", "status") and a.dir: a.project = a.dir
    if a.cmd == "import-edits" and len(a.paths) > 1: a.project = a.paths[0]
    pr = _project(a)
    if a.cmd == "status":
        from . import status as STT; st_ = STT.collect(pr)
        print(json.dumps(st_, indent=1, ensure_ascii=False) if a.json else STT.report(st_)); return
    # ---- WS6 plan review (docs/PLAN-REVIEW.md) ----
    if a.cmd == "review-plan":
        from . import planreview as PRV; sys.exit(PRV.serve(pr, a.port, open_browser=not a.no_open, keep=a.keep))
    if a.cmd == "plan" and a.action == "apply-notes":
        from . import planreview as PRV; r = PRV.apply_notes(pr, force=a.force, dry_run=a.dry_run); PRV.print_apply(r); return
    if a.cmd == "moodboard" and a.full:     # plain `cves moodboard` (incremental) runs in its usual branch below
        from .moodboard import moodboard; s, k = moodboard(pr, full=True); print(f"edit plan: {s} shots, {k} keyframes -> {pr.p('Moodboard', 'EDIT-PLAN.html')}"); return
    # ---- end WS6 plan review ----
    if a.cmd == "control":       # control mode: re-render named layers in Export/control + refresh layers.json
        from .layered import update
        for line in update(pr, a.only): print(line)
        print("relink in the editor (same paths), or rebuild the project file: `cves export resolve|kdenlive --no-build`"); return
    if a.cmd == "import-edits":  # human edits in Resolve / Kdenlive -> edit.yaml / selects.yaml + Edit/IMPORT-REPORT.md
        from .importer import import_edits; from . import learn
        E0 = pr.edit; rep = import_edits(pr, a.paths[-1], a.src, captions=a.captions, dry_run=a.dry_run); print(rep["summary"])
        learn.on_import(pr, E0, rep, a.dry_run); return     # WS E: journal what the human changed
    if a.cmd == "critique":    # WS E: senior-editor review pack
        from .critique import critique; r = critique(pr, a.which)
        print(f"review pack -> {r['dir']}\n  {r['sheet']}\n  {r['timeline']}\n  {r['md']}  (fill the rubric; log it with `cves learn rate ... --by claude`)")
        for n, u, b, s in r["budget"]:
            if s == "OVER": print(f"  restraint budget OVER: {n} {u} > {b}")
        return
    # ---- WS F: review loop (docs/REVIEW.md) ----
    if a.cmd == "review":
        from . import review as RV
        if a.action == "build":
            r = RV.build(pr, a.which); c = r["counts"]
            if a.json:
                print(json.dumps({k: r[k] for k in ("dir", "md", "round", "max_rounds", "cap_reached", "counts", "qc_fail", "findings")}
                                 | {"look": r.get("look", [])}, indent=1, ensure_ascii=False)); return
            print(f"review round {r['round']}/{r['max_rounds']} -> {r['dir']}\n  {c['high']} high, {c['med']} med, {c['low']} low; QC FAIL {r['qc_fail']}")
            qcg = [] if a.verbose else [x for x in r["findings"] if RV._qc_only(x)]
            for x in r["findings"]:
                if x["severity"] == "low" or x in qcg: continue
                print(f"  {x['id']} {x['severity']:4s} {'' if x['t'] is None else '%.2fs' % x['t']:>7s} {x['kind']:18s} {x['message'][:140]}")
            for sev, lab in (("high", "QC FAIL"), ("low", "QC WARN")):
                g_ = sorted(x["gate"] for x in qcg if (x["severity"] == "high") == (sev == "high"))
                if g_: print(f"  {lab}: {', '.join(g_)} (as in the QC summary; detail in QC-REPORT.txt)")
            look = r.get("look") or []
            print(f"  read {r['md']}, then look at {len(look)} image(s): {', '.join(os.path.relpath(p, r['dir']) for p in look) or 'index.jpg'}")
            if r["cap_reached"]: print(f"  ROUND CAP REACHED ({r['round']}/{r['max_rounds']}): last round of this loop; sign off with `cves review signoff --verdict ship|revise --notes ...`")
            ready = c["high"] == 0 and r["qc_fail"] == 0
            print("  ready to show the owner" if ready else "  NOT ready: fix (`cves review apply` for safe patches), re-render, `cves review build` again")
        elif a.action == "apply":
            r = RV.apply(pr, a.only, a.dry_run)
            for x in r["applied"]: print(f"  {'would apply' if a.dry_run else 'applied'} {x['id']} {x['kind']}: " + "; ".join(f"{c['path']} {c['old']} -> {c['new']}" for c in x["changes"]))
            if r["skipped_unsafe_or_failed"]: print(f"  not applied (unsafe: fix by hand, or failed): {', '.join(r['skipped_unsafe_or_failed'])}")
            if not r["applied"]: print("  no safe patch to apply")
            elif not a.dry_run: print(f"  edit.yaml: {r['how']}; backup {r['backup']}\n  next: `cves build`, `cves critique`, `cves review build`")
        elif a.action == "signoff":
            if not a.verdict: raise SystemExit("cves review signoff needs --verdict ship|revise and --notes \"...\"")
            r = RV.signoff(pr, a.verdict, a.notes)
            print(f"signed off round {r['round']} (loop {r['loop']}): {r['verdict']}; {len(r['open'])} open high/med finding(s) recorded in the journal")
            for w in r["warnings"]: print("  WARNING:", w)
        else: print(RV.show(pr, a.json))
        return
    # ---- end WS F ----
    if a.cmd == "validate":
        from . import schema; e_, w_ = schema.validate(pr)
        print(json.dumps({"errors": e_, "warnings": w_}, indent=1) if a.json else schema.report(e_, w_)); sys.exit(1 if e_ else 0)
    if a.cmd == "inspire":
        from . import inspire   # WS B: --mix / --refresh / --min-conf
        inspire.run(pr, refs=a.refs, dry_run=a.dry_run, max_s=a.max_s, mix=a.mix, refresh=a.refresh, min_conf=a.min_conf); return
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
        from . import ingest
        if a.align_only:
            from . import align as AL
            cl = ingest._clips(pr); AL.align_clips(pr, cl, {c["id"]: ingest.norm_src(pr, c.get("src")) for c in cl}, ingest._S(pr)); return
        n_, t_ = ingest.select(pr); print(f"{n_} segments, {t_:.2f} s; voice -> Edit/voice_final.wav")
    elif a.cmd == "prep":
        from . import ingest; ingest.run_all(pr, ["words", "plate", "matte", "faces"])
    elif a.cmd == "story":
        print(open(pr.e("raw_transcript.txt"), encoding="utf-8").read() if os.path.exists(pr.e("raw_transcript.txt")) else "run `cves ingest` first")
        from . import structure as STR, style as STY
        S_ = STY.load(pr); G_ = S_.get("grammar.beats")
        print(f"structure: {STR.preset_for(STR.beats_of(S_)) or 'custom' if G_ else STR.name_of(S_)}  beats: {STR.legend(S_)}  (X = cut)"
              f"  [style grammar.structure: {' | '.join(STR.NAMES)}; grammar.beats overrides]")
        if os.path.exists(pr.e("edl.json")):
            edl_ = pr.json("edl.json"); cl_ = {c["id"]: c for c in edl_.get("clips", [])}
            for s in edl_["segments"]:
                c_ = cl_.get(s.get("clip"), {}); b_ = c_.get("beat") or ""
                print(f"  {s['id']:20s} {s['in']:8.2f} - {s['out']:8.2f}  {b_:3s} {STR.label(b_):14s} {(c_.get('text') or '')[:60]}")
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
        n_, N = render(pr, only=only, out_dir=a.out, mode=a.mode, cache=False if a.no_cache else None); print(f"rendered {n_} of {N} frames")
    elif a.cmd == "mix":
        from .mix import mix; print(f"mix {mix(pr):.2f} s -> {pr.e('mix.wav')}")
    elif a.cmd == "encode":
        from .encode import encode; from . import learn; v = encode(pr, a.out); print(v); learn.on_build(pr, v)
    elif a.cmd == "qc":
        from . import qc
        if a.stage in ("story", "plan"):
            if a.stage == "plan": from . import schema; schema.require_valid(pr)    # the same validation `cves build` runs: a plan that passes here builds
            nf, rep = qc.run_stage(pr, a.stage); _print_qc(a, rep, None, title=f"QC ({a.stage} stage)"); sys.exit(1 if nf else 0)
        v = a.video or _latest_export(pr); nf, rep = qc.run(pr, v, fast=a.fast); _print_qc(a, rep, pr.e("QC-REPORT.txt"), video=v)
        from . import learn; learn.on_qc(pr); sys.exit(1 if nf else 0)
    elif a.cmd == "deliver":
        from .deliver import deliver
        d, m = deliver(pr, a.variants, a.only, a.force_unchecked, a.video, a.keep_temp)
        for v in m["variants"]: print(f"  {v['status']:9s} {v['id']:10s} {v.get('file') or v.get('reason', '')[:160]}")
        print(("UNCHECKED (forced) " if m.get("forced_unchecked") else "") + f"delivered {m['version']} -> {d}")
        from . import learn; learn.on_deliver(pr, m)
    elif a.cmd == "build":
        from .build import build
        v, nf, rep, T = build(pr, draft=a.draft, cache=False if a.no_cache else None)
        print(("draft (not deliverable): " if a.draft else "master: ") + str(v) + "  (" + ", ".join(f"{k} {t:.0f}s" for k, t in T.items()) + ")")
        _print_qc(a, rep, pr.e("draft", "QC-REPORT.txt") if a.draft else pr.e("QC-REPORT.txt"), video=v)
        if not a.draft:
            from . import learn; learn.on_build(pr, v); learn.on_qc(pr)
        sys.exit(1 if nf else 0)
    elif a.cmd == "export":     # control mode: layered media + layers.json, then the Resolve / Kdenlive project
        if a.target != "selftest" and "--no-build" not in a.rest:
            from .layered import build; print("layers ->", build(pr))
        from .export.__main__ import main as xmain
        rest = [r for r in a.rest if r != "--no-build"]
        if not any(not r.startswith("-") for r in rest): rest = [pr.p("Export", "control")] + rest   # the project's, not the cwd's
        sys.exit(xmain([a.target] + rest))

def _print_qc(a, rep, path, title=None, video=None):
    """full report with -v; --json: machine-readable; else the short summary (counts, FAILs, WARN one-liners, the path)"""
    if getattr(a, "json", False): print(json.dumps(OUT.qc_json(rep, path, video), indent=1, ensure_ascii=False))
    elif a.verbose: print(rep)
    else: print(OUT.qc_summary(rep, path, title=title))

def _latest_export(pr):
    vids = sorted([os.path.join(pr.p("Export"), f) for f in os.listdir(pr.p("Export")) if f.endswith(".mp4")], key=os.path.getmtime)
    if not vids: raise SystemExit("no Export/*.mp4: run `cves encode` or pass --video")
    return vids[-1]

if __name__ == "__main__":
    main()
