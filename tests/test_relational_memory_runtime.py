from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from long_memory_test.memory import RelationalMemoryRuntime


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeRelationalCompletions:
    def __init__(self, response_style: str = "json") -> None:
        self.requests = []
        self.response_style = response_style

    def create(self, **kwargs):
        self.requests.append(kwargs)
        prompt = kwargs["messages"][-1]["content"]
        if "relationship_conclusion_memory" in prompt:
            summary = "LLM结论：用户在这条事件线上需要具体承接和少泛化回应。"
        elif "event_line_summary_memory" in prompt:
            summary = "LLM事件摘要：这条事件线从初始担心推进到需要重新判断下一步。"
        elif "detail_anchor_memory" in prompt:
            summary = "LLM细节锚点：可复用线索是用户提到的老师反馈和继续观察边界。"
        else:
            summary = "LLM记忆摘要。"
        content = json.dumps(
            {
                "summary": summary,
                "fact_basis": ["fact_layer.current_user_message"],
                "answer_observation": "本轮回答只作为表现观察，不作为事件事实。",
                "answer_misuse_risk": "不要把 assistant 回答文本写成用户事实。",
                "evidence_turn_ids": ["P0001_D01_M001"],
                "update_type": "update",
                "use_boundary": "只在同一事件线相关时使用。",
                "misuse_risk": "不要扩展成未说出的事实。",
            },
            ensure_ascii=False,
        )
        if self.response_style == "wrapped_fence":
            content = f"已完成本层记忆更新：\n```json\n{content}\n```\n请使用 JSON 内容。"
        return _FakeCompletion(content)


class _FakeRelationalClient:
    def __init__(self, response_style: str = "json") -> None:
        self.chat = types.SimpleNamespace(
            completions=_FakeRelationalCompletions(response_style=response_style)
        )

    def with_options(self, **kwargs):
        return self


class RelationalMemoryRuntimeTests(unittest.TestCase):
    def test_llm_consolidation_writes_relational_memory_layers(self) -> None:
        client = _FakeRelationalClient()
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = RelationalMemoryRuntime(
                condition_id="M3",
                storage_root=Path(tmpdir) / "M3",
                llm_client=client,
                llm_model="fake-model",
            )
            runtime.record_completed_turn(
                message={
                    "message_id": "P0001_D01_M001",
                    "day": 1,
                    "topic": "幼儿园适应",
                    "user_message": "我第一次说清楚幼儿园适应这条线，先判断要不要找老师。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "initial",
                    },
                },
                assistant_answer="先确认老师反馈，再决定是否继续观察。",
                run_id="run-test",
            )

            snapshot = runtime.snapshot()
            self.assertEqual(snapshot["summary_writer"], "llm")
            self.assertEqual(snapshot["memory_llm_failure_count"], 0)
            self.assertEqual(len(client.chat.completions.requests), 3)
            summaries = [item["summary"] for item in snapshot["memories"]]
            self.assertIn(
                "LLM结论：用户在这条事件线上需要具体承接和少泛化回应。",
                summaries,
            )
            self.assertIn(
                "LLM事件摘要：这条事件线从初始担心推进到需要重新判断下一步。",
                summaries,
            )
            self.assertIn(
                "LLM细节锚点：可复用线索是用户提到的老师反馈和继续观察边界。",
                summaries,
            )
            for memory in snapshot["memories"]:
                self.assertEqual(memory["ld_agent_metadata"]["summary_writer"], "llm")
                self.assertEqual(
                    memory["ld_agent_metadata"]["llm_consolidation"]["writer"],
                    "llm",
                )

            event_line_dir = Path(tmpdir) / "M3" / "event_lines"
            index = json.loads((event_line_dir / "index.json").read_text(encoding="utf-8"))
            payload = json.loads(
                (event_line_dir / index["event_lines"][0]["filename"]).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                payload["auto_event_line_summary"]["summary_mode"],
                "llm_event_line_memory_consolidation_rollup",
            )
            self.assertEqual(payload["layers"]["m1_conclusion"]["summary_writer"], "llm")

    def test_llm_consolidation_accepts_wrapped_json_response(self) -> None:
        client = _FakeRelationalClient(response_style="wrapped_fence")
        runtime = RelationalMemoryRuntime(
            condition_id="M1",
            llm_client=client,
            llm_model="fake-model",
        )

        runtime.record_completed_turn(
            message={
                "message_id": "P0001_D01_M001",
                "day": 1,
                "topic": "幼儿园适应",
                "user_message": "我第一次说清楚幼儿园适应这条线，先判断要不要找老师。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            assistant_answer="先确认老师反馈，再决定是否继续观察。",
            run_id="run-test",
        )

        snapshot = runtime.snapshot()
        self.assertEqual(snapshot["memory_llm_failure_count"], 0)
        self.assertEqual(snapshot["memories"][0]["ld_agent_metadata"]["summary_writer"], "llm")
        self.assertEqual(
            snapshot["memories"][0]["ld_agent_metadata"]["llm_consolidation"][
                "evidence_turn_ids"
            ],
            ["P0001_D01_M001"],
        )

    def test_llm_prompt_explains_event_line_memory_with_examples(self) -> None:
        client = _FakeRelationalClient()
        runtime = RelationalMemoryRuntime(
            condition_id="M3",
            llm_client=client,
            llm_model="fake-model",
        )

        runtime.record_completed_turn(
            message={
                "message_id": "P0001_D01_M001",
                "day": 1,
                "topic": "幼儿园适应",
                "user_message": "我第一次说清楚幼儿园适应这条线，先判断要不要找老师。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            assistant_answer="先确认老师反馈，再决定是否继续观察。",
            run_id="run-test",
        )

        system_prompt = client.chat.completions.requests[0]["messages"][0]["content"]
        prompts = [
            request["messages"][-1]["content"]
            for request in client.chat.completions.requests
        ]
        combined_prompt = "\n".join(prompts)
        self.assertIn("事件线关系记忆者", system_prompt)
        self.assertIn("关系结论层（M1", system_prompt)
        self.assertIn("事件线摘要层（M2", system_prompt)
        self.assertIn("细节锚点层（M3", system_prompt)
        self.assertIn("事件线级记忆不是单轮摘要", combined_prompt)
        self.assertIn("最高抽象度的关系层", combined_prompt)
        self.assertIn("事件主线层", combined_prompt)
        self.assertIn("低抽象度的可引用线索层", combined_prompt)
        self.assertIn("好例子", combined_prompt)
        self.assertIn("坏例子", combined_prompt)
        self.assertIn("写入方法", combined_prompt)
        self.assertIn("fact_layer", combined_prompt)
        self.assertIn("answer_layer", combined_prompt)
        self.assertIn("summary 必须只依据 fact_layer", combined_prompt)
        self.assertIn("不得写入事件进展、事实细节", combined_prompt)
        self.assertIn("只返回 JSON 对象", combined_prompt)

    def test_m1_m2_m3_memories_are_upserted_by_event_line(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M3")

        first_message = {
            "message_id": "P0001_D01_M001",
            "day": 1,
            "topic": "幼儿园适应",
            "user_message": "我第一次说清楚幼儿园适应这条线，先判断要不要找老师。",
            "tau": {
                "event_line_id": "L_kindergarten",
                "event_stage": "initial",
                "theme_id": "T_childcare",
            },
        }
        second_message = {
            "message_id": "P0001_D05_M001",
            "day": 5,
            "topic": "幼儿园适应",
            "user_message": "幼儿园这条线又有新变化，我还是担心要不要继续观察。",
            "tau": {
                "event_line_id": "L_kindergarten",
                "event_stage": "recurrence",
                "theme_id": "T_childcare",
            },
        }

        runtime.record_completed_turn(
            message=first_message,
            assistant_answer="先确认老师反馈，再决定是否继续观察。",
            run_id="run-test",
        )
        action = runtime.record_completed_turn(
            message=second_message,
            assistant_answer="接着上一轮，把新变化和老师反馈分开判断。",
            run_id="run-test",
        )

        snapshot = runtime.snapshot()
        self.assertEqual(snapshot["memory_unit"], "event_line_relational_memory")
        self.assertEqual(snapshot["memory_count"], 3)
        self.assertEqual(action["event_line_id"], "L_kindergarten")
        self.assertEqual(action["event_line_storage_key"], "event_line:L_kindergarten")
        self.assertIn("L_kindergarten", snapshot["event_line_memory_index"])

        for memory in snapshot["memories"]:
            self.assertEqual(
                memory["ld_agent_metadata"]["event_line_id"],
                "L_kindergarten",
            )
            self.assertEqual(
                memory["ld_agent_metadata"]["storage_unit"],
                "event_line_relational_memory",
            )
            self.assertEqual(
                memory["source_turn_ids"],
                ["P0001_D01_M001", "P0001_D05_M001"],
            )
            self.assertEqual(
                memory["ld_agent_metadata"]["event_stages"],
                ["initial", "recurrence"],
            )

        payload = runtime.retrieve_payload(
            {
                "message_id": "P0001_D08_P001",
                "day": 8,
                "turn_type": "targeted_probe",
                "topic": "幼儿园适应",
                "user_message": "这条线我不想从头解释了，你接上说。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "probe",
                },
            }
        )

        self.assertFalse(payload["retrieval"]["zero_hit"])
        self.assertEqual(payload["retrieval"]["event_line_id"], "L_kindergarten")
        for hit in payload["retrieval"]["hits"]:
            self.assertTrue(hit["event_line_match"])

    def test_event_line_mainline_file_is_written_per_event_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = RelationalMemoryRuntime(
                condition_id="M3",
                storage_root=Path(tmpdir) / "M3",
            )

            for message in [
                {
                    "message_id": "P0001_D01_M001",
                    "day": 1,
                    "topic": "幼儿园适应",
                    "user_message": "我第一次说幼儿园适应这条线。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "initial",
                    },
                },
                {
                    "message_id": "P0001_D05_M001",
                    "day": 5,
                    "topic": "幼儿园适应",
                    "user_message": "幼儿园这条线又有新变化。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "recurrence",
                    },
                },
            ]:
                runtime.record_completed_turn(
                    message=message,
                    assistant_answer="先接上这条线，再拆当前变化。",
                    run_id="run-test",
                )

            event_line_dir = Path(tmpdir) / "M3" / "event_lines"
            index = json.loads((event_line_dir / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["event_line_count"], 1)
            self.assertEqual(index["event_lines"][0]["event_line_id"], "L_kindergarten")

            event_file = event_line_dir / index["event_lines"][0]["filename"]
            payload = json.loads(event_file.read_text(encoding="utf-8"))

            self.assertEqual(payload["schema_version"], "event_line_mainline_memory_file_v1")
            self.assertEqual(payload["event_line_id"], "L_kindergarten")
            self.assertEqual(payload["condition_id"], "M3")
            self.assertEqual(
                payload["auto_event_line_summary"]["summary_mode"],
                "deterministic_agent_mainline_rollup",
            )
            self.assertEqual(
                payload["auto_event_line_summary"]["source_turn_ids"],
                ["P0001_D01_M001", "P0001_D05_M001"],
            )
            self.assertEqual(
                set(payload["layers"]),
                {"m1_conclusion", "m2_event_summary", "m3_detail_anchor"},
            )
            self.assertIn(
                "幼儿园",
                payload["auto_event_line_summary"]["mainline"],
            )

    def test_relational_overlay_does_not_fallback_across_event_lines(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M3")

        runtime.record_completed_turn(
            message={
                "message_id": "P0001_D01_M001",
                "day": 1,
                "topic": "幼儿园适应",
                "user_message": "幼儿园适应这条线要先观察老师反馈。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "initial",
                },
            },
            assistant_answer="先承接幼儿园这条线。",
            run_id="run-test",
        )
        runtime.record_completed_turn(
            message={
                "message_id": "P0001_D02_M001",
                "day": 2,
                "topic": "预算报销",
                "user_message": "预算报销这条线只关心发票截止日。",
                "tau": {
                    "event_line_id": "L_budget",
                    "event_stage": "initial",
                },
            },
            assistant_answer="这次只处理预算报销。",
            run_id="run-test",
        )

        kindergarten_payload = runtime.retrieve_payload(
            {
                "message_id": "P0001_D03_P001",
                "day": 3,
                "topic": "幼儿园适应",
                "user_message": "接上幼儿园这条线说。",
                "tau": {
                    "event_line_id": "L_kindergarten",
                    "event_stage": "probe",
                },
            }
        )

        self.assertFalse(kindergarten_payload["retrieval"]["zero_hit"])
        self.assertEqual(
            kindergarten_payload["retrieval"]["event_line_scope"],
            "strict_current_event_line",
        )
        self.assertFalse(kindergarten_payload["retrieval"]["cross_event_fallback"])
        self.assertEqual(
            kindergarten_payload["retrieval"]["blocked_counts_by_type"],
            {
                "relationship_conclusion_memory": 1,
                "event_line_summary_memory": 1,
                "detail_anchor_memory": 1,
            },
        )
        self.assertNotIn("预算报销", kindergarten_payload["memory_context"])
        for hit in kindergarten_payload["retrieval"]["hits"]:
            self.assertEqual(
                hit["memory"]["ld_agent_metadata"]["event_line_id"],
                "L_kindergarten",
            )

        missing_event_payload = runtime.retrieve_payload(
            {
                "message_id": "P0001_D04_P001",
                "day": 4,
                "topic": "不存在的新事件",
                "user_message": "这条新线之前没有说过。",
                "tau": {
                    "event_line_id": "L_new_line",
                    "event_stage": "probe",
                },
            }
        )

        self.assertTrue(missing_event_payload["retrieval"]["zero_hit"])
        self.assertEqual(
            missing_event_payload["retrieval"]["blocked_cross_event_memory_count"],
            6,
        )
        self.assertNotIn("预算报销", missing_event_payload["memory_context"])

        unbound_payload = runtime.retrieve_payload(
            {
                "message_id": "P0001_D05_P001",
                "day": 5,
                "topic": "幼儿园适应",
                "user_message": "没有 tau event_line_id 时不应该读关系 overlay。",
            }
        )

        self.assertTrue(unbound_payload["retrieval"]["zero_hit"])
        self.assertEqual(
            unbound_payload["retrieval"]["event_line_scope"],
            "unbound_no_relational_overlay",
        )
        self.assertEqual(
            unbound_payload["retrieval"]["blocked_cross_event_memory_count"],
            6,
        )
        self.assertNotIn("预算报销", unbound_payload["memory_context"])

    def test_deterministic_event_summary_does_not_store_answer_as_fact(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M2")

        runtime.record_completed_turn(
            message={
                "message_id": "P0001_D01_M001",
                "day": 1,
                "topic": "学习新技能",
                "user_message": "学习新技能这条线里，我主要卡在每天练习时间太碎。",
                "tau": {
                    "event_line_id": "L_skill",
                    "event_stage": "initial",
                },
            },
            assistant_answer="你可以申请延期，把项目截止日期往后推。",
            run_id="run-test",
        )

        snapshot = runtime.snapshot()
        event_summary = next(
            memory
            for memory in snapshot["memories"]
            if memory["memory_type"] == "event_line_summary_memory"
        )
        self.assertIn("学习新技能", event_summary["summary"])
        self.assertNotIn("申请延期", event_summary["summary"])
        self.assertIn("Answer layer", event_summary["raw_dialogue"])
        self.assertTrue(
            event_summary["ld_agent_metadata"]["source_layer_contract"][
                "summary_fact_only"
            ]
        )

    def test_non_probe_without_event_line_id_does_not_write_unbound_memory(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M2")

        action = runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "没有 tau 的旧消息",
                "user_message": "这条消息没有绑定事件线。",
            },
            assistant_answer="这次不应该写入 M2 关系记忆。",
            run_id="run-test",
        )

        self.assertEqual(action["action"], "skip_relational_writeback")
        self.assertEqual(action["reason"], "missing_event_line_id")
        self.assertEqual(action["status"], "skipped")
        self.assertEqual(runtime.snapshot()["memory_count"], 0)
        self.assertEqual(runtime.snapshot()["event_line_file_count"], 0)

    def test_m2_runtime_keeps_own_conclusion_and_event_summary_memories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = RelationalMemoryRuntime(
                condition_id="M2",
                storage_root=Path(tmpdir) / "M2",
            )

            empty_payload = runtime.retrieve_payload(
                {
                    "message_id": "D01_M001",
                    "day": 1,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "幼儿园这条线又绕回来了。",
                }
            )
            self.assertTrue(empty_payload["retrieval"]["zero_hit"])
            self.assertFalse(empty_payload["retrieval"]["uses_m0_payload"])
            self.assertTrue(empty_payload["retrieval"]["final_payload_composed_with_m0_by_runner"])
            self.assertNotIn("topics=", empty_payload["memory_context"])

            action = runtime.record_completed_turn(
                message={
                    "message_id": "D01_M001",
                    "day": 1,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "幼儿园这条线又绕回来了。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "initial",
                    },
                },
                assistant_answer="先把已经确定的事实列出来，再准备和老师沟通。",
                run_id="run-test",
            )

            self.assertEqual(action["status"], "success")
            self.assertEqual(
                set(action["memory_types"]),
                {
                    "relationship_conclusion_memory",
                    "event_line_summary_memory",
                },
            )
            payload = runtime.retrieve_payload(
                {
                    "message_id": "D02_M001",
                    "day": 2,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "昨天那件事我还是放心不下。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "recurrence",
                    },
                }
            )

            self.assertFalse(payload["retrieval"]["zero_hit"])
            self.assertIn("结论级关系记忆", payload["memory_context"])
            self.assertIn("摘要级事件线记忆", payload["memory_context"])
            self.assertEqual(
                payload["memory_composition"]["composition_rule"],
                "relational_overlay_only_runner_adds_m0_base",
            )
            self.assertFalse(payload["search_indexing_policy"]["uses_m0_search_indexing"])
            self.assertFalse(
                payload["search_indexing_policy"]["relational_layer_has_independent_generic_search"]
            )
            self.assertFalse(payload["retrieval"]["uses_other_condition_payloads"])
            self.assertTrue((Path(tmpdir) / "M2" / "snapshot.json").exists())
            self.assertTrue((Path(tmpdir) / "M2" / "event_line_summaries.jsonl").exists())

    def test_m3_probe_turn_is_read_only(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M3")

        action = runtime.record_completed_turn(
            message={
                "message_id": "D10_P001",
                "day": 10,
                "turn_type": "targeted_probe",
                "user_message": "这条线我不想从头解释了。",
            },
            assistant_answer="测试回答",
            run_id="run-test",
        )

        self.assertEqual(action["action"], "skip_probe_writeback")
        self.assertEqual(action["status"], "skipped")
        self.assertEqual(runtime.snapshot()["memory_count"], 0)

    def test_z_conditions_are_single_feature_runtime_namespaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = RelationalMemoryRuntime(
                condition_id="Z2",
                storage_root=Path(tmpdir) / "Z2",
            )

            runtime.record_completed_turn(
                message={
                    "message_id": "D01_M001",
                    "day": 1,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "我今天又在想幼儿园这件事。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "initial",
                    },
                },
                assistant_answer="先确认老师反馈，再决定是否继续观察。",
                run_id="run-test",
            )

            snapshot = runtime.snapshot()
            self.assertEqual(snapshot["condition_id"], "Z2")
            self.assertEqual(snapshot["enabled_memory_types"], ["event_line_summary_memory"])
            self.assertEqual(snapshot["memory_count"], 1)
            self.assertTrue(snapshot["config"]["single_feature_runtime"])
            self.assertFalse(snapshot["config"]["final_payload_composed_with_m0_by_runner"])
            self.assertFalse(snapshot["config"]["final_payload_has_m0_base"])
            self.assertFalse(
                snapshot["config"]["cumulative_levels_are_copied_within_condition_namespace"]
            )
            self.assertEqual(
                snapshot["memories"][0]["memory_type"],
                "event_line_summary_memory",
            )
            self.assertTrue((Path(tmpdir) / "Z2" / "event_line_summaries.jsonl").exists())
            self.assertFalse((Path(tmpdir) / "Z2" / "conclusion_memories.jsonl").exists())
            self.assertFalse((Path(tmpdir) / "Z2" / "detail_anchors.jsonl").exists())
            payload = runtime.retrieve_payload(
                {
                    "message_id": "D02_M001",
                    "day": 2,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "昨天那件事我还是放心不下。",
                    "tau": {
                        "event_line_id": "L_kindergarten",
                        "event_stage": "recurrence",
                    },
                }
            )
            self.assertFalse(payload["requires_runtime_ld_agent_memory"])
            self.assertFalse(payload["memory_composition"]["base_payload_required"])
            self.assertEqual(
                payload["memory_composition"]["composition_rule"],
                "relational_overlay_only_no_m0_base",
            )
            self.assertIn("不拼接 M0", payload["memory_context"])

    def test_resume_from_snapshot_preserves_runtime_namespace(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M1")
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "user_message": "我希望你别直接泛泛安慰。",
                "tau": {
                    "event_line_id": "L_response_boundary",
                    "event_stage": "initial",
                },
            },
            assistant_answer="我会先拆事实，再给下一步。",
            run_id="run-test",
        )

        resumed = RelationalMemoryRuntime.from_snapshot(
            runtime.snapshot(),
            condition_id="M1",
        )
        payload = resumed.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "user_message": "今天还是类似的问题。",
                "tau": {
                    "event_line_id": "L_response_boundary",
                    "event_stage": "recurrence",
                },
            }
        )

        self.assertEqual(resumed.snapshot()["condition_id"], "M1")
        self.assertEqual(resumed.snapshot()["memory_count"], 1)
        self.assertFalse(payload["retrieval"]["uses_m0_payload"])
        self.assertTrue(payload["retrieval"]["final_payload_composed_with_m0_by_runner"])


if __name__ == "__main__":
    unittest.main()
