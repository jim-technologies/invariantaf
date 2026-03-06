"""NASAService — wraps NASA's open APIs into proto RPCs."""

from __future__ import annotations

import os
from typing import Any

import httpx

from nasa_mcp.gen.nasa.v1 import nasa_pb2 as pb

_BASE_URL = "https://api.nasa.gov"
_MARS_PHOTOS_URL = "https://api.nasa.gov/mars-photos/api/v1"
_NEO_URL = "https://api.nasa.gov/neo/rest/v1"
_EPIC_URL = "https://api.nasa.gov/EPIC"
_IMAGES_URL = "https://images-api.nasa.gov"
_DONKI_URL = "https://api.nasa.gov/DONKI"
_TECHTRANSFER_URL = "https://api.nasa.gov/techtransfer"


class NASAService:
    """Implements NASAService RPCs via NASA's open APIs."""

    def __init__(self, *, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("NASA_API_KEY", "DEMO_KEY")
        self._http = httpx.Client(timeout=30)

    def _get(self, url: str, params: dict | None = None) -> Any:
        p = dict(params or {})
        p["api_key"] = self._api_key
        resp = self._http.get(url, params=p)
        resp.raise_for_status()
        return resp.json()

    def _get_no_key(self, url: str, params: dict | None = None) -> Any:
        """GET without API key (for NASA Images API)."""
        resp = self._http.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    def GetAPOD(self, request: Any, context: Any = None) -> pb.GetAPODResponse:
        params = {}
        if request.date:
            params["date"] = request.date
        raw = self._get(f"{_BASE_URL}/planetary/apod", params)
        return pb.GetAPODResponse(entry=pb.APODEntry(
            title=raw.get("title", ""),
            explanation=raw.get("explanation", ""),
            url=raw.get("url", ""),
            hdurl=raw.get("hdurl", ""),
            media_type=raw.get("media_type", ""),
            date=raw.get("date", ""),
            copyright=raw.get("copyright", ""),
        ))

    def GetAPODRange(self, request: Any, context: Any = None) -> pb.GetAPODRangeResponse:
        params = {
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
        raw = self._get(f"{_BASE_URL}/planetary/apod", params)
        resp = pb.GetAPODRangeResponse()
        for item in raw:
            resp.entries.append(pb.APODEntry(
                title=item.get("title", ""),
                explanation=item.get("explanation", ""),
                url=item.get("url", ""),
                hdurl=item.get("hdurl", ""),
                media_type=item.get("media_type", ""),
                date=item.get("date", ""),
                copyright=item.get("copyright", ""),
            ))
        return resp

    def GetMarsPhotos(self, request: Any, context: Any = None) -> pb.GetMarsPhotosResponse:
        rover = request.rover or "curiosity"
        params = {}
        if request.earth_date:
            params["earth_date"] = request.earth_date
        else:
            params["sol"] = request.sol
        if request.camera:
            params["camera"] = request.camera
        raw = self._get(f"{_MARS_PHOTOS_URL}/rovers/{rover}/photos", params)
        resp = pb.GetMarsPhotosResponse()
        for p in raw.get("photos", []):
            cam = p.get("camera", {})
            rover_info = p.get("rover", {})
            resp.photos.append(pb.MarsPhoto(
                id=p.get("id", 0),
                sol=p.get("sol", 0),
                camera_name=cam.get("name", ""),
                camera_full_name=cam.get("full_name", ""),
                img_src=p.get("img_src", ""),
                earth_date=p.get("earth_date", ""),
                rover_name=rover_info.get("name", ""),
            ))
        return resp

    def GetMarsManifest(self, request: Any, context: Any = None) -> pb.GetMarsManifestResponse:
        rover = request.rover or "curiosity"
        raw = self._get(f"{_MARS_PHOTOS_URL}/manifests/{rover}")
        m = raw.get("photo_manifest", {})
        return pb.GetMarsManifestResponse(manifest=pb.RoverManifest(
            name=m.get("name", ""),
            landing_date=m.get("landing_date", ""),
            launch_date=m.get("launch_date", ""),
            status=m.get("status", ""),
            max_sol=m.get("max_sol", 0),
            max_date=m.get("max_date", ""),
            total_photos=m.get("total_photos", 0),
        ))

    def GetNEOs(self, request: Any, context: Any = None) -> pb.GetNEOsResponse:
        params = {}
        if request.start_date:
            params["start_date"] = request.start_date
        if request.end_date:
            params["end_date"] = request.end_date
        raw = self._get(f"{_NEO_URL}/feed", params)
        resp = pb.GetNEOsResponse(
            element_count=raw.get("element_count", 0),
        )
        for date_key, objects in raw.get("near_earth_objects", {}).items():
            for obj in objects:
                diameter = obj.get("estimated_diameter", {}).get("kilometers", {})
                approach = obj.get("close_approach_data", [{}])[0] if obj.get("close_approach_data") else {}
                resp.objects.append(pb.NearEarthObject(
                    id=str(obj.get("id", "")),
                    name=obj.get("name", ""),
                    absolute_magnitude=obj.get("absolute_magnitude_h", 0),
                    estimated_diameter_min_km=diameter.get("estimated_diameter_min", 0),
                    estimated_diameter_max_km=diameter.get("estimated_diameter_max", 0),
                    is_potentially_hazardous=obj.get("is_potentially_hazardous_asteroid", False),
                    close_approach_date=approach.get("close_approach_date", ""),
                    relative_velocity_kmh=float(approach.get("relative_velocity", {}).get("kilometers_per_hour", 0)),
                    miss_distance_km=float(approach.get("miss_distance", {}).get("kilometers", 0)),
                    orbiting_body=approach.get("orbiting_body", ""),
                ))
        return resp

    def GetNEOLookup(self, request: Any, context: Any = None) -> pb.GetNEOLookupResponse:
        raw = self._get(f"{_NEO_URL}/neo/{request.asteroid_id}")
        diameter = raw.get("estimated_diameter", {}).get("kilometers", {})
        approach = raw.get("close_approach_data", [{}])[0] if raw.get("close_approach_data") else {}
        return pb.GetNEOLookupResponse(object=pb.NearEarthObject(
            id=str(raw.get("id", "")),
            name=raw.get("name", ""),
            absolute_magnitude=raw.get("absolute_magnitude_h", 0),
            estimated_diameter_min_km=diameter.get("estimated_diameter_min", 0),
            estimated_diameter_max_km=diameter.get("estimated_diameter_max", 0),
            is_potentially_hazardous=raw.get("is_potentially_hazardous_asteroid", False),
            close_approach_date=approach.get("close_approach_date", ""),
            relative_velocity_kmh=float(approach.get("relative_velocity", {}).get("kilometers_per_hour", 0)),
            miss_distance_km=float(approach.get("miss_distance", {}).get("kilometers", 0)),
            orbiting_body=approach.get("orbiting_body", ""),
        ))

    def GetEPIC(self, request: Any, context: Any = None) -> pb.GetEPICResponse:
        if request.date:
            url = f"{_EPIC_URL}/api/natural/date/{request.date}"
        else:
            url = f"{_EPIC_URL}/api/natural"
        raw = self._get(url)
        resp = pb.GetEPICResponse()
        for item in raw:
            coords = item.get("centroid_coordinates", {})
            resp.images.append(pb.EPICImage(
                identifier=item.get("identifier", ""),
                caption=item.get("caption", ""),
                image=item.get("image", ""),
                date=item.get("date", ""),
                centroid_lat=coords.get("lat", 0),
                centroid_lon=coords.get("lon", 0),
            ))
        return resp

    def SearchNASAImages(self, request: Any, context: Any = None) -> pb.SearchNASAImagesResponse:
        params = {"q": request.query}
        if request.media_type:
            params["media_type"] = request.media_type
        raw = self._get_no_key(f"{_IMAGES_URL}/search", params)
        resp = pb.SearchNASAImagesResponse()
        for item in raw.get("collection", {}).get("items", []):
            data = item.get("data", [{}])[0] if item.get("data") else {}
            links = item.get("links", [{}])
            preview = links[0].get("href", "") if links else ""
            resp.items.append(pb.NASAImageItem(
                nasa_id=data.get("nasa_id", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                media_type=data.get("media_type", ""),
                date_created=data.get("date_created", ""),
                preview_url=preview,
            ))
        return resp

    def GetDonki(self, request: Any, context: Any = None) -> pb.GetDonkiResponse:
        params = {}
        if request.start_date:
            params["startDate"] = request.start_date
        if request.end_date:
            params["endDate"] = request.end_date
        raw = self._get(f"{_DONKI_URL}/CME", params)
        resp = pb.GetDonkiResponse()
        for event in raw:
            instruments = []
            for inst in event.get("instruments", []) or []:
                instruments.append(inst.get("displayName", ""))
            resp.events.append(pb.CMEEvent(
                activity_id=event.get("activityID", ""),
                start_time=event.get("startTime", ""),
                source_location=event.get("sourceLocation", ""),
                link=event.get("link", ""),
                instruments=instruments,
            ))
        return resp

    def GetTechTransfer(self, request: Any, context: Any = None) -> pb.GetTechTransferResponse:
        raw = self._get(f"{_TECHTRANSFER_URL}/patent/", params={"engine": "", "query": request.query})
        resp = pb.GetTechTransferResponse()
        results = raw.get("results", [])
        for item in results:
            # TechTransfer API returns arrays of fields per result.
            if isinstance(item, list) and len(item) >= 3:
                resp.items.append(pb.TechTransferItem(
                    title=str(item[2]) if len(item) > 2 else "",
                    description=str(item[3]) if len(item) > 3 else "",
                    patent_number=str(item[0]) if len(item) > 0 else "",
                    center=str(item[9]) if len(item) > 9 else "",
                    category=str(item[5]) if len(item) > 5 else "",
                ))
            elif isinstance(item, dict):
                resp.items.append(pb.TechTransferItem(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    patent_number=item.get("patent_number", ""),
                    center=item.get("center", ""),
                    category=item.get("category", ""),
                ))
        return resp
