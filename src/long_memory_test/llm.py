from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


DEFAULT_POIXE_BASE_URL = "https://api.poixe.com/v1"
DEFAULT_POIXE_MODEL = "gpt-5.2"


class LLMConfigError(RuntimeError):
    """Raised when the configured LLM provider is missing required settings."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


def load_dotenv_local(path: Path | str = ".env.local") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def get_llm_config(provider: str | None = None) -> LLMConfig:
    load_dotenv_local()

    selected_provider = (provider or os.getenv("LLM_PROVIDER") or "poixe").lower()
    if selected_provider != "poixe":
        raise LLMConfigError(f"Unsupported LLM_PROVIDER: {selected_provider}")

    api_key = os.getenv("POIXE_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "POIXE_API_KEY is missing. Copy .env.example to .env.local and set it locally."
        )

    return LLMConfig(
        provider="poixe",
        api_key=api_key,
        base_url=os.getenv("POIXE_BASE_URL", DEFAULT_POIXE_BASE_URL),
        model=os.getenv("POIXE_MODEL", DEFAULT_POIXE_MODEL),
    )


def create_llm_client(config: LLMConfig | None = None) -> tuple[OpenAI, LLMConfig]:
    resolved = config or get_llm_config()
    return OpenAI(api_key=resolved.api_key, base_url=resolved.base_url), resolved
