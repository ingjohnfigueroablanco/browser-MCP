"""Form interactions: fill text fields and select dropdown options."""

from __future__ import annotations

from ..cdp.connection import CDPConnection
from ..snapshot.refmap import RefEntry
from . import keyboard
from .mouse import click


async def fill(
    conn: CDPConnection,
    entry: RefEntry,
    text: str,
    human: bool = True,
    submit: bool = False,
) -> None:
    """Focus the field (via a real click), clear it, type text, optionally submit."""
    await click(conn, entry, human=human)
    await conn.call("DOM.focus", {"backendNodeId": entry.backend_node_id}, entry.session_id)
    # Select-all + delete so we replace any existing value deterministically.
    await _select_all_clear(conn, entry.session_id)
    await keyboard.type_text(conn, text, entry.session_id, human=human)
    if submit:
        await keyboard.press_key(conn, "Enter", entry.session_id)


async def _select_all_clear(conn: CDPConnection, session_id: str | None) -> None:
    res = await conn.call(
        "Runtime.evaluate",
        {
            "expression": (
                "(()=>{const el=document.activeElement;"
                "if(el&&'value' in el){"
                "const nativeSetter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                "nativeSetter.call(el,'');"
                "el.dispatchEvent(new Event('input',{bubbles:true}));return true;}"
                "return false;})()"
            ),
            "returnByValue": True,
        },
        session_id=session_id,
    )
    return (res.get("result") or {}).get("value")


async def select_option(
    conn: CDPConnection,
    entry: RefEntry,
    value: str | None = None,
    label: str | None = None,
) -> None:
    """Set a <select> to a value or visible label and dispatch change."""
    if value is None and label is None:
        raise ValueError("select_option requiere value o label")
    # Resolve the node into a JS object, then run the chooser with `this` = the <select>.
    obj = await conn.call(
        "DOM.resolveNode",
        {"backendNodeId": entry.backend_node_id},
        session_id=entry.session_id,
    )
    object_id = (obj.get("object") or {}).get("objectId")
    target = label if label is not None else value
    by_label = label is not None
    await conn.call(
        "Runtime.callFunctionOn",
        {
            "objectId": object_id,
            "functionDeclaration": (
                "function(target, byLabel){"
                " const sel=this;"
                " for(const opt of sel.options){"
                "  if((byLabel&&opt.text===target)||(!byLabel&&opt.value===target)){"
                # Use the native setter so React's onChange fires correctly.
                "   const nativeSetter=Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set;"
                "   nativeSetter.call(sel,opt.value);"
                "   sel.dispatchEvent(new Event('input',{bubbles:true}));"
                "   sel.dispatchEvent(new Event('change',{bubbles:true}));"
                "   return true;}"
                " } return false;}"
            ),
            "arguments": [{"value": target}, {"value": by_label}],
            "returnByValue": True,
        },
        session_id=entry.session_id,
    )
