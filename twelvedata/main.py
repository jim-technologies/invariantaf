"""Twelve Data MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from twelvedata_mcp.gen.twelvedata.v1 import twelvedata_pb2 as _twelvedata_pb2  # noqa: F401
from twelvedata_mcp.service import DEFAULT_BASE_URL, TwelveDataService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="twelvedata-mcp",
        version="0.1.0",
    )

    base_url = (_env("TWELVEDATA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = _env("TWELVEDATA_API_KEY")

    servicer = TwelveDataService(base_url=base_url, api_key=api_key)
    server.register(servicer, service_name="twelvedata.v1.TwelveDataService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
