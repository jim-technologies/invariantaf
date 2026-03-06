# Steam MCP Server

Player profiles, game libraries, achievements, and app metadata from the [Steam Web API](https://steamcommunity.com/dev).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetPlayerSummaries` | Yes | Get profile information for one or more Steam players |
| `GetOwnedGames` | Yes | Get the list of games owned by a Steam player |
| `GetRecentlyPlayedGames` | Yes | Get games a player has played in the last two weeks |
| `GetPlayerAchievements` | Yes | Get a player's achievements for a specific game |
| `GetAppDetails` | No | Get detailed metadata about a Steam app |
| `GetAppList` | No | Get the complete list of all apps on Steam |
| `GetNumberOfCurrentPlayers` | No | Get the number of players currently in-game for a specific app |
| `GetFriendList` | Yes | Get a player's friend list |
| `GetNewsForApp` | No | Get news articles for a Steam app |
| `GetGlobalAchievementPercentages` | No | Get global achievement unlock percentages for a game |

## Quick start

```bash
# Install
cd steam
go build -o steam-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
STEAM_API_KEY=your-key ./steam-mcp
# or: STEAM_API_KEY=your-key go run .
```

## Authentication

Required for most endpoints. Set `STEAM_API_KEY`. Get a free key at https://steamcommunity.com/dev/apikey.

`GetAppDetails`, `GetAppList`, `GetNumberOfCurrentPlayers`, `GetNewsForApp`, and `GetGlobalAchievementPercentages` do not require a key.

## MCP config

```json
{
  "mcpServers": {
    "steam": {
      "command": "/path/to/steam-mcp",
      "env": {
        "STEAM_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
