"""Live integration tests for BallDontLie API -- hits the real API.

Run with:
    BALLDONTLIE_RUN_LIVE_TESTS=1 BALLDONTLIE_API_KEY=<key> uv run python -m pytest tests/test_live.py -v

Requires a valid API key (free tier available at https://www.balldontlie.io).
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

DEFAULT_BASE_URL = "https://api.balldontlie.io/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("BALLDONTLIE_RUN_LIVE_TESTS") != "1"
    or not (os.getenv("BALLDONTLIE_API_KEY") or "").strip(),
    reason="Set BALLDONTLIE_RUN_LIVE_TESTS=1 and BALLDONTLIE_API_KEY to run live BallDontLie API tests",
)


def _cli_or_skip(live_server, service, method, params=None):
    """Call a CLI method; skip on transient errors or auth failures."""
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
    from balldontlie_mcp.gen.balldontlie.v1 import balldontlie_pb2 as _balldontlie_pb2  # noqa: F401
    from balldontlie_mcp.service import BallDontLieService

    base_url = (os.getenv("BALLDONTLIE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    api_key = (os.getenv("BALLDONTLIE_API_KEY") or "").strip()

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-balldontlie-live", version="0.0.1"
    )
    servicer = BallDontLieService(base_url=base_url, api_key=api_key)
    srv.register(servicer, service_name="balldontlie.v1.BallDontLieService")
    yield srv
    srv.stop()


# --- ListNBAPlayers ---


class TestLiveListNBAPlayers:
    def test_search_lebron(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAPlayers",
            {"search": "LeBron", "per_page": 5},
        )
        assert "data" in result
        players = result["data"]
        assert isinstance(players, list)
        assert len(players) > 0
        assert "first_name" in players[0]

    def test_search_curry(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAPlayers",
            {"search": "Curry", "per_page": 5},
        )
        assert "data" in result
        assert len(result["data"]) > 0


# --- GetNBAPlayer ---


class TestLiveGetNBAPlayer:
    def test_get_player(self, live_server):
        # First search to get a valid player ID
        search = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAPlayers",
            {"search": "LeBron", "per_page": 1},
        )
        if not search.get("data"):
            pytest.skip("No players found in search")
        player_id = search["data"][0]["id"]

        result = _cli_or_skip(
            live_server, "BallDontLieService", "GetNBAPlayer",
            {"id": player_id},
        )
        assert "data" in result
        assert result["data"]["id"] == player_id


# --- ListNBATeams ---


class TestLiveListNBATeams:
    def test_list_teams(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBATeams",
        )
        assert "data" in result
        teams = result["data"]
        assert isinstance(teams, list)
        assert len(teams) > 0
        assert "full_name" in teams[0]
        assert "abbreviation" in teams[0]


# --- ListNBAGames ---


class TestLiveListNBAGames:
    def test_list_games_by_date(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAGames",
            {"dates": ["2025-01-15"], "per_page": 5},
        )
        assert "data" in result
        games = result["data"]
        assert isinstance(games, list)
        if len(games) > 0:
            assert "home_team" in games[0]
            assert "visitor_team" in games[0]

    def test_list_games_by_season(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAGames",
            {"seasons": [2024], "per_page": 5},
        )
        assert "data" in result
        assert isinstance(result["data"], list)


# --- GetNBAGame ---


class TestLiveGetNBAGame:
    def test_get_game(self, live_server):
        # First list games to get a valid game ID
        search = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAGames",
            {"seasons": [2024], "per_page": 1},
        )
        if not search.get("data"):
            pytest.skip("No games found")
        game_id = search["data"][0]["id"]

        result = _cli_or_skip(
            live_server, "BallDontLieService", "GetNBAGame",
            {"id": game_id},
        )
        assert "data" in result
        assert result["data"]["id"] == game_id


# --- GetNBAStats ---


class TestLiveGetNBAStats:
    def test_get_stats_by_game(self, live_server):
        # First list games to get a valid game ID
        search = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAGames",
            {"seasons": [2024], "per_page": 1},
        )
        if not search.get("data"):
            pytest.skip("No games found")
        game_id = search["data"][0]["id"]

        result = _cli_or_skip(
            live_server, "BallDontLieService", "GetNBAStats",
            {"game_ids": [game_id], "per_page": 5},
        )
        assert "data" in result
        assert isinstance(result["data"], list)


# --- GetNBASeasonAverages ---


class TestLiveGetNBASeasonAverages:
    def test_season_averages(self, live_server):
        # Search for a player to get a valid ID
        search = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAPlayers",
            {"search": "LeBron", "per_page": 1},
        )
        if not search.get("data"):
            pytest.skip("No players found")
        player_id = search["data"][0]["id"]

        result = _cli_or_skip(
            live_server, "BallDontLieService", "GetNBASeasonAverages",
            {"season": 2024, "player_ids": [player_id]},
        )
        assert "data" in result
        assert isinstance(result["data"], list)


# --- ListNBAStandings ---


class TestLiveListNBAStandings:
    def test_standings(self, live_server):
        result = _cli_or_skip(
            live_server, "BallDontLieService", "ListNBAStandings",
            {"season": 2024},
        )
        assert "data" in result
        standings = result["data"]
        assert isinstance(standings, list)
        if len(standings) > 0:
            s = standings[0]
            assert "wins" in s or "team_id" in s
