# apple-reminders-mcp

An [MCP](https://modelcontextprotocol.io) server for **Apple Reminders** on macOS, driven through the official JXA scripting bridge.

Sibling project to [`apple-notes-mcp`](../apple-notes-mcp). Same architecture: Python + `osascript` + JSON.

## Tools

| Tool | Description |
|---|---|
| `list_lists` | All Reminders lists. |
| `list_reminders` | Reminders, sorted incomplete-first then by due date. Filters by list / completion status. |
| `search_reminders` | Substring search over names + notes. |
| `get_reminder` | Full details of one reminder. |
| `create_reminder` | New reminder with name, body, list, due date, remind-me date, priority, flagged. |
| `update_reminder` | Patch any field (with `clear_*` flags to null fields). |
| `complete_reminder` | Mark complete or reopen. |
| `delete_reminder` | Delete (requires `confirm=True`). |
| `create_list` | Create a new list. |

### Date format

`due_date` and `remind_at` accept ISO 8601 strings, e.g. `2026-05-12T17:00:00`. Local timezone is assumed when no offset is given.

### Priority

`"none" | "high" | "medium" | "low"` (mapped to AppleScript's 0/1/5/9).

## Requirements

- macOS
- Python ≥ 3.10
- The Reminders app, signed into iCloud (or local-only — both work)

## Install

```bash
cd apple-reminders-mcp
uv sync
```

## First-run permission

macOS will prompt: *"Cursor (or Terminal) wants to control Reminders."* Click Allow. Manage later in **System Settings → Privacy & Security → Automation**.

## Register with Cursor

In `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "apple-reminders": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/Lucas_Relva/projects/mcp_servers/apple-reminders-mcp",
        "run",
        "apple-reminders-mcp"
      ]
    }
  }
}
```

## Local debugging

```bash
uv run mcp dev src/apple_reminders_mcp/server.py
```

## License

MIT
