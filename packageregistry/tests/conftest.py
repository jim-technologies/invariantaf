"""Shared fixtures for Package Registry MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from packageregistry_mcp.gen.packageregistry.v1 import packageregistry_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real NPM/PyPI API return shapes
# ---------------------------------------------------------------------------

FAKE_NPM_SEARCH = {
    "total": 2,
    "objects": [
        {
            "package": {
                "name": "react",
                "version": "18.2.0",
                "description": "A JavaScript library for building user interfaces",
                "keywords": ["react", "ui", "frontend"],
                "date": "2022-06-14T20:00:00.000Z",
                "publisher": {"username": "gaearon"},
                "links": {
                    "homepage": "https://react.dev",
                    "repository": "https://github.com/facebook/react",
                },
            },
        },
        {
            "package": {
                "name": "react-dom",
                "version": "18.2.0",
                "description": "React package for working with the DOM",
                "keywords": ["react", "dom"],
                "date": "2022-06-14T20:00:00.000Z",
                "publisher": {"username": "gaearon"},
                "links": {
                    "homepage": "https://react.dev",
                    "repository": "https://github.com/facebook/react",
                },
            },
        },
    ],
}

FAKE_NPM_PACKAGE = {
    "name": "express",
    "description": "Fast, unopinionated, minimalist web framework",
    "dist-tags": {"latest": "4.18.2", "next": "5.0.0-beta.1"},
    "license": "MIT",
    "homepage": "http://expressjs.com/",
    "repository": {"type": "git", "url": "https://github.com/expressjs/express.git"},
    "maintainers": [
        {"name": "dougwilson", "email": "doug@somethingdoug.com"},
        {"name": "linusu", "email": "linus@folkdatorn.se"},
    ],
    "time": {
        "created": "2010-12-29T19:38:25.450Z",
        "modified": "2024-01-15T10:00:00.000Z",
        "4.18.2": "2022-10-08T14:00:00.000Z",
        "4.18.1": "2022-04-29T14:00:00.000Z",
    },
    "versions": {
        "4.18.1": {
            "dependencies": {"accepts": "~1.3.8", "body-parser": "1.20.0"},
            "devDependencies": {"mocha": "10.0.0"},
            "peerDependencies": {},
        },
        "4.18.2": {
            "dependencies": {"accepts": "~1.3.8", "body-parser": "1.20.1"},
            "devDependencies": {"mocha": "10.1.0", "supertest": "6.3.0"},
            "peerDependencies": {},
        },
    },
}

FAKE_NPM_DOWNLOADS = {
    "package": "express",
    "downloads": 25000000,
    "start": "2025-01-08",
    "end": "2025-01-14",
}

FAKE_PYPI_PACKAGE = {
    "info": {
        "name": "requests",
        "version": "2.31.0",
        "summary": "Python HTTP for Humans.",
        "description": "# Requests\n\nRequests is a simple HTTP library.",
        "author": "Kenneth Reitz",
        "author_email": "me@kennethreitz.org",
        "license": "Apache-2.0",
        "home_page": "https://requests.readthedocs.io",
        "project_urls": {
            "Documentation": "https://requests.readthedocs.io",
            "Source": "https://github.com/psf/requests",
        },
        "requires_python": ">=3.7",
        "requires_dist": [
            "charset-normalizer (<4,>=2)",
            "idna (<4,>=2.5)",
            "urllib3 (<3,>=1.21.1)",
            "certifi (>=2017.4.17)",
        ],
        "classifiers": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Programming Language :: Python :: 3",
        ],
    },
    "releases": {
        "2.30.0": [{"upload_time": "2023-05-22T15:00:00"}],
        "2.31.0": [{"upload_time": "2023-05-22T16:00:00"}],
    },
}

FAKE_PYPI_VERSION = {
    "info": {
        "name": "requests",
        "version": "2.30.0",
        "summary": "Python HTTP for Humans.",
        "author": "Kenneth Reitz",
        "license": "Apache-2.0",
        "requires_python": ">=3.7",
        "requires_dist": [
            "charset-normalizer (<4,>=2)",
            "idna (<4,>=2.5)",
            "urllib3 (<3,>=1.21.1)",
            "certifi (>=2017.4.17)",
        ],
    },
    "releases": {
        "2.30.0": [{"upload_time": "2023-05-22T15:00:00"}],
    },
}

FAKE_PYPI_DOWNLOADS = {
    "package": "requests",
    "data": {
        "last_day": 5000000,
        "last_week": 35000000,
        "last_month": 150000000,
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/-/v1/search": FAKE_NPM_SEARCH,
        "/express": FAKE_NPM_PACKAGE,
        "/downloads/point/last-week/express": FAKE_NPM_DOWNLOADS,
        "/pypi/requests/json": FAKE_PYPI_PACKAGE,
        "/pypi/requests/2.30.0/json": FAKE_PYPI_VERSION,
        "/api/packages/requests/recent": FAKE_PYPI_DOWNLOADS,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix — longest match wins to avoid ambiguity
        # (e.g., "/downloads/point/last-week/express" vs "/express").
        best_path = ""
        best_data = None
        for path, data in defaults.items():
            if url.endswith(path) and len(path) > len(best_path):
                best_path = path
                best_data = data
        resp.json.return_value = best_data if best_data is not None else {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """PackageRegistryService with mocked HTTP client."""
    from packageregistry_mcp.service import PackageRegistryService

    svc = PackageRegistryService.__new__(PackageRegistryService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked PackageRegistryService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-pkgreg", version="0.0.1")
    srv.register(service)
    return srv
