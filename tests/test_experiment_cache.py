from __future__ import annotations

import unittest

from long_memory_test.experiment_cache import (
    build_event_line_audit,
    build_canonical_timeline,
    split_memory_conditions,
)


class ExperimentCacheTests(unittest.TestCase):
    def test_build_canonical_timeline_uses_daily_contract_fields(self) -> None:
        timeline = {
            "timeline_days": 2,
            "events": [
                {
                    "event_id": "E001",
                    "day": 1,
                    "description": "幼儿园消息很模糊。",
                    "status": "new",
                },
                {
                    "event_id": "E002",
                    "day": 2,
                    "description": "幼儿园问题又绕回来。",
                    "status": "ongoing",
                    "related_event_id": "E001",
                },
            ],
        }
        daily_messages = {
            "messages": [
                {
                    "message_id": "D01_M001",
                    "day": 1,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "今天听到幼儿园消息。",
                    "primary_event_id": "E001",
                    "event_refs": ["E001"],
                    "script_stage": 0,
                    "intent": "problem_solving",
                    "memory_relevance": "possible_memory_candidate",
                },
                {
                    "message_id": "D02_M001",
                    "day": 2,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "这条线又绕回来了。",
                    "primary_event_id": "E002",
                    "event_refs": ["E002"],
                    "script_stage": 1,
                    "intent": "reflection",
                    "memory_relevance": "shared_event_memory",
                },
            ]
        }
        probes = {
            "probe_questions": [
                {
                    "probe_id": "D02_P001",
                    "insert_after_message_id": "D02_M001",
                    "tom_assessment": {
                        "hidden_user_need": "测试能否接上共同语境。",
                        "high_score_behavior": "接上旧线索。",
                    },
                }
            ]
        }
        bei = {
            "annotations": [
                {
                    "probe_id": "D02_P001",
                    "relational_expectation": "不要让用户重讲背景。",
                    "gold_response_strategy": "自然接上持续事件线。",
                }
            ]
        }

        result = build_canonical_timeline(
            event_timeline=timeline,
            daily_messages=daily_messages,
            probe_question_plan=probes,
            bei_annotations=bei,
        )

        day2 = result["days"][1]
        self.assertEqual(result["schema_version"], "timeline_v1_event_first_daily")
        self.assertEqual(day2["main_topic"], "孩子幼儿园可能不稳定")
        self.assertEqual(day2["related_previous_days"], [1])
        self.assertTrue(day2["probe_candidate"])
        self.assertEqual(day2["probe_ids"], ["D02_P001"])
        self.assertEqual(day2["latent_continuity"], "不要让用户重讲背景。")

    def test_build_canonical_timeline_prefers_planned_event_stage(self) -> None:
        result = build_canonical_timeline(
            event_timeline={
                "timeline_days": 1,
                "events": [
                    {
                        "event_id": "E001",
                        "day": 1,
                        "description": "合作已经决定降级处理。",
                        "status": "ongoing",
                        "planned_event_stage": "resolution",
                    }
                ],
            },
            daily_messages={
                "messages": [
                    {
                        "message_id": "D01_M001",
                        "day": 1,
                        "topic": "合作项目推进不顺",
                        "user_message": "我今天只是想确认是不是可以先放一放。",
                        "primary_event_id": "E001",
                        "event_refs": ["E001"],
                        "script_stage": 3,
                        "intent": "reflection",
                    }
                ]
            },
        )

        self.assertEqual(result["days"][0]["event_stage"], "resolution")

    def test_build_event_line_audit_counts_candidates_and_probe_dimensions(self) -> None:
        audit = build_event_line_audit(
            canonical_timeline={
                "days": [
                    {
                        "day": 1,
                        "main_topic": "合作项目推进不顺",
                        "event_stage": "initial",
                        "probe_candidate": True,
                        "probe_ids": ["D01_P001"],
                    },
                    {
                        "day": 2,
                        "main_topic": "合作项目推进不顺",
                        "event_stage": "turning_point",
                        "probe_candidate": False,
                        "probe_ids": [],
                    },
                ]
            },
            probe_question_plan={
                "probe_questions": [
                    {
                        "probe_id": "D01_P001",
                        "day": 1,
                        "probe_type": "state_transformation",
                        "tom_dimensions": ["shared_context_invocation"],
                        "required_memory_type": ["event_memory"],
                    }
                ]
            },
        )

        self.assertEqual(
            audit["candidate_selection_contract"]["actual_candidate_node_count"],
            1,
        )
        self.assertEqual(audit["probe_set_contract"]["actual_probe_count"], 1)
        self.assertEqual(
            audit["probe_set_contract"]["tom_dimension_counts"]["shared_context_invocation"],
            1,
        )
        self.assertIn("topic_lines", audit)

    def test_build_event_line_audit_tracks_resolution_as_required_stage(self) -> None:
        audit = build_event_line_audit(
            canonical_timeline={
                "days": [
                    {
                        "day": 1,
                        "main_topic": "睡眠被打碎",
                        "event_stage": "initial",
                        "probe_candidate": True,
                        "probe_ids": ["D01_P001"],
                    },
                    {
                        "day": 2,
                        "main_topic": "睡眠被打碎",
                        "event_stage": "recurrence",
                        "probe_candidate": False,
                        "probe_ids": [],
                    },
                    {
                        "day": 3,
                        "main_topic": "睡眠被打碎",
                        "event_stage": "turning_point",
                        "probe_candidate": False,
                        "probe_ids": [],
                    },
                    {
                        "day": 4,
                        "main_topic": "睡眠被打碎",
                        "event_stage": "reflection",
                        "probe_candidate": False,
                        "probe_ids": [],
                    },
                ]
            },
            probe_question_plan={
                "probe_questions": [
                    {
                        "probe_id": "D01_P001",
                        "day": 1,
                        "probe_type": "current_understanding",
                        "tom_dimensions": ["emotional_state_recognition"],
                    }
                ]
            },
        )

        topic_line = audit["topic_lines"][0]
        self.assertFalse(topic_line["coverage"]["has_resolution"])
        self.assertEqual(
            topic_line["suggested_fix"],
            "Add a downgrade/recovery node so the line does not only repeat or escalate.",
        )

    def test_split_memory_conditions_writes_per_condition_payloads(self) -> None:
        split = split_memory_conditions(
            {
                "condition_specs": [
                    {"condition_id": "M0", "name": "Generic"},
                    {"condition_id": "M1", "name": "Conclusion"},
                    {"condition_id": "M2", "name": "Summary"},
                    {"condition_id": "M3", "name": "Anchor"},
                ],
                "default_payloads": {
                    "M0": {"memory_context": "generic"},
                    "M1": {"memory_context": "m1"},
                    "M2": {"memory_context": "m2"},
                    "M3": {"memory_context": "m3"},
                },
                "memory_payloads_by_message_id": {
                    "D01_P001": {
                        "M0": {"memory_context": "generic d1"},
                        "M1": {"memory_context": "m1 d1"},
                        "M2": {"memory_context": "m2 d1"},
                        "M3": {"memory_context": "m3 d1"},
                    }
                },
            }
        )

        self.assertEqual(split["M0"]["schema_version"], "memory_condition_v1")
        self.assertEqual(split["M2"]["condition_id"], "M2")
        self.assertEqual(
            split["M3"]["payloads_by_message_id"]["D01_P001"]["memory_context"],
            "m3 d1",
        )


if __name__ == "__main__":
    unittest.main()
