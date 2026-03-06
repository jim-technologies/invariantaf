"""Unit tests — every LichessService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from lichess_mcp.gen.lichess.v1 import lichess_pb2 as pb
from tests.conftest import (
    FAKE_CLOUD_EVAL,
    FAKE_DAILY_PUZZLE,
    FAKE_GAME,
    FAKE_LEADERBOARD,
    FAKE_ONLINE_COUNT,
    FAKE_PUZZLE,
    FAKE_RATING_HISTORY,
    FAKE_TEAM,
    FAKE_USER,
)


class TestGetUser:
    def test_basic_fields(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.id == "drnykterstein"
        assert resp.username == "DrNykterstein"
        assert resp.title == "GM"
        assert resp.online is True

    def test_profile_fields(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.bio == "Chess is life."
        assert resp.country == "NO"

    def test_game_count(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.total_games == 15500

    def test_play_time(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.play_time == 5000000

    def test_created_at(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.created_at == 1500000000000

    def test_url(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.url == "https://lichess.org/@/DrNykterstein"

    def test_perfs(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert "bullet" in resp.perfs
        assert resp.perfs["bullet"].rating == 3200
        assert resp.perfs["bullet"].games == 5000
        assert resp.perfs["bullet"].rd == 45
        assert resp.perfs["bullet"].prog == 10
        assert resp.perfs["bullet"].prov is False

    def test_perfs_blitz(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.perfs["blitz"].rating == 3100
        assert resp.perfs["blitz"].games == 8000

    def test_perfs_classical_provisional(self, service):
        resp = service.GetUser(pb.GetUserRequest(username="drnykterstein"))
        assert resp.perfs["classical"].prov is True


class TestGetUserRatingHistory:
    def test_returns_history(self, service):
        resp = service.GetUserRatingHistory(pb.GetUserRatingHistoryRequest(username="drnykterstein"))
        assert len(resp.history) == 2

    def test_bullet_history(self, service):
        resp = service.GetUserRatingHistory(pb.GetUserRatingHistoryRequest(username="drnykterstein"))
        bullet = resp.history[0]
        assert bullet.name == "Bullet"
        assert len(bullet.points) == 3
        assert bullet.points[0].year == 2023
        assert bullet.points[0].month == 1
        assert bullet.points[0].day == 15
        assert bullet.points[0].rating == 3100

    def test_blitz_history(self, service):
        resp = service.GetUserRatingHistory(pb.GetUserRatingHistoryRequest(username="drnykterstein"))
        blitz = resp.history[1]
        assert blitz.name == "Blitz"
        assert len(blitz.points) == 2
        assert blitz.points[1].rating == 3100

    def test_latest_bullet_rating(self, service):
        resp = service.GetUserRatingHistory(pb.GetUserRatingHistoryRequest(username="drnykterstein"))
        bullet = resp.history[0]
        assert bullet.points[2].year == 2024
        assert bullet.points[2].rating == 3200


class TestGetUserGames:
    def test_returns_games(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        assert len(resp.games) == 2

    def test_first_game_fields(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[0]
        assert g.id == "abcd1234"
        assert g.rated is True
        assert g.variant == "standard"
        assert g.speed == "blitz"
        assert g.status == "mate"
        assert g.winner == "white"

    def test_players(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[0]
        assert g.white.username == "DrNykterstein"
        assert g.white.rating == 3100
        assert g.white.rating_diff == 5
        assert g.black.username == "Firouzja2003"
        assert g.black.rating == 3000

    def test_opening(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[0]
        assert g.opening_eco == "C65"
        assert g.opening_name == "Ruy Lopez: Berlin Defense"

    def test_clock(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[0]
        assert g.clock_initial == 180
        assert g.clock_increment == 0

    def test_moves(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[0]
        assert "e4" in g.moves
        assert "Bb5" in g.moves

    def test_second_game(self, service):
        resp = service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        g = resp.games[1]
        assert g.id == "efgh5678"
        assert g.speed == "bullet"
        assert g.winner == "black"

    def test_default_max(self, service, mock_http):
        service.GetUserGames(pb.GetUserGamesRequest(username="drnykterstein"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("max") == 10


class TestGetGame:
    def test_returns_game(self, service):
        resp = service.GetGame(pb.GetGameRequest(game_id="abcd1234"))
        assert resp.game.id == "abcd1234"
        assert resp.game.rated is True
        assert resp.game.status == "mate"

    def test_players(self, service):
        resp = service.GetGame(pb.GetGameRequest(game_id="abcd1234"))
        assert resp.game.white.username == "DrNykterstein"
        assert resp.game.black.username == "Firouzja2003"

    def test_opening(self, service):
        resp = service.GetGame(pb.GetGameRequest(game_id="abcd1234"))
        assert resp.game.opening_name == "Ruy Lopez: Berlin Defense"

    def test_winner(self, service):
        resp = service.GetGame(pb.GetGameRequest(game_id="abcd1234"))
        assert resp.game.winner == "white"


class TestGetDailyPuzzle:
    def test_returns_puzzle(self, service):
        resp = service.GetDailyPuzzle(pb.GetDailyPuzzleRequest())
        assert resp.puzzle.id == "K69di"
        assert resp.puzzle.rating == 1850

    def test_solution(self, service):
        resp = service.GetDailyPuzzle(pb.GetDailyPuzzleRequest())
        assert resp.puzzle.solution == ["e2e4", "d7d5", "e4d5"]

    def test_themes(self, service):
        resp = service.GetDailyPuzzle(pb.GetDailyPuzzleRequest())
        assert "fork" in resp.puzzle.themes
        assert "middlegame" in resp.puzzle.themes

    def test_plays(self, service):
        resp = service.GetDailyPuzzle(pb.GetDailyPuzzleRequest())
        assert resp.puzzle.plays == 125000

    def test_game_id(self, service):
        resp = service.GetDailyPuzzle(pb.GetDailyPuzzleRequest())
        assert resp.puzzle.game_id == "Xg7a1B2c"


class TestGetPuzzle:
    def test_returns_puzzle(self, service):
        resp = service.GetPuzzle(pb.GetPuzzleRequest(id="K69di"))
        assert resp.puzzle.id == "A1b2C"
        assert resp.puzzle.rating == 2200

    def test_solution(self, service):
        resp = service.GetPuzzle(pb.GetPuzzleRequest(id="K69di"))
        assert resp.puzzle.solution == ["f3g5", "h7h6", "g5f7"]

    def test_themes(self, service):
        resp = service.GetPuzzle(pb.GetPuzzleRequest(id="K69di"))
        assert "sacrifice" in resp.puzzle.themes
        assert "mateIn3" in resp.puzzle.themes

    def test_plays(self, service):
        resp = service.GetPuzzle(pb.GetPuzzleRequest(id="K69di"))
        assert resp.puzzle.plays == 50000


class TestGetLeaderboard:
    def test_returns_players(self, service):
        resp = service.GetLeaderboard(pb.GetLeaderboardRequest(nb=10, perf_type="bullet"))
        assert len(resp.users) == 3

    def test_first_player(self, service):
        resp = service.GetLeaderboard(pb.GetLeaderboardRequest(nb=10, perf_type="bullet"))
        assert resp.users[0].username == "DrNykterstein"
        assert resp.users[0].title == "GM"
        assert resp.users[0].rating == 3200
        assert resp.users[0].online is True

    def test_second_player(self, service):
        resp = service.GetLeaderboard(pb.GetLeaderboardRequest(nb=10, perf_type="bullet"))
        assert resp.users[1].username == "Firouzja2003"
        assert resp.users[1].rating == 3150
        assert resp.users[1].online is False

    def test_third_player(self, service):
        resp = service.GetLeaderboard(pb.GetLeaderboardRequest(nb=10, perf_type="bullet"))
        assert resp.users[2].username == "Hikaru"
        assert resp.users[2].rating == 3100


class TestGetCloudEval:
    def test_returns_eval(self, service):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        resp = service.GetCloudEval(pb.GetCloudEvalRequest(fen=fen))
        assert resp.fen == fen
        assert resp.knodes == 25000
        assert resp.depth == 40

    def test_principal_variations(self, service):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        resp = service.GetCloudEval(pb.GetCloudEvalRequest(fen=fen))
        assert len(resp.pvs) == 2
        assert resp.pvs[0].moves == "e7e5 g1f3 b8c6"
        assert resp.pvs[0].cp == 20
        assert resp.pvs[0].mate == 0

    def test_second_variation(self, service):
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        resp = service.GetCloudEval(pb.GetCloudEvalRequest(fen=fen))
        assert resp.pvs[1].cp == 35


class TestGetOnline:
    def test_returns_count(self, service):
        resp = service.GetOnline(pb.GetOnlineRequest())
        assert resp.count == 83422


class TestGetTeam:
    def test_basic_fields(self, service):
        resp = service.GetTeam(pb.GetTeamRequest(team_id="lichess-swiss"))
        assert resp.id == "lichess-swiss"
        assert resp.name == "Lichess Swiss"
        assert resp.nb_members == 50000

    def test_description(self, service):
        resp = service.GetTeam(pb.GetTeamRequest(team_id="lichess-swiss"))
        assert "official" in resp.description.lower()

    def test_leaders(self, service):
        resp = service.GetTeam(pb.GetTeamRequest(team_id="lichess-swiss"))
        assert len(resp.leaders) == 2
        assert "thibault" in resp.leaders

    def test_open(self, service):
        resp = service.GetTeam(pb.GetTeamRequest(team_id="lichess-swiss"))
        assert resp.open is True

    def test_url(self, service):
        resp = service.GetTeam(pb.GetTeamRequest(team_id="lichess-swiss"))
        assert "lichess.org/team/lichess-swiss" in resp.url
