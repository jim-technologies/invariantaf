# Wikipedia MCP Server

Articles, summaries, and historical events from [Wikipedia](https://www.wikipedia.org/), the free encyclopedia (60M+ articles, 300+ languages).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `Search` | No | Search Wikipedia articles by keyword or phrase |
| `GetPage` | No | Get a concise summary of a Wikipedia article by its title |
| `GetFullPage` | No | Get the full article content as plain text |
| `GetRandom` | No | Get one or more random Wikipedia article summaries |
| `GetOnThisDay` | No | Get historical events that happened on a specific date |
| `GetMostRead` | No | Get the most-read Wikipedia articles for a specific date |
| `GetLanguages` | No | Get available language editions for an article |
| `GetCategories` | No | Get the categories that an article belongs to |
| `GetLinks` | No | Get internal links from a Wikipedia article |
| `GetImages` | No | Get images embedded in a Wikipedia article |

## Quick start

```bash
# Install
cd wikipedia
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli WikipediaService GetPage -r '{"title": "Albert_Einstein"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/wikipedia", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
