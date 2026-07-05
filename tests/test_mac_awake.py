from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "scripts/_mac_awake.py"
SPEC = importlib.util.spec_from_file_location("_mac_awake", HELPER_PATH)
assert SPEC is not None
mac_awake = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mac_awake)


class MacAwakeTests(unittest.TestCase):
    def test_default_caffeinate_flags_allow_display_sleep(self) -> None:
        flags = mac_awake.parse_caffeinate_flags(None)

        self.assertEqual(flags, ["-i", "-m", "-s"])
        self.assertNotIn("-d", flags)

    def test_wrap_command_uses_caffeinate_on_macos(self) -> None:
        with (
            mock.patch.object(mac_awake.sys, "platform", "darwin"),
            mock.patch.object(mac_awake.shutil, "which", return_value="/usr/bin/caffeinate"),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            command, metadata = mac_awake.wrap_command_for_awake(
                ["python", "script.py"],
                disabled=False,
                flags=["-i", "-m", "-s"],
            )

        self.assertEqual(
            command,
            ["/usr/bin/caffeinate", "-i", "-m", "-s", "python", "script.py"],
        )
        self.assertTrue(metadata["enabled"])
        self.assertTrue(metadata["active"])
        self.assertTrue(metadata["allows_display_sleep"])

    def test_wrap_command_does_not_double_wrap_when_already_caffeinated(self) -> None:
        with (
            mock.patch.object(mac_awake.sys, "platform", "darwin"),
            mock.patch.object(mac_awake.shutil, "which", return_value="/usr/bin/caffeinate"),
            mock.patch.dict(os.environ, {mac_awake.CAFFEINATED_ENV: "1"}, clear=True),
        ):
            command, metadata = mac_awake.wrap_command_for_awake(
                ["python", "script.py"],
                disabled=False,
                flags=["-i", "-m", "-s"],
            )

        self.assertEqual(command, ["python", "script.py"])
        self.assertFalse(metadata["enabled"])
        self.assertTrue(metadata["active"])
        self.assertEqual(metadata["reason"], "already_caffeinated")

    def test_disabled_guard_is_recorded(self) -> None:
        command, metadata = mac_awake.wrap_command_for_awake(
            ["python", "script.py"],
            disabled=True,
            flags=["-i", "-m", "-s"],
        )

        self.assertEqual(command, ["python", "script.py"])
        self.assertFalse(metadata["active"])
        self.assertEqual(metadata["reason"], "disabled")


if __name__ == "__main__":
    unittest.main()
