"""Locate and launch Chrome (or Edge) with CDP enabled; support reattach."""

from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from ..config import Config, DEVTOOLS_HOST, PORT_SCAN_RANGE, chrome_flags

# Common Windows install locations, checked in order.
_WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    # Edge fallback (same CDP)
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# Common Linux/macOS install locations (Docker, Ubuntu, Debian, Mac).
_UNIX_CANDIDATES = [
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/local/bin/chromium",
    "/snap/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def _registry_chrome_path() -> str | None:
    """Read chrome.exe path from the Windows registry App Paths key (read-only)."""
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return None
    key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key) as handle:
                value, _ = winreg.QueryValueEx(handle, None)
                if value and Path(value).exists():
                    return value
        except OSError:
            continue
    return None


def find_browser(cfg: Config) -> str:
    """Resolve a usable browser executable path. Raises if none found."""
    if cfg.chrome_path and Path(cfg.chrome_path).exists():
        return cfg.chrome_path
    reg = _registry_chrome_path()
    if reg:
        return reg
    candidates = _WINDOWS_CANDIDATES if os.name == "nt" else _UNIX_CANDIDATES
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "No se encontro Chrome ni Edge. "
        "Define CHROME_PATH o CHROME_EXECUTABLE con la ruta al binario."
    )


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((DEVTOOLS_HOST, port))
            return True
        except OSError:
            return False


def find_free_port(start: int) -> int:
    """Return the first free port in [start, start+PORT_SCAN_RANGE]."""
    for port in range(start, start + PORT_SCAN_RANGE + 1):
        if _port_is_free(port):
            return port
    raise RuntimeError(
        f"No hay puertos libres en {start}..{start + PORT_SCAN_RANGE} para CDP"
    )


def launch(cfg: Config, port: int) -> subprocess.Popen:
    """Spawn the browser process with CDP enabled. Caller waits for /json/version."""
    exe = find_browser(cfg)
    cfg.profile_dir.mkdir(parents=True, exist_ok=True)
    args = [exe, *chrome_flags(cfg, port)]
    # DETACHED so the browser outlives transient parent hiccups but we still hold the handle.
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
