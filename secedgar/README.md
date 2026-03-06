# SEC EDGAR MCP Server

U.S. Securities and Exchange Commission [EDGAR](https://www.sec.gov/edgar) filings, financial data, and company information.

Built with [Invariant Protocol](https://github.com/jim-technologies/invariantprotocol). Every tool description comes from proto comments.

## Tools

| Tool | Auth? | Description |
|------|-------|-------------|
| `SearchCompany` | No | Search for companies by name, ticker, or keyword |
| `GetCompanyFilings` | No | Get recent filings for a company by CIK number |
| `GetCompanyFacts` | No | Get all XBRL financial facts (revenue, net income, assets, etc.) |
| `GetCompanyConcept` | No | Get a single financial concept over time (e.g., revenue history) |
| `SearchFullText` | No | Full-text search across all SEC filings |
| `GetFiling` | No | Get details of a specific filing by accession number |
| `GetInsiderTransactions` | No | Get insider trading (Form 4) data for a company |
| `GetInstitutionalHoldings` | No | Get 13F institutional holdings data |
| `GetTickerToCIK` | No | Look up CIK number from ticker symbol |
| `GetRecentFilings` | No | Get the most recent filings across all companies |

## Quick start

```bash
# Install
cd secedgar
uv sync

# Run as MCP server (for Claude, Cursor, etc.)
uv run python main.py

# Run as CLI
uv run python main.py --cli SECEdgarService GetTickerToCIK -r '{"ticker": "AAPL"}'
uv run python main.py --cli SECEdgarService GetCompanyFacts -r '{"cik": "320193"}'

# Run as HTTP server
uv run python main.py --http 8080
```

## Authentication

None required. SEC EDGAR is free and public. The SEC requires a User-Agent header with contact info. Set via `SEC_EDGAR_USER_AGENT` env var (defaults to `InvariantMCP/1.0 (contact@example.com)`).

## MCP config

```json
{
  "mcpServers": {
    "secedgar": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/secedgar", "python", "main.py"],
      "env": {
        "SEC_EDGAR_USER_AGENT": "MyApp/1.0 (your-email@example.com)"
      }
    }
  }
}
```

## Regenerate protos

```bash
make generate
```
