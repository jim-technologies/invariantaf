"""Live integration tests for PandaScore API -- hits the real API.

Run with:
    PANDASCORE_RUN_LIVE_TESTS=1 PANDASCORE_API_KEY=<your_key> uv run python -m pytest tests/test_live.py -v

Requires a valid PandaScore API key (free tier: 1000 calls/hr).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

DEFAULT_BASE_URL = "https://api.pandascore.co"

pytestmark = pytest.mark.skipif(
    os.getenv("PANDASCORE_RUN_LIVE_TESTS") != "1"
    or not os.getenv("PANDASCORE_API_KEY"),
    reason="Set PANDASCORE_RUN_LIVE_TESTS=1 and PANDASCORE_API_KEY to run live PandaScore API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors."""
    args = [service, method]
    if params:
        args.extend(["-r", json.dumps(params)])
    try:
        return live_server._cli(args)
    except (httpx.ConnectTimeout, httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"{method}: {type(exc).__name__}: {exc}")
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("401", "403", "429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from pandascore_mcp.gen.pandascore.v1 import pandascore_pb2 as _pandascore_pb2  # noqa: F401
    from pandascore_mcp.service import PandaScoreService

    base_url = (os.getenv("PANDASCORE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = os.getenv("PANDASCORE_API_KEY", "")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-pandascore-live", version="0.0.1"
    )
    servicer = PandaScoreService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="pandascore.v1.PandaScoreService")
    yield srv
    srv.stop()


# --- ListMatches ---


class TestLiveListMatches:
    def test_list_matches(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListMatches", {}
        )
        assert "matches" in result
        matches = result["matches"]
        assert isinstance(matches, list)
        assert len(matches) > 0
        m = matches[0]
        assert "id" in m
        assert "name" in m
        assert "status" in m


# --- ListUpcomingMatches ---


class TestLiveListUpcomingMatches:
    def test_list_upcoming(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListUpcomingMatches", {}
        )
        assert "matches" in result
        matches = result["matches"]
        assert isinstance(matches, list)
        # Upcoming might be empty if no matches scheduled
        if len(matches) > 0:
            assert matches[0]["status"] == "not_started"


# --- ListRunningMatches ---


class TestLiveListRunningMatches:
    def test_list_running(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListRunningMatches", {}
        )
        assert "matches" in result
        matches = result["matches"]
        assert isinstance(matches, list)
        # Running might be empty if no live matches
        if len(matches) > 0:
            assert matches[0]["status"] == "running"


# --- ListPastMatches ---


class TestLiveListPastMatches:
    def test_list_past(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListPastMatches", {}
        )
        assert "matches" in result
        matches = result["matches"]
        assert isinstance(matches, list)
        assert len(matches) > 0
        assert matches[0]["status"] == "finished"


# --- ListTournaments ---


class TestLiveListTournaments:
    def test_list_tournaments(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListTournaments", {}
        )
        assert "tournaments" in result
        tournaments = result["tournaments"]
        assert isinstance(tournaments, list)
        assert len(tournaments) > 0
        t = tournaments[0]
        assert "id" in t
        assert "name" in t


# --- ListTeams ---


class TestLiveListTeams:
    def test_list_teams(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListTeams", {}
        )
        assert "teams" in result
        teams = result["teams"]
        assert isinstance(teams, list)
        assert len(teams) > 0
        team = teams[0]
        assert "id" in team
        assert "name" in team


# --- ListPlayers ---


class TestLiveListPlayers:
    def test_list_players(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListPlayers", {}
        )
        assert "players" in result
        players = result["players"]
        assert isinstance(players, list)
        assert len(players) > 0
        p = players[0]
        assert "id" in p
        assert "name" in p


# --- ListLeagues ---


class TestLiveListLeagues:
    def test_list_leagues(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListLeagues", {}
        )
        assert "leagues" in result
        leagues = result["leagues"]
        assert isinstance(leagues, list)
        assert len(leagues) > 0
        lg = leagues[0]
        assert "id" in lg
        assert "name" in lg


# --- ListSeries ---


class TestLiveListSeries:
    def test_list_series(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListSeries", {}
        )
        assert "series" in result
        series = result["series"]
        assert isinstance(series, list)
        # Upcoming series might be empty
        if len(series) > 0:
            s = series[0]
            assert "id" in s
            assert "name" in s


# --- ListHeroes ---


class TestLiveListHeroes:
    def test_list_heroes(self, live_server):
        result = _cli_or_skip(
            live_server, "PandaScoreService", "ListHeroes", {}
        )
        assert "heroes" in result
        heroes = result["heroes"]
        assert isinstance(heroes, list)
        assert len(heroes) > 0
        h = heroes[0]
        assert "id" in h
        assert "name" in h
