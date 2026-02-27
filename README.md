# Multi-Provider Search Plugin

A Cowork plugin that fans out search queries to Gemini, Exa, and Grok in parallel, then synthesizes results through Claude Haiku.

## Components

| Component | Path | Description |
|-----------|------|-------------|
| MCP Server | `servers/server.py` | Python MCP server exposing 3 search tools |
| Skill | `skills/search-synthesis/` | Tells Claude when to use multi-provider search |
| Command | `commands/search.md` | `/search` slash command |
| Hook | `hooks/hooks.json` | Redirects built-in WebSearch through the plugin |

## Setup

### Required Environment Variables

Set these in your shell or `.env` file:

```
GEMINI_API_KEY=...     # Google AI Studio
EXA_API_KEY=...        # Exa.ai
XAI_API_KEY=...        # xAI (Grok)
ANTHROPIC_API_KEY=...  # Anthropic (for Haiku synthesis)
```

### Install Dependencies

```bash
pip install -r servers/requirements.txt
```

## Usage

### `/search` Command

```
/search react server components
```

Runs the full pipeline: fans out to all 3 providers, synthesizes via Haiku, returns deduplicated results with source attribution.

### Automatic Trigger

The skill auto-activates when Claude detects queries needing "comprehensive search", "multi-source research", or "search with social media".

The WebSearch hook redirects Claude's built-in web search through the multi-provider pipeline.

### MCP Tools

| Tool | Description |
|------|-------------|
| `search` | Full fan-out + Haiku synthesis |
| `search_provider` | Single provider (gemini, exa, or grok) without synthesis |
| `get_raw_results` | All providers, raw results without synthesis |

## Architecture

```
search(query)
│
├─ ThreadPoolExecutor (3 threads)
│   ├─ Gemini  → google.genai grounded search
│   ├─ Exa     → neural content retrieval (5 results + highlights)
│   └─ Grok    → xAI x_search (X/Twitter posts)
│
├─ as_completed() → collect in finish order
│   (15s per-provider timeout, 20s overall)
│
└─ Claude Haiku synthesis
    ├─ Deduplication across sources
    ├─ Provider attribution tags
    ├─ URL sanitization
    └─ 600-word cap
```
