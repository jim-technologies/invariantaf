"""Shared fixtures for OpenDota MCP tests."""

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

FAKE_HEALTH = {
    "postgresUsage": {"metric": 1000, "limit": 10000, "timestamp": 1772703543},
    "redisUsage": {"metric": 500, "limit": 5000, "timestamp": 1772703543},
}

FAKE_TOP_PLAYERS = [
    {"account_id": 77777, "name": "top mid", "leaderboard_rank": 1},
    {"account_id": 88888, "name": "top carry", "leaderboard_rank": 2},
]

FAKE_MATCH = {
    "match_id": 1001,
    "duration": 2345,
    "radiant_win": True,
    "players": [{"account_id": 12345, "hero_id": 1, "kills": 10}],
}

FAKE_TEAMS = [
    {
        "team_id": 39,
        "rating": 1912.5,
        "wins": 240,
        "losses": 150,
        "last_match_time": 1772600000,
        "name": "Team Liquid",
        "tag": "TL",
    }
]


class _BackendHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path

        if path == "/health":
            self._write_data(FAKE_HEALTH)
            return
        if path == "/matches/1001":
            self._write_data(FAKE_MATCH)
            return
        if path == "/topPlayers":
            self._write_data(FAKE_TOP_PLAYERS)
            return
        if path == "/teams":
            self._write_data(FAKE_TEAMS)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/request/1001":
            self._write_data({"job": {"jobId": 9876}})
            return
        self.send_response(404)
        self.end_headers()

    def _write_data(self, payload: object):
        self._write_json(200, payload)

    def _write_json(self, status: int, payload: object):
        raw = json.dumps(payload).encode()
        self.send_response(status)
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
    from gen.opendota.v1 import opendota_pb2 as _opendota_pb2  # noqa: F401

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-opendota", version="0.0.1")
    srv.connect_http(backend_url, service_name="opendota.v1.OpenDotaService")
    yield srv
    srv.stop()
