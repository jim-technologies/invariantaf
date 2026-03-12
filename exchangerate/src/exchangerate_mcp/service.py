"""ExchangeRateService — wraps the Frankfurter API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from exchangerate_mcp.gen.exchangerate.v1 import exchangerate_pb2 as pb

_BASE_URL = "https://api.frankfurter.app"


class ExchangeRateService:
    """Implements ExchangeRateService RPCs via the free Frankfurter API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def GetLatestRates(self, request: Any, context: Any = None) -> pb.GetLatestRatesResponse:
        params = {}
        if request.base:
            params["base"] = request.base
        raw = self._get("/latest", params=params or None)
        return pb.GetLatestRatesResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
        )

    def GetLatestForCurrencies(self, request: Any, context: Any = None) -> pb.GetLatestForCurrenciesResponse:
        params = {}
        if request.base:
            params["base"] = request.base
        if request.symbols:
            params["symbols"] = request.symbols
        raw = self._get("/latest", params=params or None)
        return pb.GetLatestForCurrenciesResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
        )

    def Convert(self, request: Any, context: Any = None) -> pb.ConvertResponse:
        params = {}
        if getattr(request, "from", "") or request.DESCRIPTOR.fields_by_name["from"].number:
            # Proto field "from" is a reserved keyword — access via getattr.
            from_currency = getattr(request, "from", "") or "EUR"
            params["base"] = from_currency
        if request.to:
            params["symbols"] = request.to
        if request.amount:
            params["amount"] = request.amount
        raw = self._get("/latest", params=params)
        return pb.ConvertResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
            amount=raw.get("amount", 0),
        )

    def GetHistoricalRates(self, request: Any, context: Any = None) -> pb.GetHistoricalRatesResponse:
        date = request.date or "latest"
        params = {}
        if request.base:
            params["base"] = request.base
        raw = self._get(f"/{date}", params=params or None)
        return pb.GetHistoricalRatesResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
        )

    def GetTimeSeries(self, request: Any, context: Any = None) -> pb.GetTimeSeriesResponse:
        path = f"/{request.start_date}..{request.end_date}"
        params = {}
        if request.base:
            params["base"] = request.base
        if request.symbols:
            params["symbols"] = request.symbols
        raw = self._get(path, params=params or None)
        daily = []
        for date_str in sorted(raw.get("rates", {}).keys()):
            daily.append(pb.DailyRates(
                date=date_str,
                rates=raw["rates"][date_str],
            ))
        return pb.GetTimeSeriesResponse(
            base=raw.get("base", ""),
            start_date=raw.get("start_date", ""),
            end_date=raw.get("end_date", ""),
            daily_rates=daily,
        )

    def ListCurrencies(self, request: Any, context: Any = None) -> pb.ListCurrenciesResponse:
        raw = self._get("/currencies")
        return pb.ListCurrenciesResponse(currencies=raw)

    def GetHistoricalForCurrencies(self, request: Any, context: Any = None) -> pb.GetHistoricalForCurrenciesResponse:
        date = request.date or "latest"
        params = {}
        if request.base:
            params["base"] = request.base
        if request.symbols:
            params["symbols"] = request.symbols
        raw = self._get(f"/{date}", params=params or None)
        return pb.GetHistoricalForCurrenciesResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
        )

    def ConvertHistorical(self, request: Any, context: Any = None) -> pb.ConvertHistoricalResponse:
        date = request.date or "latest"
        from_currency = getattr(request, "from", "") or "EUR"
        params = {
            "base": from_currency,
        }
        if request.to:
            params["symbols"] = request.to
        if request.amount:
            params["amount"] = request.amount
        raw = self._get(f"/{date}", params=params)
        return pb.ConvertHistoricalResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
            amount=raw.get("amount", 0),
        )

    def GetTimeSeriesForPair(self, request: Any, context: Any = None) -> pb.GetTimeSeriesForPairResponse:
        path = f"/{request.start_date}..{request.end_date}"
        from_currency = getattr(request, "from", "") or "EUR"
        params = {"base": from_currency}
        if request.to:
            params["symbols"] = request.to
        raw = self._get(path, params=params)
        daily = []
        for date_str in sorted(raw.get("rates", {}).keys()):
            daily.append(pb.DailyRates(
                date=date_str,
                rates=raw["rates"][date_str],
            ))
        return pb.GetTimeSeriesForPairResponse(
            base=raw.get("base", ""),
            start_date=raw.get("start_date", ""),
            end_date=raw.get("end_date", ""),
            daily_rates=daily,
        )

    def GetLatestAll(self, request: Any, context: Any = None) -> pb.GetLatestAllResponse:
        raw = self._get("/latest")
        return pb.GetLatestAllResponse(
            base=raw.get("base", ""),
            date=raw.get("date", ""),
            rates=raw.get("rates", {}),
        )
