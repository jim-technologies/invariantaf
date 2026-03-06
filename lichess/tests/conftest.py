"""Shared fixtures for Lichess MCP tests."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lichess_mcp.gen.lichess.v1 import lichess_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Lichess API return shapes
# ---------------------------------------------------------------------------

FAKE_USER = {
    "id": "drnykterstein",
    "username": "DrNykterstein",
    "title": "GM",
    "online": True,
    "profile": {
        "bio": "Chess is life.",
        "country": "NO",
    },
    "perfs": {
        "bullet": {"games": 5000, "rating": 3200, "rd": 45, "prog": 10, "prov": False},
        "blitz": {"games": 8000, "rating": 3100, "rd": 50, "prog": -5, "prov": False},
        "rapid": {"games": 2000, "rating": 2900, "rd": 60, "prog": 20, "prov": False},
        "classical": {"games": 500, "rating": 2800, "rd": 80, "prog": 0, "prov": True},
    },
    "count": {"all": 15500, "rated": 14000, "ai": 100, "draw": 2000, "drawH": 1900, "loss": 3000, "lossH": 2900, "win": 10500, "winH": 10400, "bookmark": 50, "playing": 1, "import": 0, "me": 0},
    "playTime": {"total": 5000000, "tv": 100000},
    "createdAt": 1500000000000,
    "url": "https://lichess.org/@/DrNykterstein",
}

FAKE_RATING_HISTORY = [
    {
        "name": "Bullet",
        "points": [
            [2023, 1, 15, 3100],
            [2023, 6, 20, 3150],
            [2024, 1, 10, 3200],
        ],
    },
    {
        "name": "Blitz",
        "points": [
            [2023, 3, 5, 3050],
            [2024, 2, 14, 3100],
        ],
    },
]

FAKE_GAME = {
    "id": "abcd1234",
    "rated": True,
    "variant": "standard",
    "speed": "blitz",
    "perf": "blitz",
    "createdAt": 1700000000000,
    "lastMoveAt": 1700000300000,
    "status": "mate",
    "players": {
        "white": {
            "user": {"name": "DrNykterstein", "id": "drnykterstein"},
            "rating": 3100,
            "ratingDiff": 5,
        },
        "black": {
            "user": {"name": "Firouzja2003", "id": "firouzja2003"},
            "rating": 3000,
            "ratingDiff": -5,
        },
    },
    "moves": "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O",
    "opening": {"eco": "C65", "name": "Ruy Lopez: Berlin Defense"},
    "clock": {"initial": 180, "increment": 0},
    "winner": "white",
}

FAKE_GAMES_NDJSON = "\n".join([
    json.dumps(FAKE_GAME),
    json.dumps({
        "id": "efgh5678",
        "rated": True,
        "variant": "standard",
        "speed": "bullet",
        "perf": "bullet",
        "createdAt": 1700001000000,
        "lastMoveAt": 1700001120000,
        "status": "resign",
        "players": {
            "white": {
                "user": {"name": "Hikaru", "id": "hikaru"},
                "rating": 3150,
                "ratingDiff": -3,
            },
            "black": {
                "user": {"name": "DrNykterstein", "id": "drnykterstein"},
                "rating": 3200,
                "ratingDiff": 3,
            },
        },
        "moves": "d4 Nf6 c4 e6 Nc3 Bb4",
        "opening": {"eco": "E20", "name": "Nimzo-Indian Defense"},
        "clock": {"initial": 60, "increment": 0},
        "winner": "black",
    }),
])

FAKE_DAILY_PUZZLE = {
    "game": {
        "id": "Xg7a1B2c",
        "pgn": "e4 e5 Nf3 Nc6 Bb5",
    },
    "puzzle": {
        "id": "K69di",
        "rating": 1850,
        "plays": 125000,
        "initialPly": 42,
        "solution": ["e2e4", "d7d5", "e4d5"],
        "themes": ["fork", "middlegame", "short"],
    },
}

FAKE_PUZZLE = {
    "game": {
        "id": "Yh8b2C3d",
        "pgn": "d4 d5 c4 e6",
    },
    "puzzle": {
        "id": "A1b2C",
        "rating": 2200,
        "plays": 50000,
        "initialPly": 30,
        "solution": ["f3g5", "h7h6", "g5f7"],
        "themes": ["sacrifice", "mateIn3", "endgame"],
    },
}

FAKE_LEADERBOARD = {
    "users": [
        {
            "username": "DrNykterstein",
            "title": "GM",
            "online": True,
            "perfs": {"bullet": {"rating": 3200, "games": 5000, "prog": 10}},
        },
        {
            "username": "Firouzja2003",
            "title": "GM",
            "online": False,
            "perfs": {"bullet": {"rating": 3150, "games": 4000, "prog": -3}},
        },
        {
            "username": "Hikaru",
            "title": "GM",
            "online": True,
            "perfs": {"bullet": {"rating": 3100, "games": 10000, "prog": 5}},
        },
    ],
}

FAKE_CLOUD_EVAL = {
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "knodes": 25000,
    "depth": 40,
    "pvs": [
        {"moves": "e7e5 g1f3 b8c6", "cp": 20, "mate": 0},
        {"moves": "c7c5 g1f3 d7d6", "cp": 35, "mate": 0},
    ],
}

FAKE_ONLINE_COUNT = "83422"

FAKE_TEAM = {
    "id": "lichess-swiss",
    "name": "Lichess Swiss",
    "description": "The official Lichess Swiss team.",
    "nbMembers": 50000,
    "leaders": [
        {"name": "thibault", "id": "thibault"},
        {"name": "ornicar", "id": "ornicar"},
    ],
    "open": True,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/api/user/drnykterstein": ("json", FAKE_USER),
        "/api/user/drnykterstein/rating-history": ("json", FAKE_RATING_HISTORY),
        "/api/games/user/drnykterstein": ("ndjson", FAKE_GAMES_NDJSON),
        "/game/export/abcd1234": ("json", FAKE_GAME),
        "/api/puzzle/daily": ("json", FAKE_DAILY_PUZZLE),
        "/api/puzzle/K69di": ("json", FAKE_PUZZLE),
        "/api/player/top/10/bullet": ("json", FAKE_LEADERBOARD),
        "/api/cloud-eval": ("json", FAKE_CLOUD_EVAL),
        "/api/user/count": ("text", FAKE_ONLINE_COUNT),
        "/api/team/lichess-swiss": ("json", FAKE_TEAM),
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    # Sort paths by length descending so more specific paths match first.
    sorted_entries = sorted(defaults.items(), key=lambda kv: len(kv[0]), reverse=True)

    def mock_get(url, params=None, headers=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        for path, (resp_type, data) in sorted_entries:
            if url.endswith(path) or path in url:
                if resp_type == "ndjson":
                    resp.text = data
                    resp.json.return_value = json.loads(data.split("\n")[0])
                elif resp_type == "text":
                    resp.text = data
                    resp.json.side_effect = ValueError("not json")
                else:
                    resp.json.return_value = data
                    resp.text = json.dumps(data)
                return resp
        resp.json.return_value = {}
        resp.text = "{}"
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """LichessService with mocked HTTP client."""
    from lichess_mcp.service import LichessService

    svc = LichessService.__new__(LichessService)
    svc._http = mock_http
    svc._api_token = None
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked LichessService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-lichess", version="0.0.1")
    srv.register(service)
    return srv
