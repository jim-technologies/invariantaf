"""BallDontLie NBA sports data service implementation for Invariant Protocol."""

from __future__ import annotations

from typing import Any

import httpx
from google.protobuf import json_format

from balldontlie_mcp.gen.balldontlie.v1 import balldontlie_pb2 as pb

DEFAULT_BASE_URL = "https://api.balldontlie.io/v1"


class BallDontLieService:
    """Implements BallDontLieService -- NBA sports data endpoints."""

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

    def ListNBAPlayers(
        self, request: pb.ListNBAPlayersRequest, context: Any = None
    ) -> pb.ListNBAPlayersResponse:
        params: list[tuple[str, str]] = []
        if self._has_field(request, "search") and request.search:
            params.append(("search", request.search))
        if self._has_field(request, "per_page"):
            params.append(("per_page", str(request.per_page)))
        if self._has_field(request, "cursor"):
            params.append(("cursor", str(request.cursor)))

        payload = self._get("/nba/players", params)
        return self._parse_response(payload, pb.ListNBAPlayersResponse)

    def GetNBAPlayer(
        self, request: pb.GetNBAPlayerRequest, context: Any = None
    ) -> pb.GetNBAPlayerResponse:
        payload = self._get(f"/nba/players/{request.id}")
        return self._parse_response({"data": payload.get("data", payload)}, pb.GetNBAPlayerResponse)

    def ListNBATeams(
        self, request: pb.ListNBATeamsRequest, context: Any = None
    ) -> pb.ListNBATeamsResponse:
        payload = self._get("/nba/teams")
        return self._parse_response(payload, pb.ListNBATeamsResponse)

    def ListNBAGames(
        self, request: pb.ListNBAGamesRequest, context: Any = None
    ) -> pb.ListNBAGamesResponse:
        params: list[tuple[str, str]] = []
        for d in request.dates:
            params.append(("dates[]", d))
        for s in request.seasons:
            params.append(("seasons[]", str(s)))
        for tid in request.team_ids:
            params.append(("team_ids[]", str(tid)))
        if self._has_field(request, "per_page"):
            params.append(("per_page", str(request.per_page)))
        if self._has_field(request, "cursor"):
            params.append(("cursor", str(request.cursor)))

        payload = self._get("/nba/games", params)
        return self._parse_response(payload, pb.ListNBAGamesResponse)

    def GetNBAGame(
        self, request: pb.GetNBAGameRequest, context: Any = None
    ) -> pb.GetNBAGameResponse:
        payload = self._get(f"/nba/games/{request.id}")
        return self._parse_response({"data": payload.get("data", payload)}, pb.GetNBAGameResponse)

    def GetNBAStats(
        self, request: pb.GetNBAStatsRequest, context: Any = None
    ) -> pb.GetNBAStatsResponse:
        params: list[tuple[str, str]] = []
        for gid in request.game_ids:
            params.append(("game_ids[]", str(gid)))
        for pid in request.player_ids:
            params.append(("player_ids[]", str(pid)))
        if self._has_field(request, "per_page"):
            params.append(("per_page", str(request.per_page)))
        if self._has_field(request, "cursor"):
            params.append(("cursor", str(request.cursor)))

        payload = self._get("/nba/stats", params)
        return self._parse_response(payload, pb.GetNBAStatsResponse)

    def GetNBASeasonAverages(
        self, request: pb.GetNBASeasonAveragesRequest, context: Any = None
    ) -> pb.GetNBASeasonAveragesResponse:
        params: list[tuple[str, str]] = []
        if self._has_field(request, "season"):
            params.append(("season", str(request.season)))
        for pid in request.player_ids:
            params.append(("player_ids[]", str(pid)))

        payload = self._get("/nba/season_averages", params)
        return self._parse_response(payload, pb.GetNBASeasonAveragesResponse)

    def ListNBAStandings(
        self, request: pb.ListNBAStandingsRequest, context: Any = None
    ) -> pb.ListNBAStandingsResponse:
        params: list[tuple[str, str]] = []
        if self._has_field(request, "season"):
            params.append(("season", str(request.season)))

        payload = self._get("/nba/standings", params)
        return self._parse_response(payload, pb.ListNBAStandingsResponse)

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str, params: list[tuple[str, str]] | None = None) -> Any:
        url = self._build_url(path, params)
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = self._api_key

        response = self._client.request("GET", url, headers=headers)

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    def _build_url(self, path: str, params: list[tuple[str, str]] | None = None) -> str:
        full = f"{self._base_url}{path}"
        if not params:
            return full
        qs = "&".join(f"{k}={v}" for k, v in params)
        return f"{full}?{qs}" if qs else full

    # -------------------------
    # Response parsing
    # -------------------------

    def _parse_response(self, payload: dict[str, Any], message_cls: type):
        """Parse an API response dict into a protobuf message."""
        data = payload.get("data", [])
        meta = payload.get("meta", {})

        # Normalize meta to match our PaginationMeta proto
        normalized_meta = {}
        if meta:
            if "next_cursor" in meta:
                normalized_meta["next_cursor"] = meta["next_cursor"] or 0
            if "per_page" in meta:
                normalized_meta["per_page"] = meta["per_page"]

        # Build the response dict
        resp: dict[str, Any] = {"data": data}
        if normalized_meta:
            resp["meta"] = normalized_meta

        message = message_cls()
        json_format.ParseDict(resp, message, ignore_unknown_fields=True)
        return message

    # -------------------------
    # Generic helpers
    # -------------------------

    def _has_field(self, message: Any, field_name: str) -> bool:
        try:
            return bool(message.HasField(field_name))
        except ValueError:
            return False
