"""Integration tests -- descriptor/registration/CLI/HTTP wiring."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from tests.conftest import DESCRIPTOR_PATH


class TestDescriptorAndRegistration:
    def test_descriptor_loads(self):
        from invariant import Server

        srv = Server.from_descriptor(DESCRIPTOR_PATH)
        assert srv is not None

    def test_all_tools_registered(self, server):
        assert len(server.tools) == 55

    def test_tool_names(self, server):
        expected = {
            "OpenDotaService.GetHealth",
            "OpenDotaService.GetProPlayers",
            "OpenDotaService.GetTopPlayers",
            "OpenDotaService.GetPlayerRankings",
            "OpenDotaService.GetTeamPlayers",
            "OpenDotaService.PostRequestMatchId",
        }
        assert expected.issubset(set(server.tools.keys()))


class TestCLIProjection:
    def test_get_health(self, server):
        result = server._cli(["OpenDotaService", "GetHealth"])
        assert "data" in result
        assert "postgresUsage" in result["data"]

    def test_get_match(self, server):
        result = server._cli(["OpenDotaService", "GetMatch", "-r", '{"match_id":1001}'])
        assert "data" in result
        assert int(float(result["data"]["match_id"])) == 1001

    def test_get_top_players(self, server):
        result = server._cli(["OpenDotaService", "GetTopPlayers", "-r", '{"query":{"turbo":1}}'])
        assert "data" in result
        assert len(result["data"]) >= 1

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["OpenDotaService", "DoesNotExist"])


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

    def test_health(self):
        result = self._post("/opendota.v1.OpenDotaService/GetHealth")
        assert "data" in result

    def test_get_teams(self):
        result = self._post("/opendota.v1.OpenDotaService/GetTeams", {"query": {"page": 0}})
        assert "data" in result
        assert len(result["data"]) >= 1

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404
