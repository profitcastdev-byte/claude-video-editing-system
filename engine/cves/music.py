"""Music and SFX sourcing.

1. Openverse (https://api.openverse.org/v1/audio/, no key needed): search CC-licensed music (Jamendo, Wikimedia, ...)
   and sound effects (Freesound), filter by licence and duration, download, and append a CREDITS.md entry
   (title, creator, licence, URL) next to the file.
2. ElevenLabs / Magnific music generation: runs through the user's Claude connectors (MCP), NOT through an API key
   in this code. `cves music generate` prints a hand-off block (prompt + parameters + where to save + the credit
   command to run afterwards) that Claude executes with the connector tool, then `cves music credit` records it.

CLI (wired as `cves music ...` by cli.py through `main(argv)`; also `python -m cves.music ...`):
    cves music search "upbeat corporate" --kind music --min 30 --max 120 --license cc0,by
    cves music search whoosh --kind sfx --max 3
    cves music download <openverse-id> Music/ [--wav]
    cves music generate "warm lo-fi bed, 92 bpm, builds to a drop" --duration 45 --drop 31.1 --out Music/
    cves music credit Music/track.mp3 --provider elevenlabs --prompt "..." [--credits Music/CREDITS.md]

Licences: search defaults to CC0 + CC BY; `--license` takes any Openverse licence code (cc0, pdm, by, by-sa, by-nc, ...).
Every download records its licence in CREDITS.md; any licence other than CC0 / PDM needs the credit line in the post
caption or description, and the licence terms (share-alike, non-commercial, no-derivatives) are the user's call.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/audio/"
UA = "cves-music/0.1 (Openverse API client)"
KINDS = {"music", "sfx"}
# Openverse "length" buckets (seconds): shortest <30, short 30-120, medium 120-600, long >600
_BUCKETS = [("shortest", 0, 30), ("short", 30, 120), ("medium", 120, 600), ("long", 600, 10 ** 9)]
_EXT = {"mp32": "mp3", "mp3": "mp3", "wav": "wav", "flac": "flac", "ogg": "ogg", "oga": "ogg", "m4a": "m4a", "aiff": "aiff"}


class MusicError(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ HTTP
def _get(url: str, params: dict | None = None, timeout: int = 30) -> dict:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    headers = {"User-Agent": UA, "Accept": "application/json"}
    tok = os.environ.get("OPENVERSE_TOKEN")  # optional: registered client token = higher rate limit
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(4):  # Openverse returns sporadic 5xx for identical queries; retry with backoff
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            if e.code == 429:
                raise MusicError("Openverse rate limit hit (anonymous). Wait a minute, or set OPENVERSE_TOKEN.") from e
            body = re.sub(r"<[^>]+>|\s+", " ", e.read().decode("utf-8", "replace"))[:200]
            raise MusicError(f"Openverse HTTP {e.code}: {body.strip()}") from e
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise MusicError(f"cannot reach Openverse: {e.reason}") from e
    raise MusicError("Openverse unreachable")


def _licenses(license: str | None) -> list[str]:
    # "commercial" (Openverse's license_type word) = CC0 + PDM + CC BY; any other value is a comma list of licence codes
    if (license or "").strip().lower() in ("", "commercial", "default", "ok", "allowed"):
        license = "cc0,pdm,by"
    return [x.strip().lower() for x in license.split(",") if x.strip()]


def _buckets(min_s: float | None, max_s: float | None) -> str | None:
    lo, hi = (min_s or 0), (max_s if max_s is not None else 10 ** 9)
    names = [n for n, a, b in _BUCKETS if a < hi and b > lo]
    return ",".join(names) if names and len(names) < len(_BUCKETS) else None


def _norm(r: dict) -> dict:
    dur = r.get("duration")
    return {
        "id": r["id"],
        "title": (r.get("title") or "Untitled").strip(),
        "creator": (r.get("creator") or "Unknown").strip(),
        "creator_url": r.get("creator_url"),
        "license": (r.get("license") or "").lower(),
        "license_version": r.get("license_version") or "",
        "license_url": r.get("license_url"),
        "landing_url": r.get("foreign_landing_url"),
        "url": r.get("url"),
        "filetype": r.get("filetype"),
        "duration_s": round(dur / 1000, 2) if dur else None,
        "source": r.get("source"),
        "attribution": r.get("attribution"),
        "openverse_url": f"https://openverse.org/audio/{r['id']}",
    }


# ------------------------------------------------------------------------------------------------ search
def search(query: str, kind: str = "music", min_s: float | None = None, max_s: float | None = None,
           license: str = "cc0,by", limit: int = 20, max_pages: int = 3) -> list[dict]:
    """Search Openverse audio. kind: "music" (category=music) or "sfx" (Freesound, where Openverse leaves the
    category empty). Duration is filtered exactly on our side after the coarse server-side length buckets.
    Returns normalized records (see _norm), at most `limit`."""
    if kind not in KINDS:
        raise MusicError(f"kind must be one of {sorted(KINDS)}")
    lic = _licenses(license)
    params = {"q": query, "license": ",".join(lic), "page_size": 20, "mature": "false",
              "length": _buckets(min_s, max_s)}
    if kind == "music":
        params["category"] = "music"
    else:
        params["source"] = "freesound"
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        params["page"] = page
        data = _get(API, params)
        for raw in data.get("results", []):
            rec = _norm(raw)
            if rec["license"] not in lic or not rec["url"]:
                continue
            d = rec["duration_s"]
            if d is not None and ((min_s is not None and d < min_s) or (max_s is not None and d > max_s)):
                continue
            if d is None and (min_s is not None or max_s is not None):
                continue
            out.append(rec)
            if len(out) >= limit:
                return out
        if page >= (data.get("page_count") or 0):
            break
    return out


def get(audio_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", audio_id or ""):
        raise MusicError(f"not an Openverse audio id: {audio_id!r}")
    return _norm(_get(API + audio_id + "/"))


# ------------------------------------------------------------------------------------------------ credits
def _slug(s: str, n: int = 48) -> str:
    return (re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower() or "audio")[:n]


def _license_label(rec: dict) -> str:
    lic = rec["license"]
    if lic == "cc0":
        return f"CC0 {rec['license_version'] or '1.0'}"
    if lic == "pdm":
        return "Public Domain Mark"
    return f"CC {lic.upper()} {rec['license_version']}".strip()


def credit_entry(rec: dict, filename: str) -> str:
    must = rec["license"] not in ("cc0", "pdm")
    lines = [
        f"## {filename}",
        f"- Title: {rec['title']}",
        f"- Creator: {rec['creator']}" + (f" ({rec['creator_url']})" if rec.get("creator_url") else ""),
        f"- Licence: {_license_label(rec)}" + (f" - {rec['license_url']}" if rec.get("license_url") else ""),
        f"- Source: {rec.get('landing_url') or rec['openverse_url']} (via Openverse {rec['openverse_url']}, provider {rec.get('source')})",
        f"- Openverse id: {rec['id']}",
        f"- Downloaded: {_dt.date.today().isoformat()}",
        f"- Attribution {'REQUIRED in the post caption/description' if must else 'not required (credit appreciated)'}: "
        f"\"{rec['title']}\" by {rec['creator']}, {_license_label(rec)}",
    ]
    return "\n".join(lines) + "\n"


def _append_credit(credits_path: str, key: str, entry: str) -> None:
    existing = open(credits_path, encoding="utf-8").read() if os.path.exists(credits_path) else ""
    if key in existing:
        return  # idempotent: one entry per id / file
    with open(credits_path, "a", encoding="utf-8") as f:
        if not existing:
            f.write("# Credits\n\nEvery music / SFX file in this folder, with its licence. Keep this file with the files.\n\n")
        elif not existing.endswith("\n\n"):
            f.write("\n")
        f.write(entry + "\n")


# ------------------------------------------------------------------------------------------------ download
def _ffmpeg() -> str:
    try:
        from cves import config
        return config.get("ffmpeg")
    except Exception:
        return "ffmpeg"


def download(audio_id: str, dest: str, wav: bool = False, credits: str | None = None) -> str:
    """Download one Openverse audio file into `dest` (a folder, or a file path) and write its CREDITS.md entry
    (default: CREDITS.md in the same folder). wav=True also converts to 48 kHz 24-bit WAV and credits that file.
    Returns the path of the file to use."""
    rec = get(audio_id)
    ext = _EXT.get((rec.get("filetype") or "").lower(), "mp3")
    if os.path.isdir(dest) or dest.endswith(("/", os.sep)) or not os.path.splitext(dest)[1]:
        os.makedirs(dest, exist_ok=True)
        path = os.path.join(dest, f"{_slug(rec['title'])}-{rec['id'][:8]}.{ext}")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        path = dest
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        req = urllib.request.Request(rec["url"], headers={"User-Agent": UA})
        tmp = path + ".part"
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
        except (urllib.error.URLError, OSError) as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise MusicError(f"download failed from {rec['url']}: {e}") from e
        if os.path.getsize(tmp) < 1024:
            os.remove(tmp)
            raise MusicError(f"download from {rec['url']} returned under 1 KB; the provider may need a login")
        os.replace(tmp, path)
    use = path
    if wav and not path.lower().endswith(".wav"):
        use = os.path.splitext(path)[0] + ".wav"
        p = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", path,
                            "-ar", "48000", "-c:a", "pcm_s24le", use], capture_output=True, text=True)
        if p.returncode != 0:
            raise MusicError(f"ffmpeg conversion failed: {p.stderr.strip()[:300]}")
    credits = credits or os.path.join(os.path.dirname(os.path.abspath(use)), "CREDITS.md")
    _append_credit(credits, f"Openverse id: {rec['id']}", credit_entry(rec, os.path.basename(use)))
    return use


# ------------------------------------------------------------------------------------------------ generation hand-off
CONNECTORS = {
    "elevenlabs": {
        "name": "ElevenLabs (Claude connector)",
        "tool_hint": "the ElevenLabs connector's music-generation tool (look for a tool with 'music' in its name)",
        "licence": "ElevenLabs Music generated on the user's paid plan: commercial use per ElevenLabs terms at generation time",
    },
    "magnific": {
        "name": "Magnific (Claude connector)",
        "tool_hint": "the Magnific connector's audio_music_generate tool (audio_sfx_generate for one-off SFX)",
        "licence": "Magnific generated audio: commercial use per Magnific/Freepik terms at generation time",
    },
}


def generate_handoff(prompt: str, duration: float, provider: str = "elevenlabs", out: str = "Music",
                     bpm: int | None = None, drop: float | None = None, instrumental: bool = True) -> dict:
    """No API call happens here. Returns (and the CLI prints) what Claude must do with the connector."""
    if provider not in CONNECTORS:
        raise MusicError(f"provider must be one of {sorted(CONNECTORS)}")
    c = CONNECTORS[provider]
    full = prompt.strip()
    if instrumental and "instrumental" not in full.lower():
        full += ". Instrumental, no vocals"
    if bpm and "bpm" not in full.lower():
        full += f", {bpm} BPM"
    if drop is not None:
        full += f". Clear build, with the drop/hit landing at {drop:.2f}s"
    fname = f"{_slug(prompt, 32)}-{provider}-{_dt.date.today().strftime('%Y%m%d')}.mp3"
    target = os.path.join(out, fname)
    return {
        "action": "generate_music_via_connector",
        "connector": c["name"],
        "tool": c["tool_hint"],
        "params": {"prompt": full, "duration_seconds": round(float(duration), 2), "instrumental": instrumental,
                   **({"bpm": bpm} if bpm else {}), **({"drop_at_seconds": drop} if drop is not None else {})},
        "save_to": target,
        "then_run": f'cves music credit "{target}" --provider {provider} --prompt {json.dumps(full)}',
        "edit_yaml": {"music": {"file": target, **({"drop_track": drop} if drop is not None else {})}},
        "licence": c["licence"],
        "notes": [
            "Generate 2-3 takes, then judge them with earshot (do not claim how audio sounds without it).",
            "If the drop lands elsewhere, measure it (earshot / onset) and set music.drop_track to the real time.",
            "Never feed a client's voice or a copyrighted track into the generator as a reference.",
        ],
    }


def credit_generated(path: str, provider: str, prompt: str, credits: str | None = None) -> str:
    if provider not in CONNECTORS:
        raise MusicError(f"provider must be one of {sorted(CONNECTORS)}")
    if not os.path.isfile(path):
        raise MusicError(f"no such file: {path}")
    credits = credits or os.path.join(os.path.dirname(os.path.abspath(path)), "CREDITS.md")
    name = os.path.basename(path)
    entry = "\n".join([
        f"## {name}",
        f"- Generated with: {CONNECTORS[provider]['name']}",
        f"- Prompt: {prompt}",
        f"- Generated: {_dt.date.today().isoformat()}",
        f"- Licence: {CONNECTORS[provider]['licence']}",
        "- Attribution: not required",
    ]) + "\n"
    _append_credit(credits, f"## {name}\n", entry)
    return credits


# ------------------------------------------------------------------------------------------------ CLI
def _fmt(rec: dict) -> str:
    d = f"{rec['duration_s']:.1f}s" if rec["duration_s"] else "?"
    return f"{rec['id']}  {d:>7}  {_license_label(rec):<10}  {rec['title'][:44]:<44}  {rec['creator'][:22]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cves music", description="Openverse music/SFX search + download; connector hand-off for generation")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="search Openverse")
    s.add_argument("query")
    s.add_argument("--kind", choices=sorted(KINDS), default="music")
    s.add_argument("--min", type=float, dest="min_s")
    s.add_argument("--max", type=float, dest="max_s")
    s.add_argument("--license", default="cc0,by", help="comma list of licence codes: cc0, pdm, by, by-sa, by-nc, ... (default cc0,by)")
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--json", action="store_true")
    d = sub.add_parser("download", help="download by Openverse id and write CREDITS.md")
    d.add_argument("id")
    d.add_argument("dest", help="folder (e.g. Music/) or file path")
    d.add_argument("--wav", action="store_true", help="also convert to 48 kHz 24-bit WAV")
    d.add_argument("--credits", help="CREDITS.md path (default: next to the file)")
    g = sub.add_parser("generate", help="print the hand-off for ElevenLabs / Magnific connectors (no API key here)")
    g.add_argument("prompt")
    g.add_argument("--duration", type=float, required=True)
    g.add_argument("--provider", choices=sorted(CONNECTORS), default="elevenlabs")
    g.add_argument("--out", default="Music")
    g.add_argument("--bpm", type=int)
    g.add_argument("--drop", type=float, help="seconds into the track where the drop should land")
    g.add_argument("--vocals", action="store_true", help="allow vocals (default instrumental)")
    c = sub.add_parser("credit", help="record a connector-generated file in CREDITS.md")
    c.add_argument("file")
    c.add_argument("--provider", choices=sorted(CONNECTORS), required=True)
    c.add_argument("--prompt", required=True)
    c.add_argument("--credits")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "search":
            res = search(a.query, a.kind, a.min_s, a.max_s, a.license, a.limit)
            if a.json:
                print(json.dumps(res, indent=1))
            else:
                print(f"{len(res)} result(s) for {a.query!r} ({a.kind}, {a.license})")
                for r in res:
                    print(_fmt(r))
                if res:
                    print("\ndownload:  cves music download <id> Music/")
        elif a.cmd == "download":
            p = download(a.id, a.dest, a.wav, a.credits)
            print(p)
        elif a.cmd == "generate":
            h = generate_handoff(a.prompt, a.duration, a.provider, a.out, a.bpm, a.drop, not a.vocals)
            print("CLAUDE: music generation runs through your connector, not this CLI. Do this:")
            print(f"  1. Call {h['tool']} ({h['connector']}) with:")
            print("     " + json.dumps(h["params"]))
            print(f"  2. Save the audio to: {h['save_to']}")
            print(f"  3. Run: {h['then_run']}")
            print(f"  4. Set in edit.yaml: {json.dumps(h['edit_yaml'])}")
            print("  Notes: " + " ".join(h["notes"]))
            print("\n" + json.dumps(h, indent=1))
        elif a.cmd == "credit":
            print(credit_generated(a.file, a.provider, a.prompt, a.credits))
    except MusicError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
