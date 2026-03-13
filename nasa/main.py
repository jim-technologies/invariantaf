"""NASA MCP server — powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nasa_mcp.service import NASAService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="nasa-mcp",
        version="0.1.0",
    )
    servicer = NASAService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
