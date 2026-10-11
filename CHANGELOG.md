# Changelog

## Unreleased

- Migrate Go and Python adapters to the root Invariant Protocol v0.16.7 module
  and generated native service registration. Preserve existing protobuf fields,
  services and provider authentication configuration.
- Generate descriptors and native bindings from the same graph, and check
  registration and generated output during the repository gate.
- Preserve exact typed int64 values at the Go provider boundary and reject
  malformed numeric or unknown provider fields. Repair Python async HTTP calls
  and connection-pool cleanup.
- Add offline wiring and transport contract checks while retaining explicitly
  gated live provider tests. Restore public Flox CI and dependency audits.
- Update existing Python live fixtures to generated registration and canonical
  tool names. Add a network-blocked entrypoint wiring check, including an
  explicit offline construction seam for Hyperliquid's official SDK.
- Commit the generated gRPC bindings for dockerhub, giphy, googlesheets,
  quicknode and unsplash. Their `<adapter>/<adapter>` binary ignore lines also
  matched the generated package directory, so a fresh clone failed `go vet`
  with an undefined `Register<Service>Server`; those five lines are removed.
