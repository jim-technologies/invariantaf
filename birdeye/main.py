"""Birdeye MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from birdeye_mcp.gen.birdeye.v1 import birdeye_pb2 as _birdeye_pb2  # noqa: F401
from birdeye_mcp.service import DEFAULT_BASE_URL, BirdeyeService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="birdeye-mcp",
        version="0.1.0",
    )

    base_url = (_env("BIRDEYE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = _env("BIRDEYE_API_KEY")

    servicer = BirdeyeService(base_url=base_url, api_key=api_key)
    server.register(servicer, service_name="birdeye.v1.BirdeyeService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
