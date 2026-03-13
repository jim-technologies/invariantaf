"""NHL public API service implementation for Invariant Protocol."""

from __future__ import annotations

from typing import Any

import httpx
from google.protobuf import json_format

from nhl_mcp.gen.nhl.v1 import nhl_pb2 as pb

DEFAULT_BASE_URL = "https://api-web.nhle.com"


class NHLService:
    """Implements NHLService -- public NHL API endpoints (no auth required)."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    # -------------------------
    # RPC handlers
    # -------------------------

    def ListTeams(
        self, request: pb.ListTeamsRequest, context: Any = None
    ) -> pb.ListTeamsResponse:
        payload = self._get("/v1/standings/now")
        standings = payload.get("standings", [])
        teams = []
        for entry in standings:
            teams.append({
                "team_abbrev": self._default_str(entry.get("teamAbbrev")),
                "team_name": self._default_str(entry.get("teamName")),
                "conference_name": entry.get("conferenceName", ""),
                "division_name": entry.get("divisionName", ""),
                "team_logo": entry.get("teamLogo", ""),
            })
        # Deduplicate by abbreviation, preserving order
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for t in teams:
            if t["team_abbrev"] not in seen:
                seen.add(t["team_abbrev"])
                unique.append(t)
        return self._parse_message({"teams": unique}, pb.ListTeamsResponse)

    def GetStandings(
        self, request: pb.GetStandingsRequest, context: Any = None
    ) -> pb.GetStandingsResponse:
        payload = self._get("/v1/standings/now")
        standings = payload.get("standings", [])
        entries = []
        for entry in standings:
            entries.append({
                "team_abbrev": self._default_str(entry.get("teamAbbrev")),
                "team_name": self._default_str(entry.get("teamName")),
                "conference_name": entry.get("conferenceName", ""),
                "division_name": entry.get("divisionName", ""),
                "games_played": entry.get("gamesPlayed", 0),
                "wins": entry.get("wins", 0),
                "losses": entry.get("losses", 0),
                "ot_losses": entry.get("otLosses", 0),
                "points": entry.get("points", 0),
                "regulation_wins": entry.get("regulationWins", 0),
                "goal_for": entry.get("goalFor", 0),
                "goal_against": entry.get("goalAgainst", 0),
                "goal_differential": entry.get("goalDifferential", 0),
                "point_pctg": entry.get("pointPctg", 0.0),
                "streak_code": entry.get("streakCode", ""),
                "streak_count": entry.get("streakCount", 0),
                "league_sequence": entry.get("leagueSequence", 0),
                "conference_sequence": entry.get("conferenceSequence", 0),
                "division_sequence": entry.get("divisionSequence", 0),
                "wildcard_sequence": entry.get("wildcardSequence", 0),
                "team_logo": entry.get("teamLogo", ""),
                "win_pctg": entry.get("winPctg", 0.0),
                "home_wins": entry.get("homeWins", 0),
                "home_losses": entry.get("homeLosses", 0),
                "home_ot_losses": entry.get("homeOtLosses", 0),
                "road_wins": entry.get("roadWins", 0),
                "road_losses": entry.get("roadLosses", 0),
                "road_ot_losses": entry.get("roadOtLosses", 0),
                "shootout_wins": entry.get("shootoutWins", 0),
                "shootout_losses": entry.get("shootoutLosses", 0),
                "l10_wins": entry.get("l10Wins", 0),
                "l10_losses": entry.get("l10Losses", 0),
                "l10_ot_losses": entry.get("l10OtLosses", 0),
            })
        return self._parse_message({"standings": entries}, pb.GetStandingsResponse)

    def GetSchedule(
        self, request: pb.GetScheduleRequest, context: Any = None
    ) -> pb.GetScheduleResponse:
        if self._has_field(request, "date") and request.date:
            path = f"/v1/schedule/{request.date}"
        else:
            path = "/v1/schedule/now"

        payload = self._get(path)
        all_games: list[dict[str, Any]] = []
        game_week = payload.get("gameWeek", [])
        for day in game_week:
            for g in day.get("games", []):
                all_games.append(self._transform_schedule_game(g))
        return self._parse_message({"games": all_games}, pb.GetScheduleResponse)

    def GetGameBoxscore(
        self, request: pb.GetGameBoxscoreRequest, context: Any = None
    ) -> pb.GetGameBoxscoreResponse:
        path = f"/v1/gamecenter/{request.game_id}/boxscore"
        payload = self._get(path)
        result = self._transform_boxscore(payload)
        return self._parse_message(result, pb.GetGameBoxscoreResponse)

    def GetPlayerStats(
        self, request: pb.GetPlayerStatsRequest, context: Any = None
    ) -> pb.GetPlayerStatsResponse:
        path = f"/v1/player/{request.player_id}/landing"
        payload = self._get(path)
        result = self._transform_player(payload)
        return self._parse_message(result, pb.GetPlayerStatsResponse)

    def GetTeamSchedule(
        self, request: pb.GetTeamScheduleRequest, context: Any = None
    ) -> pb.GetTeamScheduleResponse:
        path = f"/v1/club-schedule-season/{request.team_abbrev}/now"
        payload = self._get(path)
        games_raw = payload.get("games", [])
        games = [self._transform_team_schedule_game(g) for g in games_raw]
        return self._parse_message({"games": games}, pb.GetTeamScheduleResponse)

    def GetTeamRoster(
        self, request: pb.GetTeamRosterRequest, context: Any = None
    ) -> pb.GetTeamRosterResponse:
        path = f"/v1/roster/{request.team_abbrev}/current"
        payload = self._get(path)
        result = {
            "forwards": [self._transform_roster_player(p) for p in payload.get("forwards", [])],
            "defensemen": [self._transform_roster_player(p) for p in payload.get("defensemen", [])],
            "goalies": [self._transform_roster_player(p) for p in payload.get("goalies", [])],
        }
        return self._parse_message(result, pb.GetTeamRosterResponse)

    def GetScoreboard(
        self, request: pb.GetScoreboardRequest, context: Any = None
    ) -> pb.GetScoreboardResponse:
        payload = self._get("/v1/score/now")
        games_raw = payload.get("games", [])
        games = [self._transform_scoreboard_game(g) for g in games_raw]
        return self._parse_message({"games": games}, pb.GetScoreboardResponse)

    # -------------------------
    # HTTP helpers
    # -------------------------

    def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        response = self._client.request(
            "GET",
            url,
            headers={"Accept": "application/json"},
        )

        try:
            payload = response.json() if response.content else {}
        except Exception as exc:
            raise RuntimeError(f"GET {url}: invalid JSON response: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(f"GET {url}: HTTP {response.status_code}: {payload}")

        return payload

    # -------------------------
    # Response transforms
    # -------------------------

    def _default_str(self, val: Any) -> str:
        """Extract 'default' key from NHL's i18n dict, or return string as-is."""
        if isinstance(val, dict):
            return val.get("default", "")
        if val is None:
            return ""
        return str(val)

    def _transform_schedule_game(self, g: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": g.get("id", 0),
            "season": g.get("season", 0),
            "game_type": g.get("gameType", 0),
            "game_date": g.get("gameDate", ""),
            "venue": self._default_str(g.get("venue")),
            "start_time_utc": g.get("startTimeUTC", ""),
            "game_state": g.get("gameState", ""),
            "away_team": self._transform_schedule_team(g.get("awayTeam", {})),
            "home_team": self._transform_schedule_team(g.get("homeTeam", {})),
        }

    def _transform_schedule_team(self, t: dict[str, Any]) -> dict[str, Any]:
        name = self._default_str(t.get("placeName", ""))
        common = self._default_str(t.get("commonName", ""))
        full_name = f"{name} {common}".strip() if name and common else name or common
        return {
            "id": t.get("id", 0),
            "abbrev": t.get("abbrev", ""),
            "name": full_name,
            "logo": t.get("logo", ""),
            "score": t.get("score", 0),
        }

    def _transform_boxscore(self, data: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": data.get("id", 0),
            "season": data.get("season", 0),
            "game_type": data.get("gameType", 0),
            "game_date": data.get("gameDate", ""),
            "venue": self._default_str(data.get("venue")),
            "start_time_utc": data.get("startTimeUTC", ""),
            "game_state": data.get("gameState", ""),
        }

        player_stats = data.get("playerByGameStats", {})

        for side in ("awayTeam", "homeTeam"):
            team_data = data.get(side, {})
            side_stats = player_stats.get(side, {})
            team_key = "away_team" if side == "awayTeam" else "home_team"
            result[team_key] = self._transform_boxscore_team(team_data, side_stats)

        return result

    def _transform_boxscore_team(
        self, team: dict[str, Any], stats: dict[str, Any]
    ) -> dict[str, Any]:
        name = self._default_str(team.get("placeName", ""))
        common = self._default_str(team.get("commonName", ""))
        full_name = f"{name} {common}".strip() if name and common else name or common
        return {
            "id": team.get("id", 0),
            "abbrev": team.get("abbrev", ""),
            "name": full_name,
            "score": team.get("score", 0),
            "sog": team.get("sog", 0),
            "forwards": [self._transform_skater(p) for p in stats.get("forwards", [])],
            "defense": [self._transform_skater(p) for p in stats.get("defense", [])],
            "goalies": [self._transform_goalie(p) for p in stats.get("goalies", [])],
        }

    def _transform_skater(self, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "player_id": p.get("playerId", 0),
            "name": self._default_str(p.get("name")),
            "position": p.get("position", ""),
            "sweater_number": p.get("sweaterNumber", 0),
            "goals": p.get("goals", 0),
            "assists": p.get("assists", 0),
            "points": p.get("points", 0),
            "plus_minus": p.get("plusMinus", 0),
            "pim": p.get("pim", 0),
            "hits": p.get("hits", 0),
            "shots": p.get("sog", 0),
            "blocked_shots": p.get("blockedShots", 0),
            "toi": p.get("toi", "00:00"),
            "power_play_goals": p.get("powerPlayGoals", 0),
            "faceoff_winning_pctg": p.get("faceoffWinningPctg", 0.0),
            "takeaways": p.get("takeaways", 0),
            "giveaways": p.get("giveaways", 0),
            "shifts": p.get("shifts", 0),
        }

    def _transform_goalie(self, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "player_id": p.get("playerId", 0),
            "name": self._default_str(p.get("name")),
            "sweater_number": p.get("sweaterNumber", 0),
            "toi": p.get("toi", "00:00"),
            "saves": p.get("saves", 0),
            "shots_against": p.get("shotsAgainst", 0),
            "goals_against": p.get("goalsAgainst", 0),
            "save_pctg": p.get("savePctg", 0.0),
            "decision": p.get("decision", ""),
            "starter": p.get("starter", False),
            "even_strength_shots_against": p.get("evenStrengthShotsAgainst", ""),
            "power_play_shots_against": p.get("powerPlayShotsAgainst", ""),
            "shorthanded_shots_against": p.get("shorthandedShotsAgainst", ""),
        }

    def _transform_player(self, data: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "player_id": data.get("playerId", 0),
            "first_name": self._default_str(data.get("firstName")),
            "last_name": self._default_str(data.get("lastName")),
            "position": data.get("position", ""),
            "sweater_number": data.get("sweaterNumber", 0),
            "team_abbrev": self._default_str(data.get("currentTeamAbbrev")),
            "birth_date": data.get("birthDate", ""),
            "birth_city": self._default_str(data.get("birthCity")),
            "birth_country": data.get("birthCountry", ""),
            "shoots_catches": data.get("shootsCatches", ""),
            "height_in_inches": data.get("heightInInches", 0),
            "weight_in_pounds": data.get("weightInPounds", 0),
            "headshot": data.get("headshot", ""),
            "is_active": data.get("isActive", False),
        }

        # Current season stats from featuredStats
        featured = data.get("featuredStats", {})
        season = featured.get("regularSeason", {}).get("subSeason", {})
        if season:
            result["current_season_stats"] = {
                "goals": season.get("goals", 0),
                "assists": season.get("assists", 0),
                "points": season.get("points", 0),
                "games_played": season.get("gamesPlayed", 0),
                "plus_minus": season.get("plusMinus", 0),
                "power_play_goals": season.get("powerPlayGoals", 0),
                "power_play_points": season.get("powerPlayPoints", 0),
                "shots": season.get("shots", 0),
                "shooting_pctg": season.get("shootingPctg", 0.0),
            }

        # Career totals
        career = data.get("careerTotals", {}).get("regularSeason", {})
        if career:
            result["career_totals"] = {
                "goals": career.get("goals", 0),
                "assists": career.get("assists", 0),
                "points": career.get("points", 0),
                "games_played": career.get("gamesPlayed", 0),
                "plus_minus": career.get("plusMinus", 0),
                "power_play_goals": career.get("powerPlayGoals", 0),
                "power_play_points": career.get("powerPlayPoints", 0),
                "shots": career.get("shots", 0),
                "pim": career.get("pim", 0),
                "game_winning_goals": career.get("gameWinningGoals", 0),
                "ot_goals": career.get("otGoals", 0),
            }

        return result

    def _transform_team_schedule_game(self, g: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": g.get("id", 0),
            "season": g.get("season", 0),
            "game_type": g.get("gameType", 0),
            "game_date": g.get("gameDate", ""),
            "venue": self._default_str(g.get("venue")),
            "start_time_utc": g.get("startTimeUTC", ""),
            "game_state": g.get("gameState", ""),
            "away_team": self._transform_schedule_team(g.get("awayTeam", {})),
            "home_team": self._transform_schedule_team(g.get("homeTeam", {})),
        }

    def _transform_roster_player(self, p: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": p.get("id", 0),
            "first_name": self._default_str(p.get("firstName")),
            "last_name": self._default_str(p.get("lastName")),
            "sweater_number": p.get("sweaterNumber", 0),
            "position_code": p.get("positionCode", ""),
            "shoots_catches": p.get("shootsCatches", ""),
            "height_in_inches": p.get("heightInInches", 0),
            "weight_in_pounds": p.get("weightInPounds", 0),
            "birth_date": p.get("birthDate", ""),
            "birth_city": self._default_str(p.get("birthCity")),
            "birth_country": p.get("birthCountry", ""),
            "headshot": p.get("headshot", ""),
        }

    def _transform_scoreboard_game(self, g: dict[str, Any]) -> dict[str, Any]:
        clock = g.get("clock", {})
        period_desc = g.get("periodDescriptor", {})
        return {
            "id": g.get("id", 0),
            "game_date": g.get("gameDate", ""),
            "start_time_utc": g.get("startTimeUTC", ""),
            "game_state": g.get("gameState", ""),
            "venue": self._default_str(g.get("venue")),
            "away_team": self._transform_schedule_team(g.get("awayTeam", {})),
            "home_team": self._transform_schedule_team(g.get("homeTeam", {})),
            "period": period_desc.get("number", 0),
            "clock": clock.get("timeRemaining", "") if isinstance(clock, dict) else "",
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
