# Giphy MCP Server

GIFs, stickers, and short-form video content from [Giphy](https://giphy.com/), the world's largest animated GIF library.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `Search` | No | Search for GIFs by keyword or phrase |
| `Trending` | No | Get currently trending GIFs |
| `GetGifById` | No | Get a single GIF by its unique Giphy ID |
| `GetGifsByIds` | No | Get multiple GIFs by their Giphy IDs in a single request |
| `Random` | No | Get a single random GIF, optionally filtered by tag |
| `SearchStickers` | No | Search for stickers by keyword or phrase |
| `TrendingStickers` | No | Get currently trending stickers |
| `RandomSticker` | No | Get a single random sticker, optionally filtered by tag |
| `Translate` | No | Translate a word or phrase into the most relevant GIF |
| `GetCategories` | No | Get a list of GIF content categories |

## Quick start

```bash
# Install
cd giphy
go build -o giphy-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
./giphy-mcp
# or: go run .
```

## Authentication

Optional. Set `GIPHY_API_KEY` for a production key. A public beta key is included as default.

## MCP config

```json
{
  "mcpServers": {
    "giphy": {
      "command": "/path/to/giphy-mcp",
      "env": {
        "GIPHY_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
