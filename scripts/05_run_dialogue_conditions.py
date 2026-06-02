#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    runpy.run_path(str(REPO_ROOT / "scripts/run_dialogue_conditions.py"), run_name="__main__")
