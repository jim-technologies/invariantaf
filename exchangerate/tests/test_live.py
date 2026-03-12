"""Live integration tests for Exchange Rate API (Frankfurter) -- hits the real API.

Run with:
    EXCHANGERATE_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) Frankfurter API endpoints.
No API key or authentication is required.
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
    os.getenv("EXCHANGERATE_RUN_LIVE_TESTS") != "1",
    reason="Set EXCHANGERATE_RUN_LIVE_TESTS=1 to run live Exchange Rate API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from exchangerate_mcp.service import ExchangeRateService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-exchangerate-live", version="0.0.1"
    )
    servicer = ExchangeRateService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Latest Rates ---


class TestLiveLatestRates:
    def test_get_latest_all(self, live_server):
        result = live_server._cli(["ExchangeRateService", "GetLatestAll"])
        assert "rates" in result
        rates = result["rates"]
        assert isinstance(rates, dict)
        assert len(rates) > 0
        assert result.get("base") == "EUR"
        assert "date" in result
        # Common currencies should be present
        assert "USD" in rates

    def test_get_latest_rates_with_base(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetLatestRates",
                "-r",
                json.dumps({"base": "USD"}),
            ]
        )
        assert "rates" in result
        assert result.get("base") == "USD"
        rates = result["rates"]
        assert isinstance(rates, dict)
        assert len(rates) > 0
        assert "EUR" in rates

    def test_get_latest_for_currencies(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetLatestForCurrencies",
                "-r",
                json.dumps({"base": "EUR", "symbols": "USD,GBP,JPY"}),
            ]
        )
        assert "rates" in result
        rates = result["rates"]
        assert isinstance(rates, dict)
        # Should only contain the requested currencies
        assert "USD" in rates
        assert "GBP" in rates
        assert "JPY" in rates


# --- Currencies ---


class TestLiveCurrencies:
    def test_list_currencies(self, live_server):
        result = live_server._cli(["ExchangeRateService", "ListCurrencies"])
        assert "currencies" in result
        currencies = result["currencies"]
        assert isinstance(currencies, dict)
        assert len(currencies) > 0
        assert "USD" in currencies
        assert "EUR" in currencies
        # Values should be full names
        assert isinstance(currencies["USD"], str)
        assert len(currencies["USD"]) > 0


# --- Conversion ---


class TestLiveConvert:
    def test_convert(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "Convert",
                "-r",
                json.dumps({"from": "USD", "to": "EUR", "amount": 100}),
            ]
        )
        assert "rates" in result
        rates = result["rates"]
        assert "EUR" in rates
        assert isinstance(rates["EUR"], (int, float))
        assert rates["EUR"] > 0
        assert result.get("amount") == 100.0

    def test_convert_historical(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "ConvertHistorical",
                "-r",
                json.dumps({
                    "date": "2024-01-15",
                    "from": "USD",
                    "to": "EUR",
                    "amount": 50,
                }),
            ]
        )
        assert "rates" in result
        rates = result["rates"]
        assert "EUR" in rates
        assert isinstance(rates["EUR"], (int, float))
        assert rates["EUR"] > 0
        assert result.get("amount") == 50.0


# --- Historical Rates ---


class TestLiveHistoricalRates:
    def test_get_historical_rates(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetHistoricalRates",
                "-r",
                json.dumps({"date": "2024-01-15", "base": "EUR"}),
            ]
        )
        assert "rates" in result
        rates = result["rates"]
        assert isinstance(rates, dict)
        assert len(rates) > 0
        assert "USD" in rates
        assert result.get("date") == "2024-01-15"

    def test_get_historical_for_currencies(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetHistoricalForCurrencies",
                "-r",
                json.dumps({
                    "date": "2024-01-15",
                    "base": "EUR",
                    "symbols": "USD,GBP",
                }),
            ]
        )
        assert "rates" in result
        rates = result["rates"]
        assert "USD" in rates
        assert "GBP" in rates


# --- Time Series ---


class TestLiveTimeSeries:
    def test_get_time_series(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetTimeSeries",
                "-r",
                json.dumps({
                    "start_date": "2024-01-10",
                    "end_date": "2024-01-15",
                    "base": "EUR",
                    "symbols": "USD,GBP",
                }),
            ]
        )
        key = "dailyRates" if "dailyRates" in result else "daily_rates"
        assert key in result
        daily_rates = result[key]
        assert isinstance(daily_rates, list)
        assert len(daily_rates) > 0
        # Each entry should have date and rates
        day = daily_rates[0]
        assert "date" in day
        assert "rates" in day

    def test_get_time_series_for_pair(self, live_server):
        result = live_server._cli(
            [
                "ExchangeRateService",
                "GetTimeSeriesForPair",
                "-r",
                json.dumps({
                    "start_date": "2024-01-10",
                    "end_date": "2024-01-15",
                    "from": "USD",
                    "to": "EUR",
                }),
            ]
        )
        key = "dailyRates" if "dailyRates" in result else "daily_rates"
        assert key in result
        daily_rates = result[key]
        assert isinstance(daily_rates, list)
        assert len(daily_rates) > 0
