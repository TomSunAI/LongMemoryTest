from __future__ import annotations

import argparse
import json
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.agents import dialogue_runner_helpers as runner_helpers  # noqa: E402


class FakeCompletions:
    def __init__(self) -> None:
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        message = types.SimpleNamespace(
            content=(
                '{"user_message":"消息还很模糊，我先想确认第一步。",'
                '"move_id":"push_for_concreteness",'
                '"used_fact_ids":[],"used_concern_ids":[],"reason":"测试"}'
            )
        )
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


class FakeClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = types.SimpleNamespace(completions=self.completions)

    def with_options(self, **kwargs):
        return self


class DialogueRunnerHelpersTests(unittest.TestCase):
    def test_resolve_all_message_ids(self) -> None:
        args = argparse.Namespace(
            all_message_ids=True,
            message_ids=None,
            message_id="D01_M001",
        )
        messages = [{"message_id": "D01_M001"}, {"message_id": "D02_M001"}]

        self.assertEqual(
            runner_helpers.resolve_message_ids(args, messages),
            ["D01_M001", "D02_M001"],
        )

    def test_parse_json_object_handles_markdown_fence(self) -> None:
        raw = '```json\n{"user_message":"你好","move_id":"push_for_concreteness"}\n```'

        self.assertEqual(runner_helpers.parse_json_object(raw)["user_message"], "你好")

    def test_build_followup_message_preserves_opening_metadata(self) -> None:
        opening = {
            "message_id": "D01_M001",
            "day": 1,
            "event_refs": ["E001"],
            "primary_event_id": "E001",
            "related_event_id": None,
            "domains": ["parenting"],
            "topic": "孩子幼儿园可能不稳定",
            "script_stage": 0,
            "intent": "problem_solving",
            "tone": "urgent",
            "conversation_goal": "separate_facts_from_assumptions",
            "memory_relevance": "possible_memory_candidate",
        }
        followup = {"user_message": "消息还很模糊，我先想确认第一步。"}

        result = runner_helpers.build_followup_message(
            opening_message=opening,
            scene_card={"scene_id": "D01_SCENE"},
            followup_index=1,
            followup=followup,
        )

        self.assertEqual(result["message_id"], "D01_M001_F001")
        self.assertEqual(result["turn_type"], "llm_user_followup")
        self.assertEqual(result["event_refs"], ["E001"])
        self.assertEqual(result["scene_id"], "D01_SCENE")

    def test_expected_message_id_sequence_includes_followups(self) -> None:
        messages = [{"message_id": "D01_M001"}, {"message_id": "D02_M001"}]
        scene_cards = {
            "D01_M001": {"expansion_controls": {"followup_budget": 2}},
            "D02_M001": {"expansion_controls": {"followup_budget": 1}},
        }

        self.assertEqual(
            runner_helpers.expected_message_id_sequence(
                messages=messages,
                scene_cards=scene_cards,
                scene_followups=1,
            ),
            ["D01_M001", "D01_M001_F001", "D02_M001", "D02_M001_F001"],
        )

    def test_expected_message_id_sequence_includes_probe_questions(self) -> None:
        messages = [{"message_id": "D01_M001"}]
        scene_cards = {"D01_M001": {"expansion_controls": {"followup_budget": 1}}}
        probe_questions = {
            "D01_M001": [
                {"message_id": "D01_P001"},
                {"message_id": "D01_P002"},
            ]
        }

        self.assertEqual(
            runner_helpers.expected_message_id_sequence(
                messages=messages,
                scene_cards=scene_cards,
                scene_followups=1,
                probe_questions=probe_questions,
            ),
            ["D01_M001", "D01_M001_F001", "D01_P001", "D01_P002"],
        )

    def test_completed_turns_must_be_expected_prefix(self) -> None:
        turns = [
            {"source": {"message_id": "D01_M001"}},
            {"source": {"message_id": "D02_M001"}},
        ]

        with self.assertRaises(ValueError):
            runner_helpers.assert_completed_turns_are_expected_prefix(
                turns,
                ["D01_M001", "D01_M001_F001", "D02_M001"],
            )

    def test_write_checkpoint_syncs_log_without_duplicate_run_turns(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_path = tmp_path / "probe.json"
            log_path = tmp_path / "conversation_log.json"
            result = {
                "run_id": "run-1",
                "expected_turns": 2,
                "turns": [self._fake_turn("run-1", 1, "D01_M001")],
            }
            runner_helpers.write_checkpoint(
                output_path=output_path,
                conversation_log_path=log_path,
                result=result,
                reset_conversation_log=False,
                status="running",
            )
            result["turns"].append(self._fake_turn("run-1", 2, "D01_M001_F001"))
            runner_helpers.write_checkpoint(
                output_path=output_path,
                conversation_log_path=log_path,
                result=result,
                reset_conversation_log=False,
                status="complete",
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            log = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["checkpoint"]["status"], "complete")
            self.assertEqual(len(log["turns"]), 2)
            self.assertEqual(
                [turn["source"]["message_id"] for turn in log["turns"]],
                ["D01_M001", "D01_M001_F001"],
            )

    def test_rebuild_runtime_state_restores_histories(self) -> None:
        turns = [
            self._fake_turn("run-1", 1, "D01_M001"),
            self._fake_turn("run-1", 2, "D01_M001_F001"),
        ]

        histories, transcript_ids, completed_inputs = (
            runner_helpers.rebuild_two_condition_runtime_state(turns)
        )

        self.assertEqual(transcript_ids, ["D01_M001", "D01_M001_F001"])
        self.assertEqual(len(histories["M0"]), 4)
        self.assertEqual(len(histories["M1"]), 4)
        self.assertIn("D01_M001_F001", completed_inputs)

    def test_user_followup_prompt_contains_hard_fact_boundary(self) -> None:
        fake_client = FakeClient()
        scene_card = {
            "scene_id": "D01_SCENE",
            "expansion_controls": {
                "reveal_schedule": [
                    {
                        "followup_index": 1,
                        "preferred_moves": ["push_for_concreteness"],
                        "may_reveal_fact_ids": [],
                        "may_reveal_concern_ids": [],
                    }
                ]
            },
        }
        opening = {
            "message_id": "D01_M001",
            "user_message": "今天听到幼儿园那边可能不太稳定的消息。",
        }

        result = runner_helpers.generate_user_followup(
            client=fake_client,
            model="deepseek-v4-pro",
            scene_card=scene_card,
            opening_message=opening,
            followup_index=1,
            previous_user_messages=[opening["user_message"]],
            timeout=1,
            max_tokens=100,
        )

        self.assertEqual(result["user_message"], "消息还很模糊，我先想确认第一步。")
        request = fake_client.completions.last_request
        system_prompt = request["messages"][0]["content"]
        user_payload = request["messages"][1]["content"]
        self.assertIn(
            "assistant 回复里的例子、假设和建议不是用户事实",
            system_prompt,
        )
        self.assertIn("换承办方", user_payload)
        self.assertIn("do_not_make_the_instability_more_specific", user_payload)

    def test_build_evaluation_targets_ignores_scene_card_details_for_tom_only_quality(self) -> None:
        targets = runner_helpers.build_evaluation_targets(
            {
                "memory_detail_expectations": {
                    "stable_details": [
                        {"detail_id": "m1_response_style_direct"}
                    ],
                    "event_details": [
                        {"detail_id": "E001:kindergarten_information_vague"}
                    ],
                    "latent_concern_details": [
                        {"detail_id": "parenting_001:latent_1"}
                    ],
                    "level_rules": {"M1": "stable details only"},
                    "audit_dimensions": ["fact_continuity_candidate"],
                }
            }
        )

        self.assertEqual(targets, {})

    def test_build_evaluation_targets_ignores_explicit_detail_ids_without_tom_assessment(self) -> None:
        scene_card = {
            "memory_detail_expectations": {
                "stable_details": [
                    {"detail_id": "m1_response_style_direct"}
                ],
                "event_details": [
                    {"detail_id": "E001:kindergarten_information_vague"},
                    {"detail_id": "E002:collaboration_logic_misaligned"},
                ],
                "latent_concern_details": [
                    {"detail_id": "parenting_001:latent_1"}
                ],
            }
        }
        message = {
            "target_detail_ids": [
                "E002:collaboration_logic_misaligned",
                "parenting_001:latent_1",
            ]
        }

        self.assertEqual(runner_helpers.build_evaluation_targets(scene_card, message), {})

    def test_build_evaluation_targets_prefers_tom_quality_for_tom_probe(self) -> None:
        targets = runner_helpers.build_evaluation_targets(
            {
                "memory_detail_expectations": {
                    "stable_details": [{"detail_id": "m1_response_style_direct"}],
                    "event_details": [],
                    "latent_concern_details": [],
                }
            },
            {
                "tom_dimensions": ["hidden_intent_recognition"],
                "tom_assessment": {
                    "surface_question": "用户表面上怕标准答案。",
                    "hidden_user_need": "用户在确认 AI 是否还保持熟悉回应方式。",
                    "low_score_behavior": "客服式模板。",
                    "high_score_behavior": "承接关系期待后再拆事实。",
                },
                "target_detail_ids": ["m1_response_style_direct"],
            },
        )

        self.assertIn("tom_quality", targets)
        self.assertNotIn("detail_recall", targets)
        self.assertEqual(
            targets["tom_quality"]["dimensions"],
            ["hidden_intent_recognition"],
        )

    def _fake_turn(self, run_id: str, turn_index: int, message_id: str) -> dict:
        return {
            "run_id": run_id,
            "turn_index": turn_index,
            "source": {"message_id": message_id},
            "input": {"day": 1, "user_message": "测试用户消息"},
            "variants": {
                "M0": {"assistant_answer": "M0"},
                "M1": {"assistant_answer": "M1"},
            },
        }


if __name__ == "__main__":
    unittest.main()
