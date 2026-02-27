# Provider Technical Guide

## Gemini (Google Grounded Search)

Uses the `google.genai` SDK with `GoogleSearch` as a tool attachment. Gemini generates a natural language response informed by Google search results, then exposes source URLs in `grounding_metadata.grounding_chunks`.

- **Model:** `gemini-2.5-flash`
- **Output:** Synthesized text response + grounding source URLs
- **Strengths:** Broad web coverage, recent news, general knowledge
- **Limitations:** Sources are what Gemini chose to ground on, not a raw search result list

### Source extraction

Sources come from structured metadata (`candidate.grounding_metadata.grounding_chunks`), accessed via defensive `getattr()` chains since fields may be absent.

## Exa (Neural Content Retrieval)

Uses the `exa_py` SDK's `search_and_contents()` which combines search + full content retrieval in one call.

- **Parameters:** `type="auto"` (Exa picks keyword vs. neural), `num_results=5`, `text.max_characters=1000`, `highlights=True`
- **Output:** Actual page content with highlighted key passages + title/URL pairs
- **Strengths:** Deep content extraction, technical documentation, blog posts
- **Limitations:** Smaller index than Google, may miss very recent content

### Content formatting

Prefers `highlights` (key passage extraction) over raw `text`. Falls back to truncated text (500 chars) when highlights aren't available.

## Grok (X/Twitter via xAI)

Uses raw `httpx.post()` to xAI's responses API with `x_search` tool type. The query is reframed as "What are people saying on X/Twitter about: {query}" to prime the x_search tool.

- **Model:** `grok-4-1-fast-non-reasoning`
- **API:** `https://api.x.ai/v1/responses`
- **Auth:** Bearer token via `XAI_API_KEY`
- **Output:** Natural language response with embedded tweet URLs
- **Strengths:** Real-time X/Twitter content, community sentiment, trending discussion
- **Limitations:** Results skewed toward X platform; URL extraction is regex-based

### Source extraction

Unlike Gemini/Exa which have structured source metadata, Grok embeds tweet URLs directly in response text. URLs matching `https?://(?:x\.com|twitter\.com)/...` are extracted via regex.

## Timeout Strategy

The runner uses a two-layer timeout:

- **Per-provider timeout:** 15 seconds — applied to each `future.result()` call
- **Overall timeout:** 20 seconds — applied to the `as_completed()` iterator

Results are collected in completion order (fastest first). If the overall timeout fires, any completed-but-uncollected results are scavenged, and in-flight providers are cancelled with an error result.

## Error Handling

Each provider is wrapped in `_safe_search()` which catches all exceptions and returns a `ProviderResult` with the `error` field set. The synthesis layer skips errored providers gracefully — partial results (e.g., 2 of 3 providers) are still synthesized.

If all providers fail, the synthesis is skipped entirely and an error summary is returned.

If the Anthropic API call for synthesis fails, raw provider results are concatenated as a fallback with a `(Synthesis failed: ...)` note.
