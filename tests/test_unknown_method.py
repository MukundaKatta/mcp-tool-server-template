"""Unknown JSON-RPC methods must return -32601."""

from __future__ import annotations

from mcp_tool_server import protocol
from mcp_tool_server.server import Server


def test_unknown_method_returns_method_not_found():
    server = Server(name="t", version="0.0.1")
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "no/such/method"})

    assert response is not None
    assert response["error"]["code"] == protocol.METHOD_NOT_FOUND
    assert "no/such/method" in response["error"]["message"]


def test_unknown_notification_is_silently_ignored():
    server = Server(name="t", version="0.0.1")
    # No ``id`` -> notification -> JSON-RPC forbids responding even on
    # unknown methods.
    response = server.handle({"jsonrpc": "2.0", "method": "no/such/method"})
    assert response is None
