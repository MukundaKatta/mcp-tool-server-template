"""Allow ``python -m mcp_tool_server`` as an alias for the ``mts`` CLI."""

from .cli import main

raise SystemExit(main())
