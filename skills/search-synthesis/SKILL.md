---
name: search-synthesis
description: >
  This skill should be used when the user needs "comprehensive search",
  "multi-source research", "deep web search", "search with social media",
  or wants results that combine web, content extraction, and X/Twitter
  discussion sources. Use when a single search provider would miss
  important context or when source cross-referencing matters.
version: 0.1.0
---

# Multi-Provider Search with Synthesis

Call the `mcp__search_synthesis__search` tool to fan out a query to three independent search providers and get a deduplicated, attributed synthesis.

## Providers

- **Gemini** — Google's grounded search. Returns a synthesized answer informed by Google search results with source URLs. Best for broad web coverage and recent information.
- **Exa** — Neural content retrieval. Returns actual page content with highlighted key passages. Best for deep technical content, documentation, and blog posts.
- **Grok** — X/Twitter search via xAI. Returns what people are saying on X about the topic. Best for real-time sentiment, community discussion, and trending opinions.

## Available Tools

### `mcp__search_synthesis__search`
Full pipeline: fans out to all three providers in parallel, then synthesizes results through Claude Haiku. Returns deduplicated findings grouped by cross-source (confirmed by multiple providers) and single-source items, with provider attribution and source URLs.

### `mcp__search_synthesis__search_provider`
Query a single provider without synthesis. Pass `provider` as `"gemini"`, `"exa"`, or `"grok"`. Use when only one perspective is needed (e.g., Grok for X/Twitter sentiment on a topic).

### `mcp__search_synthesis__get_raw_results`
Fan out to all providers but return raw, unsynthesized results. Use when you want to see each provider's unprocessed output before any deduplication or reformatting.

## When to Use This

- Research tasks requiring multiple perspectives
- Fact cross-referencing (items found by 2+ providers have higher confidence)
- Gathering community sentiment alongside factual web results
- Technical research where deep content extraction (Exa) complements broad search (Gemini)
- Topics where X/Twitter discussion adds valuable context

## When NOT to Use This

- Simple factual lookups with obvious answers (use built-in WebSearch)
- Fetching a specific URL's content (use WebFetch)
- Queries where only one provider is relevant (use `search_provider` instead)

## Output Format

The synthesized output follows this structure:

- **Cross-source** — Items found by multiple providers (higher confidence), tagged with which providers found them
- **X/Twitter only** — Items unique to Grok's X search
- **Web only** — Items unique to Gemini or Exa
- **Key context** — One-paragraph landscape summary

Every item includes provider attribution tags and source URLs. Google tracking redirects are automatically stripped.
