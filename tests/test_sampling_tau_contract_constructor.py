from __future__ import annotations

import unittest

from long_memory_test.sampling.daily_interaction_constructor import (
    construct_daily_interactions_for_timeline,
)
from long_memory_test.sampling.tau_contract_constructor import (
    construct_tau_contract_for_batch,
)


class SamplingTauContractConstructorTests(unittest.TestCase):
    def test_constructs_tau_contract_with_i_and_probe_bindings(self) -> None:
        timeline = _timeline_batch()
        daily = construct_daily_interactions_for_timeline(timeline_batch=timeline)
        probe_plan = _probe_plan()

        contract = construct_tau_contract_for_batch(
            timeline_batch=timeline,
            daily_interactions=daily,
            probe_plan=probe_plan,
            sampled_personas=_sampled_personas(),
            event_lines_batch=_event_lines_batch(),
            accepted_event_sets=_accepted_event_sets(),
        )

        self.assertEqual(contract["validation"]["status"], "pass")
        self.assertEqual(contract["notation"], "tau=(z,T,L,I,P)")
        self.assertEqual(contract["summary"]["persona_count"], 1)
        self.assertEqual(contract["summary"]["theme_count"], 2)
        self.assertEqual(contract["summary"]["event_line_count"], 2)
        self.assertEqual(contract["summary"]["interaction_unit_count"], 3)
        self.assertEqual(contract["summary"]["targeted_probe_count"], 1)
        self.assertEqual(contract["summary"]["message_binding_count"], 4)
        self.assertEqual(contract["summary"]["probed_interaction_unit_count"], 1)
        self.assertEqual(contract["summary"]["unprobed_interaction_unit_count"], 2)

        probe = contract["P"][0]
        self.assertEqual(probe["probe_id"], "PRB_001")
        self.assertEqual(probe["interaction_unit_id"], "P0001_D03_M001")
        self.assertTrue(probe["read_only"])
        self.assertEqual(probe["writeback_policy"], "probe_turn_must_not_write_to_memory")
        self.assertEqual(probe["ground_truth"]["event_line_id"], "L_p0001_e_work_001")
        self.assertEqual(probe["ground_truth"]["reference_answer_zh"], "接上前序上下文回答。")

        unit_binding = contract["message_bindings"]["P0001_D03_M001"]
        probe_binding = contract["message_bindings"]["PRB_001"]
        self.assertEqual(unit_binding["turn_type"], "scripted_opening")
        self.assertEqual(probe_binding["turn_type"], "targeted_probe")
        self.assertEqual(probe_binding["interaction_unit_id"], "P0001_D03_M001")
        self.assertEqual(probe_binding["event_line_id"], unit_binding["event_line_id"])

    def test_rejects_probe_bound_to_missing_interaction_unit(self) -> None:
        timeline = _timeline_batch()
        daily = construct_daily_interactions_for_timeline(timeline_batch=timeline)
        probe_plan = _probe_plan(insert_after_message_id="P0001_D99_M001")

        contract = construct_tau_contract_for_batch(
            timeline_batch=timeline,
            daily_interactions=daily,
            probe_plan=probe_plan,
            sampled_personas=_sampled_personas(),
            event_lines_batch=_event_lines_batch(),
            accepted_event_sets=_accepted_event_sets(),
        )

        self.assertEqual(contract["validation"]["status"], "fail")
        self.assertTrue(
            any("references missing I" in issue for issue in contract["validation"]["issues"])
        )


def _timeline_batch() -> dict:
    return {
        "schema_version": "timeline_batch_v0.1",
        "sampling_stage": "P1_timeline_construction",
        "validation": {"status": "pass", "issues": [], "warnings": []},
        "timelines": [
            {
                "persona_id": "P0001",
                "persona_ref": {
                    "persona_id": "P0001",
                    "source_archetype": "A01",
                    "occupation": "assistant",
                    "family_structure": "single",
                    "primary_life_domains": ["work", "housing"],
                },
                "timeline_days": 3,
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
                                event_line_id="L_p0001_e_work_001",
                                event_category_id="E_WORK_001",
                                stage="initial",
                                occurrence_index=1,
                            )
                        ],
                    },
                    {"day": 2, "active": False, "event_occurrences": []},
                    {
                        "day": 3,
                        "active": True,
                        "day_interaction_unit_id": "P0001_D03",
                        "parallel_event_count": 2,
                        "event_occurrences": [
                            _occurrence(
                                day=3,
                                within_day_index=1,
                                event_line_id="L_p0001_e_work_001",
                                event_category_id="E_WORK_001",
                                stage="recurrence",
                                occurrence_index=2,
                                probe=True,
                            ),
                            _occurrence(
                                day=3,
                                within_day_index=2,
                                event_line_id="L_p0001_e_home_001",
                                event_category_id="E_HOME_001",
                                stage="initial",
                                occurrence_index=1,
                            ),
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
    event_category_id: str,
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
        "event_category_id": event_category_id,
        "event_domain": "work",
        "event_domain_zh": "工作",
        "event_title": {"zh": f"测试事件 {event_category_id}"},
        "persistent_event_summary": "持续事件摘要。",
        "occurrence_index": occurrence_index,
        "occurrence_count_for_line": 2,
        "stage_index": occurrence_index,
        "event_stage": stage,
        "stage_goal": "承接当前阶段。",
        "surface_event": f"第 {day} 天的用户开场。",
        "assistant_memory_expectation": "承接前序，给出低风险下一步。",
        "latent_continuity": "用户希望助手不要重置上下文。",
        "related_previous_days": [1] if occurrence_index > 1 else [],
        "allowed_new_facts": ["允许事实。"],
        "prohibited_facts": ["禁止新增重大事实。"],
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
                "question": "你接着前面说过的帮我判断。",
            }
        ]
    return occurrence


def _probe_plan(*, insert_after_message_id: str = "P0001_D03_M001") -> dict:
    return {
        "schema_version": "probe_plan_batch_v0.1",
        "sampling_stage": "P2_probe_plan_construction",
        "validation": {"status": "pass", "issues": [], "warnings": []},
        "probe_questions": [
            {
                "probe_id": "PRB_001",
                "message_id": "PRB_001",
                "turn_type": "targeted_probe",
                "persona_id": "P0001",
                "day": 3,
                "event_occurrence_id": "P0001_D03_E001",
                "insert_after_message_id": insert_after_message_id,
                "event_line_id": "L_p0001_e_work_001",
                "event_category_id": "E_WORK_001",
                "event_stage": "recurrence",
                "probe_type": "memory_invocation",
                "paper_probe_id": "P2",
                "paper_probe_type": "Memory Invocation",
                "paper_probe_zh": "共享记忆调用",
                "question": "你接着前面说过的帮我判断。",
                "required_memory_type": ["event_memory", "relational_anchor"],
                "evaluation_dimension_ids": ["D4", "D3"],
                "diagnostic_dimensions": ["shared_context_invocation"],
                "target_detail_ids": ["L_p0001_e_work_001:stage_2"],
                "ground_truth": {
                    "schema_version": "probe_ground_truth_v0.1",
                    "event_line_id": "L_p0001_e_work_001",
                    "expected_references": ["前序上下文"],
                    "reference_answer_zh": "接上前序上下文回答。",
                    "scoring_rubric": {"2": "承接正确"},
                },
                "read_only": True,
                "writeback_policy": "probe_turn_must_not_write_to_memory",
                "tom_assessment": {"probe_focus": "memory_invocation"},
            }
        ],
    }


def _sampled_personas() -> dict:
    return {
        "personas": [
            {
                "persona_id": "P0001",
                "source_archetype": "A01",
                "age_range": "30s",
                "occupation": "assistant",
                "family_structure": "single",
                "primary_life_domains": ["work", "housing"],
                "long_term_goals": ["keep work stable"],
                "communication_style": ["cautious"],
                "stress_response": ["overthinks"],
                "decision_style": ["risk-aware"],
                "memory_relevant_traits": ["prefers concrete next steps"],
                "sensitive_fields": {"gender": "unprovided"},
            }
        ]
    }


def _event_lines_batch() -> dict:
    return {
        "personas": [
            {
                "persona_ref": {"persona_id": "P0001"},
                "event_lines": [
                    _event_line("L_p0001_e_work_001", "E_WORK_001"),
                    _event_line("L_p0001_e_home_001", "E_HOME_001"),
                ],
            }
        ]
    }


def _event_line(event_line_id: str, event_category_id: str) -> dict:
    return {
        "event_line_id": event_line_id,
        "persona_id": "P0001",
        "event_category_id": event_category_id,
        "event_domain": "work",
        "event_domain_zh": "工作",
        "event_title": {"zh": f"测试事件 {event_category_id}"},
        "persistent_event_summary": "持续事件摘要。",
        "relational_memory_targets": [{"target_type": "event_continuity", "target": "承接旧线。"}],
        "stage_sequence": [
            {
                "stage_index": 1,
                "event_stage": "initial",
                "stage_goal": "初始提出。",
                "assistant_memory_expectation": "拆解当前问题。",
            },
            {
                "stage_index": 2,
                "event_stage": "recurrence",
                "stage_goal": "再次出现。",
                "assistant_memory_expectation": "承接前序。",
            },
        ],
    }


def _accepted_event_sets() -> dict:
    return {
        "accepted_persona_event_sets": [
            {
                "persona_id": "P0001",
                "accepted_events": [
                    {
                        "event_category_id": "E_WORK_001",
                        "event_domain": "work",
                        "event_type": "work_issue",
                        "core_issue": "工作事件。",
                    },
                    {
                        "event_category_id": "E_HOME_001",
                        "event_domain": "housing",
                        "event_type": "home_issue",
                        "core_issue": "居住事件。",
                    },
                ],
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
