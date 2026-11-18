"""Golden frames: the demo rendered now vs tests/golden/*.png (downscaled 270x480). Tolerant to tiny font rasteriser
differences across platforms (mean abs diff <= 3/255, 99th pct <= 40); a real regression (moved graphic, changed grade,
missing caption) blows well past that. CVES_UPDATE_GOLDEN=1 rewrites them."""
import os, json, numpy as np, pytest
from PIL import Image

GOLD = os.path.join(os.path.dirname(__file__), "golden")

def frames_to_check(TL):
    cuts = {c["id"]: c for c in TL["cutaways"]}; F = TL["fps"]
    pick = {"aroll_lower_third": 20, "c1_list": int((cuts["c1"]["end"] - .2) * F), "c2_stat": int((cuts["c2"]["end"] - .2) * F),
            "roto_word": TL["a_frames"] - 15, "end_card": TL["frames"] - 10}
    return pick

def test_golden_frames(demo_rendered):
    TL = json.load(open(os.path.join(demo_rendered, "Edit", "timeline.json"), encoding="utf-8"))
    upd = os.environ.get("CVES_UPDATE_GOLDEN") == "1"; bad = []
    for name, f in frames_to_check(TL).items():
        im = Image.open(os.path.join(demo_rendered, "Edit", "frames", f"{f:05d}.png")).convert("RGB").resize((270, 480), Image.BILINEAR)
        g = os.path.join(GOLD, f"{name}.png")
        if upd or not os.path.exists(g):
            os.makedirs(GOLD, exist_ok=True); im.save(g); continue
        d = np.abs(np.asarray(im, np.int16) - np.asarray(Image.open(g).convert("RGB"), np.int16))
        if d.mean() > 3 or np.percentile(d, 99) > 40: bad.append(f"{name} (frame {f}): mean {d.mean():.2f}, p99 {np.percentile(d, 99):.0f}")
    assert not bad, "golden mismatch:\n" + "\n".join(bad)

def test_element_log(demo_rendered):
    els = [json.loads(l) for l in open(os.path.join(demo_rendered, "Edit", "elements.jsonl"), encoding="utf-8")]
    roles = {e["role"] for e in els}
    assert {"caption", "cutaway", "chest", "roto", "end"} <= roles, roles
    assert all(len(e["bbox"]) == 4 for e in els)
