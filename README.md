# invariantaf

MCP servers for APIs across crypto, knowledge, entertainment, developer tools, and more. Each server is a self-contained project powered by [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol) -- comment your protobuf, get AI-ready tools.

## Servers

### Crypto / DeFi

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [Hyperliquid](./hyperliquid/) | Python | 13 | Yes | Perpetual futures DEX trading and market data |
| [Polymarket](./polymarket/) | Python | 17 | Partial | Prediction market data and trading on Polygon |
| [CoinGecko](./coingecko/) | Python | 10 | No | Cryptocurrency prices, charts, and market data |
| [DefiLlama](./defillama/) | Python | 10 | No | DeFi TVL, yields, DEX volumes, and protocol analytics |

### Knowledge / Reference

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [Wikipedia](./wikipedia/) | Python | 10 | No | Article summaries, search, and historical events |
| [arXiv](./arxiv/) | Python | 10 | No | Scientific paper search and discovery (2M+ papers) |
| [Open Library](./openlibrary/) | Python | 10 | No | Books, authors, and editions from the open library catalog |
| [Stack Exchange](./stackexchange/) | Go | 10 | No | Q&A from Stack Overflow and 170+ Stack Exchange sites |

### News / Social

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [Hacker News](./hackernews/) | Python | 10 | No | Tech news and discussions from Y Combinator |
| [Reddit](./reddit/) | Python | 10 | No | Read-only access to subreddits, posts, and comments |

### Entertainment

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [TMDB](./tmdb/) | Python | 10 | Yes | Movie and TV show search, details, and trending |
| [XKCD](./xkcd/) | Python | 10 | No | Webcomics with search, explanations, and random picks |
| [Giphy](./giphy/) | Go | 10 | No | GIF and sticker search, trending, and translate |
| [CocktailDB](./cocktaildb/) | Python | 10 | No | Cocktail recipes, ingredients, and discovery |
| [PokeAPI](./pokeapi/) | Python | 10 | No | Pokemon stats, moves, types, and evolution chains |
| [Fun](./fun/) | Python | 10 | No | Dad jokes, trivia, quotes, dog images, and cat facts |

### Science / Space

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [NASA](./nasa/) | Python | 10 | No | APOD, Mars rover photos, asteroids, and space weather |
| [SpaceX](./spacex/) | Python | 10 | No | Launches, rockets, crew, and Starlink satellites |

### Developer Tools

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [GitHub](./github/) | Python | 10 | No | Repository search, issues, PRs, and user profiles |
| [Docker Hub](./dockerhub/) | Go | 10 | No | Container image search, tags, and Dockerfiles |
| [Package Registry](./packageregistry/) | Python | 10 | No | NPM and PyPI package metadata and downloads |

### Gaming

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [Steam](./steam/) | Go | 10 | Yes | Player profiles, game libraries, and achievements |
| [Lichess](./lichess/) | Python | 10 | No | Chess player data, games, puzzles, and leaderboards |
| [OpenDota](./opendota/) | Python | 11 | No | Dota 2 heroes, matches, players, teams, and pro match data |
| [STRATZ](./stratz/) | Python | 10 | Yes | Dota 2 match, player, constants, and hero stats via GraphQL |

### Weather / Finance

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [OpenWeatherMap](./openweathermap/) | Python | 10 | Yes | Current weather, forecasts, air quality, and geocoding |
| [ExchangeRate](./exchangerate/) | Python | 10 | No | Foreign exchange rates from the European Central Bank |
| [Kalshi](./kalshi/) | Python | 85 | Partial | Prediction market exchange API from Kalshi OpenAPI spec |

### Photography

| Server | Lang | Tools | Auth | Description |
|--------|------|-------|------|-------------|
| [Unsplash](./unsplash/) | Go | 10 | Yes | High-resolution, freely-usable photo search and discovery |

## How it works

Each server follows the same pattern:

1. **Proto** -- define the service with rich comments in `.proto` files
2. **Descriptor** -- `buf build` produces a `descriptor.binpb` with embedded comments
3. **Implementation** -- Python/Go service wraps the API's SDK or REST endpoints
4. **Invariant** -- projects the service into MCP, CLI, HTTP, and gRPC

```
proto comments  ->  descriptor.binpb  ->  your API wrapper  ->  MCP + CLI + HTTP + gRPC
```

## Quick start

### Python servers

```bash
cd <server>
uv sync
uv run python main.py          # MCP over stdio
uv run python main.py --http 8080  # HTTP server
uv run python main.py --cli <ServiceName> <Method> -r '{"field": "value"}'  # CLI
```

### Go servers

```bash
cd <server>
go build -o <name>-mcp .
./<name>-mcp                   # MCP over stdio
```

## License

Apache 2.0
