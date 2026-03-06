"""Shared fixtures for JSONPlaceholder MCP tests."""

from __future__ import annotations

import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")


class _BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path

        if path.startswith("/posts/"):
            post_id = int(path.rsplit("/", 1)[-1])
            self._write_json(
                {
                    "userId": 1,
                    "id": post_id,
                    "title": "test post",
                    "body": "hello world",
                }
            )
            return

        if path.startswith("/users/"):
            user_id = int(path.rsplit("/", 1)[-1])
            self._write_json(
                {
                    "id": user_id,
                    "name": "Leanne Graham",
                    "username": "Bret",
                    "email": "leanne@example.com",
                    "phone": "1-770-736-8031 x56442",
                    "website": "hildegard.org",
                }
            )
            return

        if path.startswith("/todos/"):
            todo_id = int(path.rsplit("/", 1)[-1])
            self._write_json(
                {
                    "userId": 1,
                    "id": todo_id,
                    "title": "delectus aut autem",
                    "completed": False,
                }
            )
            return

        if path.startswith("/comments/"):
            comment_id = int(path.rsplit("/", 1)[-1])
            self._write_json(
                {
                    "postId": 1,
                    "id": comment_id,
                    "name": "id labore ex et quam laborum",
                    "email": "eliseo@gardner.biz",
                    "body": "laudantium enim quasi",
                }
            )
            return

        self.send_response(404)
        self.end_headers()

    def _write_json(self, payload: object):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        pass


@pytest.fixture
def backend_url():
    httpd = ThreadingHTTPServer(("localhost", 0), _BackendHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{port}"
    finally:
        httpd.shutdown()


@pytest.fixture
def server(backend_url: str):
    from invariant import Server
    from jsonplaceholder_mcp.gen.jsonplaceholder.v1 import jsonplaceholder_pb2 as _jsonplaceholder_pb2  # noqa: F401

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-jsonplaceholder", version="0.0.1")
    srv.connect_http(backend_url, service_name="jsonplaceholder.v1.JsonPlaceholderService")
    yield srv
    srv.stop()
