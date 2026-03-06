# CocktailDB MCP Server

Cocktail recipes, ingredients, and discovery from [TheCocktailDB](https://www.thecocktaildb.com/) -- the world's largest open cocktail database (600+ cocktails).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchCocktails` | No | Search for cocktails by name |
| `GetCocktail` | No | Get a cocktail by its unique ID with the full recipe |
| `GetRandomCocktail` | No | Get a random cocktail |
| `FilterByIngredient` | No | Find cocktails that contain a specific ingredient |
| `FilterByCategory` | No | Find cocktails in a specific category |
| `FilterByGlass` | No | Find cocktails served in a specific glass type |
| `ListCategories` | No | Get all cocktail categories |
| `ListGlasses` | No | Get all glass types |
| `ListIngredients` | No | Get all available ingredients |
| `SearchIngredient` | No | Get detailed information about a specific ingredient |

## Quick start

```bash
# Install
cd cocktaildb
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli CocktailDBService SearchCocktails -r '{"name": "margarita"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "cocktaildb": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/cocktaildb", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
