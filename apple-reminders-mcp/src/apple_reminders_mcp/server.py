"""FastMCP server exposing Apple Reminders operations."""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from . import scripts
from .bridge import AppleScriptError, run_osa_json

mcp = FastMCP("apple-reminders")

Priority = Literal["none", "high", "medium", "low"]

MAX_LIMIT = 1000


def _clamp_limit(limit: int) -> int:
    """Clamp a user-supplied `limit` to a sane positive range.

    Callers can pass any int; we coerce to at least 1 and at most `MAX_LIMIT`
    so the osascript layer never receives a zero/negative value (which would
    silently return an empty list) or an unbounded value (which would drag
    the entire Reminders database over Apple Events).
    """
    if limit < 1:
        return 1
    if limit > MAX_LIMIT:
        return MAX_LIMIT
    return limit


def _flag_env(value: bool) -> str:
    """Map a Python bool to the `"1"`/`""` toggle the osascript layer expects."""
    return "1" if value else ""


def _tristate_flag_env(value: bool | None) -> str:
    """Map an optional Python bool to the `"1"`/`"0"`/`""` tri-state the osascript layer expects.

    - `None` → `""`  (leave the field untouched on the reminder)
    - `True` → `"1"` (set the flag)
    - `False` → `"0"` (clear the flag)

    Pulled out of `update_reminder` to flatten the nested ternary that
    SonarQube python:S3358 flagged.
    """
    if value is None:
        return ""
    return "1" if value else "0"


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
        limit: Max results to return (1..MAX_LIMIT; out-of-range values are clamped).
    """
    inputs = {
        "REM_LIST": list_name or "",
        "REM_INCLUDE_COMPLETED": _flag_env(include_completed),
        "REM_ONLY_COMPLETED": _flag_env(only_completed),
        "REM_LIMIT": str(_clamp_limit(limit)),
    }
    return run_osa_json(scripts.LIST_REMINDERS, inputs=inputs) or []


@mcp.tool()
def search_reminders(
    query: str,
    include_completed: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Substring search across reminder names and notes (case-insensitive).

    Args:
        query: Substring to search for.
        include_completed: If True, also match completed reminders.
        limit: Max results to return (1..MAX_LIMIT; out-of-range values are clamped).
    """
    inputs = {
        "REM_QUERY": query,
        "REM_INCLUDE_COMPLETED": _flag_env(include_completed),
        "REM_LIMIT": str(_clamp_limit(limit)),
    }
    return run_osa_json(scripts.SEARCH_REMINDERS, inputs=inputs) or []


@mcp.tool()
def get_reminder(reminder_id: str, list_name: str | None = None) -> dict[str, Any]:
    """Fetch a reminder's full details by id.

    Args:
        reminder_id: The reminder id.
        list_name: Optional list name. When provided, lookup is much faster
            because we skip enumerating every list. Pass it whenever you
            already know which list the reminder lives in (e.g. from a
            previous `list_reminders` / `search_reminders` result).
    """
    return run_osa_json(scripts.GET_REMINDER, inputs={
        "REM_ID": reminder_id,
        "REM_LIST_HINT": list_name or "",
    })


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
    list_name: str | None = None,
) -> dict[str, Any]:
    """Update a reminder's fields. Only fields you pass are touched.

    Use the `clear_*` flags to explicitly null a field (e.g. remove a due date).
    Pass `list_name` if you know which list the reminder is in -- it makes
    the lookup much faster.

    Returns a slim object: {id, name, list, completed}. Call `get_reminder`
    if you need the full record.
    """
    inputs = {
        "REM_ID": reminder_id,
        "REM_LIST_HINT": list_name or "",
        "REM_NAME": name or "",
        "REM_BODY": body or "",
        "REM_DUE_DATE": due_date or "",
        "REM_REMIND_AT": remind_at or "",
        "REM_PRIORITY": priority or "",
        "REM_FLAGGED": _tristate_flag_env(flagged),
        "REM_CLEAR_BODY": _flag_env(clear_body),
        "REM_CLEAR_DUE_DATE": _flag_env(clear_due_date),
        "REM_CLEAR_REMIND_AT": _flag_env(clear_remind_at),
    }
    return run_osa_json(scripts.UPDATE_REMINDER, inputs=inputs)


@mcp.tool()
def complete_reminder(
    reminder_id: str,
    completed: bool = True,
    list_name: str | None = None,
) -> dict[str, Any]:
    """Mark a reminder complete (or set `completed=False` to reopen it).

    Pass `list_name` for a much faster lookup when you know which list the
    reminder lives in.
    """
    inputs = {
        "REM_ID": reminder_id,
        "REM_LIST_HINT": list_name or "",
        "REM_COMPLETED": "1" if completed else "0",
    }
    return run_osa_json(scripts.SET_COMPLETED, inputs=inputs)


@mcp.tool()
def delete_reminder(
    reminder_id: str,
    confirm: bool = False,
    list_name: str | None = None,
) -> dict[str, Any]:
    """Permanently delete a reminder. Pass `confirm=True` to actually delete.

    Pass `list_name` to skip list enumeration for a faster lookup.
    """
    if not confirm:
        raise ValueError(
            "Refusing to delete: pass confirm=True to acknowledge this is irreversible."
        )
    return run_osa_json(scripts.DELETE_REMINDER, inputs={
        "REM_ID": reminder_id,
        "REM_LIST_HINT": list_name or "",
    })


@mcp.tool()
def move_reminder(
    reminder_id: str,
    target_list: str,
    list_name: str | None = None,
) -> dict[str, Any]:
    """Move a reminder to a different list.

    Apple's `move` AppleScript verb is unreliable for Reminders, so this
    is implemented as: clone the reminder into the target list, copy over
    name/body/due_date/remind_at/priority/flagged/completed, then delete
    the original. The reminder's id will change as a result.

    Args:
        reminder_id: The id of the reminder to move.
        target_list: The name of the list to move the reminder into.
        list_name: Optional source list hint (faster lookup).

    Returns:
        A slim object with the **new** id, the `previous_id`, the target
        list, and a `moved: true` flag. If the reminder was already in
        the target list, `moved: false` and the id is unchanged.
    """
    return run_osa_json(scripts.MOVE_REMINDER, inputs={
        "REM_ID": reminder_id,
        "REM_LIST_HINT": list_name or "",
        "REM_TARGET_LIST": target_list,
    })


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
