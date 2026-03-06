# XKCD MCP Server

Comics from [XKCD](https://xkcd.com/) -- the legendary webcomic of romance, sarcasm, math, and language by Randall Munroe (3,000+ comics).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetLatest` | No | Get the latest XKCD comic |
| `GetComic` | No | Get a specific XKCD comic by its number |
| `GetRandom` | No | Get a random XKCD comic |
| `GetRange` | No | Get a range of consecutive XKCD comics |
| `SearchByTitle` | No | Search comics by title substring match |
| `GetExplanation` | No | Get the community explanation for a comic from explainxkcd.com |
| `GetComicCount` | No | Get the total number of XKCD comics published |
| `GetMultiple` | No | Get multiple specific comics by their numbers |
| `GetRecent` | No | Get the N most recent XKCD comics |
| `GetByDate` | No | Get comics published in a specific month and year |

## Quick start

```bash
# Install
cd xkcd
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli XKCDService GetComic -r '{"num": 327}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "xkcd": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/xkcd", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
