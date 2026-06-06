"""Compatibility wrapper for archived Letta pilot memory code.

Formal M0/M1/M2/M3 experiments now use the LD-Agent memory-only runtime in
``long_memory_test.memory``. This module remains only so historical pilot
scripts can still import the previous Letta helpers.
"""

from long_memory_test.legacy.letta_memory_legacy import *  # noqa: F401,F403
