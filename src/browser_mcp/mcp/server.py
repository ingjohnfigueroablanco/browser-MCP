"""FastMCP server wiring: lifespan holds the long-lived BrowserManager (the daemon)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

from ..browser.manager import BrowserManager


@dataclass
class AppCtx:
    browser: BrowserManager


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppCtx]:
    browser = BrowserManager()  # Chrome is NOT launched until browser_start.
    try:
        yield AppCtx(browser=browser)
    finally:
        await browser.shutdown(kill=False)


mcp = FastMCP("Browser-MCP-Navigator", lifespan=lifespan)


def get_browser() -> BrowserManager:
    return mcp.get_context().request_context.lifespan_context.browser


# Import tool registrations (decorators run on import).
from . import tools  # noqa: E402,F401
