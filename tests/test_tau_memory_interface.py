from __future__ import annotations

import json
import types
import unittest

from long_memory_test.agents.memory_condition_builder import (
    generate_memory_conditions_from_tau_contract,
)
from long_memory_test.agents.tau_dialogue_adapter import build_tau_dialogue_documents
from long_memory_test.sampling.interaction_naturalizer import (
    InteractionNaturalizationConfig,
    attach_naturalized_dialogues,
    build_naturalization_prompt,
    naturalize_interaction_unit,
    validate_naturalized_dialogue,
)


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
    def __init__(self, output: dict) -> None:
        self.output = output
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return _FakeCompletion(json.dumps(self.output, ensure_ascii=False))


class _FakeClient:
    def __init__(self, output: dict) -> None:
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(output))


class TauMemoryInterfaceTests(unittest.TestCase):
    def test_tau_contract_builds_m0_m3_payloads_for_all_bindings(self) -> None:
        tau = _tau_contract()

        memory_conditions = generate_memory_conditions_from_tau_contract(tau_contract=tau)

        self.assertEqual(memory_conditions["schema_version"], "memory_conditions_v0.2_tau_route")
        self.assertEqual(memory_conditions["summary"]["message_payload_count"], 2)
        self.assertEqual(memory_conditions["summary"]["tau_bound_message_count"], 2)
        opening_payloads = memory_conditions["memory_payloads_by_message_id"]["P0001_D01_M001"]
        probe_payloads = memory_conditions["memory_payloads_by_message_id"]["P0001_D02_P001"]
        self.assertIn("结论级关系记忆", opening_payloads["M1"]["memory_context"])
        self.assertIn("事件线：幼儿园适应", opening_payloads["M2"]["memory_context"])
        self.assertIn("可用事实", opening_payloads["M3"]["memory_context"])
        self.assertEqual(probe_payloads["M0"]["tau"]["event_line_id"], "L001")
        self.assertIn("L001:target_detail", probe_payloads["M3"]["source_detail_ids"])

    def test_tau_dialogue_adapter_preserves_i_unit_and_groups_probes(self) -> None:
        tau = _tau_contract()
        naturalized = {
            "naturalized_dialogues": [
                {
                    "naturalized_dialogue_id": "P0001_D01_M001_NAT001",
                    "source_interaction_unit_id": "P0001_D01_M001",
                    "opening_user_message": "我还是想从幼儿园适应这件事开始说，你帮我抓重点。",
                }
            ]
        }

        docs = build_tau_dialogue_documents(
            tau_contract=tau,
            naturalized_dialogues=naturalized,
        )

        self.assertEqual(docs["summary"]["message_count"], 1)
        self.assertEqual(docs["summary"]["probe_count"], 1)
        message = docs["messages"][0]
        self.assertTrue(message["naturalized_dialogue_used"])
        self.assertIn("canonical_user_message", message)
        self.assertEqual(message["interaction_unit_id"], "P0001_D01_M001")
        self.assertEqual(
            docs["probe_questions_by_insert_after"]["P0001_D01_M001"][0]["message_id"],
            "P0001_D02_P001",
        )

    def test_interaction_naturalizer_outputs_candidate_without_overwriting_i_unit(self) -> None:
        unit = _interaction_unit()
        client = _FakeClient(
            {
                "source_interaction_unit_id": "P0001_D01_M001",
                "opening_user_message": "我又有点卡在幼儿园适应这件事上，想先把最要紧的点拎出来。",
                "followup_user_messages": ["主要是我不知道要不要现在就和老师沟通。"],
                "fact_ids_used": ["P0001_D01_M001:event_title"],
                "notes": "只改写表达，没有新增事实。",
            }
        )

        prompt = build_naturalization_prompt(
            interaction_unit=unit,
            bound_probes=[
                {
                    "probe_id": "P0001_D01_P001",
                    "paper_probe_id": "P3",
                    "paper_probe_zh": "共享记忆调用",
                    "primary_dimension_id": "D4",
                    "question": "这条线我不想从头解释了，你接上说。",
                    "tom_assessment": {"hidden_user_need": "用户希望助手承接前文。"},
                    "ground_truth": {
                        "expected_references": ["前序上下文"],
                        "failure_modes": ["要求用户重讲背景"],
                    },
                }
            ],
        )
        self.assertIn("canonical I unit", prompt[1]["content"])
        self.assertIn("current_state_change_fact", prompt[1]["content"])
        self.assertIn("需要判断是否要和老师沟通", prompt[1]["content"])
        self.assertIn("bound_probe_followup_guidance", prompt[1]["content"])
        self.assertIn("只能用于 followup_user_messages", prompt[1]["content"])
        candidate = naturalize_interaction_unit(
            interaction_unit=unit,
            client=client,
            model="fake-model",
            bound_probes=[
                {
                    "probe_id": "P0001_D01_P001",
                    "paper_probe_id": "P3",
                    "primary_dimension_id": "D4",
                    "question": "这条线我不想从头解释了，你接上说。",
                }
            ],
            config=InteractionNaturalizationConfig(max_followups=2),
        )

        self.assertEqual(candidate["validation"]["status"], "pass")
        self.assertEqual(candidate["bound_probe_ids"], ["P0001_D01_P001"])
        self.assertTrue(candidate["non_destructive_policy"]["canonical_i_unit_preserved"])
        self.assertNotEqual(
            candidate["opening_user_message"],
            unit["scripted_opening"]["user_message"],
        )
        attached = attach_naturalized_dialogues(
            daily_interactions={
                "personas": [
                    {
                        "persona_id": "P0001",
                        "days": [{"day": 1, "interaction_units": [unit]}],
                    }
                ]
            },
            naturalized_dialogues={"P0001_D01_M001": candidate},
        )
        attached_unit = attached["personas"][0]["days"][0]["interaction_units"][0]
        self.assertEqual(
            attached_unit["scripted_opening"]["user_message"],
            unit["scripted_opening"]["user_message"],
        )
        self.assertIn("naturalized_dialogue_candidate", attached_unit)

    def test_interaction_naturalizer_rejects_out_of_boundary_fact_ids(self) -> None:
        validation = validate_naturalized_dialogue(
            interaction_unit=_interaction_unit(),
            naturalized_dialogue={
                "source_interaction_unit_id": "P0001_D01_M001",
                "opening_user_message": "我想继续说幼儿园适应。",
                "followup_user_messages": [],
                "fact_ids_used": ["outside_fact"],
            },
        )

        self.assertEqual(validation["status"], "fail")
        self.assertIn("outside scene_boundary", validation["issues"][0])

    def test_interaction_naturalizer_accepts_scene_boundary_latent_concern_ids(self) -> None:
        validation = validate_naturalized_dialogue(
            interaction_unit=_interaction_unit(),
            naturalized_dialogue={
                "source_interaction_unit_id": "P0001_D01_M001",
                "opening_user_message": "我想继续说幼儿园适应。",
                "followup_user_messages": [],
                "fact_ids_used": ["P0001_D01_M001:latent_stage_goal"],
            },
        )

        self.assertEqual(validation["status"], "pass")

    def test_interaction_naturalizer_rejects_probe_question_copied_as_opening(self) -> None:
        validation = validate_naturalized_dialogue(
            interaction_unit=_interaction_unit(),
            naturalized_dialogue={
                "source_interaction_unit_id": "P0001_D01_M001",
                "opening_user_message": "这条线我不想从头解释了，你接上说。",
                "followup_user_messages": [],
                "fact_ids_used": [],
                "bound_probe_refs": [
                    {"question": "这条线我不想从头解释了，你接上说。"}
                ],
            },
        )

        self.assertEqual(validation["status"], "fail")
        self.assertIn("formal probe question", " ".join(validation["issues"]))


def _tau_contract() -> dict:
    unit = _interaction_unit()
    return {
        "schema_version": "tau_contract_batch_v0.1",
        "notation": "tau=(z,T,L,I,P)",
        "validation": {"status": "pass", "issues": []},
        "message_bindings": {
            "P0001_D01_M001": {
                "schema_version": "tau_binding_batch_v0.1",
                "message_id": "P0001_D01_M001",
                "turn_type": "scripted_opening",
                "persona_id": "P0001",
                "theme_id": "T001",
                "event_line_id": "L001",
                "interaction_unit_id": "P0001_D01_M001",
                "event_occurrence_id": "E001",
                "day": 1,
                "event_stage": "initial",
            },
            "P0001_D02_P001": {
                "schema_version": "tau_binding_batch_v0.1",
                "message_id": "P0001_D02_P001",
                "turn_type": "targeted_probe",
                "persona_id": "P0001",
                "theme_id": "T001",
                "event_line_id": "L001",
                "interaction_unit_id": "P0001_D01_M001",
                "event_occurrence_id": "E001",
                "day": 2,
                "event_stage": "recurrence",
            },
        },
        "L": [
            {
                "event_line_id": "L001",
                "theme_id": "T001",
                "persona_id": "P0001",
                "event_title": {"zh": "幼儿园适应"},
                "persistent_event_summary": "孩子刚入园，用户担心适应波动。",
                "relational_memory_targets": [
                    {"target_type": "response_preference", "target": "先拆事实和低风险下一步。"}
                ],
                "observed_stage_sequence": [
                    {
                        "day": 1,
                        "event_stage": "initial",
                        "occurrence_index": 1,
                        "assistant_memory_expectation": "先拆事实。",
                    }
                ],
            }
        ],
        "I": [unit],
        "P": [
            {
                "probe_id": "P0001_D02_P001",
                "message_id": "P0001_D02_P001",
                "turn_type": "targeted_probe",
                "persona_id": "P0001",
                "day": 2,
                "day_group_id": "P0001_D02",
                "interaction_unit_id": "P0001_D01_M001",
                "event_occurrence_id": "E001",
                "event_line_id": "L001",
                "event_stage": "recurrence",
                "question": "这条线我不想从头解释了，你接上说。",
                "target_detail_ids": ["L001:target_detail"],
                "evaluation_dimension_ids": ["D4"],
                "diagnostic_dimensions": ["shared_context_invocation"],
                "tom_assessment": {"hidden_user_need": "测试连续性。"},
            }
        ],
    }


def _interaction_unit() -> dict:
    return {
        "interaction_unit_id": "P0001_D01_M001",
        "event_occurrence_id": "E001",
        "persona_id": "P0001",
        "day": 1,
        "day_group_id": "P0001_D01",
        "within_day_index": 1,
        "event_line_id": "L001",
        "event_title": {"zh": "幼儿园适应"},
        "event_stage": "initial",
        "occurrence_index": 1,
        "current_state_change_fact": {
            "fact_id": "P0001_D01_M001:current_state_change_fact",
            "type": "current_state_change_fact",
            "text": "第 1 阶段新增：用户第一次把「幼儿园适应」说清楚，首要不确定点是「需要判断是否要和老师沟通」。",
            "source": "event_line_stage_delta",
            "source_fields": ["possible_uncertainties[0]"],
            "supporting_fact_ids": ["P0001_D01_M001:stage_delta_fact_1"],
        },
        "scripted_opening": {
            "message_id": "P0001_D01_M001",
            "turn_type": "scripted_opening",
            "user_message": "我最近卡在「幼儿园适应」这件事上，你先帮我拆一下。",
            "topic": "幼儿园适应",
            "conversation_goal": "第一次提出担心。",
            "current_state_change_fact_id": "P0001_D01_M001:current_state_change_fact",
        },
        "constrained_followup": {
            "followup_budget": 2,
            "permitted_conversational_moves": [
                {"move_id": "clarify_current_constraint", "description": "补充当前约束。"}
            ],
            "reveal_steps": [
                {
                    "followup_index": 1,
                    "may_reveal_fact_ids": ["P0001_D01_M001:event_title"],
                    "instruction": "最多补充一个事实。",
                }
            ],
            "must_not_introduce": ["不能新增家庭成员。"],
            "stop_conditions": ["达到预算即停止。"],
        },
        "scene_boundary": {
            "allowed_facts": [
                {
                    "fact_id": "P0001_D01_M001:current_state_change_fact",
                    "type": "current_state_change_fact",
                    "text": "第 1 阶段新增：用户第一次把「幼儿园适应」说清楚，首要不确定点是「需要判断是否要和老师沟通」。",
                    "source": "event_line_stage_delta",
                },
                {
                    "fact_id": "P0001_D01_M001:event_title",
                    "type": "event_title",
                    "text": "幼儿园适应",
                    "source": "timeline_occurrence",
                },
                {
                    "fact_id": "P0001_D01_M001:stage_delta_fact_1",
                    "type": "stage_delta_fact",
                    "text": "第 1 阶段新增：用户第一次把「幼儿园适应」说清楚，首要不确定点是「需要判断是否要和老师沟通」。",
                    "source": "event_line_stage_delta",
                }
            ],
            "allowed_fact_ids": [
                "P0001_D01_M001:current_state_change_fact",
                "P0001_D01_M001:event_title",
                "P0001_D01_M001:stage_delta_fact_1",
            ],
            "latent_concerns": [
                {
                    "concern_id": "P0001_D01_M001:latent_stage_goal",
                    "text": "用户想先拆事实。",
                }
            ],
        },
        "source_timeline_fields": {
            "current_state_change_fact": {
                "fact_id": "P0001_D01_M001:current_state_change_fact",
                "type": "current_state_change_fact",
                "text": "第 1 阶段新增：用户第一次把「幼儿园适应」说清楚，首要不确定点是「需要判断是否要和老师沟通」。",
                "source": "event_line_stage_delta",
            },
            "prohibited_facts": ["不能新增家庭成员。"],
        },
    }


if __name__ == "__main__":
    unittest.main()
