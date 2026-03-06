"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as pb
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
            "XKCDService.GetLatest",
            "XKCDService.GetComic",
            "XKCDService.GetRandom",
            "XKCDService.GetRange",
            "XKCDService.SearchByTitle",
            "XKCDService.GetExplanation",
            "XKCDService.GetComicCount",
            "XKCDService.GetMultiple",
            "XKCDService.GetRecent",
            "XKCDService.GetByDate",
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
    def test_get_latest(self, server):
        result = server._cli(["XKCDService", "GetLatest"])
        assert "comic" in result
        assert result["comic"]["num"] == 3000

    def test_get_comic(self, server):
        result = server._cli(
            ["XKCDService", "GetComic", "-r", '{"num": 1}']
        )
        assert "comic" in result
        assert result["comic"]["num"] == 1
        assert result["comic"]["title"] == "Barrel - Part 1"

    def test_get_random(self, server):
        result = server._cli(["XKCDService", "GetRandom"])
        assert "comic" in result
        assert result["comic"]["num"] > 0

    def test_get_range(self, server):
        result = server._cli(
            ["XKCDService", "GetRange", "-r", '{"start_num": 2998, "end_num": 3000}']
        )
        assert "comics" in result
        assert len(result["comics"]) == 3

    def test_search_by_title(self, server):
        result = server._cli(
            ["XKCDService", "SearchByTitle", "-r", '{"query": "Latest", "search_count": 5}']
        )
        assert "comics" in result

    def test_get_explanation(self, server):
        result = server._cli(
            ["XKCDService", "GetExplanation", "-r", '{"num": 353}']
        )
        assert result.get("num") == 353
        assert "Python" in result.get("title", "")

    def test_get_comic_count(self, server):
        result = server._cli(["XKCDService", "GetComicCount"])
        assert result.get("count") == 3000

    def test_get_multiple(self, server):
        result = server._cli(
            ["XKCDService", "GetMultiple", "-r", '{"nums": [1, 353]}']
        )
        assert "comics" in result
        assert len(result["comics"]) == 2

    def test_get_recent(self, server):
        result = server._cli(
            ["XKCDService", "GetRecent", "-r", '{"count": 3}']
        )
        assert "comics" in result
        assert len(result["comics"]) == 3

    def test_get_by_date(self, server):
        result = server._cli(
            ["XKCDService", "GetByDate", "-r", '{"year": 2025, "month": 3, "search_count": 5}']
        )
        assert "comics" in result

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["XKCDService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "XKCDService" in result
        assert "GetLatest" in result

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

    def test_get_latest(self):
        result = self._post("/xkcd.v1.XKCDService/GetLatest")
        assert "comic" in result

    def test_get_comic(self):
        result = self._post(
            "/xkcd.v1.XKCDService/GetComic",
            {"num": 1},
        )
        assert "comic" in result

    def test_get_comic_count(self):
        result = self._post("/xkcd.v1.XKCDService/GetComicCount")
        assert result.get("count") == 3000

    def test_get_explanation(self):
        result = self._post(
            "/xkcd.v1.XKCDService/GetExplanation",
            {"num": 353},
        )
        assert result.get("num") == 353

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

from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as pb
from xkcd_mcp.service import XKCDService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "explainxkcd.com" in url:
        resp.json.return_value = {{"parse": {{"title": "353: Python", "pageid": 394,
            "wikitext": {{"*": "Explanation about Python programming."}}}}}}
    elif "/info.0.json" in url:
        # Extract comic number from URL pattern.
        import re as _re
        m = _re.search(r"xkcd\\.com/(\\d+)/info\\.0\\.json", url)
        if m:
            num = int(m.group(1))
            resp.json.return_value = {{"num": num, "title": f"Comic {{num}}",
                "safe_title": f"Comic {{num}}", "alt": f"Alt {{num}}.",
                "img": f"https://imgs.xkcd.com/comics/c_{{num}}.png",
                "year": "2025", "month": "3", "day": "1",
                "link": "", "news": "", "transcript": ""}}
        else:
            resp.json.return_value = {{"num": 3000, "title": "The Latest Comic",
                "safe_title": "The Latest Comic", "alt": "Hover text.",
                "img": "https://imgs.xkcd.com/comics/latest.png",
                "year": "2025", "month": "3", "day": "3",
                "link": "", "news": "", "transcript": ""}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = XKCDService.__new__(XKCDService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-xkcd", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-xkcd"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "XKCDService.GetLatest" in names
        assert "XKCDService.GetComic" in names
        assert "XKCDService.GetRandom" in names

    def test_tool_call_get_latest(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "XKCDService.GetLatest",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "comic" in result
        assert result["comic"]["num"] == 3000

    def test_tool_call_get_comic(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "XKCDService.GetComic",
                "arguments": {"num": 1},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "comic" in result
        assert result["comic"]["num"] == 1

    def test_tool_call_get_comic_count(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "XKCDService.GetComicCount",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("count") == 3000

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
        server._cli(["XKCDService", "GetComicCount"])
        assert len(calls) == 1
        assert calls[0] == "/xkcd.v1.XKCDService/GetComicCount"

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
        server._cli(["XKCDService", "GetLatest"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
