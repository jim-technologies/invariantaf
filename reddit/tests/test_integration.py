"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from reddit_mcp.gen.reddit.v1 import reddit_pb2 as pb
from tests.conftest import DESCRIPTOR_PATH

# Template for the MCP subprocess script. Uses __DESCRIPTOR_PATH__ as placeholder.
_MCP_SCRIPT_TEMPLATE = r'''
import sys
from pathlib import Path
from unittest.mock import MagicMock

descriptor_path = "__DESCRIPTOR_PATH__"
sys.path.insert(0, str(Path(descriptor_path).parent / "src"))

from reddit_mcp.gen.reddit.v1 import reddit_pb2 as pb
from reddit_mcp.service import RedditService
from invariant import Server

FAKE_POST = {
    "id": "abc123", "title": "Test Post Title",
    "selftext": "This is the body of the test post.", "author": "testuser",
    "subreddit": "python", "score": 1500, "num_comments": 200,
    "url": "https://www.reddit.com/r/python/comments/abc123/test_post_title/",
    "permalink": "/r/python/comments/abc123/test_post_title/",
    "created_utc": 1700000000.0, "is_self": True, "thumbnail": "self",
}

FAKE_LISTING = {"data": {"children": [{"kind": "t3", "data": FAKE_POST}]}}

FAKE_POST_DETAIL = [
    {"data": {"children": [{"kind": "t3", "data": FAKE_POST}]}},
    {"data": {"children": [
        {"kind": "t1", "data": {
            "id": "cmt001", "author": "commenter1", "body": "Great post!",
            "score": 100, "created_utc": 1700001000.0,
            "permalink": "/r/python/comments/abc123/test_post_title/cmt001/",
            "replies": "",
        }},
    ]}},
]

FAKE_SUBREDDIT = {"data": {
    "name": "t5_2qh0y", "display_name": "python", "title": "Python",
    "public_description": "Python programming language.", "subscribers": 1500000,
    "accounts_active": 5000, "created_utc": 1230000000.0,
    "url": "/r/python/", "over18": False,
}}

FAKE_USER = {"data": {
    "name": "testuser", "link_karma": 10000, "comment_karma": 50000,
    "created_utc": 1400000000.0,
    "subreddit": {"public_description": "I like Python."},
    "is_gold": True, "verified": True,
}}

FAKE_POPULAR = {"data": {"children": [
    {"kind": "t5", "data": {
        "name": "t5_2cneq", "display_name": "AskReddit", "title": "Ask Reddit...",
        "public_description": "Ask questions.", "subscribers": 45000000,
        "accounts_active": 50000, "created_utc": 1201000000.0,
        "url": "/r/AskReddit/", "over18": False,
    }},
]}}

FAKE_FRONT = {"data": {"children": [{"kind": "t3", "data": {
    "id": "fp001", "title": "Front page post", "selftext": "Front page.",
    "author": "frontpageuser", "subreddit": "worldnews", "score": 50000,
    "num_comments": 3000,
    "url": "https://www.reddit.com/r/worldnews/comments/fp001/front_page_post/",
    "permalink": "/r/worldnews/comments/fp001/front_page_post/",
    "created_utc": 1700060000.0, "is_self": True, "thumbnail": "self",
}}]}}

http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/hot.json" in url:
        resp.json.return_value = FAKE_LISTING
    elif "/top.json" in url:
        resp.json.return_value = FAKE_LISTING
    elif "/new.json" in url:
        resp.json.return_value = FAKE_LISTING
    elif "/comments/" in url:
        resp.json.return_value = FAKE_POST_DETAIL
    elif "/search.json" in url:
        resp.json.return_value = FAKE_LISTING
    elif "/about.json" in url and "/user/" in url:
        resp.json.return_value = FAKE_USER
    elif "/about.json" in url:
        resp.json.return_value = FAKE_SUBREDDIT
    elif "/submitted.json" in url:
        resp.json.return_value = FAKE_LISTING
    elif "/subreddits/popular.json" in url:
        resp.json.return_value = FAKE_POPULAR
    elif url.endswith("/.json"):
        resp.json.return_value = FAKE_FRONT
    else:
        resp.json.return_value = {}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = RedditService.__new__(RedditService)
svc._http = http

server = Server.from_descriptor(descriptor_path, name="test-reddit", version="0.0.1")
server.register(svc)
server.serve(mcp=True)
'''


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 10

    def test_tool_names(self, server):
        expected = {
            "RedditService.GetHot",
            "RedditService.GetTop",
            "RedditService.GetNew",
            "RedditService.GetPost",
            "RedditService.SearchPosts",
            "RedditService.GetSubreddit",
            "RedditService.GetUser",
            "RedditService.GetUserPosts",
            "RedditService.GetPopularSubreddits",
            "RedditService.GetFrontPage",
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
    def test_get_hot(self, server):
        result = server._cli(
            ["RedditService", "GetHot", "-r", '{"subreddit":"python"}']
        )
        assert "posts" in result
        assert len(result["posts"]) >= 1

    def test_get_top(self, server):
        result = server._cli(
            ["RedditService", "GetTop", "-r", '{"subreddit":"python","time_filter":"week"}']
        )
        assert "posts" in result

    def test_get_new(self, server):
        result = server._cli(
            ["RedditService", "GetNew", "-r", '{"subreddit":"python"}']
        )
        assert "posts" in result

    def test_get_post(self, server):
        result = server._cli(
            ["RedditService", "GetPost", "-r", '{"subreddit":"python","post_id":"abc123"}']
        )
        assert "post" in result
        assert result["post"]["id"] == "abc123"

    def test_search_posts(self, server):
        result = server._cli(
            ["RedditService", "SearchPosts", "-r", '{"query":"python tutorial"}']
        )
        assert "posts" in result
        assert len(result["posts"]) >= 1

    def test_get_subreddit(self, server):
        result = server._cli(
            ["RedditService", "GetSubreddit", "-r", '{"subreddit":"python"}']
        )
        assert "subreddit" in result
        sr = result["subreddit"]
        assert sr.get("displayName") == "python" or sr.get("display_name") == "python"

    def test_get_user(self, server):
        result = server._cli(
            ["RedditService", "GetUser", "-r", '{"username":"testuser"}']
        )
        assert "user" in result
        assert result["user"]["name"] == "testuser"

    def test_get_user_posts(self, server):
        result = server._cli(
            ["RedditService", "GetUserPosts", "-r", '{"username":"testuser"}']
        )
        assert "posts" in result

    def test_get_popular_subreddits(self, server):
        result = server._cli(["RedditService", "GetPopularSubreddits"])
        assert "subreddits" in result
        assert len(result["subreddits"]) == 2

    def test_get_front_page(self, server):
        result = server._cli(["RedditService", "GetFrontPage"])
        assert "posts" in result
        assert len(result["posts"]) >= 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["RedditService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "RedditService" in result
        assert "GetHot" in result

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

    def test_get_hot(self):
        result = self._post(
            "/reddit.v1.RedditService/GetHot",
            {"subreddit": "python"},
        )
        assert "posts" in result

    def test_get_front_page(self):
        result = self._post("/reddit.v1.RedditService/GetFrontPage")
        assert "posts" in result

    def test_get_subreddit(self):
        result = self._post(
            "/reddit.v1.RedditService/GetSubreddit",
            {"subreddit": "python"},
        )
        assert "subreddit" in result

    def test_get_user(self):
        result = self._post(
            "/reddit.v1.RedditService/GetUser",
            {"username": "testuser"},
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

        # Build the script as a plain string template to avoid f-string brace escaping.
        script = _MCP_SCRIPT_TEMPLATE.replace("__DESCRIPTOR_PATH__", DESCRIPTOR_PATH)

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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-reddit"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "RedditService.GetHot" in names
        assert "RedditService.GetTop" in names
        assert "RedditService.GetFrontPage" in names

    def test_tool_call_get_hot(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "RedditService.GetHot",
                "arguments": {"subreddit": "python"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "posts" in result
        assert len(result["posts"]) >= 1

    def test_tool_call_get_front_page(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "RedditService.GetFrontPage",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "posts" in result

    def test_tool_call_get_subreddit(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "RedditService.GetSubreddit",
                "arguments": {"subreddit": "python"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "subreddit" in result

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
        server._cli(["RedditService", "GetFrontPage"])
        assert len(calls) == 1
        assert calls[0] == "/reddit.v1.RedditService/GetFrontPage"

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
        server._cli(["RedditService", "GetFrontPage"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
