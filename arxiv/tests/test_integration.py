"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as pb
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
            "ArxivService.Search",
            "ArxivService.GetPaper",
            "ArxivService.SearchByAuthor",
            "ArxivService.SearchByTitle",
            "ArxivService.SearchByCategory",
            "ArxivService.SearchByAbstract",
            "ArxivService.GetRecent",
            "ArxivService.GetMultiple",
            "ArxivService.AdvancedSearch",
            "ArxivService.GetCategories",
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
    def test_search(self, server):
        result = server._cli(
            ["ArxivService", "Search", "-r", '{"query":"attention"}']
        )
        assert "papers" in result
        assert len(result["papers"]) >= 1

    def test_get_paper(self, server):
        result = server._cli(
            ["ArxivService", "GetPaper", "-r", '{"arxiv_id":"1706.03762"}']
        )
        assert "paper" in result
        assert result["paper"]["title"] == "Attention Is All You Need"

    def test_search_by_author(self, server):
        result = server._cli(
            ["ArxivService", "SearchByAuthor", "-r", '{"author":"Vaswani"}']
        )
        assert "papers" in result
        assert len(result["papers"]) >= 1

    def test_search_by_title(self, server):
        result = server._cli(
            ["ArxivService", "SearchByTitle", "-r", '{"title":"attention"}']
        )
        assert "papers" in result

    def test_search_by_category(self, server):
        result = server._cli(
            ["ArxivService", "SearchByCategory", "-r", '{"category":"cs.AI"}']
        )
        assert "papers" in result

    def test_get_categories(self, server):
        result = server._cli(["ArxivService", "GetCategories"])
        assert "categories" in result
        assert len(result["categories"]) > 0

    def test_get_recent(self, server):
        result = server._cli(
            ["ArxivService", "GetRecent", "-r", '{"category":"cs.AI"}']
        )
        assert "papers" in result

    def test_advanced_search(self, server):
        result = server._cli(
            ["ArxivService", "AdvancedSearch", "-r", '{"author":"Vaswani","title":"attention"}']
        )
        assert "papers" in result

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["ArxivService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "ArxivService" in result
        assert "Search" in result

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

    def test_search(self):
        result = self._post(
            "/arxiv.v1.ArxivService/Search",
            {"query": "attention"},
        )
        assert "papers" in result

    def test_get_categories(self):
        result = self._post("/arxiv.v1.ArxivService/GetCategories")
        assert "categories" in result

    def test_get_paper(self):
        result = self._post(
            "/arxiv.v1.ArxivService/GetPaper",
            {"arxiv_id": "1706.03762"},
        )
        assert "paper" in result

    def test_get_recent(self):
        result = self._post(
            "/arxiv.v1.ArxivService/GetRecent",
            {"category": "cs.AI"},
        )
        assert "papers" in result

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

from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as pb
from arxiv_mcp.service import ArxivService
from invariant import Server

FAKE_SEARCH_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models.</summary>
    <author><name>Ashish Vaswani</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.AI"/>
    <published>2017-06-12T17:57:34Z</published>
    <updated>2023-08-02T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v7" rel="related" type="application/pdf"/>
    <link href="http://arxiv.org/abs/1706.03762v7" rel="alternate" type="text/html"/>
  </entry>
</feed>'''

http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.text = FAKE_SEARCH_XML
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = ArxivService.__new__(ArxivService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-arxiv", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-arxiv"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "ArxivService.Search" in names
        assert "ArxivService.GetPaper" in names
        assert "ArxivService.GetCategories" in names

    def test_tool_call_search(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "ArxivService.Search",
                "arguments": {"query": "attention"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "papers" in result
        papers = result["papers"]
        assert len(papers) >= 1
        paper = papers[0]
        assert paper.get("arxivId") == "1706.03762v7" or paper.get("arxiv_id") == "1706.03762v7"

    def test_tool_call_get_categories(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "ArxivService.GetCategories",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "categories" in result
        assert len(result["categories"]) > 0

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
        server._cli(["ArxivService", "GetCategories"])
        assert len(calls) == 1
        assert calls[0] == "/arxiv.v1.ArxivService/GetCategories"

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
        server._cli(["ArxivService", "GetCategories"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
