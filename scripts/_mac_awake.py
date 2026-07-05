from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


CAFFEINATED_ENV = "LONG_MEMORY_TEST_CAFFEINATED"
CAFFEINATE_DISABLED_ENV = "LONG_MEMORY_TEST_NO_CAFFEINATE"
DEFAULT_CAFFEINATE_FLAGS = "-i -m -s"


def parse_caffeinate_flags(value: str | None) -> list[str]:
    return shlex.split(value or DEFAULT_CAFFEINATE_FLAGS)


def wrap_command_for_awake(
    command: list[str],
    *,
    disabled: bool,
    flags: list[str],
) -> tuple[list[str], dict[str, Any]]:
    metadata = awake_guard_metadata(disabled=disabled, flags=flags)
    if not metadata["enabled"]:
        return list(command), metadata
    return [str(metadata["binary"]), *flags, *command], metadata


def awake_guard_metadata(*, disabled: bool, flags: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "platform": sys.platform,
        "active": False,
        "enabled": False,
        "tool": "caffeinate",
        "binary": None,
        "flags": list(flags),
        "allows_display_sleep": "-d" not in flags,
        "mode": (
            "prevent idle system sleep and disk sleep while allowing display sleep"
        ),
        "reason": None,
    }
    if disabled or os.environ.get(CAFFEINATE_DISABLED_ENV) == "1":
        metadata["reason"] = "disabled"
        return metadata
    if os.environ.get(CAFFEINATED_ENV) == "1":
        metadata["active"] = True
        metadata["reason"] = "already_caffeinated"
        return metadata
    if sys.platform != "darwin":
        metadata["reason"] = "not_macos"
        return metadata
    binary = shutil.which("caffeinate")
    if not binary:
        metadata["reason"] = "caffeinate_not_found"
        return metadata
    metadata["enabled"] = True
    metadata["active"] = True
    metadata["binary"] = binary
    metadata["reason"] = "enabled"
    return metadata


def maybe_reexec_under_awake_guard(
    argv: list[str],
    *,
    disabled: bool,
    flags: list[str],
) -> int | None:
    command = [sys.executable, *argv]
    wrapped_command, metadata = wrap_command_for_awake(
        command,
        disabled=disabled,
        flags=flags,
    )
    if not metadata["enabled"]:
        return None
    env = dict(os.environ)
    mark_caffeinated(env)
    print(
        "==> macOS awake guard: "
        + shlex.join(wrapped_command[: 1 + len(flags)])
        + " "
        + shlex.join(command),
        flush=True,
    )
    return subprocess.run(wrapped_command, cwd=Path.cwd(), env=env).returncode


def mark_caffeinated(env: dict[str, str]) -> None:
    env[CAFFEINATED_ENV] = "1"


def mark_caffeinate_disabled(env: dict[str, str]) -> None:
    env[CAFFEINATE_DISABLED_ENV] = "1"
