"""Unit tests — every ExchangeRateService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from exchangerate_mcp.gen.exchangerate.v1 import exchangerate_pb2 as pb
from tests.conftest import (
    FAKE_CONVERT,
    FAKE_CONVERT_HISTORICAL,
    FAKE_CURRENCIES,
    FAKE_HISTORICAL,
    FAKE_HISTORICAL_FILTERED,
    FAKE_LATEST,
    FAKE_LATEST_FILTERED,
    FAKE_TIME_SERIES,
    FAKE_TIME_SERIES_PAIR,
)


class TestGetLatestRates:
    def test_returns_rates(self, service):
        resp = service.GetLatestRates(pb.GetLatestRatesRequest(base="EUR"))
        assert resp.base == "EUR"
        assert resp.date == "2025-01-15"
        assert len(resp.rates) == 5
        assert "USD" in resp.rates
        assert "GBP" in resp.rates

    def test_usd_rate(self, service):
        resp = service.GetLatestRates(pb.GetLatestRatesRequest(base="EUR"))
        assert resp.rates["USD"] == pytest.approx(1.0305)

    def test_default_base(self, service, mock_http):
        service.GetLatestRates(pb.GetLatestRatesRequest())
        call_args = mock_http.get.call_args
        # No base param should be passed when base is empty
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "/latest" in url

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"base": "EUR", "date": "2025-01-15", "rates": {}})
        )
        resp = service.GetLatestRates(pb.GetLatestRatesRequest())
        assert len(resp.rates) == 0


class TestGetLatestForCurrencies:
    def test_returns_filtered_rates(self, service):
        resp = service.GetLatestForCurrencies(pb.GetLatestForCurrenciesRequest(
            base="EUR", symbols="USD,GBP",
        ))
        assert resp.base == "EUR"
        assert len(resp.rates) == 2
        assert "USD" in resp.rates
        assert "GBP" in resp.rates

    def test_symbols_passed(self, service, mock_http):
        service.GetLatestForCurrencies(pb.GetLatestForCurrenciesRequest(
            symbols="USD,GBP",
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or (call_args[0][1] if len(call_args[0]) > 1 else {})
        assert params.get("symbols") == "USD,GBP"


class TestConvert:
    def test_converts_amount(self, service):
        req = pb.ConvertRequest()
        setattr(req, "from", "USD")
        req.to = "EUR"
        req.amount = 100.0
        resp = service.Convert(req)
        assert resp.base == "USD"
        assert resp.amount == 100.0
        assert "EUR" in resp.rates
        assert resp.rates["EUR"] == pytest.approx(97.04)

    def test_date_present(self, service):
        req = pb.ConvertRequest()
        setattr(req, "from", "USD")
        req.to = "EUR"
        req.amount = 100.0
        resp = service.Convert(req)
        assert resp.date == "2025-01-15"

    def test_params_sent(self, service, mock_http):
        req = pb.ConvertRequest()
        setattr(req, "from", "USD")
        req.to = "EUR"
        req.amount = 100.0
        service.Convert(req)
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or {}
        assert params.get("base") == "USD"
        assert params.get("symbols") == "EUR"
        assert params.get("amount") == 100.0


class TestGetHistoricalRates:
    def test_returns_historical(self, service):
        resp = service.GetHistoricalRates(pb.GetHistoricalRatesRequest(
            date="2024-01-15",
        ))
        assert resp.base == "EUR"
        assert resp.date == "2024-01-15"
        assert "USD" in resp.rates
        assert resp.rates["USD"] == pytest.approx(1.0891)

    def test_multiple_currencies(self, service):
        resp = service.GetHistoricalRates(pb.GetHistoricalRatesRequest(
            date="2024-01-15",
        ))
        assert "GBP" in resp.rates
        assert "JPY" in resp.rates


class TestGetTimeSeries:
    def test_returns_daily_rates(self, service):
        resp = service.GetTimeSeries(pb.GetTimeSeriesRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        ))
        assert resp.base == "EUR"
        assert resp.start_date == "2025-01-10"
        assert resp.end_date == "2025-01-15"
        assert len(resp.daily_rates) == 4

    def test_dates_sorted(self, service):
        resp = service.GetTimeSeries(pb.GetTimeSeriesRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        ))
        dates = [d.date for d in resp.daily_rates]
        assert dates == sorted(dates)

    def test_rates_in_daily(self, service):
        resp = service.GetTimeSeries(pb.GetTimeSeriesRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        ))
        first = resp.daily_rates[0]
        assert first.date == "2025-01-10"
        assert "USD" in first.rates
        assert first.rates["USD"] == pytest.approx(1.0290)

    def test_with_symbols(self, service, mock_http):
        service.GetTimeSeries(pb.GetTimeSeriesRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
            symbols="USD,GBP",
        ))
        call_args = mock_http.get.call_args
        params = call_args[1].get("params") or {}
        assert params.get("symbols") == "USD,GBP"


class TestListCurrencies:
    def test_returns_currencies(self, service):
        resp = service.ListCurrencies(pb.ListCurrenciesRequest())
        assert len(resp.currencies) == 10
        assert resp.currencies["USD"] == "United States Dollar"
        assert resp.currencies["EUR"] == "Euro"
        assert resp.currencies["JPY"] == "Japanese Yen"

    def test_all_keys_present(self, service):
        resp = service.ListCurrencies(pb.ListCurrenciesRequest())
        for code in FAKE_CURRENCIES:
            assert code in resp.currencies


class TestGetHistoricalForCurrencies:
    def test_returns_filtered_historical(self, service):
        resp = service.GetHistoricalForCurrencies(pb.GetHistoricalForCurrenciesRequest(
            date="2024-01-15",
            symbols="USD,GBP",
        ))
        assert resp.base == "EUR"
        assert resp.date == "2024-01-15"
        assert len(resp.rates) == 2
        assert "USD" in resp.rates
        assert "GBP" in resp.rates

    def test_rate_values(self, service):
        resp = service.GetHistoricalForCurrencies(pb.GetHistoricalForCurrenciesRequest(
            date="2024-01-15",
            symbols="USD,GBP",
        ))
        assert resp.rates["USD"] == pytest.approx(1.0891)
        assert resp.rates["GBP"] == pytest.approx(0.8561)


class TestConvertHistorical:
    def test_converts_at_historical_rate(self, service):
        req = pb.ConvertHistoricalRequest(date="2024-01-15")
        setattr(req, "from", "USD")
        req.to = "EUR"
        req.amount = 50.0
        resp = service.ConvertHistorical(req)
        assert resp.base == "USD"
        assert resp.date == "2024-01-15"
        assert resp.amount == 50.0
        assert "EUR" in resp.rates
        assert resp.rates["EUR"] == pytest.approx(45.91)

    def test_params_sent(self, service, mock_http):
        req = pb.ConvertHistoricalRequest(date="2024-01-15")
        setattr(req, "from", "USD")
        req.to = "EUR"
        req.amount = 50.0
        service.ConvertHistorical(req)
        call_args = mock_http.get.call_args
        url = call_args[0][0] if call_args[0] else ""
        assert "2024-01-15" in url
        params = call_args[1].get("params") or {}
        assert params.get("base") == "USD"
        assert params.get("symbols") == "EUR"
        assert params.get("amount") == 50.0


class TestGetTimeSeriesForPair:
    def test_returns_pair_series(self, service):
        req = pb.GetTimeSeriesForPairRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        )
        setattr(req, "from", "USD")
        req.to = "EUR"
        resp = service.GetTimeSeriesForPair(req)
        assert resp.base == "USD"
        assert len(resp.daily_rates) == 4

    def test_dates_sorted(self, service):
        req = pb.GetTimeSeriesForPairRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        )
        setattr(req, "from", "USD")
        req.to = "EUR"
        resp = service.GetTimeSeriesForPair(req)
        dates = [d.date for d in resp.daily_rates]
        assert dates == sorted(dates)

    def test_single_currency_in_rates(self, service):
        req = pb.GetTimeSeriesForPairRequest(
            start_date="2025-01-10",
            end_date="2025-01-15",
        )
        setattr(req, "from", "USD")
        req.to = "EUR"
        resp = service.GetTimeSeriesForPair(req)
        for day in resp.daily_rates:
            assert "EUR" in day.rates
            assert len(day.rates) == 1


class TestGetLatestAll:
    def test_returns_all_rates(self, service):
        resp = service.GetLatestAll(pb.GetLatestAllRequest())
        assert resp.base == "EUR"
        assert resp.date == "2025-01-15"
        assert len(resp.rates) == 5

    def test_rate_values(self, service):
        resp = service.GetLatestAll(pb.GetLatestAllRequest())
        assert resp.rates["USD"] == pytest.approx(1.0305)
        assert resp.rates["GBP"] == pytest.approx(0.8451)
        assert resp.rates["JPY"] == pytest.approx(161.52)
