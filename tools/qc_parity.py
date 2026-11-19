#!/usr/bin/env python3
"""Compare two QC stamps (Edit/qc.json) gate by gate: same gate ids, same PASS/WARN/FAIL/N/A, and the same numbers in
every summary (within float rounding: 1 unit in the last printed digit). Used to prove a QC speed-up changed nothing.

    python tools/qc_parity.py BEFORE/qc.json AFTER/qc.json      exit 1 on any difference
"""
import json, re, sys

NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _close(a, b):
    """two printed numbers agree within one unit of the last printed digit"""
    da = len(a.split(".")[1]) if "." in a else 0; db = len(b.split(".")[1]) if "." in b else 0
    return abs(float(a) - float(b)) <= 10 ** -min(da, db) + 1e-9


def compare(a, b):
    A = {g["id"]: g for g in a["gates"]}; B = {g["id"]: g for g in b["gates"]}; out = []
    for gid in sorted(set(A) | set(B)):
        x, y = A.get(gid), B.get(gid)
        if x is None or y is None: out.append(f"{gid}: only in {'after' if x is None else 'before'}"); continue
        if x["status"] != y["status"]: out.append(f"{gid}: status {x['status']} -> {y['status']}")
        nx, ny = NUM.findall(x["summary"]), NUM.findall(y["summary"])
        if NUM.sub("#", x["summary"]) != NUM.sub("#", y["summary"]) or len(nx) != len(ny) or not all(_close(p, q) for p, q in zip(nx, ny)):
            out.append(f"{gid}: summary\n   before: {x['summary']}\n   after:  {y['summary']}")
    return out


def main(argv):
    if len(argv) != 3: print(__doc__); return 2
    a, b = (json.load(open(p, encoding="utf-8")) for p in argv[1:])
    d = compare(a, b)
    for line in d: print(line)
    n = len(a["gates"])
    print(f"{'IDENTICAL' if not d else 'DIFFERENT'}: {n} gates before, {len(b['gates'])} after, {len(d)} differences "
          f"(before {a['fail']}F/{a['warn']}W/{a['pass']}P, after {b['fail']}F/{b['warn']}W/{b['pass']}P)")
    return 1 if d else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
