"""GitHub MCP server — powered by Invariant Protocol."""

import sys
from pathlib import Path

from invariant import Server

sys.path.insert(0, str(Path(__file__).parent / "src"))

from github_mcp.service import GitHubService

DESCRIPTOR = Path(__file__).parent / "descriptor.binpb"


def main():
    server = Server.from_descriptor(
        str(DESCRIPTOR),
        name="github-mcp",
        version="0.1.0",
    )
    servicer = GitHubService()
    server.register(servicer)

    server.serve_from_argv()


if __name__ == "__main__":
    main()
