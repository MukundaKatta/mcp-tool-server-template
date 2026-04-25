# mcp-tool-server-template

A small, dependency-free Python template for building [Model Context Protocol](https://modelcontextprotocol.io) (MCP) servers.

- Pure stdlib at runtime — no `mcp` package, no third-party requirements.
- Hand-rolled JSON-RPC 2.0 over stdio so you can read every line of the wire.
- Three example tools (`echo`, `current_time`, `add`) wired through a tiny `Server` class.
- A clean split between the protocol core (`server.py`), the transport (`transport.py`), and your tools (`tools.py`).

If you've ever looked at an MCP server and wondered "what's the actual minimum?", this repo is the answer.

## What MCP is

MCP is the open protocol Anthropic uses for Claude Desktop and Claude Code to talk to local tools. A server exposes capabilities (tools, resources, prompts) over JSON-RPC; the client (Claude) discovers them via `tools/list` and invokes them via `tools/call`. This template implements the tools half — the most useful 80% — with no dependencies.

## Install

```bash
git clone https://github.com/MukundaKatta/mcp-tool-server-template.git
cd mcp-tool-server-template
pip install -e .
```

For the dev tools (pytest):

```bash
pip install -e ".[dev]"
```

## Run

```bash
mts run        # start the server on stdio (intended for an MCP client)
mts list-tools # print registered tools to stdout — sanity check
mts --version
```

`mts run` is not meant to be used interactively; it reads JSON-RPC messages line by line from stdin and writes responses to stdout. Wire it into Claude Desktop or Claude Code (see below) and the client will drive it for you.

## Add your tool in 60 seconds

Open `src/mcp_tool_server/cli.py` inside `build_server()` and add a tool:

```diff
 def build_server() -> Server:
     server = Server(name="mcp-tool-server-template", version=__version__)

+    @server.tool(
+        name="reverse",
+        description="Reverse the given text.",
+        input_schema={
+            "type": "object",
+            "properties": {"text": {"type": "string"}},
+            "required": ["text"],
+        },
+    )
+    def _reverse(text: str) -> str:
+        return text[::-1]
+
     @server.tool(
         name="echo",
```

That's it. Reinstall (`pip install -e .`), restart your MCP client, and the tool shows up in `tools/list` automatically.

The contract for a tool function:

- Arguments are passed by keyword from the JSON `arguments` object — names must match.
- Return value is converted to a string and shipped back as a `text` content block.
- Raise an exception for tool-level errors; the server reports them with `isError: true` so the model sees the message.

## Wire it into Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tool-template": {
      "command": "mts",
      "args": ["run"]
    }
  }
}
```

If `mts` isn't on the PATH Claude Desktop sees, use the absolute path (`which mts`) instead.

## Wire it into Claude Code

Add the server with the CLI:

```bash
claude mcp add tool-template -- mts run
```

Or edit `~/.claude.json` (or your project-scoped `.mcp.json`) directly:

```json
{
  "mcpServers": {
    "tool-template": {
      "command": "mts",
      "args": ["run"]
    }
  }
}
```

## Layout

```
src/mcp_tool_server/
  __init__.py     # public re-exports
  __main__.py     # python -m mcp_tool_server
  cli.py          # mts entry point + tool registration
  protocol.py     # JSON-RPC encode/parse + error codes
  server.py       # Server class, dispatch, schema validation
  tools.py        # example tool implementations
  transport.py    # stdio read/dispatch/write loop
tests/            # pytest suite
```

## Design notes

- **Validation is intentionally minimal.** Required fields and JSON Schema `type` strings are checked; everything else is a tool's responsibility. If you need full JSON Schema, plug in `jsonschema` — but most tools don't.
- **Tool errors are not transport errors.** A failed tool call returns a normal JSON-RPC `result` with `isError: true` so the model can read the message and recover. JSON-RPC errors are reserved for malformed requests.
- **Notifications are silently ignored.** JSON-RPC forbids responding to messages without an `id`, including unknown ones; the server respects that.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

CI runs the suite on Python 3.10, 3.11, and 3.12.

## License

MIT — see [LICENSE](./LICENSE).
