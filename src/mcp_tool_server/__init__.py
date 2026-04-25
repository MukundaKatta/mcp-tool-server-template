"""mcp-tool-server-template: a dependency-free MCP server template.

Public surface re-exports:
- ``Server`` — register tools and dispatch JSON-RPC messages.
- ``tool`` — decorator alias for ``Server.tool`` (used after binding to an
  instance, see :class:`Server`).
- ``run_stdio`` — read/write JSON-RPC messages over stdio.
"""

from .server import Server, tool
from .transport import run_stdio

__all__ = ["Server", "tool", "run_stdio"]
__version__ = "0.1.0"
