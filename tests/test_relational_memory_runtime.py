from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from long_memory_test.memory import RelationalMemoryRuntime


class RelationalMemoryRuntimeTests(unittest.TestCase):
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
            self.assertNotIn("topics=", empty_payload["memory_context"])

            action = runtime.record_completed_turn(
                message={
                    "message_id": "D01_M001",
                    "day": 1,
                    "topic": "孩子幼儿园可能不稳定",
                    "user_message": "幼儿园这条线又绕回来了。",
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
                }
            )

            self.assertFalse(payload["retrieval"]["zero_hit"])
            self.assertIn("结论级关系记忆", payload["memory_context"])
            self.assertIn("摘要级事件线记忆", payload["memory_context"])
            self.assertEqual(
                payload["memory_composition"]["composition_rule"],
                "condition_runtime_namespace_only",
            )
            self.assertFalse(payload["search_indexing_policy"]["uses_m0_search_indexing"])
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

    def test_resume_from_snapshot_preserves_runtime_namespace(self) -> None:
        runtime = RelationalMemoryRuntime(condition_id="M1")
        runtime.record_completed_turn(
            message={
                "message_id": "D01_M001",
                "day": 1,
                "user_message": "我希望你别直接泛泛安慰。",
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
            }
        )

        self.assertEqual(resumed.snapshot()["condition_id"], "M1")
        self.assertEqual(resumed.snapshot()["memory_count"], 1)
        self.assertFalse(payload["retrieval"]["uses_m0_payload"])


if __name__ == "__main__":
    unittest.main()
