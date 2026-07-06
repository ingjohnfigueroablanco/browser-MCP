"""Resolve the browser-level WebSocket debugger URL from a running Chrome."""

from __future__ import annotations

import httpx

from ..config import CHROME_STARTUP_TIMEOUT, DEVTOOLS_HOST


def version_endpoint(port: int) -> str:
    return f"http://{DEVTOOLS_HOST}:{port}/json/version"


def parse_ws_url(version_payload: dict) -> str:
    """Extract webSocketDebuggerUrl from a /json/version JSON payload."""
    ws = version_payload.get("webSocketDebuggerUrl")
    if not ws:
        raise ValueError("No webSocketDebuggerUrl in /json/version payload")
    return ws


async def probe_version(port: int, timeout: float = 1.0) -> dict | None:
    """Return /json/version payload if Chrome is already listening, else None."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(version_endpoint(port))
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


async def wait_for_version(port: int, timeout: float = CHROME_STARTUP_TIMEOUT) -> dict:
    """Poll /json/version until Chrome answers or timeout elapses."""
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    last_err: Exception | None = None
    while asyncio.get_event_loop().time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(version_endpoint(port))
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            last_err = exc
            await asyncio.sleep(0.15)
    raise TimeoutError(
        f"Chrome did not expose CDP on port {port} within {timeout}s"
    ) from last_err
