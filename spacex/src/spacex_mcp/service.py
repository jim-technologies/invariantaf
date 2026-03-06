"""SpaceXService -- wraps the SpaceX v4 REST API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from spacex_mcp.gen.spacex.v1 import spacex_pb2 as pb

_BASE_URL = "https://api.spacexdata.com"


class SpaceXService:
    """Implements SpaceXService RPCs via the public SpaceX v4 API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30, headers={"Accept": "application/json"})

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_launch(raw: dict) -> pb.Launch:
        links = raw.get("links") or {}
        patch = links.get("patch") or {}
        return pb.Launch(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            date_utc=raw.get("date_utc", ""),
            date_unix=raw.get("date_unix") or 0,
            success=bool(raw.get("success")),
            flight_number=raw.get("flight_number") or 0,
            rocket=raw.get("rocket", ""),
            details=raw.get("details") or "",
            upcoming=raw.get("upcoming", False),
            launchpad=raw.get("launchpad", ""),
            payloads=raw.get("payloads") or [],
            crew=[c.get("crew", c) if isinstance(c, dict) else c for c in (raw.get("crew") or [])],
            patch_small=patch.get("small") or "",
            patch_large=patch.get("large") or "",
            webcast=links.get("webcast") or "",
            wikipedia=links.get("wikipedia") or "",
            article=links.get("article") or "",
        )

    @staticmethod
    def _parse_rocket(raw: dict) -> pb.Rocket:
        height = raw.get("height") or {}
        diameter = raw.get("diameter") or {}
        mass = raw.get("mass") or {}
        engines = raw.get("engines") or {}
        payload_weights = raw.get("payload_weights") or []
        leo_kg = 0.0
        gto_kg = 0.0
        for pw in payload_weights:
            if pw.get("id") == "leo":
                leo_kg = pw.get("kg") or 0.0
            elif pw.get("id") == "gto":
                gto_kg = pw.get("kg") or 0.0
        return pb.Rocket(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            type=raw.get("type", ""),
            active=raw.get("active", False),
            stages=raw.get("stages") or 0,
            boosters=raw.get("boosters") or 0,
            cost_per_launch=raw.get("cost_per_launch") or 0,
            first_flight=raw.get("first_flight", ""),
            country=raw.get("country", ""),
            company=raw.get("company", ""),
            height_meters=height.get("meters") or 0.0,
            diameter_meters=diameter.get("meters") or 0.0,
            mass_kg=mass.get("kg") or 0.0,
            payload_weight_leo_kg=leo_kg,
            payload_weight_gto_kg=gto_kg,
            engines_number=engines.get("number") or 0,
            engine_type=engines.get("type", ""),
            engine_propellant_1=engines.get("propellant_1", ""),
            engine_propellant_2=engines.get("propellant_2", ""),
            description=raw.get("description", ""),
            wikipedia=raw.get("wikipedia", ""),
            success_rate_pct=raw.get("success_rate_pct") or 0,
        )

    @staticmethod
    def _parse_crew(raw: dict) -> pb.CrewMember:
        return pb.CrewMember(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            status=raw.get("status", ""),
            agency=raw.get("agency", ""),
            image=raw.get("image") or "",
            wikipedia=raw.get("wikipedia") or "",
            launches=raw.get("launches") or [],
        )

    @staticmethod
    def _parse_starlink(raw: dict) -> pb.StarlinkSatellite:
        return pb.StarlinkSatellite(
            id=raw.get("id", ""),
            version=raw.get("version") or "",
            launch=raw.get("launch") or "",
            height_km=raw.get("height_km") or 0.0,
            latitude=raw.get("latitude") or 0.0,
            longitude=raw.get("longitude") or 0.0,
            velocity_kms=raw.get("velocity_kms") or 0.0,
        )

    @staticmethod
    def _parse_launchpad(raw: dict) -> pb.Launchpad:
        return pb.Launchpad(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            full_name=raw.get("full_name", ""),
            locality=raw.get("locality", ""),
            region=raw.get("region", ""),
            latitude=raw.get("latitude") or 0.0,
            longitude=raw.get("longitude") or 0.0,
            launch_attempts=raw.get("launch_attempts") or 0,
            launch_successes=raw.get("launch_successes") or 0,
            status=raw.get("status", ""),
        )

    # ------------------------------------------------------------------
    # RPCs
    # ------------------------------------------------------------------

    def GetLatestLaunch(self, request: Any, context: Any = None) -> pb.GetLatestLaunchResponse:
        raw = self._get("/v4/launches/latest")
        return pb.GetLatestLaunchResponse(launch=self._parse_launch(raw))

    def GetLaunches(self, request: Any, context: Any = None) -> pb.GetLaunchesResponse:
        raw = self._get("/v4/launches")
        return pb.GetLaunchesResponse(
            launches=[self._parse_launch(launch) for launch in raw],
        )

    def GetLaunch(self, request: Any, context: Any = None) -> pb.GetLaunchResponse:
        raw = self._get(f"/v4/launches/{request.id}")
        return pb.GetLaunchResponse(launch=self._parse_launch(raw))

    def GetRockets(self, request: Any, context: Any = None) -> pb.GetRocketsResponse:
        raw = self._get("/v4/rockets")
        return pb.GetRocketsResponse(
            rockets=[self._parse_rocket(r) for r in raw],
        )

    def GetRocket(self, request: Any, context: Any = None) -> pb.GetRocketResponse:
        raw = self._get(f"/v4/rockets/{request.id}")
        return pb.GetRocketResponse(rocket=self._parse_rocket(raw))

    def GetCrew(self, request: Any, context: Any = None) -> pb.GetCrewResponse:
        raw = self._get("/v4/crew")
        return pb.GetCrewResponse(
            crew=[self._parse_crew(c) for c in raw],
        )

    def GetStarlink(self, request: Any, context: Any = None) -> pb.GetStarlinkResponse:
        raw = self._get("/v4/starlink")
        return pb.GetStarlinkResponse(
            satellites=[self._parse_starlink(s) for s in raw],
        )

    def GetLaunchpads(self, request: Any, context: Any = None) -> pb.GetLaunchpadsResponse:
        raw = self._get("/v4/launchpads")
        return pb.GetLaunchpadsResponse(
            launchpads=[self._parse_launchpad(lp) for lp in raw],
        )

    def GetCompanyInfo(self, request: Any, context: Any = None) -> pb.GetCompanyInfoResponse:
        raw = self._get("/v4/company")
        hq = raw.get("headquarters") or {}
        links = raw.get("links") or {}
        return pb.GetCompanyInfoResponse(
            name=raw.get("name", ""),
            founder=raw.get("founder", ""),
            founded=raw.get("founded") or 0,
            employees=raw.get("employees") or 0,
            vehicles=raw.get("vehicles") or 0,
            launch_sites=raw.get("launch_sites") or 0,
            test_sites=raw.get("test_sites") or 0,
            ceo=raw.get("ceo", ""),
            cto=raw.get("cto", ""),
            coo=raw.get("coo", ""),
            cto_propulsion=raw.get("cto_propulsion", ""),
            valuation=raw.get("valuation") or 0,
            summary=raw.get("summary", ""),
            headquarters_city=hq.get("city", ""),
            headquarters_state=hq.get("state", ""),
            website=links.get("website", ""),
            flickr=links.get("flickr", ""),
            twitter=links.get("twitter", ""),
            elon_twitter=links.get("elon_twitter", ""),
        )

    def GetUpcomingLaunches(self, request: Any, context: Any = None) -> pb.GetUpcomingLaunchesResponse:
        raw = self._get("/v4/launches/upcoming")
        return pb.GetUpcomingLaunchesResponse(
            launches=[self._parse_launch(launch) for launch in raw],
        )
