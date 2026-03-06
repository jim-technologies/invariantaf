# Package Registry MCP Server

Package metadata from [NPM](https://www.npmjs.com/) and [PyPI](https://pypi.org/), the two largest package registries for JavaScript and Python.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchNPM` | No | Search for NPM packages by keyword |
| `GetNPMPackage` | No | Get detailed metadata for an NPM package |
| `GetNPMDownloads` | No | Get weekly download count for an NPM package |
| `GetNPMVersions` | No | List all published versions of an NPM package |
| `GetNPMDependencies` | No | Get dependencies for an NPM package |
| `GetPyPIPackage` | No | Get detailed metadata for a Python package from PyPI |
| `GetPyPIVersion` | No | Get metadata for a specific version of a Python package |
| `GetPyPIReleases` | No | List all released versions of a Python package |
| `GetPyPIDownloads` | No | Get recent download statistics for a Python package |
| `GetPyPIDependencies` | No | Get dependencies for a Python package |

## Quick start

```bash
# Install
cd packageregistry
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli PackageRegistryService GetNPMPackage -r '{"name": "react"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

No authentication required.

## MCP config

```json
{
  "mcpServers": {
    "packageregistry": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/packageregistry", "python", "main.py"]
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
