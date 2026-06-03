from __future__ import annotations

import unittest

from long_memory_test.evaluation.tom_quality_evaluator import (
    evaluate_tom_quality,
    evaluate_variant_tom_answer,
)


class ToMQualityEvaluatorTests(unittest.TestCase):
    def test_hidden_intent_and_emotion_score_high(self) -> None:
        result = evaluate_variant_tom_answer(
            answer=(
                "你不是只在问换不换园，而是担心孩子被反复折腾。"
                "这个不安是真实的，我们先把事实和脑补分开。"
            ),
            user_message="我更怕孩子被反复折腾。你能听懂我这层担心吗？",
            dimensions=["hidden_intent_recognition", "emotional_state_recognition"],
            tom_assessment={
                "hidden_user_need": "用户希望 AI 听见深层担心，而不是只给择校或行动清单。",
                "high_score_behavior": "把孩子稳定性、信息仍模糊和用户不安联系起来。",
            },
        )

        self.assertEqual(result["tom_score"], 100.0)
        self.assertEqual(
            result["dimension_results"]["hidden_intent_recognition"]["score"],
            2,
        )

    def test_alienation_terms_lower_alienation_score(self) -> None:
        result = evaluate_variant_tom_answer(
            answer="亲爱的用户，请重新说明你的背景，我才能继续判断。",
            user_message="别像陌生客服一样。",
            dimensions=["alienation_error_rate"],
            tom_assessment={
                "hidden_user_need": "用户在测试 AI 是否理解当前关系位置。",
                "high_score_behavior": "保持熟悉但不过度表演的语气。",
            },
        )

        self.assertEqual(result["tom_score"], 0.0)
        self.assertIn("亲爱的", result["risks"]["alienation_terms"])
        self.assertIn("用户", result["risks"]["alienation_terms"])

    def test_evaluate_tom_quality_ignores_non_probe_turns(self) -> None:
        conversation_log = {
            "turns": [
                {
                    "turn_index": 1,
                    "source": {"message_id": "D01_M001"},
                    "input": {"user_message": "普通开场"},
                    "variants": {"M0": {"assistant_answer": "普通回答"}},
                },
                {
                    "turn_index": 2,
                    "source": {"message_id": "D01_P001"},
                    "input": {
                        "day": 1,
                        "message_id": "D01_P001",
                        "probe_type": "m1_response_style",
                        "topic": "孩子幼儿园可能不稳定",
                        "user_message": "我有点怕你又开始给我标准答案了。",
                        "tom_dimensions": [
                            "hidden_intent_recognition",
                            "relationship_expectation_recognition",
                        ],
                        "tom_assessment": {
                            "hidden_user_need": "用户在确认 AI 是否还保持之前熟悉的回应方式。",
                            "high_score_behavior": "先承接用户对回应方式的期待。",
                        },
                    },
                    "variants": {
                        "M0": {
                            "assistant_answer": (
                                "我听到的不是普通提问，而是你担心我变成标准答案。"
                                "我们还是按之前熟悉的方式，直接拆事实和风险。"
                            )
                        }
                    },
                },
            ]
        }

        evaluation = evaluate_tom_quality(conversation_log=conversation_log)

        self.assertEqual(len(evaluation["turns"]), 1)
        self.assertEqual(evaluation["summary"]["variants"]["M0"]["turn_count"], 1)


if __name__ == "__main__":
    unittest.main()
