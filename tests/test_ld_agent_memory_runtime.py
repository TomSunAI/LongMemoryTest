from __future__ import annotations

import unittest
import types
from unittest import mock

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
        if "#Completed user turns for long-term memory#" in prompt:
            return _FakeCompletion(
                "User sought practical planning around possible kindergarten instability."
            )
        return _FakeCompletion("User prefers concrete planning over generic answers.")


class _FakeClient:
    def __init__(self) -> None:
        self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    def with_options(self, **kwargs):
        return self


class _FakeChromaCollection:
    def __init__(self) -> None:
        self.upserts = []

    def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    def query(self, **kwargs):
        ids = [item for upsert in self.upserts for item in upsert["ids"]]
        return {"ids": [ids]}


class _FakeChromaClient:
    def __init__(self) -> None:
        self.collection = _FakeChromaCollection()

    def get_or_create_collection(self, **kwargs):
        return self.collection


class LDAgentMemoryRuntimeTests(unittest.TestCase):
    def test_day_boundary_writes_session_summary_and_persona_memory(self) -> None:
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
        self.assertEqual(payload["storage_backend"], "json")
        self.assertFalse(payload["uses_chromadb"])
        self.assertFalse(payload["uses_spacy"])
        self.assertEqual(payload["memory_unit"], "session")
        self.assertGreaterEqual(payload["retrieval"]["session_summary_memory_count"], 1)
        self.assertEqual(
            payload["retrieval"]["event_memory_count"],
            payload["retrieval"]["session_summary_memory_count"],
        )
        self.assertGreaterEqual(payload["retrieval"]["persona_memory_count"], 1)
        self.assertIn("LD-Agent-style Session-Summary Memory", payload["memory_context"])
        self.assertIn("Retrieved session summaries", payload["memory_context"])
        self.assertIn("Persona memories", payload["memory_context"])
        self.assertNotIn("topics=", payload["memory_context"])
        session_hit = payload["retrieval"]["session_hits"][0]["memory"]
        self.assertEqual(session_hit["memory_type"], "session_summary_memory")
        self.assertEqual(session_hit["source_session_id"], "D01")
        self.assertEqual(session_hit["available_from_session"], "D02")
        self.assertIn(
            "User: 我想要一个实在一点的处理思路",
            session_hit["raw_dialogue"],
        )
        self.assertNotIn("Agent:", session_hit["raw_dialogue"])
        self.assertNotIn("先拆事实和下一步。", session_hit["raw_dialogue"])
        self.assertIn("topics", session_hit)
        self.assertGreater(len(session_hit["topics"]), 0)
        self.assertEqual(session_hit["ld_agent_metadata"]["datatype"], "text")
        self.assertFalse(session_hit["ld_agent_metadata"]["assistant_answer_writeback"])
        self.assertEqual(
            session_hit["ld_agent_metadata"]["write_policy"],
            "user_only_no_assistant_answer_writeback",
        )
        self.assertEqual(
            session_hit["ld_agent_metadata"]["implementation_unit"],
            "session_summary",
        )
        self.assertEqual(session_hit["ld_agent_metadata"]["memory_name"], "event_memory")
        self.assertIn("topics", session_hit["ld_agent_metadata"])

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

        self.assertEqual(payload["retrieval"]["session_summary_memory_count"], 0)
        self.assertNotIn("gold_response_strategy", payload["memory_context"])
        self.assertNotIn("m2_event_continuity", payload["memory_context"])

    def test_m0_user_only_memory_writeback_excludes_assistant_answer_terms(self) -> None:
        runtime = LDAgentMemoryRuntime()
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "学习新技能",
                "user_message": (
                    "学习新技能这条线里，我主要卡在每天练习时间太碎。"
                ),
            },
            assistant_answer="你可以申请延期，把项目截止日期往后推。",
            run_id="run-test",
        )

        same_day_payload = runtime.retrieve_payload(
            {
                "message_id": "D01_M002",
                "day": 1,
                "topic": "学习新技能",
                "user_message": "我想继续聊这个练习安排。",
            }
        )

        self.assertNotIn("申请延期", same_day_payload["retrieval"]["query_text"])
        self.assertNotIn("项目截止日期", same_day_payload["retrieval"]["query_text"])
        self.assertNotIn("申请延期", same_day_payload["memory_context"])
        self.assertIn("每天练习时间太碎", same_day_payload["memory_context"])

        next_day_payload = runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "学习新技能",
                "user_message": "昨天那个练习安排我还没想明白。",
            }
        )
        session_hit = next_day_payload["retrieval"]["session_hits"][0]["memory"]

        self.assertIn("每天练习时间太碎", session_hit["summary"])
        self.assertNotIn("申请延期", session_hit["summary"])
        self.assertNotIn("项目截止日期", session_hit["raw_dialogue"])
        self.assertNotIn("申请延期", session_hit["topic"])
        self.assertNotIn("项目截止日期", session_hit["ld_agent_metadata"]["topics"])
        self.assertFalse(session_hit["ld_agent_metadata"]["assistant_answer_writeback"])

    def test_probe_turn_is_read_only_for_writeback(self) -> None:
        runtime = LDAgentMemoryRuntime()

        action = runtime.record_completed_turn(
            message={
                "message_id": "D10_P001",
                "day": 10,
                "topic": "孩子入园适应",
                "turn_type": "targeted_probe",
                "probe_type": "m2_event_continuity",
                "user_message": "这条线我不想从头解释了。",
            },
            assistant_answer="测试回答",
            run_id="run-test",
        )

        self.assertEqual(action["action"], "skip_probe_writeback")
        self.assertEqual(action["status"], "skipped")
        self.assertEqual(runtime.short_term_session, [])
        self.assertEqual(runtime.snapshot()["session_summary_memories"], [])
        self.assertEqual(runtime.snapshot()["persona_memories"], [])

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
        self.assertEqual(snapshot["runtime_id"], "M0_ld_agent_style_session_summary")
        self.assertEqual(snapshot["memory_unit"], "session")
        self.assertIn(
            "User sought practical planning around possible kindergarten instability.",
            payload["memory_context"],
        )
        self.assertIn(
            "User prefers concrete planning over generic answers.",
            payload["memory_context"],
        )
        self.assertGreaterEqual(len(client.chat.completions.requests), 2)
        self.assertEqual(snapshot["agent_traits"], [])
        summary_prompts = [
            request["messages"][-1]["content"]
            for request in client.chat.completions.requests
            if "#Completed user turns for long-term memory#"
            in request["messages"][-1]["content"]
        ]
        self.assertEqual(len(summary_prompts), 1)
        summary_prompt = summary_prompts[0]
        self.assertNotIn("先拆事实和下一步。", summary_prompt)

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

        self.assertEqual(
            resumed.snapshot()["schema_version"],
            "m0_ld_agent_style_session_summary_runtime_v1",
        )
        self.assertGreaterEqual(payload["retrieval"]["session_summary_memory_count"], 1)
        self.assertGreaterEqual(payload["retrieval"]["persona_memory_count"], 1)
        self.assertEqual(payload["retrieval"]["session_hits"][0]["memory"]["source_session"], "D01")

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
            "target_detail_ids",
            "event trajectory",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, payload["memory_context"])

    def test_m0_remains_session_level_without_event_line_filtering(self) -> None:
        runtime = LDAgentMemoryRuntime()
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "topic": "工作消息打断休息",
                "user_message": "下班后工作消息一来，我就容易紧张。",
                "tau": {"event_line_id": "L_work_boundary"},
            },
            assistant_answer="可以先写一个延迟回复模板。",
            run_id="run-test",
        )

        payload = runtime.retrieve_payload(
            {
                "message_id": "D02_M001",
                "day": 2,
                "topic": "工作消息打断休息",
                "user_message": "这个紧张感今天又来了。",
                "tau": {"event_line_id": "L_other_line"},
            }
        )

        self.assertEqual(payload["memory_unit"], "session")
        self.assertEqual(payload["retrieval"]["strategy"], "topic_overlap_time_decay")
        self.assertGreaterEqual(payload["retrieval"]["session_summary_memory_count"], 1)
        self.assertIn("下班后工作消息", payload["memory_context"])
        self.assertNotIn("L_work_boundary", payload["memory_context"])
        self.assertNotIn("L_other_line", payload["memory_context"])

    def test_chroma_backend_stores_session_summary_and_retrieves_candidates(self) -> None:
        fake_chroma_client = _FakeChromaClient()
        fake_chroma_module = types.SimpleNamespace(
            Client=lambda: fake_chroma_client,
            PersistentClient=lambda path: fake_chroma_client,
        )
        with mock.patch("importlib.import_module", return_value=fake_chroma_module):
            runtime = LDAgentMemoryRuntime(storage_backend="chroma")
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

        snapshot = runtime.snapshot()
        self.assertTrue(snapshot["uses_chromadb"])
        self.assertEqual(snapshot["storage_backend"], "chroma")
        self.assertEqual(len(fake_chroma_client.collection.upserts), 1)
        self.assertGreaterEqual(payload["retrieval"]["session_summary_memory_count"], 1)

    def test_chroma_backend_requires_chromadb_dependency(self) -> None:
        with mock.patch("importlib.import_module", side_effect=ImportError):
            with self.assertRaisesRegex(RuntimeError, "chromadb is not installed"):
                LDAgentMemoryRuntime(storage_backend="chroma")


if __name__ == "__main__":
    unittest.main()
