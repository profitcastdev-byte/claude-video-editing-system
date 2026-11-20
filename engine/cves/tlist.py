"""`cves templates`: the template registry in as few lines as Claude needs.

  cves templates            one line per kind: its templates' names (+ how to get more)
  cves templates --kinds    one line: every kind and how many templates it has
  cves templates NAME       one template: kind, source, doc line, the params its code reads (with defaults) and its
                            section of docs/TEMPLATES.md
  cves templates -v         the old full list: kind, name, doc line for every template
  --json                    the same as JSON (with NAME: one template; else every template with kind + doc + params)"""
import inspect, json, os, re

DOCS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "TEMPLATES.md"))
_GET = re.compile(r"""\bp\.get\(\s*["'](\w+)["']\s*(?:,\s*([^()\n]*?(?:\([^()\n]*\)[^()\n]*?)*))?\)""")
_IDX = re.compile(r"""\bp\[\s*["'](\w+)["']\s*\]""")

def _doc(fn): return " ".join((fn.__doc__ or "").split())

def params(name):
    """{param: default-or-'required'} from the source of the template's render + cues functions (best effort)"""
    from . import templates as T
    out = {}
    for fn in T.REGISTRY[name][:2]:
        try: src = inspect.getsource(fn)
        except (OSError, TypeError): continue
        for m in _IDX.finditer(src): out.setdefault(m.group(1), "required")
        for m in _GET.finditer(src):
            d = (m.group(2) or "None").strip()
            if out.get(m.group(1)) in (None, "required") or out.get(m.group(1)) == "None": out[m.group(1)] = d[:40]
    return out

def doc_section(name):
    """the docs/TEMPLATES.md heading section (or table row) that names `name`"""
    if not os.path.exists(DOCS): return ""
    with open(DOCS, encoding="utf-8") as f: lines = f.read().splitlines()
    tok = f"`{name}`"
    for i, l in enumerate(lines):
        if l.startswith("#") and tok in l:
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("#")), len(lines))
            return "\n".join(lines[i:j]).strip()
    row = next((l for l in lines if l.startswith("|") and l.split("|")[1].strip() == tok), None)
    return row or ""

def by_kind():
    from . import templates as T
    K = {}
    for k in sorted(T.REGISTRY): K.setdefault(T.KIND[k], []).append(k)
    return K

def one(name, as_json=False):
    from . import templates as T
    if name not in T.REGISTRY:
        near = [k for k in sorted(T.REGISTRY) if name.lower() in k.lower()]
        raise SystemExit(f"unknown template '{name}'" + (f"; did you mean: {', '.join(near[:8])}" if near else "; `cves templates` lists them"))
    d = {"name": name, "kind": T.KIND[name], "source": T.SOURCE.get(name), "layout": T.LAYOUT.get(name),
         "doc": _doc(T.REGISTRY[name][0]), "params": params(name), "docs": doc_section(name)}
    if as_json: return json.dumps(d, indent=1, ensure_ascii=False)
    L = [f"{name}  ({d['kind']}, {d['source']}, layout {d['layout']})", f"  {d['doc']}" if d["doc"] else ""]
    if d["params"]: L.append("  params (from the code; default or required): " + ", ".join(f"{k}={v}" for k, v in d["params"].items()))
    if d["docs"]: L += ["", d["docs"]]
    return "\n".join(x for x in L if x is not None)

def show(name=None, kinds=False, as_json=False, verbose=False):
    from . import templates as T
    if name: return one(name, as_json)
    K = by_kind()
    if as_json:
        return json.dumps({k: [{"name": n, "doc": _doc(T.REGISTRY[n][0])} | ({"params": sorted(params(n))} if verbose else {}) for n in v]
                           for k, v in K.items()}, indent=1, ensure_ascii=False)
    if kinds: return "  ".join(f"{k} {len(v)}" for k, v in K.items()) + f"   ({len(T.REGISTRY)} templates; `cves templates` lists the names)"
    if verbose: return "\n".join(f"{T.KIND[k]:8s} {k:14s} {_doc(T.REGISTRY[k][0])}" for k in sorted(T.REGISTRY))
    L = [f"{k} ({len(v)}): {', '.join(v)}" for k, v in K.items()]
    L.append("`cves templates NAME` = its params + docs; -v = a doc line each; --json; m_* pieces: `cves motion list`")
    return "\n".join(L)
