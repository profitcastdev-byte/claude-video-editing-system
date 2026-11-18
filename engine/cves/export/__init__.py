"""Control-mode exporters (ARCHITECTURE.md section 7).

    layers.py    reads + validates Export/control/layers.json (schema in docs/CONTROL-MODE.md),
                 writes captions.srt and timeline.otio
    resolve.py   timeline.fcpxml for DaVinci Resolve + live import through the CursorBridge
    kdenlive.py  project.kdenlive (MLT XML) + melt validation
    selftest.py  synthetic layer set -> both exporters -> checks

CLI: ``python -m cves.export {resolve,kdenlive,all,selftest} [Export/control]``
"""

from .layers import LayersError, Manifest, load_manifest  # noqa: F401
