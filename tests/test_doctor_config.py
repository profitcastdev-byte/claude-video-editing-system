"""cves doctor: config paths with ~ expand, a missing projects folder is created, an unset team_taste is not a FAIL."""
import importlib.util, os, types

HERE = os.path.dirname(os.path.abspath(__file__))


def _doctor():
    spec = importlib.util.spec_from_file_location("cves_doctor", os.path.join(HERE, "..", "setup", "doctor.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_config_keys_tilde_missing_folder_and_optional_team(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path)); monkeypatch.setenv("USERPROFILE", str(tmp_path))
    d = _doctor(); d.rows.clear()
    vals = {"clients_root": "~/CVES Projects", "team_taste": ""}
    cfg = types.SimpleNamespace(DEFAULTS=dict.fromkeys(vals), get=vals.get)
    d.check_config_keys(cfg, set())
    st = {r["check"]: r for r in d.rows}
    assert st["clients_root"]["status"] == "PASS", st
    assert os.path.isdir(tmp_path / "CVES Projects")
    assert st["team_taste"]["status"] == "PASS" and "not set" in st["team_taste"]["detail"]
    d.rows.clear(); vals["team_taste"] = str(tmp_path / "nope" / "taste")
    d.check_config_keys(cfg, set())
    assert {r["check"]: r["status"] for r in d.rows}["team_taste"] == "FAIL"   # a set but missing shared folder is a real problem
