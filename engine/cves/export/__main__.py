"""python -m cves.export {resolve,kdenlive,all,selftest} [args]  (cli.py can delegate `cves export ...` here)."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "resolve":
        from .resolve import main as m
    elif cmd == "kdenlive":
        from .kdenlive import main as m
    elif cmd == "selftest":
        from .selftest import main as m
    elif cmd == "all":
        from .kdenlive import main as mk
        from .resolve import main as mr
        return mr(rest) or mk(rest)
    else:
        print(f"unknown export target {cmd!r}; use resolve, kdenlive, all or selftest")
        return 2
    return m(rest)


if __name__ == "__main__":
    raise SystemExit(main())
