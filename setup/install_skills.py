"""Install the Claude Code plugins and skills listed in setup/skills.json (Mac and Windows).
usage: python setup/install_skills.py [--core-only] [--dry-run]
Plugins go through the `claude` CLI (`claude plugin marketplace add`, `claude plugin install`). Git skills are cloned
into ~/.claude/skills/<name> (or each sub-skill of a multi-skill repo). npx skills use the `skills` CLI.
Manual entries are listed at the end: they can't be redistributed (paid licence / unknown source)."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.join(os.path.expanduser("~"), ".claude", "skills")
DRY = "--dry-run" in sys.argv; CORE = "--core-only" in sys.argv

def run(cmd):
    print("  $", " ".join(cmd))
    if DRY: return 0
    try: return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError: print(f"  ! {cmd[0]} not found"); return 127

def main():
    cfg = json.load(open(os.path.join(HERE, "skills.json"))); ok, failed, manual = [], [], []
    claude = shutil.which("claude")
    for p in cfg["plugins"]:
        if CORE and p["status"] != "core": continue
        print(f"plugin {p['name']}")
        if not claude: failed.append(f"{p['name']} (claude CLI not on PATH)"); continue
        run([claude, "plugin", "marketplace", "add", p["marketplace_repo"]])
        (ok if run([claude, "plugin", "install", f"{p['name']}@{p['marketplace']}"]) == 0 else failed).append(p["name"])
    os.makedirs(SK, exist_ok=True)
    for s in cfg["skills"]:
        if CORE and s["status"] != "core": continue
        print(f"skill {s['name']} ({s['method']})")
        if s["method"] == "manual": manual.append(s); continue
        if s["method"] == "npx":
            (ok if run(s["cmd"]) == 0 else failed).append(s["name"]); continue
        tmp = tempfile.mkdtemp()
        if run(["git", "clone", "--depth", "1", s["repo"], tmp]) != 0: failed.append(s["name"]); continue
        if DRY: ok.append(s["name"]); continue
        src = os.path.join(tmp, s["path"])
        targets = []
        if os.path.exists(os.path.join(src, "SKILL.md")): targets = [(src, s["name"].rstrip("-*"))]
        else: targets = [(os.path.join(src, d), d) for d in sorted(os.listdir(src)) if os.path.exists(os.path.join(src, d, "SKILL.md"))]
        if not targets: failed.append(f"{s['name']} (no SKILL.md found in {s['path']})"); continue
        for d, name in targets:
            dst = os.path.join(SK, name)
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(d, dst, ignore=shutil.ignore_patterns(".git"))
        ok.append(f"{s['name']} ({len(targets)} skill{'s' if len(targets) > 1 else ''})")
        shutil.rmtree(tmp, ignore_errors=True)
    print("\ninstalled:", ", ".join(ok) or "-")
    if failed: print("FAILED:", ", ".join(failed))
    if manual:
        print("\nmanual (not redistributable):")
        for s in manual: print(f"  - {s['name']}: {s['why']}")
    print("\nRestart Claude Code to load new plugins and skills.")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
