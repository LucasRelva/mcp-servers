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


def _resolve_body(body: str | None, content: str | None,
                  text: str | None, *, required: bool) -> str:
    """Pick whichever of body/content/text the caller supplied.

    `body` is the canonical name. `content` and `text` are accepted as
    aliases because some agents reach for those instead, and a tool
    that hard-fails on a parameter rename is a footgun.
    """
    provided = {k: v for k, v in (("body", body), ("content", content),
                                  ("text", text)) if v is not None}
    if len(provided) > 1:
        raise ValueError(
            f"Provide exactly one of `body`, `content`, `text` "
            f"(got: {sorted(provided)})."
        )
    if not provided:
        if required:
            raise ValueError(
                "Missing required body. Pass it as `body` (preferred), "
                "`content`, or `text`."
            )
        return ""
    return next(iter(provided.values()))


@mcp.tool()
def create_note(title: str, body: str | None = None,
                content: str | None = None, text: str | None = None,
                folder: str | None = None,
                account: str | None = None) -> dict[str, Any]:
    """Create a new note.

    Args:
        title: Note title (also rendered as an <h1> at the top of the body).
        body: HTML or plain text. Plain text is auto-wrapped with <br>
            for newlines. **`body` is the canonical parameter name.**
            `content` and `text` are accepted as aliases.
        content: Alias for `body`.
        text: Alias for `body`.
        folder: Optional target folder name. Defaults to the user's default folder.
        account: Optional account name (e.g. "iCloud") to disambiguate folders.
    """
    body_text = _resolve_body(body, content, text, required=True)
    inputs = {
        "NOTES_TITLE": title,
        "NOTES_BODY": body_text,
        "NOTES_FOLDER": folder or "",
        "NOTES_ACCOUNT": account or "",
    }
    return run_osa_json(scripts.CREATE_NOTE, inputs=inputs)


@mcp.tool()
def append_to_note(note_id: str, body: str | None = None,
                   content: str | None = None,
                   text: str | None = None) -> dict[str, Any]:
    """Append HTML or plain text to the end of an existing note.

    Non-destructive: existing content is never touched. Prefer this over
    `update_note` whenever the user is *adding* content rather than
    rewriting existing content.

    `body` is the canonical parameter name. `content` and `text` are
    accepted as aliases.
    """
    body_text = _resolve_body(body, content, text, required=True)
    inputs = {"NOTES_ID": note_id, "NOTES_BODY": body_text}
    return run_osa_json(scripts.APPEND_TO_NOTE, inputs=inputs)


@mcp.tool()
def update_note(note_id: str, body: str | None = None,
                content: str | None = None, text: str | None = None,
                title: str | None = None) -> dict[str, Any]:
    """Replace the body of an existing note. **Destructive.**

    The new body REPLACES the existing body in full. There is no undo.

    **WARNING — hidden hyperlinks are unrecoverable through this bridge.**
    Apple's AppleScript Notes interface does not expose `<a href="...">`
    URLs in the `body` property. If a note contains any hidden link
    (URL behind visible label text — e.g. created via the Notes app's
    Link button), `get_note` cannot read those URLs back, and calling
    `update_note` WILL destroy them in the live note.
    For renaming, prefer `rename_note` (it does not touch body).
    For additions, prefer `append_to_note` (it does not rewrite body).

    Before calling, you MUST:
    1. `get_note(note_id)` and read **`body_html`** (not `body_text` —
       plaintext additionally drops emphasis, table/list structure).
    2. Read the resource `notes://preservation-rules`.
    3. Inventory every `<a href="...">`, `<table>`, `<ul>`, `<ol>`,
       `<b>`/`<i>`/`<u>`/`<s>` from the original `body_html`. Your new
       body MUST contain all of them, with the same `href` URLs,
       unless the user explicitly asked you to remove a specific item.
    4. If the note may contain hidden links, do not call `update_note`.

    `body` is the canonical parameter name. `content` and `text` are
    accepted as aliases. If you only want to rename, use `rename_note`
    instead.
    """
    body_text = _resolve_body(body, content, text, required=False)
    if not body_text and not title:
        raise ValueError(
            "Nothing to update. Pass `body` to rewrite content "
            "(or use `rename_note` for title-only changes)."
        )
    if not body_text:
        raise ValueError(
            "update_note requires a body. For title-only renames, use "
            "`rename_note(note_id, title)` -- it does not touch body and "
            "is safe even on notes with hidden hyperlinks."
        )
    inputs = {
        "NOTES_ID": note_id,
        "NOTES_BODY": body_text,
        "NOTES_TITLE": title or "",
    }
    return run_osa_json(scripts.UPDATE_NOTE, inputs=inputs)


@mcp.tool()
def rename_note(note_id: str, title: str) -> dict[str, Any]:
    """Rename a note **without touching its body**.

    Sets only the note's `name` property. The body is not read, modified,
    or rewritten -- which makes this the **only** rename method that is
    safe on notes containing hidden hyperlinks (URLs behind visible
    label text). Apple's AppleScript bridge strips `<a href>` on every
    body write, so any tool that rewrites body would destroy those
    links in the live note.

    Caveats to know about:
    - In modern Notes (macOS Sonoma+ / iOS 17+), the title shown AT THE
      TOP OF THE OPEN NOTE BODY is derived from the first line of body.
      Since we don't touch body, that on-screen title does not change.
      The Notes sidebar / notes-list title does update because that
      comes from `name`, which we set.
    - If you want the body's leading title text to also change, you
      have to do that inside the Notes app manually (which preserves
      hyperlinks because the UI doesn't go through AppleScript).
    """
    return run_osa_json(scripts.RENAME_NOTE, inputs={
        "NOTES_ID": note_id,
        "NOTES_NEW_NAME": title,
    })


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
