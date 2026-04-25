"""tools/list response shape tests."""

from __future__ import annotations

from mcp_tool_server.server import Server


def _make_server_with_two_tools() -> Server:
    server = Server(name="t", version="0.0.1")

    @server.tool(
        name="echo",
        description="Echoes text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
    def _echo(text: str) -> str:
        return text

    @server.tool(
        name="add",
        description="Adds two numbers.",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    def _add(a: float, b: float) -> float:
        return a + b

    return server


def test_tools_list_returns_all_registered_tools():
    server = _make_server_with_two_tools()
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    tools = response["result"]["tools"]
    by_name = {t["name"]: t for t in tools}

    assert set(by_name) == {"echo", "add"}

    echo = by_name["echo"]
    assert echo["description"] == "Echoes text."
    assert echo["inputSchema"]["required"] == ["text"]
    assert echo["inputSchema"]["properties"]["text"]["type"] == "string"

    add = by_name["add"]
    assert add["description"] == "Adds two numbers."
    assert add["inputSchema"]["required"] == ["a", "b"]


def test_tools_list_is_empty_when_no_tools_registered():
    server = Server(name="t", version="0.0.1")
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    assert response["result"]["tools"] == []
