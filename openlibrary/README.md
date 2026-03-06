# Open Library MCP Server

Book, author, and edition data from [Open Library](https://openlibrary.org/), the world's largest open, editable library catalog.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchBooks` | No | Search for books by keyword |
| `SearchByAuthor` | No | Search for books by author name |
| `SearchBySubject` | No | Get books by subject or topic |
| `GetBook` | No | Get book details by Open Library work ID |
| `GetEdition` | No | Get a specific edition by Open Library edition ID |
| `GetAuthor` | No | Get author details by Open Library author ID |
| `GetAuthorWorks` | No | List works by an author |
| `GetBookByISBN` | No | Look up a book by ISBN |
| `GetRecentChanges` | No | Get recent changes to Open Library |
| `GetTrendingBooks` | No | Get currently trending books |

## Quick start

```bash
# Install
cd openlibrary
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli OpenLibraryService SearchBooks -r '{"query": "the lord of the rings", "limit": 5}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "openlibrary": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/openlibrary", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
