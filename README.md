# invariantaf

`invariantaf` is a multi-adapter workspace for turning external APIs into protocol-agnostic servers and clients using [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol).

Each adapter is self-contained and should project the same contract to:

- MCP (stdio)
- CLI
- HTTP
- gRPC

## Core idea

Every adapter follows the same pipeline:

1. Protobuf service contract (`.proto`)
2. Descriptor generation (`descriptor.binpb`)
3. Thin provider implementation (auth, request mapping, response mapping)
4. Invariant projections (MCP, CLI, HTTP, gRPC)

```
proto -> descriptor -> provider adapter -> MCP + CLI + HTTP + gRPC
```

## Repository layout

Top-level directories are provider adapters.

Typical adapter contents:

- `main.py` or `main.go`
- `proto/`
- `descriptor.binpb`
- `README.md`
- `Makefile`
- `tests/`

## Development environment

This repo uses Flox for reproducible tooling (`buf`, `uv`, `ruff`, `go`, and generator helpers).

```bash
flox activate
```

## Common workflow

From any adapter directory:

```bash
make generate      # if generation applies
make descriptor
make lint
make test
```

Serve projections:

```bash
make serve-mcp
make serve-cli
```

Most Python adapters also support:

```bash
uv run python main.py --http 8080
uv run python main.py --grpc 50051
```

## Contribution standard

Use [AGENTS.md](./AGENTS.md) as the source of truth for:

- adapter structure
- protobuf conventions
- auth and environment conventions
- testing contract
- build/lint/test contract

## CI

GitHub workflows run adapter matrices for lint and tests in Flox-backed environments to match local development behavior.

## License

Apache 2.0
