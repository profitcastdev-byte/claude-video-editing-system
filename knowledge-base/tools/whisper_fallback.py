"""Fallback when YouTube caption download is rate-limited (HTTP 429): download audio only and transcribe locally
with whisper.cpp large-v3-turbo. usage: python tools/whisper_fallback.py 1.7 1.8 ..."""
import json, os, re, subprocess, sys, glob
M = json.load(open("manifest.json")); R = json.load(open("resolved.json"))
V = {v["id"]: (m, v) for m in M for v in m["videos"]}
WM = os.path.expanduser("~/.cache/whisper-cpp/ggml-large-v3-turbo-q5_0.bin")
for key in sys.argv[1:]:
    m, v = V[key]; r = R[key]; tmp = f"/private/tmp/claude-501/kbw/{key}"; os.makedirs(tmp, exist_ok=True)
    subprocess.run(["yt-dlp", "--no-warnings", "-q", "-f", "bestaudio", "-x", "--audio-format", "wav", "-o", f"{tmp}/a.%(ext)s", r["url"]], check=False)
    meta = json.loads(subprocess.run(["yt-dlp", "--no-warnings", "-J", "--skip-download", r["url"]], capture_output=True, text=True).stdout or "{}")
    src = glob.glob(f"{tmp}/a.*")
    if not src: print(key, "AUDIO FAILED"); continue
    subprocess.run(["/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg", "-v", "error", "-y", "-i", src[0], "-ar", "16000", "-ac", "1", f"{tmp}/a16.wav"], check=True)
    subprocess.run(["whisper-cli", "-m", WM, "-f", f"{tmp}/a16.wav", "-l", "en", "-oj", "-of", f"{tmp}/t"], capture_output=True)
    segs = json.load(open(f"{tmp}/t.json"))["transcription"]; out, last = [], -99
    for s in segs:
        t = s["offsets"]["from"] // 1000
        if t // 30 != last // 30: out.append(f"\n[{t // 60:02d}:{t % 60:02d}] "); last = t
        out.append(s["text"].strip() + " ")
    txt = re.sub(r"[ \t]+", " ", "".join(out)).strip()
    d = f"transcripts/{m['n']} {m['name'].split(' (')[0]}"; base = f"{d}/{key} " + re.sub(r"[^\w\- ]", "", v["title"])[:70].strip()
    open(base + ".txt", "w").write(f"TITLE: {meta.get('title')}\nCHANNEL: {meta.get('channel')}\nURL: {r['url']}\nDURATION: {meta.get('duration')} s\n"
        f"CURRICULUM ENTRY: {key} {v['title']} — {v['channel']}\nRESOLVED BY: {r['how']} ({r.get('note', '')}); transcript by local Whisper (captions rate-limited)\n\n" + txt)
    r.update({"title": meta.get("title"), "channel": meta.get("channel"), "words": len(txt.split()), "transcript": "whisper"})
    json.dump(R, open("resolved.json", "w"), indent=1); print(key, "ok", len(txt.split()), "words")
