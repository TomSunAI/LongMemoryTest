from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents.probe_question_generator import (  # noqa: E402
    ProbeQuestionConfig,
    generate_a_script_plan,
    generate_probe_question_plan,
)


class ProbeQuestionGeneratorTests(unittest.TestCase):
    def test_generates_targeted_probe_plan_for_a_script(self) -> None:
        plan = generate_probe_question_plan(
            ProbeQuestionConfig(
                scene_cards_path=REPO_ROOT / "sample_output/daily_scene_cards.json",
                probe_policy_path=REPO_ROOT / "data/config/probe_question_policy.json",
            )
        )

        self.assertEqual(plan["summary"]["probe_count"], 36)
        self.assertEqual(plan["summary"]["probe_type_counts"]["natural_detail"], 7)
        self.assertEqual(plan["summary"]["probe_type_counts"]["memory_invocation"], 6)
        self.assertIn("hidden_intent_recognition", plan["summary"]["tom_dimension_counts"])
        self.assertIn("relationship_expectation_recognition", plan["summary"]["tom_dimension_counts"])
        self.assertIn("memory_misuse", plan["summary"]["tom_dimension_counts"])
        self.assertGreaterEqual(plan["summary"]["dependency_group_count"], 4)
        self.assertIn(1, plan["summary"]["days_with_probes"])
        self.assertIn(29, plan["summary"]["days_with_probes"])

    def test_probe_questions_include_tom_assessment(self) -> None:
        plan = generate_probe_question_plan(
            ProbeQuestionConfig(
                scene_cards_path=REPO_ROOT / "sample_output/daily_scene_cards.json",
                probe_policy_path=REPO_ROOT / "data/config/probe_question_policy.json",
            )
        )

        style_probe = next(
            probe
            for probe in plan["probe_questions"]
            if probe["message_id"] == "D01_P001"
        )
        self.assertEqual(style_probe["probe_type"], "current_understanding")
        self.assertEqual(style_probe["tone"], "implicit_tom_probe")
        self.assertIn("relationship_expectation_recognition", style_probe["tom_dimensions"])
        self.assertIn("required_memory_type", style_probe)
        self.assertIn("gold_bei", style_probe)
        self.assertIn("dependency_analysis", style_probe)
        self.assertIn("hidden_user_need", style_probe["tom_assessment"])
        self.assertIn("隐含意图", style_probe["tom_assessment"]["hidden_user_need"])

    def test_m3_probe_targets_primary_event_details_before_secondary_events(self) -> None:
        plan = generate_probe_question_plan(
            ProbeQuestionConfig(
                scene_cards_path=REPO_ROOT / "sample_output/daily_scene_cards.json",
                probe_policy_path=REPO_ROOT / "data/config/probe_question_policy.json",
            )
        )

        cooperation_probe = next(
            probe
            for probe in plan["probe_questions"]
            if probe["message_id"] == "D02_P002"
        )
        self.assertEqual(cooperation_probe["probe_type"], "natural_detail")
        self.assertEqual(
            cooperation_probe["target_detail_ids"],
            [
                "E002:collaboration_logic_misaligned",
                "E002:collaboration_realigning_cost",
                "career_001:latent_1",
                "career_001:latent_2",
            ],
        )

    def test_generates_full_a_script_plan_with_openings_followups_and_probes(self) -> None:
        scene_cards_doc = json.loads(
            (REPO_ROOT / "sample_output/daily_scene_cards.json").read_text(encoding="utf-8")
        )
        probe_plan = generate_probe_question_plan(
            ProbeQuestionConfig(
                scene_cards_path=REPO_ROOT / "sample_output/daily_scene_cards.json",
                probe_policy_path=REPO_ROOT / "data/config/probe_question_policy.json",
            )
        )

        script_plan = generate_a_script_plan(
            scene_cards_doc=scene_cards_doc,
            probe_question_plan=probe_plan,
        )

        self.assertEqual(script_plan["summary"]["unit_count"], 130)
        self.assertEqual(script_plan["summary"]["turn_type_counts"]["scripted_opening"], 30)
        self.assertEqual(script_plan["summary"]["turn_type_counts"]["llm_user_followup_slot"], 64)
        self.assertEqual(script_plan["summary"]["turn_type_counts"]["targeted_probe"], 36)
        probe_unit = next(
            unit
            for unit in script_plan["script_units"]
            if unit["message_id"] == "D01_P001"
        )
        self.assertIn("tom_assessment", probe_unit)
        self.assertIn("relationship_expectation_recognition", probe_unit["tom_dimensions"])
        self.assertIn("dependency_analysis", probe_unit)


if __name__ == "__main__":
    unittest.main()
