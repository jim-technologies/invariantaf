"""Alternative.me MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from alternativeme_mcp.gen.alternativeme.v1 import alternativeme_pb2 as _alternativeme_pb2  # noqa: F401
from alternativeme_mcp.service import DEFAULT_BASE_URL, AlternativeMeService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="alternativeme-mcp",
        version="0.1.0",
    )

    base_url = (_env("ALTERNATIVEME_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = AlternativeMeService(base_url=base_url)
    server.register(servicer, service_name="alternativeme.v1.AlternativeMeService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
