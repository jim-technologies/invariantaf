"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as pb
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
            "HackerNewsService.GetTopStories",
            "HackerNewsService.GetNewStories",
            "HackerNewsService.GetBestStories",
            "HackerNewsService.GetAskStories",
            "HackerNewsService.GetShowStories",
            "HackerNewsService.GetJobStories",
            "HackerNewsService.GetItem",
            "HackerNewsService.GetUser",
            "HackerNewsService.GetComments",
            "HackerNewsService.GetMaxItem",
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
    def test_get_top_stories(self, server):
        result = server._cli(
            ["HackerNewsService", "GetTopStories", "-r", '{"limit":2}']
        )
        assert "items" in result
        assert len(result["items"]) == 2

    def test_get_new_stories(self, server):
        result = server._cli(
            ["HackerNewsService", "GetNewStories", "-r", '{"limit":1}']
        )
        assert "items" in result
        assert len(result["items"]) == 1

    def test_get_best_stories(self, server):
        result = server._cli(["HackerNewsService", "GetBestStories"])
        assert "items" in result

    def test_get_ask_stories(self, server):
        result = server._cli(["HackerNewsService", "GetAskStories"])
        assert "items" in result

    def test_get_show_stories(self, server):
        result = server._cli(["HackerNewsService", "GetShowStories"])
        assert "items" in result

    def test_get_job_stories(self, server):
        result = server._cli(["HackerNewsService", "GetJobStories"])
        assert "items" in result

    def test_get_item(self, server):
        result = server._cli(
            ["HackerNewsService", "GetItem", "-r", '{"id":41881548}']
        )
        assert "item" in result
        assert result["item"].get("title") == "Hacking the attention economy"

    def test_get_user(self, server):
        result = server._cli(
            ["HackerNewsService", "GetUser", "-r", '{"id":"pg"}']
        )
        assert "user" in result
        assert result["user"].get("id") == "pg"

    def test_get_comments(self, server):
        result = server._cli(
            ["HackerNewsService", "GetComments", "-r", '{"story_id":41881548,"depth":1}']
        )
        assert "comments" in result
        assert len(result["comments"]) == 3

    def test_get_max_item(self, server):
        result = server._cli(["HackerNewsService", "GetMaxItem"])
        # int64 fields may be serialized as strings in JSON
        val = result.get("maxId") or result.get("max_id")
        assert int(val) == 41882000

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["HackerNewsService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "HackerNewsService" in result
        assert "GetTopStories" in result

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

    def test_get_top_stories(self):
        result = self._post(
            "/hackernews.v1.HackerNewsService/GetTopStories",
            {"limit": 2},
        )
        assert "items" in result

    def test_get_item(self):
        result = self._post(
            "/hackernews.v1.HackerNewsService/GetItem",
            {"id": 41881548},
        )
        assert "item" in result

    def test_get_max_item(self):
        result = self._post("/hackernews.v1.HackerNewsService/GetMaxItem")
        assert "maxId" in result or "max_id" in result

    def test_get_user(self):
        result = self._post(
            "/hackernews.v1.HackerNewsService/GetUser",
            {"id": "pg"},
        )
        assert "user" in result

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

from hackernews_mcp.gen.hackernews.v1 import hackernews_pb2 as pb
from hackernews_mcp.service import HackerNewsService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/topstories.json" in url:
        resp.json.return_value = [41881548, 41881549]
    elif "/newstories.json" in url:
        resp.json.return_value = [41881549, 41881548]
    elif "/beststories.json" in url:
        resp.json.return_value = [41881548]
    elif "/askstories.json" in url:
        resp.json.return_value = [41881550]
    elif "/showstories.json" in url:
        resp.json.return_value = [41881549]
    elif "/jobstories.json" in url:
        resp.json.return_value = [41881551]
    elif "/maxitem.json" in url:
        resp.json.return_value = 41882000
    elif "/user/pg.json" in url:
        resp.json.return_value = {{"id": "pg", "created": 1160418111, "karma": 157236,
            "about": "Bug fixer.", "submitted": [41881548]}}
    elif "/item/41881548.json" in url:
        resp.json.return_value = {{"id": 41881548, "type": "story", "by": "pg",
            "time": 1700000000, "title": "Hacking the attention economy",
            "url": "https://example.com/hacking-attention", "score": 342,
            "descendants": 187, "kids": [41881600]}}
    elif "/item/41881549.json" in url:
        resp.json.return_value = {{"id": 41881549, "type": "story", "by": "dang",
            "time": 1700000100, "title": "Show HN: A new way to build compilers",
            "url": "https://example.com/compilers", "score": 128,
            "descendants": 45, "kids": []}}
    elif "/item/41881550.json" in url:
        resp.json.return_value = {{"id": 41881550, "type": "story", "by": "tptacek",
            "time": 1700000200, "title": "Ask HN: What are you working on?",
            "text": "Curious what side projects people are building.",
            "score": 95, "descendants": 210, "kids": []}}
    elif "/item/41881551.json" in url:
        resp.json.return_value = {{"id": 41881551, "type": "job", "by": "ycombinator",
            "time": 1700000300, "title": "YC is hiring a software engineer",
            "url": "https://ycombinator.com/careers"}}
    elif "/item/41881600.json" in url:
        resp.json.return_value = {{"id": 41881600, "type": "comment", "by": "jsmith",
            "time": 1700000400, "text": "Great article!", "parent": 41881548, "kids": []}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = HackerNewsService.__new__(HackerNewsService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-hn", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-hn"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "HackerNewsService.GetTopStories" in names
        assert "HackerNewsService.GetItem" in names
        assert "HackerNewsService.GetMaxItem" in names

    def test_tool_call_get_top_stories(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "HackerNewsService.GetTopStories",
                "arguments": {"limit": 2},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "items" in result
        assert len(result["items"]) == 2

    def test_tool_call_get_item(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "HackerNewsService.GetItem",
                "arguments": {"id": 41881548},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "item" in result
        assert result["item"].get("title") == "Hacking the attention economy"

    def test_tool_call_get_max_item(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "HackerNewsService.GetMaxItem",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        # int64 fields may be serialized as strings in JSON
        val = result.get("maxId") or result.get("max_id")
        assert int(val) == 41882000

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
        server._cli(["HackerNewsService", "GetMaxItem"])
        assert len(calls) == 1
        assert calls[0] == "/hackernews.v1.HackerNewsService/GetMaxItem"

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
        server._cli(["HackerNewsService", "GetTopStories"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
