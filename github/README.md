# GitHub MCP Server

Repository discovery, user profiles, issues, and pull requests from [GitHub](https://github.com/)'s public REST API.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchRepos` | No | Search GitHub repositories by keyword |
| `SearchUsers` | No | Search GitHub users by keyword |
| `GetUser` | No | Get a user's public profile |
| `GetRepo` | No | Get detailed information about a repository |
| `ListRepoIssues` | No | List issues for a repository |
| `GetIssue` | No | Get a single issue by number |
| `ListRepoPulls` | No | List pull requests for a repository |
| `GetPull` | No | Get a single pull request by number |
| `ListRepoLanguages` | No | Get the language breakdown for a repository |
| `GetRateLimit` | No | Check the current GitHub API rate limit status |

## Quick start

```bash
# Install
cd github
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli GitHubService SearchRepos -r '{"query": "machine learning python", "per_page": 5}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Optional. Set `GITHUB_TOKEN` for higher rate limits (5,000 req/hr vs 60 req/hr unauthenticated).

## MCP config

```json
{
  "mcpServers": {
    "github": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/github", "python", "main.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
