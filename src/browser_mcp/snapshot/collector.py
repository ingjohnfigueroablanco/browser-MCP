"""Collect accessibility snapshots from the page and its (OOPIF) iframes."""

from __future__ import annotations

import asyncio

from ..cdp.connection import CDPConnection
from .refmap import RefMap
from .serializer import serialize

_MIN_USEFUL_NODES = 5   # below this, assume SPA hasn't rendered and retry
_RENDER_POLL_DELAY = 0.25
_RENDER_MAX_RETRIES = 12  # up to 3 seconds total


async def _get_ax_nodes(
    conn: CDPConnection, session_id: str | None
) -> list[dict]:
    """Fetch AX tree with retry until React/SPA finishes rendering."""
    for _ in range(_RENDER_MAX_RETRIES):
        ax = await conn.call("Accessibility.getFullAXTree", session_id=session_id)
        nodes = ax.get("nodes", [])
        if len(nodes) >= _MIN_USEFUL_NODES:
            return nodes
        await asyncio.sleep(_RENDER_POLL_DELAY)
    return nodes  # return whatever we got after max retries


async def capture(
    conn: CDPConnection,
    refmap: RefMap,
    session_id: str | None,
    child_sessions: list[str] | None = None,
    interactive_only: bool = True,
) -> tuple[str, int]:
    """Capture a snapshot for the main session plus any attached iframe sessions.

    Returns (text, snapshot_id). ``refmap`` is reset to a new generation.
    """
    snapshot_id = refmap.begin()
    sessions: list[str | None] = [session_id, *(child_sessions or [])]
    blocks: list[str] = []

    for sid in sessions:
        nodes = await _get_ax_nodes(conn, sid)
        if not nodes:
            continue
        text = serialize(nodes, refmap, interactive_only=interactive_only, session_id=sid)
        if text:
            if sid and sid != session_id:
                blocks.append(f"# iframe [{sid[:8]}]\n{text}")
            else:
                blocks.append(text)

    return "\n".join(blocks), snapshot_id
