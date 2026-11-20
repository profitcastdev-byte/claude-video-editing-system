"""A re-cut keeps segment ids (cves select, take alignment), so prep must not reuse a plate / matte cut from the old span.
Found on the first real job: aligned takes changed in/out, prep skipped the existing plates, render ran out of frames."""
import json, os
from cves import project as PRJ, ingest as ING


def test_plate_rebuilt_when_its_span_changes_and_legacy_plates_adopted(demo_copy):
    pr = PRJ.Project(demo_copy)
    edl = pr.json("edl.json"); F = edl["fps"]; segs = edl["segments"]
    mt = {s["id"]: os.path.getmtime(pr.e("plate", f"{s['id']}.mkv")) for s in segs}

    ING.plate(pr)     # plates from before span keys: the ones whose length matches are adopted, not rebuilt
    for s in segs:
        assert os.path.getmtime(pr.e("plate", f"{s['id']}.mkv")) == mt[s["id"]], s["id"]
        assert os.path.exists(pr.e("plate", f"{s['id']}.key"))

    s0 = segs[0]; s0["out"] = round(s0["out"] - 0.2, 5); pr.save_json("edl.json", edl)
    matte0 = pr.e("matte", f"{s0['id']}.mkv"); assert os.path.exists(matte0)
    ING.plate(pr)
    assert ING._frames(pr.e("plate", f"{s0['id']}.mkv")) == round((s0["out"] - s0["in"]) * F)
    assert not os.path.exists(matte0), "the stale matte of a re-cut plate must go (prep rebuilds it)"
    for s in segs[1:]:
        assert os.path.getmtime(pr.e("plate", f"{s['id']}.mkv")) == mt[s["id"]], s["id"]
