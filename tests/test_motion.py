"""Motion layer (docs/MOTION.md): HTML pieces rendered by headless Chromium to RGBA frames. Small canvases, few frames."""
import os, json
import numpy as np, pytest
from PIL import Image

from cves import motion as MO, style as STY, gfx as G

ok, why = MO.available()
pytestmark = pytest.mark.skipif(not ok, reason=f"motion renderer unavailable: {why}")

S = STY.load()
FPS = 10


def frames(job):
    return [np.asarray(Image.open(job.frame_path(k))) for k in range(job.n)]


@pytest.fixture(scope="module")
def title_job(tmp_path_factory):
    root = tmp_path_factory.mktemp("motion cache ’quoted’")          # spaces + curly apostrophes in the path
    return MO.render_piece("m_kinetic_title", {"text": "Stop *guessing*.", "eyebrow": "The fix"}, S, (270, 480), FPS, 1.2, str(root))


def test_rgba_with_transparency(title_job):
    fr = frames(title_job)
    assert len(fr) == 12 and fr[0].shape == (480, 270, 4)
    last = fr[-1][..., 3]
    assert last.min() == 0 and last.max() == 255           # transparent page, opaque type
    assert (fr[0][..., 3] > 0).sum() < (last > 0).sum()      # it builds in
    man = title_job.manifest()
    assert man["n"] == 12 and "guessing" in man["text"][-1]  # visible text per frame, for the element log


def test_deterministic_and_seek_monotonic(title_job, tmp_path):
    again = MO.render_piece("m_kinetic_title", {"text": "Stop *guessing*.", "eyebrow": "The fix"}, S, (270, 480), FPS, 1.2, str(tmp_path))
    assert again.key == title_job.key
    a, b = frames(title_job), frames(again)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))   # same t -> identical pixels (fresh render, other folder)
    assert not np.array_equal(a[1], a[4])                    # different t during the animation -> different pixels


def test_cache_hit(title_job, monkeypatch):
    def boom(*a, **k): raise AssertionError("re-rendered a cached piece")
    monkeypatch.setattr(MO.CHROME, "get_page", boom)
    job = MO.render_piece("m_kinetic_title", {"text": "Stop *guessing*.", "eyebrow": "The fix"}, S, (270, 480), FPS, 1.2, str(title_job.root))
    assert job.dir == title_job.dir and job.done


def test_landscape_piece(tmp_path):
    job = MO.render_piece("m_stat_counter", {"value": 312, "suffix": "%", "label": "calls"}, S, (480, 270), FPS, 1.6, str(tmp_path))
    fr = frames(job)
    assert fr[-1].shape == (270, 480, 4) and fr[-1][..., 3].max() == 255
    assert "312%" in job.manifest()["text"][-1]
    assert any(c[1] == "lowhit" for c in job.manifest()["cues"])


def test_template_call(tmp_path, monkeypatch):
    from cves import templates as T
    monkeypatch.setenv("CVES_MOTION_CACHE", str(tmp_path))
    monkeypatch.setattr(G, "W", 270); monkeypatch.setattr(G, "H", 480)     # canvas read at call time
    assert T.KIND["m_lower_third"] == "overlay" and T.KIND["m_kinetic_title_roto"] == "roto"
    render, cues = T.get("m_glass_card")
    ctx = {"start": 2.0, "end": 3.0, "fps": FPS, "S": S, "resolve": lambda p: p}
    p = {"title": "Show up", "icon": "place", "at": 2.0}
    assert render(1.9, p, ctx) == []                                          # before its clock starts
    els = render(2.9, p, ctx)
    assert len(els) == 1 and els[0].id == "m_glass_card" and els[0].role == "cutaway"
    assert els[0].im.size == (270, 480) and els[0].text and "Show up" in els[0].text
    assert abs(els[0].t_key - 2.0) < 1e-9
    chest = render(2.9, p, dict(ctx, chin=300))                               # over A-roll: chest role, exits on its own
    assert chest[0].role == "chest"
    cs = cues(p, ctx)
    assert cs and all(2.0 <= c[0] < 3.0 for c in cs)


def test_user_piece_discovery(tmp_path):
    from cves import templates as T
    d = tmp_path / "Brand" / "motion" / "dot"; d.mkdir(parents=True); (tmp_path / "Brand" / "templates").mkdir()
    (d / "meta.yaml").write_text("title: Dot\nkinds: [cutaway]\nparams:\n  size: {type: number, default: 10}\n", encoding="utf-8")
    (d / "piece.html").write_text("<div id=d style='width:20px;height:20px;background:var(--accent)'></div><script>"
                                  "CVES.piece({seek(t){document.getElementById('d').style.opacity=t}});</script>", encoding="utf-8")
    got = T.load_dir(str(tmp_path / "Brand" / "templates"), "project")
    assert "m_dot" in got and T.KIND["m_dot"] == "cutaway"
    try:
        job = MO.render_piece("m_dot", {}, S, (64, 64), FPS, 0.3, str(tmp_path / "cache"))
        assert np.asarray(Image.open(job.frame_path(2)))[..., 3].max() > 0
    finally:
        for reg in (T.REGISTRY, T.KIND, T.SOURCE, MO.PIECES): reg.pop("m_dot", None)


def test_style_vars_follow_the_style():
    v = MO.css_vars(STY.Style({**S, "colors": {**S["colors"], "accent": [10, 20, 30]}}), (1920, 1080))
    assert v["--accent-rgb"] == "10 20 30" and v["--u"] == "10.8000px"
    x0, y0, x1, y1 = MO.safe_frac(S, (1920, 1080))                            # 9:16 safe zone does not fit 16:9: fallback
    assert (x0, y0, x1, y1) == tuple(S["motion"]["safe_fallback"])
