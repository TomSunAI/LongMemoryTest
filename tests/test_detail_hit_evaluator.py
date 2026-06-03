from __future__ import annotations

import unittest

from long_memory_test.evaluation.detail_hit_evaluator import (
    DetailTarget,
    build_detail_lookup,
    detect_address_terms,
    evaluate_variant_answer,
    find_keyword_hits,
)


class DetailHitEvaluatorTests(unittest.TestCase):
    def test_keyword_hit_detects_detail_anchor(self) -> None:
        detail = DetailTarget(
            detail_id="E001:kindergarten_information_vague",
            category="event",
            min_memory_level="M2",
            text="幼儿园不稳定的消息仍然模糊，用户还没有拿到正式通知或具体原因。",
            expected_response_mode="后续应先帮用户确认信息来源、正式通知和可行动窗口。",
            keywords=("消息模糊", "正式通知", "具体原因"),
            should_be_remembered=True,
            detail_retention="long_term",
        )

        result = evaluate_variant_answer(
            memory_level="M1",
            answer="现在先别急，核心是还没有正式通知，也不知道具体原因。",
            user_context="今天听到幼儿园可能不稳定。",
            target_ids=[detail.detail_id],
            detail_lookup={detail.detail_id: detail},
        )

        self.assertEqual(result["hit_detail_ids"], [detail.detail_id])
        self.assertEqual(result["forbidden_hit_detail_ids"], [detail.detail_id])

    def test_user_context_makes_lower_level_detail_allowed(self) -> None:
        detail = DetailTarget(
            detail_id="E001:kindergarten_information_vague",
            category="event",
            min_memory_level="M2",
            text="幼儿园不稳定的消息仍然模糊，用户还没有拿到正式通知或具体原因。",
            expected_response_mode="",
            keywords=("正式通知", "具体原因"),
            should_be_remembered=True,
            detail_retention="long_term",
        )

        result = evaluate_variant_answer(
            memory_level="M0",
            answer="那就先确认有没有正式通知、具体原因是什么。",
            user_context="我还没有看到正式通知，也不知道具体原因。",
            target_ids=[detail.detail_id],
            detail_lookup={detail.detail_id: detail},
        )

        self.assertEqual(result["allowed_hit_detail_ids"], [detail.detail_id])
        self.assertEqual(result["forbidden_hit_detail_ids"], [])

    def test_build_detail_lookup_reads_scene_card_expectations(self) -> None:
        scene_cards = {
            "scene_cards": [
                {
                    "memory_detail_expectations": {
                        "stable_details": [
                            {
                                "detail_id": "m1_response_style_direct",
                                "min_memory_level": "M1",
                                "text": "用户偏好直接、自然、少废话的回应。",
                            }
                        ],
                        "event_details": [
                            {
                                "detail_id": "E001:kindergarten_information_vague",
                                "template_anchor_id": "kindergarten_information_vague",
                                "min_memory_level": "M2",
                                "text": "幼儿园不稳定的消息仍然模糊。",
                            }
                        ],
                        "latent_concern_details": [],
                    }
                }
            ]
        }

        lookup = build_detail_lookup(scene_cards)

        self.assertIn("m1_response_style_direct", lookup)
        self.assertIn("E001:kindergarten_information_vague", lookup)
        self.assertIn("正式通知", lookup["E001:kindergarten_information_vague"].keywords)

    def test_address_term_detector_ignores_plain_pronouns(self) -> None:
        address = detect_address_terms("你现在作为妈妈会心疼，这是正常的。")

        self.assertEqual(address["risky_terms"], {})
        self.assertEqual(address["role_terms"], {"妈妈": 1})

    def test_find_keyword_hits_normalizes_whitespace(self) -> None:
        self.assertEqual(
            find_keyword_hits("没有 正式 通知", ["正式通知", "具体原因"]),
            ["正式通知"],
        )


if __name__ == "__main__":
    unittest.main()
