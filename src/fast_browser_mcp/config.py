"""Central configuration: paths, Chrome flags, timeouts. No magic numbers elsewhere."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --- Project paths -----------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE_DIR = PROJECT_ROOT / ".chrome-profile"

# --- CDP / networking --------------------------------------------------------
DEFAULT_DEBUG_PORT = 9222
PORT_SCAN_RANGE = 100  # scan DEFAULT_DEBUG_PORT .. +PORT_SCAN_RANGE for a free port
DEVTOOLS_HOST = "127.0.0.1"

# --- Timeouts (seconds) ------------------------------------------------------
CHROME_STARTUP_TIMEOUT = 15.0      # wait for /json/version to respond
CDP_COMMAND_TIMEOUT = 30.0         # per send_raw call
NAVIGATION_TIMEOUT = 30.0          # wait="load" cap
READYSTATE_POLL_TIMEOUT = 2.0      # extra poll after load event
NETWORKIDLE_QUIET_SECONDS = 0.5    # silence window for wait="networkidle"
WAIT_FOR_POLL_INTERVAL = 0.1       # wait_for(text/ref_gone) poll cadence

# --- Human-like interaction delays (seconds) ---------------------------------
HUMAN_MOUSE_MOVE_DELAY = (0.02, 0.06)
HUMAN_MOUSE_PRESS_DELAY = (0.03, 0.08)
HUMAN_TYPE_DELAY = (0.01, 0.04)

# --- Snapshot ----------------------------------------------------------------
STATIC_TEXT_TRUNCATE = 120  # max chars kept for headings / static text


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    """Resolved runtime configuration. Built once from environment."""

    profile_dir: Path = DEFAULT_PROFILE_DIR
    headless: bool = False
    debug_port: int = DEFAULT_DEBUG_PORT
    human_delays: bool = True
    chrome_path: str | None = None  # explicit override; else auto-detect

    extra_flags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_env(cls) -> "Config":
        profile = os.environ.get("Fast-Browser-MCP_PROFILE_DIR")
        port_raw = os.environ.get("Fast-Browser-MCP_DEBUG_PORT")
        return cls(
            profile_dir=Path(profile) if profile else DEFAULT_PROFILE_DIR,
            headless=_env_bool("Fast-Browser-MCP_HEADLESS", False),
            debug_port=int(port_raw) if port_raw else DEFAULT_DEBUG_PORT,
            human_delays=_env_bool("Fast-Browser-MCP_HUMAN_DELAYS", True),
            chrome_path=(
                os.environ.get("CHROME_PATH")
                or os.environ.get("CHROME_EXECUTABLE")
                or None
            ),
            extra_flags=tuple(
                f for f in os.environ.get("CHROME_EXTRA_ARGS", "").split() if f
            ),
        )


def chrome_flags(cfg: Config, port: int) -> list[str]:
    """Speed-tuned Chrome launch flags for a dedicated automation profile."""
    flags = [
        f"--remote-debugging-port={port}",
        f"--user-data-dir={cfg.profile_dir}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-features=Translate,MediaRouter,OptimizationHints",
        "--disable-popup-blocking",
    ]
    if cfg.headless:
        flags.append("--headless=new")
    flags.extend(cfg.extra_flags)
    return flags
