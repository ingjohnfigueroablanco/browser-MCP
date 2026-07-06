"""Decide which accessibility-tree nodes are worth showing to the agent."""

from __future__ import annotations

from typing import Any

# Roles that are interactive (always kept if they carry a backend node).
INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "link",
        "textbox",
        "searchbox",
        "combobox",
        "checkbox",
        "radio",
        "switch",
        "menuitem",
        "menuitemcheckbox",
        "menuitemradio",
        "tab",
        "option",
        "slider",
        "spinbutton",
        "listbox",
        "textarea",
    }
)

# Roles kept only when they provide a non-empty accessible name (context anchors).
CONTEXT_ROLES = frozenset({"heading", "image", "StaticText", "text"})


def role_of(node: dict[str, Any]) -> str:
    return (node.get("role") or {}).get("value", "") or ""


def name_of(node: dict[str, Any]) -> str:
    return ((node.get("name") or {}).get("value", "") or "").strip()


def _prop(node: dict[str, Any], prop_name: str) -> Any:
    for prop in node.get("properties", []) or []:
        if prop.get("name") == prop_name:
            return (prop.get("value") or {}).get("value")
    return None


def keep(node: dict[str, Any], interactive_only: bool) -> bool:
    """Whether a node should appear in the serialized snapshot."""
    if node.get("ignored"):
        return False
    if node.get("backendDOMNodeId") is None:
        return False
    role = role_of(node)
    if role in INTERACTIVE_ROLES:
        return True
    if not interactive_only and role in CONTEXT_ROLES and name_of(node):
        return True
    return False


def is_interactive(node: dict[str, Any]) -> bool:
    return role_of(node) in INTERACTIVE_ROLES


def compact_attrs(node: dict[str, Any]) -> str:
    """Render the few state attributes the agent needs, e.g. {required,checked}."""
    flags: list[str] = []
    for name in ("required", "disabled", "expanded"):
        if _prop(node, name) is True:
            flags.append(name)
    checked = _prop(node, "checked")
    if checked in ("true", True):
        flags.append("checked")
    elif checked == "mixed":
        flags.append("mixed")
    return " {" + ",".join(flags) + "}" if flags else ""
