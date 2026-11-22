"""The house look as built-ins (docs/TEMPLATES.md "House templates"): the drawn house templates (templates/house.py), their
HTML motion pieces (motion/pieces/<name>/), and project Brand/templates + Brand/motion loaded by every command."""
import json, textwrap
import numpy as np, pytest
from PIL import Image

from cves import gfx as G, style as STY, motion as MO, templates as T

S = STY.load()
_ok, _why = MO.available()

# drawn template -> (kind, params that show every part of it, piece-relative to a 0-2 s slot)
FORM = {"eyebrow": "Click the link below", "title": "Contact us", "fields": [{"icon": "chat", "text": "Your name", "at": 0.3}],
        "button": "Talk to our team", "button_at": 0.8, "press_at": 1.1, "done": "Request sent", "status": "We'll call you", "status_at": 1.3}
DRAWN = {
    "calendar_card": ("roto", {"at": 0.0, "eyebrow": "Every single month", "fill_at": 0.4, "booked": 16}),
    "month_rows": ("cutaway", {"eyebrow": "Every month", "items": [{"num": "5-8", "text": "Packages", "at": 0.2, "mark_at": 0.6}]}),
    "report_card": ("cutaway", {"eyebrow": "Agency report", "title": "Report", "sub": "This month", "pill": "All leads", "pill_at": 1.0,
                                "rows": [{"text": "Leads", "at": 0.3, "fill": 0.9, "state": "xfill", "state_at": 0.8}]}),
    "bars_card": ("roto", {"eyebrow": "What matters most"}),
    "rupee_drift": ("roto", {"text": "30,000 AD SPEND"}),
    "guarantee_dial": ("roto", {}),
    "radar": ("roto", {"label": "Your clinic"}),
    "contact_form": ("cutaway", FORM),
    "contact_form_end": ("end", FORM),
    "big_stat": ("chest", {"value": 100, "suffix": "%", "label": "REFUND"}),
}
# motion piece -> its templates and their kinds
PIECES = {
    "m_calendar_card": {"m_calendar_card": "roto"}, "m_month_rows": {"m_month_rows": "cutaway"},
    "m_report_card": {"m_report_card": "cutaway"}, "m_big_stat": {"m_big_stat": "overlay"},
    "m_contact_form": {"m_contact_form": "cutaway", "m_contact_form_end": "end"}, "m_bars_card": {"m_bars_card": "roto"},
    "m_rupee_drift": {"m_rupee_drift": "roto"}, "m_guarantee_dial": {"m_guarantee_dial": "roto"}, "m_radar": {"m_radar": "roto"},
}


@pytest.fixture
def tall():
    G.apply_style(S, canvas=(1080, 1920)); yield


@pytest.mark.parametrize("name", sorted(DRAWN))
def test_drawn_house_template_is_builtin_and_draws(name, tall):
    kind, p = DRAWN[name]
    assert T.SOURCE.get(name) == "builtin" and T.KIND[name] == kind
    render, cues = T.get(name)
    ctx = {"start": 0.0, "end": 2.0, "fps": 30}
    els = render(1.5, p, ctx)
    assert els and all(e.im.size == (G.W, G.H) for e in els)
    assert any(e.im.getbbox() for e in els)
    assert all(isinstance(c[0], float) or isinstance(c[0], int) for c in cues(p, ctx))


@pytest.mark.parametrize("piece", sorted(PIECES))
def test_house_motion_piece_is_builtin(piece):
    pc = MO.discover().get(piece)
    assert pc is not None and pc.origin == "builtin", piece
    for name, kind in PIECES[piece].items():
        assert name in T.REGISTRY and T.KIND[name] == kind, name


@pytest.mark.skipif(not _ok, reason=f"motion renderer unavailable: {_why}")
@pytest.mark.xdist_group("motion")
@pytest.mark.parametrize("piece", sorted(PIECES))
def test_house_motion_piece_renders_its_preview(piece, tmp_path):
    pc = MO.discover()[piece]
    p = dict((pc.meta.get("preview") or {}).get("params") or {})
    job = MO.render_piece(pc, p, S, (1080, 1920), 2, pc.duration, str(tmp_path))     # positions are canvas px at 9:16
    last = np.asarray(Image.open(job.frame_path(job.n - 1)))
    assert last.shape == (1920, 1080, 4) and (last[..., 3] > 0).sum() > 500, piece


# ------------------------------------------------------------------ project Brand/templates + Brand/motion, no CVES_TEMPLATES
PROBE = '''
from cves.templates import El
from cves import gfx as G
KIND = "cutaway"
def probe(t, p, ctx): return [El(G.new(), "probe", "cutaway")]
T = {"_house_probe_card": (probe, lambda p, ctx: [])}
'''


@pytest.fixture
def probe_project(tmp_path, monkeypatch):
    monkeypatch.delenv("CVES_TEMPLATES", raising=False)
    d = tmp_path / "Client one" / "2026-11-22 Ad"
    (d / "Brand" / "templates").mkdir(parents=True); (d / "Edit").mkdir()
    (d / "Brand" / "templates" / "probe.py").write_text(textwrap.dedent(PROBE), encoding="utf-8")
    m = d / "Brand" / "motion" / "house_probe_dot"; m.mkdir(parents=True)
    (m / "meta.yaml").write_text("title: Dot\nkinds: [cutaway]\n", encoding="utf-8")
    (m / "piece.html").write_text("<div id=d></div><script>CVES.piece({seek(t){}});</script>", encoding="utf-8")
    (d / "Edit" / "edl.json").write_text(json.dumps({"fps": 30, "segments": [{"id": "s0", "in": 0.0, "out": 4.0}]}), encoding="utf-8")
    (d / "Edit" / "edit.yaml").write_text(textwrap.dedent("""
        cutaways:
        - {id: c1, template: _house_probe_card, start: 0.5, end: 1.5}
        - {id: c2, template: m_house_probe_dot, start: 2.0, end: 3.0}
        """), encoding="utf-8")
    for n in ("_house_probe_card", "m_house_probe_dot"): assert n not in T.REGISTRY
    yield str(d)
    from cves.templates import motion as TM
    import sys
    for reg in (T.REGISTRY, T.KIND, T.SOURCE, T.LAYOUT, T.RASTER, MO.PIECES, TM.T, TM.KINDS, TM.PARAMS):
        for n in ("_house_probe_card", "m_house_probe_dot"): reg.pop(n, None)
    for m in [m for m in sys.modules if m.startswith("cves_user_templates.")]: sys.modules.pop(m)


def test_plan_loads_project_templates_and_motion(probe_project, capsys):
    from cves import cli
    with pytest.raises(SystemExit) as e: cli.main(["--project", probe_project, "plan"])
    out = capsys.readouterr().out
    assert e.value.code == 0, out
    assert "edit.yaml OK" in out


def test_validate_loads_project_templates_and_motion(probe_project):
    from cves import project, schema
    errs, _ = schema.validate(project.Project(probe_project))
    assert not [x for x in errs if "unknown template" in x], errs


def test_a_broken_project_file_is_skipped_not_fatal(probe_project, capsys):
    """one bad Brand/templates module or Brand/motion meta must not stop every command: it is skipped with a warning"""
    import pathlib
    d = pathlib.Path(probe_project)
    (d / "Brand" / "templates" / "aaa_broken.py").write_text("def (\n", encoding="utf-8")
    bad = d / "Brand" / "motion" / "aaa_bad"; bad.mkdir()
    (bad / "meta.yaml").write_text("title: [unclosed\n", encoding="utf-8"); (bad / "piece.html").write_text("<div></div>", encoding="utf-8")
    from cves import cli
    with pytest.raises(SystemExit) as e: cli.main(["--project", probe_project, "plan"])
    out = capsys.readouterr()
    assert e.value.code == 0 and "edit.yaml OK" in out.out, out.out          # the good template and piece still load
    assert "aaa_broken.py" in out.err and "aaa_bad" in out.err, out.err


def test_contact_form_button_lands_on_the_back_curve(tall, monkeypatch):
    """before the press the button scale is back(p), not back(p) squared"""
    got = []
    real = G.pill
    monkeypatch.setattr(G, "pill", lambda *a, **k: got.append(k["sc"]) or real(*a, **k))
    p = dict(FORM, button_at=0.8, press_at=1.5)
    T.get("contact_form")[0](0.9, p, {"start": 0.0, "end": 2.0, "fps": 30})
    assert got and abs(got[0] - G.back(G.enter(0.9, 0.8, .3, 30))) < 1e-9, got
