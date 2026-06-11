#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.event_stream_generator import load_json  # noqa: E402
from long_memory_test.agents.memory_condition_builder import generate_memory_conditions  # noqa: E402
from long_memory_test.experiment_cache import (  # noqa: E402
    BEI_ANNOTATIONS_PATH,
    CACHE_MEMORY_CONDITIONS_PATH,
    CACHE_TIMELINE_EVENTS_PATH,
    DAILY_SCENE_CARDS_PATH,
    DAILY_USER_MESSAGE_PATH,
    EVENT_LINE_AUDIT_PATH,
    TAU_CONTRACT_PATH,
    M0_MEMORY_PATH,
    M1_ALIAS_MEMORY_PATH,
    M1_MEMORY_PATH,
    M2_MEMORY_PATH,
    M3_MEMORY_PATH,
    PROBE_QUESTION_PLAN_PATH,
    SCRIPT_TIMELINE_PATH,
    update_cache_manifest,
    write_json,
    write_memory_condition_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build fixed M0/M1/M2/M3 memory stores.")
    parser.add_argument("--timeline-cache", type=Path, default=CACHE_TIMELINE_EVENTS_PATH)
    parser.add_argument("--daily-messages", type=Path, default=DAILY_USER_MESSAGE_PATH)
    parser.add_argument("--probe-questions", type=Path, default=PROBE_QUESTION_PLAN_PATH)
    parser.add_argument("--bei-annotations", type=Path, default=BEI_ANNOTATIONS_PATH)
    parser.add_argument("--tau-contract", type=Path, default=TAU_CONTRACT_PATH)
    parser.add_argument("--output-cache", type=Path, default=CACHE_MEMORY_CONDITIONS_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    memory_conditions = generate_memory_conditions(
        timeline=load_json(args.timeline_cache),
        daily_messages=load_json(args.daily_messages),
        probe_question_plan=load_json(args.probe_questions),
        bei_annotations=load_json(args.bei_annotations),
        tau_contract=load_json(args.tau_contract) if args.tau_contract.exists() else None,
    )
    memory_conditions["source_paths"] = {
        "timeline_cache": _display_path(args.timeline_cache),
        "daily_messages": _display_path(args.daily_messages),
        "probe_questions": _display_path(args.probe_questions),
        "bei_annotations": _display_path(args.bei_annotations),
        "tau_contract": _display_path(args.tau_contract) if args.tau_contract.exists() else None,
    }
    write_json(args.output_cache, memory_conditions)
    write_memory_condition_files(memory_conditions)
    update_cache_manifest(
        {
            "canonical_timeline": SCRIPT_TIMELINE_PATH,
            "event_timeline_cache": args.timeline_cache,
            "daily_user_message": args.daily_messages,
            "daily_scene_cards": DAILY_SCENE_CARDS_PATH,
            "bei_annotations": args.bei_annotations,
            "probe_question_plan": args.probe_questions,
            "event_line_audit": EVENT_LINE_AUDIT_PATH,
            "tau_contract": TAU_CONTRACT_PATH,
            "memory_conditions_cache": args.output_cache,
            "m0_generic_agent_config": M0_MEMORY_PATH,
            "m1_conclusion_memory": M1_MEMORY_PATH,
            "mva_summary_memory_alias": M1_ALIAS_MEMORY_PATH,
            "m2_event_memory": M2_MEMORY_PATH,
            "m3_relational_anchor_memory": M3_MEMORY_PATH,
        },
        note="stage D memory condition stores refreshed",
    )
    print(
        "Wrote "
        f"{memory_conditions['summary']['message_payload_count']} message payloads "
        f"to {args.output_cache}"
    )
    print(f"Wrote split memory stores to {M0_MEMORY_PATH.parent}")
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
