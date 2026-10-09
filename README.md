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

Go adapters use root `invariantprotocol` v0.16.7; the `/go` import package
still exists, while the former nested module is removed. Run
`make generate-go` to regenerate Go descriptors, bindings and typed registration
from one graph. `scripts/generate-python-adapters --write` regenerates Python
bindings from the embedded graph. Run `make validate` for the offline gate and `make audit` for
unsuppressed dependency checks. Source/protobuf contracts remain unchanged;
provider live qualification stays behind its explicit opt-in.

## Common workflow

From the repo root, `make validate` is the gate — the one gate verb every public
repository in this organisation shares. Here it runs `lint` (public-surface and
tracked-artifact guards, then `go vet` and `ruff check`), generated graph checks
and `test`:

```bash
make validate
```

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

GitHub workflows run the repository gate in Flox and an unsuppressed weekly
dependency audit. Neither enables live provider tests.

The [framework migration record](docs/framework-migration.md) describes source
coverage, regeneration and the separate live-provider qualification boundary.

## License

Apache 2.0
