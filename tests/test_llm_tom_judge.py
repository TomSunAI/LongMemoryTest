from __future__ import annotations

import json
import unittest

from long_memory_test.evaluation.llm_tom_judge import (
    build_judge_case,
    evaluate_tom_quality_with_llm_judge,
    normalize_judgement,
    parse_judge_output,
)
from long_memory_test.llm import LLMConfig


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return _FakeCompletion(self.content)


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = _FakeChat(content)

    def with_options(self, **kwargs):
        return self


class LlmTomJudgeTests(unittest.TestCase):
    def test_parse_judge_output_accepts_fenced_json(self) -> None:
        parsed = parse_judge_output(
            '```json\n{"confidence": 0.8, "dimension_scores": {}}\n```'
        )

        self.assertEqual(parsed["confidence"], 0.8)

    def test_normalize_judgement_computes_score_from_dimensions(self) -> None:
        normalized = normalize_judgement(
            judgement={
                "dimension_scores": {
                    "hidden_intent_recognition": {
                        "score": 2,
                        "evidence_quote": "不是只在问选项",
                        "reason": "接住隐含意图",
                    },
                    "emotional_state_recognition": {
                        "score": 1,
                        "evidence_quote": "担心",
                        "reason": "部分识别情绪",
                    },
                },
                "flags": {"generic_comfort": True},
                "confidence": 0.9,
            },
            dimensions=[
                "hidden_intent_recognition",
                "emotional_state_recognition",
            ],
            raw_output="{}",
        )

        self.assertEqual(normalized["tom_score"], 50.0)
        self.assertTrue(normalized["flags"]["generic_comfort"])
        self.assertIn("instruction_only_success", normalized["failure_types"])
        self.assertTrue(normalized["needs_human_review"])
        self.assertEqual(
            normalized["dimension_scores"]["hidden_intent_recognition"][
                "strict_adjustments"
            ],
            ["generic_comfort_flag_cap"],
        )

    def test_build_judge_case_does_not_expose_variant_name(self) -> None:
        turns = [
            _turn("D01_M001", "普通开场", "之前回答", {}),
            _turn(
                "D01_P001",
                "我有点怕你又开始给我标准答案了。",
                "我不会用标准答案，我们先拆事实。",
                {
                    "tom_dimensions": ["hidden_intent_recognition"],
                    "tom_assessment": {
                        "hidden_user_need": "用户在确认 AI 是否还保持熟悉回应方式。",
                        "high_score_behavior": "承接用户对回应方式的期待。",
                    },
                },
            ),
        ]

        case = build_judge_case(
            turns=turns,
            turn_position=1,
            variant_name="M0",
            context_turns=3,
            max_answer_chars=500,
            max_context_answer_chars=200,
        )

        dumped = json.dumps(case, ensure_ascii=False)
        self.assertNotIn("variant_name", dumped)
        self.assertNotIn("memory_level", dumped)
        self.assertNotIn('"M0"', dumped)
        self.assertNotIn("hidden_user_need", dumped)
        self.assertNotIn("high_score_behavior", dumped)
        self.assertEqual(case["case_id"], "D01_P001")
        self.assertEqual(case["blind_condition"], "Condition A")
        self.assertIn("memory_condition", case)
        self.assertEqual(case["allowed_context"]["recent_dialogue"][0]["message_id"], "D01_M001")
        self.assertIn("strict_scoring_contract", case)

    def test_evaluate_tom_quality_with_llm_judge_aggregates_fake_client_result(self) -> None:
        fake_output = json.dumps(
            {
                "dimension_scores": {
                    "hidden_intent_recognition": {
                        "score": 2,
                        "evidence_quote": "不是标准答案",
                        "reason": "识别出关系期待背后的隐含需求。",
                    }
                },
                "failure_types": [],
                "flags": {
                    "memory_absence": False,
                    "memory_misuse": False,
                    "memory_overuse": False,
                    "fabrication": False,
                    "alienation": False,
                    "instruction_only_success": False,
                },
                "overall_reason": "回答接住了用户担心 AI 变陌生的潜台词。",
                "confidence": 0.88,
                "needs_human_review": False,
                "answer_excerpt": "不是标准答案",
            },
            ensure_ascii=False,
        )
        evaluation = evaluate_tom_quality_with_llm_judge(
            conversation_log={
                "turns": [
                    _turn(
                        "D01_P001",
                        "我有点怕你又开始给我标准答案了。",
                        "我不会用标准答案，我们先拆事实。",
                        {
                            "tom_dimensions": ["hidden_intent_recognition"],
                            "tom_assessment": {
                                "hidden_user_need": "用户在确认 AI 是否还保持熟悉回应方式。",
                                "high_score_behavior": "承接用户对回应方式的期待。",
                            },
                        },
                    )
                ]
            },
            client=_FakeClient(fake_output),
            llm_config=LLMConfig(
                provider="deepseek",
                api_key="test",
                base_url="https://example.test",
                model="deepseek-test",
            ),
            limit=1,
        )

        self.assertEqual(evaluation["summary"]["variants"]["M0"]["turn_count"], 1)
        self.assertEqual(evaluation["summary"]["variants"]["M0"]["average_tom_score"], 100.0)
        self.assertEqual(evaluation["method"]["judge_model"], "deepseek-test")


def _turn(
    message_id: str,
    user_message: str,
    assistant_answer: str,
    input_extra: dict,
) -> dict:
    input_payload = {
        "message_id": message_id,
        "day": 1,
        "topic": "测试主题",
        "user_message": user_message,
    }
    input_payload.update(input_extra)
    return {
        "turn_index": 1,
        "source": {
            "message_id": message_id,
            "turn_type": "targeted_probe" if "_P" in message_id else "scripted_opening",
        },
        "input": input_payload,
        "variants": {
            "M0": {
                "assistant_answer": assistant_answer,
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
