"""LichessService — wraps the Lichess public API into proto RPCs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from lichess_mcp.gen.lichess.v1 import lichess_pb2 as pb

_BASE_URL = "https://lichess.org"


class LichessService:
    """Implements LichessService RPCs via the free Lichess API."""

    def __init__(self, *, api_token: str | None = None):
        self._api_token = api_token or os.environ.get("LICHESS_API_TOKEN")
        headers = {"Accept": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        self._http = httpx.Client(timeout=30, headers=headers)

    def _get(self, path: str, params: dict | None = None, headers: dict | None = None) -> Any:
        h = dict(headers or {})
        resp = self._http.get(f"{_BASE_URL}{path}", params=params or {}, headers=h)
        resp.raise_for_status()
        return resp.json()

    def _get_ndjson(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch an NDJSON endpoint and return a list of parsed dicts."""
        resp = self._http.get(
            f"{_BASE_URL}{path}",
            params=params or {},
            headers={"Accept": "application/x-ndjson"},
        )
        resp.raise_for_status()
        results = []
        for line in resp.text.strip().split("\n"):
            line = line.strip()
            if line:
                results.append(json.loads(line))
        return results

    def GetUser(self, request: Any, context: Any = None) -> pb.GetUserResponse:
        raw = self._get(f"/api/user/{request.username}")

        perfs_map = {}
        for variant, data in raw.get("perfs", {}).items():
            perfs_map[variant] = pb.PerfRating(
                games=data.get("games", 0),
                rating=data.get("rating", 0),
                rd=data.get("rd", 0),
                prog=data.get("prog", 0),
                prov=data.get("prov", False),
            )

        count = raw.get("count", {})
        return pb.GetUserResponse(
            id=raw.get("id", ""),
            username=raw.get("username", ""),
            bio=raw.get("profile", {}).get("bio", "") if raw.get("profile") else "",
            title=raw.get("title", ""),
            country=raw.get("profile", {}).get("country", "") if raw.get("profile") else "",
            online=raw.get("online", False),
            total_games=count.get("all", 0),
            play_time=raw.get("playTime", {}).get("total", 0) if raw.get("playTime") else 0,
            created_at=raw.get("createdAt", 0),
            url=raw.get("url", ""),
            perfs=perfs_map,
        )

    def GetUserRatingHistory(self, request: Any, context: Any = None) -> pb.GetUserRatingHistoryResponse:
        raw = self._get(f"/api/user/{request.username}/rating-history")

        resp = pb.GetUserRatingHistoryResponse()
        for entry in raw:
            points = []
            for pt in entry.get("points", []):
                points.append(pb.RatingPoint(
                    year=pt[0],
                    month=pt[1],
                    day=pt[2],
                    rating=pt[3],
                ))
            resp.history.append(pb.RatingHistoryEntry(
                name=entry.get("name", ""),
                points=points,
            ))
        return resp

    def GetUserGames(self, request: Any, context: Any = None) -> pb.GetUserGamesResponse:
        params = {}
        max_games = request.max or 10
        params["max"] = max_games
        params["pgnInJson"] = "true"
        if request.rated:
            params["rated"] = "true"
        if request.perf_type:
            params["perfType"] = request.perf_type

        raw_games = self._get_ndjson(f"/api/games/user/{request.username}", params)

        resp = pb.GetUserGamesResponse()
        for g in raw_games:
            resp.games.append(self._parse_game(g))
        return resp

    def GetGame(self, request: Any, context: Any = None) -> pb.GetGameResponse:
        raw = self._get(f"/game/export/{request.game_id}", params={"pgnInJson": "true"})
        return pb.GetGameResponse(game=self._parse_game(raw))

    def GetDailyPuzzle(self, request: Any, context: Any = None) -> pb.GetDailyPuzzleResponse:
        raw = self._get("/api/puzzle/daily")
        return pb.GetDailyPuzzleResponse(puzzle=self._parse_puzzle(raw))

    def GetPuzzle(self, request: Any, context: Any = None) -> pb.GetPuzzleResponse:
        raw = self._get(f"/api/puzzle/{request.id}")
        return pb.GetPuzzleResponse(puzzle=self._parse_puzzle(raw))

    def GetLeaderboard(self, request: Any, context: Any = None) -> pb.GetLeaderboardResponse:
        nb = request.nb or 10
        perf_type = request.perf_type or "bullet"
        raw = self._get(f"/api/player/top/{nb}/{perf_type}")

        resp = pb.GetLeaderboardResponse()
        for u in raw.get("users", []):
            resp.users.append(pb.LeaderboardPlayer(
                username=u.get("username", ""),
                title=u.get("title", ""),
                rating=u.get("perfs", {}).get(perf_type, {}).get("rating", 0),
                online=u.get("online", False),
            ))
        return resp

    def GetCloudEval(self, request: Any, context: Any = None) -> pb.GetCloudEvalResponse:
        params = {"fen": request.fen}
        if request.multi_pv:
            params["multiPv"] = request.multi_pv
        raw = self._get("/api/cloud-eval", params=params)

        resp = pb.GetCloudEvalResponse(
            fen=raw.get("fen", ""),
            knodes=raw.get("knodes", 0),
            depth=raw.get("depth", 0),
        )
        for pv in raw.get("pvs", []):
            resp.pvs.append(pb.PrincipalVariation(
                moves=pv.get("moves", ""),
                cp=pv.get("cp", 0),
                mate=pv.get("mate", 0),
            ))
        return resp

    def GetOnline(self, request: Any, context: Any = None) -> pb.GetOnlineResponse:
        # Lichess /api/user/count returns a plain integer, but we request JSON header.
        # The response is actually just a number, so we handle it specially.
        resp = self._http.get(
            f"{_BASE_URL}/api/user/count",
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        # The response is a plain integer text like "83422"
        text = resp.text.strip()
        try:
            count = int(text)
        except ValueError:
            # If it returns JSON for some reason
            data = json.loads(text)
            count = data if isinstance(data, int) else data.get("count", 0)
        return pb.GetOnlineResponse(count=count)

    def GetTeam(self, request: Any, context: Any = None) -> pb.GetTeamResponse:
        raw = self._get(f"/api/team/{request.team_id}")

        leaders = []
        for leader in raw.get("leaders", []):
            if isinstance(leader, dict):
                leaders.append(leader.get("name", leader.get("id", "")))
            elif isinstance(leader, str):
                leaders.append(leader)

        return pb.GetTeamResponse(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            nb_members=raw.get("nbMembers", 0),
            leaders=leaders,
            open=raw.get("open", False),
            url=f"https://lichess.org/team/{raw.get('id', '')}",
        )

    def _parse_game(self, g: dict) -> pb.Game:
        """Parse a game JSON dict into a Game proto message."""
        players = g.get("players", {})
        white_data = players.get("white", {})
        black_data = players.get("black", {})

        white_user = white_data.get("user", {})
        black_user = black_data.get("user", {})

        clock = g.get("clock", {})

        return pb.Game(
            id=g.get("id", ""),
            rated=g.get("rated", False),
            variant=g.get("variant", ""),
            speed=g.get("speed", ""),
            perf=g.get("perf", ""),
            created_at=g.get("createdAt", 0),
            last_move_at=g.get("lastMoveAt", 0),
            status=g.get("status", ""),
            white=pb.GamePlayer(
                username=white_user.get("name", white_user.get("id", "")),
                rating=white_data.get("rating", 0),
                rating_diff=white_data.get("ratingDiff", 0),
            ),
            black=pb.GamePlayer(
                username=black_user.get("name", black_user.get("id", "")),
                rating=black_data.get("rating", 0),
                rating_diff=black_data.get("ratingDiff", 0),
            ),
            moves=g.get("moves", ""),
            opening_eco=g.get("opening", {}).get("eco", "") if g.get("opening") else "",
            opening_name=g.get("opening", {}).get("name", "") if g.get("opening") else "",
            clock_initial=clock.get("initial", 0) if clock else 0,
            clock_increment=clock.get("increment", 0) if clock else 0,
            winner=g.get("winner", ""),
        )

    def _parse_puzzle(self, raw: dict) -> pb.Puzzle:
        """Parse a puzzle JSON dict into a Puzzle proto message."""
        puzzle_data = raw.get("puzzle", {})
        game_data = raw.get("game", {})

        return pb.Puzzle(
            id=str(puzzle_data.get("id", "")),
            rating=puzzle_data.get("rating", 0),
            plays=puzzle_data.get("plays", 0),
            initial_fen=puzzle_data.get("initialPly", 0) and game_data.get("pgn", ""),
            solution=puzzle_data.get("solution", []),
            themes=puzzle_data.get("themes", []),
            initial_ply=puzzle_data.get("initialPly", 0),
            game_id=game_data.get("id", ""),
        )
