"""Example tools that ship with the template.

Replace or extend these to wire up your own MCP server. Each function is a
plain Python callable; the tool is registered in :mod:`mcp_tool_server.cli`
along with its JSON Schema and description.
"""

from __future__ import annotations

# Imported under aliases so the ``timezone`` parameter on ``current_time``
# can't accidentally shadow the stdlib symbol.
from datetime import datetime
from datetime import timezone as _dt_timezone

try:
    # zoneinfo lives in stdlib from Python 3.9+ (we require 3.10+).
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover — defensive, never hit on 3.10+
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment,misc]


def echo(text: str) -> str:
    """Return ``text`` unchanged. Smallest possible tool — useful as a probe."""

    return text


def current_time(timezone: str = "UTC") -> str:
    """Return the current ISO-8601 timestamp in the given IANA ``timezone``.

    Falls back to UTC if ``zoneinfo`` can't resolve the name (e.g. on a system
    without the tzdata package installed).
    """

    if timezone == "UTC" or ZoneInfo is None:
        return datetime.now(tz=_dt_timezone.utc).isoformat()

    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        # ZoneInfoNotFoundError covers unknown zone names; ValueError covers
        # malformed keys (empty string, path-traversal-style inputs like
        # "../../etc/passwd"). Both mean "can't resolve" — fall back to UTC.
        return datetime.now(tz=_dt_timezone.utc).isoformat()

    return datetime.now(tz=tz).isoformat()


def add(a: float, b: float) -> float:
    """Return ``a + b``. Demonstrates a tool that takes numeric arguments."""

    return a + b
