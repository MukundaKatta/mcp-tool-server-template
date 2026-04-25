"""End-to-end stdio tests.

Runs the full read-loop in two ways:

1. **In-memory pipes** — fast, no subprocess; verifies the transport reads
   line-delimited JSON-RPC and writes responses correctly.
2. **Subprocess** — spawns ``python -m mcp_tool_server.cli run`` and feeds it
   real bytes over stdin, mirroring what an MCP client does.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import threading

from mcp_tool_server.cli import build_server
from mcp_tool_server.transport import run_stdio


def _send_and_collect(messages: list[dict]) -> list[dict]:
    """Pipe ``messages`` through ``run_stdio`` and return the responses."""

    server = build_server()
    stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    stdout = io.StringIO()
    run_stdio(server, stdin=stdin, stdout=stdout)

    raw = stdout.getvalue().strip()
    if not raw:
        return []
    return [json.loads(line) for line in raw.splitlines()]


def test_in_memory_initialize_then_tools_list():
    responses = _send_and_collect(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
    )

    assert len(responses) == 2

    init = responses[0]
    assert init["id"] == 1
    assert init["result"]["serverInfo"]["name"] == "mcp-tool-server-template"

    tools_list = responses[1]
    assert tools_list["id"] == 2
    names = {t["name"] for t in tools_list["result"]["tools"]}
    assert {"echo", "current_time", "add"} <= names


def test_in_memory_parse_error_returns_error_envelope():
    server = build_server()
    stdin = io.StringIO("{not valid json\n")
    stdout = io.StringIO()
    run_stdio(server, stdin=stdin, stdout=stdout)

    response = json.loads(stdout.getvalue().strip())
    assert response["error"]["code"] == -32700
    assert response["id"] is None


def test_in_memory_tool_call_round_trip():
    responses = _send_and_collect(
        [
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"text": "ping"}},
            }
        ]
    )

    assert len(responses) == 1
    assert responses[0]["result"]["content"][0]["text"] == "ping"


def test_subprocess_initialize_handshake():
    """Spawn the real CLI and exchange messages over stdio."""

    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_tool_server.cli", "run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        assert proc.stdin is not None
        assert proc.stdout is not None

        # Send two requests, then close stdin so the loop exits cleanly.
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        for req in requests:
            proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        proc.stdin.close()

        # Read stdout in a thread so a hang is bounded by communicate's timeout.
        out_lines: list[str] = []

        def _drain():
            assert proc.stdout is not None
            for line in proc.stdout:
                out_lines.append(line)

        t = threading.Thread(target=_drain, daemon=True)
        t.start()
        proc.wait(timeout=10)
        t.join(timeout=2)

        responses = [json.loads(line) for line in out_lines if line.strip()]
        assert len(responses) >= 2

        init = next(r for r in responses if r.get("id") == 1)
        assert init["result"]["serverInfo"]["name"] == "mcp-tool-server-template"

        tools = next(r for r in responses if r.get("id") == 2)
        names = {t["name"] for t in tools["result"]["tools"]}
        assert "echo" in names
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


def test_list_tools_subcommand_prints_tools(capsys):
    """``mts list-tools`` prints registered tools to stdout."""

    from mcp_tool_server.cli import main

    rc = main(["list-tools"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "echo" in captured.out
    assert "current_time" in captured.out
    assert "add" in captured.out
