"""Serialize a flat AX node list into compact indented text with @eN refs.

Output example:
    @e1 button "Iniciar sesion"
    @e2 textbox "Email" {required}
      @e3 heading "Bienvenido"
"""

from __future__ import annotations

from typing import Any

from ..config import STATIC_TEXT_TRUNCATE
from .filter import compact_attrs, keep, name_of, role_of
from .refmap import RefMap


def _truncate(text: str) -> str:
    if len(text) > STATIC_TEXT_TRUNCATE:
        return text[: STATIC_TEXT_TRUNCATE - 1] + "…"
    return text


def _label(node: dict[str, Any]) -> str:
    role = role_of(node)
    name = _truncate(name_of(node))
    parts = [role]
    if name:
        parts.append(f'"{name}"')
    line = " ".join(parts)
    return line + compact_attrs(node)


def serialize(
    ax_nodes: list[dict[str, Any]],
    refmap: RefMap,
    interactive_only: bool = True,
    session_id: str | None = None,
) -> str:
    """Walk the AX tree depth-first, assign refs to kept nodes, return text.

    ``ax_nodes`` is the flat list from Accessibility.getFullAXTree. Nodes carry
    ``nodeId`` and ``childIds`` to reconstruct the hierarchy.
    """
    refmap.current_session = session_id
    by_id = {n["nodeId"]: n for n in ax_nodes}
    child_ids = {cid for n in ax_nodes for cid in (n.get("childIds") or [])}
    roots = [n for n in ax_nodes if n["nodeId"] not in child_ids]

    lines: list[str] = []

    def walk(node: dict[str, Any], depth: int) -> None:
        next_depth = depth
        if keep(node, interactive_only):
            ref = refmap.assign(
                backend_node_id=node["backendDOMNodeId"],
                role=role_of(node),
                name=name_of(node),
                session_id=session_id,
            )
            indent = "  " * depth
            lines.append(f"{indent}{ref} {_label(node)}".rstrip())
            next_depth = depth + 1
        for cid in node.get("childIds") or []:
            child = by_id.get(cid)
            if child is not None:
                walk(child, next_depth)

    for root in roots:
        walk(root, 0)

    return "\n".join(lines)
