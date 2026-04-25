"""Stdio transport for the MCP server.

MCP's stdio framing is one JSON object per line on stdin, one per line on
stdout. We keep it dumb: read a line, parse, dispatch, encode, flush.
"""

from __future__ import annotations

import json
import sys
from typing import IO

from . import protocol
from .server import Server


def run_stdio(
    server: Server,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
) -> None:
    """Run the server's read/dispatch/write loop until EOF.

    ``stdin``/``stdout`` default to the real ``sys.stdin``/``sys.stdout`` but
    can be swapped for in-memory pipes during tests.
    """

    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout

    while True:
        line = in_stream.readline()
        if not line:
            # readline returns "" only on EOF — newlines come back as "\n".
            return

        line = line.strip()
        if not line:
            # Tolerate blank/keepalive lines; clients sometimes send them.
            continue

        try:
            message = protocol.parse_message(line)
        except (json.JSONDecodeError, ValueError) as exc:
            response = protocol.make_error(
                None,
                protocol.PARSE_ERROR,
                f"Parse error: {exc}",
            )
            out_stream.write(protocol.encode_message(response))
            out_stream.flush()
            continue

        try:
            response = server.handle(message)
        except Exception as exc:  # noqa: BLE001 — last-resort handler crash
            response = protocol.make_error(
                message.get("id"),
                protocol.INTERNAL_ERROR,
                f"Internal error: {exc}",
            )

        if response is not None:
            out_stream.write(protocol.encode_message(response))
            out_stream.flush()
