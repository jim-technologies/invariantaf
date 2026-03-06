"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from github_mcp.gen.github.v1 import github_pb2 as pb
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
            "GitHubService.SearchRepos",
            "GitHubService.SearchUsers",
            "GitHubService.GetUser",
            "GitHubService.GetRepo",
            "GitHubService.ListRepoIssues",
            "GitHubService.GetIssue",
            "GitHubService.ListRepoPulls",
            "GitHubService.GetPull",
            "GitHubService.ListRepoLanguages",
            "GitHubService.GetRateLimit",
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
    def test_search_repos(self, server):
        result = server._cli(
            ["GitHubService", "SearchRepos", "-r", '{"query":"linux"}']
        )
        assert "items" in result
        assert len(result["items"]) >= 1

    def test_search_users(self, server):
        result = server._cli(
            ["GitHubService", "SearchUsers", "-r", '{"query":"torvalds"}']
        )
        assert "items" in result
        assert result["items"][0].get("login") == "torvalds"

    def test_get_user(self, server):
        result = server._cli(
            ["GitHubService", "GetUser", "-r", '{"username":"torvalds"}']
        )
        assert result.get("user", {}).get("login") == "torvalds"
        assert result.get("user", {}).get("name") == "Linus Torvalds"

    def test_get_repo(self, server):
        result = server._cli(
            ["GitHubService", "GetRepo", "-r", '{"owner":"torvalds","repo":"linux"}']
        )
        assert result.get("repo", {}).get("name") == "linux"

    def test_list_repo_issues(self, server):
        result = server._cli(
            ["GitHubService", "ListRepoIssues", "-r", '{"owner":"torvalds","repo":"linux"}']
        )
        assert "issues" in result
        assert len(result["issues"]) >= 1

    def test_get_issue(self, server):
        result = server._cli(
            ["GitHubService", "GetIssue", "-r", '{"owner":"torvalds","repo":"linux","issue_number":42}']
        )
        assert result.get("issue", {}).get("title") == "Bug in scheduler"

    def test_get_rate_limit(self, server):
        result = server._cli(["GitHubService", "GetRateLimit"])
        assert result.get("limit") == 60 or result.get("remaining") == 55

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["GitHubService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "GitHubService" in result
        assert "SearchRepos" in result

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

    def test_search_repos(self):
        result = self._post(
            "/github.v1.GitHubService/SearchRepos",
            {"query": "linux"},
        )
        assert "items" in result

    def test_get_rate_limit(self):
        result = self._post("/github.v1.GitHubService/GetRateLimit")
        assert "limit" in result or "remaining" in result

    def test_get_user(self):
        result = self._post(
            "/github.v1.GitHubService/GetUser",
            {"username": "torvalds"},
        )
        assert "user" in result

    def test_list_repo_languages(self):
        result = self._post(
            "/github.v1.GitHubService/ListRepoLanguages",
            {"owner": "torvalds", "repo": "linux"},
        )
        assert "languages" in result

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

from github_mcp.gen.github.v1 import github_pb2 as pb
from github_mcp.service import GitHubService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/search/repositories" in url:
        resp.json.return_value = {{
            "total_count": 1,
            "items": [{{
                "id": 1, "full_name": "torvalds/linux", "name": "linux",
                "owner": {{"login": "torvalds"}},
                "description": "Linux kernel source tree",
                "html_url": "https://github.com/torvalds/linux",
                "language": "C", "stargazers_count": 180000, "forks_count": 55000,
                "watchers_count": 180000, "open_issues_count": 300,
                "default_branch": "master", "license": {{"name": "GPL-2.0"}},
                "created_at": "2011-09-04T22:48:12Z", "updated_at": "2025-01-15T10:00:00Z",
                "fork": False, "archived": False, "topics": ["linux"]
            }}]
        }}
    elif "/search/users" in url:
        resp.json.return_value = {{
            "total_count": 1,
            "items": [{{"id": 1024025, "login": "torvalds",
                "avatar_url": "https://avatars.githubusercontent.com/u/1024025",
                "html_url": "https://github.com/torvalds", "type": "User"}}]
        }}
    elif "/users/" in url:
        resp.json.return_value = {{
            "id": 1024025, "login": "torvalds",
            "avatar_url": "", "html_url": "https://github.com/torvalds",
            "type": "User", "name": "Linus Torvalds", "bio": "",
            "company": "", "location": "", "email": None,
            "public_repos": 7, "public_gists": 0,
            "followers": 220000, "following": 0,
            "created_at": "2011-09-03T15:26:22Z"
        }}
    elif "/rate_limit" in url:
        resp.json.return_value = {{
            "resources": {{"core": {{
                "limit": 60, "remaining": 55, "reset": 1700003600, "used": 5
            }}}}
        }}
    elif "/languages" in url:
        resp.json.return_value = {{"C": 900000000, "Python": 1000000}}
    elif "/pulls/" in url:
        resp.json.return_value = {{
            "id": 200, "number": 99, "title": "Fix memory leak",
            "body": "", "state": "open",
            "html_url": "", "user": {{"login": "contributor3"}},
            "merged": False, "merged_at": None,
            "head": {{"ref": "fix-leak"}}, "base": {{"ref": "master"}},
            "additions": 150, "deletions": 30, "changed_files": 5,
            "commits": 3, "comments": 7,
            "labels": [], "assignees": [],
            "created_at": "", "updated_at": ""
        }}
    elif "/pulls" in url:
        resp.json.return_value = [{{
            "id": 200, "number": 99, "title": "Fix memory leak",
            "body": "", "state": "open",
            "html_url": "", "user": {{"login": "contributor3"}},
            "merged": False, "merged_at": None,
            "head": {{"ref": "fix-leak"}}, "base": {{"ref": "master"}},
            "labels": [], "assignees": [],
            "created_at": "", "updated_at": ""
        }}]
    elif "/issues/" in url:
        resp.json.return_value = {{
            "id": 100, "number": 42, "title": "Bug in scheduler",
            "body": "Race condition.", "state": "open",
            "html_url": "", "user": {{"login": "contributor1"}},
            "labels": [{{"name": "bug"}}], "assignees": [{{"login": "torvalds"}}],
            "comments": 5, "created_at": "", "updated_at": "",
            "closed_at": None, "pull_request": None
        }}
    elif "/issues" in url:
        resp.json.return_value = [{{
            "id": 100, "number": 42, "title": "Bug in scheduler",
            "body": "", "state": "open",
            "html_url": "", "user": {{"login": "contributor1"}},
            "labels": [], "assignees": [], "comments": 5,
            "created_at": "", "updated_at": "",
            "closed_at": None, "pull_request": None
        }}]
    elif "/repos/" in url:
        resp.json.return_value = {{
            "id": 1, "full_name": "torvalds/linux", "name": "linux",
            "owner": {{"login": "torvalds"}},
            "description": "Linux kernel source tree",
            "html_url": "https://github.com/torvalds/linux",
            "language": "C", "stargazers_count": 180000, "forks_count": 55000,
            "watchers_count": 180000, "open_issues_count": 300,
            "default_branch": "master", "license": {{"name": "GPL-2.0"}},
            "created_at": "", "updated_at": "",
            "fork": False, "archived": False, "topics": []
        }}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = GitHubService.__new__(GitHubService)
svc._http = http
svc._token = None

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-gh", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-gh"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "GitHubService.SearchRepos" in names
        assert "GitHubService.GetUser" in names
        assert "GitHubService.GetRateLimit" in names

    def test_tool_call_search_repos(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "GitHubService.SearchRepos",
                "arguments": {"query": "linux"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "items" in result
        assert result["items"][0].get("fullName") == "torvalds/linux" or result["items"][0].get("full_name") == "torvalds/linux"

    def test_tool_call_get_rate_limit(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "GitHubService.GetRateLimit",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("limit") == 60 or result.get("remaining") == 55

    def test_tool_call_get_user(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "GitHubService.GetUser",
                "arguments": {"username": "torvalds"},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("user", {}).get("login") == "torvalds"

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
        server._cli(["GitHubService", "GetRateLimit"])
        assert len(calls) == 1
        assert calls[0] == "/github.v1.GitHubService/GetRateLimit"

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
        server._cli(["GitHubService", "SearchRepos", "-r", '{"query":"test"}'])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
