#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _backend_common import REPO_ROOT, display_path, now_utc, write_json_atomic  # noqa: E402


DEFAULT_DATA_DIR = REPO_ROOT / "long_memory_experiment/data/generated/p0_persona_event_sampling_demo50_candidate"
DEFAULT_RUN_ROOT = REPO_ROOT / "long_memory_experiment/outputs"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs"
DEFAULT_PERSONA_COUNT = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Server-friendly one-entry experiment launcher. It prepares run-private "
            "tau inputs, then calls the unified backend without relying on Codex."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare filtered run inputs only.")
    _add_run_args(prepare)

    start = subparsers.add_parser("start", help="Prepare inputs and start detached backend run.")
    _add_run_args(start)

    run = subparsers.add_parser("run", help="Prepare inputs and run backend in this process.")
    _add_run_args(run)

    status = subparsers.add_parser("status", help="Show backend status for a run dir.")
    status.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--experiment-name",
        default=None,
        help="Optional run directory suffix. Defaults to server_pN_<conditions>.",
    )
    parser.add_argument("--conditions", default="M0,M1,M2,M3")
    parser.add_argument("--stages", default="generate,evaluate")
    parser.add_argument(
        "--persona-count",
        type=int,
        default=DEFAULT_PERSONA_COUNT,
        help=(
            "Use the first N personas from tau.z. Defaults to 2 for a cheap server "
            "smoke test; pass 50 for the full candidate pool."
        ),
    )
    parser.add_argument(
        "--personas",
        default=None,
        help="Comma-separated explicit persona ids. Overrides --persona-count.",
    )
    parser.add_argument("--condition-workers", type=int, default=4)
    parser.add_argument("--llm-timeout", type=float, default=900.0)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--generation-max-attempts", type=int, default=0)
    parser.add_argument("--generation-retry-sleep", type=float, default=30.0)
    parser.add_argument("--judge-workers", type=int, default=4)
    parser.add_argument("--judge-provider", default="deepseek")
    parser.add_argument("--eval-max-attempts", type=int, default=1)
    parser.add_argument("--eval-retry-sleep", type=float, default=30.0)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    parser.add_argument(
        "--naturalized-dialogues",
        type=Path,
        default=None,
        help="Optional P3B naturalized dialogue candidate file.",
    )
    parser.add_argument(
        "--allow-caffeinate",
        action="store_true",
        help="Allow macOS caffeinate. Server runs should leave this off.",
    )


def main() -> int:
    args = parse_args()
    if args.command == "status":
        return _status(args.run_dir)

    prepared = prepare_run_inputs(args)
    if args.command == "prepare":
        print(json.dumps(prepared, ensure_ascii=False, indent=2))
        return 0
    if args.command in {"start", "run"}:
        return _invoke_backend(args, prepared=prepared, backend_command=args.command)
    raise ValueError(f"Unsupported command: {args.command}")


def prepare_run_inputs(args: argparse.Namespace) -> dict[str, Any]:
    data_dir = args.data_dir.resolve()
    tau_path = data_dir / "tau_contract.json"
    if not tau_path.exists():
        raise FileNotFoundError(f"Missing tau contract: {tau_path}")

    source_tau = _load_json(tau_path)
    selected_personas = _resolve_personas(source_tau, args)
    run_dir = (args.run_dir or _default_run_dir(args)).resolve()
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    filtered_tau = _filter_tau_contract(source_tau, selected_personas=selected_personas)
    filtered_tau_path = inputs_dir / "tau_contract.filtered.json"
    daily_messages_path = inputs_dir / "daily_messages.json"
    probe_questions_path = inputs_dir / "probe_questions.json"
    memory_conditions_path = inputs_dir / "memory_conditions.json"
    manifest_path = run_dir / "server_experiment_manifest.json"

    write_json_atomic(filtered_tau_path, filtered_tau)
    _run_checked(
        [
            sys.executable,
            "scripts/build_tau_runner_inputs.py",
            "--tau-contract",
            str(filtered_tau_path),
            "--daily-output",
            str(daily_messages_path),
            "--probe-output",
            str(probe_questions_path),
            *(
                ["--naturalized-dialogues", str(args.naturalized_dialogues)]
                if args.naturalized_dialogues
                else []
            ),
        ]
    )
    _run_checked(
        [
            sys.executable,
            "scripts/build_tau_memory_conditions.py",
            "--tau-contract",
            str(filtered_tau_path),
            "--output",
            str(memory_conditions_path),
        ]
    )

    daily_doc = _load_json(daily_messages_path)
    probe_doc = _load_json(probe_questions_path)
    memory_doc = _load_json(memory_conditions_path)
    manifest = {
        "schema_version": "server_experiment_manifest_v1",
        "created_at": now_utc(),
        "run_dir": display_path(run_dir),
        "data_dir": display_path(data_dir),
        "source_tau_contract": display_path(tau_path),
        "selected_personas": selected_personas,
        "persona_count": len(selected_personas),
        "conditions": _split_csv(args.conditions),
        "stages": _split_csv(args.stages),
        "inputs": {
            "filtered_tau_contract": display_path(filtered_tau_path),
            "daily_messages": display_path(daily_messages_path),
            "probe_questions": display_path(probe_questions_path),
            "memory_conditions": display_path(memory_conditions_path),
        },
        "input_counts": {
            "daily_messages": len(daily_doc.get("messages", [])),
            "probe_questions": len(probe_doc.get("probe_questions", [])),
            "memory_payload_messages": memory_doc.get("summary", {}).get("message_payload_count"),
        },
        "policy": {
            "run_private_inputs": True,
            "source_data_unchanged": True,
            "persona_count_controls_scale": True,
            "full_50_requires_explicit_persona_count_50": True,
            "codex_not_required_after_launch": True,
        },
    }
    write_json_atomic(manifest_path, manifest)
    return {
        "run_dir": str(run_dir),
        "manifest": str(manifest_path),
        "data_dir": str(data_dir),
        "personas": selected_personas,
        "daily_messages": str(daily_messages_path),
        "probe_questions": str(probe_questions_path),
        "memory_conditions": str(memory_conditions_path),
        "input_counts": manifest["input_counts"],
    }


def _invoke_backend(
    args: argparse.Namespace,
    *,
    prepared: dict[str, Any],
    backend_command: str,
) -> int:
    cmd = [
        sys.executable,
        "scripts/21_experiment_backend.py",
        backend_command,
        "--run-dir",
        prepared["run_dir"],
        "--stages",
        args.stages,
        "--conditions",
        args.conditions,
        "--daily-messages",
        prepared["daily_messages"],
        "--probe-questions",
        prepared["probe_questions"],
        "--memory-conditions",
        prepared["memory_conditions"],
        "--data-dir",
        prepared["data_dir"],
        "--personas",
        ",".join(prepared["personas"]),
        "--condition-workers",
        str(args.condition_workers),
        "--llm-timeout",
        str(args.llm_timeout),
        "--generation-max-attempts",
        str(args.generation_max_attempts),
        "--generation-retry-sleep",
        str(args.generation_retry_sleep),
        "--judge-workers",
        str(args.judge_workers),
        "--judge-provider",
        args.judge_provider,
        "--eval-max-attempts",
        str(args.eval_max_attempts),
        "--eval-retry-sleep",
        str(args.eval_retry_sleep),
        "--poll-seconds",
        str(args.poll_seconds),
        "--docs-dir",
        str(args.docs_dir),
        "--all-message-ids",
    ]
    if args.temperature is not None:
        cmd.extend(["--temperature", str(args.temperature)])
    if args.top_p is not None:
        cmd.extend(["--top-p", str(args.top_p)])
    if args.max_tokens is not None:
        cmd.extend(["--max-tokens", str(args.max_tokens)])
    if not args.allow_caffeinate:
        cmd.append("--no-caffeinate")

    _append_backend_command(prepared["manifest"], cmd)
    print(shlex.join(cmd), flush=True)
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def _status(run_dir: Path) -> int:
    cmd = [
        sys.executable,
        "scripts/21_experiment_backend.py",
        "status",
        "--run-dir",
        str(run_dir),
    ]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def _resolve_personas(source_tau: dict[str, Any], args: argparse.Namespace) -> list[str]:
    available = [
        str(item.get("persona_id"))
        for item in source_tau.get("z", [])
        if isinstance(item, dict) and item.get("persona_id")
    ]
    if not available:
        raise ValueError("tau.z does not contain persona ids.")
    if args.personas:
        selected = _split_csv(args.personas)
    else:
        if args.persona_count <= 0:
            raise ValueError("--persona-count must be positive.")
        if args.persona_count > len(available):
            raise ValueError(
                f"--persona-count {args.persona_count} exceeds available personas {len(available)}."
            )
        selected = available[: args.persona_count]
    missing = [item for item in selected if item not in available]
    if missing:
        raise ValueError(f"Unknown personas for selected data dir: {', '.join(missing)}")
    return selected


def _filter_tau_contract(
    tau: dict[str, Any],
    *,
    selected_personas: list[str],
) -> dict[str, Any]:
    selected = set(selected_personas)
    result = deepcopy(tau)
    for key in ("z", "personas", "T", "L", "I", "P"):
        value = result.get(key)
        if isinstance(value, list):
            result[key] = [
                item
                for item in value
                if not isinstance(item, dict) or str(item.get("persona_id")) in selected
            ]
    bindings = result.get("message_bindings", {})
    if isinstance(bindings, dict):
        result["message_bindings"] = {
            key: value
            for key, value in bindings.items()
            if isinstance(value, dict) and str(value.get("persona_id")) in selected
        }
    result["filtered_subset"] = {
        "schema_version": "tau_persona_subset_v1",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "selected_personas": selected_personas,
        "selection_policy": "explicit_personas_or_first_n_from_tau_z",
        "source_tau_summary": tau.get("summary", {}),
    }
    result["summary"] = {
        **(result.get("summary", {}) if isinstance(result.get("summary"), dict) else {}),
        "persona_count": len(result.get("z", [])),
        "theme_count": len(result.get("T", [])),
        "event_line_count": len(result.get("L", [])),
        "interaction_unit_count": len(result.get("I", [])),
        "targeted_probe_count": len(result.get("P", [])),
        "message_binding_count": len(result.get("message_bindings", {})),
        "filtered_from_persona_count": tau.get("summary", {}).get("persona_count"),
    }
    validation = result.get("validation", {})
    if isinstance(validation, dict):
        result["validation"] = {
            **validation,
            "filtered_subset_validation_note": (
                "Source tau validation is preserved; this file is a persona-filtered "
                "run input subset generated by scripts/23_run_server_experiment.py."
            ),
        }
    return result


def _append_backend_command(manifest_path: str, cmd: list[str]) -> None:
    path = Path(manifest_path)
    manifest = _load_json(path)
    manifest["backend_command"] = cmd
    manifest["backend_command_text"] = shlex.join(cmd)
    write_json_atomic(path, manifest)


def _run_checked(cmd: list[str]) -> None:
    print(shlex.join(cmd), flush=True)
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def _default_run_dir(args: argparse.Namespace) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    persona_label = f"p{args.persona_count}"
    if args.personas:
        persona_label = f"p{len(_split_csv(args.personas))}"
    suffix = args.experiment_name or f"server_{persona_label}_{_slug(args.conditions)}"
    return args.run_root / f"run_{stamp}_{_slug(suffix)}"


def _load_json(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _slug(value: str) -> str:
    chars = [ch.lower() if ch.isalnum() else "_" for ch in value]
    text = "".join(chars).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or "experiment"


if __name__ == "__main__":
    raise SystemExit(main())
