#!/usr/bin/env python3
"""Harden 12bijaya/MCP_Server_Kdenlive for CVES: every model-chosen write path must stay in the workspace.

Usage: python patch_kdenlive_mcp.py <clone dir>

Upstream confines *relative* write paths to KDENLIVE_MCP_WORKSPACE but accepts any *absolute* path
as is, in four places (save_project / save_project_as, restore_project, export_subtitles,
start_render). That gives the model (or a prompt injection in a file it reads) a write-anywhere
primitive: restore_project copies any readable file over any path. This patch routes all four
through upstream's own ``resolve_workspace_path`` (which accepts absolute paths that are inside the
workspace), and limits render outputs to video container extensions.

It also makes the writer reference the CVES 1080x1920 23.976 Kdenlive profile (env
KDENLIVE_MCP_CUSTOM_PROFILE), so projects it saves do not trigger Kdenlive's "non standard framerate"
error on open.

CVES registers the server with KDENLIVE_MCP_WORKSPACE = the clients root (~/CVES Projects),
so every Export/control/project.kdenlive stays writable and nothing else is.

It also adds ``src/kdenlive_mcp/storage/snapshots/manager.py``: upstream imports it from
mcp_tools/state.py but never committed it (the repo's .gitignore excludes ``snapshots/``), so the
pinned commit cannot even start. The replacement stores each snapshot as JSON (project model + media
index) under KDENLIVE_MCP_SNAPSHOTS/<project id>/ and implements the four calls snapshot_tools.py
makes: create_snapshot, list_snapshots, restore_snapshot, compare_snapshots.

Only the reviewed upstream files (pinned commit + sha256) are accepted.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

UPSTREAM_COMMIT = "4733141efd1679fee29bfe0be481ab191eaf5f8f"
MARK = "# CVES-HARDENED"

FILES = {
    "src/kdenlive_mcp/kdenlive/adapter/project.py": (
        "b801ad1d08e951fde58b9be75e000023c65a40981daea46273d7f340455bee69",
        [
            ("    resolved = resolve_workspace_path(target) if not Path(target).is_absolute() else Path(target)\n",
             "    resolved = resolve_workspace_path(target)  " + MARK + "\n"),
            ("    resolved_target = resolve_workspace_path(restore_to) if not Path(restore_to).is_absolute() else Path(restore_to)\n",
             "    resolved_target = resolve_workspace_path(restore_to)  " + MARK + "\n"),
        ],
    ),
    "src/kdenlive_mcp/core/subtitles/ops.py": (
        "f4406e1786ccf1b574c9f3d6a9d2b1462ff12968f115b867dff34b7ba1b66cc7",
        [
            ("    resolved = resolve_workspace_path(output_path) if not Path(output_path).is_absolute() else Path(output_path)\n",
             "    resolved = resolve_workspace_path(output_path)  " + MARK + "\n"
             "    if resolved.suffix.lower() != \".srt\":\n"
             "        raise InvalidOperationError(\"Subtitle export path must end in .srt\")\n"),
        ],
    ),
    "src/kdenlive_mcp/kdenlive/adapter/profiles.py": (
        "688e7a8357b372172612e1920528d4e92bc9a458c970b83492b716974b420515",
        [
            ("    if key in _NAMED_PROFILES:\n        return _NAMED_PROFILES[key]\n",
             "    if key in _NAMED_PROFILES:\n        return _NAMED_PROFILES[key]\n"
             "    import os  " + MARK + ": point Kdenlive at the installed 1080x1920 23.976 profile so it does not\n"
             "    # fall back to its fps check, which rejects 24000/1001 (ProfileInfo::hasValidFps)\n"
             "    custom = os.environ.get(\"KDENLIVE_MCP_CUSTOM_PROFILE\", \"\")\n"
             "    if custom and key == (1080, 1920, \"23.976\") and os.path.isfile(custom):\n"
             "        return custom\n"),
        ],
    ),
    "src/kdenlive_mcp/media/rendering/render_engine.py": (
        "6f26eb9a42e893b4714287218f2c2ca30c92f66babdcd0b64cffaab5cba42785",
        [
            ("        resolved = resolved.resolve() if resolved.parent.exists() else resolved\n",
             "        resolved = resolved.resolve() if resolved.parent.exists() else resolved\n"
             "        from kdenlive_mcp.storage.workspace import resolve_workspace_path  " + MARK + "\n"
             "        resolved = resolve_workspace_path(str(resolved))\n"
             "        if resolved.suffix.lower() not in (\".mp4\", \".mov\", \".mkv\", \".webm\"):\n"
             "            raise InvalidOperationError(\"Render output must be .mp4/.mov/.mkv/.webm\")\n"),
        ],
    ),
}


SNAPSHOT_MANAGER = '''"""Project snapshots (added by CVES setup/control/patch_kdenlive_mcp.py; missing upstream)."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from kdenlive_mcp.config import get_config
from kdenlive_mcp.core.assets.model import MediaAsset, MediaIndex
from kdenlive_mcp.core.timeline.serialize import project_from_dict, project_to_dict
from kdenlive_mcp.errors import InvalidOperationError


@dataclass
class SnapshotInfo:
    id: str
    project_id: str
    label: str
    created_at: float
    clip_count: int
    duration_frames: int

    def to_dict(self) -> dict:
        return asdict(self)


def _safe(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name or "") or name in (".", ".."):
        raise InvalidOperationError(f"Invalid id: {name!r}")
    return name


class SnapshotManager:
    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or get_config().snapshots_dir

    def _dir(self, project_id: str) -> Path:
        d = self.root / _safe(project_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _stats(project) -> tuple[int, int]:
        seq = project.active_sequence()
        if seq is None:
            return 0, 0
        return sum(len(t.clips) for t in seq.tracks), seq.duration()

    def create_snapshot(self, project, media_index: MediaIndex, label: str = "") -> SnapshotInfo:
        clips, dur = self._stats(project)
        info = SnapshotInfo(id=f"snap_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                            project_id=project.id, label=label, created_at=time.time(),
                            clip_count=clips, duration_frames=dur)
        payload = {"info": info.to_dict(), "project": project_to_dict(project),
                   "media": [a.to_dict() for a in media_index.list()]}
        (self._dir(project.id) / f"{info.id}.json").write_text(json.dumps(payload), encoding="utf-8")
        return info

    def _load(self, project_id: str, snapshot_id: str) -> dict:
        p = self._dir(project_id) / f"{_safe(snapshot_id)}.json"
        if not p.is_file():
            raise InvalidOperationError(f"Snapshot not found: {snapshot_id}")
        return json.loads(p.read_text(encoding="utf-8"))

    def list_snapshots(self, project_id: str) -> list[SnapshotInfo]:
        out = []
        for p in sorted(self._dir(project_id).glob("snap_*.json")):
            try:
                out.append(SnapshotInfo(**json.loads(p.read_text(encoding="utf-8"))["info"]))
            except (ValueError, KeyError, TypeError):
                continue
        return out

    def restore_snapshot(self, project_id: str, snapshot_id: str):
        data = self._load(project_id, snapshot_id)
        project = project_from_dict(data["project"])
        index = MediaIndex(None)
        for a in data.get("media", []):
            index.upsert(MediaAsset.from_dict(a))
        return project, index

    def compare_snapshots(self, project_id: str, snapshot_id_a: str, snapshot_id_b: str) -> dict:
        a, b = self._load(project_id, snapshot_id_a), self._load(project_id, snapshot_id_b)
        ia, ib = a["info"], b["info"]
        pa, pb = json.dumps(a["project"], sort_keys=True), json.dumps(b["project"], sort_keys=True)
        return {"a": ia, "b": ib, "identical": pa == pb,
                "clip_count_delta": ib["clip_count"] - ia["clip_count"],
                "duration_delta_frames": ib["duration_frames"] - ia["duration_frames"]}
'''


def add_snapshot_manager(root: Path) -> None:
    pkg = root / "src/kdenlive_mcp/storage/snapshots"
    target = pkg / "manager.py"
    if target.exists() and MARK not in target.read_text(encoding="utf-8") and "CVES" not in target.read_text(encoding="utf-8"):
        print("upstream now ships storage/snapshots/manager.py; leaving it alone (re-review the pin)")
        return
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    compile(SNAPSHOT_MANAGER, str(target), "exec")
    target.write_text(SNAPSHOT_MANAGER, encoding="utf-8")
    print("added: src/kdenlive_mcp/storage/snapshots/manager.py (missing upstream)")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    for rel, (sha, edits) in FILES.items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        if MARK in text:
            print(f"already hardened: {rel}")
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != sha:
            print(f"refusing: {rel} sha256 {digest} is not the reviewed upstream file (commit {UPSTREAM_COMMIT}). "
                  "Re-review before updating the pin.")
            return 1
        for old, new in edits:
            if text.count(old) != 1:
                print(f"refusing: anchor not found exactly once in {rel}: {old.strip()[:70]}")
                return 1
            text = text.replace(old, new)
        # (both patched modules already import InvalidOperationError upstream)
        compile(text, str(p), "exec")
        p.write_text(text, encoding="utf-8")
        print(f"hardened: {rel}")
    add_snapshot_manager(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
