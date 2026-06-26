from __future__ import annotations

import unittest

from long_memory_test.sampling.daily_interaction_constructor import (
    DailyInteractionConstructionConfig,
    construct_daily_interactions_for_timeline,
)


class SamplingDailyInteractionConstructorTests(unittest.TestCase):
    def test_constructs_one_unit_per_occurrence_with_probe_binding(self) -> None:
        payload = construct_daily_interactions_for_timeline(
            timeline_batch=_timeline_batch(),
            config=DailyInteractionConstructionConfig(include_inactive_days=True),
        )

        self.assertEqual(payload["validation"]["status"], "pass")
        self.assertFalse(payload["construction_scope"]["llm_generation_used"])
        self.assertEqual(payload["summary"]["persona_count"], 1)
        self.assertEqual(payload["summary"]["calendar_day_count"], 4)
        self.assertEqual(payload["summary"]["active_day_total"], 3)
        self.assertEqual(payload["summary"]["interaction_unit_count"], 4)
        self.assertEqual(payload["summary"]["parallel_day_total"], 1)
        self.assertEqual(payload["summary"]["probe_link_count"], 1)

        persona = payload["personas"][0]
        inactive_day = persona["days"][1]
        self.assertFalse(inactive_day["active"])
        self.assertEqual(inactive_day["interaction_units"], [])

        parallel_day = persona["days"][2]
        self.assertTrue(parallel_day["has_parallel_events"])
        self.assertFalse(parallel_day["cross_occurrence_reference_allowed"])
        self.assertEqual(len(parallel_day["interaction_units"]), 2)
        self.assertEqual(
            [unit["event_line_id"] for unit in parallel_day["interaction_units"]],
            ["L_001", "L_002"],
        )

        probed_unit = parallel_day["interaction_units"][0]
        self.assertEqual(probed_unit["interaction_unit_id"], "P0001_D03_M001")
        self.assertEqual(probed_unit["probe_links"][0]["probe_id"], "PRB_001")
        self.assertEqual(
            probed_unit["probe_links"][0]["insert_after_message_id"],
            probed_unit["interaction_unit_id"],
        )
        self.assertIn("PRB_001", persona["message_bindings"])
        self.assertEqual(
            persona["message_bindings"]["PRB_001"]["interaction_unit_id"],
            probed_unit["interaction_unit_id"],
        )

        for unit in _iter_units(persona):
            self.assertTrue(unit["scripted_opening"]["user_message"])
            self.assertTrue(unit["current_state_change_fact"])
            self.assertIn(
                unit["current_state_change_fact"]["fact_id"],
                unit["scene_boundary"]["allowed_fact_ids"],
            )
            self.assertIn(
                "follow-up judgment point",
                unit["scripted_opening"]["user_message"],
            )
            self.assertIn(
                "后续判断点",
                unit["scripted_opening"]["user_message_zh"],
            )
            first_reveal = unit["constrained_followup"]["reveal_steps"][0]
            self.assertIn(
                unit["current_state_change_fact"]["fact_id"],
                first_reveal["may_reveal_fact_ids"],
            )
            self.assertIn(
                f"{unit['interaction_unit_id']}:stage_delta_fact_1",
                first_reveal["may_reveal_fact_ids"],
            )
            self.assertEqual(unit["constrained_followup"]["followup_budget"], 2)
            self.assertTrue(unit["constrained_followup"]["permitted_conversational_moves"])
            self.assertTrue(unit["constrained_followup"]["reveal_steps"])
            self.assertTrue(unit["constrained_followup"]["must_not_introduce"])
            self.assertTrue(unit["scene_boundary"]["allowed_facts"])
            self.assertTrue(unit["scene_boundary"]["latent_concerns"])


def _iter_units(persona: dict) -> list[dict]:
    return [
        unit
        for day in persona["days"]
        for unit in day.get("interaction_units", [])
    ]


def _timeline_batch() -> dict:
    return {
        "schema_version": "timeline_batch_v0.1",
        "sampling_stage": "P1_timeline_construction",
        "timelines": [
            {
                "persona_id": "P0001",
                "persona_ref": {
                    "source_archetype": "A01",
                    "occupation": "property service assistant",
                    "family_structure": "single, rents a room",
                    "primary_life_domains": ["housing", "work"],
                },
                "timeline_days": 4,
                "days": [
                    {
                        "day": 1,
                        "active": True,
                        "day_interaction_unit_id": "P0001_D01",
                        "parallel_event_count": 1,
                        "event_occurrences": [
                            _occurrence(
                                day=1,
                                within_day_index=1,
                                event_line_id="L_001",
                                stage="initial",
                                occurrence_index=1,
                            )
                        ],
                    },
                    {
                        "day": 2,
                        "active": False,
                    },
                    {
                        "day": 3,
                        "active": True,
                        "day_interaction_unit_id": "P0001_D03",
                        "parallel_event_count": 2,
                        "event_occurrences": [
                            _occurrence(
                                day=3,
                                within_day_index=1,
                                event_line_id="L_001",
                                stage="recurrence",
                                occurrence_index=2,
                                probe=True,
                            ),
                            _occurrence(
                                day=3,
                                within_day_index=2,
                                event_line_id="L_002",
                                stage="initial",
                                occurrence_index=1,
                            ),
                        ],
                    },
                    {
                        "day": 4,
                        "active": True,
                        "day_interaction_unit_id": "P0001_D04",
                        "parallel_event_count": 1,
                        "event_occurrences": [
                            _occurrence(
                                day=4,
                                within_day_index=1,
                                event_line_id="L_002",
                                stage="recurrence",
                                occurrence_index=2,
                            )
                        ],
                    },
                ],
            }
        ],
    }


def _occurrence(
    *,
    day: int,
    within_day_index: int,
    event_line_id: str,
    stage: str,
    occurrence_index: int,
    probe: bool = False,
) -> dict:
    unit_id = f"P0001_D{day:02d}_M{within_day_index:03d}"
    occurrence_id = f"P0001_D{day:02d}_E{within_day_index:03d}"
    occurrence = {
        "day": day,
        "active": True,
        "event_occurrence_id": occurrence_id,
        "within_day_index": within_day_index,
        "interaction_unit_id": unit_id,
        "persona_id": "P0001",
        "event_line_id": event_line_id,
        "event_category_id": f"E_{event_line_id}",
        "event_domain": "housing",
        "event_domain_zh": "住房",
        "event_title": {
            "source": f"test event line {event_line_id}",
            "zh": f"测试事件线 {event_line_id}",
        },
        "persistent_event_summary": f"Persistent event summary for {event_line_id}.",
        "persistent_event_summary_zh": f"{event_line_id} 的持续事件摘要。",
        "occurrence_index": occurrence_index,
        "occurrence_count_for_line": 3,
        "stage_index": occurrence_index,
        "event_stage": stage,
        "stage_goal": "Continue the current stage and state the concrete constraint.",
        "stage_goal_zh": "承接当前阶段，说明具体约束。",
        "surface_event": f"This is the day {day} user opening about {event_line_id}.",
        "surface_event_zh": f"这是第 {day} 天关于 {event_line_id} 的用户开场。",
        "assistant_memory_expectation": "Continue prior context and provide one low-risk next step.",
        "assistant_memory_expectation_zh": "需要承接前序并给出低风险下一步。",
        "latent_continuity": "The user wants the assistant not to ask for a full restart.",
        "latent_continuity_zh": "用户希望助手不要让他从头解释。",
        "related_previous_days": [1] if occurrence_index > 1 else [],
        "stage_delta_facts": [
            {
                "source_fields": [f"stage_{stage}"],
                "text": f'Stage {occurrence_index} adds: the new judgment pressure shifts toward "follow-up judgment point {event_line_id}".',
                "text_zh": f"第 {occurrence_index} 阶段新增：新的判断压力转向「后续判断点 {event_line_id}」。",
            }
        ],
        "allowed_new_facts": ["Only one fact from this event line may be added."],
        "allowed_new_facts_zh": ["只能补充这个事件线中的一个事实。"],
        "prohibited_facts": ["Do not introduce a new event outside this test."],
        "prohibited_facts_zh": ["不能引入测试之外的新事件。"],
        "probe_candidate": probe,
        "probe_ids": [],
        "probe_insertions": [],
    }
    if probe:
        occurrence["probe_ids"] = ["PRB_001"]
        occurrence["probe_insertions"] = [
            {
                "probe_id": "PRB_001",
                "probe_type": "memory_invocation",
                "paper_probe_id": "P2",
                "paper_probe_type": "Memory Invocation",
                "paper_probe_zh": "共享记忆调用",
                "evaluation_dimension_ids": ["D4", "D3"],
                "event_occurrence_id": occurrence_id,
                "insert_after_message_id": unit_id,
                "question": "你还记得我前面怎么说过这件事吗？",
            }
        ]
    return occurrence


if __name__ == "__main__":
    unittest.main()
