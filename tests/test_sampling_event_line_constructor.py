from __future__ import annotations

import unittest

from long_memory_test.sampling.event_line_constructor import construct_event_lines_for_batch


class SamplingEventLineConstructorTests(unittest.TestCase):
    def test_event_line_facts_use_full_event_persona_and_stage_layers(self) -> None:
        payload = construct_event_lines_for_batch(
            sampled_personas={
                "personas": [
                    {
                        "persona_id": "P0001",
                        "source_archetype": "A01",
                        "source_archetype_label": "Service worker under ordinary pressure",
                        "age_range": "20s",
                        "occupation": "call center customer service agent",
                        "occupation_status": "employed",
                        "family_structure": "single, lives with roommates",
                        "economic_condition": "monthly budget is tight",
                        "social_support": "roommates are friendly but busy",
                        "primary_life_domains": ["finance", "work"],
                        "long_term_goals": ["save for a certificate or skill program"],
                        "decision_style": ["checks rules repeatedly"],
                        "communication_style": ["polite"],
                    }
                ]
            },
            accepted_event_sets={
                "accepted_persona_event_sets": [
                    {
                        "persona_id": "P0001",
                        "accepted_event_ids": ["E_FIN_001"],
                    }
                ]
            },
            event_pool={
                "event_categories": [
                    {
                        "event_category_id": "E_FIN_001",
                        "event_domain": "finance",
                        "event_type": "rent_or_bill_pressure",
                        "title": "Rent, utility, or bill pressure",
                        "core_issue": (
                            "The user needs to manage necessary expenses under "
                            "limited or unstable income."
                        ),
                        "possible_uncertainties": [
                            "what to pay first",
                            "whether to ask for help",
                            "what expense can be delayed",
                        ],
                        "possible_actions": [
                            "rank fixed expenses",
                            "identify official options",
                            "make one temporary cut",
                        ],
                        "possible_emotional_load": [
                            "scarcity anxiety",
                            "shame",
                            "urgency",
                        ],
                        "stage_patterns": [
                            [
                                "initial concern",
                                "recurrence",
                                "turning point",
                                "partial resolution",
                                "reflection",
                            ]
                        ],
                    }
                ]
            },
        )

        line = payload["event_lines"][0]
        stages = line["stage_sequence"]
        first_stage = stages[0]
        candidate_keys = {
            (item["source_field"], item["source_index"])
            for item in first_stage["event_candidate_facts"]
        }
        self.assertIn(("possible_uncertainties", 2), candidate_keys)
        self.assertIn(("possible_actions", 2), candidate_keys)
        self.assertIn(("possible_emotional_load", 2), candidate_keys)

        self.assertTrue(
            any("monthly budget" in item["text"] for item in first_stage["persona_conditioned_facts"])
        )
        self.assertTrue(
            any("月度预算偏紧" in item["text_zh"] for item in first_stage["persona_conditioned_facts"])
        )
        self.assertTrue(any("monthly budget" in item for item in first_stage["allowed_new_facts"]))
        self.assertTrue(any("月度预算偏紧" in item for item in first_stage["allowed_new_facts_zh"]))

        stage_delta_sets = {
            tuple(item["text"] for item in stage["stage_delta_facts"])
            for stage in stages
        }
        self.assertEqual(len(stage_delta_sets), 5)
        self.assertTrue(
            any("what expense can be delayed" in item for item in stages[2]["allowed_new_facts"])
        )
        self.assertTrue(
            any("哪些支出可以延后" in item for item in stages[2]["allowed_new_facts_zh"])
        )
        self.assertTrue(
            any("make one temporary cut" in item for item in stages[3]["allowed_new_facts"])
        )
        self.assertTrue(
            any("先做一个临时削减" in item for item in stages[3]["allowed_new_facts_zh"])
        )


if __name__ == "__main__":
    unittest.main()
