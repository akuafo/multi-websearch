from __future__ import annotations

from dataclasses import dataclass, field

from .config import SearchConfig
from .providers import ProviderResult
from .runner import run_parallel_search
from .synthesizer import synthesize


@dataclass
class SearchResult:
    query: str
    synthesis: str
    provider_results: list[ProviderResult] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""
    errors: list[str] = field(default_factory=list)


def search(query: str, config: SearchConfig | None = None) -> SearchResult:
    """Main entry point: search across providers and synthesize results."""
    if config is None:
        config = SearchConfig()

    # Run parallel search across providers
    provider_results = run_parallel_search(query, config)

    # Collect errors
    errors = [
        f"{r.provider}: {r.error}" for r in provider_results if r.error
    ]

    # Synthesize results
    synthesis, tokens_in, tokens_out, model = synthesize(
        query, provider_results, config
    )

    return SearchResult(
        query=query,
        synthesis=synthesis,
        provider_results=provider_results,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
        errors=errors,
    )


__all__ = ["search", "SearchResult", "SearchConfig", "ProviderResult"]
