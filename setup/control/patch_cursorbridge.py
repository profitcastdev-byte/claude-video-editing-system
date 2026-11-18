#!/usr/bin/env python3
"""Harden hiteshK03/davinci-resolve-mcp's in-app bridge (src/CursorBridge.py) for CVES.

Usage: python patch_cursorbridge.py <upstream CursorBridge.py> <output CursorBridge.py>

Only accepts the exact upstream file reviewed in docs/CONTROL-MODE.md (pinned commit + sha256), so a
changed upstream file fails loudly instead of being patched blindly.

What it changes (security review, docs/CONTROL-MODE.md):
  1. No CORS: removes ``Access-Control-Allow-Origin: *`` and refuses OPTIONS preflights. Upstream lets
     any web page open in your browser read and drive Resolve through 127.0.0.1:9876.
  2. Rejects any request that carries an ``Origin`` header or a cross-site ``Sec-Fetch-Site``
     (browsers always send these; the MCP server and CVES never do).
  3. Rejects any ``Host`` other than 127.0.0.1:9876 / localhost:9876 (DNS-rebinding guard).
  4. POST bodies must be ``Content-Type: application/json`` (no "simple" cross-site form posts).
  5. Adds three CVES endpoints used by ``cves export resolve --push``:
     /cves/timeline/current, /cves/append (AppendToTimeline with clipInfo: track + record frame),
     /cves/subtitles (put captions.srt on subtitle track 1 at the timeline start, verified).
Binding stays 127.0.0.1 (upstream already does that; asserted below).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

UPSTREAM_COMMIT = "f812df7ab5d376592a24fb94611473fdf3a1acb2"
UPSTREAM_SHA256 = "ed8f7e1e4fec939506f5771494a584357ad61058b2e77788600098b2ec8ff48e"
MARK = "CVES-HARDENED"

GUARD = '''
    # --- CVES hardening (setup/control/patch_cursorbridge.py) ---------------
    _CVES_HOSTS = {"127.0.0.1:%d" % PORT, "localhost:%d" % PORT}

    def _cves_refuse(self):
        """True (and a 403 sent) when the request may come from a browser or a rebinding host."""
        host = (self.headers.get("Host") or "").strip().lower()
        site = (self.headers.get("Sec-Fetch-Site") or "none").strip().lower()
        why = None
        if host not in self._CVES_HOSTS:
            why = "bad Host header"
        elif self.headers.get("Origin") is not None:
            why = "browser origin not allowed"
        elif site not in ("none", "same-origin"):
            why = "cross-site request not allowed"
        elif self.command == "POST" and not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            why = "POST must be application/json"
        if why:
            self._error(403, "CursorBridge (CVES-hardened): " + why)
            return True
        return False
'''

CVES_ROUTES = '''

# ---------------------------------------------------------------------------
# CVES endpoints (setup/control/patch_cursorbridge.py)
# ---------------------------------------------------------------------------

def _cves_set_timeline(proj, name):
    if not name:
        return proj.GetCurrentTimeline()
    for i in range(1, (safe(lambda: proj.GetTimelineCount()) or 0) + 1):
        tl = proj.GetTimelineByIndex(i)
        if tl and safe(lambda: tl.GetName()) == name:
            proj.SetCurrentTimeline(tl)
            return tl
    return None


def action_cves_timeline_current(body):
    _, proj, err = _project()
    if err:
        return err
    tl = _cves_set_timeline(proj, body.get("timelineName", ""))
    if not tl:
        return {"error": "timeline '%s' not found" % body.get("timelineName", "")}
    return {"success": True, "timeline": safe(lambda: tl.GetName()), "startFrame": safe(lambda: tl.GetStartFrame())}


def action_cves_append(body):
    """AppendToTimeline with clipInfo dicts: {clipName, startFrame, endFrame, trackIndex, recordFrame, mediaType}.
    recordFrame is relative to the timeline start (0 = first frame)."""
    _, proj, err = _project()
    if err:
        return err
    pool = proj.GetMediaPool()
    tl = _cves_set_timeline(proj, body.get("timelineName", ""))
    if not tl:
        return {"error": "No timeline"}
    infos = []
    for it in body.get("items", []):
        item = _find_pool_item(pool, it.get("clipName", ""))
        if not item:
            return {"error": "Clip '%s' not found in media pool" % it.get("clipName", "")}
        info = {"mediaPoolItem": item,
                "startFrame": int(it.get("startFrame", 0)),
                "endFrame": int(it["endFrame"]),
                "trackIndex": int(it.get("trackIndex", 1)),
                "recordFrame": int(tl.GetStartFrame()) + int(it.get("recordFrame", 0))}
        if it.get("mediaType"):
            info["mediaType"] = int(it["mediaType"])
        infos.append(info)
    if not infos:
        return {"error": "items is required"}
    out = pool.AppendToTimeline(infos)
    return {"success": bool(out), "appended": len(out or [])}


def action_cves_subtitles(body):
    """Import an .srt and place it on subtitle track 1 at the timeline start; report where it landed."""
    _, proj, err = _project()
    if err:
        return err
    pool = proj.GetMediaPool()
    tl = _cves_set_timeline(proj, body.get("timelineName", ""))
    if not tl:
        return {"error": "No timeline"}
    srt = body.get("srtPath", "")
    if not srt:
        return {"error": "srtPath is required"}
    if (safe(lambda: tl.GetTrackCount("subtitle")) or 0) < 1:
        tl.AddTrack("subtitle")
    existing = safe(lambda: tl.GetItemListInTrack("subtitle", 1)) or []
    if existing and body.get("replace", True):
        tl.DeleteClips(existing, False)
    items = pool.ImportMedia([srt])
    if not items:
        return {"error": "ImportMedia refused %s" % srt}
    item = items[0]
    start = int(tl.GetStartFrame())
    attempts = []
    frames = safe(lambda: int(str(item.GetClipProperty("Frames")).strip() or 0)) or 0
    if frames > 0:
        attempts.append([{"mediaPoolItem": item, "startFrame": 0, "endFrame": frames - 1,
                          "trackIndex": 1, "recordFrame": start}])
    attempts.append([{"mediaPoolItem": item, "trackIndex": 1, "recordFrame": start}])
    attempts.append([item])
    used = None
    for n, a in enumerate(attempts):
        if safe(lambda a=a: pool.AppendToTimeline(a)):
            used = n
            break
    placed = safe(lambda: tl.GetItemListInTrack("subtitle", 1)) or []
    if used is None or not placed:
        return {"error": "AppendToTimeline did not place the subtitle clip", "attempts": len(attempts)}
    first = safe(lambda: placed[0].GetStart())
    return {"success": first == start, "attempt": used, "cues": len(placed),
            "firstCueFrame": first, "timelineStart": start,
            **({} if first == start else {"error": "subtitles landed at frame %s, not %s" % (first, start)})}


POST_ROUTES.update({
    "/cves/timeline/current": action_cves_timeline_current,
    "/cves/append": action_cves_append,
    "/cves/subtitles": action_cves_subtitles,
})
'''


def patch(src: str) -> str:
    def once(s: str, old: str, new: str) -> str:
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"anchor found {n} times (expected 1): {old[:60]!r}")
        return s.replace(old, new)

    assert 'HOST = "127.0.0.1"' in src, "upstream no longer binds 127.0.0.1 - re-review before use"
    s = once(src, 'BRIDGE_VERSION = "2.0.0"', f'BRIDGE_VERSION = "2.0.0+cves1"  # {MARK}')
    # 1. no wildcard CORS on responses
    s = once(s, '''        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _error''', '''        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error''')
    # 2-4. guard every GET/POST
    s = once(s, '''    def do_GET(self):
        parsed = urlparse(self.path)''', GUARD + '''
    def do_GET(self):
        if self._cves_refuse():
            return
        parsed = urlparse(self.path)''')
    s = once(s, '''    def do_POST(self):
        parsed = urlparse(self.path)''', '''    def do_POST(self):
        if self._cves_refuse():
            return
        parsed = urlparse(self.path)''')
    s = once(s, '''    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()''', '''    def do_OPTIONS(self):
        self._error(403, "CursorBridge (CVES-hardened): CORS preflight refused")''')
    # 5. CVES endpoints, registered before the server starts
    s = once(s, "# ---------------------------------------------------------------------------\n# HTTP handler",
             CVES_ROUTES.lstrip("\n") + "\n\n# ---------------------------------------------------------------------------\n# HTTP handler")
    assert "Access-Control-Allow-Origin" not in s
    return s


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    raw = src_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    if MARK in text:
        print("already hardened; copying as is")
        out = text
    elif digest != UPSTREAM_SHA256:
        print(f"refusing: {src_path} sha256 {digest} is not the reviewed upstream file "
              f"({UPSTREAM_SHA256}, commit {UPSTREAM_COMMIT}). Re-review before updating the pin.")
        return 1
    else:
        out = patch(text)
    compile(out, str(out_path), "exec")  # syntax check before it lands in Resolve
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"hardened CursorBridge written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
