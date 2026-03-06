# Lichess MCP Server

Chess data from [Lichess.org](https://lichess.org/), the free, open-source chess server with millions of active players.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetUser` | No | Get a chess player's profile including ratings and game count |
| `GetUserRatingHistory` | No | Get a player's rating history across all game types over time |
| `GetUserGames` | No | Get recent games played by a user |
| `GetGame` | No | Get a specific game by its game ID |
| `GetDailyPuzzle` | No | Get today's daily chess puzzle |
| `GetPuzzle` | No | Get a specific puzzle by its ID |
| `GetLeaderboard` | No | Get the top players leaderboard for a specific time control |
| `GetCloudEval` | No | Get cloud engine evaluation for a chess position |
| `GetOnline` | No | Get the count of currently online players |
| `GetTeam` | No | Get information about a Lichess team |

## Quick start

```bash
# Install
cd lichess
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli LichessService GetUser -r '{"username": "DrNykterstein"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Optional. Set `LICHESS_API_TOKEN` for higher rate limits.

## MCP config

```json
{
  "mcpServers": {
    "lichess": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/lichess", "python", "main.py"],
      "env": {
        "LICHESS_API_TOKEN": "lip_your_token_here"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
