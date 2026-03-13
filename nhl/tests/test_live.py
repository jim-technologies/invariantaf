"""Live integration tests for NHL API -- hits the real API.

Run with:
    NHL_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) endpoints.
No API keys or credentials needed.
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

DEFAULT_BASE_URL = "https://api-web.nhle.com"

pytestmark = pytest.mark.skipif(
    os.getenv("NHL_RUN_LIVE_TESTS") != "1",
    reason="Set NHL_RUN_LIVE_TESTS=1 to run live NHL API tests",
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
        if any(code in msg for code in ("429", "500", "502", "503", "Timeout", "timed out")):
            pytest.skip(f"{method}: {msg[:120]}")
        raise


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from nhl_mcp.gen.nhl.v1 import nhl_pb2 as _nhl_pb2  # noqa: F401
    from nhl_mcp.service import NHLService

    base_url = (os.getenv("NHL_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-nhl-live", version="0.0.1"
    )
    servicer = NHLService(base_url=base_url)
    srv.register(servicer, service_name="nhl.v1.NHLService")
    yield srv
    srv.stop()


# --- ListTeams ---


class TestLiveListTeams:
    def test_list_teams(self, live_server):
        result = _cli_or_skip(live_server, "NHLService", "ListTeams")
        assert "teams" in result
        teams = result["teams"]
        assert isinstance(teams, list)
        assert len(teams) >= 32  # NHL has 32 teams
        t = teams[0]
        assert "team_abbrev" in t
        assert "team_name" in t
        assert "conference_name" in t
        assert "division_name" in t


# --- GetStandings ---


class TestLiveGetStandings:
    def test_full_standings(self, live_server):
        result = _cli_or_skip(live_server, "NHLService", "GetStandings")
        assert "standings" in result
        standings = result["standings"]
        assert isinstance(standings, list)
        assert len(standings) >= 32
        s = standings[0]
        assert "team_abbrev" in s
        assert s["wins"] > 0 or s.get("games_played", 0) >= 0
        assert "points" in s
        assert "losses" in s
        assert "goal_for" in s
        assert "goal_against" in s


# --- GetSchedule ---


class TestLiveGetSchedule:
    def test_get_schedule_now(self, live_server):
        result = _cli_or_skip(live_server, "NHLService", "GetSchedule")
        assert "games" in result
        games = result["games"]
        assert isinstance(games, list)
        # There may be no games today, so just check structure
        if len(games) > 0:
            g = games[0]
            assert "id" in g
            assert "game_state" in g
            assert "away_team" in g
            assert "home_team" in g

    def test_get_schedule_with_date(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetSchedule",
            {"date": "2026-01-15"},
        )
        assert "games" in result
        games = result["games"]
        assert isinstance(games, list)
        if len(games) > 0:
            assert "away_team" in games[0]
            assert "home_team" in games[0]


# --- GetGameBoxscore ---


class TestLiveGetGameBoxscore:
    def test_get_boxscore(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetGameBoxscore",
            {"game_id": 2025020001},
        )
        assert "id" in result
        assert "game_state" in result
        assert "away_team" in result
        assert "home_team" in result
        away = result["away_team"]
        assert "abbrev" in away
        assert "score" in away
        assert "forwards" in away
        assert "goalies" in away


# --- GetPlayerStats ---


class TestLiveGetPlayerStats:
    def test_mcdavid(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetPlayerStats",
            {"player_id": 8478402},
        )
        assert result["first_name"] == "Connor"
        assert result["last_name"] == "McDavid"
        assert result["position"] == "C"
        assert result["team_abbrev"] == "EDM"
        assert result["is_active"] is True
        assert "current_season_stats" in result
        assert result["current_season_stats"]["games_played"] > 0
        assert "career_totals" in result
        assert result["career_totals"]["points"] > 0

    def test_matthews(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetPlayerStats",
            {"player_id": 8479318},
        )
        assert result["last_name"] == "Matthews"
        assert result["is_active"] is True


# --- GetTeamSchedule ---


class TestLiveGetTeamSchedule:
    def test_leafs_schedule(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetTeamSchedule",
            {"team_abbrev": "TOR"},
        )
        assert "games" in result
        games = result["games"]
        assert isinstance(games, list)
        assert len(games) > 0
        g = games[0]
        assert "id" in g
        assert "game_state" in g
        assert "away_team" in g
        assert "home_team" in g


# --- GetTeamRoster ---


class TestLiveGetTeamRoster:
    def test_leafs_roster(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetTeamRoster",
            {"team_abbrev": "TOR"},
        )
        assert "forwards" in result
        assert "defensemen" in result
        assert "goalies" in result
        assert len(result["forwards"]) > 0
        assert len(result["defensemen"]) > 0
        assert len(result["goalies"]) > 0
        fwd = result["forwards"][0]
        assert "first_name" in fwd
        assert "last_name" in fwd
        assert "position_code" in fwd

    def test_oilers_roster(self, live_server):
        result = _cli_or_skip(
            live_server, "NHLService", "GetTeamRoster",
            {"team_abbrev": "EDM"},
        )
        assert len(result["forwards"]) > 0


# --- GetScoreboard ---


class TestLiveGetScoreboard:
    def test_scoreboard_now(self, live_server):
        result = _cli_or_skip(live_server, "NHLService", "GetScoreboard")
        assert "games" in result
        games = result["games"]
        assert isinstance(games, list)
        # May be empty if no games today
        if len(games) > 0:
            g = games[0]
            assert "id" in g
            assert "game_state" in g
            assert "away_team" in g
            assert "home_team" in g
