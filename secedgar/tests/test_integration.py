"""Integration tests -- verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 10

    def test_tool_names(self, server):
        expected = {
            "SECEdgarService.SearchCompany",
            "SECEdgarService.GetCompanyFilings",
            "SECEdgarService.GetCompanyFacts",
            "SECEdgarService.GetCompanyConcept",
            "SECEdgarService.SearchFullText",
            "SECEdgarService.GetFiling",
            "SECEdgarService.GetInsiderTransactions",
            "SECEdgarService.GetInstitutionalHoldings",
            "SECEdgarService.GetTickerToCIK",
            "SECEdgarService.GetRecentFilings",
        }
        actual = set(server.tools.keys())
        missing = expected - actual
        assert not missing, f"Missing tools: {missing}"
        assert expected.issubset(actual)

    def test_tools_have_descriptions(self, server):
        for name, tool in server.tools.items():
            assert tool.description, f"{name} has no description"
            assert len(tool.description) > 10, f"{name} description too short"

    def test_tools_have_input_schemas(self, server):
        for name, tool in server.tools.items():
            schema = tool.input_schema
            assert isinstance(schema, dict), f"{name} schema is not a dict"
            assert schema.get("type") == "object", f"{name} schema type != object"


class TestCLIProjection:
    def test_search_company(self, server):
        result = server._cli(
            ["SECEdgarService", "SearchCompany", "-r", '{"query":"Apple"}']
        )
        assert "companies" in result
        assert len(result["companies"]) >= 1

    def test_get_company_filings(self, server):
        result = server._cli(
            ["SECEdgarService", "GetCompanyFilings", "-r", '{"cik":"320193"}']
        )
        assert "filings" in result
        assert result.get("companyName") == "Apple Inc." or result.get("company_name") == "Apple Inc."

    def test_get_company_facts(self, server):
        result = server._cli(
            ["SECEdgarService", "GetCompanyFacts", "-r", '{"cik":"320193"}']
        )
        assert "facts" in result
        assert len(result["facts"]) > 0

    def test_get_company_concept(self, server):
        result = server._cli(
            ["SECEdgarService", "GetCompanyConcept", "-r", '{"cik":"320193","taxonomy":"us-gaap","concept":"Revenues"}']
        )
        assert "values" in result
        assert len(result["values"]) == 2

    def test_search_full_text(self, server):
        result = server._cli(
            ["SECEdgarService", "SearchFullText", "-r", '{"query":"artificial intelligence"}']
        )
        assert "hits" in result

    def test_get_ticker_to_cik(self, server):
        result = server._cli(
            ["SECEdgarService", "GetTickerToCIK", "-r", '{"ticker":"AAPL"}']
        )
        assert result.get("cik") == "0000320193" or result.get("cik") == "320193"

    def test_get_recent_filings(self, server):
        result = server._cli(
            ["SECEdgarService", "GetRecentFilings"]
        )
        assert "filings" in result
        assert len(result["filings"]) >= 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["SECEdgarService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "SECEdgarService" in result
        assert "SearchCompany" in result

    def test_no_args_shows_usage(self, server):
        result = server._cli([])
        assert "Usage:" in result


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path, body=None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_search_company(self):
        result = self._post(
            "/secedgar.v1.SECEdgarService/SearchCompany",
            {"query": "Apple"},
        )
        assert "companies" in result

    def test_get_company_filings(self):
        result = self._post(
            "/secedgar.v1.SECEdgarService/GetCompanyFilings",
            {"cik": "320193"},
        )
        assert "filings" in result

    def test_get_ticker_to_cik(self):
        result = self._post(
            "/secedgar.v1.SECEdgarService/GetTickerToCIK",
            {"ticker": "AAPL"},
        )
        assert "cik" in result

    def test_get_recent_filings(self):
        result = self._post("/secedgar.v1.SECEdgarService/GetRecentFilings")
        assert "filings" in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


class TestMCPProjection:
    """Test the actual MCP JSON-RPC protocol over stdio."""

    @staticmethod
    def _mcp_request(msg_id, method, params=None):
        msg = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            msg["params"] = params
        return json.dumps(msg)

    @staticmethod
    def _run_mcp_session(messages: list[str]) -> list[dict]:
        import subprocess
        import sys

        stdin_data = "\n".join(messages) + "\n"

        script = f"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as pb
from secedgar_mcp.service import SECEdgarService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/company_tickers" in url:
        resp.json.return_value = {{
            "0": {{"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}},
            "1": {{"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}},
        }}
    elif "/submissions/" in url:
        resp.json.return_value = {{
            "cik": "320193", "name": "Apple Inc.", "tickers": ["AAPL"],
            "filings": {{"recent": {{
                "accessionNumber": ["0000320193-23-000077"],
                "form": ["10-K"], "filingDate": ["2023-11-03"],
                "primaryDocument": ["aapl-20230930.htm"],
                "primaryDocDescription": ["10-K Annual Report"],
                "reportDate": ["2023-09-30"],
            }}}},
        }}
    elif "/companyfacts/" in url:
        resp.json.return_value = {{
            "cik": 320193, "entityName": "Apple Inc.",
            "facts": {{"us-gaap": {{"Revenues": {{
                "label": "Revenues",
                "units": {{"USD": [{{
                    "val": 394328000000, "accn": "0000320193-23-000077",
                    "fy": 2023, "fp": "FY", "form": "10-K",
                    "filed": "2023-11-03", "start": "2022-10-01", "end": "2023-09-30",
                }}]}},
            }}}}}},
        }}
    elif "/companyconcept/" in url:
        resp.json.return_value = {{
            "cik": 320193, "taxonomy": "us-gaap", "tag": "Revenues",
            "label": "Revenues", "description": "Amount of revenue.",
            "units": {{"USD": [{{
                "val": 394328000000, "accn": "0000320193-23-000077",
                "fy": 2023, "fp": "FY", "form": "10-K",
                "filed": "2023-11-03", "start": "2022-10-01", "end": "2023-09-30",
            }}]}},
        }}
    elif "search-index" in url:
        q = (params or {{}}).get("q", "")
        if q == "Apple":
            resp.json.return_value = {{
                "hits": {{"total": {{"value": 1}}, "hits": [{{
                    "_source": {{"entity_id": 320193, "entity_name": "Apple Inc.",
                        "tickers": ["AAPL"], "display_names": ["Apple Inc."]}},
                }}]}},
            }}
        else:
            resp.json.return_value = {{
                "hits": {{"total": {{"value": 1}}, "hits": [{{
                    "_source": {{"file_num": "0000320193-23-000077", "form_type": "10-K",
                        "file_date": "2023-11-03", "entity_name": "Apple Inc.",
                        "entity_id": 320193, "display_names": ["Apple Inc. 10-K"],
                        "file_url": "https://sec.gov/test", "period_of_report": "2023-09-30"}},
                }}]}},
            }}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = SECEdgarService.__new__(SECEdgarService)
svc._http = http
svc._data_url = "https://data.sec.gov"
svc._efts_url = "https://efts.sec.gov/LATEST"

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-secedgar", version="0.0.1")
server.register(svc)
server.serve(mcp=True)
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=10,
        )

        responses = []
        for line in proc.stdout.strip().split("\n"):
            if line.strip():
                responses.append(json.loads(line))
        return responses

    def test_initialize(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            }),
        ])
        assert len(responses) == 1
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["result"]["serverInfo"]["name"] == "test-secedgar"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "SECEdgarService.SearchCompany" in names
        assert "SECEdgarService.GetCompanyFilings" in names
        assert "SECEdgarService.GetTickerToCIK" in names

    def test_tool_call_search_company(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SECEdgarService.SearchCompany",
                "arguments": {"query": "Apple"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "companies" in result
        c = result["companies"][0]
        assert c.get("name") == "Apple Inc."

    def test_tool_call_get_ticker_to_cik(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SECEdgarService.GetTickerToCIK",
                "arguments": {"ticker": "AAPL"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("cik") == "0000320193"

    def test_tool_call_get_recent_filings(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "SECEdgarService.GetRecentFilings",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "filings" in result

    def test_unknown_tool(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "DoesNotExist",
                "arguments": {},
            }),
        ])
        resp = responses[1]
        assert "error" in resp or resp.get("result", {}).get("isError") is True

    def test_ping(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "ping", {}),
        ])
        assert responses[1]["result"] == {}

    def test_unknown_method(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "unknown/method", {}),
        ])
        assert "error" in responses[1]
        assert responses[1]["error"]["code"] == -32601

    def test_notification_ignored(self):
        """Notifications (no id) should not produce a response."""
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
        ids = [r.get("id") for r in responses]
        assert 0 in ids
        assert 2 in ids
        assert len(responses) == 2


class TestInterceptor:
    def test_interceptor_fires(self, server):
        calls = []

        def logging_interceptor(request, context, info, handler):
            calls.append(info.full_method)
            return handler(request, context)

        server.use(logging_interceptor)
        server._cli(["SECEdgarService", "GetRecentFilings"])
        assert len(calls) == 1
        assert calls[0] == "/secedgar.v1.SECEdgarService/GetRecentFilings"

    def test_interceptor_chain_order(self, server):
        order = []

        def interceptor_a(request, context, info, handler):
            order.append("A-before")
            resp = handler(request, context)
            order.append("A-after")
            return resp

        def interceptor_b(request, context, info, handler):
            order.append("B-before")
            resp = handler(request, context)
            order.append("B-after")
            return resp

        server.use(interceptor_a)
        server.use(interceptor_b)
        server._cli(["SECEdgarService", "GetRecentFilings"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
