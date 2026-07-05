#!/usr/bin/env python3
"""Extract a compact conversation log from a large dialogue result file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, TextIO


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a compact evaluator input from responses_by_condition.json."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--personas", required=True, help="Comma-separated ids, e.g. P0001,P0002")
    parser.add_argument(
        "--memory-excerpt-chars",
        type=int,
        default=1800,
        help="Maximum memory context chars kept per variant for LLM judge boundary.",
    )
    args = parser.parse_args()

    keep_personas = tuple(
        item.strip() for item in args.personas.split(",") if item.strip()
    )
    if not keep_personas:
        raise SystemExit("--personas must contain at least one persona id")

    stats = extract_eval_log(
        input_path=args.input,
        output_path=args.output,
        keep_personas=keep_personas,
        memory_excerpt_chars=args.memory_excerpt_chars,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def extract_eval_log(
    *,
    input_path: Path,
    output_path: Path,
    keep_personas: tuple[str, ...],
    memory_excerpt_chars: int,
) -> dict[str, Any]:
    tmp_path = output_path.with_name(f"{output_path.name}.tmp")
    kept_turns = 0
    probe_turns = 0
    last_message_id = None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as src, tmp_path.open(
        "w", encoding="utf-8"
    ) as dst:
        skip_to_turns(src)
        dst.write("{\n")
        dst.write('  "schema_version": "conversation_log_v0.1",\n')
        dst.write(
            '  "description": "Compact two-person evaluator input extracted from responses_by_condition.json.",\n'
        )
        dst.write('  "turns": [')

        first_turn = True
        for item in iter_turn_objects(src):
            if isinstance(item, ArrayEnd):
                break
            message_id = get_turn_message_id(item)
            if not should_keep_message_id(message_id, keep_personas):
                continue

            compact = compact_turn(item, memory_excerpt_chars=memory_excerpt_chars)
            if compact.get("input", {}).get("tom_dimensions"):
                probe_turns += 1

            if first_turn:
                dst.write("\n")
            else:
                dst.write(",\n")
            write_indented_json(dst, compact, indent_spaces=4)
            first_turn = False
            kept_turns += 1
            last_message_id = message_id

        if first_turn:
            dst.write("\n")
        else:
            dst.write("\n")
        dst.write("  ],\n")
        dst.write('  "extraction": ')
        extraction = {
            "source": str(input_path),
            "personas": list(keep_personas),
            "kept_turns": kept_turns,
            "probe_turns": probe_turns,
            "last_message_id": last_message_id,
            "memory_excerpt_chars": memory_excerpt_chars,
        }
        dst.write(json.dumps(extraction, ensure_ascii=False, indent=2).replace("\n", "\n  "))
        dst.write("\n}\n")

    validate_json(tmp_path)
    tmp_path.replace(output_path)
    return {
        "output": str(output_path),
        "kept_turns": kept_turns,
        "probe_turns": probe_turns,
        "last_message_id": last_message_id,
    }


def skip_to_turns(src: TextIO) -> None:
    for line in src:
        if line.lstrip().startswith('"turns"'):
            return
    raise ValueError("Could not find top-level turns array")


class ArrayEnd:
    pass


def iter_turn_objects(src: TextIO):
    buffer: list[str] = []
    depth = 0
    in_string = False
    escaped = False
    collecting = False

    for line in src:
        stripped = line.strip()
        if not collecting:
            if stripped.startswith("]"):
                yield ArrayEnd()
                return
            if not stripped:
                continue
            collecting = True

        buffer.append(line)
        depth, in_string, escaped = update_json_depth(
            line,
            depth=depth,
            in_string=in_string,
            escaped=escaped,
        )
        if collecting and depth == 0:
            text = "".join(buffer).rstrip()
            if text.endswith(","):
                text = text[:-1].rstrip()
            yield json.loads(text)
            buffer = []
            collecting = False

    if buffer:
        raise ValueError("Unclosed object in turns array")


def update_json_depth(
    line: str,
    *,
    depth: int,
    in_string: bool,
    escaped: bool,
) -> tuple[int, bool, bool]:
    for char in line:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
    return depth, in_string, escaped


def compact_turn(turn: dict[str, Any], *, memory_excerpt_chars: int) -> dict[str, Any]:
    compact = {
        "run_id": turn.get("run_id"),
        "created_at": turn.get("created_at"),
        "turn_index": turn.get("turn_index"),
        "probe": turn.get("probe"),
        "conversation_context_policy": turn.get("conversation_context_policy"),
        "source": compact_source(turn.get("source", {})),
        "input": turn.get("input", {}),
        "variants": {},
    }
    for variant_name, variant in sorted((turn.get("variants") or {}).items()):
        compact["variants"][variant_name] = compact_variant(
            variant,
            memory_excerpt_chars=memory_excerpt_chars,
        )
    return compact


def compact_source(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {
        key: source.get(key)
        for key in (
            "daily_messages_path",
            "scene_cards_path",
            "memory_conditions_path",
            "message_id",
            "tau",
            "scene_id",
            "turn_type",
        )
        if key in source
    }


def compact_variant(variant: Any, *, memory_excerpt_chars: int) -> dict[str, Any]:
    if not isinstance(variant, dict):
        return {}
    result = {
        "condition_id": variant.get("condition_id"),
        "assistant_answer": variant.get("assistant_answer"),
        "llm": variant.get("llm"),
        "memory_condition": variant.get("memory_condition"),
    }
    memory = (
        variant.get("memory_payload")
        or variant.get("memory_context")
        or variant.get("prompt_memory")
    )
    if isinstance(memory, str):
        result["memory_context"] = truncate(memory, memory_excerpt_chars)
    elif isinstance(memory, dict):
        result["memory_payload"] = compact_memory_payload(memory, memory_excerpt_chars)
    return {key: value for key, value in result.items() if value is not None}


def compact_memory_payload(memory: dict[str, Any], max_chars: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in (
        "condition_description",
        "readable_memory",
        "allowed_memory",
        "cannot_read",
        "forbidden_memory",
        "memory_boundary",
        "policy",
        "memory_context",
        "memory_text",
        "summary",
        "event_memory",
        "relational_anchor_memory",
        "payload",
    ):
        if key not in memory or memory[key] in (None, ""):
            continue
        value = memory[key]
        if isinstance(value, str):
            result[key] = truncate(value, max_chars)
        else:
            result[key] = truncate(json.dumps(value, ensure_ascii=False), max_chars)
    for key in (
        "condition_id",
        "memory_provider",
        "runtime_id",
        "payload_role",
        "memory_unit",
        "storage_backend",
        "enabled_memory_types",
        "source_detail_ids",
    ):
        if key in memory and memory[key] not in (None, ""):
            result[key] = compact_audit_value(memory[key], max_chars=max_chars)
    for key in ("retrieval", "memory_composition"):
        if isinstance(memory.get(key), dict):
            result[key] = compact_audit_value(memory[key], max_chars=max_chars)
    for key in ("m0_base_memory", "relational_overlay"):
        if isinstance(memory.get(key), dict):
            result[key] = compact_nested_memory_audit(memory[key], max_chars=max_chars)
    return result


def compact_nested_memory_audit(memory: dict[str, Any], *, max_chars: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in (
        "condition_id",
        "memory_provider",
        "runtime_id",
        "payload_role",
        "memory_unit",
        "storage_backend",
        "enabled_memory_types",
        "source_detail_ids",
        "retrieval",
    ):
        if key in memory and memory[key] not in (None, ""):
            result[key] = compact_audit_value(memory[key], max_chars=max_chars)
    return result


def compact_audit_value(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        return truncate(value, max_chars)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [compact_audit_value(item, max_chars=max_chars) for item in value[:50]]
    if isinstance(value, dict):
        return {
            str(key): compact_audit_value(item, max_chars=max_chars)
            for key, item in value.items()
            if item not in (None, "")
        }
    return truncate(json.dumps(value, ensure_ascii=False), max_chars)


def truncate(value: str, max_chars: int) -> str:
    text = str(value)
    return text if len(text) <= max_chars else text[:max_chars] + "..."


def get_turn_message_id(turn: dict[str, Any]) -> str:
    message_id = turn.get("source", {}).get("message_id")
    if message_id:
        return str(message_id)
    return str(turn.get("input", {}).get("message_id") or "")


def should_keep_message_id(message_id: str, keep_personas: tuple[str, ...]) -> bool:
    return any(message_id.startswith(f"{persona}_") for persona in keep_personas)


def write_indented_json(dst: TextIO, value: Any, *, indent_spaces: int) -> None:
    prefix = " " * indent_spaces
    rendered = json.dumps(value, ensure_ascii=False, indent=2)
    for index, line in enumerate(rendered.splitlines()):
        if index:
            dst.write("\n")
        dst.write(prefix + line)


def validate_json(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
