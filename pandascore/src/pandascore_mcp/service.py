"""PandaScore esports data service implementation for Invariant Protocol."""

from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx
from google.protobuf import json_format

from pandascore_mcp.gen.pandascore.v1 import pandascore_pb2 as pb

DEFAULT_BASE_URL = "https://api.pandascore.co"


def _safe_str(value: Any) -> str:
    """Convert a value to a string safe for protobuf (replaces None with empty string)."""
    if value is None:
        return ""
    return str(value)


def _safe_int(value: Any) -> int:
    """Convert a value to int safe for protobuf (replaces None with 0)."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _clean_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively replace None values with protobuf-compatible defaults."""
    cleaned: dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        elif isinstance(v, dict):
            cleaned[k] = _clean_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [_clean_dict(i) if isinstance(i, dict) else i for i in v if i is not None]
        else:
            cleaned[k] = v
    return cleaned


class PandaScoreService:
    """Implements PandaScoreService -- esports data endpoints."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.getenv("PANDASCORE_API_KEY", "")
        self._timeout = timeout
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._client = httpx.Client(timeout=timeout, headers=headers)

    # -------------------------
    # RPC handlers
    # -------------------------

    def ListMatches(
        self, request: pb.ListMatchesRequest, context: Any = None
    ) -> pb.ListMatchesResponse:
        query = self._pagination_params(request, per_page_default=50)
        query["sort"] = "-scheduled_at"
        data = self._get("/dota2/matches", query)
        matches = self._transform_matches(data)
        return self._parse_message({"matches": matches}, pb.ListMatchesResponse)

    def ListUpcomingMatches(
        self, request: pb.ListUpcomingMatchesRequest, context: Any = None
    ) -> pb.ListUpcomingMatchesResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/matches/upcoming", query)
        matches = self._transform_matches(data)
        return self._parse_message({"matches": matches}, pb.ListUpcomingMatchesResponse)

    def ListRunningMatches(
        self, request: pb.ListRunningMatchesRequest, context: Any = None
    ) -> pb.ListRunningMatchesResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/matches/running", query)
        matches = self._transform_matches(data)
        return self._parse_message({"matches": matches}, pb.ListRunningMatchesResponse)

    def ListPastMatches(
        self, request: pb.ListPastMatchesRequest, context: Any = None
    ) -> pb.ListPastMatchesResponse:
        query = self._pagination_params(request, per_page_default=50)
        query["sort"] = "-scheduled_at"
        data = self._get("/dota2/matches/past", query)
        matches = self._transform_matches(data)
        return self._parse_message({"matches": matches}, pb.ListPastMatchesResponse)

    def ListTournaments(
        self, request: pb.ListTournamentsRequest, context: Any = None
    ) -> pb.ListTournamentsResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/tournaments", query)
        tournaments = self._transform_tournaments(data)
        return self._parse_message({"tournaments": tournaments}, pb.ListTournamentsResponse)

    def ListTeams(
        self, request: pb.ListTeamsRequest, context: Any = None
    ) -> pb.ListTeamsResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/teams", query)
        teams = self._transform_teams(data)
        return self._parse_message({"teams": teams}, pb.ListTeamsResponse)

    def ListPlayers(
        self, request: pb.ListPlayersRequest, context: Any = None
    ) -> pb.ListPlayersResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/players", query)
        players = self._transform_players(data)
        return self._parse_message({"players": players}, pb.ListPlayersResponse)

    def ListLeagues(
        self, request: pb.ListLeaguesRequest, context: Any = None
    ) -> pb.ListLeaguesResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/leagues", query)
        leagues = self._transform_leagues(data)
        return self._parse_message({"leagues": leagues}, pb.ListLeaguesResponse)

    def ListSeries(
        self, request: pb.ListSeriesRequest, context: Any = None
    ) -> pb.ListSeriesResponse:
        query = self._pagination_params(request, per_page_default=50)
        data = self._get("/dota2/series/upcoming", query)
        series = self._transform_series(data)
        return self._parse_message({"series": series}, pb.ListSeriesResponse)

    def ListHeroes(
        self, request: pb.ListHeroesRequest, context: Any = None
    ) -> pb.ListHeroesResponse:
        query = self._pagination_params(request, per_page_default=100)
        data = self._get("/dota2/heroes", query)
        heroes = self._transform_heroes(data)
        return self._parse_message({"heroes": heroes}, pb.ListHeroesResponse)

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path, query)
        response = self._client.request("GET", url)

        try:
            payload = response.json() if response.content else []
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

    def _pagination_params(
        self, request: Any, per_page_default: int = 50
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if self._has_field(request, "page"):
            query["page"] = request.page
        if self._has_field(request, "per_page"):
            query["per_page"] = request.per_page
        else:
            query["per_page"] = per_page_default
        return query

    # -------------------------
    # Response transforms
    # -------------------------

    def _transform_matches(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        matches = []
        for item in data:
            match = {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "scheduled_at": _safe_str(item.get("scheduled_at")),
                "status": _safe_str(item.get("status")),
                "number_of_games": _safe_int(item.get("number_of_games")),
                "begin_at": _safe_str(item.get("begin_at")),
                "end_at": _safe_str(item.get("end_at")),
                "match_type": _safe_str(item.get("match_type")),
                "slug": _safe_str(item.get("slug")),
            }
            # Tournament
            tournament = item.get("tournament")
            if isinstance(tournament, dict):
                match["tournament"] = {
                    "id": _safe_int(tournament.get("id")),
                    "name": _safe_str(tournament.get("name")),
                    "slug": _safe_str(tournament.get("slug")),
                }
            # League
            league = item.get("league")
            if isinstance(league, dict):
                match["league"] = {
                    "id": _safe_int(league.get("id")),
                    "name": _safe_str(league.get("name")),
                    "slug": _safe_str(league.get("slug")),
                    "image_url": _safe_str(league.get("image_url")),
                }
            # Serie
            serie = item.get("serie")
            if isinstance(serie, dict):
                match["serie"] = {
                    "id": _safe_int(serie.get("id")),
                    "name": _safe_str(serie.get("name")),
                    "slug": _safe_str(serie.get("slug")),
                    "full_name": _safe_str(serie.get("full_name")),
                }
            # Opponents
            opponents_raw = item.get("opponents")
            if isinstance(opponents_raw, list):
                opponents = []
                for opp in opponents_raw:
                    if isinstance(opp, dict):
                        opp_inner = opp.get("opponent")
                        if isinstance(opp_inner, dict):
                            opponents.append({
                                "type": _safe_str(opp.get("type")),
                                "opponent": {
                                    "id": _safe_int(opp_inner.get("id")),
                                    "name": _safe_str(opp_inner.get("name")),
                                    "slug": _safe_str(opp_inner.get("slug")),
                                    "acronym": _safe_str(opp_inner.get("acronym")),
                                    "image_url": _safe_str(opp_inner.get("image_url")),
                                },
                            })
                match["opponents"] = opponents
            # Winner
            winner = item.get("winner")
            if isinstance(winner, dict):
                match["winner"] = {
                    "id": _safe_int(winner.get("id")),
                    "name": _safe_str(winner.get("name")),
                    "slug": _safe_str(winner.get("slug")),
                    "acronym": _safe_str(winner.get("acronym")),
                    "image_url": _safe_str(winner.get("image_url")),
                }
            # Results
            results_raw = item.get("results")
            if isinstance(results_raw, list):
                results = []
                for r in results_raw:
                    if isinstance(r, dict):
                        results.append({
                            "team_id": _safe_int(r.get("team_id")),
                            "score": _safe_int(r.get("score")),
                        })
                match["results"] = results
            # Games
            games_raw = item.get("games")
            if isinstance(games_raw, list):
                games = []
                for g in games_raw:
                    if isinstance(g, dict):
                        game_entry: dict[str, Any] = {
                            "id": _safe_int(g.get("id")),
                            "position": _safe_int(g.get("position")),
                            "status": _safe_str(g.get("status")),
                            "forfeit": bool(g.get("forfeit", False)),
                            "length": _safe_int(g.get("length")),
                            "begin_at": _safe_str(g.get("begin_at")),
                            "end_at": _safe_str(g.get("end_at")),
                        }
                        game_winner = g.get("winner")
                        if isinstance(game_winner, dict):
                            game_entry["winner"] = {
                                "id": _safe_int(game_winner.get("id")),
                                "name": _safe_str(game_winner.get("name")),
                                "slug": _safe_str(game_winner.get("slug")),
                                "acronym": _safe_str(game_winner.get("acronym")),
                                "image_url": _safe_str(game_winner.get("image_url")),
                            }
                        games.append(game_entry)
                match["games"] = games
            matches.append(match)
        return matches

    def _transform_tournaments(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        tournaments = []
        for item in data:
            t: dict[str, Any] = {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "slug": _safe_str(item.get("slug")),
                "begin_at": _safe_str(item.get("begin_at")),
                "end_at": _safe_str(item.get("end_at")),
                "tier": _safe_str(item.get("tier")),
                "prizepool": _safe_int(item.get("prizepool")),
            }
            league = item.get("league")
            if isinstance(league, dict):
                t["league"] = {
                    "id": _safe_int(league.get("id")),
                    "name": _safe_str(league.get("name")),
                    "slug": _safe_str(league.get("slug")),
                    "image_url": _safe_str(league.get("image_url")),
                }
            serie = item.get("serie")
            if isinstance(serie, dict):
                t["serie"] = {
                    "id": _safe_int(serie.get("id")),
                    "name": _safe_str(serie.get("name")),
                    "slug": _safe_str(serie.get("slug")),
                    "full_name": _safe_str(serie.get("full_name")),
                }
            tournaments.append(t)
        return tournaments

    def _transform_teams(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        teams = []
        for item in data:
            team: dict[str, Any] = {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "slug": _safe_str(item.get("slug")),
                "acronym": _safe_str(item.get("acronym")),
                "image_url": _safe_str(item.get("image_url")),
                "location": _safe_str(item.get("location")),
            }
            players_raw = item.get("players")
            if isinstance(players_raw, list):
                players = []
                for p in players_raw:
                    if isinstance(p, dict):
                        players.append({
                            "id": _safe_int(p.get("id")),
                            "name": _safe_str(p.get("name")),
                            "slug": _safe_str(p.get("slug")),
                            "first_name": _safe_str(p.get("first_name")),
                            "last_name": _safe_str(p.get("last_name")),
                            "role": _safe_str(p.get("role")),
                            "image_url": _safe_str(p.get("image_url")),
                        })
                team["players"] = players
            teams.append(team)
        return teams

    def _transform_players(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        players = []
        for item in data:
            player: dict[str, Any] = {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "slug": _safe_str(item.get("slug")),
                "first_name": _safe_str(item.get("first_name")),
                "last_name": _safe_str(item.get("last_name")),
                "role": _safe_str(item.get("role")),
                "image_url": _safe_str(item.get("image_url")),
            }
            current_team = item.get("current_team")
            if isinstance(current_team, dict):
                player["current_team"] = {
                    "id": _safe_int(current_team.get("id")),
                    "name": _safe_str(current_team.get("name")),
                    "slug": _safe_str(current_team.get("slug")),
                    "acronym": _safe_str(current_team.get("acronym")),
                    "image_url": _safe_str(current_team.get("image_url")),
                }
            players.append(player)
        return players

    def _transform_leagues(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        return [
            {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "slug": _safe_str(item.get("slug")),
                "image_url": _safe_str(item.get("image_url")),
                "url": _safe_str(item.get("url")),
            }
            for item in data
            if isinstance(item, dict)
        ]

    def _transform_series(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        series = []
        for item in data:
            s: dict[str, Any] = {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "slug": _safe_str(item.get("slug")),
                "begin_at": _safe_str(item.get("begin_at")),
                "end_at": _safe_str(item.get("end_at")),
                "full_name": _safe_str(item.get("full_name")),
                "tier": _safe_str(item.get("tier")),
                "year": _safe_int(item.get("year")),
            }
            league = item.get("league")
            if isinstance(league, dict):
                s["league"] = {
                    "id": _safe_int(league.get("id")),
                    "name": _safe_str(league.get("name")),
                    "slug": _safe_str(league.get("slug")),
                    "image_url": _safe_str(league.get("image_url")),
                }
            series.append(s)
        return series

    def _transform_heroes(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            return []
        return [
            {
                "id": _safe_int(item.get("id")),
                "name": _safe_str(item.get("name")),
                "localized_name": _safe_str(item.get("localized_name")),
            }
            for item in data
            if isinstance(item, dict)
        ]

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
