from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

from long_memory_test.agents.bei_annotator import generate_bei_annotations
from long_memory_test.agents.memory_condition_builder import generate_memory_conditions


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


class _FakeBlocks:
    def __init__(self) -> None:
        self.updated = []

    def list(self, **kwargs):
        return [
            {
                "label": "persona",
                "value": "Generic M0 persona.",
            },
            {
                "id": "block-history",
                "label": "m0_conversation_history",
                "value": "No M0 conversation turns have been written yet.",
            }
        ]

    def update(self, block_label, **kwargs):
        self.updated.append((block_label, kwargs))
        return {
            "id": "block-history",
            "label": block_label,
            "value": kwargs.get("value", ""),
        }


class _FakeTopBlocks:
    def create(self, **kwargs):
        return {"id": "block-created", **kwargs}


class _FakeMessages:
    def search(self, **kwargs):
        return {"results": []}


class _FakePassages:
    def __init__(self) -> None:
        self.created = []

    def search(self, **kwargs):
        return {"results": []}

    def create(self, **kwargs):
        self.created.append(kwargs)
        return {"id": "passage-test"}


class _FakeAgents:
    def __init__(self) -> None:
        self.blocks = _FakeBlocks()
        self.passages = _FakePassages()


class _FakeLetta:
    def __init__(self) -> None:
        self.agents = _FakeAgents()
        self.messages = _FakeMessages()
        self.blocks = _FakeTopBlocks()


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

    def test_memory_conditions_make_m0_generic_and_m2_m3_cumulative(self) -> None:
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
        self.assertIn("Letta 默认记忆基线", payloads["M0"]["memory_context"])
        self.assertTrue(payloads["M0"]["requires_runtime_letta"])
        self.assertNotIn("第 10 天", payloads["M0"]["memory_context"])
        self.assertNotIn("M0_letta_default_memory", specs["M1"]["can_read"])
        self.assertNotIn("M0_letta_default_memory", specs["M2"]["can_read"])
        self.assertNotIn("M0_letta_default_memory", specs["M3"]["can_read"])
        self.assertNotIn("Letta M0 默认记忆 +", specs["M1"]["definition"])
        self.assertNotIn("Letta M0 默认记忆 +", specs["M2"]["definition"])
        self.assertNotIn("Letta M0 默认记忆 +", specs["M3"]["definition"])
        self.assertIn("结论级关系记忆", payloads["M2"]["memory_context"])
        self.assertIn("摘要级事件记忆", payloads["M2"]["memory_context"])
        self.assertIn("细节级关系锚点", payloads["M3"]["memory_context"])
        self.assertIn("使用边界", payloads["M3"]["memory_context"])
        self.assertNotIn("误用风险", payloads["M3"]["memory_context"])
        self.assertNotIn("- 关系锚点：", payloads["M3"]["memory_context"])

    def test_runner_payload_for_relational_conditions_does_not_attach_m0(self) -> None:
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
            m0_letta_payload={
                "condition_id": "M0",
                "memory_context": "M0 Letta 默认记忆：不应拼入 M2",
                "source_detail_ids": ["m0_source"],
            },
        )

        self.assertIn("摘要级事件记忆", payload["memory_context"])
        self.assertNotIn("M0 Letta 默认记忆", payload["memory_context"])
        self.assertNotIn("m0_letta_baseline", payload)
        self.assertNotIn("m0_source", payload.get("source_detail_ids", []))

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

    def test_runner_writes_m0_turn_back_to_letta_core_block(self) -> None:
        client = _FakeClient()
        letta = _FakeLetta()
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
            },
            scene_card=None,
            llm_client=client,
            letta_client=letta,
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
                        "definition": "Letta 默认记忆基线",
                    }
                ]
            },
            m0_letta_agent_id="agent-test",
            m0_letta_search_limit=5,
            m0_letta_writeback=True,
            condition_ids=["M0"],
            short_term_histories={"M0": []},
            previous_message_ids=[],
        )

        self.assertEqual(len(letta.agents.blocks.updated), 1)
        block_label, update = letta.agents.blocks.updated[0]
        self.assertEqual(block_label, "m0_conversation_history")
        self.assertEqual(update["agent_id"], "agent-test")
        self.assertIn("我今天又在想幼儿园这件事。", update["value"])
        self.assertIn("m0_assistant_answer", update["value"])
        self.assertIn("message_id: D01_M001", update["value"])
        self.assertEqual(turn["memory_actions"][0]["status"], "success")
        self.assertEqual(
            turn["variants"]["M0"]["memory_writeback"]["method"],
            "agents.blocks.update",
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
