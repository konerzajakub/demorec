import pytest

from demorec import config


def test_relative_url_becomes_file_url(tmp_path):
    (tmp_path / "project.toml").write_text('[app]\nurl = "./site/index.html"\n', encoding="utf-8")
    cfg = config.load(tmp_path)
    assert cfg.url.startswith("file:///") and cfg.url.endswith("site/index.html")
    assert cfg.login is None and cfg.out_dir.endswith("out")


def test_login_reads_env(tmp_path, monkeypatch):
    (tmp_path / "project.toml").write_text('[app]\nurl = "http://x/"\n[login]\nusername = "a"\n', encoding="utf-8")
    monkeypatch.setenv("DEMOREC_PASSWORD", "secret")
    cfg = config.load(tmp_path)
    assert (cfg.login.username, cfg.login.password) == ("a", "secret")


def test_missing_url_fails(tmp_path):
    (tmp_path / "project.toml").write_text("[app]\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        config.load(tmp_path)
