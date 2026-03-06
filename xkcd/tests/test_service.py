"""Unit tests — every XKCDService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock, patch

from xkcd_mcp.gen.xkcd.v1 import xkcd_pb2 as pb
from tests.conftest import (
    FAKE_LATEST,
    FAKE_COMIC_1,
    FAKE_COMIC_353,
    FAKE_COMIC_2998,
    FAKE_COMIC_2999,
    FAKE_EXPLANATION,
)


class TestGetLatest:
    def test_returns_latest_comic(self, service):
        resp = service.GetLatest(pb.GetLatestRequest())
        assert resp.comic.num == 3000
        assert resp.comic.title == "The Latest Comic"

    def test_latest_has_alt_text(self, service):
        resp = service.GetLatest(pb.GetLatestRequest())
        assert resp.comic.alt == "This is the hover text for the latest comic."

    def test_latest_has_image_url(self, service):
        resp = service.GetLatest(pb.GetLatestRequest())
        assert resp.comic.img.startswith("https://")
        assert resp.comic.img.endswith(".png")

    def test_latest_has_date(self, service):
        resp = service.GetLatest(pb.GetLatestRequest())
        assert resp.comic.year == "2025"
        assert resp.comic.month == "3"
        assert resp.comic.day == "3"


class TestGetComic:
    def test_get_comic_1(self, service):
        resp = service.GetComic(pb.GetComicRequest(num=1))
        assert resp.comic.num == 1
        assert resp.comic.title == "Barrel - Part 1"
        assert resp.comic.alt == "Don't we all."

    def test_get_comic_353(self, service):
        resp = service.GetComic(pb.GetComicRequest(num=353))
        assert resp.comic.num == 353
        assert resp.comic.title == "Python"
        assert "Python" in resp.comic.alt

    def test_get_comic_has_image(self, service):
        resp = service.GetComic(pb.GetComicRequest(num=1))
        assert resp.comic.img.startswith("https://")

    def test_get_comic_has_transcript(self, service):
        resp = service.GetComic(pb.GetComicRequest(num=1))
        assert "barrel" in resp.comic.transcript.lower()


class TestGetRandom:
    def test_returns_a_comic(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert resp.comic.num > 0
        assert resp.comic.title != ""

    def test_random_has_all_fields(self, service):
        resp = service.GetRandom(pb.GetRandomRequest())
        assert resp.comic.img != ""
        assert resp.comic.alt != ""


class TestGetRange:
    def test_returns_comics_in_range(self, service):
        resp = service.GetRange(pb.GetRangeRequest(start_num=2998, end_num=3000))
        assert len(resp.comics) == 3
        nums = [c.num for c in resp.comics]
        assert 2998 in nums
        assert 2999 in nums
        assert 3000 in nums

    def test_range_order(self, service):
        resp = service.GetRange(pb.GetRangeRequest(start_num=2998, end_num=3000))
        nums = [c.num for c in resp.comics]
        assert nums == sorted(nums)

    def test_range_clamped_to_50(self, service):
        resp = service.GetRange(pb.GetRangeRequest(start_num=1, end_num=100))
        # Should be clamped: 1 to 50 (50 comics, but 404 doesn't exist in this range).
        assert len(resp.comics) <= 50

    def test_skips_404(self, service):
        resp = service.GetRange(pb.GetRangeRequest(start_num=403, end_num=405))
        nums = [c.num for c in resp.comics]
        assert 404 not in nums


class TestSearchByTitle:
    def test_finds_matching_comics(self, service):
        resp = service.SearchByTitle(pb.SearchByTitleRequest(query="Comic", search_count=10))
        # The mock generates "Comic {num}" for unknown numbers, so recent ones match.
        assert len(resp.comics) > 0

    def test_case_insensitive(self, service):
        resp = service.SearchByTitle(pb.SearchByTitleRequest(query="latest", search_count=10))
        titles = [c.title.lower() for c in resp.comics]
        assert any("latest" in t for t in titles)

    def test_no_results(self, service):
        resp = service.SearchByTitle(pb.SearchByTitleRequest(query="zzzznonexistentzzzz", search_count=5))
        assert len(resp.comics) == 0

    def test_search_count_defaults(self, service):
        # With default search_count (100), should search more comics.
        resp = service.SearchByTitle(pb.SearchByTitleRequest(query="Comic"))
        # Just verify it runs without error.
        assert isinstance(resp, pb.SearchByTitleResponse)


class TestGetExplanation:
    def test_returns_explanation(self, service):
        resp = service.GetExplanation(pb.GetExplanationRequest(num=353))
        assert resp.num == 353
        assert "Python" in resp.title
        assert len(resp.explanation) > 0

    def test_explanation_has_url(self, service):
        resp = service.GetExplanation(pb.GetExplanationRequest(num=353))
        assert resp.url == "https://www.explainxkcd.com/wiki/index.php/353"

    def test_explanation_cleaned(self, service):
        resp = service.GetExplanation(pb.GetExplanationRequest(num=353))
        # Wiki markup like == should be stripped.
        assert "==" not in resp.explanation
        # Should contain readable text about Python.
        assert "Python" in resp.explanation


class TestGetComicCount:
    def test_returns_count(self, service):
        resp = service.GetComicCount(pb.GetComicCountRequest())
        assert resp.count == 3000

    def test_count_is_positive(self, service):
        resp = service.GetComicCount(pb.GetComicCountRequest())
        assert resp.count > 0


class TestGetMultiple:
    def test_returns_requested_comics(self, service):
        resp = service.GetMultiple(pb.GetMultipleRequest(nums=[1, 353]))
        assert len(resp.comics) == 2
        nums = {c.num for c in resp.comics}
        assert 1 in nums
        assert 353 in nums

    def test_skips_404(self, service):
        resp = service.GetMultiple(pb.GetMultipleRequest(nums=[1, 404, 353]))
        nums = {c.num for c in resp.comics}
        assert 404 not in nums
        assert len(resp.comics) == 2

    def test_clamped_to_50(self, service):
        big_list = list(range(1, 100))
        resp = service.GetMultiple(pb.GetMultipleRequest(nums=big_list))
        assert len(resp.comics) <= 50

    def test_empty_list(self, service):
        resp = service.GetMultiple(pb.GetMultipleRequest(nums=[]))
        assert len(resp.comics) == 0


class TestGetRecent:
    def test_returns_recent_comics(self, service):
        resp = service.GetRecent(pb.GetRecentRequest(count=3))
        assert len(resp.comics) == 3

    def test_default_count(self, service):
        resp = service.GetRecent(pb.GetRecentRequest())
        # Default is 10.
        assert len(resp.comics) == 10

    def test_recent_in_descending_order(self, service):
        resp = service.GetRecent(pb.GetRecentRequest(count=3))
        nums = [c.num for c in resp.comics]
        assert nums == sorted(nums, reverse=True)

    def test_clamped_to_50(self, service):
        resp = service.GetRecent(pb.GetRecentRequest(count=100))
        assert len(resp.comics) <= 50


class TestGetByDate:
    def test_finds_comics_by_date(self, service):
        # FAKE_LATEST is year=2025, month=3.
        resp = service.GetByDate(pb.GetByDateRequest(year=2025, month=3, search_count=10))
        assert len(resp.comics) > 0
        for c in resp.comics:
            assert c.year == "2025"
            assert c.month == "3"

    def test_no_results_for_old_date(self, service):
        # Search only 5 recent comics — won't find 2006 comics.
        resp = service.GetByDate(pb.GetByDateRequest(year=2006, month=1, search_count=5))
        assert len(resp.comics) == 0

    def test_default_search_count(self, service):
        # Just verify it runs with default search_count.
        resp = service.GetByDate(pb.GetByDateRequest(year=2025, month=3))
        assert isinstance(resp, pb.GetByDateResponse)
