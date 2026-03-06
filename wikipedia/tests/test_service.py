"""Unit tests — every WikipediaService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from wikipedia_mcp.gen.wikipedia.v1 import wikipedia_pb2 as pb
from tests.conftest import (
    FAKE_SEARCH,
    FAKE_PAGE_SUMMARY,
    FAKE_FULL_PAGE,
    FAKE_RANDOM_SUMMARY,
    FAKE_ON_THIS_DAY,
    FAKE_FEATURED,
    FAKE_LANGLINKS,
    FAKE_CATEGORIES,
    FAKE_LINKS,
    FAKE_IMAGES,
)


class TestSearch:
    def test_returns_results(self, service):
        resp = service.Search(pb.SearchRequest(query="quantum"))
        assert len(resp.results) == 2

    def test_first_result_fields(self, service):
        resp = service.Search(pb.SearchRequest(query="quantum"))
        r = resp.results[0]
        assert r.page_id == 100
        assert r.title == "Quantum computing"
        assert "Quantum" in r.snippet
        assert r.word_count == 8500
        assert r.timestamp == "2025-01-10T12:00:00Z"

    def test_second_result(self, service):
        resp = service.Search(pb.SearchRequest(query="quantum"))
        r = resp.results[1]
        assert r.page_id == 200
        assert r.title == "Quantum mechanics"
        assert r.word_count == 15000

    def test_total_hits(self, service):
        resp = service.Search(pb.SearchRequest(query="quantum"))
        assert resp.total_hits == 12345

    def test_default_limit(self, service, mock_http):
        service.Search(pb.SearchRequest(query="test"))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("srlimit") == "10"

    def test_custom_limit(self, service, mock_http):
        service.Search(pb.SearchRequest(query="test", limit=5))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("srlimit") == "5"

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"query": {"searchinfo": {"totalhits": 0}, "search": []}}),
        )
        resp = service.Search(pb.SearchRequest(query="xyznonexistent"))
        assert len(resp.results) == 0
        assert resp.total_hits == 0


class TestGetPage:
    def test_returns_summary(self, service):
        resp = service.GetPage(pb.GetPageRequest(title="Albert_Einstein"))
        assert resp.title == "Albert Einstein"
        assert "German-born theoretical physicist" in resp.extract

    def test_thumbnail(self, service):
        resp = service.GetPage(pb.GetPageRequest(title="Albert_Einstein"))
        assert "einstein.jpg" in resp.thumbnail_url

    def test_description(self, service):
        resp = service.GetPage(pb.GetPageRequest(title="Albert_Einstein"))
        assert "1879" in resp.description

    def test_page_id(self, service):
        resp = service.GetPage(pb.GetPageRequest(title="Albert_Einstein"))
        assert resp.page_id == 736

    def test_content_url(self, service):
        resp = service.GetPage(pb.GetPageRequest(title="Albert_Einstein"))
        assert "wikipedia.org" in resp.content_url


class TestGetFullPage:
    def test_returns_content(self, service):
        resp = service.GetFullPage(pb.GetFullPageRequest(title="Albert_Einstein"))
        assert resp.title == "Albert Einstein"
        assert "theory of relativity" in resp.content

    def test_page_id(self, service):
        resp = service.GetFullPage(pb.GetFullPageRequest(title="Albert_Einstein"))
        assert resp.page_id == 736

    def test_content_is_plain_text(self, service):
        resp = service.GetFullPage(pb.GetFullPageRequest(title="Albert_Einstein"))
        assert "<" not in resp.content  # No HTML tags

    def test_empty_pages(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"query": {"pages": {}}}),
        )
        resp = service.GetFullPage(pb.GetFullPageRequest(title="NonexistentPage"))
        assert resp.title == ""
        assert resp.content == ""


class TestGetRandom:
    def test_returns_one_page(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert len(resp.pages) == 1
        assert resp.pages[0].title == "Platypus"

    def test_extract(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert "semiaquatic" in resp.pages[0].extract

    def test_thumbnail(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert "platypus.jpg" in resp.pages[0].thumbnail_url

    def test_multiple(self, service):
        resp = service.GetRandom(pb.GetRandomRequest(count=3))
        assert len(resp.pages) == 3
        for page in resp.pages:
            assert page.title == "Platypus"

    def test_page_id(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert resp.pages[0].page_id == 24407


class TestGetOnThisDay:
    def test_returns_events(self, service):
        resp = service.GetOnThisDay(pb.GetOnThisDayRequest(month=7, day=4))
        assert len(resp.events) == 2

    def test_first_event(self, service):
        resp = service.GetOnThisDay(pb.GetOnThisDayRequest(month=7, day=4))
        e = resp.events[0]
        assert e.year == 1776
        assert "Declaration of Independence" in e.text

    def test_event_pages(self, service):
        resp = service.GetOnThisDay(pb.GetOnThisDayRequest(month=7, day=4))
        pages = resp.events[0].pages
        assert len(pages) == 1
        assert pages[0].title == "United States Declaration of Independence"

    def test_second_event(self, service):
        resp = service.GetOnThisDay(pb.GetOnThisDayRequest(month=7, day=4))
        e = resp.events[1]
        assert e.year == 2012
        assert "Higgs boson" in e.text

    def test_event_page_with_no_thumbnail(self, service):
        resp = service.GetOnThisDay(pb.GetOnThisDayRequest(month=7, day=4))
        # Second event's page has thumbnail=None
        page = resp.events[1].pages[0]
        assert page.thumbnail_url == ""


class TestGetMostRead:
    def test_returns_articles(self, service):
        resp = service.GetMostRead(pb.GetMostReadRequest(year=2025, month=1, day=14))
        assert len(resp.articles) == 2

    def test_first_article(self, service):
        resp = service.GetMostRead(pb.GetMostReadRequest(year=2025, month=1, day=14))
        a = resp.articles[0]
        assert a.title == "ChatGPT"
        assert a.views == 250000
        assert "artificial intelligence" in a.extract

    def test_second_article(self, service):
        resp = service.GetMostRead(pb.GetMostReadRequest(year=2025, month=1, day=14))
        a = resp.articles[1]
        assert a.title == "Super Bowl LIX"
        assert a.views == 180000

    def test_date(self, service):
        resp = service.GetMostRead(pb.GetMostReadRequest(year=2025, month=1, day=14))
        assert resp.date == "2025-01-14"

    def test_thumbnail(self, service):
        resp = service.GetMostRead(pb.GetMostReadRequest(year=2025, month=1, day=14))
        assert "chatgpt.png" in resp.articles[0].thumbnail_url


class TestGetLanguages:
    def test_returns_languages(self, service):
        resp = service.GetLanguages(pb.GetLanguagesRequest(title="Albert_Einstein"))
        assert len(resp.languages) == 3

    def test_french(self, service):
        resp = service.GetLanguages(pb.GetLanguagesRequest(title="Albert_Einstein"))
        fr = [l for l in resp.languages if l.lang == "fr"][0]
        assert fr.title == "Albert Einstein"

    def test_german(self, service):
        resp = service.GetLanguages(pb.GetLanguagesRequest(title="Albert_Einstein"))
        de = [l for l in resp.languages if l.lang == "de"][0]
        assert de.title == "Albert Einstein"

    def test_japanese(self, service):
        resp = service.GetLanguages(pb.GetLanguagesRequest(title="Albert_Einstein"))
        ja = [l for l in resp.languages if l.lang == "ja"][0]
        assert len(ja.title) > 0


class TestGetCategories:
    def test_returns_categories(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest(title="Albert_Einstein"))
        assert len(resp.categories) == 3

    def test_category_names(self, service):
        resp = service.GetCategories(pb.GetCategoriesRequest(title="Albert_Einstein"))
        assert "Category:Nobel laureates in Physics" in resp.categories
        assert "Category:German physicists" in resp.categories
        assert "Category:20th-century physicists" in resp.categories


class TestGetLinks:
    def test_returns_links(self, service):
        resp = service.GetLinks(pb.GetLinksRequest(title="Albert_Einstein"))
        assert len(resp.links) == 3

    def test_link_titles(self, service):
        resp = service.GetLinks(pb.GetLinksRequest(title="Albert_Einstein"))
        assert "Theory of relativity" in resp.links
        assert "Photoelectric effect" in resp.links
        assert "Nobel Prize in Physics" in resp.links


class TestGetImages:
    def test_returns_images(self, service):
        resp = service.GetImages(pb.GetImagesRequest(title="Albert_Einstein"))
        assert len(resp.images) == 3

    def test_image_filenames(self, service):
        resp = service.GetImages(pb.GetImagesRequest(title="Albert_Einstein"))
        assert "File:Albert Einstein Head.jpg" in resp.images
        assert "File:Einstein 1921 by F Schmutzer.jpg" in resp.images
        assert "File:Nobel Prize.png" in resp.images
