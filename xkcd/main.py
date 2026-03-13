"""XKCD MCP server — powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from xkcd_mcp.service import XKCDService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="xkcd-mcp",
        version="0.1.0",
    )
    servicer = XKCDService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
