"""tools/call dispatch + validation tests."""

from __future__ import annotations

from mcp_tool_server import protocol
from mcp_tool_server.server import Server


def _server_with_echo() -> Server:
    server = Server(name="t", version="0.0.1")

    @server.tool(
        name="echo",
        description="Echo back text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
    def _echo(text: str) -> str:
        return text

    return server


def test_tools_call_returns_text_content_on_success():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": "hi"}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["content"][0] == {"type": "text", "text": "hi"}
    assert "isError" not in result or result["isError"] is False


def test_tools_call_missing_required_arg_is_tool_error():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "text" in result["content"][0]
    assert "text" in result["content"][0]["text"]  # mentions the missing arg


def test_tools_call_unknown_tool_is_tool_error():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "does-not-exist", "arguments": {}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "Unknown tool" in result["content"][0]["text"]


def test_tools_call_non_dict_arguments_is_invalid_params():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": "not-a-dict"},
        }
    )

    assert response is not None
    assert "error" in response
    assert response["error"]["code"] == protocol.INVALID_PARAMS


def test_tools_call_non_dict_params_is_invalid_params():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": "totally-wrong",
        }
    )

    assert response is not None
    assert response["error"]["code"] == protocol.INVALID_PARAMS


def test_tools_call_non_string_name_is_invalid_params():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": 42, "arguments": {}},
        }
    )

    assert response is not None
    assert response["error"]["code"] == protocol.INVALID_PARAMS


def test_tools_call_type_mismatch_is_tool_error():
    server = _server_with_echo()
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "echo", "arguments": {"text": 123}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True


def test_tools_call_tool_exception_is_surfaced_as_tool_error():
    server = Server(name="t", version="0.0.1")

    @server.tool(
        name="boom",
        description="Always raises.",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    def _boom() -> str:
        raise RuntimeError("kaboom")

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "boom", "arguments": {}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "kaboom" in result["content"][0]["text"]
