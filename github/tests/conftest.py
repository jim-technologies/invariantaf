"""Shared fixtures for GitHub MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_mcp.gen.github.v1 import github_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real GitHub API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH_REPOS = {
    "total_count": 2,
    "items": [
        {
            "id": 1,
            "full_name": "torvalds/linux",
            "name": "linux",
            "owner": {"login": "torvalds"},
            "description": "Linux kernel source tree",
            "html_url": "https://github.com/torvalds/linux",
            "language": "C",
            "stargazers_count": 180000,
            "forks_count": 55000,
            "watchers_count": 180000,
            "open_issues_count": 300,
            "default_branch": "master",
            "license": {"name": "GPL-2.0"},
            "created_at": "2011-09-04T22:48:12Z",
            "updated_at": "2025-01-15T10:00:00Z",
            "fork": False,
            "archived": False,
            "topics": ["linux", "kernel", "os"],
        },
        {
            "id": 2,
            "full_name": "rust-lang/rust",
            "name": "rust",
            "owner": {"login": "rust-lang"},
            "description": "Empowering everyone to build reliable software",
            "html_url": "https://github.com/rust-lang/rust",
            "language": "Rust",
            "stargazers_count": 95000,
            "forks_count": 12000,
            "watchers_count": 95000,
            "open_issues_count": 9000,
            "default_branch": "master",
            "license": {"name": "MIT"},
            "created_at": "2010-06-16T20:39:03Z",
            "updated_at": "2025-01-15T10:00:00Z",
            "fork": False,
            "archived": False,
            "topics": ["rust", "compiler", "programming-language"],
        },
    ],
}

FAKE_SEARCH_USERS = {
    "total_count": 1,
    "items": [
        {
            "id": 1024025,
            "login": "torvalds",
            "avatar_url": "https://avatars.githubusercontent.com/u/1024025",
            "html_url": "https://github.com/torvalds",
            "type": "User",
        },
    ],
}

FAKE_USER = {
    "id": 1024025,
    "login": "torvalds",
    "avatar_url": "https://avatars.githubusercontent.com/u/1024025",
    "html_url": "https://github.com/torvalds",
    "type": "User",
    "name": "Linus Torvalds",
    "bio": "Creator of Linux and Git",
    "company": "Linux Foundation",
    "location": "Portland, OR",
    "email": None,
    "public_repos": 7,
    "public_gists": 0,
    "followers": 220000,
    "following": 0,
    "created_at": "2011-09-03T15:26:22Z",
}

FAKE_REPO = {
    "id": 1,
    "full_name": "torvalds/linux",
    "name": "linux",
    "owner": {"login": "torvalds"},
    "description": "Linux kernel source tree",
    "html_url": "https://github.com/torvalds/linux",
    "language": "C",
    "stargazers_count": 180000,
    "forks_count": 55000,
    "watchers_count": 180000,
    "open_issues_count": 300,
    "default_branch": "master",
    "license": {"name": "GPL-2.0"},
    "created_at": "2011-09-04T22:48:12Z",
    "updated_at": "2025-01-15T10:00:00Z",
    "fork": False,
    "archived": False,
    "topics": ["linux", "kernel"],
}

FAKE_ISSUES = [
    {
        "id": 100,
        "number": 42,
        "title": "Bug in scheduler",
        "body": "The scheduler has a race condition.",
        "state": "open",
        "html_url": "https://github.com/torvalds/linux/issues/42",
        "user": {"login": "contributor1"},
        "labels": [{"name": "bug", "color": "d73a4a", "description": "Something is broken"}],
        "assignees": [{"login": "torvalds"}],
        "comments": 5,
        "created_at": "2025-01-10T08:00:00Z",
        "updated_at": "2025-01-14T12:00:00Z",
        "closed_at": None,
        "pull_request": None,
    },
    {
        "id": 101,
        "number": 43,
        "title": "Add ARM64 support for new chip",
        "body": "PR to add support for the new ARM chip.",
        "state": "open",
        "html_url": "https://github.com/torvalds/linux/issues/43",
        "user": {"login": "contributor2"},
        "labels": [{"name": "enhancement", "color": "a2eeef", "description": "New feature"}],
        "assignees": [],
        "comments": 2,
        "created_at": "2025-01-11T09:00:00Z",
        "updated_at": "2025-01-13T10:00:00Z",
        "closed_at": None,
        "pull_request": {"url": "https://api.github.com/repos/torvalds/linux/pulls/43"},
    },
]

FAKE_ISSUE = {
    "id": 100,
    "number": 42,
    "title": "Bug in scheduler",
    "body": "The scheduler has a race condition.",
    "state": "open",
    "html_url": "https://github.com/torvalds/linux/issues/42",
    "user": {"login": "contributor1"},
    "labels": [{"name": "bug", "color": "d73a4a", "description": "Something is broken"}],
    "assignees": [{"login": "torvalds"}],
    "comments": 5,
    "created_at": "2025-01-10T08:00:00Z",
    "updated_at": "2025-01-14T12:00:00Z",
    "closed_at": None,
    "pull_request": None,
}

FAKE_PULLS = [
    {
        "id": 200,
        "number": 99,
        "title": "Fix memory leak in driver",
        "body": "This PR fixes a memory leak in the network driver.",
        "state": "open",
        "html_url": "https://github.com/torvalds/linux/pull/99",
        "user": {"login": "contributor3"},
        "merged": False,
        "merged_at": None,
        "head": {"ref": "fix-memory-leak"},
        "base": {"ref": "master"},
        "labels": [{"name": "bugfix", "color": "d73a4a", "description": ""}],
        "assignees": [{"login": "torvalds"}],
        "created_at": "2025-01-12T10:00:00Z",
        "updated_at": "2025-01-14T15:00:00Z",
    },
]

FAKE_PULL = {
    "id": 200,
    "number": 99,
    "title": "Fix memory leak in driver",
    "body": "This PR fixes a memory leak in the network driver.",
    "state": "open",
    "html_url": "https://github.com/torvalds/linux/pull/99",
    "user": {"login": "contributor3"},
    "merged": False,
    "merged_at": None,
    "head": {"ref": "fix-memory-leak"},
    "base": {"ref": "master"},
    "additions": 150,
    "deletions": 30,
    "changed_files": 5,
    "commits": 3,
    "comments": 7,
    "labels": [{"name": "bugfix", "color": "d73a4a", "description": ""}],
    "assignees": [{"login": "torvalds"}],
    "created_at": "2025-01-12T10:00:00Z",
    "updated_at": "2025-01-14T15:00:00Z",
}

FAKE_LANGUAGES = {
    "C": 900000000,
    "Assembly": 50000000,
    "Shell": 5000000,
    "Makefile": 3000000,
    "Python": 1000000,
}

FAKE_RATE_LIMIT = {
    "resources": {
        "core": {
            "limit": 60,
            "remaining": 55,
            "reset": 1700003600,
            "used": 5,
        },
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/search/repositories": FAKE_SEARCH_REPOS,
        "/search/users": FAKE_SEARCH_USERS,
        "/users/torvalds": FAKE_USER,
        "/repos/torvalds/linux": FAKE_REPO,
        "/repos/torvalds/linux/issues": FAKE_ISSUES,
        "/repos/torvalds/linux/issues/42": FAKE_ISSUE,
        "/repos/torvalds/linux/pulls": FAKE_PULLS,
        "/repos/torvalds/linux/pulls/99": FAKE_PULL,
        "/repos/torvalds/linux/languages": FAKE_LANGUAGES,
        "/rate_limit": FAKE_RATE_LIMIT,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
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
    """GitHubService with mocked HTTP client."""
    from github_mcp.service import GitHubService

    svc = GitHubService.__new__(GitHubService)
    svc._http = mock_http
    svc._token = None
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked GitHubService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-gh", version="0.0.1")
    srv.register(service)
    return srv
