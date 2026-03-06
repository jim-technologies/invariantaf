# Hacker News MCP Server

Tech news and discussions from [Hacker News](https://news.ycombinator.com/), the popular Y Combinator tech news aggregator.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetTopStories` | No | Get the top stories currently on the front page |
| `GetNewStories` | No | Get the newest stories posted to Hacker News |
| `GetBestStories` | No | Get the best stories on Hacker News |
| `GetAskStories` | No | Get Ask HN stories -- questions posed by the community |
| `GetShowStories` | No | Get Show HN stories -- projects shared by the community |
| `GetJobStories` | No | Get job postings from Hacker News |
| `GetItem` | No | Get a single item by its ID |
| `GetUser` | No | Get a user profile by username |
| `GetComments` | No | Get comments for a story, with optional recursive depth |
| `GetMaxItem` | No | Get the current maximum item ID |

## Quick start

```bash
# Install
cd hackernews
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli HackerNewsService GetTopStories -r '{"limit": 5}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/hackernews", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
