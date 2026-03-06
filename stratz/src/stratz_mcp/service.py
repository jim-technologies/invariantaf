"""StratzService — GraphQL wrapper for STRATZ Dota 2 data."""

from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx
from google.protobuf import json_format, struct_pb2

_DEFAULT_BASE_URL = "https://api.stratz.com/graphql"

_QUERY_MATCH_SUMMARY = """
query GetMatchSummary($matchId: Long!) {
  match(id: $matchId) {
    id
    sequenceNum
    startDateTime
    durationSeconds
    didRadiantWin
  }
}
""".strip()

_QUERY_MATCH_PLAYERS = """
query GetMatchPlayers($matchId: Long!) {
  match(id: $matchId) {
    id
    players {
      steamAccountId
      heroId
      isRadiant
      lane
      role
      kills
      deaths
      assists
      networthPerMinute
    }
  }
}
""".strip()

_QUERY_MATCH_LANE_OUTCOMES = """
query GetMatchLaneOutcomes($matchId: Long!) {
  match(id: $matchId) {
    id
    players {
      steamAccountId
      isRadiant
      lane
      role
      networthPerMinute
      kills
      deaths
      assists
    }
  }
}
""".strip()

_QUERY_MATCH_DOTAPLUS_LEVELS = """
query GetMatchDotaPlusLevels($matchId: Long!) {
  match(id: $matchId) {
    id
    firstBloodTime
    players {
      steamAccountId
      heroId
      dotaPlus {
        level
      }
    }
  }
}
""".strip()

_QUERY_PLAYER_RECENT_MATCHES = """
query GetPlayerRecentMatches($steamAccountId: Long!, $take: Int!, $before: Long) {
  player(steamAccountId: $steamAccountId) {
    steamAccount {
      id
      name
      avatar
    }
    matches(request: { take: $take, before: $before }) {
      id
      didRadiantWin
      durationSeconds
      startDateTime
      players(steamAccountId: $steamAccountId) {
        isVictory
        kills
        deaths
        assists
        hero {
          displayName
          shortName
        }
      }
    }
  }
}
""".strip()

_QUERY_CONSTANTS_HEROES = """
query GetConstantsHeroes {
  constants {
    heroes {
      id
      name
      displayName
      shortName
    }
  }
}
""".strip()

_QUERY_CONSTANTS_ITEMS = """
query GetConstantsItems {
  constants {
    items {
      id
      name
    }
  }
}
""".strip()

_QUERY_CONSTANTS_ABILITIES = """
query GetConstantsAbilities {
  constants {
    abilities {
      id
      name
    }
  }
}
""".strip()

_HERO_NEUTRAL_ITEMS_TEMPLATE = """
query GetHeroNeutralItemStats($heroId: Short!, $week: Long!) {
  heroStats {
    itemNeutral(heroId: $heroId, week: $week, bracketBasicIds: [%(brackets)s]) {
      itemId
      equippedMatchCount
      item {
        name
        stat {
          neutralItemTier
        }
      }
    }
  }
}
""".strip()


class StratzService:
    """Implements StratzService RPCs via STRATZ GraphQL."""

    def __init__(self, *, api_key: str | None = None, base_url: str | None = None):
        self._http = httpx.Client(timeout=45)
        self._api_key = api_key or os.environ.get("STRATZ_API_KEY", "")
        self._base_url = (base_url or os.environ.get("STRATZ_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "STRATZ_API",
            # Matches STRATZ GraphiQL clients and avoids some intermediary rejections.
            "graphql-require-preflight": "1",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _graphql(
        self,
        query: str,
        *,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> struct_pb2.Struct:
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        resp = self._http.post(self._base_url, json=payload, headers=self._headers())
        resp.raise_for_status()

        body = resp.json()
        errors = body.get("errors") if isinstance(body, dict) else None
        if errors:
            messages: list[str] = []
            for err in errors:
                if isinstance(err, dict):
                    messages.append(str(err.get("message", "GraphQL error")))
                else:
                    messages.append(str(err))
            raise RuntimeError("; ".join(messages))

        data = body.get("data") if isinstance(body, dict) else {}
        if not isinstance(data, dict):
            data = {}
        return _to_struct(data)

    def ExecuteRawQuery(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        variables = {}
        if request.HasField("variables"):
            variables = json_format.MessageToDict(request.variables)
        return self._graphql(
            request.query,
            variables=variables,
            operation_name=request.operation_name or None,
        )

    def GetMatchSummary(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_MATCH_SUMMARY,
            variables={"matchId": request.match_id},
            operation_name="GetMatchSummary",
        )

    def GetMatchPlayers(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_MATCH_PLAYERS,
            variables={"matchId": request.match_id},
            operation_name="GetMatchPlayers",
        )

    def GetMatchLaneOutcomes(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_MATCH_LANE_OUTCOMES,
            variables={"matchId": request.match_id},
            operation_name="GetMatchLaneOutcomes",
        )

    def GetMatchDotaPlusLevels(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_MATCH_DOTAPLUS_LEVELS,
            variables={"matchId": request.match_id},
            operation_name="GetMatchDotaPlusLevels",
        )

    def GetPlayerRecentMatches(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        variables: dict[str, Any] = {
            "steamAccountId": request.steam_account_id,
            "take": request.take or 10,
            "before": request.before_match_id or None,
        }
        return self._graphql(
            _QUERY_PLAYER_RECENT_MATCHES,
            variables=variables,
            operation_name="GetPlayerRecentMatches",
        )

    def GetConstantsHeroes(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_CONSTANTS_HEROES,
            operation_name="GetConstantsHeroes",
        )

    def GetConstantsItems(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_CONSTANTS_ITEMS,
            operation_name="GetConstantsItems",
        )

    def GetConstantsAbilities(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        return self._graphql(
            _QUERY_CONSTANTS_ABILITIES,
            operation_name="GetConstantsAbilities",
        )

    def GetHeroNeutralItemStats(self, request: Any, context: Any = None) -> struct_pb2.Struct:
        # Enum literals must be injected into the query string (GraphQL enum values are not quoted).
        raw_brackets = list(request.bracket_basic_ids) or ["DIVINE_IMMORTAL"]
        brackets: list[str] = []
        for bracket in raw_brackets:
            if not re.fullmatch(r"[A-Z0-9_]+", bracket):
                raise ValueError(f"Invalid bracket enum literal: {bracket!r}")
            brackets.append(bracket)

        query = _HERO_NEUTRAL_ITEMS_TEMPLATE % {"brackets": ", ".join(brackets)}
        week = request.week_unix or int(time.time()) - (7 * 24 * 60 * 60)

        return self._graphql(
            query,
            variables={"heroId": request.hero_id, "week": week},
            operation_name="GetHeroNeutralItemStats",
        )


def _to_struct(value: dict[str, Any]) -> struct_pb2.Struct:
    struct_value = struct_pb2.Struct()
    struct_value.update(value)
    return struct_value
