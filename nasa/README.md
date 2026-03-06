# NASA MCP Server

Space science, Earth observation, and planetary exploration data from [NASA's open APIs](https://api.nasa.gov/).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetAPOD` | No | Get the Astronomy Picture of the Day |
| `GetAPODRange` | No | Get Astronomy Pictures of the Day for a date range |
| `GetMarsPhotos` | No | Get photos taken by Mars rovers (Curiosity, Opportunity, Spirit) |
| `GetMarsManifest` | No | Get the mission manifest for a Mars rover |
| `GetNEOs` | No | Get near-Earth objects (asteroids) for a date range |
| `GetNEOLookup` | No | Look up a specific near-Earth asteroid by its ID |
| `GetEPIC` | No | Get Earth images from the EPIC camera on DSCOVR |
| `SearchNASAImages` | No | Search NASA's Image and Video Library |
| `GetDonki` | No | Get space weather events from DONKI |
| `GetTechTransfer` | No | Search NASA Technology Transfer patents and software |

## Quick start

```bash
# Install
cd nasa
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli NASAService GetAPOD -r '{"date": "2024-01-01"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Optional. Defaults to `DEMO_KEY` (30 req/hr). Get a free unlimited key at https://api.nasa.gov and set `NASA_API_KEY`.

## MCP config

```json
{
  "mcpServers": {
    "nasa": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/nasa", "python", "main.py"],
      "env": {
        "NASA_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
