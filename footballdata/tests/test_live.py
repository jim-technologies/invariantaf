"""Live integration tests for Football-Data.org API -- hits the real API.

Run with:
    FOOTBALLDATA_RUN_LIVE_TESTS=1 FOOTBALLDATA_API_KEY=your_key uv run python -m pytest tests/test_live.py -v

Requires a Football-Data.org API key (free tier available).
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

DEFAULT_BASE_URL = "https://api.football-data.org/v4"

pytestmark = pytest.mark.skipif(
    os.getenv("FOOTBALLDATA_RUN_LIVE_TESTS") != "1"
    or not os.getenv("FOOTBALLDATA_API_KEY"),
    reason="Set FOOTBALLDATA_RUN_LIVE_TESTS=1 and FOOTBALLDATA_API_KEY to run live tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors or rate limits."""
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
    from footballdata_mcp.gen.footballdata.v1 import footballdata_pb2 as _footballdata_pb2  # noqa: F401
    from footballdata_mcp.service import FootballDataService

    base_url = (os.getenv("FOOTBALLDATA_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = (os.getenv("FOOTBALLDATA_API_KEY") or "").strip()

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-footballdata-live", version="0.0.1"
    )
    servicer = FootballDataService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="footballdata.v1.FootballDataService")
    yield srv
    srv.stop()


# --- ListCompetitions ---


class TestLiveListCompetitions:
    def test_list_competitions(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "ListCompetitions",
        )
        assert "competitions" in result
        competitions = result["competitions"]
        assert isinstance(competitions, list)
        assert len(competitions) > 0
        comp = competitions[0]
        assert "name" in comp
        assert "code" in comp


# --- GetCompetition ---


class TestLiveGetCompetition:
    def test_get_premier_league(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetCompetition",
            {"code": "PL"},
        )
        assert "competition" in result
        comp = result["competition"]
        assert comp["code"] == "PL"
        assert comp["name"] == "Premier League"

    def test_get_bundesliga(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetCompetition",
            {"code": "BL1"},
        )
        assert "competition" in result
        assert result["competition"]["code"] == "BL1"


# --- GetStandings ---


class TestLiveGetStandings:
    def test_pl_standings(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetStandings",
            {"code": "PL"},
        )
        assert "standings" in result
        standings = result["standings"]
        assert isinstance(standings, list)
        assert len(standings) > 0
        table = standings[0]["table"]
        assert len(table) > 0
        first = table[0]
        assert "position" in first
        assert "team" in first
        assert "points" in first


# --- ListMatches ---


class TestLiveListMatches:
    def test_pl_matches(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "ListMatches",
            {"code": "PL"},
        )
        assert "matches" in result
        matches = result["matches"]
        assert isinstance(matches, list)
        assert len(matches) > 0

    def test_pl_finished_matches(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "ListMatches",
            {"code": "PL", "status": "FINISHED"},
        )
        assert "matches" in result
        for match in result["matches"]:
            assert match["status"] == "FINISHED"


# --- ListTodayMatches ---


class TestLiveListTodayMatches:
    def test_today_matches(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "ListTodayMatches",
        )
        assert "matches" in result
        assert isinstance(result["matches"], list)


# --- GetTeam ---


class TestLiveGetTeam:
    def test_get_arsenal(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetTeam",
            {"id": 57},
        )
        assert result["name"] == "Arsenal FC"
        assert "squad" in result
        assert isinstance(result["squad"], list)

    def test_get_man_city(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetTeam",
            {"id": 65},
        )
        assert result["name"] == "Manchester City FC"


# --- GetScorers ---


class TestLiveGetScorers:
    def test_pl_scorers(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetScorers",
            {"code": "PL"},
        )
        assert "scorers" in result
        scorers = result["scorers"]
        assert isinstance(scorers, list)
        assert len(scorers) > 0
        scorer = scorers[0]
        assert "player" in scorer
        assert "team" in scorer
        assert "goals" in scorer

    def test_pl_scorers_with_limit(self, live_server):
        result = _cli_or_skip(
            live_server, "FootballDataService", "GetScorers",
            {"code": "PL", "limit": 5},
        )
        assert "scorers" in result
        assert len(result["scorers"]) <= 5
