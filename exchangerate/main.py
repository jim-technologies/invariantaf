"""Exchange Rate MCP server — powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from exchangerate_mcp.service import ExchangeRateService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="exchangerate-mcp",
        version="0.1.0",
    )
    servicer = ExchangeRateService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
