"""Client project folders and edit.yaml. One folder per video, outside the repo (ARCHITECTURE §2)."""
import os, json, datetime, yaml

FOLDERS = ["Raw", "Inspirations", "Brand", "Music", "Assets", "Edit", "Moodboard", "Export"]
def clients_root():
    """where client project folders live: $CVES_CLIENTS, else config `clients_root`, else ~/CVES Projects"""
    from . import config as C
    return os.path.expanduser(os.environ.get("CVES_CLIENTS") or C.get("clients_root"))
CLIENTS_ROOT = None   # resolved lazily by clients_root()

class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        if not os.path.isdir(os.path.join(self.root, "Edit")):
            raise SystemExit(f"not a CVES project (no Edit/ folder): {self.root}")
    def p(self, *parts): return os.path.join(self.root, *parts)
    def e(self, *parts): return os.path.join(self.root, "Edit", *parts)
    @property
    def edit(self):
        f = self.e("edit.yaml")
        return yaml.safe_load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    def save_edit(self, d): yaml.safe_dump(d, open(self.e("edit.yaml"), "w", encoding="utf-8"), sort_keys=False, allow_unicode=True, width=140)
    def json(self, name, default=None):
        f = self.e(name)
        return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else default
    def save_json(self, name, d): json.dump(d, open(self.e(name), "w", encoding="utf-8"), indent=1)
    @property
    def raw(self):
        r = self.edit.get("project", {}).get("raw")
        if r: return self.p(r)
        vids = [f for f in sorted(os.listdir(self.p("Raw"))) if f.lower().endswith((".mp4", ".mov", ".mkv", ".m4v"))]
        if not vids: raise SystemExit("no raw video in Raw/")
        return self.p("Raw", vids[0])

def new(client, title, raw=None, root=None):
    d = os.path.join(root or clients_root(), client, f"{datetime.date.today():%Y-%m-%d} {title}")
    for f in FOLDERS: os.makedirs(os.path.join(d, f), exist_ok=True)
    if raw:
        import shutil; dst = os.path.join(d, "Raw", os.path.basename(raw))
        if not os.path.exists(dst): shutil.copy2(raw, dst)
    pr = Project(d)
    if not os.path.exists(pr.e("edit.yaml")):
        pr.save_edit({"project": {"client": client, "title": title,                    # fps/size come from the footage + style
                                  "raw": f"Raw/{os.path.basename(raw)}" if raw else None},
                      "style": {},          # {preset: <name>} or inline keys; `cves inspire` writes Edit/style.yaml
                      "qc": {"topic_keywords": [], "brand_tail": [], "duration": None}})
    if not os.path.exists(os.path.join(d, "Brand", "claims.md")):
        open(os.path.join(d, "Brand", "claims.md"), "w", encoding="utf-8").write("# Approved claims\nOnly published, verifiable proof goes on screen. List each claim with its source.\n")
    return d
