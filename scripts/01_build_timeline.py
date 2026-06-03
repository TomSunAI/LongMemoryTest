#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.daily_message_generator import (  # noqa: E402
    DailyMessageConfig,
    generate_daily_user_messages,
)
from long_memory_test.agents.daily_scene_card_generator import (  # noqa: E402
    DailySceneCardConfig,
    generate_daily_scene_cards,
)
from long_memory_test.agents.event_stream_generator import (  # noqa: E402
    DEFAULT_TIMELINE_DAYS,
    GeneratorConfig,
    generate_timeline,
)
from long_memory_test.experiment_cache import (  # noqa: E402
    CACHE_MANIFEST_PATH,
    CACHE_TIMELINE_EVENTS_PATH,
    DAILY_SCENE_CARDS_PATH,
    DAILY_USER_MESSAGE_PATH,
    SCRIPT_TIMELINE_PATH,
    refresh_canonical_timeline_from_files,
    update_cache_manifest,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the canonical event-first script data structure."
    )
    parser.add_argument(
        "--persona",
        type=Path,
        default=REPO_ROOT / "data/config/persona.json",
    )
    parser.add_argument(
        "--life-domains",
        type=Path,
        default=REPO_ROOT / "data/config/life_domains.json",
    )
    parser.add_argument(
        "--event-templates",
        type=Path,
        default=REPO_ROOT / "data/config/event_templates.json",
    )
    parser.add_argument(
        "--user-actor",
        type=Path,
        default=REPO_ROOT / "data/config/user_actor.json",
    )
    parser.add_argument(
        "--expansion-policy",
        type=Path,
        default=REPO_ROOT / "data/config/conversation_expansion_policy.json",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_TIMELINE_DAYS)
    parser.add_argument("--timeline-seed", type=int, default=42)
    parser.add_argument("--message-seed", type=int, default=142)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event_timeline = generate_timeline(
        GeneratorConfig(
            persona_path=args.persona,
            life_domains_path=args.life_domains,
            event_templates_path=args.event_templates,
            timeline_days=args.days,
            seed=args.timeline_seed,
        )
    )
    write_json(CACHE_TIMELINE_EVENTS_PATH, event_timeline)

    daily_messages = generate_daily_user_messages(
        DailyMessageConfig(
            timeline_path=CACHE_TIMELINE_EVENTS_PATH,
            seed=args.message_seed,
        )
    )
    write_json(DAILY_USER_MESSAGE_PATH, daily_messages)

    scene_cards = generate_daily_scene_cards(
        DailySceneCardConfig(
            timeline_path=CACHE_TIMELINE_EVENTS_PATH,
            daily_messages_path=DAILY_USER_MESSAGE_PATH,
            user_actor_path=args.user_actor,
            expansion_policy_path=args.expansion_policy,
        )
    )
    write_json(DAILY_SCENE_CARDS_PATH, scene_cards)

    canonical = refresh_canonical_timeline_from_files()
    update_cache_manifest(
        {
            "canonical_timeline": SCRIPT_TIMELINE_PATH,
            "event_timeline_cache": CACHE_TIMELINE_EVENTS_PATH,
            "daily_user_message": DAILY_USER_MESSAGE_PATH,
            "daily_scene_cards": DAILY_SCENE_CARDS_PATH,
            "cache_manifest": CACHE_MANIFEST_PATH,
        },
        note="stage A script data refreshed",
    )
    print(f"Wrote canonical timeline days={len(canonical['days'])} to {SCRIPT_TIMELINE_PATH}")
    print(f"Wrote event cache to {CACHE_TIMELINE_EVENTS_PATH}")
    print(f"Wrote daily messages to {DAILY_USER_MESSAGE_PATH}")
    print(f"Wrote scene cards to {DAILY_SCENE_CARDS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
