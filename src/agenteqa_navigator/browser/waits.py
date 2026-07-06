"""Fast page-readiness waits driven by CDP events, not fixed sleeps."""

from __future__ import annotations

import asyncio

from ..cdp.connection import CDPConnection
from ..config import (
    NAVIGATION_TIMEOUT,
    NETWORKIDLE_QUIET_SECONDS,
    READYSTATE_POLL_TIMEOUT,
    WAIT_FOR_POLL_INTERVAL,
)


async def wait_load(conn: CDPConnection, session_id: str | None, timeout: float = NAVIGATION_TIMEOUT) -> None:
    """Wait for Page.loadEventFired, then briefly poll document.readyState."""
    loop = asyncio.get_event_loop()
    fired: asyncio.Future[None] = loop.create_future()

    def on_load(_params: dict, sid: str | None) -> None:
        if not fired.done():
            fired.set_result(None)

    conn.on("Page.loadEventFired", on_load)
    try:
        await asyncio.wait_for(fired, timeout=timeout)
    except TimeoutError:
        pass  # fall through to readyState poll; partial load is still usable
    finally:
        conn.off("Page.loadEventFired", on_load)

    deadline = loop.time() + READYSTATE_POLL_TIMEOUT
    while loop.time() < deadline:
        ready = await _eval(conn, "document.readyState", session_id)
        if ready == "complete":
            return
        await asyncio.sleep(0.05)


async def wait_networkidle(
    conn: CDPConnection,
    session_id: str | None,
    quiet: float = NETWORKIDLE_QUIET_SECONDS,
    timeout: float = NAVIGATION_TIMEOUT,
) -> None:
    """Wait until no in-flight requests for ``quiet`` seconds (capped by timeout)."""
    loop = asyncio.get_event_loop()
    inflight = 0
    last_change = loop.time()

    def bump(delta: int) -> None:
        nonlocal inflight, last_change
        inflight = max(0, inflight + delta)
        last_change = loop.time()

    def on_send(_p: dict, _s: str | None) -> None:
        bump(+1)

    def on_done(_p: dict, _s: str | None) -> None:
        bump(-1)

    conn.on("Network.requestWillBeSent", on_send)
    conn.on("Network.loadingFinished", on_done)
    conn.on("Network.loadingFailed", on_done)
    try:
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if inflight == 0 and (loop.time() - last_change) >= quiet:
                return
            await asyncio.sleep(0.05)
    finally:
        conn.off("Network.requestWillBeSent", on_send)
        conn.off("Network.loadingFinished", on_done)
        conn.off("Network.loadingFailed", on_done)


async def wait_for_text(
    conn: CDPConnection, text: str, session_id: str | None, timeout_ms: int
) -> bool:
    """Poll until ``text`` appears in document body innerText."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_ms / 1000.0
    expr = "document.body ? document.body.innerText : ''"
    while loop.time() < deadline:
        body = await _eval(conn, expr, session_id) or ""
        if text in body:
            return True
        await asyncio.sleep(WAIT_FOR_POLL_INTERVAL)
    return False


async def _eval(conn: CDPConnection, expression: str, session_id: str | None):
    res = await conn.call(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True},
        session_id=session_id,
    )
    return (res.get("result") or {}).get("value")
