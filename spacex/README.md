# SpaceX MCP Server

Launch data, rocket specs, crew, and Starlink satellites from the open [SpaceX API](https://github.com/r-spacex/SpaceX-API) (v4).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetLatestLaunch` | No | Get the most recent SpaceX launch with full details |
| `GetLaunches` | No | Get all SpaceX launches (past and future) |
| `GetLaunch` | No | Get a specific SpaceX launch by its unique ID |
| `GetRockets` | No | Get all SpaceX rockets (Falcon 1, Falcon 9, Falcon Heavy, Starship) |
| `GetRocket` | No | Get detailed specifications for a specific rocket |
| `GetCrew` | No | Get all SpaceX crew members who have flown on Dragon missions |
| `GetStarlink` | No | Get Starlink satellite constellation data |
| `GetLaunchpads` | No | Get all SpaceX launch pad locations and their status |
| `GetCompanyInfo` | No | Get SpaceX company information |
| `GetUpcomingLaunches` | No | Get upcoming scheduled SpaceX launches |

## Quick start

```bash
# Install
cd spacex
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli SpaceXService GetLatestLaunch -r '{}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "spacex": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/spacex", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
