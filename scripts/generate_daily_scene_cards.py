#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.daily_scene_card_generator import (  # noqa: E402
    DailySceneCardConfig,
    generate_daily_scene_cards,
)
from long_memory_test.agents.event_stream_generator import write_json  # noqa: E402
from long_memory_test.experiment_cache import (  # noqa: E402
    CACHE_TIMELINE_EVENTS_PATH,
    DAILY_SCENE_CARDS_PATH,
    DAILY_USER_MESSAGE_PATH,
    update_cache_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate script-anchored daily scene cards for LLM user follow-ups."
    )
    parser.add_argument(
        "--timeline",
        type=Path,
        default=CACHE_TIMELINE_EVENTS_PATH,
        help="Path to cached event-level timeline.json.",
    )
    parser.add_argument(
        "--daily-messages",
        type=Path,
        default=DAILY_USER_MESSAGE_PATH,
        help="Path to daily_user_message.json.",
    )
    parser.add_argument(
        "--user-actor",
        type=Path,
        default=REPO_ROOT / "data/config/user_actor.json",
        help="Path to user_actor.json.",
    )
    parser.add_argument(
        "--expansion-policy",
        type=Path,
        default=REPO_ROOT / "data/config/conversation_expansion_policy.json",
        help="Path to conversation_expansion_policy.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DAILY_SCENE_CARDS_PATH,
        help="Output path for daily_scene_cards.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = generate_daily_scene_cards(
        DailySceneCardConfig(
            timeline_path=args.timeline,
            daily_messages_path=args.daily_messages,
            user_actor_path=args.user_actor,
            expansion_policy_path=args.expansion_policy,
        )
    )
    write_json(args.output, result)
    update_cache_manifest(
        {
            "event_timeline_cache": args.timeline,
            "daily_user_message": args.daily_messages,
            "daily_scene_cards": args.output,
        },
        note="daily scene cards refreshed",
    )
    print(f"Wrote {len(result['scene_cards'])} daily scene cards to {args.output}")


if __name__ == "__main__":
    main()
