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
| `move_reminder` | Move a reminder between lists (clones + deletes; new id returned). |
| `delete_reminder` | Delete (requires `confirm=True`). |
| `create_list` | Create a new list. |

### Performance tips

Apple's `osascript` ↔ Reminders.app bridge is intrinsically slow (every
property read/write is a round-trip and Reminders syncs with iCloud
synchronously). The server already does what it can:

- `list_reminders` / `search_reminders` push the completion filter into
  the app via `whose({completed: false})`, so they don't drag thousands
  of years-old completed items over Apple Events.
- Write tools (`create`, `update`, `complete`, `move`, `delete`) return
  a slim `{id, name, list, completed}` object instead of re-reading every
  field. Call `get_reminder` if you need the full record.
- All single-reminder tools (`get`, `update`, `complete`, `move`,
  `delete`) accept an optional `list_name` argument. **Pass it whenever
  you know the list** — it avoids enumerating every list when looking up
  the reminder, which is the dominant cost on accounts with many lists.

### About `move_reminder`

Reminders.app's AppleScript `move` verb is unreliable across iCloud lists,
so this tool clones the reminder into the target list and deletes the
original. As a consequence, **the reminder's id changes**. The response
includes both the new `id` and the original `previous_id` so callers can
remap any local references. If the reminder is already in the target
list, the tool returns `moved: false` with the unchanged id.

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
