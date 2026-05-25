<div align="center">

# HubSeek

**Natural language GitHub project finder powered by AI**

Describe what you need in plain words. HubSeek searches GitHub, analyzes results with AI, and delivers curated recommendations with Chinese summaries and pros/cons.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## Features

- **Natural Language Search** -- Describe your need in Chinese or English; AI generates optimal GitHub search keywords
- **Smart Analysis** -- AI evaluates each project and generates Chinese summaries with pros/cons
- **Concurrent Fetching** -- Async httpx for parallel repo detail retrieval, fast and efficient
- **Local Caching** -- 24-hour SQLite cache via diskcache, saves API quota
- **Structured Output** -- Forced JSON mode ensures stable, parseable AI responses
- **Interactive Browser** -- After results display, open any project in your browser with one keypress
- **Graceful Errors** -- Friendly Chinese error messages instead of Python tracebacks

## Quick Start

### Install

```bash
# Clone the repo
git clone https://github.com/yourname/hubseek.git
cd hubseek

# Install in editable mode
pip install -e .

# Now `hubseek` is available globally
hubseek --version
```

### Configure

HubSeek needs two API keys:

| Key | Purpose | Where to get |
|-----|---------|-------------|
| `github_token` | GitHub API access (raises rate limit from 10 to 30 req/min) | [github.com/settings/tokens](https://github.com/settings/tokens) |
| `openai_api_key` | AI analysis (any OpenAI-compatible API works) | Your LLM provider |

**Option A: Config file (recommended)**

```bash
# Create default config
hubseek config:init

# Edit the file at:
#   Windows: %USERPROFILE%\.github-finder\config.json
#   macOS/Linux: ~/.github-finder/config.json
```

Config file format:

```json
{
  "openai_api_key": "sk-xxx",
  "openai_base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "github_token": "ghp_xxx",
  "max_results": 20,
  "final_recommendations": 5,
  "cache_ttl_hours": 24,
  "readme_max_chars": 2500
}
```

**Option B: Environment variables (higher priority)**

```bash
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
export GITHUB_TOKEN="ghp_xxx"
```

### Use

```bash
# Basic search
hubseek search "markdown to resume converter"

# Limit to 3 results
hubseek search "Python web framework" --results 3

# Chinese queries work naturally
hubseek search "法律判决预测工具"

# With custom config file
hubseek search "React state management" -c /path/to/config.json
```

## Example Output

```
$ hubseek search "能将 markdown 转换为简历的工具"

  Search Query: 能将 markdown 转换为简历的工具
  ──────────────────────────────────────────

  AI Generating search strategy...

  Search Strategy:
    Keywords: markdown, resume
    Topics: (none)
    Language: (any)

  Searching... Found 20 candidates
  Source: Repositories (20 results)
  Fetching repo details concurrently...
  Fetched 20 project details
  AI Analyzing...

  ┌ Top 5 Recommendations ────────────────────────────────┐
  │                                                        │
  └────────────────────────────────────────────────────────┘

  ┌ #1 Awesome-CV | Stars: 22,345 | Updated: 2025-03-10 ─┐
  │                                                        │
  │  LaTeX/Markdown resume template with beautiful layout   │
  │                                                        │
  │  Pros:                                                 │
  │    + Professional typography                           │
  │    + Active community                                  │
  │    + Multiple templates                                │
  │                                                        │
  │  Cons:                                                 │
  │    - Requires LaTeX environment                        │
  │    - Complex setup for beginners                       │
  │                                                        │
  │  Verdict: Best choice for professional output          │
  └────────────────────────────────────────────────────────┘

  Open in browser? Enter number (1-5) or 0 to exit: 1
  Opening https://github.com/posquit0/Awesome-CV...
```

## CLI Reference

```
hubseek [COMMAND]

Commands:
  search        Search GitHub projects with natural language
  config:init   Initialize config file
  config:show   Show current config
  cache:clear   Clear all cache
  cache:stats   Show cache statistics

Options:
  --version     Show version
  --help        Show help
```

### `hubseek search`

```
hubseek search <QUERY> [OPTIONS]

Arguments:
  QUERY              Natural language description of what you need

Options:
  -c, --config PATH  Custom config file path
  -n, --results INT  Number of recommendations (default: 5)
```

## How It Works

```
User Input (natural language)
        |
        v
  [1] AI generates search strategy (keywords, topics)
        |
        v
  [2] GitHub API search (repos + code fallback)
        |
        v
  [3] Concurrent fetch of repo details + README
        |
        v
  [4] AI analyzes candidates, ranks top 3-5
        |
        v
  [5] Rich terminal output with interactive browser open
```

## Tech Stack

| Library | Purpose |
|---------|---------|
| [httpx](https://github.com/encode/httpx) | Async HTTP client for GitHub API |
| [openai](https://github.com/openai/openai-python) | OpenAI-compatible API client |
| [diskcache](https://github.com/grantjenks/python-diskcache) | SQLite-based local caching |
| [click](https://github.com/pallets/click) | CLI framework |
| [rich](https://github.com/Textualize/rich) | Beautiful terminal output |

## Advanced: Use with Non-OpenAI LLMs

HubSeek works with any OpenAI-compatible API. Just change `openai_base_url` and `model`:

```json
{
  "openai_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat"
}
```

```json
{
  "openai_base_url": "https://api.groq.com/openai/v1",
  "model": "llama-3.3-70b-versatile"
}
```

## License

MIT
