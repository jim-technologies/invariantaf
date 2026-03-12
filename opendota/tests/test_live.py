"""Live integration tests for OpenDota API -- hits the real API.

Run with:
    OPENDOTA_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) OpenDota endpoints.
Set OPENDOTA_BASE_URL to override the default API base URL.
Set OPENDOTA_API_KEY for higher rate limits (optional).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.opendota.com/api"

pytestmark = pytest.mark.skipif(
    os.getenv("OPENDOTA_RUN_LIVE_TESTS") != "1",
    reason="Set OPENDOTA_RUN_LIVE_TESTS=1 to run live OpenDota API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from gen.opendota.v1 import opendota_pb2 as _opendota_pb2  # noqa: F401

    base_url = (
        os.getenv("OPENDOTA_BASE_URL") or DEFAULT_BASE_URL
    ).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-opendota-live", version="0.0.1"
    )
    srv.connect_http(base_url, service_name="opendota.v1.OpenDotaService")
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def pro_player_account_id(live_server):
    """Discover a valid pro player account_id for tests that need one."""
    result = live_server._cli(["OpenDotaService", "GetProPlayers"])
    data = result.get("data", [])
    assert data, "expected at least one pro player"
    account_id = data[0].get("account_id")
    assert account_id, "expected account_id on pro player"
    return int(account_id)


@pytest.fixture(scope="module")
def hero_id(live_server):
    """Discover a valid hero_id for tests that need one."""
    result = live_server._cli(["OpenDotaService", "GetHeroes"])
    data = result.get("data", [])
    assert data, "expected at least one hero"
    hid = data[0].get("id")
    assert hid, "expected id on hero"
    return int(hid)


@pytest.fixture(scope="module")
def team_id(live_server):
    """Discover a valid team_id for tests that need one."""
    result = live_server._cli(
        ["OpenDotaService", "GetTeams", "-r", json.dumps({"query": {"page": 0}})]
    )
    data = result.get("data", [])
    assert data, "expected at least one team"
    tid = data[0].get("team_id")
    assert tid, "expected team_id on team"
    return int(tid)


# --- Health ---


class TestLiveHealth:
    def test_get_health(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetHealth"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)


# --- Heroes ---


class TestLiveHeroes:
    def test_get_heroes(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetHeroes"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        h = data[0]
        assert "id" in h
        assert "localized_name" in h or "name" in h

    def test_get_hero_stats(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetHeroStats"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_hero_matchups(self, live_server, hero_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetHeroMatchups",
                "-r",
                json.dumps({"hero_id": hero_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        if data:
            m = data[0]
            assert "hero_id" in m
            assert "games_played" in m or "wins" in m

    def test_get_hero_durations(self, live_server, hero_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetHeroDurations",
                "-r",
                json.dumps({"hero_id": hero_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_get_hero_matches(self, live_server, hero_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetHeroMatches",
                "-r",
                json.dumps({"hero_id": hero_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)


# --- Players ---


class TestLivePlayers:
    def test_get_pro_players(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetProPlayers"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        p = data[0]
        assert "account_id" in p

    def test_get_player(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayer",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)

    def test_get_player_win_loss(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayerWinLoss",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert "win" in data or "lose" in data

    def test_get_player_recent_matches(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayerRecentMatches",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_get_player_heroes(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayerHeroes",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_get_player_totals(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayerTotals",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_search_players(self, live_server):
        result = live_server._cli(
            [
                "OpenDotaService",
                "SearchPlayers",
                "-r",
                json.dumps({"query": {"q": "dendi"}}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_get_player_rankings(self, live_server, pro_player_account_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetPlayerRankings",
                "-r",
                json.dumps({"account_id": pro_player_account_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)


# --- Teams ---


class TestLiveTeams:
    def test_get_teams(self, live_server):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetTeams",
                "-r",
                json.dumps({"query": {"page": 0}}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        t = data[0]
        assert "team_id" in t

    def test_get_team(self, live_server, team_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetTeam",
                "-r",
                json.dumps({"team_id": team_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)

    def test_get_team_players(self, live_server, team_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetTeamPlayers",
                "-r",
                json.dumps({"team_id": team_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)

    def test_get_team_heroes(self, live_server, team_id):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetTeamHeroes",
                "-r",
                json.dumps({"team_id": team_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)


# --- Leagues ---


class TestLiveLeagues:
    def test_get_leagues(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetLeagues"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0
        lg = data[0]
        assert "leagueid" in lg or "league_id" in lg


# --- Game data ---


class TestLiveGameData:
    def test_get_benchmarks(self, live_server):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetBenchmarks",
                "-r",
                json.dumps({"query": {"hero_id": 1}}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)

    def test_get_distributions(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetDistributions"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)

    def test_get_constants_resource(self, live_server):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetConstantsResource",
                "-r",
                json.dumps({"resource": "heroes"}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, (dict, list))

    def test_get_rankings(self, live_server):
        result = live_server._cli(
            [
                "OpenDotaService",
                "GetRankings",
                "-r",
                json.dumps({"query": {"hero_id": 1}}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)

    def test_get_pro_matches(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetProMatches"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_public_matches(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetPublicMatches"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_live(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetLive"])
        assert "data" in result
        # Live data may be empty if no games are happening
        data = result["data"]
        assert isinstance(data, list)

    def test_get_schema(self, live_server):
        result = live_server._cli(["OpenDotaService", "GetSchema"])
        assert "data" in result
        data = result["data"]
        assert isinstance(data, list)
        assert len(data) > 0


# --- Match data ---


class TestLiveMatches:
    def test_get_pro_match(self, live_server):
        """Fetch a pro match ID first, then retrieve its data."""
        pro_result = live_server._cli(["OpenDotaService", "GetProMatches"])
        matches = pro_result.get("data", [])
        if not matches:
            pytest.skip("no pro matches available")
        match_id = int(matches[0].get("match_id", 0))
        if not match_id:
            pytest.skip("no match_id in pro match data")

        result = live_server._cli(
            [
                "OpenDotaService",
                "GetMatch",
                "-r",
                json.dumps({"match_id": match_id}),
            ]
        )
        assert "data" in result
        data = result["data"]
        assert isinstance(data, dict)
        assert int(float(data.get("match_id", 0))) == match_id
