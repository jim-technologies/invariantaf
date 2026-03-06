# JSONPlaceholder MCP Server

Descriptor-driven JSONPlaceholder proxy built on [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

## Coverage

`JsonPlaceholderService` tools:

- `GetPost`
- `GetUser`
- `GetTodo`
- `GetComment`

All endpoints are wired through `Server.connect_http(...)` + `google.api.http` annotations.

## Authentication

No authentication required.

## Base URL

Default:

- `https://jsonplaceholder.typicode.com`

Override with:

- `JSONPLACEHOLDER_BASE_URL`

## Quick start

```bash
cd jsonplaceholder
uv sync
make generate

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli JsonPlaceholderService GetPost -r '{"id":1}'

# HTTP
uv run python main.py --http 8080
```

## Regenerate

```bash
make generate
```

## Run tests

```bash
make test
```

## Source docs

- https://jsonplaceholder.typicode.com/
