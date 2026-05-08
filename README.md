# mcp-servers

Personal collection of [Model Context Protocol](https://modelcontextprotocol.io) servers I run locally with Cursor / Claude Desktop.

## Servers

| Server | Description |
|---|---|
| [`apple-notes-mcp`](./apple-notes-mcp) | Read & write Apple Notes via JXA on macOS. |
| [`apple-reminders-mcp`](./apple-reminders-mcp) | Read & write Apple Reminders via JXA on macOS. |

Each server has its own README with install + Cursor registration instructions.

## Stack

- Python 3.10+
- [`mcp`](https://github.com/modelcontextprotocol/python-sdk) (FastMCP)
- [`uv`](https://github.com/astral-sh/uv) for env / dependency management
- `osascript` (JXA) as the bridge to macOS scriptable apps — no private APIs, no SQLite hacks

## Local layout

```
mcp-servers/
├── apple-notes-mcp/
│   ├── pyproject.toml
│   ├── README.md
│   └── src/apple_notes_mcp/
│       ├── bridge.py     # subprocess wrapper around osascript
│       ├── scripts.py    # JXA snippets, one per tool
│       └── server.py     # FastMCP tool definitions
└── apple-reminders-mcp/
    └── ... (same structure)
```

## License

MIT
