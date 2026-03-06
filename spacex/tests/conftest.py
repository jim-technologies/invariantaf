"""Shared fixtures for SpaceX MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from spacex_mcp.gen.spacex.v1 import spacex_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real SpaceX v4 API return shapes
# ---------------------------------------------------------------------------

FAKE_LAUNCH = {
    "id": "5eb87d46ffd86e000604b388",
    "name": "Starlink Group 6-14",
    "date_utc": "2024-01-15T12:00:00.000Z",
    "date_unix": 1705320000,
    "success": True,
    "flight_number": 250,
    "rocket": "5e9d0d95eda69973a809d1ec",
    "details": "SpaceX launched 23 Starlink satellites to low Earth orbit.",
    "upcoming": False,
    "launchpad": "5e9e4502f509094188566f88",
    "payloads": ["60428aafc041c16716f73cd6"],
    "crew": [],
    "links": {
        "patch": {
            "small": "https://images2.imgbox.com/patch_small.png",
            "large": "https://images2.imgbox.com/patch_large.png",
        },
        "webcast": "https://www.youtube.com/watch?v=abc123",
        "wikipedia": "https://en.wikipedia.org/wiki/Starlink",
        "article": "https://www.spacex.com/launches/starlink-6-14",
    },
}

FAKE_LAUNCH_UPCOMING = {
    "id": "6243ae24af52800c6e919258",
    "name": "Starlink Group 10-1",
    "date_utc": "2026-04-01T00:00:00.000Z",
    "date_unix": 1774828800,
    "success": None,
    "flight_number": 400,
    "rocket": "5e9d0d95eda69973a809d1ec",
    "details": None,
    "upcoming": True,
    "launchpad": "5e9e4502f509094188566f88",
    "payloads": [],
    "crew": [],
    "links": {
        "patch": {"small": None, "large": None},
        "webcast": None,
        "wikipedia": None,
        "article": None,
    },
}

FAKE_ROCKET = {
    "id": "5e9d0d95eda69973a809d1ec",
    "name": "Falcon 9",
    "type": "rocket",
    "active": True,
    "stages": 2,
    "boosters": 0,
    "cost_per_launch": 50000000,
    "first_flight": "2010-06-04",
    "country": "United States",
    "company": "SpaceX",
    "height": {"meters": 70, "feet": 229.6},
    "diameter": {"meters": 3.7, "feet": 12},
    "mass": {"kg": 549054, "lb": 1207920},
    "payload_weights": [
        {"id": "leo", "name": "Low Earth Orbit", "kg": 22800, "lb": 50265},
        {"id": "gto", "name": "Geosynchronous Transfer Orbit", "kg": 8300, "lb": 18300},
    ],
    "engines": {
        "number": 9,
        "type": "merlin",
        "propellant_1": "liquid oxygen",
        "propellant_2": "RP-1 kerosene",
    },
    "description": "Falcon 9 is a two-stage rocket designed and manufactured by SpaceX for the reliable and safe transport of satellites and the Dragon spacecraft into orbit.",
    "wikipedia": "https://en.wikipedia.org/wiki/Falcon_9",
    "success_rate_pct": 98,
}

FAKE_CREW_MEMBER = {
    "id": "5ebf1b7323a9a60006e03a7b",
    "name": "Robert Behnken",
    "status": "active",
    "agency": "NASA",
    "image": "https://i.imgur.com/behnken.png",
    "wikipedia": "https://en.wikipedia.org/wiki/Robert_L._Behnken",
    "launches": ["5eb87d46ffd86e000604b388"],
}

FAKE_STARLINK = {
    "id": "5eed7714096e590006985825",
    "version": "v1.0",
    "launch": "5eb87d46ffd86e000604b388",
    "height_km": 550.5,
    "latitude": 45.123,
    "longitude": -93.456,
    "velocity_kms": 7.6,
    "spaceTrack": {},
}

FAKE_LAUNCHPAD = {
    "id": "5e9e4502f509094188566f88",
    "name": "KSC LC 39A",
    "full_name": "Kennedy Space Center Historic Launch Complex 39A",
    "locality": "Cape Canaveral",
    "region": "Florida",
    "latitude": 28.6080585,
    "longitude": -80.6039558,
    "launch_attempts": 200,
    "launch_successes": 198,
    "status": "active",
}

FAKE_COMPANY = {
    "name": "SpaceX",
    "founder": "Elon Musk",
    "founded": 2002,
    "employees": 12000,
    "vehicles": 4,
    "launch_sites": 3,
    "test_sites": 3,
    "ceo": "Elon Musk",
    "cto": "Elon Musk",
    "coo": "Gwynne Shotwell",
    "cto_propulsion": "Tom Mueller",
    "valuation": 74000000000,
    "summary": "SpaceX designs, manufactures and launches advanced rockets and spacecraft.",
    "headquarters": {
        "city": "Hawthorne",
        "state": "California",
    },
    "links": {
        "website": "https://www.spacex.com",
        "flickr": "https://www.flickr.com/photos/spacex/",
        "twitter": "https://twitter.com/SpaceX",
        "elon_twitter": "https://twitter.com/elonmusk",
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/v4/launches/latest": FAKE_LAUNCH,
        "/v4/launches/upcoming": [FAKE_LAUNCH_UPCOMING],
        "/v4/launches/5eb87d46ffd86e000604b388": FAKE_LAUNCH,
        "/v4/launches": [FAKE_LAUNCH, FAKE_LAUNCH_UPCOMING],
        "/v4/rockets/5e9d0d95eda69973a809d1ec": FAKE_ROCKET,
        "/v4/rockets": [FAKE_ROCKET],
        "/v4/crew": [FAKE_CREW_MEMBER],
        "/v4/starlink": [FAKE_STARLINK],
        "/v4/launchpads": [FAKE_LAUNCHPAD],
        "/v4/company": FAKE_COMPANY,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix -- try longest match first to avoid
        # "/v4/launches" matching before "/v4/launches/latest".
        for path in sorted(defaults.keys(), key=len, reverse=True):
            if url.endswith(path):
                resp.json.return_value = defaults[path]
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """SpaceXService with mocked HTTP client."""
    from spacex_mcp.service import SpaceXService

    svc = SpaceXService.__new__(SpaceXService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked SpaceXService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-spacex", version="0.0.1")
    srv.register(service)
    return srv
