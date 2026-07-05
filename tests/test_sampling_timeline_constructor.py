from __future__ import annotations

import unittest

from long_memory_test.sampling.timeline_constructor import (
    TimelineConstructionConfig,
    construct_timeline_for_batch,
)


class SamplingTimelineConstructorTests(unittest.TestCase):
    def test_construct_timeline_respects_demo_constraints(self) -> None:
        payload = construct_timeline_for_batch(
            event_lines_batch=_event_lines_batch(),
            config=TimelineConstructionConfig(
                random_seed=1,
                timeline_days=30,
                active_sessions_min=15,
                active_sessions_max=20,
                event_line_occurrences_min=3,
                event_line_occurrences_max=6,
            ),
        )

        self.assertEqual(payload["validation"]["status"], "pass")
        timeline = payload["timelines"][0]
        self.assertGreaterEqual(timeline["active_session_count"], 15)
        self.assertLessEqual(timeline["active_session_count"], 20)
        self.assertEqual(len(timeline["days"]), 30)
        active_days = [day for day in timeline["days"] if day.get("active")]
        event_occurrences = [
            occurrence
            for day in active_days
            for occurrence in day.get("event_occurrences", [])
        ]
        self.assertEqual(timeline["active_day_count"], len(active_days))
        self.assertEqual(timeline["active_session_count"], len(event_occurrences))
        self.assertEqual(timeline["event_occurrence_total"], len(event_occurrences))
        self.assertLess(timeline["active_day_count"], timeline["active_session_count"])
        self.assertGreaterEqual(timeline["parallel_event_day_count"], 2)
        self.assertLessEqual(
            max(len(day.get("event_occurrences", [])) for day in active_days),
            2,
        )
        for count in timeline["event_line_occurrence_counts"].values():
            self.assertGreaterEqual(count, 3)
            self.assertLessEqual(count, 6)

    def test_construct_timeline_rejects_impossible_active_session_range(self) -> None:
        with self.assertRaises(ValueError):
            construct_timeline_for_batch(
                event_lines_batch=_event_lines_batch(line_count=6),
                config=TimelineConstructionConfig(
                    timeline_days=30,
                    active_sessions_min=1,
                    active_sessions_max=2,
                    event_line_occurrences_min=3,
                    event_line_occurrences_max=6,
                ),
            )

    def test_construct_timeline_respects_fixed_dense_daily_distribution(self) -> None:
        payload = construct_timeline_for_batch(
            event_lines_batch=_event_lines_batch(line_count=7),
            config=TimelineConstructionConfig(
                random_seed=7,
                timeline_days=10,
                active_sessions_min=26,
                active_sessions_max=26,
                event_line_occurrences_min=3,
                event_line_occurrences_max=5,
                max_events_per_active_day=5,
                parallel_event_days_min=6,
                probe_candidate_min_per_persona=10,
                daily_event_count_distribution={0: 1, 1: 1, 2: 2, 3: 4, 4: 1, 5: 1},
                daily_event_count_median_target=3,
            ),
        )

        self.assertEqual(payload["validation"]["status"], "pass")
        self.assertEqual(
            payload["summary"]["daily_event_count_histogram"],
            {0: 1, 1: 1, 2: 2, 3: 4, 4: 1, 5: 1},
        )
        self.assertEqual(payload["summary"]["daily_event_count_median_calendar"], 3)
        self.assertEqual(payload["summary"]["max_events_on_single_day"], 5)

        timeline = payload["timelines"][0]
        self.assertEqual(timeline["active_session_count"], 26)
        self.assertEqual(timeline["active_day_count"], 9)
        for day in timeline["days"]:
            occurrences = day.get("event_occurrences", [])
            self.assertLessEqual(len(occurrences), 5)
            self.assertEqual(
                len({item["event_line_id"] for item in occurrences}),
                len(occurrences),
            )
        for count in timeline["event_line_occurrence_counts"].values():
            self.assertGreaterEqual(count, 3)
            self.assertLessEqual(count, 5)


def _event_lines_batch(*, line_count: int = 5) -> dict:
    return {
        "personas": [
            {
                "persona_ref": {
                    "persona_id": "P0001",
                    "source_archetype": "A01",
                    "occupation": "assistant",
                },
                "event_lines": [_event_line(index) for index in range(1, line_count + 1)],
            }
        ]
    }


def _event_line(index: int) -> dict:
    return {
        "event_line_id": f"L_{index}",
        "event_category_id": f"E_{index}",
        "event_domain": "work",
        "event_domain_zh": "工作",
        "event_title": {"zh": f"事件 {index}"},
        "persistent_event_summary": f"事件线 {index}",
        "stage_sequence": [
            {
                "stage_index": stage_index,
                "event_stage": stage,
                "stage_goal": stage,
                "user_message_seed": f"{stage} message",
                "assistant_memory_expectation": "接上旧线。",
            }
            for stage_index, stage in enumerate(
                ["initial", "recurrence", "turning_point", "partial_resolution", "reflection"],
                start=1,
            )
        ],
    }
