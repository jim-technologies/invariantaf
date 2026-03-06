"""Shared fixtures for STRATZ MCP tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")


FAKE_MATCH_SUMMARY = {
    "data": {
        "match": {
            "id": 8597260572,
            "sequenceNum": 6012345678,
            "startDateTime": 1739216400,
            "durationSeconds": 2284,
            "didRadiantWin": True,
        }
    }
}

FAKE_MATCH_PLAYERS = {
    "data": {
        "match": {
            "id": 8597260572,
            "players": [
                {
                    "steamAccountId": 111,
                    "heroId": 1,
                    "isRadiant": True,
                    "lane": "SAFE_LANE",
                    "role": "CORE",
                    "kills": 10,
                    "deaths": 2,
                    "assists": 8,
                    "networthPerMinute": 740,
                },
                {
                    "steamAccountId": 222,
                    "heroId": 74,
                    "isRadiant": False,
                    "lane": "MID_LANE",
                    "role": "CORE",
                    "kills": 7,
                    "deaths": 4,
                    "assists": 6,
                    "networthPerMinute": 680,
                },
            ],
        }
    }
}

FAKE_MATCH_DOTAPLUS = {
    "data": {
        "match": {
            "id": 8597260572,
            "firstBloodTime": 94,
            "players": [
                {"steamAccountId": 111, "heroId": 1, "dotaPlus": {"level": 30}},
                {"steamAccountId": 222, "heroId": 74, "dotaPlus": {"level": 28}},
            ],
        }
    }
}

FAKE_PLAYER_RECENT_MATCHES = {
    "data": {
        "player": {
            "steamAccount": {
                "id": 123456789,
                "name": "test-player",
                "avatar": "https://cdn.example/avatar.jpg",
            },
            "matches": [
                {
                    "id": 8597260572,
                    "didRadiantWin": True,
                    "durationSeconds": 2284,
                    "startDateTime": 1739216400,
                    "players": [
                        {
                            "isVictory": True,
                            "kills": 12,
                            "deaths": 3,
                            "assists": 9,
                            "hero": {"displayName": "Invoker", "shortName": "invoker"},
                        }
                    ],
                },
                {
                    "id": 8597211111,
                    "didRadiantWin": False,
                    "durationSeconds": 1980,
                    "startDateTime": 1739202800,
                    "players": [
                        {
                            "isVictory": False,
                            "kills": 4,
                            "deaths": 7,
                            "assists": 10,
                            "hero": {"displayName": "Rubick", "shortName": "rubick"},
                        }
                    ],
                },
            ],
        }
    }
}

FAKE_CONSTANTS_HEROES = {
    "data": {
        "constants": {
            "heroes": [
                {"id": 1, "name": "npc_dota_hero_antimage", "displayName": "Anti-Mage", "shortName": "antimage"},
                {"id": 74, "name": "npc_dota_hero_invoker", "displayName": "Invoker", "shortName": "invoker"},
            ]
        }
    }
}

FAKE_CONSTANTS_ITEMS = {
    "data": {
        "constants": {
            "items": [
                {"id": 1, "name": "item_blink"},
                {"id": 36, "name": "item_magic_wand"},
            ]
        }
    }
}

FAKE_CONSTANTS_ABILITIES = {
    "data": {
        "constants": {
            "abilities": [
                {"id": 5001, "name": "antimage_mana_break"},
                {"id": 5020, "name": "invoker_quas"},
            ]
        }
    }
}

FAKE_HERO_NEUTRAL_ITEMS = {
    "data": {
        "heroStats": {
            "itemNeutral": [
                {
                    "itemId": 289,
                    "equippedMatchCount": 240,
                    "item": {
                        "name": "item_ogre_seal_totem",
                        "stat": {"neutralItemTier": 3},
                    },
                }
            ]
        }
    }
}

FAKE_RAW_QUERY = {
    "data": {
        "constants": {
            "heroes": [{"id": 1, "name": "npc_dota_hero_antimage"}]
        }
    }
}


class _MockResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload



def _make_mock_http():
    http = MagicMock()

    def mock_post(url, json=None, headers=None):
        query = (json or {}).get("query", "")
        op_name = (json or {}).get("operationName", "")

        if op_name == "GetMatchSummary" or "query GetMatchSummary" in query:
            return _MockResponse(FAKE_MATCH_SUMMARY)
        if op_name == "GetMatchPlayers" or "query GetMatchPlayers" in query:
            return _MockResponse(FAKE_MATCH_PLAYERS)
        if op_name == "GetMatchLaneOutcomes" or "query GetMatchLaneOutcomes" in query:
            return _MockResponse(FAKE_MATCH_PLAYERS)
        if op_name == "GetMatchDotaPlusLevels" or "query GetMatchDotaPlusLevels" in query:
            return _MockResponse(FAKE_MATCH_DOTAPLUS)
        if op_name == "GetPlayerRecentMatches" or "query GetPlayerRecentMatches" in query:
            return _MockResponse(FAKE_PLAYER_RECENT_MATCHES)
        if op_name == "GetConstantsHeroes" or "query GetConstantsHeroes" in query:
            return _MockResponse(FAKE_CONSTANTS_HEROES)
        if op_name == "GetConstantsItems" or "query GetConstantsItems" in query:
            return _MockResponse(FAKE_CONSTANTS_ITEMS)
        if op_name == "GetConstantsAbilities" or "query GetConstantsAbilities" in query:
            return _MockResponse(FAKE_CONSTANTS_ABILITIES)
        if op_name == "GetHeroNeutralItemStats" or "query GetHeroNeutralItemStats" in query:
            return _MockResponse(FAKE_HERO_NEUTRAL_ITEMS)

        return _MockResponse(FAKE_RAW_QUERY)

    http.post = MagicMock(side_effect=mock_post)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    from stratz_mcp.service import StratzService

    svc = StratzService.__new__(StratzService)
    svc._http = mock_http
    svc._api_key = "test-token"
    svc._base_url = "https://api.stratz.com/graphql"
    return svc


@pytest.fixture
def server(service):
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-stratz", version="0.0.1")
    srv.register(service)
    return srv
