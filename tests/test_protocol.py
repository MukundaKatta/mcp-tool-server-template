"""Unit tests for the JSON-RPC helpers."""

from __future__ import annotations

import json

import pytest

from mcp_tool_server import protocol


def test_encode_message_ends_with_newline():
    encoded = protocol.encode_message({"jsonrpc": "2.0", "id": 1, "result": {}})
    assert encoded.endswith("\n")


def test_encode_parse_round_trip():
    original = {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
    line = protocol.encode_message(original)
    parsed = protocol.parse_message(line.rstrip("\n"))
    assert parsed == original


def test_parse_message_rejects_non_object():
    with pytest.raises(ValueError):
        protocol.parse_message("[1, 2, 3]")


def test_parse_message_rejects_bad_json():
    with pytest.raises(json.JSONDecodeError):
        protocol.parse_message("{not json")


def test_make_response_envelope():
    resp = protocol.make_response(42, {"ok": True})
    assert resp == {"jsonrpc": "2.0", "id": 42, "result": {"ok": True}}


def test_make_error_envelope_basic():
    err = protocol.make_error(1, protocol.METHOD_NOT_FOUND, "nope")
    assert err == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "nope"},
    }


def test_make_error_envelope_with_data():
    err = protocol.make_error(None, protocol.PARSE_ERROR, "bad", data={"raw": "x"})
    assert err["error"]["data"] == {"raw": "x"}
    assert err["id"] is None


def test_error_codes_are_jsonrpc_standard():
    assert protocol.PARSE_ERROR == -32700
    assert protocol.INVALID_REQUEST == -32600
    assert protocol.METHOD_NOT_FOUND == -32601
    assert protocol.INVALID_PARAMS == -32602
    assert protocol.INTERNAL_ERROR == -32603
    assert protocol.JSONRPC_VERSION == "2.0"
