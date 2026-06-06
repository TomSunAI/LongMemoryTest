from __future__ import annotations

import unittest

from long_memory_test.memory import LDAgentMemoryRuntime


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
        self.assertIn("用户讨论过", payload["memory_context"])
        self.assertIn("用户偏好直接", payload["memory_context"])

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


if __name__ == "__main__":
    unittest.main()
