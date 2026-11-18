#!/usr/bin/env python3
"""Portability + no-hard-coded-style lint for the engine (docs/CONTRACTS.md §7). Runs in CI on Mac, Windows and Linux.

Rules (each line can opt out with a trailing `# lint: ok <reason>`):
  L1  no /tmp paths                     -> use tempfile
  L2  text-mode open() without encoding -> encoding="utf-8"
  L3  hard-coded 24000/1001 or 23.976   -> timeline fps_rational
  L4  hard-coded 1080x1920 canvas       -> style platform.size / gfx.W, gfx.H
  L5  client or brand names in code     -> params / style presets
  L6  hex colour literals in templates  -> gfx / style colours
Exit 1 on any finding."""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE = os.path.join(ROOT, "engine", "cves")
SKIP_DIRS = {"__pycache__", "styles"}
# files where a literal is the definition itself (the design space) or a test fixture
ALLOW = {
    "L4": {"gfx.py", "selftest.py"},
    "L3": {"selftest.py"},
}
BRANDS = re.compile(r"vedh?avalli|madapalli|srinivas|sattvic|pure veg|profitcast(?!-dark)", re.I)
RULES = [
    ("L1", re.compile(r"""['"]/tmp(/|['"])"""), "use tempfile, not /tmp"),
    ("L3", re.compile(r"24000\s*/\s*1001|\b23\.976\b|24000,\s*1001|1001/24000"), "frame rate must come from the timeline (fps_rational)"),
    ("L4", re.compile(r"\b1080\s*[x:,]\s*1920\b|\(1080,\s*1920\)|\[1080,\s*1920\]"), "canvas size must come from the style (platform.size) or gfx.W/H"),
    ("L5", BRANDS, "no client or brand names in engine code"),
]
OPEN = re.compile(r"(?<![\.\w])open\(")
HEX = re.compile(r"""['"]#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?['"]""")

def text_open_without_encoding(line):
    for m in OPEN.finditer(line):
        depth, j = 0, m.end() - 1
        while j < len(line):
            depth += line[j] == "("; depth -= line[j] == ")"
            if depth == 0: break
            j += 1
        args = line[m.end():j]
        if "encoding" in args or re.search(r"""['"][rwax]?\+?b\+?['"]""", args): continue
        return True
    return False

def main():
    bad = []
    for d, dirs, files in os.walk(ENGINE):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if not f.endswith(".py"): continue
            p = os.path.join(d, f); rel = os.path.relpath(p, ROOT)
            with open(p, encoding="utf-8") as fh: lines = fh.read().splitlines()
            in_doc = False
            for n, line in enumerate(lines, 1):
                s = line.strip()
                if s.count('"""') % 2 == 1: in_doc = not in_doc; continue
                if in_doc or s.startswith("#") or "# lint: ok" in line: continue
                code = line.split(" # ")[0]
                for rid, rx, msg in RULES:
                    if f in ALLOW.get(rid, ()): continue
                    if rx.search(code): bad.append(f"{rel}:{n}: {rid} {msg}\n    {s[:120]}")
                if text_open_without_encoding(code): bad.append(f"{rel}:{n}: L2 text open() without encoding=\"utf-8\"\n    {s[:120]}")
                if "templates" in rel and HEX.search(code): bad.append(f"{rel}:{n}: L6 colour literal in a template: use gfx/style colours\n    {s[:120]}")
    print("\n".join(bad) if bad else "lint: clean")
    print(f"\n{len(bad)} finding(s)" if bad else "")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
