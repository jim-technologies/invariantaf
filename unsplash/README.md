# Unsplash MCP Server

High-resolution, freely-usable photography from [Unsplash](https://unsplash.com/), the internet's largest source of free photos.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchPhotos` | Yes | Search for photos by keyword or phrase |
| `GetPhoto` | Yes | Get a single photo by its unique Unsplash ID |
| `GetRandomPhoto` | Yes | Get one or more random photos, optionally filtered by query |
| `ListPhotos` | Yes | List editorial photos curated by the Unsplash team |
| `SearchCollections` | Yes | Search for photo collections by keyword |
| `GetCollection` | Yes | Get details of a specific collection by its ID |
| `GetCollectionPhotos` | Yes | Get photos belonging to a specific collection |
| `SearchUsers` | Yes | Search for Unsplash users (photographers) by keyword |
| `GetUser` | Yes | Get a user's public profile by username |
| `GetUserPhotos` | Yes | Get photos uploaded by a specific user |

## Quick start

```bash
# Install
cd unsplash
go build -o unsplash-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
UNSPLASH_ACCESS_KEY=your-key ./unsplash-mcp
# or: UNSPLASH_ACCESS_KEY=your-key go run .
```

## Authentication

Required. Set `UNSPLASH_ACCESS_KEY`. Register an app at https://unsplash.com/developers.

## MCP config

```json
{
  "mcpServers": {
    "unsplash": {
      "command": "/path/to/unsplash-mcp",
      "env": {
        "UNSPLASH_ACCESS_KEY": "your-access-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
