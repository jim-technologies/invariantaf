"""Live integration tests for arXiv API -- hits the real API.

Run with:
    ARXIV_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) arXiv API endpoints.
The arXiv API is rate-limited; keep test volume low.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("ARXIV_RUN_LIVE_TESTS") != "1",
    reason="Set ARXIV_RUN_LIVE_TESTS=1 to run live arXiv API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as _arxiv_pb2  # noqa: F401
    from arxiv_mcp.service import ArxivService
    from invariant import Server

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-arxiv-live", version="0.0.1"
    )
    svc = ArxivService()
    srv.register(svc)
    yield srv
    srv.stop()


# --- Shared fixtures for paper discovery ---


@pytest.fixture(scope="module")
def discovered_paper(live_server):
    """Discover a valid paper via search for tests that need a paper ID."""
    result = live_server._cli(
        ["ArxivService", "Search", "-r", json.dumps({"query": "attention", "limit": 1})]
    )
    papers = result.get("papers", [])
    assert papers, "expected at least one paper from search"
    return papers[0]


# --- Search ---


class TestLiveSearch:
    def test_search(self, live_server):
        result = live_server._cli(
            ["ArxivService", "Search", "-r", json.dumps({"query": "transformer", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0
        p = papers[0]
        assert "title" in p
        assert "summary" in p

    def test_search_by_author(self, live_server):
        result = live_server._cli(
            ["ArxivService", "SearchByAuthor", "-r", json.dumps({"author": "Vaswani", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0

    def test_search_by_title(self, live_server):
        result = live_server._cli(
            ["ArxivService", "SearchByTitle", "-r", json.dumps({"title": "attention", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0

    def test_search_by_category(self, live_server):
        result = live_server._cli(
            ["ArxivService", "SearchByCategory", "-r", json.dumps({"category": "cs.AI", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0

    def test_search_by_abstract(self, live_server):
        result = live_server._cli(
            ["ArxivService", "SearchByAbstract", "-r", json.dumps({"query": "neural network", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0

    def test_advanced_search(self, live_server):
        result = live_server._cli(
            [
                "ArxivService",
                "AdvancedSearch",
                "-r",
                json.dumps({"author": "Vaswani", "title": "attention", "limit": 3}),
            ]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0


# --- Paper lookup ---


class TestLivePaper:
    def test_get_paper(self, live_server):
        result = live_server._cli(
            ["ArxivService", "GetPaper", "-r", json.dumps({"arxiv_id": "1706.03762"})]
        )
        paper = result.get("paper", {})
        assert "Attention" in paper.get("title", "")
        assert len(paper.get("authors", [])) > 0

    def test_get_paper_from_discovery(self, live_server, discovered_paper):
        arxiv_id = discovered_paper.get("arxivId") or discovered_paper.get("arxiv_id", "")
        if not arxiv_id:
            pytest.skip("no arxiv_id in discovered paper")
        # Strip version suffix for lookup if present
        base_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
        result = live_server._cli(
            ["ArxivService", "GetPaper", "-r", json.dumps({"arxiv_id": base_id})]
        )
        assert "paper" in result
        assert result["paper"].get("title")

    def test_get_multiple(self, live_server):
        result = live_server._cli(
            [
                "ArxivService",
                "GetMultiple",
                "-r",
                json.dumps({"arxiv_ids": ["1706.03762", "2106.09685"]}),
            ]
        )
        papers = result.get("papers", [])
        assert len(papers) >= 1


# --- Recent / Categories ---


class TestLiveRecent:
    def test_get_recent(self, live_server):
        result = live_server._cli(
            ["ArxivService", "GetRecent", "-r", json.dumps({"category": "cs.AI", "limit": 3})]
        )
        papers = result.get("papers", [])
        assert isinstance(papers, list)
        assert len(papers) > 0


class TestLiveCategories:
    def test_get_categories(self, live_server):
        result = live_server._cli(["ArxivService", "GetCategories"])
        categories = result.get("categories", [])
        assert isinstance(categories, list)
        assert len(categories) > 0
        cat = categories[0]
        assert "code" in cat
        assert "name" in cat
