"""Initialize handshake tests."""

from __future__ import annotations

from mcp_tool_server.server import PROTOCOL_VERSION, Server


def test_initialize_returns_server_info():
    server = Server(name="test-server", version="9.9.9")
    response = server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )

    assert response is not None
    result = response["result"]

    assert result["protocolVersion"] == PROTOCOL_VERSION
    assert result["serverInfo"] == {"name": "test-server", "version": "9.9.9"}
    assert result["capabilities"] == {"tools": {}}


def test_initialized_notification_has_no_response():
    server = Server(name="test-server", version="0.0.1")
    # Notifications have no ``id``.
    response = server.handle({"jsonrpc": "2.0", "method": "initialized"})
    assert response is None


def test_namespaced_initialized_notification_has_no_response():
    server = Server(name="test-server", version="0.0.1")
    response = server.handle(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert response is None
