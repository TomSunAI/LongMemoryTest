from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from long_memory_test.agents.bei_annotator import generate_bei_annotations
from long_memory_test.agents.memory_condition_builder import generate_memory_conditions
from long_memory_test.memory import LDAgentMemoryRuntime, RelationalMemoryRuntime


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts/run_dialogue_conditions.py"
SPEC = importlib.util.spec_from_file_location("run_dialogue_conditions", RUNNER_PATH)
assert SPEC is not None
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


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
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return _FakeCompletion("这是一段用于测试的正常长度回答，可以通过质量门槛。")


class _FakeClient:
    def __init__(self) -> None:
        self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    def with_options(self, **kwargs):
        return self


class DocxRoutePipelineTests(unittest.TestCase):
    def test_generate_bei_annotations_adds_required_memory_and_failure_modes(self) -> None:
        annotations = generate_bei_annotations(
            probe_question_plan={
                "schema_version": "probe_question_plan_v0.1",
                "probe_questions": [
                    {
                        "probe_id": "D10_P001",
                        "message_id": "D10_P001",
                        "day": 10,
                        "topic": "孩子幼儿园可能不稳定",
                        "probe_type": "m2_event_continuity",
                        "user_message": "这条线我不想从头解释了。",
                        "event_refs": ["E001"],
                        "tom_dimensions": [
                            "shared_context_invocation",
                            "relationship_expectation_recognition",
                        ],
                        "tom_assessment": {
                            "hidden_user_need": "用户在测试 AI 是否能恢复共同语境。",
                            "low_score_behavior": "要求用户重讲背景。",
                            "high_score_behavior": "自然接上持续事件线。",
                        },
                    }
                ],
            },
            timeline={
                "events": [
                    {
                        "event_id": "E001",
                        "day": 1,
                        "title": "Kindergarten unstable",
                        "status": "ongoing",
                    }
                ]
            },
        )

        annotation = annotations["annotations"][0]
        self.assertIn("event_memory", annotation["required_memory_type"])
        self.assertIn("relational_anchor", annotation["required_memory_type"])
        self.assertTrue(annotation["failure_mode_expected"])
        self.assertEqual(annotation["emotion"], ["抗拒"])

    def test_memory_conditions_make_m0_ld_agent_memory_and_m2_m3_cumulative(self) -> None:
        bei = generate_bei_annotations(
            probe_question_plan=_probe_doc(),
            timeline=_timeline_doc(),
        )
        conditions = generate_memory_conditions(
            timeline=_timeline_doc(),
            daily_messages=_daily_messages_doc(),
            probe_question_plan=_probe_doc(),
            bei_annotations=bei,
        )

        payloads = conditions["memory_payloads_by_message_id"]["D10_P001"]
        specs = {
            item["condition_id"]: item
            for item in conditions["condition_specs"]
        }
        self.assertIn("LD-Agent memory-only", payloads["M0"]["memory_context"])
        self.assertFalse(payloads["M0"]["requires_runtime_letta"])
        self.assertTrue(payloads["M0"]["requires_runtime_ld_agent_memory"])
        self.assertNotIn("第 10 天", payloads["M0"]["memory_context"])
        self.assertIn("shared_m0_ld_agent_retrieved_payload", specs["M1"]["can_read"])
        self.assertIn("shared_m0_ld_agent_retrieved_payload", specs["M2"]["can_read"])
        self.assertIn("shared_m0_ld_agent_retrieved_payload", specs["M3"]["can_read"])
        self.assertIn("独立 runtime namespace", specs["M1"]["definition"])
        self.assertIn("同轮 M0 检索结果组合", specs["M2"]["definition"])
        self.assertIn("不读取其他关系条件的 payload", specs["M3"]["definition"])
        self.assertIn("结论级关系记忆", payloads["M2"]["memory_context"])
        self.assertIn("摘要级事件记忆", payloads["M2"]["memory_context"])
        self.assertIn("细节级关系锚点", payloads["M3"]["memory_context"])
        self.assertIn("使用边界", payloads["M3"]["memory_context"])
        self.assertNotIn("误用风险", payloads["M3"]["memory_context"])
        self.assertNotIn("- 关系锚点：", payloads["M3"]["memory_context"])

    def test_z_memory_conditions_are_single_feature_payloads(self) -> None:
        conditions = generate_memory_conditions(
            timeline=_timeline_doc(),
            daily_messages=_daily_messages_doc(),
            probe_question_plan=_probe_doc(),
            bei_annotations={},
        )

        payloads = conditions["memory_payloads_by_message_id"]["D10_P001"]
        specs = {item["condition_id"]: item for item in conditions["condition_specs"]}
        self.assertIn("Z1", specs)
        self.assertIn("Z2", specs)
        self.assertIn("Z3", specs)
        self.assertIn("结论级关系记忆", payloads["Z1"]["memory_context"])
        self.assertFalse(payloads["Z1"]["requires_runtime_ld_agent_memory"])
        self.assertIn("摘要级事件记忆", payloads["Z2"]["memory_context"])
        self.assertFalse(payloads["Z2"]["requires_runtime_ld_agent_memory"])
        self.assertNotIn("结论级关系记忆", payloads["Z2"]["memory_context"])
        self.assertIn("细节级关系锚点", payloads["Z3"]["memory_context"])
        self.assertFalse(payloads["Z3"]["requires_runtime_ld_agent_memory"])
        self.assertNotIn("摘要级事件记忆", payloads["Z3"]["memory_context"])

        self.assertEqual(
            runner._resolve_condition_ids(
                "M0,Z1,Z2,Z3",
                {"condition_specs": [{"condition_id": "M0"}]},
            ),
            ["M0", "Z1", "Z2", "Z3"],
        )

    def test_memory_conditions_carry_tau_contract_bindings(self) -> None:
        tau_contract = {
            "schema_version": "tau_construction_contract_v1",
            "notation": "tau=(z,T,L,I,P)",
            "summary": {"bound_message_count": 1},
            "validation": {"status": "pass", "issues": []},
            "message_bindings": {
                "D10_P001": {
                    "persona_id": "user_001",
                    "theme_id": "T_parenting",
                    "event_line_id": "L_kindergarten",
                    "event_stage": "recurrence",
                    "interaction_unit_id": "D10_M001",
                    "probe_ids": ["D10_P001"],
                    "primary_event_id": "E021",
                    "root_event_id": "E001",
                    "related_event_ids": ["E001"],
                    "event_refs": ["E021"],
                }
            },
        }

        conditions = generate_memory_conditions(
            timeline=_timeline_doc(),
            daily_messages=_daily_messages_doc(),
            probe_question_plan=_probe_doc(),
            bei_annotations={},
            tau_contract=tau_contract,
        )

        self.assertTrue(conditions["tau_contract"]["available"])
        payload = conditions["memory_payloads_by_message_id"]["D10_P001"]["M2"]
        self.assertEqual(payload["tau"]["event_line_id"], "L_kindergarten")
        self.assertEqual(
            conditions["summary"]["tau_bound_message_count"],
            1,
        )

    def test_runner_payload_for_relational_conditions_composes_m0_base_memory(self) -> None:
        conditions = generate_memory_conditions(
            timeline=_timeline_doc(),
            daily_messages=_daily_messages_doc(),
            probe_question_plan=_probe_doc(),
            bei_annotations={},
        )

        payload = runner._payload_for_condition(
            conditions,
            "M2",
            _probe_doc()["probe_questions"][0],
            m0_ld_agent_payload={
                "condition_id": "M0",
                "memory_provider": "ld_agent_memory",
                "memory_context": "M0 LD-Agent 普通记忆：应拼入 M2",
                "source_detail_ids": ["m0_source"],
                "storage_backend": "chroma",
                "retrieval": {"strategy": "topic_overlap_time_decay"},
            },
        )

        self.assertIn("摘要级事件记忆", payload["memory_context"])
        self.assertIn("M0 LD-Agent 普通记忆", payload["memory_context"])
        self.assertIn("M0 基石记忆检索结果", payload["memory_context"])
        self.assertLess(
            payload["memory_context"].index("M2 关系记忆增强层"),
            payload["memory_context"].index("M0 基石记忆检索结果"),
        )
        self.assertIn("主记忆：M2 关系记忆增强层", payload["memory_context"])
        self.assertIn("辅助背景：M0 基石记忆检索结果", payload["memory_context"])
        self.assertIn("不要跟随 M0 背景", payload["memory_context"])
        self.assertIn("当前事件感知 overlay", payload["memory_context"])
        self.assertIn("当前用户输入点名主题/事件线时", payload["memory_context"])
        self.assertIn("不得回答 M0 背景或历史短期上下文中的其他事件线", payload["memory_context"])
        self.assertIn("必须回答最后一条当前用户输入", payload["memory_context"])
        self.assertIn("m0_base_memory", payload)
        self.assertIn("m0_source", payload.get("source_detail_ids", []))
        self.assertEqual(payload["memory_composition"]["base_condition"], "M0")
        self.assertEqual(
            payload["memory_composition"]["composition_rule"],
            "m0_base_plus_condition_relational_overlay",
        )
        self.assertTrue(payload["search_indexing_policy"]["uses_m0_search_indexing"])
        self.assertEqual(
            payload["search_indexing_policy"]["m0_retrieval_strategy"],
            "topic_overlap_time_decay",
        )
        self.assertEqual(payload["search_indexing_policy"]["m0_storage_backend"], "chroma")
        self.assertFalse(
            payload["search_indexing_policy"]["relational_layer_has_independent_generic_search"]
        )
        self.assertEqual(
            payload["retrieval"]["strategy"],
            "m0_retrieval_plus_relational_overlay",
        )
        self.assertTrue(payload["retrieval"]["uses_m0_payload"])
        self.assertTrue(payload["memory_composition"]["relational_overlay_precedence"])
        self.assertFalse(payload["memory_composition"]["m0_event_line_filtering"])

    def test_z_payload_is_not_composed_with_m0_base_memory(self) -> None:
        conditions = generate_memory_conditions(
            timeline=_timeline_doc(),
            daily_messages=_daily_messages_doc(),
            probe_question_plan=_probe_doc(),
            bei_annotations={},
        )

        payload = runner._payload_for_condition(
            conditions,
            "Z2",
            _probe_doc()["probe_questions"][0],
            m0_ld_agent_payload={
                "condition_id": "M0",
                "memory_provider": "ld_agent_memory",
                "memory_context": "M0 LD-Agent 普通记忆：不应拼入 Z2",
                "source_detail_ids": ["m0_source"],
                "retrieval": {"strategy": "topic_overlap_time_decay"},
            },
        )

        self.assertIn("摘要级事件记忆", payload["memory_context"])
        self.assertNotIn("M0 LD-Agent 普通记忆", payload["memory_context"])
        self.assertNotIn("M0 基石记忆检索结果", payload["memory_context"])
        self.assertNotIn("m0_base_memory", payload)
        self.assertNotIn("m0_source", payload.get("source_detail_ids", []))
        self.assertFalse(payload["requires_runtime_ld_agent_memory"])
        self.assertEqual(payload["memory_composition"]["base_condition"], None)
        self.assertEqual(
            payload["memory_composition"]["composition_rule"],
            "independent_relational_payload_no_m0_base",
        )
        self.assertFalse(payload["retrieval"]["uses_m0_payload"])
        self.assertFalse(payload["search_indexing_policy"]["uses_m0_search_indexing"])

    def test_relational_payload_uses_empty_m0_base_fallback(self) -> None:
        payload = runner._compose_relational_payload_with_m0_base(
            condition_id="M1",
            m0_ld_agent_payload={
                "condition_id": "M0",
                "memory_provider": "ld_agent_memory",
                "memory_context": "",
                "source_detail_ids": [],
                "retrieval": {},
            },
            relational_overlay={
                "condition_id": "M1",
                "memory_context": "结论级关系记忆：测试",
                "source_detail_ids": [],
            },
            overlay_source="unit_test",
        )

        self.assertIn("结论级关系记忆：测试", payload["memory_context"])
        self.assertIn("当前 M0 runtime 没有检索到可用普通长期记忆", payload["memory_context"])
        self.assertTrue(payload["search_indexing_policy"]["uses_m0_search_indexing"])

    def test_relational_payload_strips_m0_current_session_agent_answers(self) -> None:
        payload = runner._compose_relational_payload_with_m0_base(
            condition_id="M2",
            m0_ld_agent_payload={
                "condition_id": "M0",
                "memory_provider": "ld_agent_memory",
                "memory_context": "\n".join(
                    [
                        "[Available M0 Memory: LD-Agent-style Session-Summary Memory]",
                        "",
                        "Current short-term session:",
                        "- (line 1) User: 当前用户问题 | Assistant(M0): M0 上一轮错误回答",
                        "",
                        "Retrieved session snippets:",
                        "   - (line 1) User: 长期片段 | Assistant(M0): 长期 M0 回答",
                        "",
                        "Retrieved session summaries:",
                        "1. Long-term summary can remain.",
                    ]
                ),
                "source_detail_ids": [],
                "retrieval": {},
            },
            relational_overlay={
                "condition_id": "M2",
                "memory_context": "摘要级关系记忆：测试",
                "source_detail_ids": [],
            },
            overlay_source="unit_test",
        )

        self.assertIn("- (line 1) User: 当前用户问题", payload["memory_context"])
        self.assertNotIn("M0 上一轮错误回答", payload["memory_context"])
        self.assertIn("   - (line 1) User: 长期片段", payload["memory_context"])
        self.assertNotIn("长期 M0 回答", payload["memory_context"])
        self.assertTrue(
            payload["memory_composition"]["m0_current_session_agent_answers_removed"]
        )

    def test_runner_prompt_blinds_condition_labels(self) -> None:
        prompt = runner._build_condition_system_prompt(
            condition_id="M0",
            condition_spec={
                "name": "Generic Agent Memory Baseline",
                "definition": "普通长短期记忆强基线",
                "can_read": ["generic_conversation_summary"],
                "cannot_read": ["bei_annotations"],
            },
            memory_payload={"memory_context": "普通 agent 记忆摘要：测试"},
        )

        self.assertIn("普通 agent 记忆摘要：测试", prompt)
        self.assertNotIn("当前条件", prompt)
        self.assertNotIn("M0 是", prompt)
        self.assertNotIn("bei_annotations", prompt)
        self.assertNotIn("本轮主记忆", prompt)
        self.assertNotIn("关系记忆增强层", prompt)
        self.assertNotIn("M0 只是普通 session/day 背景", prompt)
        self.assertNotIn("不要跟随 M0 背景", prompt)
        self.assertNotIn("当前用户输入是本轮唯一需要回答的问题", prompt)
        self.assertNotIn("本轮必须只围绕该主题/事件线回答", prompt)
        self.assertNotIn("不得替代当前用户点名的事件线", prompt)

    def test_runner_prompt_prioritizes_relational_overlay_for_relational_conditions(self) -> None:
        prompt = runner._build_condition_system_prompt(
            condition_id="M2",
            condition_spec={
                "name": "Summary-level Relational Memory",
                "definition": "普通记忆加摘要级关系记忆",
            },
            memory_payload={"memory_context": "M2 关系记忆增强层：测试\nM0 基石记忆检索结果：测试"},
        )

        self.assertIn("本轮主记忆是 M2 关系记忆增强层", prompt)
        self.assertIn("M0 只是普通 session/day 背景", prompt)
        self.assertIn("若二者冲突，不要跟随 M0 背景", prompt)
        self.assertIn("当前用户输入是本轮唯一需要回答的问题", prompt)
        self.assertIn("本轮必须只围绕该主题/事件线回答", prompt)
        self.assertIn("不得替代当前用户点名的事件线", prompt)
        self.assertLess(
            prompt.index("本轮主记忆是 M2 关系记忆增强层"),
            prompt.index("本轮你只能使用下面这段可用长期记忆载荷"),
        )

    def test_runner_rebuild_runtime_state_handles_four_conditions(self) -> None:
        turns = [
            {
                "turn_index": 1,
                "source": {"message_id": "D01_M001"},
                "input": {"user_message": "测试"},
                "variants": {
                    condition: {"assistant_answer": f"{condition}回答"}
                    for condition in ["M0", "M1", "M2", "M3"]
                },
            }
        ]

        histories, transcript_ids, completed = runner._rebuild_runtime_state(
            turns,
            condition_ids=["M0", "M1", "M2", "M3"],
        )

        self.assertEqual(transcript_ids, ["D01_M001"])
        self.assertEqual(histories["M3"], [{"role": "user", "content": "测试"}])
        self.assertIn("D01_M001", completed)

    def test_runner_ask_condition_sends_temperature_and_memory_payload(self) -> None:
        client = _FakeClient()
        answer = runner._ask_a_condition(
            client=client,
            model="test-model",
            condition_id="M2",
            condition_spec={
                "name": "Summary-level Relational Memory",
                "definition": "M1 + 摘要级记忆",
                "can_read": ["M1_conclusion_memory"],
                "cannot_read": ["bei_annotations"],
            },
            user_message="测试用户消息",
            memory_payload={"memory_context": "摘要级事件记忆：测试"},
            short_term_history=[],
            timeout=1,
            max_tokens=100,
            temperature=0.2,
            top_p=0.7,
        )

        self.assertEqual(answer, "这是一段用于测试的正常长度回答，可以通过质量门槛。")
        request = client.chat.completions.requests[0]
        self.assertEqual(request["temperature"], 0.2)
        self.assertEqual(request["top_p"], 0.7)
        self.assertIn("摘要级事件记忆：测试", request["messages"][0]["content"])

    def test_runner_records_m0_turn_in_ld_agent_memory_runtime(self) -> None:
        client = _FakeClient()
        memory_runtime = LDAgentMemoryRuntime()
        turn = runner._run_condition_turn(
            run_id="run-test",
            created_at="2026-06-05T00:00:00Z",
            turn_index=1,
            daily_messages_path=Path("daily.json"),
            scene_cards_path=None,
            memory_conditions_path=Path("memory.json"),
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "turn_type": "scripted_opening",
                "user_message": "我今天又在想幼儿园这件事。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            scene_card=None,
            llm_client=client,
            llm_config=types.SimpleNamespace(provider="fake", base_url="fake", model="fake-model"),
            max_tokens=100,
            temperature=0.2,
            top_p=1.0,
            timeout_seconds=1,
            condition_workers=1,
            print_condition_progress=False,
            memory_conditions={
                "condition_specs": [
                    {
                        "condition_id": "M0",
                        "definition": "LD-Agent memory baseline",
                    }
                ]
            },
            m0_memory_runtime=memory_runtime,
            condition_ids=["M0"],
            short_term_histories={"M0": []},
            previous_message_ids=[],
        )

        self.assertEqual(len(memory_runtime.short_term_session), 1)
        self.assertEqual(memory_runtime.short_term_session[0]["message_id"], "D01_M001")
        self.assertIn("我今天又在想幼儿园这件事。", memory_runtime.short_term_session[0]["user_message"])
        self.assertEqual(turn["memory_actions"][0]["status"], "success")
        self.assertEqual(
            turn["variants"]["M0"]["memory_writeback"]["action"],
            "append_short_term_session",
        )

    def test_runner_records_relational_turns_in_independent_runtimes(self) -> None:
        client = _FakeClient()
        m0_runtime = LDAgentMemoryRuntime()
        m2_runtime = RelationalMemoryRuntime(condition_id="M2")
        turn = runner._run_condition_turn(
            run_id="run-test",
            created_at="2026-06-05T00:00:00Z",
            turn_index=1,
            daily_messages_path=Path("daily.json"),
            scene_cards_path=None,
            memory_conditions_path=Path("memory.json"),
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "turn_type": "scripted_opening",
                "user_message": "我今天又在想幼儿园这件事。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            scene_card=None,
            llm_client=client,
            llm_config=types.SimpleNamespace(provider="fake", base_url="fake", model="fake-model"),
            max_tokens=100,
            temperature=0.2,
            top_p=1.0,
            timeout_seconds=1,
            condition_workers=1,
            print_condition_progress=False,
            memory_conditions={
                "condition_specs": [
                    {"condition_id": "M0", "definition": "LD-Agent memory baseline"},
                    {"condition_id": "M2", "definition": "M2 independent runtime"},
                ],
                "default_payloads": {
                    "M2": {
                        "condition_id": "M2",
                        "memory_context": "静态 payload 不应该被 runtime 路径使用",
                    }
                },
            },
            m0_memory_runtime=m0_runtime,
            relational_memory_runtimes={"M2": m2_runtime},
            condition_ids=["M0", "M2"],
            short_term_histories={"M0": [], "M2": []},
            previous_message_ids=[],
        )

        self.assertEqual(m2_runtime.snapshot()["memory_count"], 2)
        self.assertIn("L_kindergarten", m2_runtime.snapshot()["event_line_memory_index"])
        self.assertEqual(
            turn["variants"]["M2"]["memory_payload"]["memory_provider"],
            "m0_base_plus_relational_overlay",
        )
        self.assertEqual(
            turn["variants"]["M2"]["memory_payload"]["relational_overlay"]["memory_provider"],
            "independent_relational_memory_runtime",
        )
        self.assertTrue(
            turn["variants"]["M2"]["memory_payload"]["retrieval"]["uses_m0_payload"]
        )
        self.assertEqual(
            turn["variants"]["M2"]["memory_payload"]["memory_composition"]["base_condition"],
            "M0",
        )
        self.assertNotIn(
            "静态 payload 不应该被 runtime 路径使用",
            turn["variants"]["M2"]["memory_payload"]["memory_context"],
        )
        self.assertEqual(
            turn["variants"]["M2"]["memory_writeback"]["action"],
            "upsert_relational_memories",
        )
        self.assertIn(
            "M2",
            turn["memory_setup"]["relational_runtime_conditions"],
        )
        self.assertTrue(turn["memory_setup"]["m1_m2_m3_share_m0_base_memory"])

    def test_runner_records_z_turn_without_m0_base_or_writeback(self) -> None:
        client = _FakeClient()
        m0_runtime = LDAgentMemoryRuntime()
        z2_runtime = RelationalMemoryRuntime(condition_id="Z2")
        turn = runner._run_condition_turn(
            run_id="run-test",
            created_at="2026-06-05T00:00:00Z",
            turn_index=1,
            daily_messages_path=Path("daily.json"),
            scene_cards_path=None,
            memory_conditions_path=Path("memory.json"),
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "turn_type": "scripted_opening",
                "user_message": "我今天又在想幼儿园这件事。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            scene_card=None,
            llm_client=client,
            llm_config=types.SimpleNamespace(provider="fake", base_url="fake", model="fake-model"),
            max_tokens=100,
            temperature=0.2,
            top_p=1.0,
            timeout_seconds=1,
            condition_workers=1,
            print_condition_progress=False,
            memory_conditions={
                "condition_specs": [
                    {"condition_id": "Z2", "definition": "Z2 independent runtime"},
                ],
            },
            m0_memory_runtime=m0_runtime,
            relational_memory_runtimes={"Z2": z2_runtime},
            condition_ids=["Z2"],
            short_term_histories={"Z2": []},
            previous_message_ids=[],
        )

        payload = turn["variants"]["Z2"]["memory_payload"]
        self.assertEqual(z2_runtime.snapshot()["memory_count"], 1)
        self.assertEqual(len(m0_runtime.actions), 0)
        self.assertEqual(turn["memory_actions"], [turn["variants"]["Z2"]["memory_writeback"]])
        self.assertNotIn("m0_base_memory", payload)
        self.assertFalse(payload["requires_runtime_ld_agent_memory"])
        self.assertFalse(payload["retrieval"]["uses_m0_payload"])
        self.assertEqual(
            payload["memory_composition"]["composition_rule"],
            "independent_relational_payload_no_m0_base",
        )
        self.assertFalse(turn["memory_setup"]["m1_m2_m3_share_m0_base_memory"])
        self.assertFalse(turn["memory_setup"]["relational_conditions_share_m0_base_memory"])
        self.assertFalse(turn["memory_setup"]["z1_z2_z3_use_m0_base_memory"])

    def test_run_config_records_m1_m2_m3_share_m0_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = {
                "run_id": "test_run",
                "created_at": "2026-06-27T00:00:00",
                "expected_turns": 1,
                "tau_contract": {},
                "m0_ld_agent_memory": {
                    "ld_agent_reference": "ld_agent://test",
                },
            }
            args = types.SimpleNamespace(
                temperature=0.2,
                top_p=1.0,
                llm_timeout=60,
                condition_workers=1,
                daily_messages=temp_path / "daily.json",
                scene_cards=temp_path / "scene.json",
                probe_questions=temp_path / "probe.json",
                memory_conditions=temp_path / "memory.json",
                relational_memory_top_k=5,
                m0_ld_agent_top_k=6,
                m0_ld_agent_short_term_k=3,
                m0_ld_agent_storage_backend="json",
                m0_ld_agent_chroma_path=None,
                scene_followups=False,
                output=temp_path / "responses_by_condition.json",
                conversation_log=temp_path / "conversation_log.json",
            )
            llm_config = types.SimpleNamespace(
                provider="deepseek",
                base_url="https://api.deepseek.com",
                model="deepseek-v4-pro",
            )

            runner._write_run_config(
                temp_path / "run_config.json",
                result=result,
                args=args,
                llm_config=llm_config,
                max_tokens=1200,
                condition_ids=["M0", "M1", "M2", "M3"],
            )

            self.assertTrue(
                result["run_config"]["controlled_variables"][
                    "m1_m2_m3_share_m0_base_memory"
                ]
            )
            self.assertTrue(
                result["run_config"]["relational_memory_runtimes"]["uses_m0_payload"]
            )
            self.assertEqual(
                result["run_config"]["relational_memory_runtimes"][
                    "uses_m0_payload_by_condition"
                ],
                {"M1": True, "M2": True, "M3": True},
            )

    def test_run_config_records_z_conditions_without_m0_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result = {
                "run_id": "test_run",
                "created_at": "2026-06-27T00:00:00",
                "expected_turns": 1,
                "tau_contract": {},
                "m0_ld_agent_memory": {
                    "ld_agent_reference": "ld_agent://test",
                },
            }
            args = types.SimpleNamespace(
                temperature=0.2,
                top_p=1.0,
                llm_timeout=60,
                condition_workers=1,
                daily_messages=temp_path / "daily.json",
                scene_cards=temp_path / "scene.json",
                probe_questions=temp_path / "probe.json",
                memory_conditions=temp_path / "memory.json",
                relational_memory_top_k=5,
                m0_ld_agent_top_k=6,
                m0_ld_agent_short_term_k=3,
                m0_ld_agent_storage_backend="json",
                m0_ld_agent_chroma_path=None,
                scene_followups=False,
                output=temp_path / "responses_by_condition.json",
                conversation_log=temp_path / "conversation_log.json",
            )
            llm_config = types.SimpleNamespace(
                provider="deepseek",
                base_url="https://api.deepseek.com",
                model="deepseek-v4-pro",
            )

            runner._write_run_config(
                temp_path / "run_config.json",
                result=result,
                args=args,
                llm_config=llm_config,
                max_tokens=1200,
                condition_ids=["Z1", "Z2", "Z3"],
            )

            self.assertFalse(
                result["run_config"]["controlled_variables"][
                    "m1_m2_m3_share_m0_base_memory"
                ]
            )
            self.assertFalse(
                result["run_config"]["controlled_variables"][
                    "relational_conditions_share_m0_base_memory"
                ]
            )
            self.assertFalse(
                result["run_config"]["controlled_variables"][
                    "z1_z2_z3_use_m0_base_memory"
                ]
            )
            self.assertFalse(
                result["run_config"]["relational_memory_runtimes"]["uses_m0_payload"]
            )
            self.assertEqual(
                result["run_config"]["relational_memory_runtimes"][
                    "uses_m0_payload_by_condition"
                ],
                {"Z1": False, "Z2": False, "Z3": False},
            )
            self.assertEqual(
                result["run_config"]["m0_ld_agent_memory_baseline"]["used_by_conditions"],
                [],
            )


def _timeline_doc() -> dict:
    return {
        "events": [
            {
                "event_id": "E021",
                "day": 10,
                "title": "Kindergarten line recurs",
                "status": "ongoing",
                "memory_detail_anchors": [
                    {
                        "detail_id": "E021:kindergarten_information_vague",
                        "min_memory_level": "M2",
                        "text": "幼儿园不稳定的消息仍然模糊。",
                    },
                    {
                        "detail_id": "E021:child_stability_not_school_choice",
                        "min_memory_level": "M3",
                        "text": "用户真正担心的是孩子被现实变动反复折腾。",
                        "expected_response_mode": (
                            "接住孩子稳定感，而不是只给换园清单。"
                        ),
                    },
                ],
            }
        ]
    }


def _daily_messages_doc() -> dict:
    return {
        "messages": [
            {
                "message_id": "D10_M001",
                "day": 10,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这条线又绕回来了。",
            }
        ]
    }


def _probe_doc() -> dict:
    return {
        "probe_questions": [
            {
                "probe_id": "D10_P001",
                "message_id": "D10_P001",
                "day": 10,
                "topic": "孩子幼儿园可能不稳定",
                "probe_type": "m2_event_continuity",
                "event_refs": ["E021"],
                "target_detail_ids": ["E021:child_stability_not_school_choice"],
                "user_message": "这条线我不想从头解释了。",
                "tom_dimensions": ["shared_context_invocation"],
                "tom_assessment": {
                    "hidden_user_need": "用户在测试 AI 是否能恢复共同语境。",
                    "low_score_behavior": "要求用户重讲背景。",
                    "high_score_behavior": "自然接上持续事件线。",
                },
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
