# arXiv MCP Server

Search and discover scientific papers from [arXiv](https://arxiv.org/), the world's largest open-access preprint server (2M+ papers).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `Search` | No | Search papers by query string across all fields |
| `GetPaper` | No | Get a specific paper by its arxiv ID |
| `SearchByAuthor` | No | Search papers by author name |
| `SearchByTitle` | No | Search papers by title keywords |
| `SearchByCategory` | No | Search papers by category (cs.AI, cs.LG, etc.) |
| `SearchByAbstract` | No | Search papers by abstract content |
| `GetRecent` | No | Get recent papers in a category, sorted by date |
| `GetMultiple` | No | Get multiple papers by their arxiv IDs in a single request |
| `AdvancedSearch` | No | Advanced search combining multiple fields |
| `GetCategories` | No | Get a reference list of arxiv categories with descriptions |

## Quick start

```bash
# Install
cd arxiv
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli ArxivService Search -r '{"query": "transformer architecture", "limit": 5}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/arxiv", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
