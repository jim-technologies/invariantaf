# Stack Exchange MCP Server

Q&A data from the [Stack Exchange](https://stackexchange.com/) network (Stack Overflow, Server Fault, Super User, and 170+ sites) via the public API v2.3.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchQuestions` | No | Search for questions matching a query string |
| `GetQuestion` | No | Get a single question by its numeric ID |
| `GetAnswers` | No | Get the answers posted to a specific question |
| `GetUser` | No | Get a user's profile by their numeric user ID |
| `GetTags` | No | Get popular tags on a Stack Exchange site |
| `GetTopQuestions` | No | Get top questions, optionally filtered by tag |
| `SearchAdvanced` | No | Advanced search with multiple filters |
| `GetUserReputation` | No | Get a user's reputation change history |
| `GetSimilar` | No | Find questions similar to a given title |
| `GetUnanswered` | No | Get unanswered questions, optionally filtered by tag |

## Quick start

```bash
# Install
cd stackexchange
go build -o stackexchange-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
./stackexchange-mcp
# or: go run .
```

## Authentication

Optional. Set `STACKEXCHANGE_API_KEY` for higher rate limits (10,000 req/day vs 300 req/day).

## MCP config

```json
{
  "mcpServers": {
    "stackexchange": {
      "command": "/path/to/stackexchange-mcp",
      "env": {
        "STACKEXCHANGE_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
