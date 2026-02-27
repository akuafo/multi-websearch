# Multi-Provider Search — Cowork Plugin Build Plan

Use this document as context when starting your Claude Code session to build the plugin.

---

## What You're Building

A Cowork plugin that packages your existing multi-provider search module (Gemini + Exa + Grok → Claude Haiku synthesis) as an installable `.plugin` file. This replaces the current pattern of copying the module into individual Claude Code repos.

The plugin bundles four components: an MCP server (your Python search code), a skill (tells Claude when to use multi-provider search), a slash command (`/search`), and a hook (intercepts built-in WebSearch to redirect through your module).

---

## Repository Setup

Create a new standalone repository. The plugin is self-contained — it gets zipped into a `.plugin` file for distribution.

```
multi-provider-search/
├── .claude-plugin/
│   └── plugin.json              # Required manifest
├── servers/
│   └── server.py                # MCP stdio server wrapping your search module
│   └── requirements.txt         # Python dependencies
├── skills/
│   └── search-synthesis/
│       ├── SKILL.md             # When/how Claude should use multi-provider search
│       └── references/
│           └── provider-guide.md  # Detailed provider behavior docs
├── commands/
│   └── search.md                # /search slash command
├── hooks/
│   └── hooks.json               # PreToolUse hook to intercept WebSearch
├── .mcp.json                    # Registers the Python MCP server
└── README.md
```

### Key structural rules
- `.claude-plugin/plugin.json` is the ONLY file inside `.claude-plugin/`
- All component directories (`commands/`, `skills/`, `hooks/`) go at the plugin root
- Only create directories for components the plugin actually uses
- Kebab-case everything
- Use `${CLAUDE_PLUGIN_ROOT}` for all internal path references (never hardcode)
- Installed plugins cannot reference files outside their directory

---

## Phase 1: MCP Server (`servers/server.py`)

This is the main engineering work. Wrap your existing search module in the MCP stdio protocol using the `mcp` Python SDK.

### Minimal MCP server pattern

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("search-synthesis")

@mcp.tool()
async def search(query: str) -> str:
    """Fan out a search query to Gemini, Exa, and Grok, then synthesize results via Claude Haiku."""
    # Your existing search logic here:
    # 1. ThreadPoolExecutor fans out to 3 providers (15s per-provider, 20s ceiling)
    # 2. _safe_search() wraps each call for error isolation
    # 3. synthesize() sends all results to Claude Haiku
    # 4. Return the SearchResult synthesis
    ...

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Important stdio rules
- **Never use `print()` to stdout** — it corrupts the MCP protocol. Use `print(..., file=sys.stderr)` or `logging` instead
- Install via `pip install "mcp[cli]"` (or add to requirements.txt)
- The `FastMCP` class handles all protocol negotiation automatically
- Test with the MCP Inspector: `mcp dev servers/server.py`

### What to expose as tools

You have a choice here. The simplest approach is one tool:

- `search(query: str) -> str` — runs the full fan-out + synthesis pipeline, returns the synthesized result

Or you could expose more granular tools if you want Claude to sometimes query individual providers:

- `search(query: str) -> str` — full pipeline
- `search_provider(query: str, provider: str) -> str` — single provider
- `get_raw_results(query: str) -> str` — full pipeline but returns raw per-provider results without synthesis

Start with just `search()`. You can add the others later.

### Porting your existing code

Your current module structure (`src/search/`) can be copied into `servers/` largely as-is. The MCP server file (`server.py`) just needs to import and call your existing `search()` function. The main changes:

1. Make `search()` async-compatible (wrap the ThreadPoolExecutor in `asyncio.to_thread` or use `loop.run_in_executor`)
2. Return strings instead of `SearchResult` objects (serialize the synthesis + sources)
3. Read API keys from environment variables (which come from `.mcp.json` env config)

---

## Phase 2: MCP Configuration (`.mcp.json`)

Registers your server with Claude. Environment variables use `${VAR_NAME}` syntax.

```json
{
  "mcpServers": {
    "search-synthesis": {
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/servers/server.py"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "EXA_API_KEY": "${EXA_API_KEY}",
        "XAI_API_KEY": "${XAI_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

MCP tool naming convention: tools from this server will appear as `mcp__search_synthesis__search` in Claude's tool list. This matters for the hook matcher and command `allowed-tools`.

---

## Phase 3: Skill (`skills/search-synthesis/SKILL.md`)

Tells Claude when and how to use multi-provider search instead of built-in WebSearch.

### Frontmatter rules
- `description` must be third-person: "This skill should be used when..."
- Include specific trigger phrases in quotes
- Keep body under 3,000 words (ideally 1,500–2,000)
- Move detailed content to `references/`

```yaml
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
```

### Body content should cover
- What the three providers find (Gemini = broad web, Exa = deep content/passages, Grok = X/Twitter)
- How the synthesis layer works (cross-source vs single-source grouping, source tagging)
- When to prefer this over built-in WebSearch (research tasks, opinion gathering, fact cross-referencing)
- When NOT to use it (simple factual lookups, single-URL fetches)
- How to interpret the output format
- Write in imperative form: "Call the search-synthesis tool" not "You should call"

### Progressive disclosure
1. **Metadata** (always loaded): name + description (~100 words)
2. **SKILL.md body** (loaded when triggered): core usage guidance
3. **references/provider-guide.md** (loaded on demand): detailed provider behavior, timeout strategies, error handling patterns

---

## Phase 4: Command (`commands/search.md`)

Gives users a `/search` slash command.

```markdown
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
```

### Command syntax reference
- `$ARGUMENTS` — all arguments as a single string
- `$1`, `$2`, `$3` — positional arguments
- `@path` — includes file contents in command context
- `` !`command` `` — executes bash inline for dynamic context
- Commands are instructions FOR Claude, not documentation for users

---

## Phase 5: Hook (`hooks/hooks.json`)

Replaces your current `redirect-websearch.sh`. Intercepts Claude's built-in WebSearch tool and redirects through your multi-provider module.

```json
{
  "PreToolUse": [
    {
      "matcher": "WebSearch",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "The user has the search-synthesis plugin installed which provides superior multi-provider search. Instead of using the built-in WebSearch tool, use the mcp__search_synthesis__search tool with the same query. This fans out to Gemini, Exa, and Grok simultaneously and synthesizes the results.",
          "timeout": 30
        }
      ]
    }
  ]
}
```

### Hook type options
- **Prompt-based** (used above): sends prompt to Claude for evaluation. Good for nuanced decisions. Supported on: PreToolUse, Stop, SubagentStop, UserPromptSubmit
- **Command-based**: runs a shell script, returns JSON `{"decision": "block"|"approve"|"ask_user", "reason": "..."}`. Good for deterministic checks.

### Available hook events
| Event | When it fires |
|-------|--------------|
| `PreToolUse` | Before a tool call executes |
| `PostToolUse` | After a tool call completes |
| `Stop` | When Claude finishes a response |
| `SubagentStop` | When a subagent finishes |
| `SessionStart` | When a session begins |
| `UserPromptSubmit` | When the user sends a message |

MCP tools follow the naming pattern `mcp__<server>__<tool>` in hook matchers.

---

## Phase 6: Manifest & README

### `.claude-plugin/plugin.json`

```json
{
  "name": "multi-provider-search",
  "version": "0.1.0",
  "description": "Fan-out search across Gemini, Exa, and Grok with Claude Haiku synthesis",
  "author": {
    "name": "Matt"
  },
  "keywords": ["search", "research", "multi-provider", "synthesis"]
}
```

Name rules: kebab-case, lowercase with hyphens, no spaces or special characters.

### README.md should document
1. Overview — what the plugin does
2. Components — list of commands, skills, hooks, MCP servers
3. Setup — required environment variables (GEMINI_API_KEY, EXA_API_KEY, XAI_API_KEY, ANTHROPIC_API_KEY)
4. Usage — how to use `/search` and when the skill auto-triggers
5. Architecture — the fan-out/synthesis diagram from your existing docs

---

## Phase 7: Package & Validate

```bash
# Validate the plugin structure
claude plugin validate .claude-plugin/plugin.json

# Package as .plugin file (just a zip)
cd multi-provider-search
zip -r ../multi-provider-search.plugin . -x "*.DS_Store" -x "__pycache__/*" -x "*.pyc"
```

The `.plugin` file renders as a rich preview in Cowork with an install button.

---

## Build Order (suggested for Claude Code session)

1. **Scaffold the directory structure** — create all directories and empty files
2. **Port the search module** — copy your existing `src/search/` code into `servers/`, adapt imports
3. **Write `server.py`** — MCP wrapper using FastMCP, expose the `search()` tool
4. **Write `.mcp.json`** — register the server with env var slots
5. **Write `SKILL.md`** — skill frontmatter + body explaining when/how to use
6. **Write `commands/search.md`** — the `/search` slash command
7. **Write `hooks/hooks.json`** — PreToolUse hook to intercept WebSearch
8. **Write `plugin.json`** — the manifest
9. **Write `README.md`** — setup and usage docs
10. **Test** — `mcp dev servers/server.py` to verify the MCP server works
11. **Validate** — `claude plugin validate .claude-plugin/plugin.json`
12. **Package** — zip into `.plugin`

---

## Source Documentation

### Cowork Plugin System
- [Create Plugins — Claude Code Docs](https://docs.claude.com/en/docs/claude-code/plugins) — plugin creation guide, directory structure, common mistakes
- [Plugins Reference — Claude Code Docs](https://docs.claude.com/en/docs/claude-code/plugins-reference) — complete technical specs, `${CLAUDE_PLUGIN_ROOT}`, MCP inline config
- [Hooks Reference — Claude Code Docs](https://docs.claude.com/en/docs/claude-code/hooks) — hook types, event list, matcher patterns, MCP tool naming
- [Hooks Guide — Claude Code Docs](https://docs.claude.com/en/docs/claude-code/hooks-guide) — practical hook examples, prompt vs command hooks
- [MCP in Claude Code — Claude Code Docs](https://docs.claude.com/en/docs/claude-code/mcp) — MCP server scopes, plugin-bundled servers, transport types

### MCP Python SDK
- [MCP Python SDK — GitHub](https://github.com/modelcontextprotocol/python-sdk) — official SDK repo
- [Build an MCP Server — modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/build-server) — official tutorial (FastMCP, stdio transport)
- [MCP Python SDK Docs](https://modelcontextprotocol.github.io/python-sdk/) — full API reference
- [mcp on PyPI](https://pypi.org/project/mcp/) — package installation (`pip install "mcp[cli]"`)

### Provider APIs (for your existing code)
- [google.genai SDK](https://ai.google.dev/gemini-api/docs) — Gemini with GoogleSearch tool
- [exa_py](https://docs.exa.ai/) — Exa search and content retrieval
- [x.ai API](https://docs.x.ai/) — Grok with x_search tool
