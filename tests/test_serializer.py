from browser_mcp.snapshot.refmap import RefMap
from browser_mcp.snapshot.serializer import serialize


def _node(node_id, role, name, backend, children=None, ignored=False, props=None):
    return {
        "nodeId": node_id,
        "role": {"value": role},
        "name": {"value": name},
        "backendDOMNodeId": backend,
        "ignored": ignored,
        "childIds": children or [],
        "properties": props or [],
    }


def _fixture():
    # root(WebArea) -> [heading, form] ; form -> [email textbox(required), submit button]
    return [
        _node("1", "WebArea", "Login", 100, children=["2", "3"]),
        _node("2", "heading", "Bienvenido", 101),
        _node("3", "form", "", 102, children=["4", "5"]),
        _node(
            "4", "textbox", "Email", 103,
            props=[{"name": "required", "value": {"value": True}}],
        ),
        _node("5", "button", "Entrar", 104),
    ]


def test_serialize_interactive_only_lists_refs_with_attrs():
    rm = RefMap()
    text = serialize(_fixture(), rm, interactive_only=True)
    lines = text.splitlines()
    assert lines == ['@e1 textbox "Email" {required}', '@e2 button "Entrar"']
    assert rm.resolve("@e1").backend_node_id == 103
    assert rm.resolve("@e2").role == "button"


def test_serialize_includes_headings_when_not_interactive_only():
    rm = RefMap()
    text = serialize(_fixture(), rm, interactive_only=False)
    assert '@e1 heading "Bienvenido"' in text
    assert "textbox" in text and "button" in text


def test_ignored_and_missing_backend_nodes_are_skipped():
    rm = RefMap()
    nodes = [
        _node("1", "WebArea", "", 1, children=["2", "3"]),
        _node("2", "button", "Hidden", 2, ignored=True),
        {"nodeId": "3", "role": {"value": "button"}, "name": {"value": "NoBackend"},
         "backendDOMNodeId": None, "ignored": False, "childIds": [], "properties": []},
    ]
    text = serialize(nodes, rm, interactive_only=True)
    assert text == ""
    assert len(rm) == 0


def test_long_static_text_is_truncated():
    rm = RefMap()
    long_name = "x" * 300
    nodes = [_node("1", "heading", long_name, 1)]
    text = serialize(nodes, rm, interactive_only=False)
    assert "…" in text
    assert len(text) < 200
