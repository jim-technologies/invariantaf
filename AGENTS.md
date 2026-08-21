# AGENTS.md

Contributor guide for `invariantaf/` API adapters.

## 1) Purpose

This repo contains many independent MCP servers that expose external APIs through Invariant Protocol.

Each adapter should make it easy to project the same API surface to:

- MCP (stdio)
- CLI
- HTTP
- gRPC

Primary goal: keep adapters protocol-agnostic and consistent, so converting a new API into an MCP server/client is straightforward.

## 2) Core Invariants

1. Keep each provider self-contained in its own directory.
2. Use protobuf + descriptor as the contract source of truth.
3. Prefer deterministic generation from source specs/docs where possible.
4. Keep runtime thin: map request/response/auth only.
5. Include tests for descriptor wiring and projection behavior.

## 3) Adapter Patterns

Use one of these patterns (or combine when needed):

1. `Server.connect_http(...)` + `google.api.http` annotations.
   - Best when endpoint mapping is mostly 1:1 REST.
   - Common for OpenAPI-driven adapters (for example: Kalshi, OpenDota).

2. Custom servicer class with `server.register(...)`.
   - Use when auth/signing, response transforms, or multi-backend routing is non-trivial.
   - Common for bespoke exchanges/APIs (for example: Kraken, Hyperliquid).

3. `connect_http(...)` plus dynamic header provider.
   - Use when endpoint mapping is 1:1 but auth requires per-request signatures.
   - Common for signed REST APIs (for example: Bybit/Polymarket style flows).

## 4) Standard Project Layout (Python)

Expected files/directories for new adapters:

- `main.py`
- `Makefile`
- `pyproject.toml`  (`requires-python = ">=3.11"`)
- `uv.lock`
- `proto/buf.yaml`
- `proto/buf.gen.yaml`  (Python output goes to `../src/<provider>_mcp/gen`)
- `proto/<provider>/v1/<provider>.proto`
- `descriptor.binpb` (generated)
- `src/<provider>_mcp/service.py`
- `src/<provider>_mcp/gen/...` (generated protobuf)
- `tests/test_live.py` (live integration tests, gated by env var)

Optional but recommended for generated adapters:

- `openapi/` (or other vendored spec input)
- `scripts/` generation scripts

### Python async requirements

The framework is async-native. Adapters MUST follow these rules:

1. **All RPC handler methods are `async def`.** `Server.register()` rejects sync
   handlers with `TypeError`.
2. **`main.py` runs the server via `asyncio.run(server.serve(...))`.**
   `Server.serve()` is a coroutine that takes kwargs (`mcp=True`, `cli=True`,
   `http=<port>`, `grpc=<port>`). There is no `serve_from_argv()` — parse argv
   yourself.
3. **HTTP clients are `httpx.AsyncClient`, not `httpx.Client`.** Sync clients
   inside `async def` block the event loop. Internal helper methods that touch
   the client should also be `async def`, with `await` on every call.
4. **Expose `async def aclose(self)`** that calls `await self._client.aclose()`
   so tests / future framework versions can drain the connection pool cleanly.
5. **`Server.from_descriptor(path)`** takes only the path now. The old
   `name=`/`version=` kwargs are gone — name and version are framework-level
   constants.

A minimal `main.py`:

```python
import asyncio, sys
from pathlib import Path
from invariant import Server
from foo_mcp.service import FooService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"

def _projection_from_argv(argv):
    if not argv: return {"mcp": True}
    cmd = argv[0]
    if cmd in ("--cli",):  return {"cli": True}
    if cmd in ("--http",): return {"http": int(argv[1]) if len(argv) > 1 else 8080}
    if cmd in ("--grpc",): return {"grpc": int(argv[1]) if len(argv) > 1 else 50051}
    return {"mcp": True}

def main():
    server = Server.from_descriptor(str(DESCRIPTOR))
    server.register(FooService(), service_name="foo.v1.FooService")
    asyncio.run(server.serve(**_projection_from_argv(sys.argv[1:])))

if __name__ == "__main__":
    main()
```

## 5) Standard Project Layout (Go)

Go adapters typically:

- embed `descriptor.binpb` via `//go:embed`
- initialize with `invariant.ServerFromBytes(...)`
- register a servicer and call `server.Serve(ctx, invariant.MCP())`

`Serve` requires a `context.Context` — typically `context.Background()`. The
old `server.Name`/`server.Version` setters are gone (those are framework
constants now).

Keep Go projects similarly self-contained under their provider directory.

## 6) Protobuf Conventions

1. Package naming: `<provider>.v1`.
2. Service names should be clear and domain-oriented.
3. Add RPC comments (they become tool descriptions).
4. Use typed request/response messages where practical.
5. Use `google.protobuf.Value` or `Struct` only for truly dynamic or ambiguous shapes.
6. For HTTP proxy mode, use `google.api.http` annotations with explicit path/body mapping.

If a proto is generated, edit the generator/input source, not the generated `.proto` manually.

## 7) Auth and Environment Conventions

1. Provider env vars should be explicit and prefixed (for example: `BYBIT_API_KEY`).
2. Expose exactly one clear base URL override env var per adapter (for example: `*_BASE_URL`).
3. Keep auth logic near the boundary:
   - static headers via env mapping when possible
   - dynamic request signing via `server.use_http_header_provider(...)` when needed
4. Fail private methods with actionable auth errors when credentials are missing.

## 8) Testing Contract (Minimum)

Each adapter should include **live integration tests** gated by an env var (e.g., `PROVIDER_RUN_LIVE_TESTS=1`). Do NOT write mock tests that mock HTTP responses — they only test our own mocks and provide no value.

Tests should:

1. Hit the real API (skipped by default without env var).
2. Validate response structure.
3. Handle rate limits and timeouts gracefully (skip, don't fail).

For Go, include a smoke test that verifies the service can be instantiated.

For authenticated adapters, live tests should also require the API key env var.

## 9) Build/Lint/Test Contract

### Single-language adapters

Provide consistent Make targets:

- `make generate`
- `make descriptor`
- `make lint`
- `make fmt`
- `make test`
- `make clean`

### Dual-language adapters (Go + Python)

Use standardized target names:

- `make test` — runs both `test-go` and `test-py`
- `make test-go` — `go test -v -count=1 ./...`
- `make test-py` — `uv run python -m pytest tests/ -v`
- `make serve-go` — `go run .`
- `make serve-py` — `uv run python main.py`
- `make lint` — both `go vet` and `ruff check`

### Repo-root gates

`make lint` runs two repo-wide guards before it reaches `go vet` and `ruff`, and
either one turning red stops the build:

- `make public-surface` — `scripts/public-surface-check` scans the content of
  every tracked file, every tracked path, and the commit messages a push would
  publish, and fails on private repository names, internal infrastructure,
  first-party codenames, cluster shapes, credential shapes, secret stores and
  private remotes. `scripts/public-surface-check-test` then proves the guard
  still works. Justified exceptions go in `.public-surface-allow` at the repo
  root (`category | path-glob | reason | pattern`), one line each with a reason
  — never by editing the shared script, which is identical in every public repo.
- `make tracked-artifacts` — `scripts/tracked-artifact-check` fails if a tracked
  file is a compiled executable image or is larger than 2MB. `.gitignore` alone
  does not protect us here: it has no effect on a file that is already tracked,
  which is how two 19MB Go binaries were once committed despite being listed.

### Pre-push checklist

**Always lint and test before pushing.** Run from the repo root:

```bash
make test    # runs all Go + Python tests
make lint    # public-surface + tracked-artifacts, then go vet + ruff check
```

Or for a single adapter:

```bash
make -C <adapter> lint
make -C <adapter> test
```

CI runs the same `make lint` and `make test` targets — if it passes locally, it passes in CI.

## 10) README Contract

Each adapter README should include:

1. What API is covered and current coverage scope.
2. Auth requirements and env vars.
3. Base URL override.
4. Quick start commands.
5. Regeneration instructions (if generated).
6. Source docs/spec links.

## 11) Contribution Checklist

1. Keep changes scoped to one provider unless intentionally cross-cutting.
2. Preserve existing adapter patterns unless there is a clear improvement.
3. Do not commit local caches/venvs/temp files.
4. Regenerate artifacts and commit generated outputs expected by that adapter.
5. Ensure tests and lint pass locally.
6. Update README when behavior/config/coverage changes.

## 12) Anti-Patterns to Avoid

1. Mixing provider-specific SDK internals into protobuf contracts.
2. Multiple competing host override mechanisms in one adapter.
3. Silent auth fallbacks that hide missing credentials.
4. Hand-editing generated artifacts without updating generators.
5. Writing mock tests that test mocked HTTP responses — they only validate our own mocks.
6. Pushing without running `make lint` and `make test` first.
7. Adding `buf.build/googleapis` deps to buf.yaml without checking CI compatibility.
