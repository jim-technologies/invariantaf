"""Slack MCP server -- Slack Web API via Invariant Protocol."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ensure generated descriptors are loaded into the default descriptor pool.
from slack_mcp.gen.slack.v1 import slack_pb2 as _slack_pb2  # noqa: F401
from slack_mcp.service import SlackService

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
    server.register(SlackService(), service_name="slack.v1.SlackService")
    asyncio.run(server.serve(**_projection_from_argv(sys.argv[1:])))


if __name__ == "__main__":
    main()
