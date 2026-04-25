"""JSON-RPC 2.0 helpers for hand-rolled MCP transports.

This module is intentionally tiny: just enough of JSON-RPC 2.0 to encode and
parse one message at a time, plus the standard error codes the MCP server
uses. There is no framing logic here — that lives in
:mod:`mcp_tool_server.transport`, which delimits messages by newline.
"""

from __future__ import annotations

import json
from typing import Any

JSONRPC_VERSION = "2.0"

# Standard JSON-RPC 2.0 error codes (https://www.jsonrpc.org/specification).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def parse_message(line: str) -> dict[str, Any]:
    """Parse a single JSON-RPC message from a line of text.

    Raises ``ValueError`` if the payload is not a JSON object — callers
    should translate this to a JSON-RPC ``PARSE_ERROR``.
    """

    obj = json.loads(line)
    if not isinstance(obj, dict):
        raise ValueError("JSON-RPC message must be a JSON object")
    return obj


def encode_message(d: dict[str, Any]) -> str:
    """Serialize a JSON-RPC message and append a trailing newline.

    The newline is part of the line-delimited framing every stdio MCP client
    expects; do not strip it.
    """

    return json.dumps(d, separators=(",", ":")) + "\n"


def make_response(id: Any, result: Any) -> dict[str, Any]:
    """Build a successful JSON-RPC response envelope."""

    return {"jsonrpc": JSONRPC_VERSION, "id": id, "result": result}


def make_error(
    id: Any,
    code: int,
    message: str,
    data: Any | None = None,
) -> dict[str, Any]:
    """Build a JSON-RPC error response envelope.

    ``id`` may be ``None`` for parse-error responses where the request id
    could not be recovered.
    """

    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "error": error}
