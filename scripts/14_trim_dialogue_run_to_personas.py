#!/usr/bin/env python3
"""Trim a dialogue-condition run directory to selected complete personas."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


MESSAGE_ID_RE = re.compile(r"\b(P\d{4})_D\d{2}_[MP]\d{3}\b")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trim large dialogue run outputs to selected persona prefixes."
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--personas", required=True, help="Comma-separated ids, e.g. P0001,P0002")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Replace files in place after writing validated .tmp files.",
    )
    args = parser.parse_args()

    keep_personas = tuple(
        item.strip() for item in args.personas.split(",") if item.strip()
    )
    if not keep_personas:
        raise SystemExit("--personas must contain at least one persona id")

    run_dir = args.run_dir
    responses_path = run_dir / "responses_by_condition.json"
    log_path = run_dir / "conversation_log.json"

    responses_stats = trim_turns_file(
        responses_path,
        keep_personas=keep_personas,
        include_checkpoint=True,
        in_place=args.in_place,
    )
    log_stats = trim_turns_file(
        log_path,
        keep_personas=keep_personas,
        include_checkpoint=False,
        in_place=args.in_place,
    )
    runtime_stats = trim_memory_runtimes(
        run_dir / "memory_runtimes",
        keep_personas=keep_personas,
        in_place=args.in_place,
    )
    config_stats = update_run_config(
        run_dir / "run_config.json",
        expected_turns=responses_stats["kept_turns"],
        keep_personas=keep_personas,
        in_place=args.in_place,
    )
    status_stats = update_supervisor_status(
        run_dir / "dialogue_supervisor_status.json",
        keep_personas=keep_personas,
        in_place=args.in_place,
    )

    summary = {
        "run_dir": str(run_dir),
        "personas": list(keep_personas),
        "responses_by_condition": responses_stats,
        "conversation_log": log_stats,
        "memory_runtimes": runtime_stats,
        "run_config": config_stats,
        "dialogue_supervisor_status": status_stats,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def trim_turns_file(
    path: Path,
    *,
    keep_personas: tuple[str, ...],
    include_checkpoint: bool,
    in_place: bool,
) -> dict[str, Any]:
    tmp_path = path.with_name(f"{path.name}.trim.tmp")
    kept_turns = 0
    seen_turns = 0
    kept_message_ids: list[str] = []
    input_hashes: dict[str, str] = {}
    conditions_by_message_id: dict[str, list[str]] = {}

    with path.open("r", encoding="utf-8") as src:
        header = read_header_until_turns(src)
        header = filter_header(header, keep_personas)

        with tmp_path.open("w", encoding="utf-8") as dst:
            dst.write("{\n")
            first_key = True
            for key, value in header.items():
                write_top_level_key(dst, key, value, first=first_key)
                first_key = False

            if not first_key:
                dst.write(",\n")
            dst.write('  "turns": [')

            first_turn = True
            tail_text = ""
            for item in iter_turn_objects(src):
                if isinstance(item, ArrayEnd):
                    tail_text = src.read()
                    break

                seen_turns += 1
                turn = item
                message_id = get_turn_message_id(turn)
                if not should_keep_message_id(message_id, keep_personas):
                    continue

                if first_turn:
                    dst.write("\n")
                else:
                    dst.write(",\n")
                write_indented_json(dst, turn, indent_spaces=4)
                first_turn = False

                kept_turns += 1
                kept_message_ids.append(message_id)
                input_hash = turn.get("input", {}).get("input_hash")
                if input_hash:
                    input_hashes[message_id] = str(input_hash)
                variants = turn.get("variants") or {}
                conditions_by_message_id[message_id] = sorted(str(k) for k in variants)

            if first_turn:
                dst.write("\n")
            else:
                dst.write("\n")
            dst.write("  ]")

            tail = parse_tail_object(tail_text)
            if include_checkpoint:
                tail = update_response_tail(
                    tail,
                    kept_message_ids=kept_message_ids,
                    input_hashes=input_hashes,
                    conditions_by_message_id=conditions_by_message_id,
                )

            for key, value in tail.items():
                dst.write(",\n")
                write_top_level_key(dst, key, value, first=True)
            dst.write("\n}\n")

    if in_place:
        tmp_path.replace(path)

    return {
        "path": str(path),
        "seen_turns": seen_turns,
        "kept_turns": kept_turns,
        "last_kept_message_id": kept_message_ids[-1] if kept_message_ids else None,
        "tmp_path": None if in_place else str(tmp_path),
    }


def read_header_until_turns(src: TextIO) -> dict[str, Any]:
    lines: list[str] = []
    for line in src:
        if line.lstrip().startswith('"turns"'):
            text = "".join(lines) + '  "turns": []\n}\n'
            data = json.loads(text)
            data.pop("turns", None)
            return data
        lines.append(line)
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


def parse_tail_object(tail_text: str) -> dict[str, Any]:
    stripped = tail_text.strip()
    if not stripped or stripped == "}":
        return {}
    return json.loads("{\n" + tail_text)


def filter_header(data: dict[str, Any], keep_personas: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(data.get("message_ids"), list):
        data["message_ids"] = [
            message_id
            for message_id in data["message_ids"]
            if should_keep_message_id(str(message_id), keep_personas)
        ]
    return data


def update_response_tail(
    tail: dict[str, Any],
    *,
    kept_message_ids: list[str],
    input_hashes: dict[str, str],
    conditions_by_message_id: dict[str, list[str]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    expected_turns = len(kept_message_ids)

    tail["expected_turns"] = expected_turns
    tail["completed_message_ids"] = kept_message_ids
    tail["completed_input_hashes_by_message_id"] = input_hashes
    tail["completed_conditions_by_message_id"] = conditions_by_message_id

    run_config = tail.get("run_config")
    if isinstance(run_config, dict):
        run_config["expected_turns"] = expected_turns
        run_config["trimmed_to_personas"] = list(
            dict.fromkeys(message_id.split("_", 1)[0] for message_id in kept_message_ids)
        )
        run_config["trimmed_at"] = now

    tail["checkpoint"] = {
        "status": "complete",
        "updated_at": now,
        "completed_turns": expected_turns,
        "expected_turns": expected_turns,
        "last_message_id": kept_message_ids[-1] if kept_message_ids else None,
    }
    return tail


def write_top_level_key(dst: TextIO, key: str, value: Any, *, first: bool) -> None:
    if not first:
        dst.write(",\n")
    rendered = json.dumps({key: value}, ensure_ascii=False, indent=2)
    inner = rendered[2:-2]
    dst.write(f"  {inner}")


def write_indented_json(dst: TextIO, value: Any, *, indent_spaces: int) -> None:
    prefix = " " * indent_spaces
    rendered = json.dumps(value, ensure_ascii=False, indent=2)
    for index, line in enumerate(rendered.splitlines()):
        if index:
            dst.write("\n")
        dst.write(prefix + line)


def get_turn_message_id(turn: dict[str, Any]) -> str:
    message_id = turn.get("source", {}).get("message_id")
    if message_id:
        return str(message_id)
    message_id = turn.get("input", {}).get("message_id")
    return str(message_id or "")


def should_keep_message_id(message_id: str, keep_personas: tuple[str, ...]) -> bool:
    return any(message_id.startswith(f"{persona}_") for persona in keep_personas)


def trim_memory_runtimes(
    path: Path,
    *,
    keep_personas: tuple[str, ...],
    in_place: bool,
) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}

    stats: dict[str, Any] = {"path": str(path), "files": {}}
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix == ".jsonl":
            stats["files"][str(file_path)] = trim_jsonl_file(
                file_path,
                keep_personas=keep_personas,
                in_place=in_place,
            )
        elif file_path.name == "snapshot.json":
            stats["files"][str(file_path)] = trim_snapshot_file(
                file_path,
                keep_personas=keep_personas,
                in_place=in_place,
            )
    return stats


def trim_jsonl_file(
    path: Path,
    *,
    keep_personas: tuple[str, ...],
    in_place: bool,
) -> dict[str, Any]:
    tmp_path = path.with_name(f"{path.name}.trim.tmp")
    seen = 0
    kept = 0
    with path.open("r", encoding="utf-8") as src, tmp_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            seen += 1
            item = json.loads(line)
            if not object_belongs_to_kept_personas(item, keep_personas):
                continue
            dst.write(json.dumps(item, ensure_ascii=False) + "\n")
            kept += 1

    validate_jsonl_file(tmp_path)
    if in_place:
        tmp_path.replace(path)
    return {"seen": seen, "kept": kept, "tmp_path": None if in_place else str(tmp_path)}


def trim_snapshot_file(
    path: Path,
    *,
    keep_personas: tuple[str, ...],
    in_place: bool,
) -> dict[str, Any]:
    tmp_path = path.with_name(f"{path.name}.trim.tmp")
    data = json.loads(path.read_text(encoding="utf-8"))
    memories = data.get("memories")
    seen = len(memories) if isinstance(memories, list) else 0
    if isinstance(memories, list):
        data["memories"] = [
            item for item in memories if object_belongs_to_kept_personas(item, keep_personas)
        ]
        data["memory_count"] = len(data["memories"])
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_json_file(tmp_path)
    if in_place:
        tmp_path.replace(path)
    return {
        "seen": seen,
        "kept": data.get("memory_count"),
        "tmp_path": None if in_place else str(tmp_path),
    }


def object_belongs_to_kept_personas(item: Any, keep_personas: tuple[str, ...]) -> bool:
    message_ids = sorted(extract_message_ids(item))
    if message_ids:
        return all(should_keep_message_id(message_id, keep_personas) for message_id in message_ids)

    if isinstance(item, dict) and "message_id" in item:
        return should_keep_message_id(str(item["message_id"]), keep_personas)

    return True


def extract_message_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        found.update(match.group(0) for match in MESSAGE_ID_RE.finditer(value))
    elif isinstance(value, list):
        for item in value:
            found.update(extract_message_ids(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.update(extract_message_ids(item))
    return found


def update_run_config(
    path: Path,
    *,
    expected_turns: int,
    keep_personas: tuple[str, ...],
    in_place: bool,
) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    tmp_path = path.with_name(f"{path.name}.trim.tmp")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["expected_turns"] = expected_turns
    data["trimmed_to_personas"] = list(keep_personas)
    data["trimmed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_json_file(tmp_path)
    if in_place:
        tmp_path.replace(path)
    return {"path": str(path), "expected_turns": expected_turns}


def update_supervisor_status(
    path: Path,
    *,
    keep_personas: tuple[str, ...],
    in_place: bool,
) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    tmp_path = path.with_name(f"{path.name}.trim.tmp")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "stopped_by_user_trimmed"
    data["stopped_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data["trimmed_to_personas"] = list(keep_personas)
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validate_json_file(tmp_path)
    if in_place:
        tmp_path.replace(path)
    return {"path": str(path), "status": data["status"]}


def validate_json_file(path: Path) -> None:
    depth = 0
    in_string = False
    escaped = False
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            depth, in_string, escaped = update_json_depth(
                line,
                depth=depth,
                in_string=in_string,
                escaped=escaped,
            )
            if depth < 0:
                raise ValueError(f"JSON object depth went negative: {path}")
    if depth != 0 or in_string or escaped:
        raise ValueError(f"JSON text is not balanced: {path}")


def validate_jsonl_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                json.loads(line)


if __name__ == "__main__":
    raise SystemExit(main())
