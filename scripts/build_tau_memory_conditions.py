#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.event_stream_generator import load_json, write_json  # noqa: E402
from long_memory_test.agents.memory_condition_builder import (  # noqa: E402
    generate_memory_conditions_from_tau_contract,
)
from long_memory_test.experiment_cache import write_memory_condition_files  # noqa: E402


DEFAULT_TAU_CONTRACT = (
    REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/tau_contract.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "long_memory_experiment/cache/tau_memory_conditions_combined.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Adapt latest tau=(z,T,L,I,P) contract into M0/M1/M2/M3 memory "
            "condition payloads. This script does not create new tasks."
        )
    )
    parser.add_argument("--tau-contract", type=Path, default=DEFAULT_TAU_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--split",
        action="store_true",
        help="Also refresh long_memory_experiment/data/memory_conditions/*.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    memory_conditions = generate_memory_conditions_from_tau_contract(
        tau_contract=load_json(args.tau_contract)
    )
    memory_conditions["source_paths"] = {
        "tau_contract": _display_path(args.tau_contract),
    }
    write_json(args.output, memory_conditions)
    if args.split:
        write_memory_condition_files(memory_conditions)
    print(
        "Wrote "
        f"{memory_conditions['summary']['message_payload_count']} tau-route message payloads "
        f"to {args.output}"
    )
    if args.split:
        print("Refreshed split memory condition files.")
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
