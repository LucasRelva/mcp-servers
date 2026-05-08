# apple-notes-mcp

An [MCP](https://modelcontextprotocol.io) server that lets an LLM agent read and write **Apple Notes** on macOS.

It drives the Notes app via JXA (JavaScript for Automation, Apple's official scripting bridge) — no private APIs, no SQLite hacks. Works with iCloud, On My Mac, and any other account signed into Notes.

## Tools

| Tool | Description |
|---|---|
| `list_folders` | All folders across every account. |
| `list_notes` | Note metadata, newest first. Optional folder filter. |
| `search_notes` | Substring search over titles + bodies. |
| `get_note` | Full content of one note (HTML + plaintext). |
| `create_note` | New note with title, body, optional folder/account. |
| `append_to_note` | Append HTML / text to an existing note. |
| `update_note` | Replace a note's body (optionally rename). |
| `delete_note` | Delete a note. Requires `confirm=True`. |

## Requirements

- macOS (any reasonably modern version)
- Python ≥ 3.10
- The Notes app, signed into whatever accounts you want to use

## Install

With [`uv`](https://github.com/astral-sh/uv) (recommended):

```bash
cd apple-notes-mcp
uv sync
```

Or with pip:

```bash
cd apple-notes-mcp
pip install -e .
```

## First-run permission

The first time the server runs, macOS will pop up:

> "Cursor" (or your terminal) wants to control "Notes".

Click **Allow**. You can later manage this in **System Settings → Privacy & Security → Automation**. Without it, every call returns a permissions error — that's the OS sandbox doing its job.

## Register with Cursor

Add an entry to `~/.cursor/mcp.json` (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "apple-notes": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/Lucas_Relva/projects/mcp_servers/apple-notes-mcp",
        "run",
        "apple-notes-mcp"
      ]
    }
  }
}
```

(If you installed with pip into a venv, point `command` at the venv's `apple-notes-mcp` binary directly and drop `args`.)

Restart Cursor; you should see `apple-notes` in the MCP list with 8 tools.

## Use with Claude Desktop

Same idea, in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apple-notes": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/apple-notes-mcp", "run", "apple-notes-mcp"]
    }
  }
}
```

## Try it from the command line

You can poke the server with the MCP CLI inspector:

```bash
uv run mcp dev src/apple_notes_mcp/server.py
```

That opens a browser tool that lists the server's tools and lets you call them by hand.

## Design notes

- **JXA, not raw AppleScript.** JXA has native `JSON.stringify`, which makes round-tripping note bodies (HTML, special characters, newlines) far more reliable.
- **No string interpolation.** All user input flows through environment variables and is read inside the script with `getenv()`. The script source is static — no injection surface.
- **Metadata vs. content.** `list_notes` returns metadata only; bodies come from `get_note`. Reading every note's body up front is slow on large libraries.
- **Locked notes** can't be read while locked; `search_notes` skips them silently.
- **`delete_note` is gated** behind `confirm=True` to avoid accidental data loss.

## License

MIT
