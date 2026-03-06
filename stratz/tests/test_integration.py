"""Integration tests — verify invariant protocol wiring for STRATZ."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest
from google.protobuf import json_format

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
            "StratzService.ExecuteRawQuery",
            "StratzService.GetMatchSummary",
            "StratzService.GetMatchPlayers",
            "StratzService.GetMatchLaneOutcomes",
            "StratzService.GetMatchDotaPlusLevels",
            "StratzService.GetPlayerRecentMatches",
            "StratzService.GetConstantsHeroes",
            "StratzService.GetConstantsItems",
            "StratzService.GetConstantsAbilities",
            "StratzService.GetHeroNeutralItemStats",
        }
        actual = set(server.tools.keys())
        missing = expected - actual
        assert not missing, f"Missing tools: {missing}"

    def test_tools_have_descriptions(self, server):
        for name, tool in server.tools.items():
            assert tool.description, f"{name} has no description"
            assert len(tool.description) > 10, f"{name} description too short"


class TestCLIProjection:
    def test_match_summary(self, server):
        result = server._cli(
            ["StratzService", "GetMatchSummary", "-r", '{"match_id": 8597260572}']
        )
        assert "match" in result

    def test_constants_heroes(self, server):
        result = server._cli(["StratzService", "GetConstantsHeroes"])
        assert "constants" in result
        assert "heroes" in result["constants"]

    def test_raw_query(self, server):
        result = server._cli(
            [
                "StratzService",
                "ExecuteRawQuery",
                "-r",
                '{"query":"query Q { constants { heroes { id name } } }"}',
            ]
        )
        assert "constants" in result

    def test_unknown_method(self, server):
        with pytest.raises(Exception, match="(?i)unknown service/method"):
            server._cli(["StratzService", "DoesNotExist"])

    def test_help(self, server):
        result = server._cli(["--help"])
        assert "StratzService" in result
        assert "GetMatchSummary" in result


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

    def test_match_summary(self):
        result = self._post(
            "/stratz.v1.StratzService/GetMatchSummary",
            {"match_id": 8597260572},
        )
        assert "match" in result

    def test_constants_items(self):
        result = self._post("/stratz.v1.StratzService/GetConstantsItems")
        assert "constants" in result

    def test_404_unknown_route(self):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self._post("/unknown.Service/Method")
        assert exc_info.value.code == 404


class TestLiveStratzAPI:
    def test_live_get_constants_heroes(self):
        if os.getenv("STRATZ_RUN_LIVE_TESTS") != "1":
            pytest.skip("Set STRATZ_RUN_LIVE_TESTS=1 to run live STRATZ API tests")

        token = (os.getenv("STRATZ_API_KEY") or "").strip()
        if not token:
            pytest.skip("Set STRATZ_API_KEY for live STRATZ API tests")

        from stratz_mcp.gen.stratz.v1 import stratz_pb2 as pb
        from stratz_mcp.service import StratzService

        svc = StratzService(api_key=token)
        try:
            resp = svc.GetConstantsHeroes(pb.GetConstantsRequest())
        finally:
            svc._http.close()

        data = json_format.MessageToDict(resp)
        assert "constants" in data
        assert isinstance(data["constants"].get("heroes"), list)
        assert len(data["constants"]["heroes"]) > 0
        assert "id" in data["constants"]["heroes"][0]
