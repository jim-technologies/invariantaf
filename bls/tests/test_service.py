"""Unit tests -- every BLSService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from bls_mcp.gen.bls.v1 import bls_pb2 as pb
from tests.conftest import (
    FAKE_CPI_RESPONSE,
    FAKE_UNEMPLOYMENT_RESPONSE,
    FAKE_NONFARM_RESPONSE,
    FAKE_MULTIPLE_SERIES_RESPONSE,
    FAKE_CATALOG_RESPONSE,
    FAKE_EMPTY_RESPONSE,
)


class TestGetSeriesData:
    def test_returns_series(self, service):
        resp = service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="CUUR0000SA0",
            start_year="2024",
            end_year="2024",
        ))
        assert resp.series is not None
        assert resp.series.series_id == "CUUR0000SA0"

    def test_has_observations(self, service):
        resp = service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="CUUR0000SA0",
            start_year="2024",
            end_year="2024",
        ))
        assert len(resp.series.observations) == 3

    def test_observation_fields(self, service):
        resp = service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="CUUR0000SA0",
            start_year="2024",
            end_year="2024",
        ))
        obs = resp.series.observations[0]
        assert obs.year == "2024"
        assert obs.period == "M12"
        assert obs.period_name == "December"
        assert obs.value == "315.605"
        assert obs.latest is True

    def test_non_latest_observation(self, service):
        resp = service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="CUUR0000SA0",
            start_year="2024",
            end_year="2024",
        ))
        obs = resp.series.observations[1]
        assert obs.year == "2024"
        assert obs.period == "M11"
        assert obs.period_name == "November"
        assert obs.value == "314.175"
        assert obs.latest is False

    def test_posts_correct_body(self, service, mock_http):
        service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="CUUR0000SA0",
            start_year="2023",
            end_year="2024",
        ))
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None
        assert body is not None
        assert body["seriesid"] == ["CUUR0000SA0"]
        assert body["startyear"] == "2023"
        assert body["endyear"] == "2024"

    def test_empty_result(self, service, mock_http):
        mock_http.post.side_effect = lambda url, json=None, headers=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value=FAKE_EMPTY_RESPONSE),
        )
        resp = service.GetSeriesData(pb.GetSeriesDataRequest(
            series_id="INVALID_SERIES",
        ))
        assert resp.series.series_id == "INVALID_SERIES"
        assert len(resp.series.observations) == 0


class TestGetMultipleSeries:
    def test_returns_multiple_series(self, service):
        resp = service.GetMultipleSeries(pb.GetMultipleSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
            start_year="2024",
            end_year="2024",
        ))
        assert len(resp.series) == 2

    def test_series_ids_match(self, service):
        resp = service.GetMultipleSeries(pb.GetMultipleSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
            start_year="2024",
            end_year="2024",
        ))
        ids = {s.series_id for s in resp.series}
        assert "CUUR0000SA0" in ids
        assert "LNS14000000" in ids

    def test_each_series_has_observations(self, service):
        resp = service.GetMultipleSeries(pb.GetMultipleSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
            start_year="2024",
            end_year="2024",
        ))
        for s in resp.series:
            assert len(s.observations) > 0

    def test_posts_multiple_ids(self, service, mock_http):
        service.GetMultipleSeries(pb.GetMultipleSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
            start_year="2024",
            end_year="2024",
        ))
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body is not None
        assert len(body["seriesid"]) == 2


class TestGetLatestCPI:
    def test_returns_cpi(self, service):
        resp = service.GetLatestCPI(pb.GetLatestCPIRequest())
        assert resp.series_id == "CUUR0000SA0"

    def test_has_observation(self, service):
        resp = service.GetLatestCPI(pb.GetLatestCPIRequest())
        assert resp.observation is not None

    def test_latest_value(self, service):
        resp = service.GetLatestCPI(pb.GetLatestCPIRequest())
        assert resp.observation.value == "315.605"
        assert resp.observation.period_name == "December"
        assert resp.observation.year == "2024"

    def test_fetches_correct_series(self, service, mock_http):
        service.GetLatestCPI(pb.GetLatestCPIRequest())
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body is not None
        assert body["seriesid"] == ["CUUR0000SA0"]


class TestGetLatestUnemployment:
    def test_returns_unemployment(self, service):
        resp = service.GetLatestUnemployment(pb.GetLatestUnemploymentRequest())
        assert resp.series_id == "LNS14000000"

    def test_has_observation(self, service):
        resp = service.GetLatestUnemployment(pb.GetLatestUnemploymentRequest())
        assert resp.observation is not None

    def test_latest_value(self, service):
        resp = service.GetLatestUnemployment(pb.GetLatestUnemploymentRequest())
        assert resp.observation.value == "4.1"
        assert resp.observation.period_name == "December"
        assert resp.observation.year == "2024"

    def test_fetches_correct_series(self, service, mock_http):
        service.GetLatestUnemployment(pb.GetLatestUnemploymentRequest())
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body is not None
        assert body["seriesid"] == ["LNS14000000"]


class TestGetLatestNonfarmPayrolls:
    def test_returns_payrolls(self, service):
        resp = service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        assert resp.series_id == "CES0000000001"

    def test_has_observation(self, service):
        resp = service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        assert resp.observation is not None

    def test_latest_value(self, service):
        resp = service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        assert resp.observation.value == "157233"
        assert resp.observation.period_name == "December"

    def test_preliminary_flag(self, service):
        resp = service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        assert resp.observation.preliminary is True

    def test_footnotes_parsed(self, service):
        resp = service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        assert "Preliminary" in resp.observation.footnotes

    def test_fetches_correct_series(self, service, mock_http):
        service.GetLatestNonfarmPayrolls(pb.GetLatestNonfarmPayrollsRequest())
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body is not None
        assert body["seriesid"] == ["CES0000000001"]


class TestSearchSeries:
    def test_returns_results(self, service):
        resp = service.SearchSeries(pb.SearchSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
        ))
        assert len(resp.results) == 2

    def test_catalog_fields(self, service):
        resp = service.SearchSeries(pb.SearchSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
        ))
        cpi = next(r for r in resp.results if r.series_id == "CUUR0000SA0")
        assert "All items" in cpi.series_title
        assert cpi.survey_abbreviation == "CU"
        assert cpi.seasonally_adjusted is False

    def test_seasonally_adjusted(self, service):
        resp = service.SearchSeries(pb.SearchSeriesRequest(
            series_ids=["CUUR0000SA0", "LNS14000000"],
        ))
        unemp = next(r for r in resp.results if r.series_id == "LNS14000000")
        assert unemp.seasonally_adjusted is True
        assert "Unemployment" in unemp.series_title

    def test_sends_catalog_flag(self, service, mock_http):
        service.SearchSeries(pb.SearchSeriesRequest(
            series_ids=["CUUR0000SA0"],
        ))
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body is not None
        assert body.get("catalog") is True


class TestAPIKeyHandling:
    def test_no_api_key(self, service, mock_http, monkeypatch):
        monkeypatch.delenv("BLS_API_KEY", raising=False)
        service.GetLatestCPI(pb.GetLatestCPIRequest())
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert "registrationkey" not in body

    def test_with_api_key(self, service, mock_http, monkeypatch):
        monkeypatch.setenv("BLS_API_KEY", "test-key-12345")
        service.GetLatestCPI(pb.GetLatestCPIRequest())
        call_kwargs = mock_http.post.call_args
        body = call_kwargs[1]["json"] if "json" in call_kwargs[1] else None
        assert body["registrationkey"] == "test-key-12345"
