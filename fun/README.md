# Fun MCP Server

Dad jokes, trivia, quotes, dog images, and cat facts from several free APIs combined into one service.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetDadJoke` | No | Get a random dad joke |
| `SearchDadJokes` | No | Search for dad jokes by keyword |
| `GetTrivia` | No | Get random trivia questions |
| `GetTriviaCategories` | No | List all available trivia categories |
| `GetRandomQuote` | No | Get a random inspirational quote |
| `SearchQuotes` | No | Search for quotes by content |
| `GetRandomDogImage` | No | Get a random dog image |
| `GetDogImageByBreed` | No | Get a random dog image for a specific breed |
| `ListDogBreeds` | No | List all available dog breeds |
| `GetRandomCatFact` | No | Get a random cat fact |

## Quick start

```bash
# Install
cd fun
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli FunService GetDadJoke -r '{}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "fun": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/fun", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
