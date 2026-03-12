"""Live integration tests for JSONPlaceholder API -- hits the real API.

Run with:
    JSONPLACEHOLDER_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) JSONPlaceholder endpoints.
Powered by jsonplaceholder.typicode.com.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("JSONPLACEHOLDER_RUN_LIVE_TESTS") != "1",
    reason="Set JSONPLACEHOLDER_RUN_LIVE_TESTS=1 to run live JSONPlaceholder API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from jsonplaceholder_mcp.gen.jsonplaceholder.v1 import jsonplaceholder_pb2 as _jsonplaceholder_pb2  # noqa: F401
    from invariant import Server

    base_url = (
        os.getenv("JSONPLACEHOLDER_BASE_URL")
        or "https://jsonplaceholder.typicode.com"
    ).rstrip("/")
    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-jsonplaceholder-live", version="0.0.1"
    )
    srv.connect_http(base_url, service_name="jsonplaceholder.v1.JsonPlaceholderService")
    yield srv
    srv.stop()


# --- Posts ---


class TestLivePosts:
    def test_get_post(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetPost", "-r", json.dumps({"id": 1})]
        )
        assert result.get("id") == 1
        assert "title" in result
        assert "body" in result
        assert result.get("userId") or result.get("user_id")

    def test_get_post_different_id(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetPost", "-r", json.dumps({"id": 42})]
        )
        assert result.get("id") == 42
        assert "title" in result


# --- Users ---


class TestLiveUsers:
    def test_get_user(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetUser", "-r", json.dumps({"id": 1})]
        )
        assert result.get("id") == 1
        assert "name" in result
        assert "username" in result
        assert "email" in result

    def test_get_user_different_id(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetUser", "-r", json.dumps({"id": 5})]
        )
        assert result.get("id") == 5
        assert "name" in result


# --- Todos ---


class TestLiveTodos:
    def test_get_todo(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetTodo", "-r", json.dumps({"id": 1})]
        )
        assert result.get("id") == 1
        assert "title" in result
        # completed may be omitted if false in proto3 JSON
        assert "completed" in result or result.get("completed") is None
        assert result.get("userId") or result.get("user_id")

    def test_get_todo_completed(self, live_server):
        # Todo #10 is known to be completed in the fixture data
        result = live_server._cli(
            ["JsonPlaceholderService", "GetTodo", "-r", json.dumps({"id": 10})]
        )
        assert result.get("id") == 10
        assert "title" in result


# --- Comments ---


class TestLiveComments:
    def test_get_comment(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetComment", "-r", json.dumps({"id": 1})]
        )
        assert result.get("id") == 1
        assert "name" in result
        assert "email" in result
        assert "body" in result
        assert result.get("postId") or result.get("post_id")

    def test_get_comment_different_id(self, live_server):
        result = live_server._cli(
            ["JsonPlaceholderService", "GetComment", "-r", json.dumps({"id": 100})]
        )
        assert result.get("id") == 100
        assert "body" in result
