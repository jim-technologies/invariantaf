# Reddit MCP Server

Read-only access to [Reddit](https://www.reddit.com/) content via the public JSON API.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetHot` | No | Get hot posts from a subreddit |
| `GetTop` | No | Get top posts from a subreddit |
| `GetNew` | No | Get newest posts from a subreddit |
| `GetPost` | No | Get a single post with its comments |
| `SearchPosts` | No | Search for posts across all of Reddit |
| `GetSubreddit` | No | Get information about a subreddit |
| `GetUser` | No | Get a Reddit user's profile information |
| `GetUserPosts` | No | Get posts submitted by a specific user |
| `GetPopularSubreddits` | No | Get a list of popular subreddits |
| `GetFrontPage` | No | Get Reddit front page posts |

## Quick start

```bash
# Install
cd reddit
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli RedditService GetHot -r '{"subreddit": "python", "limit": 5}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "reddit": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/reddit", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
