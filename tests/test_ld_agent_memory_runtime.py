from __future__ import annotations

import unittest
import types

from long_memory_test.memory import LDAgentMemoryRuntime


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
        prompt = kwargs["messages"][-1]["content"]
        if "#Conversation#" in prompt:
            return _FakeCompletion(
                "User sought practical planning around possible kindergarten instability."
            )
        if "先拆事实" in prompt:
            return _FakeCompletion("Agent prefers practical, structured responses.")
        return _FakeCompletion("User prefers concrete planning over generic answers.")


class _FakeClient:
    def __init__(self) -> None:
        self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    def with_options(self, **kwargs):
        return self


class LDAgentMemoryRuntimeTests(unittest.TestCase):
    def test_day_boundary_writes_generic_event_and_persona_memory(self) -> None:
        runtime = LDAgentMemoryRuntime()
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "我想要一个实在一点的处理思路，不要太像标准答案。",
            },
            assistant_answer="先拆事实和下一步。",
            run_id="run-test",
        )

        payload = runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这件事又绕回来了。",
            }
        )

        self.assertEqual(payload["memory_provider"], "ld_agent_memory")
        self.assertGreaterEqual(payload["retrieval"]["event_memory_count"], 1)
        self.assertGreaterEqual(payload["retrieval"]["persona_memory_count"], 1)
        self.assertIn("Session summary", payload["memory_context"])
        self.assertIn("Persona traits", payload["memory_context"])
        event_hit = payload["retrieval"]["event_hits"][0]["memory"]
        self.assertEqual(event_hit["ld_agent_metadata"]["datatype"], "text")
        self.assertIn("topics", event_hit["ld_agent_metadata"])

    def test_current_turn_is_not_written_before_retrieval(self) -> None:
        runtime = LDAgentMemoryRuntime()

        payload = runtime.retrieve_payload(
            {
                "message_id": "D10_P001",
                "day": 10,
                "topic": "孩子入园适应",
                "probe_type": "m2_event_continuity",
                "gold_response_strategy": "不要进入 M0",
                "user_message": "这条线我不想从头解释了。",
            }
        )

        self.assertEqual(payload["retrieval"]["event_memory_count"], 0)
        self.assertNotIn("gold_response_strategy", payload["memory_context"])
        self.assertNotIn("m2_event_continuity", payload["memory_context"])

    def test_memory_llm_writes_ld_summary_and_persona_traits(self) -> None:
        client = _FakeClient()
        runtime = LDAgentMemoryRuntime(llm_client=client, llm_model="fake-model")
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "我想要一个实在一点的处理思路，不要太像标准答案。",
            },
            assistant_answer="先拆事实和下一步。",
            run_id="run-test",
        )

        payload = runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这件事又绕回来了。",
            }
        )
        snapshot = runtime.snapshot()

        self.assertEqual(snapshot["summary_writer"], "llm")
        self.assertEqual(snapshot["persona_writer"], "llm")
        self.assertEqual(snapshot["memory_llm_failure_count"], 0)
        self.assertIn(
            "User sought practical planning around possible kindergarten instability.",
            payload["memory_context"],
        )
        self.assertIn(
            "User prefers concrete planning over generic answers.",
            payload["memory_context"],
        )
        self.assertGreaterEqual(len(client.chat.completions.requests), 3)

    def test_snapshot_resume_preserves_ld_memory_without_replaying_turns(self) -> None:
        runtime = LDAgentMemoryRuntime()
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "我想要一个实在一点的处理思路。",
            },
            assistant_answer="先拆事实和下一步。",
            run_id="run-test",
        )
        runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这件事又绕回来了。",
            }
        )

        resumed = LDAgentMemoryRuntime.from_snapshot(runtime.snapshot())
        payload = resumed.retrieve_payload(
            {
                "message_id": "D03_M001",
                "day": 3,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这条线还没完。",
            }
        )

        self.assertEqual(resumed.snapshot()["schema_version"], "ld_agent_memory_runtime_v2")
        self.assertGreaterEqual(payload["retrieval"]["event_memory_count"], 1)
        self.assertGreaterEqual(payload["retrieval"]["persona_memory_count"], 1)
        self.assertEqual(payload["retrieval"]["event_hits"][0]["memory"]["source_session"], "D01")

    def test_m0_payload_does_not_include_relational_memory_layers(self) -> None:
        runtime = LDAgentMemoryRuntime()
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "我想要一个实在一点的处理思路。",
            },
            assistant_answer="先拆事实和下一步。",
            run_id="run-test",
        )

        payload = runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "孩子幼儿园可能不稳定",
                "user_message": "幼儿园这件事又绕回来了。",
            }
        )

        forbidden_terms = [
            "结论级关系记忆",
            "摘要级事件记忆",
            "细节级关系锚点",
            "gold_response_strategy",
            "bei_annotations",
            "failure_mode",
            "probe_type",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, payload["memory_context"])


if __name__ == "__main__":
    unittest.main()
