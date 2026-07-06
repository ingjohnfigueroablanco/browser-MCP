from pathlib import Path

import pytest

from browser_mcp.chrome import launcher
from browser_mcp.config import Config, chrome_flags
from browser_mcp.chrome.ws_url import parse_ws_url


def test_chrome_flags_include_port_profile_and_origin():
    cfg = Config(profile_dir=Path("X:/profile"), headless=False)
    flags = chrome_flags(cfg, 9333)
    assert "--remote-debugging-port=9333" in flags
    assert "--user-data-dir=X:\\profile" in flags or "--user-data-dir=X:/profile" in flags
    assert any(f.startswith("--remote-allow-origins=") for f in flags)
    assert "--headless=new" not in flags


def test_chrome_flags_headless_toggle():
    cfg = Config(headless=True)
    assert "--headless=new" in chrome_flags(cfg, 9222)


def test_find_browser_prefers_explicit_path(tmp_path):
    fake = tmp_path / "chrome.exe"
    fake.write_text("")
    cfg = Config(chrome_path=str(fake))
    assert launcher.find_browser(cfg) == str(fake)


def test_find_browser_raises_when_missing(monkeypatch):
    monkeypatch.setattr(launcher, "_registry_chrome_path", lambda: None)
    monkeypatch.setattr(launcher, "_WINDOWS_CANDIDATES", [])
    cfg = Config(chrome_path=None)
    with pytest.raises(FileNotFoundError):
        launcher.find_browser(cfg)


def test_parse_ws_url_extracts_field():
    payload = {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc"}
    assert parse_ws_url(payload).endswith("/abc")


def test_parse_ws_url_raises_without_field():
    with pytest.raises(ValueError):
        parse_ws_url({})


def test_find_free_port_returns_bindable(monkeypatch):
    seen = []

    def fake_free(port):
        seen.append(port)
        return port == 9225

    monkeypatch.setattr(launcher, "_port_is_free", fake_free)
    assert launcher.find_free_port(9222) == 9225
