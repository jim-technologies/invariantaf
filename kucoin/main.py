"""KuCoin MCP server -- powered by Invariant Protocol."""

from __future__ import annotations

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from kucoin_mcp.gen.kucoin.v1 import kucoin_pb2 as _kucoin_pb2  # noqa: F401
from kucoin_mcp.service import KucoinService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main() -> None:
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="kucoin-mcp",
        version="0.1.0",
    )
    servicer = KucoinService()
    server.register(servicer, service_name="kucoin.v1.KucoinService")
    server.serve_from_argv()


if __name__ == "__main__":
    main()
