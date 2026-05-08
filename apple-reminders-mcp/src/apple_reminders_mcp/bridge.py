"""Subprocess bridge to AppleScript / JXA via `osascript`.

User-supplied strings are passed through environment variables and read
inside the script with `getenv()` (JXA) or `system attribute` (AppleScript),
so they never get interpolated into the script source. This avoids quoting
bugs and AppleScript injection.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from typing import Any


class AppleScriptError(RuntimeError):
    """Raised when osascript exits non-zero."""


def _ensure_macos() -> None:
    if platform.system() != "Darwin":
        raise AppleScriptError(
            "Apple Reminders MCP only works on macOS (current platform: "
            f"{platform.system()})."
        )


def run_osa(script: str, *, language: str = "JavaScript",
            inputs: dict[str, str] | None = None,
            timeout: float = 90.0) -> str:
    """Run an osascript snippet and return its stdout (stripped)."""
    _ensure_macos()

    env_extra = {k: ("" if v is None else str(v)) for k, v in (inputs or {}).items()}

    try:
        proc = subprocess.run(
            ["osascript", "-l", language, "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, **env_extra},
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise AppleScriptError(f"osascript timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise AppleScriptError("`osascript` not found; macOS required.") from e

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        raise AppleScriptError(f"osascript failed (exit {proc.returncode}): {msg}")
    return proc.stdout.rstrip("\n")


def run_osa_json(script: str, *, inputs: dict[str, str] | None = None,
                 timeout: float = 90.0) -> Any:
    """Run a JXA snippet that prints a JSON document, parse it."""
    raw = run_osa(script, language="JavaScript", inputs=inputs, timeout=timeout)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise AppleScriptError(
            f"Could not parse JSON output: {e}\n--- raw ---\n{raw}"
        ) from e
