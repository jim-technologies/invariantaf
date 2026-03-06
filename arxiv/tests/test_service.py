"""Unit tests — every ArxivService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as pb
from tests.conftest import (
    FAKE_SEARCH_XML,
    FAKE_SINGLE_PAPER_XML,
    FAKE_EMPTY_XML,
    FAKE_MULTI_XML,
)


class TestSearch:
    def test_returns_papers(self, service):
        resp = service.Search(pb.SearchRequest(query="attention", limit=10))
        assert len(resp.papers) == 2

    def test_paper_fields(self, service):
        resp = service.Search(pb.SearchRequest(query="attention"))
        paper = resp.papers[0]
        assert paper.arxiv_id == "1706.03762v7"
        assert paper.title == "Attention Is All You Need"
        assert "sequence transduction" in paper.summary
        assert "Ashish Vaswani" in paper.authors
        assert "Noam Shazeer" in paper.authors
        assert "cs.CL" in paper.categories
        assert "cs.AI" in paper.categories
        assert paper.published == "2017-06-12T17:57:34Z"
        assert paper.pdf_url == "http://arxiv.org/pdf/1706.03762v7"
        assert paper.arxiv_url == "http://arxiv.org/abs/1706.03762v7"

    def test_default_limit(self, service, mock_http):
        service.Search(pb.SearchRequest(query="test"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("max_results") == 10

    def test_custom_limit(self, service, mock_http):
        service.Search(pb.SearchRequest(query="test", limit=5))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("max_results") == 5

    def test_query_format(self, service, mock_http):
        service.Search(pb.SearchRequest(query="transformers"))
        call_args = mock_http.get.call_args
        assert "all:transformers" in call_args[1].get("params", {}).get("search_query", "")


class TestGetPaper:
    def test_returns_paper(self, service):
        resp = service.GetPaper(pb.GetPaperRequest(arxiv_id="1706.03762"))
        assert resp.paper is not None
        assert resp.paper.arxiv_id == "1706.03762v7"
        assert resp.paper.title == "Attention Is All You Need"

    def test_paper_authors(self, service):
        resp = service.GetPaper(pb.GetPaperRequest(arxiv_id="1706.03762"))
        assert len(resp.paper.authors) == 3
        assert "Ashish Vaswani" in resp.paper.authors

    def test_paper_categories(self, service):
        resp = service.GetPaper(pb.GetPaperRequest(arxiv_id="1706.03762"))
        assert "cs.CL" in resp.paper.categories
        assert "cs.AI" in resp.paper.categories

    def test_uses_id_list_param(self, service, mock_http):
        service.GetPaper(pb.GetPaperRequest(arxiv_id="1706.03762"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("id_list") == "1706.03762"

    def test_updated_field(self, service):
        resp = service.GetPaper(pb.GetPaperRequest(arxiv_id="1706.03762"))
        assert resp.paper.updated == "2023-08-02T00:00:00Z"


class TestSearchByAuthor:
    def test_returns_papers(self, service):
        resp = service.SearchByAuthor(pb.SearchByAuthorRequest(author="Vaswani"))
        assert len(resp.papers) == 2

    def test_query_format(self, service, mock_http):
        service.SearchByAuthor(pb.SearchByAuthorRequest(author="Vaswani", limit=5))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert "au:Vaswani" in params.get("search_query", "")
        assert params.get("max_results") == 5


class TestSearchByTitle:
    def test_returns_papers(self, service):
        resp = service.SearchByTitle(pb.SearchByTitleRequest(title="attention"))
        assert len(resp.papers) == 2

    def test_query_format(self, service, mock_http):
        service.SearchByTitle(pb.SearchByTitleRequest(title="attention", limit=3))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert "ti:attention" in params.get("search_query", "")
        assert params.get("max_results") == 3


class TestSearchByCategory:
    def test_returns_papers(self, service):
        resp = service.SearchByCategory(pb.SearchByCategoryRequest(category="cs.AI"))
        assert len(resp.papers) == 2

    def test_query_format(self, service, mock_http):
        service.SearchByCategory(pb.SearchByCategoryRequest(category="cs.LG", limit=20))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert "cat:cs.LG" in params.get("search_query", "")
        assert params.get("max_results") == 20


class TestSearchByAbstract:
    def test_returns_papers(self, service):
        resp = service.SearchByAbstract(pb.SearchByAbstractRequest(query="neural network"))
        assert len(resp.papers) == 2

    def test_query_format(self, service, mock_http):
        service.SearchByAbstract(pb.SearchByAbstractRequest(query="transformer", limit=15))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert "abs:transformer" in params.get("search_query", "")
        assert params.get("max_results") == 15


class TestGetRecent:
    def test_returns_papers(self, service):
        resp = service.GetRecent(pb.GetRecentRequest(category="cs.AI"))
        assert len(resp.papers) == 2

    def test_query_format(self, service, mock_http):
        service.GetRecent(pb.GetRecentRequest(category="cs.CL", limit=5))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert "cat:cs.CL" in params.get("search_query", "")
        assert params.get("sortBy") == "submittedDate"
        assert params.get("sortOrder") == "descending"
        assert params.get("max_results") == 5


class TestGetMultiple:
    def test_returns_multiple_papers(self, service):
        resp = service.GetMultiple(pb.GetMultipleRequest(
            arxiv_ids=["1706.03762", "2106.09685", "2005.14165"]
        ))
        assert len(resp.papers) == 3

    def test_uses_comma_separated_ids(self, service, mock_http):
        service.GetMultiple(pb.GetMultipleRequest(
            arxiv_ids=["1706.03762", "2106.09685"]
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("id_list") == "1706.03762,2106.09685"

    def test_paper_details(self, service):
        resp = service.GetMultiple(pb.GetMultipleRequest(
            arxiv_ids=["1706.03762", "2106.09685", "2005.14165"]
        ))
        titles = [p.title for p in resp.papers]
        assert "Attention Is All You Need" in titles
        assert "LoRA: Low-Rank Adaptation of Large Language Models" in titles
        assert "Language Models are Few-Shot Learners" in titles


class TestAdvancedSearch:
    def test_returns_papers(self, service):
        resp = service.AdvancedSearch(pb.AdvancedSearchRequest(
            author="Vaswani", title="attention"
        ))
        assert len(resp.papers) == 2

    def test_single_field(self, service, mock_http):
        service.AdvancedSearch(pb.AdvancedSearchRequest(author="Vaswani"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("search_query") == "au:Vaswani"

    def test_multiple_fields_combined(self, service, mock_http):
        service.AdvancedSearch(pb.AdvancedSearchRequest(
            author="Vaswani", title="attention", category="cs.CL"
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        query = params.get("search_query", "")
        assert "au:Vaswani" in query
        assert "ti:attention" in query
        assert "cat:cs.CL" in query
        assert "+AND+" in query

    def test_all_four_fields(self, service, mock_http):
        service.AdvancedSearch(pb.AdvancedSearchRequest(
            author="Vaswani", title="attention", abstract="transformer", category="cs.CL"
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        query = params.get("search_query", "")
        assert "au:Vaswani" in query
        assert "ti:attention" in query
        assert "abs:transformer" in query
        assert "cat:cs.CL" in query

    def test_custom_limit(self, service, mock_http):
        service.AdvancedSearch(pb.AdvancedSearchRequest(author="Vaswani", limit=25))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("max_results") == 25


class TestGetCategories:
    def test_returns_categories(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest())
        assert len(resp.categories) > 0

    def test_category_fields(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest())
        cs_ai = [c for c in resp.categories if c.code == "cs.AI"]
        assert len(cs_ai) == 1
        assert cs_ai[0].name == "Artificial Intelligence"
        assert len(cs_ai[0].description) > 10

    def test_common_categories_present(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest())
        codes = {c.code for c in resp.categories}
        assert "cs.AI" in codes
        assert "cs.LG" in codes
        assert "cs.CL" in codes
        assert "math.CO" in codes
        assert "stat.ML" in codes

    def test_no_http_call(self, service, mock_http):
        service.GetCategories(pb.GetCategoriesRequest())
        mock_http.get.assert_not_called()
