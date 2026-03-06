# STRATZ MCP Server

Advanced Dota 2 analytics from [STRATZ](https://stratz.com/) via GraphQL.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `ExecuteRawQuery` | Yes | Run any custom GraphQL query with variables |
| `GetMatchSummary` | Yes | Get core match metadata (winner, duration, start time) |
| `GetMatchPlayers` | Yes | Get per-player match rows (hero, lane/role, KDA) |
| `GetMatchLaneOutcomes` | Yes | Get lane/role/net-worth/KDA match outcomes |
| `GetMatchDotaPlusLevels` | Yes | Get match first-blood timing and Dota Plus hero levels |
| `GetPlayerRecentMatches` | Yes | Get recent matches for a Steam account |
| `GetConstantsHeroes` | Yes | Get STRATZ hero constants |
| `GetConstantsItems` | Yes | Get STRATZ item constants |
| `GetConstantsAbilities` | Yes | Get STRATZ ability constants |
| `GetHeroNeutralItemStats` | Yes | Get hero neutral-item usage stats by bracket |

## Quick start

```bash
# Install
cd stratz
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
STRATZ_API_KEY=your-token uv run python main.py

# Run as CLI
STRATZ_API_KEY=your-token uv run python main.py --cli StratzService GetMatchSummary -r '{"match_id": 8597260572}'

# Run as HTTP server
STRATZ_API_KEY=your-token uv run python main.py --http 8080
```

## Authentication

Set `STRATZ_API_KEY` (Bearer token from STRATZ API access).

Optional: set `STRATZ_BASE_URL` to override the default endpoint (`https://api.stratz.com/graphql`).

## Notes on GraphQL

Yes: STRATZ is GraphQL, and operationally this is a single POST endpoint receiving query text + variables and returning JSON.
This server wraps those operations as typed tools so they are easier for agents to discover and call.

## MCP config

```json
{
  "mcpServers": {
    "stratz": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/stratz", "python", "main.py"],
      "env": {
        "STRATZ_API_KEY": "your-token"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```

## Run tests

```bash
# Local + mocked tests
uv run python -m pytest tests -q

# Optional live STRATZ smoke test
STRATZ_API_KEY=your-token STRATZ_RUN_LIVE_TESTS=1 \
  uv run python -m pytest tests/test_integration.py::TestLiveStratzAPI::test_live_get_constants_heroes -q
```
