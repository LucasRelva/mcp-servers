"""FastMCP server exposing Apple Reminders operations."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import scripts
from .bridge import AppleScriptError, run_osa_json

mcp = FastMCP("apple-reminders")

Priority = Literal["none", "high", "medium", "low"]


@mcp.tool()
def list_lists() -> list[dict[str, Any]]:
    """List every Reminders list."""
    return run_osa_json(scripts.LIST_LISTS) or []


@mcp.tool()
def list_reminders(
    list_name: str | None = None,
    include_completed: bool = False,
    only_completed: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List reminders, sorted incomplete-first then by due date.

    Args:
        list_name: Optional list to filter by (e.g. "Groceries").
        include_completed: If True, include completed reminders alongside open ones.
        only_completed: If True, return only completed reminders (overrides include_completed).
        limit: Max results to return.
    """
    inputs = {
        "REM_LIST": list_name or "",
        "REM_INCLUDE_COMPLETED": "1" if include_completed else "",
        "REM_ONLY_COMPLETED": "1" if only_completed else "",
        "REM_LIMIT": str(limit),
    }
    return run_osa_json(scripts.LIST_REMINDERS, inputs=inputs) or []


@mcp.tool()
def search_reminders(query: str, include_completed: bool = False,
                     limit: int = 50) -> list[dict[str, Any]]:
    """Substring search across reminder names and notes (case-insensitive)."""
    inputs = {
        "REM_QUERY": query,
        "REM_INCLUDE_COMPLETED": "1" if include_completed else "",
        "REM_LIMIT": str(limit),
    }
    return run_osa_json(scripts.SEARCH_REMINDERS, inputs=inputs) or []


@mcp.tool()
def get_reminder(reminder_id: str) -> dict[str, Any]:
    """Fetch a reminder's full details by id."""
    return run_osa_json(scripts.GET_REMINDER, inputs={"REM_ID": reminder_id})


@mcp.tool()
def create_reminder(
    name: str,
    body: str | None = None,
    list_name: str | None = None,
    due_date: str | None = None,
    remind_at: str | None = None,
    priority: Priority = "none",
    flagged: bool = False,
) -> dict[str, Any]:
    """Create a new reminder.

    Args:
        name: Reminder title.
        body: Optional notes/body.
        list_name: Target list. Defaults to the user's default list.
        due_date: Optional ISO 8601 date/time (e.g. "2026-05-12T17:00:00").
        remind_at: Optional ISO 8601 date/time when macOS should fire the alert.
        priority: "none" | "high" | "medium" | "low".
        flagged: Whether to flag the reminder.
    """
    inputs = {
        "REM_NAME": name,
        "REM_BODY": body or "",
        "REM_LIST": list_name or "",
        "REM_DUE_DATE": due_date or "",
        "REM_REMIND_AT": remind_at or "",
        "REM_PRIORITY": priority,
        "REM_FLAGGED": "1" if flagged else "",
    }
    return run_osa_json(scripts.CREATE_REMINDER, inputs=inputs)


@mcp.tool()
def update_reminder(
    reminder_id: str,
    name: str | None = None,
    body: str | None = None,
    due_date: str | None = None,
    remind_at: str | None = None,
    priority: Priority | None = None,
    flagged: bool | None = None,
    clear_body: bool = False,
    clear_due_date: bool = False,
    clear_remind_at: bool = False,
) -> dict[str, Any]:
    """Update a reminder's fields. Only fields you pass are touched.

    Use the `clear_*` flags to explicitly null a field (e.g. remove a due date).
    """
    inputs = {
        "REM_ID": reminder_id,
        "REM_NAME": name or "",
        "REM_BODY": body or "",
        "REM_DUE_DATE": due_date or "",
        "REM_REMIND_AT": remind_at or "",
        "REM_PRIORITY": priority or "",
        "REM_FLAGGED": "" if flagged is None else ("1" if flagged else "0"),
        "REM_CLEAR_BODY": "1" if clear_body else "",
        "REM_CLEAR_DUE_DATE": "1" if clear_due_date else "",
        "REM_CLEAR_REMIND_AT": "1" if clear_remind_at else "",
    }
    return run_osa_json(scripts.UPDATE_REMINDER, inputs=inputs)


@mcp.tool()
def complete_reminder(reminder_id: str, completed: bool = True) -> dict[str, Any]:
    """Mark a reminder complete (or set `completed=False` to reopen it)."""
    inputs = {"REM_ID": reminder_id, "REM_COMPLETED": "1" if completed else "0"}
    return run_osa_json(scripts.SET_COMPLETED, inputs=inputs)


@mcp.tool()
def delete_reminder(reminder_id: str, confirm: bool = False) -> dict[str, Any]:
    """Permanently delete a reminder. Pass `confirm=True` to actually delete."""
    if not confirm:
        raise ValueError(
            "Refusing to delete: pass confirm=True to acknowledge this is irreversible."
        )
    return run_osa_json(scripts.DELETE_REMINDER, inputs={"REM_ID": reminder_id})


@mcp.tool()
def create_list(name: str) -> dict[str, Any]:
    """Create a new Reminders list."""
    return run_osa_json(scripts.CREATE_LIST, inputs={"REM_LIST_NAME": name})


def main() -> None:
    """Entry point for the `apple-reminders-mcp` console script."""
    try:
        mcp.run()
    except AppleScriptError as e:
        import sys
        print(f"apple-reminders-mcp: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
