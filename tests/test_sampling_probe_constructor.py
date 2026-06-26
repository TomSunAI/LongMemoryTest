from __future__ import annotations

import unittest

from long_memory_test.sampling.probe_constructor import (
    ProbeConstructionConfig,
    construct_probe_plan_for_timeline,
)


class SamplingProbeConstructorTests(unittest.TestCase):
    def test_inserts_probes_only_after_initial_stage(self) -> None:
        payload = construct_probe_plan_for_timeline(
            timeline_batch=_timeline_batch(),
            config=ProbeConstructionConfig(
                probes_per_persona_min=2,
                probes_per_persona_max=5,
            ),
        )

        probe_plan = payload["probe_plan"]
        timeline = payload["timeline_with_probes"]
        self.assertEqual(probe_plan["validation"]["status"], "pass")
        self.assertEqual(probe_plan["summary"]["probe_count"], 4)
        active_days = [
            day
            for day in timeline["timelines"][0]["days"]
            if day.get("active") and day.get("probe_ids")
        ]
        self.assertEqual([day["event_stage"] for day in active_days], [
            "recurrence",
            "turning_point",
            "partial_resolution",
            "reflection",
        ])
        probes = probe_plan["probe_questions"]
        self.assertEqual(
            [probe["primary_dimension_id"] for probe in probes],
            ["D1", "D2", "D3", "D4"],
        )
        self.assertEqual(
            [probe["paper_probe_id"] for probe in probes],
            ["P1", "P2", "P4", "P6"],
        )
        self.assertEqual(probes[-1]["probe_type"], "alienation_avoidance")
        self.assertEqual(probes[-1]["paper_probe_type"], "Alienation Avoidance")
        self.assertEqual(probes[-1]["primary_dimension_id"], "D4")
        self.assertIn("D4", probes[-1]["evaluation_dimension_ids"])
        self.assertIn("alienation_error_rate", probes[-1]["diagnostic_dimensions"])
        self.assertIn("paper_probe_type_counts", probe_plan["summary"])
        self.assertIn("evaluation_dimension_counts", probe_plan["summary"])
        self.assertEqual(probes[0]["ground_truth"]["schema_version"], "probe_ground_truth_v0.1")
        self.assertEqual(probes[0]["ground_truth"]["event_line_id"], "L_001")
        self.assertIn("expected_references", probes[0]["ground_truth"])
        self.assertIn("scoring_rubric", probes[0]["ground_truth"])
        self.assertEqual(
            probe_plan["summary"]["primary_dimension_counts"],
            {"D1": 1, "D2": 1, "D3": 1, "D4": 1},
        )

    def test_parallel_day_probe_targets_one_specific_occurrence(self) -> None:
        payload = construct_probe_plan_for_timeline(
            timeline_batch=_parallel_timeline_batch(),
            config=ProbeConstructionConfig(
                probes_per_persona_min=1,
                probes_per_persona_max=2,
            ),
        )

        probe_plan = payload["probe_plan"]
        timeline = payload["timeline_with_probes"]
        self.assertEqual(probe_plan["validation"]["status"], "pass")
        self.assertEqual(probe_plan["summary"]["probe_count"], 1)
        probe = probe_plan["probe_questions"][0]
        day = timeline["timelines"][0]["days"][2]
        probed_occurrences = [
            occurrence
            for occurrence in day["event_occurrences"]
            if occurrence.get("probe_ids")
        ]
        self.assertEqual(len(day["probe_ids"]), 1)
        self.assertEqual(len(probed_occurrences), 1)
        self.assertEqual(probe["event_occurrence_id"], probed_occurrences[0]["event_occurrence_id"])
        self.assertEqual(
            probe["insert_after_message_id"],
            probed_occurrences[0]["interaction_unit_id"],
        )


def _timeline_batch() -> dict:
    days = [
        _day(1, "initial", 1, False),
        _day(3, "recurrence", 2, True),
        _day(5, "turning_point", 3, True),
        _day(8, "partial_resolution", 4, True),
        _day(10, "reflection", 5, True),
    ]
    return {
        "schema_version": "timeline_batch_v0.1",
        "timelines": [
            {
                "persona_id": "P0001",
                "days": days,
            }
        ],
    }


def _day(day: int, stage: str, occurrence_index: int, probe_candidate: bool) -> dict:
    return {
        "day": day,
        "active": True,
        "interaction_unit_id": f"P0001_D{day:02d}_M001",
        "persona_id": "P0001",
        "event_line_id": "L_001",
        "event_category_id": "E_001",
        "event_stage": stage,
        "stage_index": occurrence_index,
        "occurrence_index": occurrence_index,
        "probe_candidate": probe_candidate,
        "event_title": {"zh": "测试事件线"},
        "related_previous_days": [1] if occurrence_index > 1 else [],
    }


def _parallel_timeline_batch() -> dict:
    return {
        "schema_version": "timeline_batch_v0.1",
        "timelines": [
            {
                "persona_id": "P0001",
                "days": [
                    {"day": 1, "active": True, "event_occurrences": [_occurrence(1, 1, "L_001", "initial", 1, False)]},
                    {"day": 2, "active": True, "event_occurrences": [_occurrence(2, 1, "L_002", "initial", 1, False)]},
                    {
                        "day": 3,
                        "active": True,
                        "parallel_event_count": 2,
                        "event_occurrences": [
                            _occurrence(3, 1, "L_001", "recurrence", 2, True),
                            _occurrence(3, 2, "L_002", "recurrence", 2, True),
                        ],
                    },
                ],
            }
        ],
    }


def _occurrence(
    day: int,
    within_day_index: int,
    event_line_id: str,
    stage: str,
    occurrence_index: int,
    probe_candidate: bool,
) -> dict:
    return {
        "day": day,
        "active": True,
        "event_occurrence_id": f"P0001_D{day:02d}_E{within_day_index:03d}",
        "within_day_index": within_day_index,
        "interaction_unit_id": f"P0001_D{day:02d}_M{within_day_index:03d}",
        "persona_id": "P0001",
        "event_line_id": event_line_id,
        "event_category_id": f"E_{event_line_id}",
        "event_stage": stage,
        "stage_index": occurrence_index,
        "occurrence_index": occurrence_index,
        "probe_candidate": probe_candidate,
        "event_title": {"zh": f"测试事件线 {event_line_id}"},
        "related_previous_days": [1] if occurrence_index > 1 else [],
    }
