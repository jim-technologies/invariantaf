"""Telegram MCP server -- Telegram Bot API via Invariant Protocol."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from telegram_mcp.gen.telegram.v1 import telegram_pb2 as _telegram_pb2  # noqa: F401
from telegram_mcp.service import TelegramService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def _projection_from_argv(argv: list[str]) -> dict:
    """Parse [--mcp|--cli|--http [port]|--grpc [port]] into serve() kwargs."""
    if not argv:
        return {"mcp": True}
    cmd = argv[0]
    if cmd in ("--mcp", "mcp", ""):
        return {"mcp": True}
    if cmd in ("--cli", "cli"):
        return {"cli": True}
    if cmd in ("--http", "http"):
        port = int(argv[1]) if len(argv) > 1 else 8080
        return {"http": port}
    if cmd in ("--grpc", "grpc"):
        port = int(argv[1]) if len(argv) > 1 else 50051
        return {"grpc": port}
    return {"mcp": True}


def main() -> None:
    server = Server.from_descriptor(str(DESCRIPTOR))
    server.register(TelegramService(), service_name="telegram.v1.TelegramService")
    asyncio.run(server.serve(**_projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()
