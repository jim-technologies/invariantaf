"""FREDService — wraps the FRED (Federal Reserve Economic Data) API into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from fred_mcp.gen.fred.v1 import fred_pb2 as pb

_BASE_URL = "https://api.stlouisfed.org/fred"


class FREDService:
    """Implements FREDService RPCs via the FRED API."""

    def __init__(self, *, api_key: str | None = None):
        self._http = httpx.Client(timeout=30)
        self._api_key = api_key or os.environ.get("FRED_API_KEY", "")

    def _get(self, path: str, **params: Any) -> Any:
        params["api_key"] = self._api_key
        params["file_type"] = "json"
        resp = self._http.get(f"{_BASE_URL}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse_series(s: dict) -> pb.Series:
        return pb.Series(
            id=s.get("id", ""),
            title=s.get("title", ""),
            frequency=s.get("frequency", ""),
            units=s.get("units", ""),
            seasonal_adjustment=s.get("seasonal_adjustment", ""),
            last_updated=s.get("last_updated", ""),
            observation_start=s.get("observation_start", ""),
            observation_end=s.get("observation_end", ""),
            notes=s.get("notes", ""),
            popularity=s.get("popularity", 0) or 0,
        )

    def GetSeries(self, request: Any, context: Any = None) -> pb.GetSeriesResponse:
        raw = self._get("series", series_id=request.series_id)
        items = raw.get("seriess", [])
        s = items[0] if items else {}
        return pb.GetSeriesResponse(series=self._parse_series(s))

    def GetSeriesObservations(self, request: Any, context: Any = None) -> pb.GetSeriesObservationsResponse:
        params: dict[str, Any] = {"series_id": request.series_id}
        if request.observation_start:
            params["observation_start"] = request.observation_start
        if request.observation_end:
            params["observation_end"] = request.observation_end
        if request.sort_order:
            params["sort_order"] = request.sort_order
        if request.limit:
            params["limit"] = request.limit
        raw = self._get("series/observations", **params)
        observations = []
        for obs in raw.get("observations", []):
            observations.append(pb.Observation(
                date=obs.get("date", ""),
                value=obs.get("value", ""),
            ))
        return pb.GetSeriesObservationsResponse(observations=observations)

    def SearchSeries(self, request: Any, context: Any = None) -> pb.SearchSeriesResponse:
        params: dict[str, Any] = {"search_text": request.search_text}
        if request.limit:
            params["limit"] = request.limit
        if request.offset:
            params["offset"] = request.offset
        if request.order_by:
            params["order_by"] = request.order_by
        raw = self._get("series/search", **params)
        results = []
        for s in raw.get("seriess", []):
            results.append(self._parse_series(s))
        return pb.SearchSeriesResponse(
            results=results,
            count=raw.get("count", 0),
        )

    def GetCategory(self, request: Any, context: Any = None) -> pb.GetCategoryResponse:
        raw = self._get("category", category_id=request.category_id)
        cats = raw.get("categories", [])
        c = cats[0] if cats else {}
        return pb.GetCategoryResponse(
            category=pb.FREDCategory(
                id=c.get("id", 0),
                name=c.get("name", ""),
                parent_id=c.get("parent_id", 0),
            )
        )

    def GetCategoryChildren(self, request: Any, context: Any = None) -> pb.GetCategoryChildrenResponse:
        raw = self._get("category/children", category_id=request.category_id)
        categories = []
        for c in raw.get("categories", []):
            categories.append(pb.FREDCategory(
                id=c.get("id", 0),
                name=c.get("name", ""),
                parent_id=c.get("parent_id", 0),
            ))
        return pb.GetCategoryChildrenResponse(categories=categories)

    def GetCategorySeries(self, request: Any, context: Any = None) -> pb.GetCategorySeriesResponse:
        params: dict[str, Any] = {"category_id": request.category_id}
        if request.limit:
            params["limit"] = request.limit
        if request.offset:
            params["offset"] = request.offset
        if request.order_by:
            params["order_by"] = request.order_by
        raw = self._get("category/series", **params)
        seriess = []
        for s in raw.get("seriess", []):
            seriess.append(self._parse_series(s))
        return pb.GetCategorySeriesResponse(seriess=seriess)

    def GetRelease(self, request: Any, context: Any = None) -> pb.GetReleaseResponse:
        raw = self._get("release", release_id=request.release_id)
        releases = raw.get("releases", [])
        r = releases[0] if releases else {}
        return pb.GetReleaseResponse(
            release=pb.Release(
                id=r.get("id", 0),
                name=r.get("name", ""),
                link=r.get("link", ""),
                notes=r.get("notes", ""),
                press_release=r.get("press_release", False),
            )
        )

    def GetReleaseDates(self, request: Any, context: Any = None) -> pb.GetReleaseDatesResponse:
        params: dict[str, Any] = {"release_id": request.release_id}
        if request.limit:
            params["limit"] = request.limit
        if request.offset:
            params["offset"] = request.offset
        if request.sort_order:
            params["sort_order"] = request.sort_order
        raw = self._get("release/dates", **params)
        release_dates = []
        for rd in raw.get("release_dates", []):
            release_dates.append(pb.ReleaseDate(
                release_id=rd.get("release_id", 0),
                release_name=rd.get("release_name", ""),
                date=rd.get("date", ""),
            ))
        return pb.GetReleaseDatesResponse(release_dates=release_dates)

    def GetReleaseSeries(self, request: Any, context: Any = None) -> pb.GetReleaseSeriesResponse:
        params: dict[str, Any] = {"release_id": request.release_id}
        if request.limit:
            params["limit"] = request.limit
        if request.offset:
            params["offset"] = request.offset
        if request.order_by:
            params["order_by"] = request.order_by
        raw = self._get("release/series", **params)
        seriess = []
        for s in raw.get("seriess", []):
            seriess.append(self._parse_series(s))
        return pb.GetReleaseSeriesResponse(seriess=seriess)

    def GetSeriesCategories(self, request: Any, context: Any = None) -> pb.GetSeriesCategoriesResponse:
        raw = self._get("series/categories", series_id=request.series_id)
        categories = []
        for c in raw.get("categories", []):
            categories.append(pb.FREDCategory(
                id=c.get("id", 0),
                name=c.get("name", ""),
                parent_id=c.get("parent_id", 0),
            ))
        return pb.GetSeriesCategoriesResponse(categories=categories)
