#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = REPO_ROOT / "long_memory_experiment/outputs/run_20260628_demo5_tau_full_m0_m3"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wait for the two-person dialogue generation, then run evaluation reports."
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--personas", default="P0001,P0002")
    parser.add_argument("--poll-seconds", type=float, default=60.0)
    parser.add_argument("--judge-workers", type=int, default=4)
    parser.add_argument("--judge-provider", default="deepseek")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DEFAULT_DOCS_DIR,
        help="Directory for canonical final report copies.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Trajectory data directory used by the HTML report for persona metadata.",
    )
    parser.add_argument(
        "--variants",
        default=None,
        help="Comma-separated variants to judge. Defaults to run_config conditions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir
    status_path = run_dir / "dialogue_supervisor_status.json"
    responses = run_dir / "responses_by_condition.json"
    eval_status = run_dir / "eval_status.json"
    _write_status(eval_status, "waiting_for_generation", run_dir=run_dir)
    _log(f"waiting for generation status: {status_path} or {responses}")
    while True:
        status = _load_json(status_path)
        response_status = _load_json(responses)
        state = _generation_state(status, response_status)
        _write_status(
            eval_status,
            "waiting_for_generation",
            run_dir=run_dir,
            generation_status=state,
        )
        _log(f"generation status={state}")
        if state == "complete":
            break
        if state == "failed":
            _write_status(eval_status, "failed", run_dir=run_dir, error="generation failed")
            _log("generation failed; postprocess aborted")
            return 1
        time.sleep(max(args.poll_seconds, 1.0))

    conversation = run_dir / "conversation_log_two_person_eval.json"
    automatic_json = run_dir / "automatic_scores_two_person.json"
    automatic_md = run_dir / "automatic_scores_two_person.md"
    llm_json = run_dir / "llm_judge_scores_two_person.json"
    llm_md = run_dir / "llm_judge_scores_two_person.md"
    markdown_report = run_dir / "two_person_eval_report.md"
    html_report = run_dir / "two_person_eval_report.html"
    variants = args.variants or _variants_from_run_config(run_dir)

    _run_step(
        eval_status,
        "extract_conversation",
        [
            sys.executable,
            "scripts/15_extract_eval_conversation_log.py",
            "--input",
            str(responses),
            "--output",
            str(conversation),
            "--personas",
            args.personas,
        ],
        run_dir=run_dir,
    )
    _run_step(
        eval_status,
        "automatic_eval",
        [
            sys.executable,
            "scripts/evaluate_tom_quality.py",
            "--conversation-log",
            str(conversation),
            "--output-json",
            str(automatic_json),
            "--output-md",
            str(automatic_md),
        ],
        run_dir=run_dir,
    )
    _run_step(
        eval_status,
        "llm_judge",
        [
            sys.executable,
            "scripts/evaluate_tom_quality_llm.py",
            "--conversation-log",
            str(conversation),
            "--output-json",
            str(llm_json),
            "--output-md",
            str(llm_md),
            "--provider",
            args.judge_provider,
            "--variants",
            variants,
            "--judge-workers",
            str(args.judge_workers),
            "--print-progress",
        ],
        run_dir=run_dir,
    )
    _run_step(
        eval_status,
        "markdown_report",
        [
            sys.executable,
            "scripts/16_generate_two_person_eval_report.py",
            "--run-dir",
            str(run_dir),
            "--output",
            str(markdown_report),
        ],
        run_dir=run_dir,
    )
    _run_step(
        eval_status,
        "html_report",
        [
            sys.executable,
            "scripts/17_generate_two_person_eval_report_html.py",
            "--run-dir",
            str(run_dir),
            "--output",
            str(html_report),
            "--data-dir",
            str(args.data_dir),
        ],
        run_dir=run_dir,
    )
    docs_artifacts = _publish_final_reports(
        run_dir=run_dir,
        docs_dir=args.docs_dir,
        data_dir=args.data_dir,
        variants=variants,
        markdown_report=markdown_report,
        html_report=html_report,
        automatic_json=automatic_json,
        automatic_md=automatic_md,
        llm_json=llm_json,
        llm_md=llm_md,
    )
    _write_status(
        eval_status,
        "complete",
        run_dir=run_dir,
        artifacts={
            "conversation_log": _display_path(conversation),
            "automatic_json": _display_path(automatic_json),
            "automatic_md": _display_path(automatic_md),
            "llm_json": _display_path(llm_json),
            "llm_md": _display_path(llm_md),
            "markdown_report": _display_path(markdown_report),
            "html_report": _display_path(html_report),
            "docs": docs_artifacts,
        },
    )
    _log("two-person postprocess complete")
    return 0


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _generation_state(status: dict, response_status: dict) -> str:
    state = (
        status.get("status")
        or response_status.get("checkpoint", {}).get("status")
        or response_status.get("status")
    )
    if state:
        return str(state)
    completed_turns = (
        response_status.get("checkpoint", {}).get("completed_turns")
        or len(response_status.get("turns") or [])
    )
    expected_turns = (
        response_status.get("checkpoint", {}).get("expected_turns")
        or response_status.get("expected_turns")
        or response_status.get("run_config", {}).get("expected_turns")
    )
    if expected_turns and completed_turns >= expected_turns:
        return "complete"
    if completed_turns:
        return "running"
    return "missing"


def _run_step(status_path: Path, step: str, cmd: list[str], *, run_dir: Path) -> None:
    _write_status(status_path, "running", run_dir=run_dir, step=step, command=cmd)
    try:
        _run(cmd)
    except Exception as exc:
        _write_status(status_path, "failed", run_dir=run_dir, step=step, error=str(exc))
        raise


def _run(cmd: list[str]) -> None:
    _log("running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _variants_from_run_config(run_dir: Path) -> str:
    config = _load_json(run_dir / "run_config.json")
    conditions = [
        str(item)
        for item in config.get("conditions", [])
        if item
    ]
    return ",".join(conditions or ["M0", "M1", "M2", "M3"])


def _publish_final_reports(
    *,
    run_dir: Path,
    docs_dir: Path,
    data_dir: Path,
    variants: str,
    markdown_report: Path,
    html_report: Path,
    automatic_json: Path,
    automatic_md: Path,
    llm_json: Path,
    llm_md: Path,
) -> dict[str, str]:
    stem = _docs_report_stem(run_dir=run_dir, variants=variants)
    experiment_dir = docs_dir / "experiments" / stem
    experiment_dir.mkdir(parents=True, exist_ok=True)
    legacy_markdown = run_dir / "two_person_m0_m3_evaluation_report.md"
    markdown_source = markdown_report if markdown_report.exists() else legacy_markdown
    copies: list[tuple[str, Path, Path]] = [
        ("html_report", html_report, experiment_dir / f"{stem}.html"),
        ("markdown_report", markdown_source, experiment_dir / f"{stem}.md"),
        ("automatic_json", automatic_json, experiment_dir / f"{stem}_automatic_scores.json"),
        ("automatic_markdown", automatic_md, experiment_dir / f"{stem}_automatic_scores.md"),
        ("llm_judge_json", llm_json, experiment_dir / f"{stem}_llm_judge.json"),
        ("llm_judge_markdown", llm_md, experiment_dir / f"{stem}_llm_judge.md"),
    ]
    artifacts: dict[str, str] = {
        "docs_experiment_dir": _display_path(experiment_dir),
        "experiment_id": stem,
    }
    for key, source, target in copies:
        if not source.exists():
            continue
        shutil.copy2(source, target)
        artifacts[key] = _display_path(target)

    manifest_path = run_dir / "final_report_manifest.json"
    docs_manifest_path = experiment_dir / f"{stem}_manifest.json"
    readme_path = experiment_dir / f"{stem}_README.md"
    artifacts["manifest"] = _display_path(manifest_path)
    artifacts["docs_manifest"] = _display_path(docs_manifest_path)
    artifacts["readme"] = _display_path(readme_path)

    manifest = {
        "schema_version": "final_report_docs_manifest_v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_dir": _display_path(run_dir),
        "data_dir": _display_path(data_dir),
        "variants": _split_variants(variants),
        "experiment_id": stem,
        "artifacts": artifacts,
        "policy": {
            "canonical_final_reports_live_in_docs_experiment_folder": True,
            "run_dir_keeps_raw_and_resume_artifacts": True,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    docs_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(
        _experiment_readme(manifest=manifest),
        encoding="utf-8",
    )
    _write_experiments_index(docs_dir)
    return artifacts


def _experiment_readme(*, manifest: dict[str, object]) -> str:
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    variants = ", ".join(str(item) for item in manifest.get("variants", []))
    lines = [
        f"# {manifest.get('experiment_id', 'experiment')}",
        "",
        f"- Run dir: `{manifest.get('run_dir', '')}`",
        f"- Variants: `{variants}`",
        "",
        "## Files",
        "",
    ]
    labels = [
        ("html_report", "HTML report"),
        ("markdown_report", "Markdown report"),
        ("llm_judge_markdown", "LLM judge summary"),
        ("llm_judge_json", "LLM judge JSON"),
        ("automatic_markdown", "Rule-based diagnostic summary"),
        ("automatic_json", "Rule-based diagnostic JSON"),
        ("docs_manifest", "Manifest"),
    ]
    for key, label in labels:
        value = artifacts.get(key)
        if value:
            lines.append(f"- {label}: `{Path(str(value)).name}`")
    lines.append("")
    return "\n".join(lines)


def _write_experiments_index(docs_dir: Path) -> None:
    experiments_dir = docs_dir / "experiments"
    if not experiments_dir.exists():
        return
    rows: list[tuple[str, dict[str, object]]] = []
    for manifest_path in sorted(experiments_dir.glob("*/*_manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows.append((manifest_path.parent.name, manifest))
    lines = [
        "# Experiment Reports",
        "",
        "Each folder contains the final readable outputs for one experiment. Raw run logs, checkpoints, and oversized response artifacts remain under `long_memory_experiment/outputs/`.",
        "",
        "| Experiment | Variants | Report | Run dir |",
        "|---|---|---|---|",
    ]
    for folder_name, manifest in rows:
        variants = ", ".join(str(item) for item in manifest.get("variants", []))
        artifacts = manifest.get("artifacts", {})
        report = "report.html"
        if isinstance(artifacts, dict):
            report = Path(str(artifacts.get("html_report", report))).name
        lines.append(
            f"| `{folder_name}` | `{variants}` | [`{report}`]({folder_name}/{report}) | `{manifest.get('run_dir', '')}` |"
        )
    lines.append("")
    (experiments_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _docs_report_stem(*, run_dir: Path, variants: str) -> str:
    name = run_dir.name
    descriptor = name[4:] if name.startswith("run_") else name
    report_date = ""
    match = re.match(r"(?P<date>\d{8})(?:_\d{4})?_(?P<rest>.+)", descriptor)
    if match:
        report_date = match.group("date")
        descriptor = match.group("rest")
    if not descriptor.startswith("two_person_"):
        descriptor = f"two_person_{_variant_slug(variants)}_{descriptor}"
    stem = f"{descriptor}_eval_report"
    if report_date:
        stem = f"{stem}_{report_date}"
    return _safe_slug(stem)


def _variant_slug(variants: str) -> str:
    return "_".join(_safe_slug(item) for item in _split_variants(variants)) or "conditions"


def _split_variants(variants: str) -> list[str]:
    return [item.strip() for item in variants.split(",") if item.strip()]


def _safe_slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^0-9A-Za-z]+", "_", value.strip().lower())).strip("_")


def _log(message: str) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"[{now}] {message}", flush=True)


def _write_status(path: Path, status: str, *, run_dir: Path, **extra: object) -> None:
    payload = {
        "schema_version": "two_person_eval_status_v1",
        "status": status,
        "run_dir": _display_path(run_dir),
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **extra,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
