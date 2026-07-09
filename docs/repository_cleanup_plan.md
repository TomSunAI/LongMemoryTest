# Repository Cleanup Plan

Last updated: 2026-07-09

This file records the cleanup boundary for keeping the experiment trunk clean while preserving reproducibility for the paper. It is a working file: update it when an old entry point is archived, deleted, or promoted back into the formal pipeline.

## Current Trunk Boundary

The formal experiment trunk is:

- Trajectory construction: `src/long_memory_test/sampling/` plus `scripts/run_p0_persona_event_sampling.py`, `scripts/run_p1_event_line_batch_construction.py`, `scripts/run_p1_timeline_construction.py`, `scripts/run_p2_probe_insertion.py`, `scripts/run_p3_daily_interaction_construction.py`, `scripts/run_p4_tau_contract_construction.py`, and `scripts/run_p3b_interaction_naturalization.py`.
- Runtime conditions: `src/long_memory_test/memory/`, `src/long_memory_test/agents/memory_condition_builder.py`, `src/long_memory_test/agents/tau_dialogue_adapter.py`, and `scripts/build_tau_memory_conditions.py`.
- Server launch and generation/evaluation backend: `scripts/23_run_server_experiment.py`, `scripts/21_experiment_backend.py`, `scripts/_backend_common.py`, `scripts/run_dialogue_conditions.py`, `scripts/12_supervise_dialogue_conditions.py`, `scripts/13_start_dialogue_conditions_background.py`, `scripts/18_run_two_person_postprocess_after_generation.py`, `scripts/19_start_two_person_postprocess_background.py`, and `scripts/20_supervise_two_person_postprocess.py`.
- Evaluation/reporting: `src/long_memory_test/evaluation/`, `scripts/08_report_results.py`, `scripts/16_generate_two_person_eval_report.py`, and `scripts/17_generate_two_person_eval_report_html.py`.
- Appendix/report publication: `scripts/22_generate_appendix_html.py`, `docs/appendix/aaai_appendix/`, and `docs/experiments/`.
- Project operating notes: `agent.md`.

## Documentation Layout

Current documentation folders are:

- `docs/experiments/`: final readable experiment reports grouped by experiment id.
- `docs/appendix/`: AAAI appendix / supplementary material outputs.
- `docs/references/`: paper/reference sources used as current research basis.
- `docs/history/`: archived old reports, pilot notes, and generated one-off documents.
- `docs/repository_cleanup_plan.md`: current repository cleanup/governance record.

Do not use `docs/history/` as an implementation source for current coding or experiment decisions unless the user explicitly asks to inspect historical material. New reports should not be written to the `docs/` root.

The repository `.ignore` excludes `docs/history/` from default local text search, so `rg`-based code/document searches do not accidentally use archived reports as current guidance.

## Formal Data To Preserve

These are not temporary even when they look generated:

- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo50_candidate/`: current 50-person candidate trajectory pool.
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo15_candidate/`: 15-person candidate predecessor, useful for verifying that P0001-P0015 remained stable after expansion.
- `long_memory_experiment/data/generated/p0_persona_event_sampling_demo5/`: canonical pilot trajectory used by earlier reports and appendix examples.
- `long_memory_experiment/outputs/`: raw run outputs, logs, checkpoints, judge JSON, and resumable state. These are ignored by Git, but should not be bulk-deleted while an experiment is being audited.
- `docs/experiments/`: final human-readable experiment report archives.
- `docs/appendix/aaai_appendix/`: fixed working appendix output.
- `docs/history/`: historical documents retained only for audit trail; not part of current implementation guidance.

## Archived Or Transitional Code

These items are historical or transitional. They should not be used as the default path for new formal experiments.

- `scripts/01_build_timeline.py`, `scripts/02_annotate_bei.py`, `scripts/03_generate_probe_plan.py`, `scripts/04_build_memory_conditions.py`: first-generation script route.
- `scripts/generate_timeline.py`, `scripts/generate_daily_user_messages.py`, `scripts/generate_daily_scene_cards.py`, `scripts/generate_probe_question_plan.py`, `scripts/generate_a_script_report_html.py`: scene-card route helpers.
- `src/long_memory_test/agents/event_stream_generator.py`, `daily_message_generator.py`, `daily_scene_card_generator.py`, and `probe_question_generator.py`: first-generation scene-card/probe generation modules.
- `sample_output/`: first-generation sample artifacts. The directory is ignored by Git, but some early files are still tracked for historical tests.
- `long_memory_experiment/cache/`: cache artifacts. The directory is ignored by Git, but a few early cache files were already tracked.
- Removed on 2026-07-09: `scripts/run_m0_m1_dialogue_probe.py`. Its reusable helper functions were extracted into `src/long_memory_test/agents/dialogue_runner_helpers.py`, and tests were moved to `tests/test_dialogue_runner_helpers.py`.
- Removed on 2026-07-09: Letta pilot code and tools: `src/long_memory_test/legacy/`, `src/long_memory_test/letta_memory.py`, `scripts/letta_memory_smoke.py`, `scripts/create_m0_letta_baseline.py`, and `scripts/12_check_m0_letta_full_retrieval.py`.
- Removed on 2026-07-09: old full-experiment wrappers `scripts/09_run_full_experiment.py`, `scripts/10_supervise_full_experiment.py`, and `scripts/11_start_full_experiment_background.py`. Server runs now use `scripts/23_run_server_experiment.py`.

## Safe Cleanup Already Done

On 2026-07-09:

- Removed workspace `.DS_Store` files.
- Removed project-level `__pycache__` directories under `scripts/`, `src/`, and `tests/`.
- Left `.venv/` cache directories untouched.
- Extracted reusable dialogue-runner helper functions into `src/long_memory_test/agents/dialogue_runner_helpers.py`.
- Removed the old `scripts/run_m0_m1_dialogue_probe.py` pilot entry point after `scripts/run_dialogue_conditions.py` no longer depended on it.
- Removed Letta pilot code/tools and the obsolete 09/10/11 full-experiment wrappers.
- Moved root-level historical docs into `docs/history/`; current docs root now only keeps `repository_cleanup_plan.md` plus standard subdirectories.

These artifacts are already ignored by `.gitignore` and can be removed again at any time.

## Next Cleanup Pass

Recommended sequence:

1. Update `README.md` so it describes the current backend/tau pipeline first, and moves the A-V0.1/A-V0.4 scene-card route to a historical section.
2. Decide whether early tracked generated artifacts should remain in Git:
   - `sample_output/*.json`
   - `long_memory_experiment/cache/*.json`
   - early root-level `docs/*.html`
3. If those artifacts are no longer needed for reproducibility, remove them from Git with `git rm --cached` first, not by silently deleting the local evidence.
4. Move first-generation report generators into an archive namespace only after current appendix/report generation no longer imports or links them.

## Rules For Future Work

- New generation/evaluation experiments must use `scripts/21_experiment_backend.py` as the unified entry point.
- Server-side experiments should use `scripts/23_run_server_experiment.py`, which prepares run-private persona subsets before calling `scripts/21_experiment_backend.py`.
- Full 50-person runs must pass `--persona-count 50`; smaller `--persona-count` values are the expected smoke-test path.
- Final experiment reports must be published to `docs/experiments/<experiment_id>/`.
- Appendix output must be regenerated through `scripts/22_generate_appendix_html.py` and overwrite `docs/appendix/aaai_appendix/` unless the user explicitly requests a versioned snapshot.
- Do not add new one-off scripts at repository root. New scripts must either be formal pipeline entry points or clearly named transitional utilities with a cleanup note here.
- Do not put temporary files, local model logs, PID files, or ad hoc HTML snapshots into the tracked trunk.
- Do not place new reports directly in `docs/`; use `docs/experiments/`, `docs/appendix/`, `docs/references/`, or `docs/history/` according to purpose.
