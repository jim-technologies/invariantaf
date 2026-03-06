# OpenDota MCP Server

Full OpenDota MCP/CLI/HTTP projection built on [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

- Source API: <https://api.opendota.com/api>
- Coverage: all `GET`/`POST` operations in the OpenDota OpenAPI spec (55 operations)
- Auth: public endpoints (no key required)

Optional API key (recommended for higher limits):

- Set `OPENDOTA_API_KEY` in environment.
- `main.py` maps it to `INVARIANT_HTTP_HEADER_AUTHORIZATION=Bearer ...` for `connect_http`.

## Design

This project uses descriptor-driven HTTP client proxy mode:

- RPC methods map 1:1 to OpenDota endpoints.
- `google.api.http` annotations are generated from OpenAPI.
- Runtime uses `Server.connect_http("https://api.opendota.com/api")`.
- Requests support path params + `query` and `body` structs.
- Responses map raw endpoint payload to `data` (`google.protobuf.Value`) via `response_body: "data"`.

## Generated artifacts

- Vendored spec: `openapi/opendota.openapi.json`
- Generated Python protobuf bindings: `src/gen/`
- Descriptor: `descriptor.binpb`

## Quick start

```bash
cd opendota
uv sync

# MCP (stdio)
uv run python main.py

# CLI
uv run python main.py --cli OpenDotaService GetTopPlayers -r '{"query":{"turbo":1}}'
uv run python main.py --cli OpenDotaService GetPlayer -r '{"account_id":12345}'

# HTTP
uv run python main.py --http 8080
curl -sS localhost:8080/opendota.v1.OpenDotaService/GetTopPlayers \
  -H 'content-type: application/json' \
  -d '{"query":{"turbo":1}}'
```

## MCP config

```json
{
  "mcpServers": {
    "opendota": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/opendota", "python", "main.py"]
    }
  }
}
```
