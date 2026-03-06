"""Integration tests — verify invariant protocol wiring (descriptor, registration, projections)."""

import json
import urllib.request

import pytest

from lichess_mcp.gen.lichess.v1 import lichess_pb2 as pb
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
            "LichessService.GetUser",
            "LichessService.GetUserRatingHistory",
            "LichessService.GetUserGames",
            "LichessService.GetGame",
            "LichessService.GetDailyPuzzle",
            "LichessService.GetPuzzle",
            "LichessService.GetLeaderboard",
            "LichessService.GetCloudEval",
            "LichessService.GetOnline",
            "LichessService.GetTeam",
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
    def test_get_user(self, server):
        result = server._cli(
            ["LichessService", "GetUser", "-r", '{"username":"drnykterstein"}']
        )
        assert result.get("username") == "DrNykterstein" or result.get("id") == "drnykterstein"

    def test_get_user_rating_history(self, server):
        result = server._cli(
            ["LichessService", "GetUserRatingHistory", "-r", '{"username":"drnykterstein"}']
        )
        assert "history" in result
        assert len(result["history"]) == 2

    def test_get_user_games(self, server):
        result = server._cli(
            ["LichessService", "GetUserGames", "-r", '{"username":"drnykterstein"}']
        )
        assert "games" in result
        assert len(result["games"]) == 2

    def test_get_game(self, server):
        result = server._cli(
            ["LichessService", "GetGame", "-r", '{"game_id":"abcd1234"}']
        )
        assert "game" in result
        assert result["game"].get("id") == "abcd1234"

    def test_get_daily_puzzle(self, server):
        result = server._cli(["LichessService", "GetDailyPuzzle"])
        assert "puzzle" in result

    def test_get_leaderboard(self, server):
        result = server._cli(
            ["LichessService", "GetLeaderboard", "-r", '{"nb":10,"perf_type":"bullet"}']
        )
        assert "users" in result
        assert len(result["users"]) == 3

    def test_get_cloud_eval(self, server):
        result = server._cli(
            ["LichessService", "GetCloudEval", "-r", '{"fen":"rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"}']
        )
        assert "pvs" in result
        assert len(result["pvs"]) == 2

    def test_get_online(self, server):
        result = server._cli(["LichessService", "GetOnline"])
        assert result.get("count") == 83422

    def test_get_team(self, server):
        result = server._cli(
            ["LichessService", "GetTeam", "-r", '{"team_id":"lichess-swiss"}']
        )
        assert result.get("name") == "Lichess Swiss"

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["LichessService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "LichessService" in result
        assert "GetUser" in result

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

    def test_get_user(self):
        result = self._post(
            "/lichess.v1.LichessService/GetUser",
            {"username": "drnykterstein"},
        )
        assert result.get("username") == "DrNykterstein" or result.get("id") == "drnykterstein"

    def test_get_daily_puzzle(self):
        result = self._post("/lichess.v1.LichessService/GetDailyPuzzle")
        assert "puzzle" in result

    def test_get_online(self):
        result = self._post("/lichess.v1.LichessService/GetOnline")
        assert result.get("count") == 83422

    def test_get_leaderboard(self):
        result = self._post(
            "/lichess.v1.LichessService/GetLeaderboard",
            {"nb": 10, "perf_type": "bullet"},
        )
        assert "users" in result

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
import json
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path({DESCRIPTOR_PATH!r}).parent.parent / "src"))

from lichess_mcp.gen.lichess.v1 import lichess_pb2 as pb
from lichess_mcp.service import LichessService
from invariant import Server

# Build mocked service.
http = MagicMock()
def mock_get(url, params=None, headers=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/api/user/drnykterstein/rating-history" in url:
        resp.json.return_value = [
            {{"name": "Bullet", "points": [[2023, 1, 15, 3100]]}},
        ]
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/user/drnykterstein" in url:
        resp.json.return_value = {{
            "id": "drnykterstein", "username": "DrNykterstein", "title": "GM",
            "online": True,
            "profile": {{"bio": "Chess is life.", "country": "NO"}},
            "perfs": {{"bullet": {{"games": 5000, "rating": 3200, "rd": 45, "prog": 10, "prov": False}}}},
            "count": {{"all": 15500}},
            "playTime": {{"total": 5000000}},
            "createdAt": 1500000000000,
            "url": "https://lichess.org/@/DrNykterstein"
        }}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/games/user/" in url:
        resp.text = json.dumps({{
            "id": "abcd1234", "rated": True, "variant": "standard", "speed": "blitz",
            "perf": "blitz", "createdAt": 1700000000000, "lastMoveAt": 1700000300000,
            "status": "mate", "players": {{
                "white": {{"user": {{"name": "DrNykterstein"}}, "rating": 3100, "ratingDiff": 5}},
                "black": {{"user": {{"name": "Firouzja2003"}}, "rating": 3000, "ratingDiff": -5}}
            }}, "moves": "e4 e5 Nf3", "opening": {{"eco": "C65", "name": "Ruy Lopez"}},
            "clock": {{"initial": 180, "increment": 0}}, "winner": "white"
        }})
        resp.json.return_value = json.loads(resp.text)
    elif "/game/export/" in url:
        resp.json.return_value = {{
            "id": "abcd1234", "rated": True, "variant": "standard", "speed": "blitz",
            "perf": "blitz", "createdAt": 1700000000000, "lastMoveAt": 1700000300000,
            "status": "mate", "players": {{
                "white": {{"user": {{"name": "DrNykterstein"}}, "rating": 3100, "ratingDiff": 5}},
                "black": {{"user": {{"name": "Firouzja2003"}}, "rating": 3000, "ratingDiff": -5}}
            }}, "moves": "e4 e5 Nf3", "opening": {{"eco": "C65", "name": "Ruy Lopez"}},
            "clock": {{"initial": 180, "increment": 0}}, "winner": "white"
        }}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/puzzle/daily" in url:
        resp.json.return_value = {{
            "game": {{"id": "Xg7a1B2c", "pgn": "e4 e5"}},
            "puzzle": {{"id": "K69di", "rating": 1850, "plays": 125000, "initialPly": 42,
                "solution": ["e2e4", "d7d5", "e4d5"], "themes": ["fork", "middlegame"]}}
        }}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/puzzle/" in url:
        resp.json.return_value = {{
            "game": {{"id": "Yh8b2C3d", "pgn": "d4 d5"}},
            "puzzle": {{"id": "A1b2C", "rating": 2200, "plays": 50000, "initialPly": 30,
                "solution": ["f3g5"], "themes": ["sacrifice"]}}
        }}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/player/top/" in url:
        resp.json.return_value = {{"users": [
            {{"username": "DrNykterstein", "title": "GM", "online": True,
              "perfs": {{"bullet": {{"rating": 3200}}}}}}
        ]}}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/cloud-eval" in url:
        resp.json.return_value = {{
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "knodes": 25000, "depth": 40,
            "pvs": [{{"moves": "e7e5 g1f3", "cp": 20, "mate": 0}}]
        }}
        resp.text = json.dumps(resp.json.return_value)
    elif "/api/user/count" in url:
        resp.text = "83422"
        resp.json.side_effect = ValueError("not json")
    elif "/api/team/" in url:
        resp.json.return_value = {{
            "id": "lichess-swiss", "name": "Lichess Swiss",
            "description": "The official team.", "nbMembers": 50000,
            "leaders": [{{"name": "thibault", "id": "thibault"}}], "open": True
        }}
        resp.text = json.dumps(resp.json.return_value)
    else:
        resp.json.return_value = {{}}
        resp.text = "{{}}"
    return resp

http.get = MagicMock(side_effect=mock_get)

svc = LichessService.__new__(LichessService)
svc._http = http

server = Server.from_descriptor({DESCRIPTOR_PATH!r}, name="test-lichess", version="0.0.1")
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
        assert responses[0]["result"]["serverInfo"]["name"] == "test-lichess"

    def test_tools_list(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/list", {}),
        ])
        tools = responses[1]["result"]["tools"]
        assert len(tools) >= 10
        names = {t["name"] for t in tools}
        assert "LichessService.GetUser" in names
        assert "LichessService.GetDailyPuzzle" in names
        assert "LichessService.GetOnline" in names

    def test_tool_call_get_user(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LichessService.GetUser",
                "arguments": {"username": "drnykterstein"},
            }),
        ])
        content = responses[1]["result"]["content"]
        result = json.loads(content[0]["text"])
        assert result.get("username") == "DrNykterstein" or result.get("id") == "drnykterstein"

    def test_tool_call_get_daily_puzzle(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LichessService.GetDailyPuzzle",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert "puzzle" in result

    def test_tool_call_get_online(self):
        responses = self._run_mcp_session([
            self._mcp_request(0, "initialize", {}),
            self._mcp_request(1, "tools/call", {
                "name": "LichessService.GetOnline",
                "arguments": {},
            }),
        ])
        result = json.loads(responses[1]["result"]["content"][0]["text"])
        assert result.get("count") == 83422

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
        server._cli(["LichessService", "GetOnline"])
        assert len(calls) == 1
        assert calls[0] == "/lichess.v1.LichessService/GetOnline"

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
        server._cli(["LichessService", "GetDailyPuzzle"])
        assert order == ["A-before", "B-before", "B-after", "A-after"]
