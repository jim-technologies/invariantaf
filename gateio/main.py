"""Gate.io MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from gateio_mcp.gen.gateio.v1 import gateio_pb2 as _gateio_pb2  # noqa: F401
from gateio_mcp.service import GateioService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"

def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="gateio-mcp",
        version="0.1.0",
    )
    servicer = GateioService()
    server.register(servicer, service_name="gateio.v1.GateioService")
    server.serve_from_argv()

if __name__ == "__main__":
    main()
