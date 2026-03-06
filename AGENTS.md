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
- `README.md`
- `Makefile`
- `pyproject.toml`
- `proto/buf.yaml`
- `proto/buf.gen.yaml`
- `proto/<provider>/v1/<provider>.proto`
- `descriptor.binpb` (generated)
- `src/gen/...` (generated protobuf)
- `tests/conftest.py`
- `tests/test_integration.py`

Optional but recommended for generated adapters:

- `openapi/` (or other vendored spec input)
- `scripts/` generation scripts

## 5) Standard Project Layout (Go)

Go adapters typically:

- embed `descriptor.binpb` via `//go:embed`
- initialize with `invariant.ServerFromBytes(...)`
- register a servicer and call `server.Serve(invariant.MCP())`

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

Each adapter should include integration tests that validate:

1. Descriptor loads successfully.
2. Expected tools are registered.
3. CLI projection works for representative methods.
4. HTTP projection works for representative methods.
5. Unknown method/route behavior is correct.

For authenticated adapters, add tests that verify auth/signature headers are actually applied.

Optional: live API tests behind an explicit env gate (never on by default).

## 9) Build/Lint/Test Contract

Provide consistent Make targets:

- `make generate`
- `make descriptor`
- `make lint`
- `make fmt`
- `make serve-mcp`
- `make serve-cli`
- `make test`
- `make clean`

Before finalizing changes to an adapter, run:

1. `make generate` (if generation applies)
2. `make lint`
3. `make test`

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
5. Shipping adapters without descriptor/registration/projection tests.
