"""Resolve every curriculum entry to a real video and save its full transcript.
usage (from Knowledge Base/):  python tools/fetch_transcripts.py
 - watch URLs are used as-is; search links are resolved with yt-dlp ytsearch8, picking the candidate whose channel
   matches the curriculum's named channel (fuzzy) and whose title is closest; weak matches are flagged.
 - subtitles: manual English first, else auto-captions; VTT is de-duplicated into clean prose with [mm:ss] markers.
Writes transcripts/<module>/<id> <title>.txt and resolved.json (what was actually fetched, with match confidence)."""
import json, os, re, subprocess, time, difflib, glob, shutil
from concurrent.futures import ThreadPoolExecutor
YT = ["yt-dlp", "--no-warnings", "--quiet"]
M = json.load(open("manifest.json"))
RES = json.load(open("resolved.json")) if os.path.exists("resolved.json") else {}

def norm(s): return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
def sim(a, b): return difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio()

def resolve(v):
    if not v["search"]:
        if "youtube.com/watch" in v["url"]:
            return {"url": v["url"], "how": "direct"}
        # non-YouTube page (e.g. Envato Tuts+): find the same talk on YouTube
        q = f"{v['title']} {v['channel']}"
    else:
        q = v["search"]
    out = subprocess.run(YT + ["--flat-playlist", "-J", f"ytsearch8:{q}"], capture_output=True, text=True, timeout=120).stdout
    ents = json.loads(out).get("entries", []) if out else []
    best, score = None, -1
    for e in ents:
        ch = e.get("channel") or e.get("uploader") or ""
        chs = max(sim(ch, c) for c in v["channel"].split("/"))
        s = .55 * sim(e.get("title"), v["title"]) + .45 * chs
        if s > score: best, score = e, s
    if not best: return {"url": None, "how": "not found", "query": q}
    return {"url": f"https://www.youtube.com/watch?v={best['id']}", "how": "search", "query": q, "score": round(score, 2),
            "found_title": best.get("title"), "found_channel": best.get("channel") or best.get("uploader"),
            "flag": score < .55}

def vtt_to_text(path):
    lines, last, out = open(path, encoding="utf-8", errors="ignore").read().splitlines(), "", []
    stamp = None
    for ln in lines:
        m = re.match(r"(\d\d):(\d\d):(\d\d)\.\d+ -->", ln)
        if m: stamp = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]); continue
        if not ln.strip() or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or ln.strip().isdigit(): continue
        t = re.sub(r"<[^>]+>", "", ln).replace("&nbsp;", " ").replace("&amp;", "&").strip()
        if not t or t == last: continue
        if last and t.startswith(last): t = t[len(last):].strip()
        if not t: continue
        if stamp is not None and (not out or stamp // 30 != out[-1][0] // 30): out.append((stamp, f"\n[{stamp // 60:02d}:{stamp % 60:02d}] "))
        out.append((stamp or 0, t + " ")); last = re.sub(r"<[^>]+>", "", ln).strip()
    return re.sub(r"[ \t]+", " ", "".join(x for _, x in out)).strip()

def fetch(mod, v):
    key = v["id"]
    r = RES.get(key) or resolve(v)
    RES[key] = r
    if not r.get("url"): return key, "UNRESOLVED"
    d = f"transcripts/{mod['n']} {mod['name'].split(' (')[0]}"; os.makedirs(d, exist_ok=True)
    base = f"{d}/{key} " + re.sub(r"[^\w\- ]", "", v["title"])[:70].strip()
    if os.path.exists(base + ".txt") and os.path.getsize(base + ".txt") > 500: return key, "cached"
    tmp = f"/private/tmp/claude-501/kb/{key}"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)   # fresh dir: stale subs from a replaced video must never be reused
    for attempt in range(4):
        info = subprocess.run(YT + ["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en,en-US,en-GB,en-orig,en.*",
                                    "--sub-format", "vtt", "--print-json", "-o", f"{tmp}/s.%(ext)s", r["url"]], capture_output=True, text=True, timeout=300)
        subs = sorted(glob.glob(f"{tmp}/s*.vtt"), key=lambda p: ("orig" in p, "-" in os.path.basename(p)))
        if subs: break
        time.sleep(8 * (attempt + 1))
    if not subs: return key, "NO SUBS: " + info.stderr[-200:]
    try: meta = json.loads(info.stdout.splitlines()[0])
    except Exception: meta = {}
    manual = [p for p in subs if not re.search(r"\.en-orig|auto", p)]
    txt = vtt_to_text(subs[0])
    r.update({"title": meta.get("title"), "channel": meta.get("channel"), "duration_s": meta.get("duration"), "words": len(txt.split())})
    head = (f"TITLE: {meta.get('title')}\nCHANNEL: {meta.get('channel')}\nURL: {r['url']}\nDURATION: {meta.get('duration')} s\n"
            f"CURRICULUM ENTRY: {key} {v['title']} — {v['channel']}\nRESOLVED BY: {r['how']} (match {r.get('score', 1)})"
            f"{'  ** WEAK MATCH - check relevance **' if r.get('flag') else ''}\n\n")
    open(base + ".txt", "w").write(head + txt)
    return key, f"ok {len(txt.split())} words"

jobs = [(m, v) for m in M for v in m["videos"]]
with ThreadPoolExecutor(2) as ex:
    for key, status in ex.map(lambda a: fetch(*a), jobs):
        print(key, status, flush=True); json.dump(RES, open("resolved.json", "w"), indent=1)
json.dump(RES, open("resolved.json", "w"), indent=1)
