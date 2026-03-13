"""Football-Data.org MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from footballdata_mcp.gen.footballdata.v1 import footballdata_pb2 as _footballdata_pb2  # noqa: F401
from footballdata_mcp.service import DEFAULT_BASE_URL, FootballDataService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="footballdata-mcp",
        version="0.1.0",
    )

    base_url = (_env("FOOTBALLDATA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = _env("FOOTBALLDATA_API_KEY")

    servicer = FootballDataService(base_url=base_url, api_key=api_key)
    server.register(servicer, service_name="footballdata.v1.FootballDataService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
