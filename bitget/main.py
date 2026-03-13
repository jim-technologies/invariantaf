"""Bitget MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bitget_mcp.gen.bitget.v1 import bitget_pb2 as _bitget_pb2  # noqa: F401
from bitget_mcp.service import BitgetService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="bitget-mcp",
        version="0.1.0",
    )
    servicer = BitgetService()
    server.register(servicer, service_name="bitget.v1.BitgetService")
    server.serve_from_argv()


if __name__ == "__main__":
    main()
