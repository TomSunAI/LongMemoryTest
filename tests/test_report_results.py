from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/08_report_results.py"
SPEC = importlib.util.spec_from_file_location("report_results", SCRIPT_PATH)
assert SPEC is not None
report_results = importlib.util.module_from_spec(SPEC)
sys.modules["report_results"] = report_results
assert SPEC.loader is not None
SPEC.loader.exec_module(report_results)


class ReportResultsTests(unittest.TestCase):
    def test_review_sampling_keeps_low_high_and_divergence_buckets(self) -> None:
        candidates = [
            _candidate("low-1", "low_or_flagged"),
            _candidate("low-2", "low_or_flagged"),
            _candidate("high-1", "high_score"),
            _candidate("div-1", "model_divergence"),
            _candidate("mid-1", "random_middle"),
        ]

        selected = report_results._select_review_candidates(candidates, limit=3)

        self.assertEqual(
            {item["sampling_bucket"] for item in selected},
            {"low_or_flagged", "high_score", "model_divergence"},
        )

    def test_review_rows_blind_conditions_and_sampling_bucket(self) -> None:
        rows = report_results._review_rows(
            {
                "turns": [
                    {
                        "message_id": "D01_P001",
                        "day": 1,
                        "topic": "测试",
                        "probe_type": "current_understanding",
                        "user_message": "测试用户问题",
                        "variants": {
                            "M0": {
                                "tom_score": 20,
                                "confidence": 0.5,
                                "failure_types": ["memory_absence"],
                                "needs_human_review": True,
                                "answer_excerpt": "低分回答",
                                "overall_reason": "需要复核",
                            },
                            "M3": {
                                "tom_score": 95,
                                "confidence": 0.9,
                                "failure_types": [],
                                "needs_human_review": False,
                                "answer_excerpt": "高分回答",
                                "overall_reason": "高分样本",
                            },
                        },
                    }
                ]
            },
            limit=2,
        )

        header = rows[0]
        blind_condition_index = header.index("blind_condition")
        bucket_index = header.index("sampling_bucket")
        values = rows[1:]
        self.assertNotIn("M0", {row[blind_condition_index] for row in values})
        self.assertNotIn("M3", {row[blind_condition_index] for row in values})
        buckets = " | ".join(row[bucket_index] for row in values)
        self.assertIn("low_or_flagged", buckets)
        self.assertIn("high_score", buckets)


def _candidate(case_id: str, bucket: str) -> dict:
    return {
        "case_id": case_id,
        "message_id": case_id,
        "blind_condition": "Condition A",
        "sampling_bucket": bucket,
    }


if __name__ == "__main__":
    unittest.main()
