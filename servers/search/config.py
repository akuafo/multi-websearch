from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    enabled_providers: list[str] = field(default_factory=lambda: ["gemini", "exa", "grok"])
    per_provider_timeout: float = 15.0
    overall_timeout: float = 20.0
    synthesis_model: str = "claude-haiku-4-5-20251001"
    synthesis_max_tokens: int = 1024
    anthropic_api_key: str | None = None  # Falls back to ANTHROPIC_API_KEY env var
