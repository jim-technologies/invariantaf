"""Hyperliquid MCP server — powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

# Add src/ to path so hyperliquid_mcp package is importable.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hyperliquid_mcp.service import HyperliquidService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="hyperliquid-mcp",
        version="0.1.0",
    )
    servicer = HyperliquidService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
