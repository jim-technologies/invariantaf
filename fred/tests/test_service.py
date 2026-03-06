"""Unit tests — every FREDService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from fred_mcp.gen.fred.v1 import fred_pb2 as pb
from tests.conftest import (
    FAKE_CATEGORY,
    FAKE_CATEGORY_CHILDREN,
    FAKE_CATEGORY_SERIES,
    FAKE_OBSERVATIONS,
    FAKE_RELEASE,
    FAKE_RELEASE_DATES,
    FAKE_RELEASE_SERIES,
    FAKE_SEARCH,
    FAKE_SERIES,
    FAKE_SERIES_CATEGORIES,
)


class TestGetSeries:
    def test_returns_series_metadata(self, service):
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="GDP"))
        s = resp.series
        assert s.id == "GDP"
        assert s.title == "Gross Domestic Product"
        assert s.frequency == "Quarterly"
        assert s.units == "Billions of Dollars"
        assert s.seasonal_adjustment == "Seasonally Adjusted Annual Rate"

    def test_date_range(self, service):
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="GDP"))
        s = resp.series
        assert s.observation_start == "1947-01-01"
        assert s.observation_end == "2024-07-01"

    def test_notes(self, service):
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="GDP"))
        assert "BEA Account Code" in resp.series.notes

    def test_last_updated(self, service):
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="GDP"))
        assert "2024-12-19" in resp.series.last_updated

    def test_popularity(self, service):
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="GDP"))
        assert resp.series.popularity == 93

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"seriess": []})
        )
        resp = service.GetSeries(pb.GetSeriesRequest(series_id="NONEXISTENT"))
        assert resp.series.id == ""


class TestGetSeriesObservations:
    def test_returns_observations(self, service):
        resp = service.GetSeriesObservations(
            pb.GetSeriesObservationsRequest(series_id="GDP")
        )
        assert len(resp.observations) == 3
        assert resp.observations[0].date == "2024-01-01"
        assert resp.observations[0].value == "27956.998"

    def test_observation_values(self, service):
        resp = service.GetSeriesObservations(
            pb.GetSeriesObservationsRequest(series_id="GDP")
        )
        assert resp.observations[1].date == "2024-04-01"
        assert resp.observations[1].value == "28277.367"
        assert resp.observations[2].date == "2024-07-01"
        assert resp.observations[2].value == "28571.460"

    def test_date_range_params(self, service, mock_http):
        service.GetSeriesObservations(
            pb.GetSeriesObservationsRequest(
                series_id="GDP",
                observation_start="2024-01-01",
                observation_end="2024-12-31",
            )
        )
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("observation_start") == "2024-01-01"
        assert params.get("observation_end") == "2024-12-31"

    def test_sort_order_param(self, service, mock_http):
        service.GetSeriesObservations(
            pb.GetSeriesObservationsRequest(series_id="GDP", sort_order="desc")
        )
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("sort_order") == "desc"

    def test_limit_param(self, service, mock_http):
        service.GetSeriesObservations(
            pb.GetSeriesObservationsRequest(series_id="GDP", limit=10)
        )
        call_args = mock_http.get.call_args
        params = call_args[1].get("params", {})
        assert params.get("limit") == 10


class TestSearchSeries:
    def test_returns_results(self, service):
        resp = service.SearchSeries(
            pb.SearchSeriesRequest(search_text="inflation")
        )
        assert len(resp.results) == 2
        assert resp.results[0].id == "CPIAUCSL"
        assert resp.results[0].title == "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average"

    def test_count(self, service):
        resp = service.SearchSeries(
            pb.SearchSeriesRequest(search_text="inflation")
        )
        assert resp.count == 1532

    def test_second_result(self, service):
        resp = service.SearchSeries(
            pb.SearchSeriesRequest(search_text="inflation")
        )
        assert resp.results[1].id == "CPILFESL"
        assert resp.results[1].popularity == 88

    def test_series_fields(self, service):
        resp = service.SearchSeries(
            pb.SearchSeriesRequest(search_text="inflation")
        )
        s = resp.results[0]
        assert s.frequency == "Monthly"
        assert s.units == "Index 1982-1984=100"
        assert s.seasonal_adjustment == "Seasonally Adjusted"
        assert s.popularity == 95


class TestGetCategory:
    def test_returns_category(self, service):
        resp = service.GetCategory(pb.GetCategoryRequest(category_id=32991))
        assert resp.category.id == 32991
        assert resp.category.name == "Prices"
        assert resp.category.parent_id == 0

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"categories": []})
        )
        resp = service.GetCategory(pb.GetCategoryRequest(category_id=99999))
        assert resp.category.id == 0


class TestGetCategoryChildren:
    def test_returns_children(self, service):
        resp = service.GetCategoryChildren(
            pb.GetCategoryChildrenRequest(category_id=32991)
        )
        assert len(resp.categories) == 2
        assert resp.categories[0].id == 32992
        assert resp.categories[0].name == "Consumer Price Indexes (CPI and PCE)"
        assert resp.categories[0].parent_id == 32991

    def test_second_child(self, service):
        resp = service.GetCategoryChildren(
            pb.GetCategoryChildrenRequest(category_id=32991)
        )
        assert resp.categories[1].id == 32993
        assert resp.categories[1].name == "Producer Price Indexes (PPI)"


class TestGetCategorySeries:
    def test_returns_series(self, service):
        resp = service.GetCategorySeries(
            pb.GetCategorySeriesRequest(category_id=32992)
        )
        assert len(resp.seriess) == 1
        assert resp.seriess[0].id == "CPIAUCSL"
        assert resp.seriess[0].popularity == 95


class TestGetRelease:
    def test_returns_release(self, service):
        resp = service.GetRelease(pb.GetReleaseRequest(release_id=10))
        r = resp.release
        assert r.id == 10
        assert r.name == "Consumer Price Index"
        assert r.link == "https://www.bls.gov/cpi/"
        assert r.press_release is True

    def test_notes(self, service):
        resp = service.GetRelease(pb.GetReleaseRequest(release_id=10))
        assert "Consumer Price Index" in resp.release.notes


class TestGetReleaseDates:
    def test_returns_dates(self, service):
        resp = service.GetReleaseDates(
            pb.GetReleaseDatesRequest(release_id=10)
        )
        assert len(resp.release_dates) == 3
        assert resp.release_dates[0].date == "2025-01-15"
        assert resp.release_dates[0].release_id == 10
        assert resp.release_dates[0].release_name == "Consumer Price Index"

    def test_multiple_dates(self, service):
        resp = service.GetReleaseDates(
            pb.GetReleaseDatesRequest(release_id=10)
        )
        dates = [rd.date for rd in resp.release_dates]
        assert "2025-02-12" in dates
        assert "2025-03-12" in dates


class TestGetReleaseSeries:
    def test_returns_series(self, service):
        resp = service.GetReleaseSeries(
            pb.GetReleaseSeriesRequest(release_id=10)
        )
        assert len(resp.seriess) == 2
        ids = {s.id for s in resp.seriess}
        assert "CPIAUCSL" in ids
        assert "UNRATE" in ids

    def test_series_fields(self, service):
        resp = service.GetReleaseSeries(
            pb.GetReleaseSeriesRequest(release_id=10)
        )
        unrate = [s for s in resp.seriess if s.id == "UNRATE"][0]
        assert unrate.title == "Unemployment Rate"
        assert unrate.frequency == "Monthly"
        assert unrate.units == "Percent"
        assert unrate.popularity == 96


class TestGetSeriesCategories:
    def test_returns_categories(self, service):
        resp = service.GetSeriesCategories(
            pb.GetSeriesCategoriesRequest(series_id="GDP")
        )
        assert len(resp.categories) == 2
        assert resp.categories[0].id == 106
        assert resp.categories[0].name == "Gross Domestic Product"
        assert resp.categories[0].parent_id == 18

    def test_parent_category(self, service):
        resp = service.GetSeriesCategories(
            pb.GetSeriesCategoriesRequest(series_id="GDP")
        )
        assert resp.categories[1].id == 18
        assert resp.categories[1].name == "National Income & Product Accounts"
