"""Keyboard input via CDP Input domain: human typing and named key presses."""

from __future__ import annotations

import asyncio
import random

from ..cdp.connection import CDPConnection
from ..config import HUMAN_TYPE_DELAY

# Minimal map of named keys to CDP key descriptors.
_KEY_MAP: dict[str, dict] = {
    "Enter": {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13},
    "Tab": {"key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9},
    "Escape": {"key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27},
    "Backspace": {"key": "Backspace", "code": "Backspace", "windowsVirtualKeyCode": 8},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "windowsVirtualKeyCode": 40},
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "windowsVirtualKeyCode": 38},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "windowsVirtualKeyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "windowsVirtualKeyCode": 39},
}


async def type_text(
    conn: CDPConnection, text: str, session_id: str | None, human: bool = True
) -> None:
    """Type text char-by-char so input/keyup handlers fire like a real user."""
    if not human:
        await conn.call("Input.insertText", {"text": text}, session_id)
        return
    for ch in text:
        await conn.call("Input.dispatchKeyEvent", {"type": "keyDown", "text": ch}, session_id)
        await conn.call("Input.dispatchKeyEvent", {"type": "keyUp", "text": ch}, session_id)
        await asyncio.sleep(random.uniform(*HUMAN_TYPE_DELAY))


async def press_key(conn: CDPConnection, key: str, session_id: str | None) -> None:
    """Press a single named key (Enter, Tab, ArrowDown, ...)."""
    desc = _KEY_MAP.get(key)
    if desc is None:
        raise ValueError(f"Tecla no soportada: {key}. Soportadas: {sorted(_KEY_MAP)}")
    await conn.call("Input.dispatchKeyEvent", {"type": "rawKeyDown", **desc}, session_id)
    await conn.call("Input.dispatchKeyEvent", {"type": "keyUp", **desc}, session_id)
