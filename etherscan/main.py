"""Etherscan MCP server -- powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from etherscan_mcp.service import EtherscanService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="etherscan-mcp",
        version="0.1.0",
    )
    servicer = EtherscanService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
