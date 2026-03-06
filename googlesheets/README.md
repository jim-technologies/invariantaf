# Google Sheets MCP Server

Full CRUD access to [Google Sheets API v4](https://developers.google.com/sheets/api) -- create spreadsheets, read/write cell values, manage sheets.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `GetSpreadsheet` | API key | Get spreadsheet metadata (title, sheets, properties) |
| `CreateSpreadsheet` | SA | Create a new spreadsheet |
| `GetValues` | API key | Read cell values from a range |
| `BatchGetValues` | API key | Read cell values from multiple ranges |
| `UpdateValues` | SA | Write cell values to a range |
| `AppendValues` | SA | Append rows after existing data |
| `BatchUpdateValues` | SA | Write to multiple ranges |
| `ClearValues` | SA | Clear values from a range |
| `BatchClearValues` | SA | Clear values from multiple ranges |
| `AddSheet` | SA | Add a new sheet tab |
| `DeleteSheet` | SA | Delete a sheet tab by ID |
| `DuplicateSheet` | SA | Duplicate a sheet within the spreadsheet |

**Auth?** column: "API key" = read-only with `GOOGLE_API_KEY`, "SA" = requires `GOOGLE_SERVICE_ACCOUNT_KEY`.

## Quick start

```bash
cd googlesheets
go build -o googlesheets-mcp .

# Run as MCP server (for Claude, Cursor, etc.)
./googlesheets-mcp
# or: go run .
```

## Authentication

| Env var | Required | Description |
|---------|----------|-------------|
| `GOOGLE_API_KEY` | For read-only | API key for reading public sheets |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | For read/write | Base64-encoded service account JSON |
| `GOOGLE_SHEETS_BASE_URL` | No | Override API base URL (default: `https://sheets.googleapis.com`) |

## MCP config

```json
{
  "mcpServers": {
    "googlesheets": {
      "command": "/path/to/googlesheets-mcp",
      "env": {
        "GOOGLE_SERVICE_ACCOUNT_KEY": "<base64-encoded-service-account-json>"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
