"""Shared fixtures for XKCD MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real XKCD JSON API return shapes
# ---------------------------------------------------------------------------

FAKE_LATEST = {
    "num": 3000,
    "title": "The Latest Comic",
    "safe_title": "The Latest Comic",
    "alt": "This is the hover text for the latest comic.",
    "img": "https://imgs.xkcd.com/comics/the_latest_comic.png",
    "year": "2025",
    "month": "3",
    "day": "3",
    "link": "",
    "news": "",
    "transcript": "A person is standing at a computer.",
}

FAKE_COMIC_1 = {
    "num": 1,
    "title": "Barrel - Part 1",
    "safe_title": "Barrel - Part 1",
    "alt": "Don't we all.",
    "img": "https://imgs.xkcd.com/comics/barrel_cropped_(1).jpg",
    "year": "2006",
    "month": "1",
    "day": "1",
    "link": "",
    "news": "",
    "transcript": "[[A boy sits in a barrel which is floating in an ocean.]]\nBoy: I wonder where I'll float next?\n[[The barrel drifts into the distance. Nothing else can be seen.]]\n{{Alt: Don't we all.}}",
}

FAKE_COMIC_353 = {
    "num": 353,
    "title": "Python",
    "safe_title": "Python",
    "alt": "I wrote 20 short programs in Python yesterday.  It was wonderful.  Series of tubes.",
    "img": "https://imgs.xkcd.com/comics/python.png",
    "year": "2007",
    "month": "12",
    "day": "5",
    "link": "",
    "news": "",
    "transcript": "[[Person is flying through the air.]]\nPerson: WHEEEE!\n{{ I wrote 20 short programs in Python yesterday.  It was wonderful.  Surreal. }}",
}

FAKE_COMIC_2999 = {
    "num": 2999,
    "title": "Almost There",
    "safe_title": "Almost There",
    "alt": "So close to 3000.",
    "img": "https://imgs.xkcd.com/comics/almost_there.png",
    "year": "2025",
    "month": "3",
    "day": "1",
    "link": "",
    "news": "",
    "transcript": "",
}

FAKE_COMIC_2998 = {
    "num": 2998,
    "title": "Data Pipeline",
    "safe_title": "Data Pipeline",
    "alt": "My pipeline has a pipeline.",
    "img": "https://imgs.xkcd.com/comics/data_pipeline.png",
    "year": "2025",
    "month": "2",
    "day": "28",
    "link": "",
    "news": "",
    "transcript": "",
}

FAKE_EXPLANATION = {
    "parse": {
        "title": "353: Python",
        "pageid": 394,
        "wikitext": {
            "*": "== Explanation ==\nIn this comic, [[Randall]] discovers the [[Python]] programming language. He is so delighted by how easy it is to use that he starts flying. The '''alt text''' references writing 20 short programs, highlighting Python's productivity.\n\n== Transcript ==\nPerson flying.\n\n{{comic discussion}}"
        },
    }
}

# Map of comic number -> fake data
COMIC_DATA = {
    None: FAKE_LATEST,  # latest (no number)
    1: FAKE_COMIC_1,
    353: FAKE_COMIC_353,
    2998: FAKE_COMIC_2998,
    2999: FAKE_COMIC_2999,
    3000: FAKE_LATEST,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    overrides = url_responses or {}
    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Check overrides first.
        for pattern, data in overrides.items():
            if pattern in url:
                resp.json.return_value = data
                return resp

        # explainxkcd API
        if "explainxkcd.com" in url:
            resp.json.return_value = FAKE_EXPLANATION
            return resp

        # XKCD comic JSON API
        if "xkcd.com" in url:
            if "/info.0.json" in url:
                # Check if it's a numbered comic or latest.
                # Pattern: https://xkcd.com/{num}/info.0.json or https://xkcd.com/info.0.json
                parts = url.replace("https://xkcd.com/", "").replace("/info.0.json", "")
                if parts == "" or parts == "https://xkcd.com":
                    # Latest.
                    resp.json.return_value = FAKE_LATEST
                else:
                    try:
                        num = int(parts)
                        if num in COMIC_DATA:
                            resp.json.return_value = COMIC_DATA[num]
                        else:
                            # Generate a fake comic for any number.
                            resp.json.return_value = {
                                "num": num,
                                "title": f"Comic {num}",
                                "safe_title": f"Comic {num}",
                                "alt": f"Alt text for comic {num}.",
                                "img": f"https://imgs.xkcd.com/comics/comic_{num}.png",
                                "year": "2025",
                                "month": "3",
                                "day": "1",
                                "link": "",
                                "news": "",
                                "transcript": "",
                            }
                    except ValueError:
                        resp.json.return_value = FAKE_LATEST
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
    """XKCDService with mocked HTTP client."""
    from xkcd_mcp.service import XKCDService

    svc = XKCDService.__new__(XKCDService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked XKCDService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-xkcd", version="0.0.1")
    srv.register(service)
    return srv
