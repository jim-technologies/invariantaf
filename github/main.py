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

    args = sys.argv[1:]
    if "--cli" in args:
        idx = args.index("--cli")
        sys.argv = [sys.argv[0], *args[idx + 1 :]]
        server.serve(cli=True)
    elif "--http" in args:
        port = 8080
        idx = args.index("--http")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(http=port)
    elif "--grpc" in args:
        port = 50051
        idx = args.index("--grpc")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            port = int(args[idx + 1])
        server.serve(grpc=port)
    else:
        server.serve(mcp=True)


if __name__ == "__main__":
    main()
