"""Integration tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH

_ALL_TOOL_NAMES = {
    "JsonPlaceholderService.GetPost",
    "JsonPlaceholderService.GetUser",
    "JsonPlaceholderService.GetTodo",
    "JsonPlaceholderService.GetComment",
}


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 4

    def test_tool_names(self, server):
        assert set(server.tools.keys()) == _ALL_TOOL_NAMES


class TestCLIProjection:
    def test_get_post(self, server):
        result = server._cli(["JsonPlaceholderService", "GetPost", "-r", '{"id":1}'])
        assert result["id"] == 1
        assert result["title"] == "test post"

    def test_get_user(self, server):
        result = server._cli(["JsonPlaceholderService", "GetUser", "-r", '{"id":2}'])
        assert result["id"] == 2
        assert result["username"] == "Bret"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["JsonPlaceholderService", "DoesNotExist"])


class TestHTTPProjection:
    @pytest.fixture(autouse=True)
    def start_http(self, server):
        self.port = server._start_http(0)
        yield
        server._stop_http()

    def _post(self, path: str, body: dict | None = None):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read())

    def test_get_todo(self):
        result = self._post("/jsonplaceholder.v1.JsonPlaceholderService/GetTodo", {"id": 3})
        assert result["id"] == 3
        # Proto3 JSON may omit default bool=false fields.
        assert result.get("completed", False) is False

    def test_get_comment(self):
        result = self._post("/jsonplaceholder.v1.JsonPlaceholderService/GetComment", {"id": 4})
        assert result["id"] == 4
        # Depending on projection settings, field names can be camelCase or snake_case.
        assert result.get("postId", result.get("post_id")) == 1

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
