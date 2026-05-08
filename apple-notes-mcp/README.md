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
| `append_to_note` | Append HTML / text to an existing note (non-destructive). |
| `update_note` | Replace a note's body. **Destructive** — see the hidden-links caveat below. |
| `rename_note` | Change the title without touching body. **Safe on notes with hidden links.** |
| `delete_note` | Delete a note. Requires `confirm=True`. |

`create_note`, `append_to_note`, and `update_note` accept the body under any of `body` (canonical), `content`, or `text` — whichever the agent reaches for first. Passing more than one is rejected with a clear error.

### The hidden-hyperlink limitation (important)

Apple's AppleScript bridge **does not expose `<a href="...">` URLs**. If the user typed a hyperlink in the Notes app (URL hidden behind label text like "click here"), `get_note` won't return the URL. The live note still has the link clickable in the Notes UI, but rewriting body via AppleScript will destroy it. There is no workaround at the bridge level — Apple just doesn't expose the field.

For notes that may contain hidden hyperlinks:

- **Use `rename_note`** for title changes — it does not read or write body.
- **Use `append_to_note`** to add content — it does not rewrite existing content.
- **Do not use `update_note`** — it will silently strip every hidden link.

The full decision flow is in the `notes://preservation-rules` resource.

## Resources

The server exposes formatting documentation that the agent can pull on demand
to produce well-structured notes:

| URI | Description |
|---|---|
| `notes://styleguide` | What Apple Notes supports: headings, lists, tables, collapsible sections, checklist limitations. |
| `notes://html-reference` | Terse, copy-pasteable HTML snippets for every supported element. |
| `notes://preservation-rules` | **Critical** rules for `append_to_note` / `update_note`: always work from `body_html`, never `body_text`; preserve every link/table/list/emphasis tag. |
| `notes://templates/meeting` | Meeting-note skeleton (metadata table + agenda + decisions + action items). |
| `notes://templates/checklist` | TODO / checklist note. |
| `notes://templates/longform` | Long-form reference doc with collapsible sections. |
| `notes://templates/table` | Tabular / comparison note. |

## Prompts

| Name | Use it for |
|---|---|
| `compose_note(topic)` | Pre-flight checklist for creating a new note: tells the agent to read the styleguide + a template before calling `create_note`. |
| `expand_note(note_id, content)` | Pre-flight checklist for `append_to_note` / `update_note`: tells the agent to fetch the existing note first and match its structure. |

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
