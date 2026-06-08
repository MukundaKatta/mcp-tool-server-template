"""Unit tests for the example tool implementations in ``tools.py``."""

from __future__ import annotations

import re

from mcp_tool_server import tools

# Matches an ISO-8601 timestamp with an offset (e.g. "+00:00" for UTC).
_ISO_WITH_OFFSET = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*[+-]\d{2}:\d{2}$")


def test_echo_returns_input_unchanged():
    assert tools.echo("hello") == "hello"
    assert tools.echo("") == ""


def test_add_sums_numbers():
    assert tools.add(2, 3) == 5
    assert tools.add(-1.5, 0.5) == -1.0


def test_current_time_default_is_utc_iso():
    stamp = tools.current_time()
    assert _ISO_WITH_OFFSET.match(stamp)
    assert stamp.endswith("+00:00")  # UTC offset


def test_current_time_resolves_named_zone():
    stamp = tools.current_time("America/New_York")
    assert _ISO_WITH_OFFSET.match(stamp)


def test_current_time_unknown_zone_falls_back_to_utc():
    stamp = tools.current_time("Not/AReal/Zone")
    assert stamp.endswith("+00:00")


def test_current_time_malformed_zone_falls_back_to_utc():
    # ZoneInfo raises ValueError (not ZoneInfoNotFoundError) for these inputs;
    # the documented contract is to fall back to UTC rather than raise.
    for bad in ("", "../../etc/passwd"):
        stamp = tools.current_time(bad)
        assert stamp.endswith("+00:00"), bad
