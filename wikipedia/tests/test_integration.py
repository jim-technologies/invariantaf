"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as pb
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
            "WikipediaService.Search",
            "WikipediaService.GetPage",
            "WikipediaService.GetFullPage",
            "WikipediaService.GetRandom",
            "WikipediaService.GetOnThisDay",
            "WikipediaService.GetMostRead",
            "WikipediaService.GetLanguages",
            "WikipediaService.GetCategories",
            "WikipediaService.GetLinks",
            "WikipediaService.GetImages",
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
            ["WikipediaService", "Search", "-r", '{"query":"quantum"}']
        )
        assert "results" in result
        assert len(result["results"]) == 2

    def test_get_page(self, server):
        result = server._cli(
            ["WikipediaService", "GetPage", "-r", '{"title":"Albert_Einstein"}']
        )
        assert result.get("title") == "Albert Einstein"

    def test_get_full_page(self, server):
        result = server._cli(
            ["WikipediaService", "GetFullPage", "-r", '{"title":"Albert_Einstein"}']
        )
        assert result.get("title") == "Albert Einstein"
        assert "relativity" in result.get("content", "")

    def test_get_random(self, server):
        result = server._cli(["WikipediaService", "GetRandom"])
        assert "pages" in result
        assert len(result["pages"]) >= 1

    def test_get_on_this_day(self, server):
        result = server._cli(
            ["WikipediaService", "GetOnThisDay", "-r", '{"month":7,"day":4}']
        )
        assert "events" in result
        assert len(result["events"]) == 2

    def test_get_most_read(self, server):
        result = server._cli(
            ["WikipediaService", "GetMostRead", "-r", '{"year":2025,"month":1,"day":14}']
        )
        assert "articles" in result
        assert len(result["articles"]) == 2

    def test_get_languages(self, server):
        result = server._cli(
            ["WikipediaService", "GetLanguages", "-r", '{"title":"Albert_Einstein"}']
        )
        assert "languages" in result
        assert len(result["languages"]) == 3

    def test_get_categories(self, server):
        result = server._cli(
            ["WikipediaService", "GetCategories", "-r", '{"title":"Albert_Einstein"}']
        )
        assert "categories" in result
        assert len(result["categories"]) == 3

    def test_get_links(self, server):
        result = server._cli(
            ["WikipediaService", "GetLinks", "-r", '{"title":"Albert_Einstein"}']
        )
        assert "links" in result
        assert len(result["links"]) == 3

    def test_get_images(self, server):
        result = server._cli(
            ["WikipediaService", "GetImages", "-r", '{"title":"Albert_Einstein"}']
        )
        assert "images" in result
        assert len(result["images"]) == 3

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["WikipediaService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "WikipediaService" in result
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
            "/wikipedia.v1.WikipediaService/Search",
            {"query": "quantum"},
        )
        assert "results" in result

    def test_get_page(self):
        result = self._post(
            "/wikipedia.v1.WikipediaService/GetPage",
            {"title": "Albert_Einstein"},
        )
        assert result.get("title") == "Albert Einstein"

    def test_get_random(self):
        result = self._post("/wikipedia.v1.WikipediaService/GetRandom")
        assert "pages" in result

    def test_get_categories(self):
        result = self._post(
            "/wikipedia.v1.WikipediaService/GetCategories",
            {"title": "Albert_Einstein"},
        )
        assert "categories" in result

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

from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as pb
from wikipedia_mcp.service import WikipediaService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if params and params.get("action") == "query":
        if params.get("list") == "search":
            resp.json.return_value = {{"query": {{"searchinfo": {{"totalhits": 12345}},
                "search": [{{"pageid": 100, "title": "Quantum computing",
                "snippet": "Quantum computing is...", "wordcount": 8500,
                "timestamp": "2025-01-10T12:00:00Z"}}]}}}}
            return resp
        prop = params.get("prop", "")
        if prop == "extracts":
            resp.json.return_value = {{"query": {{"pages": {{"736": {{
                "pageid": 736, "title": "Albert Einstein",
                "extract": "Albert Einstein was a theoretical physicist."}}}}}}}}
            return resp
        if prop == "langlinks":
            resp.json.return_value = {{"query": {{"pages": {{"736": {{
                "pageid": 736, "title": "Albert Einstein",
                "langlinks": [{{"lang": "fr", "*": "Albert Einstein"}}]}}}}}}}}
            return resp
        if prop == "categories":
            resp.json.return_value = {{"query": {{"pages": {{"736": {{
                "pageid": 736, "title": "Albert Einstein",
                "categories": [{{"title": "Category:Nobel laureates"}}]}}}}}}}}
            return resp
        if prop == "links":
            resp.json.return_value = {{"query": {{"pages": {{"736": {{
                "pageid": 736, "title": "Albert Einstein",
                "links": [{{"title": "Theory of relativity"}}]}}}}}}}}
            return resp
        if prop == "images":
            resp.json.return_value = {{"query": {{"pages": {{"736": {{
                "pageid": 736, "title": "Albert Einstein",
                "images": [{{"title": "File:Einstein.jpg"}}]}}}}}}}}
            return resp
    if "/page/summary/" in url:
        resp.json.return_value = {{"title": "Albert Einstein",
            "extract": "Albert Einstein was a physicist.",
            "thumbnail": {{"source": "https://upload.wikimedia.org/thumb/einstein.jpg"}},
            "description": "German-born theoretical physicist",
            "pageid": 736,
            "content_urls": {{"desktop": {{"page": "https://en.wikipedia.org/wiki/Albert_Einstein"}}}}}}
        return resp
    if "/page/random/summary" in url:
        resp.json.return_value = {{"title": "Platypus",
            "extract": "The platypus is a mammal.",
            "thumbnail": {{"source": "https://upload.wikimedia.org/thumb/platypus.jpg"}},
            "description": "Egg-laying mammal", "pageid": 24407,
            "content_urls": {{"desktop": {{"page": "https://en.wikipedia.org/wiki/Platypus"}}}}}}
        return resp
    if "/feed/onthisday/" in url:
        resp.json.return_value = {{"events": [{{"year": 1776,
            "text": "US Declaration of Independence adopted.",
            "pages": [{{"title": "Declaration of Independence",
            "extract": "The Declaration...", "pageid": 3355,
            "content_urls": {{"desktop": {{"page": "https://en.wikipedia.org/wiki/Declaration"}}}}}}]}}]}}
        return resp
    if "/feed/featured/" in url:
        resp.json.return_value = {{"mostread": {{"date": "2025-01-14",
            "articles": [{{"title": "ChatGPT", "views": 250000,
            "extract": "ChatGPT is an AI chatbot.",
            "thumbnail": {{"source": "https://upload.wikimedia.org/thumb/chatgpt.png"}},
            "description": "AI chatbot"}}]}}}}
        return resp
    resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = WikipediaService.__new__(WikipediaService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-wiki", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-wiki"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "WikipediaService.Search" in names
        assert "WikipediaService.GetPage" in names
        assert "WikipediaService.GetRandom" in names

    def test_tool_call_search(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "WikipediaService.Search",
                "arguments": {"query": "quantum"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "results" in result
        assert result["results"][0].get("title") == "Quantum computing"

    def test_tool_call_get_page(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "WikipediaService.GetPage",
                "arguments": {"title": "Albert_Einstein"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("title") == "Albert Einstein"

    def test_tool_call_get_random(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "WikipediaService.GetRandom",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "pages" in result
        assert result["pages"][0].get("title") == "Platypus"

    def test_tool_call_get_on_this_day(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "WikipediaService.GetOnThisDay",
                "arguments": {"month": 7, "day": 4},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "events" in result
        assert result["events"][0].get("year") == 1776

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
            # notification — no id field
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            self._mcp_request(2, "ping", {}),
        ])
        # Should only get responses for id=0 and id=2, not the notification.
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
        server._cli(["WikipediaService", "Search", "-r", '{"query":"test"}'])
        assert len(calls) == 1
        assert calls[0] == "/wikipedia.v1.WikipediaService/Search"

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
        server._cli(["WikipediaService", "GetRandom"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
