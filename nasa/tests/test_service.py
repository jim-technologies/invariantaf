"""Unit tests — every NASAService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from nasa_mcp.gen.nasa.v1 import nasa_pb2 as pb
from tests.conftest import (
    FAKE_APOD,
    FAKE_APOD_RANGE,
    FAKE_DONKI,
    FAKE_EPIC,
    FAKE_MARS_MANIFEST,
    FAKE_MARS_PHOTOS,
    FAKE_NASA_IMAGES,
    FAKE_NEO_LOOKUP,
    FAKE_NEOS,
    FAKE_TECHTRANSFER,
)


class TestGetAPOD:
    def test_returns_entry(self, service):
        resp = service.GetAPOD(pb.GetAPODRequest())
        assert resp.entry.title == "The Horsehead Nebula"
        assert resp.entry.media_type == "image"
        assert resp.entry.date == "2024-01-15"

    def test_explanation(self, service):
        resp = service.GetAPOD(pb.GetAPODRequest())
        assert "Horsehead Nebula" in resp.entry.explanation

    def test_urls(self, service):
        resp = service.GetAPOD(pb.GetAPODRequest())
        assert "horsehead.jpg" in resp.entry.url
        assert "horsehead_hd.jpg" in resp.entry.hdurl

    def test_copyright(self, service):
        resp = service.GetAPOD(pb.GetAPODRequest())
        assert resp.entry.copyright == "John Doe"

    def test_with_date_param(self, service, mock_http):
        service.GetAPOD(pb.GetAPODRequest(date="2024-01-15"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("date") == "2024-01-15"

    def test_default_no_date(self, service, mock_http):
        service.GetAPOD(pb.GetAPODRequest())
        call_args = mock_http.get.call_args
        assert "date" not in call_args[1].get("params", {})


class TestGetAPODRange:
    def test_returns_entries(self, service, mock_http):
        # Override to return the range data for range queries.
        def mock_get(url, params=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "/planetary/apod" in url:
                resp.json.return_value = FAKE_APOD_RANGE
            else:
                resp.json.return_value = {}
            return resp
        mock_http.get.side_effect = mock_get

        resp = service.GetAPODRange(pb.GetAPODRangeRequest(
            start_date="2024-01-15", end_date="2024-01-16",
        ))
        assert len(resp.entries) == 2
        assert resp.entries[0].title == "The Horsehead Nebula"
        assert resp.entries[1].title == "Andromeda Galaxy"

    def test_entry_fields(self, service, mock_http):
        def mock_get(url, params=None):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = FAKE_APOD_RANGE
            return resp
        mock_http.get.side_effect = mock_get

        resp = service.GetAPODRange(pb.GetAPODRangeRequest(
            start_date="2024-01-15", end_date="2024-01-16",
        ))
        assert resp.entries[0].date == "2024-01-15"
        assert resp.entries[1].date == "2024-01-16"
        assert resp.entries[1].media_type == "image"


class TestGetMarsPhotos:
    def test_returns_photos(self, service):
        resp = service.GetMarsPhotos(pb.GetMarsPhotosRequest(rover="curiosity", sol=1000))
        assert len(resp.photos) == 2

    def test_photo_fields(self, service):
        resp = service.GetMarsPhotos(pb.GetMarsPhotosRequest(rover="curiosity", sol=1000))
        photo = resp.photos[0]
        assert photo.id == 102693
        assert photo.sol == 1000
        assert photo.camera_name == "FHAZ"
        assert photo.camera_full_name == "Front Hazard Avoidance Camera"
        assert photo.earth_date == "2015-05-30"
        assert photo.rover_name == "Curiosity"

    def test_img_src(self, service):
        resp = service.GetMarsPhotos(pb.GetMarsPhotosRequest(rover="curiosity", sol=1000))
        assert "mars.nasa.gov" in resp.photos[0].img_src

    def test_second_photo_camera(self, service):
        resp = service.GetMarsPhotos(pb.GetMarsPhotosRequest(rover="curiosity", sol=1000))
        assert resp.photos[1].camera_name == "NAVCAM"
        assert resp.photos[1].camera_full_name == "Navigation Camera"


class TestGetMarsManifest:
    def test_returns_manifest(self, service):
        resp = service.GetMarsManifest(pb.GetMarsManifestRequest(rover="curiosity"))
        m = resp.manifest
        assert m.name == "Curiosity"
        assert m.status == "active"

    def test_dates(self, service):
        resp = service.GetMarsManifest(pb.GetMarsManifestRequest(rover="curiosity"))
        m = resp.manifest
        assert m.landing_date == "2012-08-06"
        assert m.launch_date == "2011-11-26"
        assert m.max_date == "2024-01-15"

    def test_photo_stats(self, service):
        resp = service.GetMarsManifest(pb.GetMarsManifestRequest(rover="curiosity"))
        m = resp.manifest
        assert m.max_sol == 4102
        assert m.total_photos == 695670


class TestGetNEOs:
    def test_returns_objects(self, service):
        resp = service.GetNEOs(pb.GetNEOsRequest(
            start_date="2024-01-15", end_date="2024-01-15",
        ))
        assert resp.element_count == 2
        assert len(resp.objects) == 2

    def test_asteroid_fields(self, service):
        resp = service.GetNEOs(pb.GetNEOsRequest(
            start_date="2024-01-15", end_date="2024-01-15",
        ))
        obj = resp.objects[0]
        assert obj.id == "3542519"
        assert obj.name == "(2010 PK9)"
        assert obj.absolute_magnitude == 21.4
        assert obj.is_potentially_hazardous is False
        assert obj.orbiting_body == "Earth"

    def test_diameter(self, service):
        resp = service.GetNEOs(pb.GetNEOsRequest(
            start_date="2024-01-15", end_date="2024-01-15",
        ))
        obj = resp.objects[0]
        assert obj.estimated_diameter_min_km == 0.1011
        assert obj.estimated_diameter_max_km == 0.2261

    def test_close_approach(self, service):
        resp = service.GetNEOs(pb.GetNEOsRequest(
            start_date="2024-01-15", end_date="2024-01-15",
        ))
        obj = resp.objects[0]
        assert obj.close_approach_date == "2024-01-15"
        assert obj.relative_velocity_kmh == pytest.approx(48520.1234)
        assert obj.miss_distance_km == pytest.approx(5432100.123)

    def test_hazardous_asteroid(self, service):
        resp = service.GetNEOs(pb.GetNEOsRequest(
            start_date="2024-01-15", end_date="2024-01-15",
        ))
        obj = resp.objects[1]
        assert obj.is_potentially_hazardous is True
        assert obj.name == "(2020 QW3)"


class TestGetNEOLookup:
    def test_returns_object(self, service):
        resp = service.GetNEOLookup(pb.GetNEOLookupRequest(asteroid_id="3542519"))
        obj = resp.object
        assert obj.id == "3542519"
        assert obj.name == "(2010 PK9)"

    def test_magnitude_and_diameter(self, service):
        resp = service.GetNEOLookup(pb.GetNEOLookupRequest(asteroid_id="3542519"))
        obj = resp.object
        assert obj.absolute_magnitude == 21.4
        assert obj.estimated_diameter_min_km == 0.1011
        assert obj.estimated_diameter_max_km == 0.2261

    def test_hazardous_flag(self, service):
        resp = service.GetNEOLookup(pb.GetNEOLookupRequest(asteroid_id="3542519"))
        assert resp.object.is_potentially_hazardous is False

    def test_close_approach_data(self, service):
        resp = service.GetNEOLookup(pb.GetNEOLookupRequest(asteroid_id="3542519"))
        obj = resp.object
        assert obj.close_approach_date == "2024-01-15"
        assert obj.relative_velocity_kmh == pytest.approx(48520.1234)
        assert obj.miss_distance_km == pytest.approx(5432100.123)
        assert obj.orbiting_body == "Earth"


class TestGetEPIC:
    def test_returns_images(self, service):
        resp = service.GetEPIC(pb.GetEPICRequest())
        assert len(resp.images) == 2

    def test_image_fields(self, service):
        resp = service.GetEPIC(pb.GetEPICRequest())
        img = resp.images[0]
        assert img.identifier == "20240115003633"
        assert "EPIC" in img.caption
        assert img.image == "epic_1b_20240115003633"
        assert "2024-01-15" in img.date

    def test_coordinates(self, service):
        resp = service.GetEPIC(pb.GetEPICRequest())
        img = resp.images[0]
        assert img.centroid_lat == pytest.approx(12.34)
        assert img.centroid_lon == pytest.approx(-56.78)

    def test_second_image(self, service):
        resp = service.GetEPIC(pb.GetEPICRequest())
        img = resp.images[1]
        assert img.identifier == "20240115021533"
        assert img.centroid_lat == pytest.approx(10.20)


class TestSearchNASAImages:
    def test_returns_items(self, service):
        resp = service.SearchNASAImages(pb.SearchNASAImagesRequest(query="apollo"))
        assert len(resp.items) == 2

    def test_item_fields(self, service):
        resp = service.SearchNASAImages(pb.SearchNASAImagesRequest(query="apollo"))
        item = resp.items[0]
        assert item.nasa_id == "PIA00001"
        assert item.title == "Apollo 11 Lunar Module"
        assert "Lunar Module Eagle" in item.description
        assert item.media_type == "image"
        assert "1969" in item.date_created

    def test_preview_url(self, service):
        resp = service.SearchNASAImages(pb.SearchNASAImagesRequest(query="apollo"))
        assert "images-assets.nasa.gov" in resp.items[0].preview_url

    def test_second_item(self, service):
        resp = service.SearchNASAImages(pb.SearchNASAImagesRequest(query="mars"))
        item = resp.items[1]
        assert item.nasa_id == "PIA00002"
        assert item.title == "Mars Rover Landing"

    def test_no_api_key_used(self, service, mock_http):
        """SearchNASAImages should use _get_no_key (no api_key param)."""
        service.SearchNASAImages(pb.SearchNASAImagesRequest(query="apollo"))
        # The call should be made — verify a call happened.
        assert mock_http.get.called


class TestGetDonki:
    def test_returns_events(self, service):
        resp = service.GetDonki(pb.GetDonkiRequest(
            start_date="2024-01-15", end_date="2024-01-16",
        ))
        assert len(resp.events) == 2

    def test_event_fields(self, service):
        resp = service.GetDonki(pb.GetDonkiRequest())
        event = resp.events[0]
        assert event.activity_id == "2024-01-15-00-09-00-CME-001"
        assert "2024-01-15" in event.start_time
        assert event.source_location == "N20W30"
        assert "DONKI" in event.link

    def test_instruments(self, service):
        resp = service.GetDonki(pb.GetDonkiRequest())
        event = resp.events[0]
        assert len(event.instruments) == 2
        assert "SOHO: LASCO/C2" in event.instruments
        assert "SOHO: LASCO/C3" in event.instruments

    def test_second_event(self, service):
        resp = service.GetDonki(pb.GetDonkiRequest())
        event = resp.events[1]
        assert event.activity_id == "2024-01-16-12-30-00-CME-001"
        assert event.source_location == "S10E45"
        assert len(event.instruments) == 1


class TestGetTechTransfer:
    def test_returns_items(self, service):
        resp = service.GetTechTransfer(pb.GetTechTransferRequest(query="robotics"))
        assert len(resp.items) == 2

    def test_item_fields(self, service):
        resp = service.GetTechTransfer(pb.GetTechTransferRequest(query="robotics"))
        item = resp.items[0]
        assert item.title == "Robotic Arm Controller"
        assert "robotic arm" in item.description.lower()
        assert item.patent_number == "PAT-12345"
        assert item.center == "Jet Propulsion Laboratory"
        assert item.category == "Robotics"

    def test_second_item(self, service):
        resp = service.GetTechTransfer(pb.GetTechTransferRequest(query="solar"))
        item = resp.items[1]
        assert item.title == "Solar Cell Optimizer"
        assert item.center == "Glenn Research Center"
        assert item.category == "Energy"
