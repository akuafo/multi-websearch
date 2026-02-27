from __future__ import annotations

import asyncio
import logging
import os
import sys

# Ensure the search package is importable from this directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from search import SearchResult, search as run_search
from search.config import SearchConfig
from search.providers import ProviderResult
from search.runner import run_parallel_search

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("search-synthesis")

mcp = FastMCP("search-synthesis")


# ---------------------------------------------------------------------------
# Formatters — serialize dataclasses to readable text for MCP tool responses
# ---------------------------------------------------------------------------

def _format_provider_result(result: ProviderResult) -> str:
    """Format a single provider result."""
    parts = [f"## {result.provider.upper()}"]
    if result.error:
        parts.append(f"**Error:** {result.error}")
    else:
        parts.append(result.content)
        if result.sources:
            parts.append("\n**Sources:**")
            for src in result.sources:
                title = src.get("title", "Link")
                url = src.get("url", "")
                parts.append(f"- [{title}]({url})")
    return "\n".join(parts)


def _format_raw_results(query: str, results: list[ProviderResult]) -> str:
    """Format all provider results without synthesis."""
    parts = [f"# Raw results for: {query}\n"]
    for result in results:
        parts.append(_format_provider_result(result))
        parts.append("")
    errors = [f"{r.provider}: {r.error}" for r in results if r.error]
    if errors:
        parts.append(f"**Errors:** {'; '.join(errors)}")
    return "\n".join(parts)


def _format_search_result(result: SearchResult) -> str:
    """Format a full search result (synthesis + metadata)."""
    parts = [result.synthesis, ""]

    # Append provider source lists
    all_sources = []
    for pr in result.provider_results:
        for src in pr.sources:
            title = src.get("title", "Link")
            url = src.get("url", "")
            all_sources.append(f"- [{title}]({url}) [{pr.provider}]")
    if all_sources:
        parts.append("## All sources")
        parts.extend(all_sources)

    if result.errors:
        parts.append(f"\n**Provider errors:** {'; '.join(result.errors)}")

    parts.append(f"\n_Model: {result.model} | Tokens: {result.tokens_in} in / {result.tokens_out} out_")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def search(query: str) -> str:
    """Fan out a search query to Gemini, Exa, and Grok, then synthesize results via Claude Haiku.

    Returns a synthesis with cross-source deduplication, provider attribution, and source URLs.
    Use this for comprehensive research that benefits from multiple search perspectives.
    """
    logger.info("search() called with query: %s", query)
    result = await asyncio.to_thread(run_search, query)
    return _format_search_result(result)


@mcp.tool()
async def search_provider(query: str, provider: str) -> str:
    """Search using a single provider without synthesis.

    Args:
        query: The search query.
        provider: One of "gemini", "exa", or "grok".

    Returns raw results from the specified provider only. Use when you need
    results from a specific source (e.g., Grok for X/Twitter sentiment).
    """
    valid = ("gemini", "exa", "grok")
    if provider not in valid:
        return f"Invalid provider '{provider}'. Must be one of: {', '.join(valid)}"

    logger.info("search_provider() called: provider=%s, query=%s", provider, query)
    config = SearchConfig(enabled_providers=[provider])
    results = await asyncio.to_thread(run_parallel_search, query, config)

    if not results:
        return f"No results from {provider}."
    return _format_provider_result(results[0])


@mcp.tool()
async def get_raw_results(query: str) -> str:
    """Fan out a search query to all providers but return raw results without synthesis.

    Returns unprocessed results from Gemini, Exa, and Grok separately.
    Use when you want to see each provider's raw output before any deduplication.
    """
    logger.info("get_raw_results() called with query: %s", query)
    results = await asyncio.to_thread(run_parallel_search, query)
    return _format_raw_results(query, results)


if __name__ == "__main__":
    mcp.run(transport="stdio")
