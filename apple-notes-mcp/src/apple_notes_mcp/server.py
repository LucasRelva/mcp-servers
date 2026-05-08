"""FastMCP server exposing Apple Notes operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import content as _content
from . import scripts
from .bridge import AppleScriptError, run_osa_json

mcp = FastMCP("apple-notes")


# --------------------------------------------------------------------------- #
# Resources — formatting reference the agent should read before authoring     #
# --------------------------------------------------------------------------- #

@mcp.resource(
    "notes://styleguide",
    name="Apple Notes Styleguide",
    description="What Apple Notes supports: headings, lists, tables, "
                "collapsible sections, checklist limitations, etc.",
    mime_type="text/markdown",
)
def styleguide() -> str:
    return _content.STYLEGUIDE


@mcp.resource(
    "notes://html-reference",
    name="Apple Notes HTML Reference",
    description="Terse, copy-pasteable HTML snippets for every supported "
                "Apple Notes formatting element.",
    mime_type="text/markdown",
)
def html_reference() -> str:
    return _content.HTML_REFERENCE


@mcp.resource(
    "notes://preservation-rules",
    name="Apple Notes Preservation Rules",
    description="Critical rules to follow before any append_to_note or "
                "update_note call so you don't silently destroy links, "
                "tables, emphasis, or list structure.",
    mime_type="text/markdown",
)
def preservation_rules() -> str:
    return _content.PRESERVATION_RULES


@mcp.resource(
    "notes://templates/{kind}",
    name="Apple Notes Template",
    description="Ready-to-fill HTML templates. `kind` is one of: "
                "meeting, checklist, longform, table.",
    mime_type="text/markdown",
)
def template(kind: str) -> str:
    if kind not in _content.TEMPLATES:
        raise ValueError(
            f"Unknown template '{kind}'. Available: "
            f"{', '.join(sorted(_content.TEMPLATES))}."
        )
    return _content.TEMPLATES[kind]


# --------------------------------------------------------------------------- #
# Prompts — guide the agent when authoring or expanding a note                #
# --------------------------------------------------------------------------- #

@mcp.prompt(
    name="compose_note",
    description="Compose a new Apple Note. Reads the styleguide, HTML "
                "reference and templates first, then produces a well-structured "
                "body for `create_note`.",
)
def compose_note_prompt(topic: str) -> str:
    return _content.COMPOSE_NOTE_PROMPT.format(topic=topic)


@mcp.prompt(
    name="expand_note",
    description="Append to or update an existing Apple Note while preserving "
                "its existing structure and conventions.",
)
def expand_note_prompt(note_id: str, content: str) -> str:  # noqa: A002
    return _content.EXPAND_NOTE_PROMPT.format(note_id=note_id, content=content)


@mcp.tool()
def list_folders() -> list[dict[str, Any]]:
    """List every Notes folder across all accounts (iCloud, On My Mac, etc.)."""
    return run_osa_json(scripts.LIST_FOLDERS) or []


@mcp.tool()
def list_notes(folder: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List notes (metadata only), newest first.

    Args:
        folder: Optional folder name to filter by (case-sensitive, e.g. "Notes").
        limit: Maximum number of notes to return (default 50).
    """
    inputs = {"NOTES_FOLDER": folder or "", "NOTES_LIMIT": str(limit)}
    return run_osa_json(scripts.LIST_NOTES, inputs=inputs) or []


@mcp.tool()
def search_notes(query: str, limit: int = 25) -> list[dict[str, Any]]:
    """Substring search across note titles and bodies (case-insensitive).

    Returns matches with a 200-character plaintext snippet. Locked notes are
    skipped.
    """
    inputs = {"NOTES_QUERY": query, "NOTES_LIMIT": str(limit)}
    return run_osa_json(scripts.SEARCH_NOTES, inputs=inputs) or []


@mcp.tool()
def get_note(note_id: str) -> dict[str, Any]:
    """Fetch a note's full content by id (use `list_notes` / `search_notes` to
    get ids). Returns both `body_html` (Notes' native format) and `body_text`.

    IMPORTANT: When you intend to **modify** the note (`append_to_note` or
    `update_note`), always work from `body_html`. `body_text` is a lossy
    projection — it hides URLs inside `<a href="...">`, drops table/list
    structure, and discards inline emphasis. Rewriting from `body_text`
    will silently delete this content. See `notes://preservation-rules`.
    """
    return run_osa_json(scripts.GET_NOTE, inputs={"NOTES_ID": note_id})


@mcp.tool()
def create_note(title: str, body: str, folder: str | None = None,
                account: str | None = None) -> dict[str, Any]:
    """Create a new note.

    Args:
        title: Note title (also rendered as an <h1> at the top of the body).
        body: HTML or plain text. Plain text is auto-wrapped with <br> for newlines.
        folder: Optional target folder name. Defaults to the user's default folder.
        account: Optional account name (e.g. "iCloud") to disambiguate folders.
    """
    inputs = {
        "NOTES_TITLE": title,
        "NOTES_BODY": body,
        "NOTES_FOLDER": folder or "",
        "NOTES_ACCOUNT": account or "",
    }
    return run_osa_json(scripts.CREATE_NOTE, inputs=inputs)


@mcp.tool()
def append_to_note(note_id: str, body: str) -> dict[str, Any]:
    """Append HTML or plain text to the end of an existing note.

    Non-destructive: existing content is never touched. Prefer this over
    `update_note` whenever the user is *adding* content rather than
    rewriting existing content.
    """
    inputs = {"NOTES_ID": note_id, "NOTES_BODY": body}
    return run_osa_json(scripts.APPEND_TO_NOTE, inputs=inputs)


@mcp.tool()
def update_note(note_id: str, body: str, title: str | None = None) -> dict[str, Any]:
    """Replace the body of an existing note. **Destructive.**

    The new `body` REPLACES the existing body in full. There is no undo.

    Before calling, you MUST:
    1. `get_note(note_id)` and read the **`body_html`** (not `body_text` —
       it is lossy and hides URLs inside `<a href="...">` and other
       structure).
    2. Read the resource `notes://preservation-rules`.
    3. Inventory every `<a href="...">`, `<table>`, `<ul>`, `<ol>`,
       `<b>`/`<i>`/`<u>`/`<s>` from the original `body_html`. Your new
       `body` MUST contain all of them, with the same `href` URLs,
       unless the user explicitly asked you to remove a specific item.
    4. If you can achieve the user's goal with `append_to_note` instead,
       do that — it cannot lose data.
    """
    inputs = {
        "NOTES_ID": note_id,
        "NOTES_BODY": body,
        "NOTES_TITLE": title or "",
    }
    return run_osa_json(scripts.UPDATE_NOTE, inputs=inputs)


@mcp.tool()
def delete_note(note_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a note permanently. You must pass `confirm=True` to actually delete."""
    if not confirm:
        raise ValueError(
            "Refusing to delete: pass confirm=True to acknowledge this is irreversible."
        )
    return run_osa_json(scripts.DELETE_NOTE, inputs={"NOTES_ID": note_id})


def main() -> None:
    """Entry point for the `apple-notes-mcp` console script."""
    try:
        mcp.run()
    except AppleScriptError as e:
        import sys
        print(f"apple-notes-mcp: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
