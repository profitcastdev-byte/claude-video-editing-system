import os, sys, json, subprocess, pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_lint_clean():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "lint.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout

def test_only_ids(demo_copy):
    from cves import project, render
    TL = render.Timeline(project.Project(demo_copy)); t = TL.only_targets()
    assert "c1" in t and "end_card" in t and any(k.startswith("roto") for k in t)
    lo, hi, kind = t["c1"]; assert kind == "cutaway" and hi > lo

def test_templates_registered_with_kinds():
    from cves import templates as T
    must = {"title_card", "stat", "checklist", "comparison", "quote", "lower_third", "cta", "end_card", "steps", "chart",
            "image", "video_broll", "screen_rec", "pip", "split", "overlay_render", "kinetic_caption_emphasis"}
    assert must <= set(T.REGISTRY), must - set(T.REGISTRY)
    assert all(T.KIND[k] in ("cutaway", "roto", "chest", "end", "media", "overlay") for k in T.REGISTRY)

def hook(cmd, cwd):
    p = os.path.join(ROOT, "plugin", "hooks", "qc_guard.py")
    inp = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}
    r = subprocess.run([sys.executable, p], input=json.dumps(inp), capture_output=True, text=True, cwd=cwd)
    return r.stdout + r.stderr, r.returncode

def test_hook_blocks_unchecked_delivery(demo_copy):
    os.makedirs(os.path.join(demo_copy, "Export"), exist_ok=True)
    open(os.path.join(demo_copy, "Export", "x.mp4"), "wb").close()
    out, rc = hook(f'cp "{os.path.join(demo_copy, "Export", "x.mp4")}" ~/Desktop/', demo_copy)
    assert "deny" in out or rc == 2, out
    out, rc = hook("ls Export", demo_copy)
    assert "deny" not in out and rc == 0, out
    # a shell glob that matches a real file out of Export is still blocked
    out, rc = hook("cp Export/*.mp4 ~/Desktop/", demo_copy)
    assert "deny" in out or rc == 2, out


def test_hook_ignores_export_words_that_are_not_files(tmp_path):
    """prose, commit messages and heredocs that only mention Export paths ('Copy', 'move', 'Export/v001') are not
    deliveries, even in a project whose QC has not run yet"""
    proj = tmp_path / "proj"; (proj / "Edit").mkdir(parents=True)
    cmd = "cat > notes.md <<EOF\nTo deliver, move the files in Export/v001 to Drive\nEOF"
    out, rc = hook(cmd, str(proj))
    assert "deny" not in out and rc == 0, out
    out, rc = hook('git commit -m "copy Export/v002 notes"', str(proj))
    assert "deny" not in out and rc == 0, out
    (proj / "Export").mkdir(); (proj / "Export" / "m.mp4").write_bytes(b"x")    # a real file: still blocked
    out, rc = hook("cp Export/m.mp4 ~/Desktop/", str(proj))
    assert "deny" in out or rc == 2, out

def test_selftest_export():
    r = subprocess.run([sys.executable, "-m", "cves.cli", "export", "selftest", "--no-gui"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]

def test_every_style_key_is_documented():
    import yaml
    d = yaml.safe_load(open(os.path.join(ROOT, "engine", "cves", "styles", "default.yaml"), encoding="utf-8"))
    doc = open(os.path.join(ROOT, "docs", "STYLE.md"), encoding="utf-8").read()
    def keys(x, p=""):
        for k, v in x.items():
            q = f"{p}.{k}" if p else k
            if isinstance(v, dict) and v and not q.startswith(("font_files.script_fallback", "captions.per_style")): yield from keys(v, q)
            else: yield q
    miss = [k for k in keys(d) if k != "name" and f"`{k}`" not in doc and f"`{k.split('.')[-1]}`" not in doc]
    assert not miss, f"add these style keys to docs/STYLE.md: {miss}"

def test_no_client_names_in_repo():
    import re
    bad = re.compile(r"vedh?avalli|madapalli|srinivas|sattvic|pure veg|gmb map pack|profitcast clients", re.I)
    hits = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", ".pytest_cache", "golden")]
        for f in files:
            if f.endswith((".py", ".md", ".yaml", ".yml", ".json", ".sh", ".ps1", ".txt")) and f != "lint.py" and f != "test_cli_and_tools.py":
                p = os.path.join(d, f)
                try: s = open(p, encoding="utf-8").read()
                except UnicodeDecodeError: continue
                if bad.search(s): hits.append(os.path.relpath(p, ROOT))
    assert not hits, hits
