# PokeAPI MCP Server

Pokemon data from [PokeAPI](https://pokeapi.co/), the world's most comprehensive Pokemon data source (1,000+ Pokemon).

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetPokemon` | No | Get detailed information about a specific Pokemon |
| `GetPokemonSpecies` | No | Get species-level information about a Pokemon |
| `GetAbility` | No | Get detailed information about an ability |
| `GetMove` | No | Get detailed information about a move |
| `GetType` | No | Get type matchup information |
| `GetEvolutionChain` | No | Get a full evolution chain |
| `GetGeneration` | No | Get information about a Pokemon generation |
| `GetItem` | No | Get detailed information about an item |
| `GetNature` | No | Get nature stat modification details |
| `ListPokemon` | No | List Pokemon with pagination |

## Quick start

```bash
# Install
cd pokeapi
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli PokeAPIService GetPokemon -r '{"name_or_id": "pikachu"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "pokeapi": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pokeapi", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
