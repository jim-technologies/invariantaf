"""NWS MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated protobuf descriptors are loaded in the default descriptor pool.
from nws_mcp.gen.nws.v1 import nws_pb2 as _nws_pb2  # noqa: F401
from nws_mcp.service import DEFAULT_BASE_URL, NwsService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="nws-mcp",
        version="0.1.0",
    )

    base_url = (_env("NWS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    servicer = NwsService(base_url=base_url)
    server.register(servicer, service_name="nws.v1.NwsService")

    server.serve_from_argv()


if __name__ == "__main__":
    main()
