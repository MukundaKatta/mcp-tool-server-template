"""Transport-agnostic MCP server core.

The :class:`Server` here knows nothing about stdio, sockets, or pipes — it
takes a parsed JSON-RPC dict and returns a response dict (or ``None`` for
notifications). The transport layer in :mod:`mcp_tool_server.transport` does
the actual I/O.

This split keeps the server trivially testable: the unit tests just call
``server.handle({...})`` and assert on the returned dict.
"""

from __future__ import annotations

from typing import Any, Callable, NamedTuple

from . import protocol

# MCP protocol version this server speaks. Matches the dated revisions Claude
# Desktop / Claude Code accept; bump when upgrading to a newer MCP spec.
PROTOCOL_VERSION = "2024-11-05"


class ToolDef(NamedTuple):
    """A registered tool: callable + JSON Schema + human description."""

    func: Callable[..., Any]
    input_schema: dict[str, Any]
    description: str


# JSON Schema "type" string -> Python type(s) accepted by ``isinstance``.
# JSON's "number" allows int or float; "integer" excludes float; everything
# else is a straight mapping.
_JSON_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def _type_matches(value: Any, json_type: str) -> bool:
    """Loose JSON-Schema-style ``type`` check.

    ``True``/``False`` are intentionally excluded from numeric matches:
    Python's ``bool`` is a subclass of ``int``, but accepting it for
    ``"integer"``/``"number"`` would let clients pass ``true`` where a number
    is required.
    """

    if json_type == "integer" and isinstance(value, bool):
        return False
    if json_type == "number" and isinstance(value, bool):
        return False
    expected = _JSON_TYPE_MAP.get(json_type)
    if expected is None:
        # Unknown type names pass through — schemas may use formats we don't
        # validate here, and we'd rather under-validate than reject good calls.
        return True
    return isinstance(value, expected)


def _validate_arguments(
    arguments: dict[str, Any],
    schema: dict[str, Any],
) -> str | None:
    """Minimal schema validation: ``required`` keys + per-property ``type``.

    Returns ``None`` on success, or a human-readable error string. We don't
    pull in ``jsonschema`` to keep the runtime dependency-free; this covers
    the cases tools care about in practice.
    """

    required = schema.get("required", []) or []
    for key in required:
        if key not in arguments:
            return f"Missing required argument: {key}"

    properties = schema.get("properties", {}) or {}
    for key, value in arguments.items():
        if key not in properties:
            continue
        prop_schema = properties[key]
        if not isinstance(prop_schema, dict):
            continue
        json_type = prop_schema.get("type")
        if isinstance(json_type, str) and not _type_matches(value, json_type):
            return f"Argument {key!r} must be of type {json_type}"

    return None


class Server:
    """An MCP server with hand-rolled JSON-RPC dispatch.

    Usage::

        server = Server(name="my-server", version="0.1.0")

        @server.tool(
            name="echo",
            description="Echo back the input.",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        )
        def echo(text: str) -> str:
            return text

        run_stdio(server)
    """

    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version
        self.tools: dict[str, ToolDef] = {}

    # ----- registration ----------------------------------------------------

    def tool(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict[str, Any],
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a callable as an MCP tool."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = ToolDef(
                func=func,
                input_schema=input_schema,
                description=description,
            )
            return func

        return decorator

    # ----- dispatch --------------------------------------------------------

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch a parsed JSON-RPC message.

        Returns the response dict to send back, or ``None`` for notifications
        (messages without an ``id`` field, like ``initialized``).
        """

        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications carry no ``id``; we never respond to them per the
        # JSON-RPC spec, regardless of method.
        is_notification = "id" not in message

        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": self.name, "version": self.version},
                "capabilities": {"tools": {}},
            }
            return protocol.make_response(msg_id, result)

        if method in ("initialized", "notifications/initialized"):
            return None

        if method == "tools/list":
            tools_payload = [
                {
                    "name": tool_name,
                    "description": tdef.description,
                    "inputSchema": tdef.input_schema,
                }
                for tool_name, tdef in self.tools.items()
            ]
            return protocol.make_response(msg_id, {"tools": tools_payload})

        if method == "tools/call":
            return self._handle_tool_call(msg_id, params)

        if is_notification:
            # Unknown notifications are silently ignored — JSON-RPC forbids
            # responding to them.
            return None

        return protocol.make_error(
            msg_id,
            protocol.METHOD_NOT_FOUND,
            f"Method not found: {method}",
        )

    def _handle_tool_call(
        self,
        msg_id: Any,
        params: Any,
    ) -> dict[str, Any]:
        """Validate ``tools/call`` params and invoke the tool."""

        if not isinstance(params, dict):
            return protocol.make_error(
                msg_id,
                protocol.INVALID_PARAMS,
                "params must be an object",
            )

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not isinstance(tool_name, str):
            return protocol.make_error(
                msg_id,
                protocol.INVALID_PARAMS,
                "params.name must be a string",
            )

        if not isinstance(arguments, dict):
            return protocol.make_error(
                msg_id,
                protocol.INVALID_PARAMS,
                "params.arguments must be an object",
            )

        tool_def = self.tools.get(tool_name)
        if tool_def is None:
            # Unknown tool name is a tool-level error (isError=true), not a
            # JSON-RPC error — that way the client can surface the message in
            # the model's context instead of bubbling a transport failure.
            return protocol.make_response(
                msg_id,
                {
                    "content": [
                        {"type": "text", "text": f"Unknown tool: {tool_name}"}
                    ],
                    "isError": True,
                },
            )

        validation_error = _validate_arguments(arguments, tool_def.input_schema)
        if validation_error is not None:
            return protocol.make_response(
                msg_id,
                {
                    "content": [{"type": "text", "text": validation_error}],
                    "isError": True,
                },
            )

        try:
            result = tool_def.func(**arguments)
        except TypeError as exc:
            # Catches mismatches the schema didn't catch (e.g. extra kwargs).
            return protocol.make_response(
                msg_id,
                {
                    "content": [{"type": "text", "text": f"Invalid arguments: {exc}"}],
                    "isError": True,
                },
            )
        except Exception as exc:  # noqa: BLE001 — surface tool errors to client
            return protocol.make_response(
                msg_id,
                {
                    "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
                    "isError": True,
                },
            )

        return protocol.make_response(
            msg_id,
            {"content": [{"type": "text", "text": str(result)}]},
        )


def tool(
    server: Server,
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Module-level alias for :meth:`Server.tool`.

    Lets you write ``from mcp_tool_server import tool`` and pass the server
    explicitly, mirroring the API of larger MCP libraries.
    """

    return server.tool(name=name, description=description, input_schema=input_schema)
