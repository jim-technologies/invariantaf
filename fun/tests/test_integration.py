"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from fun_mcp.gen.fun.v1 import fun_pb2 as pb
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
            "FunService.GetDadJoke",
            "FunService.SearchDadJokes",
            "FunService.GetTrivia",
            "FunService.GetTriviaCategories",
            "FunService.GetRandomQuote",
            "FunService.SearchQuotes",
            "FunService.GetRandomDogImage",
            "FunService.GetDogImageByBreed",
            "FunService.ListDogBreeds",
            "FunService.GetRandomCatFact",
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
    def test_get_dad_joke(self, server):
        result = server._cli(["FunService", "GetDadJoke"])
        assert "joke" in result
        assert result["joke"]["id"] == "R7UfaahVfFd"

    def test_search_dad_jokes(self, server):
        result = server._cli(
            ["FunService", "SearchDadJokes", "-r", '{"query":"noodle"}']
        )
        assert "jokes" in result
        assert len(result["jokes"]) == 2

    def test_get_trivia(self, server):
        result = server._cli(
            ["FunService", "GetTrivia", "-r", '{"amount":2}']
        )
        assert "questions" in result
        assert len(result["questions"]) == 2

    def test_get_trivia_categories(self, server):
        result = server._cli(["FunService", "GetTriviaCategories"])
        assert "categories" in result
        assert len(result["categories"]) == 5

    def test_get_random_quote(self, server):
        result = server._cli(["FunService", "GetRandomQuote"])
        assert "quote" in result
        assert result["quote"]["author"] == "Steve Jobs"

    def test_search_quotes(self, server):
        result = server._cli(
            ["FunService", "SearchQuotes", "-r", '{"query":"opportunity"}']
        )
        assert "quotes" in result
        assert len(result["quotes"]) == 2

    def test_get_random_dog_image(self, server):
        result = server._cli(["FunService", "GetRandomDogImage"])
        img = result.get("imageUrl") or result.get("image_url")
        assert img is not None
        assert "labrador" in img

    def test_get_dog_image_by_breed(self, server):
        result = server._cli(
            ["FunService", "GetDogImageByBreed", "-r", '{"breed":"husky"}']
        )
        img = result.get("imageUrl") or result.get("image_url")
        assert img is not None
        assert "husky" in img

    def test_list_dog_breeds(self, server):
        result = server._cli(["FunService", "ListDogBreeds"])
        assert "breeds" in result
        assert len(result["breeds"]) == 4

    def test_get_random_cat_fact(self, server):
        result = server._cli(["FunService", "GetRandomCatFact"])
        fact = result.get("fact")
        assert fact is not None
        assert "vocalizations" in fact

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["FunService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "FunService" in result
        assert "GetDadJoke" in result

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

    def test_get_dad_joke(self):
        result = self._post("/fun.v1.FunService/GetDadJoke")
        assert "joke" in result

    def test_get_trivia(self):
        result = self._post(
            "/fun.v1.FunService/GetTrivia",
            {"amount": 2},
        )
        assert "questions" in result

    def test_get_trivia_categories(self):
        result = self._post("/fun.v1.FunService/GetTriviaCategories")
        assert "categories" in result

    def test_get_random_dog_image(self):
        result = self._post("/fun.v1.FunService/GetRandomDogImage")
        img = result.get("imageUrl") or result.get("image_url")
        assert img is not None

    def test_get_random_cat_fact(self):
        result = self._post("/fun.v1.FunService/GetRandomCatFact")
        fact = result.get("fact")
        assert fact is not None

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

from fun_mcp.gen.fun.v1 import fun_pb2 as pb
from fun_mcp.service import FunService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None, headers=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if url == "https://icanhazdadjoke.com" and (params is None or "term" not in (params or {{}})):
        resp.json.return_value = {{"id": "R7UfaahVfFd", "joke": "My dog used to chase people on a bike.", "status": 200}}
    elif "icanhazdadjoke.com/search" in url:
        resp.json.return_value = {{"results": [{{"id": "abc123", "joke": "What do you call a fake noodle?"}}], "total_jokes": 1}}
    elif "opentdb.com/api.php" in url:
        resp.json.return_value = {{"results": [{{"type": "multiple", "difficulty": "medium",
            "category": "General Knowledge", "question": "Test?",
            "correct_answer": "Yes", "incorrect_answers": ["No", "Maybe", "Perhaps"]}}]}}
    elif "opentdb.com/api_category.php" in url:
        resp.json.return_value = {{"trivia_categories": [{{"id": 9, "name": "General Knowledge"}}]}}
    elif "quotable.io/quotes/random" in url:
        resp.json.return_value = [{{"_id": "q1", "content": "Be the change.", "author": "Gandhi", "tags": ["wisdom"], "length": 14}}]
    elif "quotable.io/search/quotes" in url:
        resp.json.return_value = {{"results": [{{"_id": "q2", "content": "Test quote.", "author": "Tester", "tags": [], "length": 11}}], "totalCount": 1}}
    elif "dog.ceo/api/breeds/image/random" in url:
        resp.json.return_value = {{"message": "https://images.dog.ceo/breeds/labrador/img.jpg", "status": "success"}}
    elif "dog.ceo/api/breed/" in url:
        resp.json.return_value = {{"message": "https://images.dog.ceo/breeds/husky/img.jpg", "status": "success"}}
    elif "dog.ceo/api/breeds/list/all" in url:
        resp.json.return_value = {{"message": {{"labrador": [], "poodle": ["standard"]}}, "status": "success"}}
    elif "catfact.ninja/fact" in url:
        resp.json.return_value = {{"fact": "Cats sleep 70% of their lives.", "length": 31}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = FunService.__new__(FunService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-fun", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-fun"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "FunService.GetDadJoke" in names
        assert "FunService.GetTrivia" in names
        assert "FunService.GetRandomCatFact" in names

    def test_tool_call_get_dad_joke(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FunService.GetDadJoke",
                "arguments": {},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "joke" in result
        assert result["joke"]["id"] == "R7UfaahVfFd"

    def test_tool_call_get_trivia(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FunService.GetTrivia",
                "arguments": {"amount": 1},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "questions" in result
        assert len(result["questions"]) == 1

    def test_tool_call_get_random_cat_fact(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "FunService.GetRandomCatFact",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("fact") is not None

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
        server._cli(["FunService", "GetDadJoke"])
        assert len(calls) == 1
        assert calls[0] == "/fun.v1.FunService/GetDadJoke"

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
        server._cli(["FunService", "GetRandomCatFact"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
