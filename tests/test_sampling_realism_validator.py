from __future__ import annotations

import unittest

from long_memory_test.sampling.realism_validator import (
    RealismValidationConfig,
    _validate_batch_diversity,
    build_realism_validation_report,
    validate_batch_samples,
    validate_persona_event_set,
    validate_pool_feasibility,
)


class SamplingRealismValidatorTests(unittest.TestCase):
    def test_pool_feasibility_passes_when_each_archetype_has_enough_domains(self) -> None:
        report = validate_pool_feasibility(
            archetype_pool=_archetype_pool(),
            event_pool=_event_pool(),
            config=RealismValidationConfig(candidate_events_min=3),
        )

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["archetypes_ready"], 2)

    def test_persona_event_set_rejects_hard_rule_mismatch(self) -> None:
        events_by_id = {
            event["event_category_id"]: event for event in _event_pool()["event_categories"]
        }
        archetypes_by_id = {item["archetype_id"]: item for item in _archetype_pool()["archetypes"]}

        report = validate_persona_event_set(
            persona=_sample_persona("P001", "A01_early_career_renter"),
            accepted_event_ids=[
                "E_WORK_001",
                "E_FIN_001",
                "E_HOME_001",
                "E_ELDER_001",
            ],
            events_by_id=events_by_id,
            archetypes_by_id=archetypes_by_id,
        )

        self.assertEqual(report["status"], "fail")
        self.assertIn("eldercare", " ".join(report["issues"]))

    def test_batch_report_catches_autobiography_risk(self) -> None:
        report = build_realism_validation_report(
            archetype_pool=_archetype_pool(include_researcher=True),
            event_pool=_event_pool(include_researcher_events=True),
            sampled_personas={
                "personas": [
                    {
                        **_sample_persona("P001", "A13_researcher_parent"),
                        "occupation": "researcher",
                        "family_structure": "married with one child",
                        "primary_life_domains": ["work", "childcare", "family"],
                    }
                ]
            },
            accepted_event_sets={
                "accepted_persona_event_sets": [
                    {
                        "persona_id": "P001",
                        "accepted_event_ids": [
                            "E_PAPER_001",
                            "E_COLLAB_001",
                            "E_CHILD_001",
                            "E_SLEEP_001",
                        ],
                    }
                ]
            },
            config=RealismValidationConfig(
                candidate_events_min=3,
                max_same_archetype_ratio_in_batch=1.0,
                max_researcher_or_student_ratio_in_batch=1.0,
                max_child_related_ratio_in_batch=1.0,
            ),
        )

        self.assertEqual(report["status"], "fail")
        persona_report = report["batch_report"]["persona_reports"][0]
        self.assertEqual(persona_report["autobiography_risk"]["level"], "high")

    def test_batch_child_related_ratio_ignores_high_school_and_no_children_text(self) -> None:
        archetype_pool = _archetype_pool()
        archetype_pool["archetypes"][0]["education_options"].append("high school graduate")
        archetype_pool["archetypes"][0]["family_structure_options"].append(
            "married, no children"
        )
        sampled_personas = {
            "personas": [
                {
                    **_sample_persona("P001", "A01_early_career_renter"),
                    "education_background": "high school graduate",
                    "family_structure": "married, no children",
                    "primary_life_domains": ["work", "finance", "housing"],
                }
            ]
        }
        accepted_event_sets = {
            "accepted_persona_event_sets": [
                {
                    "persona_id": "P001",
                    "accepted_event_ids": [
                        "E_WORK_001",
                        "E_FIN_001",
                        "E_HOME_001",
                        "E_DAILY_001",
                    ],
                }
            ]
        }

        report = validate_batch_samples(
            sampled_personas=sampled_personas,
            accepted_event_sets=accepted_event_sets,
            archetype_pool=archetype_pool,
            event_pool=_event_pool(),
            config=RealismValidationConfig(
                candidate_events_min=3,
                max_same_archetype_ratio_in_batch=1.0,
            ),
        )

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["batch_diversity"]["counts"]["child_related_count"], 0)
        self.assertEqual(report["persona_reports"][0]["autobiography_risk"]["level"], "low")

    def test_demo_batch_child_ratio_is_warning_not_failure(self) -> None:
        personas = [
            _sample_persona("P001", "A01_early_career_renter"),
            _sample_persona("P002", "A02_service_emotional_labor"),
            _sample_persona("P003", "A03_gig_worker_parent"),
            _sample_persona("P004", "A04_small_business_owner"),
            _sample_persona("P005", "A05_single_parent_service_worker"),
        ]

        report = _validate_batch_diversity(
            personas,
            config=RealismValidationConfig(max_child_related_ratio_in_batch=0.35),
        )

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["counts"]["child_related_count"], 2)
        self.assertIn("Child-related ratio 0.40 exceeds 0.35", report["warnings"][0])


def _archetype_pool(*, include_researcher: bool = False) -> dict:
    archetypes = [
        _archetype("A01_early_career_renter", ["work", "finance", "housing"]),
        _archetype("A06_midlife_caregiver", ["work", "finance", "eldercare"]),
    ]
    if include_researcher:
        archetypes.append(
            _archetype(
                "A13_researcher_parent",
                ["work", "childcare", "family", "sleep"],
                occupations=["researcher"],
                family=["married with one child"],
            )
        )
    return {"archetypes": archetypes}


def _archetype(
    archetype_id: str,
    domains: list[str],
    *,
    occupations: list[str] | None = None,
    family: list[str] | None = None,
) -> dict:
    return {
        "archetype_id": archetype_id,
        "label": archetype_id,
        "age_range_options": ["30s"],
        "occupation_options": occupations or ["office clerk"],
        "occupation_status_options": ["employed"],
        "education_options": ["bachelor's degree"],
        "family_structure_options": family or ["single, rents a room"],
        "life_stage_options": ["stable work"],
        "economic_condition_options": ["stable but tight monthly budget"],
        "social_support_options": ["a few close friends"],
        "likely_life_domains": domains,
        "long_term_goal_options": ["keep routine", "reduce stress"],
        "communication_style_options": ["plain", "detail-seeking"],
        "stress_response_options": ["overthinks", "checks messages"],
        "decision_style_options": ["risk-averse"],
        "memory_relevant_trait_options": ["prefers concrete next steps"],
    }


def _event_pool(*, include_researcher_events: bool = False) -> dict:
    events = [
        _event(
            "E_WORK_001",
            "work",
            "possible_workplace_mistake",
            ["A01_early_career_renter"],
        ),
        _event("E_FIN_001", "finance", "budget_pressure", ["A01_early_career_renter"]),
        _event("E_HOME_001", "housing", "rent_or_roommate_issue", ["A01_early_career_renter"]),
        _event("E_DAILY_001", "daily_life", "routine_disruption", ["A01_early_career_renter"]),
        _event(
            "E_ELDER_001",
            "eldercare",
            "eldercare_coordination_burden",
            ["A06_midlife_caregiver"],
        ),
        _event("E_HEALTH_001", "health_routine", "routine_checkup", ["A06_midlife_caregiver"]),
        _event("E_ADMIN_001", "administration", "paperwork_uncertainty", ["A06_midlife_caregiver"]),
        _event("E_FAMILY_001", "family", "family_coordination", ["A06_midlife_caregiver"]),
    ]
    if include_researcher_events:
        events.extend(
            [
                _event("E_PAPER_001", "work", "paper_deadline", ["A13_researcher_parent"]),
                _event(
                    "E_COLLAB_001",
                    "work",
                    "collaboration_misalignment",
                    ["A13_researcher_parent"],
                ),
                _event(
                    "E_CHILD_001",
                    "childcare",
                    "child_school_or_care_uncertainty",
                    ["A13_researcher_parent"],
                ),
                _event(
                    "E_SLEEP_001",
                    "health_routine",
                    "sleep_disruption",
                    ["A13_researcher_parent"],
                ),
            ]
        )
    return {"event_categories": events}


def _event(event_id: str, domain: str, event_type: str, compatible: list[str]) -> dict:
    return {
        "event_category_id": event_id,
        "event_domain": domain,
        "event_type": event_type,
        "title": event_type,
        "core_issue": f"{event_type} core issue",
        "compatible_archetypes": compatible,
        "incompatible_archetypes": [],
        "stage_patterns": [["initial concern", "recurrence", "partial resolution"]],
        "possible_uncertainties": ["what is true"],
        "possible_emotional_load": ["worry"],
        "possible_actions": ["document facts"],
        "relational_memory_potential": "high",
        "memory_risks": ["generic advice"],
    }


def _sample_persona(persona_id: str, source_archetype: str) -> dict:
    return {
        "persona_id": persona_id,
        "source_archetype": source_archetype,
        "age_range": "30s",
        "occupation": "office clerk",
        "occupation_status": "employed",
        "education_background": "bachelor's degree",
        "family_structure": "single, rents a room",
        "life_stage": "stable work",
        "economic_condition": "stable but tight monthly budget",
        "social_support": "a few close friends",
        "primary_life_domains": ["work", "finance", "housing"],
        "long_term_goals": ["keep routine", "reduce stress"],
        "communication_style": ["plain", "detail-seeking"],
        "stress_response": ["overthinks", "checks messages"],
        "decision_style": ["risk-averse"],
        "memory_relevant_traits": ["prefers concrete next steps"],
    }
