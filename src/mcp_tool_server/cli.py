"""CLI entry point for the example server.

The ``mts`` binary (declared in ``pyproject.toml`` under ``project.scripts``)
calls :func:`main`, which wires up the example tools from
:mod:`mcp_tool_server.tools` and either starts the stdio loop or prints the
registered tools for sanity checking.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__, tools
from .server import Server
from .transport import run_stdio


def build_server() -> Server:
    """Build the example server with all bundled tools registered.

    Pulled out into its own function so :func:`main` and tests can share the
    same registration without duplicating schemas.
    """

    server = Server(name="mcp-tool-server-template", version=__version__)

    @server.tool(
        name="echo",
        description="Echo back the given text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )
    def _echo(text: str) -> str:
        return tools.echo(text)

    @server.tool(
        name="current_time",
        description="Return the current ISO-8601 timestamp in the given IANA timezone.",
        input_schema={
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone name, e.g. 'UTC' or 'America/New_York'.",
                }
            },
            "required": [],
        },
    )
    def _current_time(timezone: str = "UTC") -> str:
        return tools.current_time(timezone)

    @server.tool(
        name="add",
        description="Add two numbers and return the sum.",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    )
    def _add(a: float, b: float) -> float:
        return tools.add(a, b)

    return server


def _cmd_run(_args: argparse.Namespace) -> int:
    """Start the stdio loop. Intended to be launched by an MCP client."""

    server = build_server()
    run_stdio(server)
    return 0


def _cmd_list_tools(_args: argparse.Namespace) -> int:
    """Print registered tools to stdout — a quick sanity check for humans."""

    server = build_server()
    for tool_name, tdef in server.tools.items():
        print(f"{tool_name}\t{tdef.description}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Argparse entry point for the ``mts`` console script."""

    parser = argparse.ArgumentParser(
        prog="mts",
        description="Run the example MCP tool server template.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the MCP server over stdio (intended for MCP clients).",
    )
    run_parser.set_defaults(func=_cmd_run)

    list_parser = subparsers.add_parser(
        "list-tools",
        help="Print the names and descriptions of registered tools.",
    )
    list_parser.set_defaults(func=_cmd_list_tools)

    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover — module entry shim
    sys.exit(main())
