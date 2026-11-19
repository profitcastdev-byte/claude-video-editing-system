"""Import a human's edits back from the editor (control mode round trip, docs/CONTROL-MODE.md §4).

    cves import-edits [PROJECT] [--from resolve|kdenlive|fcpxml|otio] FILE [--captions edited.srt] [--dry-run]

export -> the human edits in DaVinci Resolve or Kdenlive -> import -> re-render. FILE is the edited timeline:
  resolve / fcpxml   an FCPXML (1.8-1.11) exported from Resolve (File > Export > Timeline) or our own timeline.fcpxml
  kdenlive           the saved project.kdenlive (MLT XML); its subtitle file (.srt or Kdenlive's .ass) is read too
  otio               an OpenTimelineIO .otio file
Every placed clip is matched to the layer it came from through Export/control/layers.json: by the `cves:<id>` note
(FCPXML), else by the media file path, else by a unique file name (media that was relinked or moved). layers.json also
holds the cut as it was at export (`source.segments`), so changes are measured against what the human was given.

What maps back (written to Edit/edit.yaml / Edit/selects.yaml, each with a timestamped backup):
  V2 cutaway moved / trimmed     cutaways[id].start/end (snap: false when off a segment boundary); a move also shifts
                                 the template's animation times (numbers inside the old window; every shift is listed)
  V2 cutaway deleted             removed from cutaways
  V2 end card trimmed / deleted  end_card.duration / end_card removed
  V3 chest overlay moved/deleted chest params shifted / chest entry removed
  B-roll shot moved / trimmed /  broll[k].start/end (+ snap: false off a segment boundary), a head trim moves broll[k].in
    deleted / speed changed      (in source seconds, at the shot's speed); deleted -> removed; an editor speed change
                                 multiplies broll[k].speed. V2 on the A-roll spine, V1 on voiceover / music / broll spines
  motion piece (m_*) trimmed     cutaway / chest motion pieces re-time: `at` follows a head trim past the piece's clock
                                 start and `duration` fits the new out point, so entry and exit both play
  V1 A-roll head / tail trim     selects.yaml clip in / out when the trim is at a clip's outer edge
  V1 clips deleted / reordered   selects.yaml clips removed / reordered (whole clips only)
  V1 ripple                      roto params, captions.hide, sfx.extra, aroll.snap, music.drop_cut, transitions follow
  A1-A3 volume                   music.bed_lu (music), style.sound.sfx_offset_db (sfx), both relative for voice
  A2 music moved                 music.drop_cut
  captions moved / retimed / retyped / deleted / added   captions.events (captions are then frozen from words.json)
Everything else (new media, effects, transitions, titles, speed changes, splits inside a layer, trims between tightened
segments) is listed in Edit/IMPORT-REPORT.md under "Not mapped", never silently dropped."""
import os, re, json, time, copy, shutil, difflib, urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from fractions import Fraction
import yaml


# ------------------------------------------------------------------ normalised timeline
@dataclass
class Placement:
    track: str                    # editor track label, informational ("V1", "A2", "lane 2")
    kind: str                     # video | audio
    path: str | None              # media file (absolute) or None for generators
    start: int                    # timeline frames (end exclusive)
    end: int
    src_in: int                   # source in, frames
    gain_db: float | None = None
    note: str = ""                # cves:<id> note when the editor kept it
    effects: list = field(default_factory=list)
    speed: float | None = None
    name: str = ""


@dataclass
class Cue:
    start: int
    end: int
    text: str


@dataclass
class Edited:
    fps: tuple
    placements: list
    captions: list | None         # None: the file carries no subtitles
    unmapped: list                # editor-only things (transitions, titles, compositions, compound clips)
    source: str


def _frames(sec: Fraction | float, fps) -> int:
    return int(round(Fraction(sec) * Fraction(fps[0], fps[1])))


def _url_path(u: str | None) -> str | None:
    if not u: return None
    if u.startswith("file:"):
        p = urllib.parse.unquote(urllib.parse.urlparse(u).path)
        if os.name == "nt" and re.match(r"^/[A-Za-z]:", p): p = p[1:]
        return p
    return u


# ------------------------------------------------------------------ FCPXML
def _rt(v: str | None) -> Fraction:
    """FCPXML rational time '<n>/<d>s' / '5s' / '0s' -> seconds"""
    if not v: return Fraction(0)
    v = v.strip().rstrip("s")
    if "/" in v:
        n, d = v.split("/"); return Fraction(int(n), int(d))
    return Fraction(v)


def parse_fcpxml(path: str) -> Edited:
    if os.path.isdir(path):            # .fcpxmld bundle
        path = os.path.join(path, "Info.fcpxml")
    root = ET.parse(path).getroot()
    if root.tag != "fcpxml": raise SystemExit(f"{path} is not an FCPXML file (root <{root.tag}>)")
    fmts = {f.get("id"): f for f in root.iter("format")}
    assets = {}
    for a in root.iter("asset"):
        rep = a.find("media-rep")
        src = rep.get("src") if rep is not None else a.get("src")
        assets[a.get("id")] = {"path": _url_path(src), "start": _rt(a.get("start")), "video": a.get("hasVideo") == "1",
                               "name": a.get("name", "")}
    medias = {m.get("id") for m in root.iter("media")}
    seq = root.find(".//library//sequence")
    if seq is None: seq = root.find(".//sequence")
    if seq is None: raise SystemExit(f"{path}: no <sequence> (export a timeline, not a library)")
    fd = fmts.get(seq.get("format"), {}).get("frameDuration") if seq.get("format") in fmts else None
    if not fd: raise SystemExit(f"{path}: the sequence format has no frameDuration")
    one = _rt(fd); fps = (one.denominator, one.numerator)
    tc0 = _rt(seq.get("tcStart"))
    places, unmapped, caps = [], [], []
    F = lambda s: _frames(s, fps)

    def media_of(el):
        """(asset dict, el carrying offset/start) for asset-clip / video / audio / clip"""
        if el.tag in ("asset-clip", "video", "audio"):
            return assets.get(el.get("ref")), el
        if el.tag in ("clip", "sync-clip"):
            for ch in el:
                if ch.tag in ("video", "audio") and ch.get("lane") in (None, "0"):
                    return assets.get(ch.get("ref")), ch
            for ch in el:
                if ch.tag in ("asset-clip",) and ch.get("lane") in (None, "0"):
                    return assets.get(ch.get("ref")), ch
        return None, None

    def effects_of(el):
        out = []
        for ch in el:
            if ch.tag in ("filter-video", "filter-audio"): out.append(f"{ch.tag[7:]} effect '{ch.get('name') or ch.get('ref')}'")
            elif ch.tag in ("adjust-transform", "adjust-crop", "adjust-blend", "adjust-colorConform", "adjust-stabilization",
                            "adjust-rollingShutter", "adjust-corners", "adjust-360-transform", "adjust-reorient", "adjust-orientation"):
                if ch.tag == "adjust-transform" and all(ch.get(k) in (None, d) for k, d in
                                                        (("position", "0 0"), ("scale", "1 1"), ("rotation", "0"), ("anchor", "0 0"))): continue
                if ch.tag == "adjust-blend" and ch.get("amount") in (None, "1") and ch.get("mode") in (None, "0"): continue
                out.append(ch.tag.replace("adjust-", "") + " adjustment")
        return out

    def gain_of(el):
        v = el.find("adjust-volume")
        if v is None: return None
        m = re.match(r"^\s*(-?[\d.]+)\s*dB", v.get("amount", ""))
        if v.find("param") is not None or v.find(".//keyframe") is not None:
            unmapped.append(f"volume keyframes on '{el.get('name')}' (only the static level is read)")
        return float(m.group(1)) if m else None

    def speed_of(el):
        tm = el.find("timeMap")
        if tm is not None:
            pts = [(_rt(t.get("time")), _rt(t.get("value"))) for t in tm.findall("timept")]
            if len(pts) >= 2 and pts[-1][0] != pts[0][0]:
                return float((pts[-1][1] - pts[0][1]) / (pts[-1][0] - pts[0][0]))
        cr = el.find("conform-rate")
        if cr is not None and cr.get("scaleEnabled", "1") == "1" and cr.get("srcFrameRate"):
            return None
        return None

    def walk(children, p_abs: Fraction, p_start: Fraction, lane_default: int, mode: str):
        """mode: top (the sequence spine: offsets are sequence time), seq (a secondary storyline: items play one after
        another from p_abs), anchored (connected items: offset is in the parent's local time, which starts at p_start)"""
        cursor = p_abs
        for el in children:
            tag = el.tag
            if tag not in ("asset-clip", "video", "audio", "clip", "sync-clip", "ref-clip", "mc-clip", "gap", "spine",
                           "transition", "caption", "title"):
                continue
            off, st, dur = _rt(el.get("offset")), _rt(el.get("start")), _rt(el.get("duration"))
            lane = int(el.get("lane", lane_default))
            abs_ = off if mode == "top" else cursor if mode == "seq" else p_abs + (off - p_start)
            at = f"{float(abs_ - tc0):.2f}s"
            if tag == "spine":
                walk(list(el), abs_, Fraction(0), lane, "seq")
            elif tag == "transition":
                unmapped.append(f"transition '{el.get('name', 'transition')}' at {at} (editor-only)")
                if mode == "seq": continue           # transitions overlap their neighbours; they take no storyline time
            elif tag == "caption":
                txt = " ".join(t.strip() for t in el.itertext() if t.strip())
                if txt: caps.append(Cue(F(abs_ - tc0), F(abs_ - tc0 + dur), txt))
            elif tag == "title":
                txt = " ".join(t.strip() for t in el.itertext() if t.strip())
                unmapped.append(f"title '{txt[:40] or el.get('name')}' at {at} on lane {lane} (titles are editor-only)")
            elif tag in ("ref-clip", "mc-clip"):
                unmapped.append(f"{tag} '{el.get('name')}' at {at} (compound / multicam clip: flatten it before exporting)")
            elif tag == "gap":
                walk(list(el), abs_, st, 0, "anchored")
            else:
                asset, mel = media_of(el)
                if asset is None:
                    if el.get("ref") in medias: unmapped.append(f"compound clip '{el.get('name')}' at {at} (flatten it)")
                    else: unmapped.append(f"generator '{el.get('name')}' at {at} (editor-only)")
                else:
                    src = st - asset["start"] if mel is el else _rt(mel.get("start")) + (st - _rt(mel.get("offset"))) - asset["start"]
                    note = " ".join((n.text or "") for n in el.findall("note"))
                    kind = "video" if (asset["video"] and tag != "audio") else "audio"
                    places.append(Placement(track=f"lane {lane}", kind=kind, path=asset["path"], start=F(abs_ - tc0),
                                            end=F(abs_ - tc0 + dur), src_in=F(src), gain_db=gain_of(el), note=note,
                                            effects=effects_of(el), speed=speed_of(el), name=el.get("name", "")))
                    sp_ = speed_of(el)
                    if sp_ is not None and abs(sp_ - 1) > 1e-6: places[-1].effects.append(f"speed {sp_:g}x")
                walk([c for c in el if c.get("lane") not in (None, "0") or c.tag == "spine"], abs_, st, lane, "anchored")
            if mode == "seq": cursor = abs_ + dur

    spine = seq.find("spine")
    walk(list(spine) if spine is not None else [], Fraction(0), Fraction(0), 0, "top")
    return Edited(fps=fps, placements=places, captions=caps or None, unmapped=unmapped, source=path)


# ------------------------------------------------------------------ Kdenlive / MLT
def _props(el) -> dict:
    return {p.get("name"): (p.text or "") for p in el.findall("property")}


def _mlt_time(v: str | None, fps) -> int:
    if v is None or v == "": return 0
    v = v.strip()
    if re.fullmatch(r"-?\d+", v): return int(v)
    m = re.fullmatch(r"(\d+):(\d+):(\d+)[.,](\d+)", v)
    if m:
        h, mi, s, frac = m.groups(); sec = Fraction(int(h) * 3600 + int(mi) * 60 + int(s)) + Fraction(int(frac), 10 ** len(frac))
        return _frames(sec, fps)
    m = re.fullmatch(r"(\d+):(\d+):(\d+)[:;](\d+)", v)
    if m:
        h, mi, s, f = (int(x) for x in m.groups()); return ((h * 60 + mi) * 60 + s) * round(fps[0] / fps[1]) + f
    return _frames(Fraction(v), fps)


def parse_subtitles(path: str, fps) -> list:
    txt = open(path, encoding="utf-8-sig").read()
    cues = []
    if path.lower().endswith(".ass") or "[Events]" in txt:
        fmt = None
        for ln in txt.splitlines():
            if ln.startswith("Format:") and fmt is None and "Start" in ln:
                fmt = [x.strip() for x in ln[7:].split(",")]
            elif ln.startswith("Dialogue:") and fmt:
                parts = ln[9:].split(",", len(fmt) - 1); d = dict(zip(fmt, (p.strip() for p in parts)))
                t = lambda s: _frames(Fraction(int(s.split(":")[0]) * 3600 + int(s.split(":")[1]) * 60) + Fraction(s.split(":")[2]), fps)
                text = re.sub(r"\{[^}]*\}", "", d.get("Text", "")).replace("\\N", "\n").replace("\\n", "\n").strip()
                if text: cues.append(Cue(t(d["Start"]), t(d["End"]), text))
        return sorted(cues, key=lambda c: c.start)
    for block in re.split(r"\n\s*\n", txt.replace("\r\n", "\n").strip()):
        lines = block.strip().split("\n")
        k = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if k is None: continue
        a, b = (x.strip() for x in lines[k].split("-->"))
        def srt(s):
            h, m, rest = s.split(":"); sec, ms = re.split(r"[,.]", rest)
            return _frames(Fraction(int(h) * 3600 + int(m) * 60 + int(sec)) + Fraction(int(ms), 1000), fps)
        text = "\n".join(lines[k + 1:]).strip()
        if text: cues.append(Cue(srt(a), srt(b.split()[0]), text))
    return sorted(cues, key=lambda c: c.start)


def parse_kdenlive(path: str) -> Edited:
    root = ET.parse(path).getroot()
    if root.tag != "mlt": raise SystemExit(f"{path} is not a Kdenlive / MLT project (root <{root.tag}>)")
    pf = root.find("profile")
    if pf is None: raise SystemExit(f"{path}: no <profile> (frame rate unknown)")
    fps = (int(pf.get("frame_rate_num")), int(pf.get("frame_rate_den")))
    base = root.get("root") or os.path.dirname(os.path.abspath(path))
    prod = {el.get("id"): el for el in root if el.tag in ("producer", "chain")}
    pls = {el.get("id"): el for el in root if el.tag == "playlist"}
    trs = {el.get("id"): el for el in root if el.tag == "tractor"}
    unmapped, places = [], []

    # the sequence: projectTractor -> its track producer; else the root's producer; else the last tractor
    seq = None
    for t in trs.values():
        if _props(t).get("kdenlive:projectTractor") == "1":
            tk = t.find("track"); seq = trs.get(tk.get("producer")) if tk is not None else None
    if seq is None: seq = trs.get(root.get("producer")) or (list(trs.values())[-1] if trs else None)
    if seq is None: raise SystemExit(f"{path}: no timeline tractor")
    tracks = []      # (kind, [playlist elements])
    for tk in seq.findall("track"):
        pid = tk.get("producer")
        if pid in trs:
            t = trs[pid]; pr = _props(t)
            kind = "audio" if pr.get("kdenlive:audio_track") == "1" or any(x.get("hide") == "video" for x in t.findall("track")) else "video"
            tracks.append((kind, [pls[x.get("producer")] for x in t.findall("track") if x.get("producer") in pls], pr.get("kdenlive:track_name", "")))
        elif pid in pls:
            kind = "audio" if tk.get("hide") == "video" or _props(pls[pid]).get("kdenlive:audio_track") == "1" else "video"
            tracks.append((kind, [pls[pid]], ""))
    nv = sum(1 for k, _, _ in tracks if k == "video"); na = sum(1 for k, _, _ in tracks if k == "audio")
    vi = ai = 0
    for kind, plist, tname in tracks:
        if kind == "video": vi += 1; label = f"V{vi}"
        else: label = f"A{na - ai}"; ai += 1               # Kdenlive lists audio tracks bottom-up
        label += f" ({tname})" if tname else ""
        for pl in plist:
            pos = 0
            for it in pl:
                if it.tag == "blank": pos += _mlt_time(it.get("length"), fps); continue
                if it.tag != "entry": continue
                a, b = _mlt_time(it.get("in"), fps), _mlt_time(it.get("out"), fps); n = b - a + 1
                p = prod.get(it.get("producer")); pp = _props(p) if p is not None else {}
                svc = pp.get("mlt_service", ""); res = pp.get("resource", ""); speed = None
                if svc == "timewarp" or res.split(":", 1)[0].replace(".", "").isdigit() and ":" in res:
                    sp_, _, res = res.partition(":"); speed = float(sp_) if sp_ else None
                if svc in ("color", "colour") or res in ("black", ""):
                    if res not in ("black",) and svc in ("color", "colour"): unmapped.append(f"colour clip on {label} at {pos / (fps[0] / fps[1]):.2f}s (editor-only)")
                    pos += n; continue
                if svc.startswith("kdenlivetitle") or svc == "qtext":
                    unmapped.append(f"title clip on {label} at {pos / (fps[0] / fps[1]):.2f}s (titles are editor-only)"); pos += n; continue
                if pp.get("kdenlive:producer_type") == "17" or it.get("producer") in trs:
                    unmapped.append(f"nested sequence on {label} at {pos / (fps[0] / fps[1]):.2f}s (flatten it)"); pos += n; continue
                rpath = res if os.path.isabs(res) else os.path.normpath(os.path.join(base, res))
                gain, effects = None, []
                for f in list(it.findall("filter")) + (list(p.findall("filter")) if p is not None else []):
                    fp = _props(f); s = fp.get("mlt_service", "")
                    if fp.get("internal_added") or fp.get("disable") == "1": continue
                    if s == "volume":
                        lv = fp.get("level") or fp.get("gain") or ""
                        m = re.findall(r"(-?[\d.]+)", lv.split(";")[-1].split("=")[-1])
                        if ";" in lv or "=" in lv: unmapped.append(f"volume keyframes on {os.path.basename(rpath)} (the last level is used)")
                        if m: gain = float(m[-1]) if "gain" not in fp or fp.get("level") else 20 * __import__("math").log10(max(1e-6, float(m[-1])))
                    else: effects.append(f"effect '{fp.get('kdenlive_id') or s}'")
                if speed is not None and abs(speed - 1) > 1e-6: effects.append(f"speed {speed:g}x")
                places.append(Placement(track=label, kind=kind, path=rpath, start=pos, end=pos + n, src_in=a, gain_db=gain,
                                        effects=effects, speed=speed, name=pp.get("kdenlive:clipname", os.path.basename(rpath))))
                pos += n
    for t in seq.findall("transition"):
        tp = _props(t)
        if tp.get("internal_added") or tp.get("always_active") == "1" or (t.get("id") or "").startswith("transition_"): continue
        unmapped.append(f"composition '{tp.get('kdenlive_id') or tp.get('mlt_service')}' between tracks {tp.get('a_track')} and {tp.get('b_track')} (editor-only)")
    # subtitles: the sequence's subtitlesList / avfilter.subtitles file; Kdenlive 24.08+ keeps them as .ass
    sp = _props(seq); subs = []
    try:
        subs += [d.get("file") for d in json.loads(sp.get("kdenlive:sequenceproperties.subtitlesList") or "[]")]
    except (ValueError, TypeError):
        pass
    for f in seq.findall("filter"):
        fp = _props(f)
        if fp.get("mlt_service") == "avfilter.subtitles": subs.append(fp.get("av.filename"))
    subs += [path + ".ass", path + ".srt"]
    caps = None
    for s in subs:
        if not s: continue
        # Kdenlive 24.08+ converts the .srt to .ass on open and saves edits there (the .srt is left stale): newest wins
        cands = [c for c in ([s, os.path.splitext(s)[0] + ".ass"] if s.endswith(".srt") else [s]) if os.path.isfile(c)]
        got = max(cands, key=os.path.getmtime) if cands else None
        if got:
            caps = parse_subtitles(got, fps); break
    return Edited(fps=fps, placements=places, captions=caps, unmapped=unmapped, source=path)


# ------------------------------------------------------------------ OTIO
def parse_otio(path: str) -> Edited:
    try:
        import opentimelineio as otio
    except ImportError:
        raise SystemExit("OpenTimelineIO is not installed: pip install -r setup/control/requirements-control.txt") from None
    tl = otio.adapters.read_from_file(path)
    if not isinstance(tl, otio.schema.Timeline): tl = next(x for x in tl if isinstance(x, otio.schema.Timeline))
    rate = tl.tracks[0].duration().rate if tl.tracks else 24
    fr = Fraction(rate).limit_denominator(1001); fps = (fr.numerator, fr.denominator)
    places, caps, unmapped = [], [], []
    for track in tl.tracks:
        kind = "video" if track.kind == otio.schema.TrackKind.Video else "audio"
        for item in track:
            if isinstance(item, otio.schema.Transition):
                unmapped.append(f"transition '{item.name}' on {track.name} (editor-only)"); continue
            if not isinstance(item, otio.schema.Clip): continue
            r = track.range_of_child(item); sr = item.source_range or item.available_range()
            ref = item.media_reference; p = _url_path(getattr(ref, "target_url", None))
            md = (item.metadata or {}).get("cves", {})
            places.append(Placement(track=track.name, kind=kind, path=p, start=round(r.start_time.to_frames(rate)),
                                    end=round(r.end_time_exclusive().to_frames(rate)), src_in=round(sr.start_time.to_frames(rate)),
                                    gain_db=md.get("gain_db"), note=f"cves:{md['id']}" if md.get("id") else "",
                                    effects=[f"effect '{e.name or e.effect_name}'" for e in item.effects], name=item.name))
        for m in track.markers:
            if "caption" in (m.metadata or {}).get("cves", {}):
                caps.append(Cue(round(m.marked_range.start_time.to_frames(rate)), round(m.marked_range.end_time_exclusive().to_frames(rate)), m.name))
    return Edited(fps=fps, placements=places, captions=sorted(caps, key=lambda c: c.start) or None, unmapped=unmapped, source=path)


def parse(path: str, src: str | None = None) -> Edited:
    if not os.path.exists(path): raise SystemExit(f"{path} not found")
    ext = os.path.splitext(path)[1].lower()
    src = src or {".fcpxml": "fcpxml", ".xml": "fcpxml", ".fcpxmld": "fcpxml", ".kdenlive": "kdenlive", ".mlt": "kdenlive",
                  ".otio": "otio"}.get(ext)
    if src in ("resolve", "fcpxml"): return parse_fcpxml(path)
    if src == "kdenlive": return parse_kdenlive(path)
    if src == "otio": return parse_otio(path)
    raise SystemExit(f"cannot tell the format of {path}: pass --from resolve|kdenlive|fcpxml|otio")


# ------------------------------------------------------------------ mapping helpers
NOT_TIME = {"value", "size", "n", "count_to", "max", "min", "scale", "x", "y", "w", "h", "width", "height", "opacity", "alpha", "zoom",
            "gain", "gain_db", "db", "font_size", "radius", "rotation", "angle", "decimals", "digits", "speed", "duration", "dur", "len",
            "length", "stars", "rating", "pitch", "lines", "index", "id", "max_chars", "level", "volume", "pad", "margin", "rows"}


def shift_params(obj, delta: float, lo: float, hi: float, path: str = "params", key: str = ""):
    """shift the animation times inside a template's params by delta seconds. A number counts as a time when it lies in
    [lo, hi] (the layer's old window, widened) and its key is not a known non-time key; in a [t, d] pair with d < t the
    second number is a duration. Returns (new obj, [(path, old, new)])."""
    changes = []
    def num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
    def go(o, p, k):
        if isinstance(o, dict):
            return {kk: go(vv, f"{p}.{kk}", kk) for kk, vv in o.items()}
        if isinstance(o, list):
            if len(o) == 2 and all(num(v) for v in o) and o[1] < o[0]:          # [start, duration]
                return [go(o[0], f"{p}[0]", k), o[1]]
            return [go(v, f"{p}[{i}]", k) for i, v in enumerate(o)]
        if num(o) and k.lower() not in NOT_TIME and lo <= o <= hi:
            n = round(o + delta, 3); changes.append((p, o, n)); return n
        return o
    return go(obj, path, key), changes


def _norm(t: str) -> str:
    return re.sub(r"[^\w]+", " ", t.lower()).strip()


def _sha(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def broll_entry(E, sid):
    """the edit.yaml broll: entry of shot id `sid` (an explicit `id:`, else the `b<NN>` index spines.shots gives it)"""
    track = E.get("broll") or []
    for x in track:
        if isinstance(x, dict) and str(x.get("id")) == sid: return x
    m = re.fullmatch(r"b(\d+)", sid or "")
    if m and 0 < int(m.group(1)) <= len(track):
        x = track[int(m.group(1)) - 1]
        if isinstance(x, dict) and not x.get("id"): return x
    return None


def _map_broll(E, sid, L, pl, Fr, sec, new_bounds, aroll, applied, notmapped, info):
    """one B-roll shot layer (V2 on the A-roll spine, V1 on the others) -> edit.yaml broll[k]"""
    x = broll_entry(E, sid)
    if x is None: notmapped.append(f"B-roll shot {sid} is no longer in edit.yaml broll:"); return
    if pl is None:
        E["broll"] = [y for y in E["broll"] if y is not x]; applied.append(f"B-roll `{sid}` deleted ({x.get('asset') or x.get('src')}, {x['start']}-{x['end']}s)"); return
    if (pl.start, pl.end, pl.src_in) == (L["f0"], L["f1"], L["si"]) and not (pl.speed and abs(pl.speed - 1) > 1e-6): return
    if abs(float(x["start"]) - sec(pl.start)) < .5 / Fr and abs(float(x["end"]) - sec(pl.end)) < .5 / Fr and (pl.start, pl.end) != (L["f0"], L["f1"]):
        info.append(f"B-roll `{sid}` already sits at {x['start']}-{x['end']}s in edit.yaml (imported before?): left as is"); return
    sp = float(x.get("speed", 1) or 1); head = pl.src_in - L["si"]
    if (pl.start, pl.end) != (L["f0"], L["f1"]):
        ns, ne = sec(pl.start), sec(pl.end); cs = (pl.start - pl.src_in) - (L["f0"] - L["si"])
        applied.append(f"B-roll `{sid}` {x['start']}-{x['end']}s -> {ns}-{ne}s" + (f" (moved {cs:+d} frames)" if cs else " (trim)")); x["start"], x["end"] = ns, ne
        if aroll and not (min((abs(b - pl.start) for b in new_bounds), default=1) == 0 and min((abs(b - pl.end) for b in new_bounds), default=1) == 0):
            if x.get("snap", True) is not False: x["snap"] = False; applied.append(f"B-roll `{sid}` snap: false (it no longer sits on a segment boundary)")
    if head:
        old = float(x.get("in", 0) or 0); new = round(max(0.0, old + head / Fr * sp), 3)
        applied.append(f"B-roll `{sid}` in: {old} -> {new} (head {'trimmed' if head > 0 else 'extended'} {abs(head)} frames)"); x["in"] = new
    if pl.speed and abs(pl.speed - 1) > 1e-6:
        new = round(sp * pl.speed, 4); applied.append(f"B-roll `{sid}` speed: {sp:g} -> {new:g} (editor speed {pl.speed:g}x)"); x["speed"] = new
        notmapped[:] = [n for n in notmapped if not n.startswith(f"{L['id']}: speed ")]


def _is_motion(tpl): return isinstance(tpl, str) and tpl.startswith("m_")


def _retime_motion(entry, label, L, pl, Fr, sec, applied, chest=False):
    """a motion piece whose layer was trimmed: start its clock no earlier than the new in point and fit its duration to the
    new out point (entry + exit play inside the window). chest pieces always get explicit at / duration (their slot is
    the segment, not the layer)."""
    p = entry.setdefault("params", {}); ns, ne = sec(pl.start), sec(pl.end); ch = []
    if (pl.start, pl.end) == (L["f0"], L["f1"]): return
    at = p.get("at")
    if (at is not None and at < ns - .5 / Fr) or (at is None and (chest or pl.start != L["f0"])):
        ch.append(f"at {at} -> {ns}"); p["at"] = at = ns
    at = at if at is not None else ns
    if chest or "duration" in p or pl.end != L["f1"]:
        d = round(ne - at, 3)
        if d > 0 and p.get("duration") != d: ch.append(f"duration {p.get('duration')} -> {d}"); p["duration"] = d
    if ch: applied.append(f"{label} motion piece re-timed to {ns}-{ne}s: " + ", ".join(ch))


# ------------------------------------------------------------------ the import
def import_edits(pr, file, src=None, captions=None, dry_run=False):
    from .export.layers import seconds_to_frames
    from . import style as STY
    ctl = pr.p("Export", "control"); mp = os.path.join(ctl, "layers.json")
    if not os.path.exists(mp): raise SystemExit("no Export/control/layers.json: the round trip starts with `cves export resolve|kdenlive|all`")
    man = json.load(open(mp, encoding="utf-8")); mfps = tuple(man["fps"]); Fr = mfps[0] / mfps[1]
    ed = parse(os.path.abspath(file), src)
    if tuple(ed.fps) != mfps:
        raise SystemExit(f"the edited timeline runs at {ed.fps[0]}/{ed.fps[1]} fps but the export was {mfps[0]}/{mfps[1]}: set the editor's timeline rate back and export again")
    if captions:
        ed.captions = parse_subtitles(captions, mfps)
    sec = lambda f: round(f / Fr, 4)
    E0 = pr.edit; E = copy.deepcopy(E0)
    sel_path = pr.e("selects.yaml")
    SEL0 = yaml.safe_load(open(sel_path, encoding="utf-8")) if os.path.exists(sel_path) else {}
    SEL = copy.deepcopy(SEL0)
    S = STY.load(pr)
    applied, notmapped, info = [], list(ed.unmapped), []
    snap_src = man.get("source") or {}
    if snap_src.get("edit_sha256") and os.path.exists(pr.e("edit.yaml")) and _sha(pr.e("edit.yaml")) != snap_src["edit_sha256"]:
        info.append("edit.yaml changed after the export; changes are measured against the export and applied to today's "
                    "edit.yaml. If this edit was imported before, re-export (`cves export ...`) before importing again, "
                    "or changes such as trims are applied twice (check the diff)")

    # ---- the layers as exported
    layers = []
    for c in man["clips"]:
        p = c["path"]; ap = os.path.realpath(p if os.path.isabs(p) else os.path.join(ctl, p))
        sf, ef = seconds_to_frames(c["start"], mfps), seconds_to_frames(c["end"], mfps)
        layers.append({**c, "abs": ap, "f0": sf, "f1": ef, "si": seconds_to_frames(c.get("source_in", 0.0), mfps), "gain": float(c.get("gain_db", 0) or 0)})
    by_id = {L["id"]: L for L in layers}
    by_path = {L["abs"]: L for L in layers}
    by_name = {}
    for L in layers: by_name.setdefault(os.path.basename(L["abs"]), []).append(L)

    # ---- match placements to layers
    got = {L["id"]: [] for L in layers}
    for pl in ed.placements:
        m = re.search(r"cves:(\S+)", pl.note or "")
        L = by_id.get(m.group(1)) if m else None
        if L is None and pl.path: L = by_path.get(os.path.realpath(pl.path))
        if L is None and pl.path:
            cands = by_name.get(os.path.basename(pl.path), [])
            L = cands[0] if len(cands) == 1 else None
        if L is None:
            notmapped.append(f"new media on {pl.track}: {pl.path or pl.name} at {sec(pl.start):.2f}-{sec(pl.end):.2f}s (not from this export; add it to edit.yaml as an asset/cutaway by hand)")
            continue
        if L["track"].startswith("V") and pl.kind == "audio": continue      # attached audio component of a video layer
        got[L["id"]].append(pl)
        for e in pl.effects: notmapped.append(f"{L['id']}: {e} (editor-only; not rendered by cves)")
    # merge blade splits that still play continuously
    single = {}
    for lid, pls in got.items():
        pls.sort(key=lambda p: p.start)
        merged = [pls[0]] if pls else []
        for p in pls[1:]:
            q = merged[-1]
            if p.start == q.end and p.src_in == q.src_in + (q.end - q.start) and p.gain_db == q.gain_db:
                merged[-1] = Placement(q.track, q.kind, q.path, q.start, p.end, q.src_in, q.gain_db, q.note, q.effects, q.speed, q.name)
            else: merged.append(p)
        if len(merged) > 1:
            notmapped.append(f"{lid}: used {len(merged)} times / split with a gap ({', '.join(f'{sec(p.start):.2f}-{sec(p.end):.2f}s' for p in merged)}); "
                             "cves cannot express a split layer: re-time it in edit.yaml by hand")
            single[lid] = "split"
        else: single[lid] = merged[0] if merged else None

    # ---- V1: A-roll segments -> selects.yaml + the ripple time map
    segs = snap_src.get("segments") or [dict(s) for s in pr.json("edl.json", {"segments": []})["segments"]]
    seg_by = {s["id"]: s for s in segs}
    clip_segs = {}
    for s in segs: clip_segs.setdefault(s.get("clip") or s["id"].rsplit("_", 1)[0], []).append(s["id"])
    v1 = [L for L in layers if L["track"] == "V1"]
    tmap = []                                     # (old f0, old f1, content shift frames | None if deleted)
    sel_clips = {c["id"]: c for c in (SEL.get("clips") or [])}
    deleted_segs = set()
    aroll = not any(L.get("edit_ref", "").startswith(("broll.", "gap.")) for L in v1)
    shot_layers = [L for L in v1 if L.get("edit_ref", "").startswith("broll.")]
    v1 = [L for L in v1 if not L.get("edit_ref", "").startswith(("broll.", "gap."))]     # non-aroll spines: shots map to broll:, not selects
    for L in v1:
        sid = L["edit_ref"].split(".", 1)[1] if L.get("edit_ref", "").startswith("edl.") else L["id"][2:]
        pl = single.get(L["id"]); s = seg_by.get(sid)
        if pl == "split": tmap.append((L["f0"], L["f1"], None)); continue
        if pl is None:
            deleted_segs.add(sid); tmap.append((L["f0"], L["f1"], None)); continue
        cs = (pl.start - pl.src_in) - (L["f0"] - L["si"]); tmap.append((L["f0"], L["f1"], cs))
        if s is None: notmapped.append(f"{L['id']}: segment {sid} not in the export snapshot"); continue
        cid = s.get("clip") or sid.rsplit("_", 1)[0]; group = clip_segs.get(cid, [sid])
        head = pl.src_in - L["si"]; tail = (L["si"] + L["f1"] - L["f0"]) - (pl.src_in + pl.end - pl.start)
        c = sel_clips.get(cid)
        if head:
            if group[0] == sid and c is not None:
                new = round(c["in"] + head / Fr, 3)          # relative: selects in/out are not frame-snapped like segments
                applied.append(f"selects `{cid}` in: {c['in']} -> {new} (A-roll head {'trimmed' if head > 0 else 'extended'} {abs(head)} frames on {L['id']})"); c["in"] = new
            else: notmapped.append(f"{L['id']}: head trim of {head} frames inside clip `{cid}` (between tightened segments); change selects.yaml `{cid}` or trim the pause in edl by hand")
        if tail:
            if group[-1] == sid and c is not None:
                new = round(c["out"] - tail / Fr, 3)
                applied.append(f"selects `{cid}` out: {c['out']} -> {new} (A-roll tail {'trimmed' if tail > 0 else 'extended'} {abs(tail)} frames on {L['id']})"); c["out"] = new
            else: notmapped.append(f"{L['id']}: tail trim of {tail} frames inside clip `{cid}` (between tightened segments); change selects.yaml `{cid}` by hand")
    for cid, group in clip_segs.items():
        gone = [g for g in group if g in deleted_segs]
        if not gone: continue
        if len(gone) == len(group) and cid in sel_clips:
            SEL["clips"] = [c for c in SEL["clips"] if c["id"] != cid]; applied.append(f"selects `{cid}` removed (all its A-roll on V1 was deleted)")
            for k in ("roto", "chest"):
                for r in list(E.get(k) or []):
                    segl = [r["segment"]] if isinstance(r["segment"], str) else r["segment"]
                    if set(segl) <= set(group):
                        E[k].remove(r); applied.append(f"{k} on `{','.join(segl)}` removed with its clip")
        else: notmapped.append(f"A-roll {', '.join(gone)} deleted but clip `{cid}` keeps {len(group) - len(gone)} segment(s): split `{cid}` in selects.yaml by hand")
    # reorder (whole clips)
    live = [(single[L["id"]].start, L) for L in v1 if isinstance(single.get(L["id"]), Placement)]
    order_new = []
    for _, L in sorted(live, key=lambda x: x[0]):
        cid = (seg_by.get(L["id"][2:]) or {}).get("clip") or L["id"][2:].rsplit("_", 1)[0]
        if not order_new or order_new[-1] != cid: order_new.append(cid)
    order_old = [c["id"] for c in (SEL0.get("clips") or []) if c["id"] in set(order_new)]
    if order_new != order_old and len(order_new) == len(set(order_new)) and set(order_new) <= set(sel_clips):
        rest = [c for c in SEL["clips"] if c["id"] not in set(order_new)]
        SEL["clips"] = [next(c for c in SEL["clips"] if c["id"] == i) for i in order_new] + rest
        applied.append(f"selects clips reordered: {' '.join(order_new)}")
    elif order_new != order_old:
        notmapped.append("A-roll reordered so that a clip's tightened segments are no longer together: reorder selects.yaml by hand")
    ripple = any(cs for _, _, cs in tmap if cs)

    def remap(t):
        """old cut time (s) -> new, through the V1 content shifts; None when the shot was deleted"""
        f = t * Fr
        for a, b, cs in tmap:
            if a <= f < b: return None if cs is None else round(t + cs / Fr, 3)
        last = tmap[-1] if tmap else None
        return round(t + (last[2] or 0) / Fr, 3) if last and f >= last[1] else t

    if ripple:
        for k, r in enumerate(E.get("roto") or []):
            s = seg_by.get(r["segment"]); L = by_id.get(f"a_{r['segment']}")
            if not s or not L: continue
            cs = next((c for a, b, c in tmap if a == L["f0"]), 0)
            if cs:
                r["params"], ch = shift_params(r.get("params", {}), cs / Fr, L["f0"] / Fr - .5, L["f1"] / Fr + .5)
                if ch: applied.append(f"roto.{k} ({r['segment']}) animation follows its shot ({cs:+d} frames): " + ", ".join(f"{p} {o}->{n}" for p, o, n in ch))
        cap = E.get("captions") or {}
        if cap.get("hide"):
            new = [[remap(a), remap(b)] for a, b in cap["hide"]]; new = [x for x in new if None not in x]
            if new != cap["hide"]: applied.append(f"captions.hide follows the cut: {cap['hide']} -> {new}"); cap["hide"] = new
        for x in (E.get("sfx") or {}).get("extra", []) or []:
            n = remap(x["t"])
            if n is not None and n != x["t"]: applied.append(f"sfx.extra {x['name']} {x['t']} -> {n}"); x["t"] = n
        sn = (E.get("aroll") or {}).get("snap")
        if sn:
            a, b = remap(sn["start"]), remap(sn["end"])
            if None not in (a, b) and (a, b) != (sn["start"], sn["end"]): applied.append(f"aroll.snap {sn['start']}-{sn['end']} -> {a}-{b}"); sn["start"], sn["end"] = a, b
        for tr in E.get("transitions") or []:
            n = remap(tr["t"])
            if n is not None and n != tr["t"]: applied.append(f"transition {tr['kind']} {tr['t']} -> {n}"); tr["t"] = n

    new_bounds = sorted({p.start for p in (single.get(L["id"]) for L in v1) if isinstance(p, Placement)} |
                        {p.end for p in (single.get(L["id"]) for L in v1) if isinstance(p, Placement)})

    # ---- B-roll shots on V1 (voiceover / music / broll spines)
    for L in shot_layers:
        pl = single.get(L["id"])
        if pl != "split": _map_broll(E, L["edit_ref"].split(".", 1)[1], L, pl, Fr, sec, new_bounds, False, applied, notmapped, info)

    # ---- V2 cutaways + end card, V3 chest
    for L in [L for L in layers if L["track"] in ("V2", "V3")]:
        pl = single.get(L["id"]); ref = L.get("edit_ref", "")
        if pl == "split": continue
        if ref.startswith("cutaways.") and not any(str(x.get("id")) == ref.split(".", 1)[1] for x in (E.get("cutaways") or [])) \
                and broll_entry(E, ref.split(".", 1)[1]) is not None:
            ref = "broll." + ref.split(".", 1)[1]                  # an export from before B-roll layers had their own edit_ref
        if ref.startswith("broll."):
            _map_broll(E, ref.split(".", 1)[1], L, pl, Fr, sec, new_bounds, aroll, applied, notmapped, info); continue
        if ref.startswith("cutaways."):
            cid = ref.split(".", 1)[1]; cuts = E.get("cutaways") or []
            c = next((x for x in cuts if str(x.get("id")) == cid), None)
            if c is None: notmapped.append(f"cutaway {cid} is no longer in edit.yaml"); continue
            if pl is None:
                E["cutaways"] = [x for x in cuts if x is not c]; applied.append(f"cutaway `{cid}` deleted ({c['template']}, {c['start']}-{c['end']}s)"); continue
            cs = (pl.start - pl.src_in) - (L["f0"] - L["si"])
            if (pl.start, pl.end) != (L["f0"], L["f1"]) and abs(c["start"] - sec(pl.start)) < .5 / Fr and abs(c["end"] - sec(pl.end)) < .5 / Fr:
                info.append(f"cutaway `{cid}` already sits at {c['start']}-{c['end']}s in edit.yaml (imported before?): left as is"); continue
            if (pl.start, pl.end) != (L["f0"], L["f1"]):
                ns, ne = sec(pl.start), sec(pl.end)
                applied.append(f"cutaway `{cid}` {c['start']}-{c['end']}s -> {ns}-{ne}s" + (f" (content moved {cs:+d} frames)" if cs else " (trim)"))
                c["start"], c["end"] = ns, ne
                if not (min((abs(b - pl.start) for b in new_bounds), default=1) == 0 and min((abs(b - pl.end) for b in new_bounds), default=1) == 0):
                    if c.get("snap", True): c["snap"] = False; applied.append(f"cutaway `{cid}` snap: false (it no longer sits on a segment boundary)")
            if cs:
                c["params"], ch = shift_params(c.get("params", {}), cs / Fr, L["f0"] / Fr - .5, L["f1"] / Fr + .5)
                if ch: applied.append(f"cutaway `{cid}` animation times shifted {cs / Fr:+.3f}s: " + ", ".join(f"{p} {o}->{n}" for p, o, n in ch))
            if _is_motion(c.get("template")) and (pl.end - pl.start) != (L["f1"] - L["f0"]):
                _retime_motion(c, f"cutaway `{cid}`", L, pl, Fr, sec, applied)
        elif ref == "end_card":
            if pl is None:
                if E.get("end_card"): E.pop("end_card"); applied.append("end card deleted")
                continue
            d0, d1 = L["f1"] - L["f0"], pl.end - pl.start
            if d1 != d0 and E.get("end_card"):
                applied.append(f"end_card.duration {E['end_card'].get('duration')} -> {sec(d1)}"); E["end_card"]["duration"] = sec(d1)
            if pl.start != L["f0"]: info.append(f"end card now starts at {sec(pl.start)}s (was {sec(L['f0'])}s): it always follows the A-roll on re-render")
        elif ref.startswith("chest."):
            ks = [int(x) for x in ref.split(".", 1)[1].split("+")]; ch_list = E.get("chest") or []
            if pl is None:
                for k in sorted(ks, reverse=True):
                    if k < len(ch_list): applied.append(f"chest.{k} ({ch_list[k]['template']}) deleted"); ch_list.pop(k)
                continue
            cs = (pl.start - pl.src_in) - (L["f0"] - L["si"])
            if cs:
                for k in ks:
                    if k < len(ch_list):
                        ch_list[k]["params"], ch = shift_params(ch_list[k].get("params", {}), cs / Fr, L["f0"] / Fr - .5, L["f1"] / Fr + .5)
                        if ch: applied.append(f"chest.{k} animation shifted {cs / Fr:+.3f}s: " + ", ".join(f"{p} {o}->{n}" for p, o, n in ch))
            if (pl.end - pl.start) != (L["f1"] - L["f0"]) or pl.src_in != L["si"]:
                mo = [k for k in ks if k < len(ch_list) and _is_motion(ch_list[k].get("template"))]
                for k in mo: _retime_motion(ch_list[k], f"chest.{k}", L, pl, Fr, sec, applied, chest=True)
                if len(mo) < len(ks):
                    notmapped.append(f"{L['id']}: overlay trimmed to {sec(pl.start)}-{sec(pl.end)}s; a chest graphic spans its segments: change its `out_at` / segment in edit.yaml")

    # ---- audio stems
    had_music = "music" in E
    if not isinstance(E.get("music"), dict): E["music"] = {}
    bed0 = E["music"].get("bed_lu", S.get("sound.bed_lu", -10)); sfx0 = S.get("sound.sfx_offset_db", -3)
    bed, sfxo = bed0, sfx0
    for L in [L for L in layers if L["track"] in ("A1", "A2", "A3")]:
        pl = single.get(L["id"])
        if pl == "split": continue
        if pl is None:
            if L["id"] == "music" and E["music"].get("file"):
                applied.append(f"music deleted: music.file {E['music']['file']} -> null"); E["music"]["file"] = None
            elif L["id"] == "sfx":
                E.setdefault("sfx", {}); E["sfx"]["auto"] = False; E["sfx"]["extra"] = []; applied.append("sfx stem deleted: sfx.auto false, sfx.extra []")
            else: notmapped.append(f"{L['id']} stem deleted (the voice is tied to the picture; not mapped)")
            continue
        d = round((pl.gain_db or 0) - L["gain"], 2)
        if d:
            if L["id"] == "music": bed += d
            elif L["id"] == "sfx": sfxo += d
            elif L["id"] == "voice": bed -= d; sfxo -= d; info.append(f"voice {d:+g} dB maps to music and SFX {-d:+g} dB relative (the master is loudness-normalised)")
        cs = (pl.start - pl.src_in) - (L["f0"] - L["si"])
        if cs:
            if L["id"] == "music" and E["music"].get("file"):
                dc = E["music"].get("drop_cut", 0) or 0; n = round(dc + cs / Fr, 3)
                applied.append(f"music moved {cs:+d} frames: music.drop_cut {dc} -> {n}"); E["music"]["drop_cut"] = n
            else: notmapped.append(f"{L['id']} stem moved {cs:+d} frames ({L['id']} follows the picture; not mapped)")
        elif (pl.start, pl.end) != (L["f0"], L["f1"]):
            notmapped.append(f"{L['id']} stem trimmed to {sec(pl.start)}-{sec(pl.end)}s (stems run the whole timeline; not mapped)")
    if round(bed - bed0, 2):
        applied.append(f"music level: music.bed_lu {bed0} -> {round(bed, 2)}"); E["music"]["bed_lu"] = round(bed, 2)
    if round(sfxo - sfx0, 2):
        st = E.get("style") if isinstance(E.get("style"), dict) else {}; E["style"] = st
        st.setdefault("sound", {})["sfx_offset_db"] = round(sfxo, 2); applied.append(f"SFX level: style.sound.sfx_offset_db {sfx0} -> {round(sfxo, 2)}")
    if not E["music"] and not E0.get("music"):
        if had_music: E["music"] = E0["music"]
        else: E.pop("music")

    # ---- captions
    old = man.get("captions") or []
    if ed.captions is None:
        info.append("the edited file carries no subtitles: captions unchanged (export them from the editor and pass --captions FILE.srt)")
    else:
        oc = [{"ref": c.get("ref"), "index": c["index"], "f0": seconds_to_frames(c["start"], mfps), "f1": seconds_to_frames(c["end"], mfps),
               "text": c["text"]} for c in old]
        nc = ed.captions
        sm = difflib.SequenceMatcher(a=[_norm(c["text"]) for c in oc], b=[_norm(c.text) for c in nc], autojunk=False)
        mods, dels, adds = [], [], []
        for op, a0, a1, b0, b1 in sm.get_opcodes():
            if op == "equal" or op == "replace":
                for i, j in zip(range(a0, a1), range(b0, b1)): mods.append((oc[i], nc[j]))
                dels += oc[a0 + (b1 - b0):a1] if op == "replace" and a1 - a0 > b1 - b0 else []
                adds += nc[b0 + (a1 - a0):b1] if op == "replace" and b1 - b0 > a1 - a0 else []
            elif op == "delete": dels += oc[a0:a1]
            elif op == "insert": adds += nc[b0:b1]
        mods = [(o, n) for o, n in mods if (o["f0"], o["f1"]) != (n.start, n.end) or o["text"].strip() != n.text.strip()]
        if mods or dels or adds or ripple:
            if not (mods or dels or adds): pass
            elif any(o.get("ref") is None for o, _ in mods) or any(o.get("ref") is None for o in dels):
                notmapped.append("captions changed, but layers.json predates caption refs: re-export (`cves export ... `) and edit again, or edit captions in edit.yaml")
            else:
                from .render import Timeline
                TL = Timeline(pr)
                evs = []
                for ref, (a, b, words) in enumerate(TL.caps):
                    na, nb = remap(a), remap(b)
                    if na is None or nb is None: continue
                    evs.append({"ref": ref, "start": na, "end": nb, "words": [[w, remap(t) if remap(t) is not None else na] for w, t in words]})
                byref = {e["ref"]: e for e in evs}
                for o, n in mods:
                    e = byref.get(o["ref"])
                    if e is None: continue
                    a0, a1 = o["f0"] / Fr, o["f1"] / Fr; na, nb = round(n.start / Fr, 3), round(n.end / Fr, 3)
                    if _norm(o["text"]) == _norm(n.text) and len(e["words"]) == len(n.text.split()) or _norm(o["text"]) == _norm(n.text):
                        span = max(1e-6, a1 - a0)
                        e["words"] = [[w, round(min(nb - .001, max(na, na + (t - a0) / span * (nb - na))), 3)] for w, t in
                                      [(w, TL.caps[o["ref"]][2][k][1]) for k, (w, _) in enumerate(e["words"])]]
                        if o["text"].strip() != n.text.strip():
                            ws = n.text.split(); e["words"] = [[w, e["words"][min(k, len(e["words"]) - 1)][1]] for k, w in enumerate(ws)]
                    else:
                        ws = n.text.split(); e["words"] = [[w, round(na + k * (nb - na) / max(1, len(ws)), 3)] for k, w in enumerate(ws)]
                    applied.append(f"caption {o['index']} \"{o['text']}\" {o['f0'] / Fr:.3f}-{o['f1'] / Fr:.3f}s -> "
                                   + (f"\"{n.text}\" " if o["text"].strip() != n.text.strip() else "") + f"{na:.3f}-{nb:.3f}s")
                    e["start"], e["end"] = na, nb
                for o in dels:
                    byref.pop(o["ref"], None); applied.append(f"caption {o['index']} \"{o['text']}\" deleted")
                extra = []
                for n in adds:
                    na, nb = round(n.start / Fr, 3), round(n.end / Fr, 3); ws = n.text.split()
                    extra.append({"start": na, "end": nb, "words": [[w, round(na + k * (nb - na) / max(1, len(ws)), 3)] for k, w in enumerate(ws)]})
                    applied.append(f"caption added \"{n.text}\" {na:.3f}-{nb:.3f}s")
                events = sorted([{k: v for k, v in e.items() if k != "ref"} for e in byref.values()] + extra, key=lambda e: e["start"])
                for e1, e2 in zip(events, events[1:]):
                    if e1["end"] > e2["start"] + 1e-6:
                        info.append(f"caption \"{' '.join(w for w, _ in e1['words'])}\" now overlaps the next one ({e1['end']} > {e2['start']}): the earlier one shows until the next starts")
                E.setdefault("captions", {})["events"] = events
                info.append("captions are now frozen in edit.yaml captions.events (delete that key to go back to auto captions from words.json)")

    # ---- write
    changed_edit = E != E0; changed_sel = SEL != SEL0
    ts = time.strftime("%Y%m%d-%H%M%S"); written = []
    if not dry_run:
        if changed_edit:
            shutil.copy2(pr.e("edit.yaml"), pr.e(f"edit.yaml.bak-{ts}")); _save_yaml(pr.e("edit.yaml"), E); written.append(f"Edit/edit.yaml (backup Edit/edit.yaml.bak-{ts})")
        if changed_sel:
            shutil.copy2(sel_path, pr.e(f"selects.yaml.bak-{ts}")); _save_yaml(sel_path, SEL); written.append(f"Edit/selects.yaml (backup Edit/selects.yaml.bak-{ts})")
    steps = []
    if changed_sel: steps += ["cves select", "cves prep"]
    if changed_edit or changed_sel: steps += ["cves plan", "cves render", "cves mix", "cves encode", "cves qc"]
    if (changed_edit or changed_sel) and not changed_sel:
        ids = sorted({re.search(r"`([^`]+)`", a).group(1) for a in applied if a.startswith("cutaway `")})
        if ids: steps.append(f"cves control update --only {','.join(ids)},captions   (layers only, if you keep editing in the editor)")
    report = _report(pr, file, ed, applied, notmapped, info, written, steps, dry_run, E0, E, SEL0, SEL)
    if not dry_run or True:
        open(pr.e("IMPORT-REPORT.md"), "w", encoding="utf-8").write(report)
    summ = (f"{'dry run: ' if dry_run else ''}{len(applied)} change(s) mapped, {len(notmapped)} not mapped"
            + (f"; wrote {', '.join(written)}" if written else "") + f"; report -> {pr.e('IMPORT-REPORT.md')}")
    return {"summary": summ, "applied": applied, "not_mapped": notmapped, "info": info, "edit": E, "selects": SEL, "written": written}


def _save_yaml(path, data):
    head = []
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            if ln.startswith("#"): head.append(ln)
            else: break
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(head); yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=140)


def _report(pr, file, ed, applied, notmapped, info, written, steps, dry_run, E0, E, SEL0, SEL):
    L = [f"# Import report", "", f"- edited file: `{file}` ({os.path.basename(ed.source)}, {ed.fps[0]}/{ed.fps[1]} fps)",
         f"- imported: {time.strftime('%Y-%m-%d %H:%M:%S')}" + ("  **(dry run: nothing written)**" if dry_run else ""),
         f"- clips read: {len(ed.placements)}; captions read: {'none' if ed.captions is None else len(ed.captions)}", ""]
    L += ["## Applied to edit.yaml / selects.yaml", ""] + ([f"- {a}" for a in applied] or ["- nothing: the timeline matches the export"]) + [""]
    L += ["## Not mapped (still only in the editor)", ""] + ([f"- {n}" for n in notmapped] or ["- nothing"]) + [""]
    if info: L += ["## Notes", ""] + [f"- {i}" for i in info] + [""]
    if written: L += ["## Written", ""] + [f"- {w}" for w in written] + [""]
    if steps: L += ["## Next", "", "```"] + steps + ["```", ""]
    diff = list(difflib.unified_diff(yaml.safe_dump(E0, sort_keys=False, allow_unicode=True, width=140).splitlines(),
                                     yaml.safe_dump(E, sort_keys=False, allow_unicode=True, width=140).splitlines(),
                                     "edit.yaml (before)", "edit.yaml (after)", lineterm="", n=1))
    diff += list(difflib.unified_diff(yaml.safe_dump(SEL0, sort_keys=False, allow_unicode=True).splitlines(),
                                      yaml.safe_dump(SEL, sort_keys=False, allow_unicode=True).splitlines(),
                                      "selects.yaml (before)", "selects.yaml (after)", lineterm="", n=1))
    if diff: L += ["## Diff", "", "```diff"] + diff + ["```", ""]
    L += ["Comments in edit.yaml / selects.yaml are not kept by the rewrite (except a leading comment block); the backup has them."]
    return "\n".join(L) + "\n"
