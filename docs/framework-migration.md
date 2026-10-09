# Native framework migration

The source candidate uses Invariant Protocol v0.16.7. Go imports remain
`github.com/jim-technologies/invariantprotocol/go`; `go.mod` requires the root
module. Python locks pin the same release at an immutable source revision.
Existing protobuf services, methods, fields, enums and authored `go_package`
options remain unchanged.

## Source coverage

The 37 Go modules contain 36 local provider implementations and the Temporal
forwarding adapter. Local providers expose 530 RPCs, including 375 typed
responses. Generated, explicit registration connects the canonical protobuf
service to its provider implementation. The forwarding adapter uses the
framework's native gRPC connection API.

The 80 Python adapters include 74 native generated registrations and six
descriptor-backed HTTP proxies. Registration uses generated gRPC functions;
MCP, CLI and HTTP use framework projections. Python HTTP helpers await their
async client operations and close the actual stored client. Provider parsing
and authentication remain local to each adapter.

Go MCP, CLI and HTTP run through `ServeProjections`. Native gRPC runs through
`Serve(listener)` with a signal context and a bounded drain before forced
shutdown. Python native gRPC uses its async native server.

## Contract boundaries

The Go generator preserves protobuf int64 and uint64 request values as decimal
strings at the existing generic provider boundary. Numeric consumers parse
them explicitly and reject invalid values or conversions outside the exact
double-number range. Typed replies retain `json.Number` through raw JSON into
ProtoJSON without a floating-point Struct intermediate. Canonical dynamic
Struct responses retain their declared double-number domain.

Typed response decoding rejects unknown and malformed fields. A response with
one declared message, map or repeated field can bind an existing raw provider
object or list envelope to that field; scalar responses require the named
canonical field. This is descriptor-derived binding, not a new provider schema.
Known provider aliases are normalized at their provider boundary.

## Reproduction

Run from the repository root:

```sh
flox activate -- make generate-go
flox activate -- python3 scripts/generate-python-adapters --write
flox activate -- make validate
flox activate -- make audit
```

Both generators first build the canonical FileDescriptorSet and then generate
native bindings from that graph. Source info is retained in the embedded graph.
Go uses standard plugin mappings when a source file has no `go_package`;
generation does not rewrite authored options. `make generate-check` rebuilds
both language projections in temporary directories and rejects drift.

The Flox environment supplies a checksum-selected Go 1.27.2 toolchain, Python
3.14.7, Buf 1.72.0 and protoc 36.1. Go dependency audits include tests and require
module checksum verification. Python audits scan locked environments without
ignoring findings.

## Qualification and rollback

The default gate proves source compilation, native wiring, generated graph
agreement and offline contract behavior. Loopback gRPC and Connect tests prove
exact integers above 2^53 and strict provider-response decoding. These checks
do not prove compatibility with every current upstream provider payload or
credential scope. Existing live API tests remain opt-in and require the named
provider environment gate; authenticated tests also require credentials.

`make wiring-check` imports each actual Python entrypoint in a separate locked
environment, compiles its generated registrar expressions, constructs real
services with synthetic credential arguments, checks canonical method and
message identities, and closes clients. A socket/DNS audit hook rejects
provider I/O. The helper does not run `main`, auth derivation or a provider RPC.
Hyperliquid uses an injected official SDK `Info` constructed with complete
synthetic metadata and WebSockets disabled; its default eager live metadata
construction is preserved and is not qualified by this offline check.

Jito's documented provider status keys are explicitly normalized into its
existing response. Unknown row fields and malformed envelopes fail. Its
current protobuf response has no nullable status entry, so unsupported
not-found null responses fail rather than inventing an empty success. See the
[Jito provider contract](https://docs.jito.wtf/lowlatencytxnsend/#getbundlestatuses).

The Temporal forwarding descriptor remains the checked-in historical artifact.
Its original upstream revision is unverified; local descriptor regeneration
checks cover the 36 source-owning Go providers. A Temporal descriptor refresh
requires an explicit immutable upstream commit and separate graph review.

No provider job, account action or deployment is authorized by this source
candidate. Live provider qualification and release publication are separate
steps. Reverting the source commit and its dependency/generated artifacts
restores the previous source state; this migration changes no persisted data.
