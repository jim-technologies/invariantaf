# TMDB MCP Server

Movie and TV show data from [The Movie Database (TMDB)](https://www.themoviedb.org/), one of the largest community-built entertainment databases.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchMovies` | Yes | Search for movies by title |
| `SearchTV` | Yes | Search for TV shows by name |
| `GetMovie` | Yes | Get detailed information about a specific movie |
| `GetTVShow` | Yes | Get detailed information about a specific TV show |
| `GetTrending` | Yes | Get trending movies, TV shows, or people |
| `GetMovieCredits` | Yes | Get cast and crew credits for a movie |
| `GetMovieReviews` | Yes | Get user reviews for a movie |
| `GetPopularMovies` | Yes | Get currently popular movies |
| `GetTopRatedMovies` | Yes | Get top rated movies of all time |
| `DiscoverMovies` | Yes | Discover movies with filters |

## Quick start

```bash
# Install
cd tmdb
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
TMDB_API_KEY=your-key uv run python main.py

# Run as CLI
uv run python main.py --cli TMDBService SearchMovies -r '{"query": "Inception"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

Required. Set `TMDB_API_KEY`. Get a free key at https://www.themoviedb.org/settings/api.

## MCP config

```json
{
  "mcpServers": {
    "tmdb": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/tmdb", "python", "main.py"],
      "env": {
        "TMDB_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
