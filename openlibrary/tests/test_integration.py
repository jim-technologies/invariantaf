"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as pb
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
            "OpenLibraryService.SearchBooks",
            "OpenLibraryService.SearchByAuthor",
            "OpenLibraryService.SearchBySubject",
            "OpenLibraryService.GetBook",
            "OpenLibraryService.GetEdition",
            "OpenLibraryService.GetAuthor",
            "OpenLibraryService.GetAuthorWorks",
            "OpenLibraryService.GetBookByISBN",
            "OpenLibraryService.GetRecentChanges",
            "OpenLibraryService.GetTrendingBooks",
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
    def test_search_books(self, server):
        result = server._cli(
            ["OpenLibraryService", "SearchBooks", "-r", '{"query":"lord of the rings"}']
        )
        assert "books" in result
        assert len(result["books"]) >= 1

    def test_search_by_author(self, server):
        result = server._cli(
            ["OpenLibraryService", "SearchByAuthor", "-r", '{"name":"George Orwell"}']
        )
        assert "books" in result
        assert result["books"][0]["title"] == "1984"

    def test_search_by_subject(self, server):
        result = server._cli(
            ["OpenLibraryService", "SearchBySubject", "-r", '{"subject":"fantasy"}']
        )
        assert "works" in result
        assert result["name"] == "Fantasy"

    def test_get_book(self, server):
        result = server._cli(
            ["OpenLibraryService", "GetBook", "-r", '{"work_id":"OL45883W"}']
        )
        assert result["title"] == "The Lord of the Rings"

    def test_get_edition(self, server):
        result = server._cli(
            ["OpenLibraryService", "GetEdition", "-r", '{"edition_id":"OL7353617M"}']
        )
        assert result["title"] == "The Lord of the Rings"

    def test_get_author(self, server):
        result = server._cli(
            ["OpenLibraryService", "GetAuthor", "-r", '{"author_id":"OL23919A"}']
        )
        assert result["name"] == "J.R.R. Tolkien"

    def test_get_author_works(self, server):
        result = server._cli(
            ["OpenLibraryService", "GetAuthorWorks", "-r", '{"author_id":"OL23919A"}']
        )
        assert "works" in result
        assert len(result["works"]) == 2

    def test_get_book_by_isbn(self, server):
        result = server._cli(
            ["OpenLibraryService", "GetBookByISBN", "-r", '{"isbn":"9780261103573"}']
        )
        assert result["title"] == "The Lord of the Rings"

    def test_get_recent_changes(self, server):
        result = server._cli(["OpenLibraryService", "GetRecentChanges"])
        assert "changes" in result
        assert len(result["changes"]) == 2

    def test_get_trending_books(self, server):
        result = server._cli(["OpenLibraryService", "GetTrendingBooks"])
        assert "books" in result
        assert len(result["books"]) == 2

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OpenLibraryService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "OpenLibraryService" in result
        assert "SearchBooks" in result

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

    def test_search_books(self):
        result = self._post(
            "/openlibrary.v1.OpenLibraryService/SearchBooks",
            {"query": "lord of the rings"},
        )
        assert "books" in result

    def test_get_trending_books(self):
        result = self._post("/openlibrary.v1.OpenLibraryService/GetTrendingBooks")
        assert "books" in result

    def test_get_recent_changes(self):
        result = self._post("/openlibrary.v1.OpenLibraryService/GetRecentChanges")
        assert "changes" in result

    def test_get_author(self):
        result = self._post(
            "/openlibrary.v1.OpenLibraryService/GetAuthor",
            {"author_id": "OL23919A"},
        )
        assert result["name"] == "J.R.R. Tolkien"

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

from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as pb
from openlibrary_mcp.service import OpenLibraryService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/search.json" in url and params and "author" in params:
        resp.json.return_value = {{"numFound": 1, "docs": [{{"title": "1984",
            "author_name": ["George Orwell"], "first_publish_year": 1949,
            "isbn": ["9780451524935"], "cover_i": 8575964, "number_of_pages_median": 328,
            "subject": ["Dystopia"], "key": "/works/OL1168083W"}}]}}
    elif "/search.json" in url:
        resp.json.return_value = {{"numFound": 2, "docs": [
            {{"title": "The Lord of the Rings", "author_name": ["J.R.R. Tolkien"],
              "first_publish_year": 1954, "isbn": ["9780261103573"], "cover_i": 8474036,
              "number_of_pages_median": 1216, "subject": ["Fantasy"], "key": "/works/OL45883W"}},
            {{"title": "The Hobbit", "author_name": ["J.R.R. Tolkien"],
              "first_publish_year": 1937, "isbn": ["9780547928227"], "cover_i": 8406786,
              "number_of_pages_median": 310, "subject": ["Fantasy"], "key": "/works/OL262758W"}}
        ]}}
    elif "/subjects/" in url:
        resp.json.return_value = {{"name": "Fantasy", "work_count": 50000, "works": [
            {{"title": "A Game of Thrones", "authors": [{{"name": "George R.R. Martin"}}],
              "key": "/works/OL17346379W", "cover_id": 8451036, "edition_count": 85,
              "first_publish_year": 1996}}
        ]}}
    elif "/works/" in url:
        resp.json.return_value = {{"title": "The Lord of the Rings",
            "description": {{"value": "An epic high-fantasy novel."}},
            "subjects": ["Fantasy", "Fiction"], "covers": [8474036],
            "created": {{"value": "2008-04-01T03:28:50.625462"}}, "key": "/works/OL45883W"}}
    elif "/isbn/" in url:
        resp.json.return_value = {{"title": "The Lord of the Rings",
            "publishers": ["Houghton Mifflin"], "publish_date": "2004",
            "isbn_13": ["9780618640157"], "isbn_10": ["0618640150"],
            "number_of_pages": 1216, "covers": [8474036], "key": "/books/OL7353617M"}}
    elif "/authors/" in url and "/works.json" in url:
        resp.json.return_value = {{"size": 50, "entries": [
            {{"title": "The Lord of the Rings", "key": "/works/OL45883W",
              "covers": [8474036], "first_publish_year": 1954}}
        ]}}
    elif "/authors/" in url:
        resp.json.return_value = {{"name": "J.R.R. Tolkien",
            "bio": {{"value": "English writer."}}, "birth_date": "3 January 1892",
            "death_date": "2 September 1973", "photos": [6304727],
            "links": [{{"title": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Tolkien"}}],
            "key": "/authors/OL23919A"}}
    elif "/books/" in url:
        resp.json.return_value = {{"title": "The Lord of the Rings",
            "publishers": ["Houghton Mifflin"], "publish_date": "2004",
            "isbn_13": ["9780618640157"], "isbn_10": ["0618640150"],
            "number_of_pages": 1216, "covers": [8474036], "key": "/books/OL7353617M"}}
    elif "/recentchanges.json" in url:
        resp.json.return_value = [
            {{"kind": "edit-book", "author": {{"key": "/people/ImportBot"}},
              "timestamp": "2025-01-15T10:00:00Z", "comment": "Updated", "id": "12345"}}
        ]
    elif "/trending/daily.json" in url:
        resp.json.return_value = {{"works": [
            {{"title": "Dune", "author_name": ["Frank Herbert"],
              "key": "/works/OL893415W", "cover_i": 8231856,
              "first_publish_year": 1965, "availability": {{"status": "borrow_available"}}}}
        ]}}
    else:
        resp.json.return_value = {{}}
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = OpenLibraryService.__new__(OpenLibraryService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-ol", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-ol"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "OpenLibraryService.SearchBooks" in names
        assert "OpenLibraryService.GetBook" in names
        assert "OpenLibraryService.GetTrendingBooks" in names

    def test_tool_call_search_books(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OpenLibraryService.SearchBooks",
                "arguments": {"query": "lord of the rings"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert "books" in result
        assert result["books"][0]["title"] == "The Lord of the Rings"

    def test_tool_call_get_trending_books(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OpenLibraryService.GetTrendingBooks",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "books" in result
        assert result["books"][0]["title"] == "Dune"

    def test_tool_call_get_recent_changes(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "OpenLibraryService.GetRecentChanges",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "changes" in result
        assert len(result["changes"]) >= 1

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
        server._cli(["OpenLibraryService", "GetRecentChanges"])
        assert len(calls) == 1
        assert calls[0] == "/openlibrary.v1.OpenLibraryService/GetRecentChanges"

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
        server._cli(["OpenLibraryService", "GetTrendingBooks"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
