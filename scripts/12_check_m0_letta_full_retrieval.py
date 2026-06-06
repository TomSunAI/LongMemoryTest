#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from openai import OpenAI


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_memory_test.letta_memory import create_letta_client  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight checks for the M0 Letta full-retrieval baseline. "
            "This validates embedding support, Turbopuffer/message-search settings, "
            "Letta reachability, and optionally an existing M0 agent search API."
        )
    )
    parser.add_argument(
        "--env-file",
        action="append",
        type=Path,
        default=None,
        help=(
            "Env file to load. Defaults to .env.local and .env.letta.local if present. "
            "Later files override earlier files."
        ),
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help=(
            "Embedding model to test. Defaults to LETTA_EMBEDDING with an openai/ "
            "prefix stripped, or text-embedding-3-small."
        ),
    )
    parser.add_argument(
        "--m0-agent-id",
        default=os.getenv("LETTA_M0_AGENT_ID"),
        help="Optional existing M0 Letta agent id for direct message/passages search checks.",
    )
    parser.add_argument("--skip-embedding-call", action="store_true")
    parser.add_argument("--skip-letta-health", action="store_true")
    parser.add_argument("--skip-agent-search", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env_files(args.env_file)

    checks: list[dict[str, Any]] = []
    checks.append(_check_required_env("OPENAI_API_KEY"))
    checks.append(_check_required_env("OPENAI_API_BASE"))
    checks.append(_check_embedding_model_env(args.embedding_model))
    checks.extend(_check_turbopuffer_env())
    if not args.skip_embedding_call:
        checks.append(_check_embedding_call(args.embedding_model))
    if not args.skip_letta_health:
        checks.append(_check_letta_health())
    if args.m0_agent_id and not args.skip_agent_search:
        checks.extend(_check_agent_search(args.m0_agent_id))
    elif not args.skip_agent_search:
        checks.append(
            {
                "name": "m0_agent_search",
                "status": "skipped",
                "reason": "No --m0-agent-id or LETTA_M0_AGENT_ID provided.",
            }
        )

    ok = all(item["status"] in {"ok", "skipped"} for item in checks)
    payload = {
        "schema_version": "m0_letta_full_retrieval_preflight_v1",
        "status": "ok" if ok else "failed",
        "checks": checks,
        "full_retrieval_run_flags": [
            "--m0-letta-full-retrieval",
            "--m0-letta-search-limit 5",
        ],
        "required_runtime_env": {
            "M0_LETTA_ENABLE_MESSAGE_SEARCH": "1",
            "M0_LETTA_ENABLE_PASSAGE_SEARCH": "1",
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def _load_env_files(paths: list[Path] | None) -> None:
    resolved = paths or [REPO_ROOT / ".env.local", REPO_ROOT / ".env.letta.local"]
    for path in resolved:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'").strip('"')


def _check_required_env(key: str) -> dict[str, Any]:
    return {
        "name": f"env:{key}",
        "status": "ok" if os.getenv(key) else "failed",
        "present": bool(os.getenv(key)),
    }


def _check_embedding_model_env(model_override: str | None) -> dict[str, Any]:
    raw_model = model_override or os.getenv("LETTA_EMBEDDING")
    model = _embedding_model(model_override)
    if raw_model and raw_model.startswith("letta/") and not model_override:
        return {
            "name": "embedding_model",
            "status": "failed",
            "model_for_openai_call": model,
            "letta_embedding_env": os.getenv("LETTA_EMBEDDING"),
            "reason": (
                "Current LETTA_EMBEDDING is a Letta fallback embedding. "
                "Use an embedding-capable OpenAI-compatible model such as "
                "openai/text-embedding-3-small for full retrieval."
            ),
        }
    return {
        "name": "embedding_model",
        "status": "ok" if model else "failed",
        "model_for_openai_call": model,
        "letta_embedding_env": os.getenv("LETTA_EMBEDDING"),
    }


def _check_turbopuffer_env() -> list[dict[str, Any]]:
    use_tpuf = _truthy(os.getenv("USE_TPUF"))
    embed_all_messages = _truthy(os.getenv("EMBED_ALL_MESSAGES"))
    tpuf_key_present = bool(os.getenv("TPUF_API_KEY") or os.getenv("TURBOPUFFER_API_KEY"))
    return [
        {
            "name": "env:USE_TPUF",
            "status": "ok" if use_tpuf else "failed",
            "expected": "true",
            "present_value": _safe_value(os.getenv("USE_TPUF")),
        },
        {
            "name": "env:EMBED_ALL_MESSAGES",
            "status": "ok" if embed_all_messages else "failed",
            "expected": "true",
            "present_value": _safe_value(os.getenv("EMBED_ALL_MESSAGES")),
        },
        {
            "name": "env:TPUF_API_KEY_or_TURBOPUFFER_API_KEY",
            "status": "ok" if tpuf_key_present else "failed",
            "present": tpuf_key_present,
        },
    ]


def _check_embedding_call(model_override: str | None) -> dict[str, Any]:
    base_url = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY")
    model = _embedding_model(model_override)
    if not base_url or not api_key or not model:
        return {
            "name": "embedding_call",
            "status": "failed",
            "reason": "Missing OPENAI_API_BASE, OPENAI_API_KEY, or embedding model.",
        }
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(model=model, input="long memory embedding preflight")
        vector = response.data[0].embedding
    except Exception as exc:
        return {
            "name": "embedding_call",
            "status": "failed",
            "base_url": base_url,
            "model": model,
            "error": _sanitize_error(str(exc)),
        }
    return {
        "name": "embedding_call",
        "status": "ok",
        "base_url": base_url,
        "model": model,
        "embedding_dimension": len(vector),
    }


def _check_letta_health() -> dict[str, Any]:
    base_url = os.getenv("LETTA_BASE_URL", "http://127.0.0.1:8283").rstrip("/")
    try:
        with urllib.request.urlopen(base_url, timeout=10) as response:
            status = response.status
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "name": "letta_health",
            "status": "failed",
            "base_url": base_url,
            "error": str(exc),
        }
    return {
        "name": "letta_health",
        "status": "ok" if 200 <= status < 500 else "failed",
        "base_url": base_url,
        "http_status": status,
    }


def _check_agent_search(agent_id: str) -> list[dict[str, Any]]:
    client, _ = create_letta_client()
    checks: list[dict[str, Any]] = []
    try:
        response = client.messages.search(
            agent_id=agent_id,
            query="long memory preflight",
            limit=1,
            search_mode="hybrid",
        )
    except Exception as exc:
        checks.append(
            {
                "name": "letta_message_search",
                "status": "failed",
                "agent_id": agent_id,
                "error": _sanitize_error(str(exc)),
            }
        )
    else:
        checks.append(
            {
                "name": "letta_message_search",
                "status": "ok",
                "agent_id": agent_id,
                "result_shape": type(response).__name__,
            }
        )

    try:
        response = client.agents.passages.search(
            agent_id=agent_id,
            query="long memory preflight",
            top_k=1,
        )
    except Exception as exc:
        checks.append(
            {
                "name": "letta_passage_search",
                "status": "failed",
                "agent_id": agent_id,
                "error": _sanitize_error(str(exc)),
            }
        )
    else:
        checks.append(
            {
                "name": "letta_passage_search",
                "status": "ok",
                "agent_id": agent_id,
                "result_shape": type(response).__name__,
            }
        )
    return checks


def _embedding_model(model_override: str | None) -> str:
    model = model_override or os.getenv("LETTA_EMBEDDING") or "text-embedding-3-small"
    if model.startswith("openai/"):
        return model.split("/", 1)[1]
    return model


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_value(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > 32:
        return "<set>"
    return value


def _sanitize_error(text: str) -> str:
    for key in ["OPENAI_API_KEY", "TPUF_API_KEY", "TURBOPUFFER_API_KEY"]:
        value = os.getenv(key)
        if value:
            text = text.replace(value, "<secret>")
    return text[:1000]


if __name__ == "__main__":
    raise SystemExit(main())
