---
description: Multi-provider search with synthesis
argument-hint: [query]
allowed-tools: ["mcp__search_synthesis__search"]
---

Call the search-synthesis MCP tool with the query: $ARGUMENTS

Present the synthesized results to the user. Clearly indicate:
- Which findings were confirmed by multiple sources (higher confidence)
- Which findings came from a single source (note the provider)
- All source URLs, with Google tracking redirects stripped

If the search returns errors from individual providers, note which
providers failed but still present results from the ones that succeeded.
