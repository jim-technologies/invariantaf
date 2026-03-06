"""Shared fixtures for NASA MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nasa_mcp.gen.nasa.v1 import nasa_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real NASA API return shapes
# ---------------------------------------------------------------------------

FAKE_APOD = {
    "title": "The Horsehead Nebula",
    "explanation": "One of the most identifiable nebulae in the sky, the Horsehead Nebula...",
    "url": "https://apod.nasa.gov/apod/image/2401/horsehead.jpg",
    "hdurl": "https://apod.nasa.gov/apod/image/2401/horsehead_hd.jpg",
    "media_type": "image",
    "date": "2024-01-15",
    "copyright": "John Doe",
}

FAKE_APOD_RANGE = [
    {
        "title": "The Horsehead Nebula",
        "explanation": "One of the most identifiable nebulae...",
        "url": "https://apod.nasa.gov/apod/image/2401/horsehead.jpg",
        "hdurl": "https://apod.nasa.gov/apod/image/2401/horsehead_hd.jpg",
        "media_type": "image",
        "date": "2024-01-15",
        "copyright": "John Doe",
    },
    {
        "title": "Andromeda Galaxy",
        "explanation": "The nearest large galaxy to the Milky Way...",
        "url": "https://apod.nasa.gov/apod/image/2401/andromeda.jpg",
        "hdurl": "https://apod.nasa.gov/apod/image/2401/andromeda_hd.jpg",
        "media_type": "image",
        "date": "2024-01-16",
        "copyright": "",
    },
]

FAKE_MARS_PHOTOS = {
    "photos": [
        {
            "id": 102693,
            "sol": 1000,
            "camera": {"name": "FHAZ", "full_name": "Front Hazard Avoidance Camera"},
            "img_src": "https://mars.nasa.gov/msl-raw-images/proj/msl/redops/ods/surface/sol/01000/opgs/edr/fcam/FLB_486615455EDR_F0481570FHAZ00323M_.JPG",
            "earth_date": "2015-05-30",
            "rover": {"name": "Curiosity"},
        },
        {
            "id": 102694,
            "sol": 1000,
            "camera": {"name": "NAVCAM", "full_name": "Navigation Camera"},
            "img_src": "https://mars.nasa.gov/msl-raw-images/proj/msl/redops/ods/surface/sol/01000/navcam.JPG",
            "earth_date": "2015-05-30",
            "rover": {"name": "Curiosity"},
        },
    ]
}

FAKE_MARS_MANIFEST = {
    "photo_manifest": {
        "name": "Curiosity",
        "landing_date": "2012-08-06",
        "launch_date": "2011-11-26",
        "status": "active",
        "max_sol": 4102,
        "max_date": "2024-01-15",
        "total_photos": 695670,
    }
}

FAKE_NEOS = {
    "element_count": 2,
    "near_earth_objects": {
        "2024-01-15": [
            {
                "id": "3542519",
                "name": "(2010 PK9)",
                "absolute_magnitude_h": 21.4,
                "estimated_diameter": {
                    "kilometers": {
                        "estimated_diameter_min": 0.1011,
                        "estimated_diameter_max": 0.2261,
                    }
                },
                "is_potentially_hazardous_asteroid": False,
                "close_approach_data": [
                    {
                        "close_approach_date": "2024-01-15",
                        "relative_velocity": {"kilometers_per_hour": "48520.1234"},
                        "miss_distance": {"kilometers": "5432100.123"},
                        "orbiting_body": "Earth",
                    }
                ],
            },
            {
                "id": "54088823",
                "name": "(2020 QW3)",
                "absolute_magnitude_h": 26.7,
                "estimated_diameter": {
                    "kilometers": {
                        "estimated_diameter_min": 0.0110,
                        "estimated_diameter_max": 0.0247,
                    }
                },
                "is_potentially_hazardous_asteroid": True,
                "close_approach_data": [
                    {
                        "close_approach_date": "2024-01-15",
                        "relative_velocity": {"kilometers_per_hour": "72340.5678"},
                        "miss_distance": {"kilometers": "1234567.890"},
                        "orbiting_body": "Earth",
                    }
                ],
            },
        ]
    },
}

FAKE_NEO_LOOKUP = {
    "id": "3542519",
    "name": "(2010 PK9)",
    "absolute_magnitude_h": 21.4,
    "estimated_diameter": {
        "kilometers": {
            "estimated_diameter_min": 0.1011,
            "estimated_diameter_max": 0.2261,
        }
    },
    "is_potentially_hazardous_asteroid": False,
    "close_approach_data": [
        {
            "close_approach_date": "2024-01-15",
            "relative_velocity": {"kilometers_per_hour": "48520.1234"},
            "miss_distance": {"kilometers": "5432100.123"},
            "orbiting_body": "Earth",
        }
    ],
}

FAKE_EPIC = [
    {
        "identifier": "20240115003633",
        "caption": "This image was taken by NASA's EPIC camera onboard the NOAA DSCOVR spacecraft",
        "image": "epic_1b_20240115003633",
        "date": "2024-01-15 00:36:33",
        "centroid_coordinates": {"lat": 12.34, "lon": -56.78},
    },
    {
        "identifier": "20240115021533",
        "caption": "This image was taken by NASA's EPIC camera onboard the NOAA DSCOVR spacecraft",
        "image": "epic_1b_20240115021533",
        "date": "2024-01-15 02:15:33",
        "centroid_coordinates": {"lat": 10.20, "lon": -50.30},
    },
]

FAKE_NASA_IMAGES = {
    "collection": {
        "items": [
            {
                "data": [
                    {
                        "nasa_id": "PIA00001",
                        "title": "Apollo 11 Lunar Module",
                        "description": "The Apollo 11 Lunar Module Eagle in landing configuration.",
                        "media_type": "image",
                        "date_created": "1969-07-20T00:00:00Z",
                    }
                ],
                "links": [
                    {"href": "https://images-assets.nasa.gov/image/PIA00001/PIA00001~thumb.jpg"}
                ],
            },
            {
                "data": [
                    {
                        "nasa_id": "PIA00002",
                        "title": "Mars Rover Landing",
                        "description": "Artist concept of Mars rover landing.",
                        "media_type": "image",
                        "date_created": "2020-07-30T00:00:00Z",
                    }
                ],
                "links": [
                    {"href": "https://images-assets.nasa.gov/image/PIA00002/PIA00002~thumb.jpg"}
                ],
            },
        ]
    }
}

FAKE_DONKI = [
    {
        "activityID": "2024-01-15-00-09-00-CME-001",
        "startTime": "2024-01-15T00:09Z",
        "sourceLocation": "N20W30",
        "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/CME/12345/-1",
        "instruments": [
            {"displayName": "SOHO: LASCO/C2"},
            {"displayName": "SOHO: LASCO/C3"},
        ],
    },
    {
        "activityID": "2024-01-16-12-30-00-CME-001",
        "startTime": "2024-01-16T12:30Z",
        "sourceLocation": "S10E45",
        "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/CME/12346/-1",
        "instruments": [
            {"displayName": "STEREO A: SECCHI/COR2"},
        ],
    },
]

FAKE_TECHTRANSFER = {
    "results": [
        ["PAT-12345", "http://example.com", "Robotic Arm Controller", "A lightweight robotic arm controller for space applications.", "NASA", "Robotics", "", "", "", "Jet Propulsion Laboratory", ""],
        ["PAT-67890", "http://example.com", "Solar Cell Optimizer", "Advanced solar cell optimization technology.", "NASA", "Energy", "", "", "", "Glenn Research Center", ""],
    ]
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/planetary/apod": FAKE_APOD,
        "/rovers/curiosity/photos": FAKE_MARS_PHOTOS,
        "/manifests/curiosity": FAKE_MARS_MANIFEST,
        "/neo/rest/v1/feed": FAKE_NEOS,
        "/neo/rest/v1/neo/3542519": FAKE_NEO_LOOKUP,
        "/EPIC/api/natural": FAKE_EPIC,
        "/search": FAKE_NASA_IMAGES,
        "/DONKI/CME": FAKE_DONKI,
        "/techtransfer/patent/": FAKE_TECHTRANSFER,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        p = params or {}
        # Special case: APOD range vs single (same URL, differentiated by params).
        if "/planetary/apod" in url and "start_date" in p:
            resp.json.return_value = FAKE_APOD_RANGE
            return resp
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        # Check if URL contains the path (for URLs with query-like paths).
        for path, data in defaults.items():
            if path in url:
                resp.json.return_value = data
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
    """NASAService with mocked HTTP client."""
    from nasa_mcp.service import NASAService

    svc = NASAService.__new__(NASAService)
    svc._http = mock_http
    svc._api_key = "DEMO_KEY"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked NASAService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-nasa", version="0.0.1")
    srv.register(service)
    return srv
