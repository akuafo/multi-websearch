from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import SearchConfig
from .providers import ProviderResult, SearchProvider


def _safe_search(provider: SearchProvider, query: str) -> ProviderResult:
    """Execute a provider search, catching all exceptions."""
    try:
        return provider.search(query)
    except Exception as e:
        return ProviderResult(
            provider=provider.name,
            query=query,
            content="",
            error=str(e),
        )


def _get_provider(name: str) -> SearchProvider:
    """Instantiate a provider by name."""
    if name == "gemini":
        from .providers.gemini import GeminiProvider

        return GeminiProvider()
    elif name == "exa":
        from .providers.exa import ExaProvider

        return ExaProvider()
    elif name == "grok":
        from .providers.grok import GrokProvider

        return GrokProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")


def run_parallel_search(
    query: str, config: SearchConfig | None = None
) -> list[ProviderResult]:
    """Run search across all enabled providers in parallel."""
    if config is None:
        config = SearchConfig()

    providers = []
    for name in config.enabled_providers:
        try:
            providers.append(_get_provider(name))
        except ValueError as e:
            providers.append(None)

    results: list[ProviderResult] = []

    executor = ThreadPoolExecutor(max_workers=max(len(providers), 1))
    future_to_provider = {}
    for provider in providers:
        if provider is not None:
            future = executor.submit(_safe_search, provider, query)
            future_to_provider[future] = provider.name

    try:
        for future in as_completed(
            future_to_provider, timeout=config.overall_timeout
        ):
            try:
                result = future.result(timeout=config.per_provider_timeout)
                results.append(result)
            except Exception as e:
                provider_name = future_to_provider[future]
                results.append(
                    ProviderResult(
                        provider=provider_name,
                        query=query,
                        content="",
                        error=f"Timeout or error: {e}",
                    )
                )
    except TimeoutError:
        # Overall timeout exceeded — collect whatever we have
        for future, name in future_to_provider.items():
            if future.done() and not any(r.provider == name for r in results):
                try:
                    results.append(future.result(timeout=0))
                except Exception:
                    pass
            elif not future.done():
                future.cancel()
                results.append(
                    ProviderResult(
                        provider=name,
                        query=query,
                        content="",
                        error="Provider timed out",
                    )
                )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return results
