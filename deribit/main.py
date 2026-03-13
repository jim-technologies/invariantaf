"""Deribit MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from deribit_mcp.gen.deribit.v1 import deribit_pb2 as _deribit_pb2  # noqa: F401
from deribit_mcp.service import DEFAULT_BASE_URL, DeribitService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="deribit-mcp",
        version="0.1.0",
    )

    base_url = (_env("DERIBIT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = DeribitService(base_url=base_url)
    server.register(servicer, service_name="deribit.v1.DeribitService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
