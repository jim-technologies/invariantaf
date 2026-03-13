"""Manifold Markets MCP server -- descriptor-driven HTTP proxy via Invariant Protocol."""

from __future__ import annotations

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded into the default descriptor pool.
from gen.manifold.v1 import manifold_pb2 as _manifold_pb2  # noqa: F401

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"

DEFAULT_BASE_URL = "https://api.manifold.markets/v0"


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="manifold-mcp",
        version="0.1.0",
    )

    base_url = DEFAULT_BASE_URL.rstrip("/")

    server.connect_http(base_url, service_name="manifold.v1.ManifoldService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
