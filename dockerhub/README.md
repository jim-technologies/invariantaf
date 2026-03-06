# Docker Hub MCP Server

Container image metadata from [Docker Hub](https://hub.docker.com/) -- search repositories, inspect tags, browse categories, and discover extensions.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchRepositories` | No | Search Docker Hub for repositories matching a query |
| `GetRepository` | No | Get detailed information about a specific repository |
| `GetTags` | No | List all tags for a repository with pagination |
| `GetTag` | No | Get detailed information about a specific tag |
| `GetNamespaceRepositories` | No | List all repositories in a given namespace |
| `GetTopImages` | No | Get the most popular official Docker images |
| `GetBuildHistory` | No | Get the automated build history for a repository |
| `GetDockerfileContent` | No | Get the Dockerfile content for a repository |
| `GetCategories` | No | Get the list of Docker Hub content categories |
| `GetExtensions` | No | Get the Docker extensions catalog |

## Quick start

```bash
# Install
cd dockerhub
go build -o dockerhub-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
./dockerhub-mcp
# or: go run .
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "dockerhub": {
      "command": "/path/to/dockerhub-mcp"
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
