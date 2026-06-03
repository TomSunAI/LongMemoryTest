from __future__ import annotations

import unittest
from pathlib import Path

from long_memory_test.agents.daily_scene_card_generator import (
    DailySceneCardConfig,
    generate_daily_scene_cards,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class DailySceneCardGeneratorTests(unittest.TestCase):
    def test_generates_one_scene_card_per_daily_message(self) -> None:
        result = generate_daily_scene_cards(
            DailySceneCardConfig(
                timeline_path=REPO_ROOT / "sample_output/timeline.json",
                daily_messages_path=REPO_ROOT / "sample_output/daily_user_message.json",
                user_actor_path=REPO_ROOT / "data/config/user_actor.json",
                expansion_policy_path=(
                    REPO_ROOT / "data/config/conversation_expansion_policy.json"
                ),
            )
        )

        scene_cards = result["scene_cards"]
        self.assertEqual(len(scene_cards), 30)
        self.assertEqual(result["summary"]["scene_count"], 30)
        self.assertEqual(scene_cards[0]["scene_id"], "D01_SCENE")
        self.assertEqual(scene_cards[0]["opening_message_id"], "D01_M001")

    def test_scene_card_contains_script_boundary_fields(self) -> None:
        result = generate_daily_scene_cards(
            DailySceneCardConfig(
                timeline_path=REPO_ROOT / "sample_output/timeline.json",
                daily_messages_path=REPO_ROOT / "sample_output/daily_user_message.json",
                user_actor_path=REPO_ROOT / "data/config/user_actor.json",
                expansion_policy_path=(
                    REPO_ROOT / "data/config/conversation_expansion_policy.json"
                ),
            )
        )
        card = result["scene_cards"][0]

        self.assertIn("script_anchor", card)
        self.assertIn("allowed_facts", card)
        self.assertIn("latent_concerns", card)
        self.assertIn("memory_detail_expectations", card)
        self.assertIn("expansion_controls", card)
        self.assertGreaterEqual(card["expansion_controls"]["followup_budget"], 1)
        self.assertTrue(card["expansion_controls"]["reveal_schedule"])
        self.assertIn("new family members", card["expansion_controls"]["must_not_invent"])

    def test_scene_card_contains_memory_detail_targets(self) -> None:
        result = generate_daily_scene_cards(
            DailySceneCardConfig(
                timeline_path=REPO_ROOT / "sample_output/timeline.json",
                daily_messages_path=REPO_ROOT / "sample_output/daily_user_message.json",
                user_actor_path=REPO_ROOT / "data/config/user_actor.json",
                expansion_policy_path=(
                    REPO_ROOT / "data/config/conversation_expansion_policy.json"
                ),
            )
        )
        card = result["scene_cards"][0]
        expectations = card["memory_detail_expectations"]

        self.assertGreater(result["summary"]["event_detail_target_count"], 0)
        self.assertGreater(result["summary"]["long_term_event_detail_target_count"], 0)
        self.assertGreater(len(expectations["stable_details"]), 0)
        self.assertGreater(len(expectations["event_details"]), 0)
        self.assertIn("M1", expectations["level_rules"])
        self.assertIn(
            "memory_detail_anchor",
            {fact["type"] for fact in card["allowed_facts"]},
        )
        self.assertTrue(
            expectations["event_details"][0]["detail_id"].startswith("E001:")
        )
        self.assertTrue(expectations["event_details"][0]["should_be_remembered"])


if __name__ == "__main__":
    unittest.main()
