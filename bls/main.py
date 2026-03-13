"""BLS (Bureau of Labor Statistics) MCP server -- powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bls_mcp.service import BLSService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="bls-mcp",
        version="0.1.0",
    )
    servicer = BLSService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
