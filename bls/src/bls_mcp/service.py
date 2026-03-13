"""BLSService -- wraps the BLS Public Data API v2 into proto RPCs."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from bls_mcp.gen.bls.v1 import bls_pb2 as pb

_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# Key series IDs for prediction markets.
_SERIES_CPI_U = "CUUR0000SA0"
_SERIES_UNEMPLOYMENT = "LNS14000000"
_SERIES_NONFARM_PAYROLLS = "CES0000000001"


def _build_body(
    series_ids: list[str],
    start_year: str = "",
    end_year: str = "",
    catalog: bool = False,
) -> dict:
    """Build the JSON request body for the BLS API."""
    current_year = str(datetime.now().year)
    body: dict[str, Any] = {
        "seriesid": series_ids,
        "startyear": start_year or current_year,
        "endyear": end_year or current_year,
    }
    if catalog:
        body["catalog"] = True
    api_key = os.environ.get("BLS_API_KEY", "")
    if api_key:
        body["registrationkey"] = api_key
    return body


def _parse_observation(raw: dict) -> pb.Observation:
    """Parse a raw BLS data point into an Observation proto message."""
    footnotes = []
    for fn in raw.get("footnotes") or []:
        text = fn.get("text") or fn.get("code") or ""
        if text:
            footnotes.append(text)

    latest = raw.get("latest", "") == "true"
    preliminary = "P" in (raw.get("footnotes") and "".join(
        fn.get("code", "") for fn in raw["footnotes"]
    ) or "")

    return pb.Observation(
        year=raw.get("year", ""),
        period=raw.get("period", ""),
        period_name=raw.get("periodName", ""),
        value=raw.get("value", ""),
        footnotes=footnotes,
        preliminary=preliminary,
        latest=latest,
    )


def _parse_series(raw: dict) -> pb.SeriesData:
    """Parse a raw BLS series JSON into a SeriesData proto message."""
    observations = []
    for d in raw.get("data") or []:
        observations.append(_parse_observation(d))
    return pb.SeriesData(
        series_id=raw.get("seriesID", ""),
        observations=observations,
    )


def _parse_catalog(raw: dict) -> pb.SeriesCatalog:
    """Parse a raw BLS series with catalog info into a SeriesCatalog proto."""
    catalog = raw.get("catalog") or {}
    return pb.SeriesCatalog(
        series_id=raw.get("seriesID", ""),
        series_title=catalog.get("series_title", ""),
        survey_name=catalog.get("survey_name", ""),
        survey_abbreviation=catalog.get("survey_abbreviation", ""),
        seasonally_adjusted=catalog.get("seasonally_adjusted_code", "") == "S",
    )


def _get_latest_observation(series_data: pb.SeriesData) -> pb.Observation | None:
    """Return the latest observation from a series (first in the list)."""
    if series_data.observations:
        return series_data.observations[0]
    return None


class BLSService:
    """Implements BLSService RPCs via the BLS Public Data API v2."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _post(self, body: dict) -> Any:
        resp = self._http.post(
            _BASE_URL,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_series(
        self,
        series_ids: list[str],
        start_year: str = "",
        end_year: str = "",
        catalog: bool = False,
    ) -> dict:
        """Fetch data from the BLS API and return the parsed JSON response."""
        body = _build_body(series_ids, start_year, end_year, catalog)
        return self._post(body)

    def GetSeriesData(self, request: Any, context: Any = None) -> pb.GetSeriesDataResponse:
        raw = self._fetch_series(
            [request.series_id],
            request.start_year,
            request.end_year,
        )
        results = raw.get("Results", {}).get("series", [])
        if results:
            series = _parse_series(results[0])
        else:
            series = pb.SeriesData(series_id=request.series_id)
        return pb.GetSeriesDataResponse(series=series)

    def GetMultipleSeries(self, request: Any, context: Any = None) -> pb.GetMultipleSeriesResponse:
        raw = self._fetch_series(
            list(request.series_ids),
            request.start_year,
            request.end_year,
        )
        series_list = []
        for s in raw.get("Results", {}).get("series", []):
            series_list.append(_parse_series(s))
        return pb.GetMultipleSeriesResponse(series=series_list)

    def GetLatestCPI(self, request: Any, context: Any = None) -> pb.GetLatestCPIResponse:
        raw = self._fetch_series([_SERIES_CPI_U])
        results = raw.get("Results", {}).get("series", [])
        observation = None
        if results:
            series = _parse_series(results[0])
            observation = _get_latest_observation(series)
        return pb.GetLatestCPIResponse(
            series_id=_SERIES_CPI_U,
            observation=observation,
        )

    def GetLatestUnemployment(self, request: Any, context: Any = None) -> pb.GetLatestUnemploymentResponse:
        raw = self._fetch_series([_SERIES_UNEMPLOYMENT])
        results = raw.get("Results", {}).get("series", [])
        observation = None
        if results:
            series = _parse_series(results[0])
            observation = _get_latest_observation(series)
        return pb.GetLatestUnemploymentResponse(
            series_id=_SERIES_UNEMPLOYMENT,
            observation=observation,
        )

    def GetLatestNonfarmPayrolls(self, request: Any, context: Any = None) -> pb.GetLatestNonfarmPayrollsResponse:
        raw = self._fetch_series([_SERIES_NONFARM_PAYROLLS])
        results = raw.get("Results", {}).get("series", [])
        observation = None
        if results:
            series = _parse_series(results[0])
            observation = _get_latest_observation(series)
        return pb.GetLatestNonfarmPayrollsResponse(
            series_id=_SERIES_NONFARM_PAYROLLS,
            observation=observation,
        )

    def SearchSeries(self, request: Any, context: Any = None) -> pb.SearchSeriesResponse:
        raw = self._fetch_series(list(request.series_ids), catalog=True)
        results_list = []
        for s in raw.get("Results", {}).get("series", []):
            results_list.append(_parse_catalog(s))
        return pb.SearchSeriesResponse(results=results_list)
