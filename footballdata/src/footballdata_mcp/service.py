"""Football-Data.org service implementation for Invariant Protocol."""

from __future__ import annotations

import datetime
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from footballdata_mcp.gen.footballdata.v1 import footballdata_pb2 as pb

DEFAULT_BASE_URL = "https://api.football-data.org/v4"


class FootballDataService:
    """Implements FootballDataService -- Football-Data.org API endpoints."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # -------------------------
    # RPC handlers
    # -------------------------

    def ListCompetitions(
        self, request: pb.ListCompetitionsRequest, context: Any = None
    ) -> pb.ListCompetitionsResponse:
        payload = self._get("/competitions")
        competitions = payload.get("competitions", [])
        transformed = [self._transform_competition(c) for c in competitions]
        return self._parse_message(
            {"competitions": transformed}, pb.ListCompetitionsResponse
        )

    def GetCompetition(
        self, request: pb.GetCompetitionRequest, context: Any = None
    ) -> pb.GetCompetitionResponse:
        payload = self._get(f"/competitions/{request.code}")
        transformed = self._transform_competition(payload)
        return self._parse_message(
            {"competition": transformed}, pb.GetCompetitionResponse
        )

    def GetStandings(
        self, request: pb.GetStandingsRequest, context: Any = None
    ) -> pb.GetStandingsResponse:
        payload = self._get(f"/competitions/{request.code}/standings")
        competition = self._transform_competition(payload.get("competition", {}))
        standings = [self._transform_standing(s) for s in payload.get("standings", [])]
        return self._parse_message(
            {"competition": competition, "standings": standings},
            pb.GetStandingsResponse,
        )

    def ListMatches(
        self, request: pb.ListMatchesRequest, context: Any = None
    ) -> pb.ListMatchesResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "date_from"):
            query["dateFrom"] = request.date_from
        if self._has_field(request, "date_to"):
            query["dateTo"] = request.date_to
        if self._has_field(request, "status"):
            query["status"] = request.status

        payload = self._get(f"/competitions/{request.code}/matches", query or None)
        matches = [self._transform_match(m) for m in payload.get("matches", [])]
        return self._parse_message({"matches": matches}, pb.ListMatchesResponse)

    def GetMatch(
        self, request: pb.GetMatchRequest, context: Any = None
    ) -> pb.GetMatchResponse:
        payload = self._get(f"/matches/{request.id}")
        transformed = self._transform_match(payload)
        return self._parse_message({"match": transformed}, pb.GetMatchResponse)

    def ListTodayMatches(
        self, request: pb.ListTodayMatchesRequest, context: Any = None
    ) -> pb.ListTodayMatchesResponse:
        today = datetime.date.today().isoformat()
        query = {"dateFrom": today, "dateTo": today}
        payload = self._get("/matches", query)
        matches = [self._transform_match(m) for m in payload.get("matches", [])]
        return self._parse_message({"matches": matches}, pb.ListTodayMatchesResponse)

    def GetTeam(
        self, request: pb.GetTeamRequest, context: Any = None
    ) -> pb.GetTeamResponse:
        payload = self._get(f"/teams/{request.id}")
        transformed = self._transform_team(payload)
        return self._parse_message(transformed, pb.GetTeamResponse)

    def GetScorers(
        self, request: pb.GetScorersRequest, context: Any = None
    ) -> pb.GetScorersResponse:
        query: dict[str, Any] = {}
        if self._has_field(request, "limit"):
            query["limit"] = request.limit

        payload = self._get(
            f"/competitions/{request.code}/scorers", query or None
        )
        competition = self._transform_competition(payload.get("competition", {}))
        scorers = [self._transform_scorer(s) for s in payload.get("scorers", [])]
        return self._parse_message(
            {"competition": competition, "scorers": scorers}, pb.GetScorersResponse
        )

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["X-Auth-Token"] = self._api_key

        response = self._client.request("GET", url, headers=headers)

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    def _build_url(self, path: str, query: dict[str, Any] | None = None) -> str:
        full = f"{self._base_url}{path}"
        if not query:
            return full
        qs = urllib.parse.urlencode(
            [(k, self._to_http_scalar(v)) for k, v in query.items() if v is not None]
        )
        return f"{full}?{qs}" if qs else full

    def _to_http_scalar(self, value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value
        if isinstance(value, int | float):
            return str(value)
        return str(value)

    # -------------------------
    # Response transforms
    # -------------------------

    def _transform_competition(self, data: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": data.get("id", 0),
            "name": data.get("name", ""),
            "code": data.get("code", ""),
        }
        area = data.get("area")
        if area and isinstance(area, dict):
            result["area"] = {
                "name": area.get("name", ""),
                "code": area.get("code", ""),
            }
        season = data.get("currentSeason")
        if season and isinstance(season, dict):
            result["current_season"] = {
                "id": season.get("id", 0),
                "start_date": season.get("startDate", ""),
                "end_date": season.get("endDate", ""),
                "current_matchday": season.get("currentMatchday", 0),
            }
        return result

    def _transform_standing(self, data: dict[str, Any]) -> dict[str, Any]:
        table_entries = []
        for entry in data.get("table", []):
            team = entry.get("team", {})
            table_entries.append({
                "position": entry.get("position", 0),
                "team": {
                    "id": team.get("id", 0),
                    "name": team.get("name", ""),
                    "short_name": team.get("shortName", ""),
                    "tla": team.get("tla", ""),
                    "crest": team.get("crest", ""),
                },
                "played_games": entry.get("playedGames", 0),
                "won": entry.get("won", 0),
                "draw": entry.get("draw", 0),
                "lost": entry.get("lost", 0),
                "points": entry.get("points", 0),
                "goals_for": entry.get("goalsFor", 0),
                "goals_against": entry.get("goalsAgainst", 0),
                "goal_difference": entry.get("goalDifference", 0),
            })
        return {
            "stage": data.get("stage", ""),
            "type": data.get("type", ""),
            "group": data.get("group", ""),
            "table": table_entries,
        }

    def _transform_match(self, data: dict[str, Any]) -> dict[str, Any]:
        score_raw = data.get("score", {})
        full_time = score_raw.get("fullTime", {}) or {}
        half_time = score_raw.get("halfTime", {}) or {}

        score: dict[str, Any] = {
            "full_time": {},
            "half_time": {},
        }
        if full_time.get("home") is not None:
            score["full_time"]["home"] = full_time["home"]
        if full_time.get("away") is not None:
            score["full_time"]["away"] = full_time["away"]
        if half_time.get("home") is not None:
            score["half_time"]["home"] = half_time["home"]
        if half_time.get("away") is not None:
            score["half_time"]["away"] = half_time["away"]

        home = data.get("homeTeam", {}) or {}
        away = data.get("awayTeam", {}) or {}

        competition_raw = data.get("competition", {}) or {}
        competition = self._transform_competition(competition_raw) if competition_raw else {}

        referees = []
        for ref in data.get("referees", []):
            referees.append({
                "name": ref.get("name", ""),
                "type": ref.get("type", ""),
                "nationality": ref.get("nationality", ""),
            })

        return {
            "id": data.get("id", 0),
            "competition": competition,
            "home_team": {
                "id": home.get("id", 0),
                "name": home.get("name", ""),
                "short_name": home.get("shortName", ""),
                "tla": home.get("tla", ""),
                "crest": home.get("crest", ""),
            },
            "away_team": {
                "id": away.get("id", 0),
                "name": away.get("name", ""),
                "short_name": away.get("shortName", ""),
                "tla": away.get("tla", ""),
                "crest": away.get("crest", ""),
            },
            "score": score,
            "status": data.get("status", ""),
            "matchday": data.get("matchday", 0),
            "utc_date": data.get("utcDate", ""),
            "referees": referees,
        }

    def _transform_team(self, data: dict[str, Any]) -> dict[str, Any]:
        coach_raw = data.get("coach", {}) or {}
        coach = {
            "id": coach_raw.get("id", 0),
            "name": coach_raw.get("name", ""),
            "nationality": coach_raw.get("nationality", ""),
        }
        squad = []
        for p in data.get("squad", []):
            squad.append({
                "id": p.get("id", 0),
                "name": p.get("name", ""),
                "nationality": p.get("nationality", ""),
                "position": p.get("position", ""),
            })
        return {
            "id": data.get("id", 0),
            "name": data.get("name", ""),
            "short_name": data.get("shortName", ""),
            "tla": data.get("tla", ""),
            "crest": data.get("crest", ""),
            "venue": data.get("venue", ""),
            "coach": coach,
            "squad": squad,
        }

    def _transform_scorer(self, data: dict[str, Any]) -> dict[str, Any]:
        player_raw = data.get("player", {}) or {}
        team_raw = data.get("team", {}) or {}
        return {
            "player": {
                "id": player_raw.get("id", 0),
                "name": player_raw.get("name", ""),
                "nationality": player_raw.get("nationality", ""),
                "position": player_raw.get("position", ""),
            },
            "team": {
                "id": team_raw.get("id", 0),
                "name": team_raw.get("name", ""),
                "short_name": team_raw.get("shortName", ""),
                "tla": team_raw.get("tla", ""),
                "crest": team_raw.get("crest", ""),
            },
            "goals": data.get("goals", 0),
            "assists": data.get("assists", 0),
            "penalties": data.get("penalties", 0),
        }

    # -------------------------
    # Generic helpers
    # -------------------------

    def _parse_message(self, payload: dict[str, Any], message_cls: type):
        message = message_cls()
        json_format.ParseDict(payload, message, ignore_unknown_fields=True)
        return message

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
