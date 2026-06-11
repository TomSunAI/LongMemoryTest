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
from long_memory_test.agents.probe_question_generator import (  # noqa: E402
    ProbeQuestionConfig,
    generate_a_script_plan,
    generate_probe_question_plan,
)
from long_memory_test.experiment_cache import (  # noqa: E402
    A_SCRIPT_PLAN_PATH,
    DAILY_SCENE_CARDS_PATH,
    EVENT_LINE_AUDIT_PATH,
    PROBE_QUESTION_PLAN_PATH,
    SCRIPT_TIMELINE_PATH,
    TAU_CONTRACT_PATH,
    refresh_canonical_timeline_from_files,
    update_cache_manifest,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ToM probe plan for the canonical script.")
    parser.add_argument("--scene-cards", type=Path, default=DAILY_SCENE_CARDS_PATH)
    parser.add_argument(
        "--probe-policy",
        type=Path,
        default=REPO_ROOT / "data/config/probe_question_policy.json",
    )
    parser.add_argument("--output", type=Path, default=PROBE_QUESTION_PLAN_PATH)
    parser.add_argument("--script-output", type=Path, default=A_SCRIPT_PLAN_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    probe_plan = generate_probe_question_plan(
        ProbeQuestionConfig(
            scene_cards_path=args.scene_cards,
            probe_policy_path=args.probe_policy,
        )
    )
    script_plan = generate_a_script_plan(
        scene_cards_doc=load_json(args.scene_cards),
        probe_question_plan=probe_plan,
    )
    write_json(args.output, probe_plan)
    write_json(args.script_output, script_plan)
    refresh_canonical_timeline_from_files()
    update_cache_manifest(
        {
            "canonical_timeline": SCRIPT_TIMELINE_PATH,
            "daily_scene_cards": args.scene_cards,
            "probe_question_plan": args.output,
            "a_script_plan": args.script_output,
            "tau_contract": TAU_CONTRACT_PATH,
            "event_line_audit": EVENT_LINE_AUDIT_PATH,
        },
        note="stage C probe plan refreshed",
    )
    print(f"Wrote {probe_plan['summary']['probe_count']} probe questions to {args.output}")
    print(f"Wrote {script_plan['summary']['unit_count']} script units to {args.script_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
