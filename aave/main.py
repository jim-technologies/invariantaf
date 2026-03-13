"""Aave MCP server -- GraphQL-backed via Invariant Protocol."""

from __future__ import annotations

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aave_mcp.service import AaveService  # noqa: E402

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="aave-mcp",
        version="0.1.0",
    )
    servicer = AaveService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
