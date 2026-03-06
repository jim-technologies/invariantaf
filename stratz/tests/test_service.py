"""Unit tests — every StratzService RPC method, mocked HTTP."""

from __future__ import annotations

from google.protobuf import json_format

from stratz_mcp.gen.stratz.v1 import stratz_pb2 as pb



def _data(resp) -> dict:
    return json_format.MessageToDict(resp)


class TestExecuteRawQuery:
    def test_runs_custom_query(self, service):
        req = pb.ExecuteRawQueryRequest(query="query X { constants { heroes { id } } }")
        resp = service.ExecuteRawQuery(req)
        data = _data(resp)
        assert "constants" in data
        assert "heroes" in data["constants"]

    def test_passes_operation_name(self, service, mock_http):
        req = pb.ExecuteRawQueryRequest(
            query="query CustomOp { constants { heroes { id } } }",
            operation_name="CustomOp",
        )
        service.ExecuteRawQuery(req)
        call_args = mock_http.post.call_args
        assert call_args.kwargs["json"]["operationName"] == "CustomOp"

    def test_sends_auth_and_graphql_headers(self, service, mock_http):
        service.GetConstantsHeroes(pb.GetConstantsRequest())
        call_args = mock_http.post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["graphql-require-preflight"] == "1"
        assert headers["User-Agent"] == "STRATZ_API"


class TestMatchQueries:
    def test_match_summary(self, service):
        resp = service.GetMatchSummary(pb.GetMatchRequest(match_id=8597260572))
        match = _data(resp)["match"]
        assert int(match["id"]) == 8597260572
        assert match["didRadiantWin"] is True

    def test_match_players(self, service):
        resp = service.GetMatchPlayers(pb.GetMatchRequest(match_id=8597260572))
        players = _data(resp)["match"]["players"]
        assert len(players) == 2
        assert players[0]["heroId"] == 1

    def test_lane_outcomes(self, service):
        resp = service.GetMatchLaneOutcomes(pb.GetMatchRequest(match_id=8597260572))
        players = _data(resp)["match"]["players"]
        assert players[0]["lane"] == "SAFE_LANE"

    def test_dota_plus_levels(self, service):
        resp = service.GetMatchDotaPlusLevels(pb.GetMatchRequest(match_id=8597260572))
        players = _data(resp)["match"]["players"]
        assert players[0]["dotaPlus"]["level"] == 30


class TestPlayerQueries:
    def test_player_recent_matches(self, service):
        req = pb.GetPlayerRecentMatchesRequest(steam_account_id=123456789, take=2)
        resp = service.GetPlayerRecentMatches(req)
        player = _data(resp)["player"]
        assert player["steamAccount"]["name"] == "test-player"
        assert len(player["matches"]) == 2

    def test_player_recent_matches_passes_take(self, service, mock_http):
        req = pb.GetPlayerRecentMatchesRequest(steam_account_id=123456789, take=5)
        service.GetPlayerRecentMatches(req)
        call_args = mock_http.post.call_args
        assert call_args.kwargs["json"]["variables"]["take"] == 5


class TestConstantsQueries:
    def test_constants_heroes(self, service):
        resp = service.GetConstantsHeroes(pb.GetConstantsRequest())
        heroes = _data(resp)["constants"]["heroes"]
        assert len(heroes) == 2
        assert heroes[1]["displayName"] == "Invoker"

    def test_constants_items(self, service):
        resp = service.GetConstantsItems(pb.GetConstantsRequest())
        items = _data(resp)["constants"]["items"]
        assert items[0]["name"] == "item_blink"

    def test_constants_abilities(self, service):
        resp = service.GetConstantsAbilities(pb.GetConstantsRequest())
        abilities = _data(resp)["constants"]["abilities"]
        assert abilities[0]["id"] == 5001


class TestHeroStatsQueries:
    def test_hero_neutral_item_stats(self, service):
        req = pb.GetHeroNeutralItemStatsRequest(hero_id=74, week_unix=1739000000)
        resp = service.GetHeroNeutralItemStats(req)
        rows = _data(resp)["heroStats"]["itemNeutral"]
        assert len(rows) == 1
        assert rows[0]["item"]["stat"]["neutralItemTier"] == 3

    def test_hero_neutral_bracket_validation(self, service):
        req = pb.GetHeroNeutralItemStatsRequest(
            hero_id=74,
            week_unix=1739000000,
            bracket_basic_ids=["DIVINE_IMMORTAL", "ANCIENT"],
        )
        resp = service.GetHeroNeutralItemStats(req)
        rows = _data(resp)["heroStats"]["itemNeutral"]
        assert rows[0]["equippedMatchCount"] == 240

    def test_hero_neutral_rejects_invalid_literal(self, service):
        req = pb.GetHeroNeutralItemStatsRequest(
            hero_id=74,
            week_unix=1739000000,
            bracket_basic_ids=["DIVINE_IMMORTAL", "bad-literal"],
        )
        try:
            service.GetHeroNeutralItemStats(req)
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "Invalid bracket enum literal" in str(exc)
