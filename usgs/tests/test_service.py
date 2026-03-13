"""Unit tests for USGSService -- uses mocked HTTP."""

from usgs_mcp.gen.usgs.v1 import usgs_pb2 as pb


class TestGetRecentEarthquakes:
    def test_returns_collection(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        assert resp.collection.count == 2
        assert resp.collection.title == "USGS All Earthquakes, Past Hour"

    def test_earthquake_fields(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        eq = resp.collection.earthquakes[0]
        assert eq.id == "us7000test1"
        assert eq.magnitude == 4.5
        assert eq.magnitude_type == "mw"
        assert eq.place == "10 km SSW of Los Angeles, CA"
        assert eq.time == 1704067200000
        assert eq.longitude == -118.2437
        assert eq.latitude == 33.9425
        assert eq.depth == 12.5

    def test_earthquake_impact_fields(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        eq = resp.collection.earthquakes[0]
        assert eq.felt == 1500
        assert eq.cdi == 5.2
        assert eq.mmi == 4.8
        assert eq.alert == "green"
        assert eq.status == "reviewed"
        assert eq.tsunami == 0
        assert eq.sig == 612

    def test_earthquake_network_fields(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        eq = resp.collection.earthquakes[0]
        assert eq.net == "us"
        assert eq.code == "7000test1"
        assert eq.nst == 45
        assert eq.rms == 0.87

    def test_second_earthquake(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        eq = resp.collection.earthquakes[1]
        assert eq.id == "nc73000test2"
        assert eq.magnitude == 2.1
        assert eq.place == "5 km NE of San Francisco, CA"

    def test_null_fields_handled(self, service):
        resp = service.GetRecentEarthquakes(pb.GetRecentEarthquakesRequest())
        eq = resp.collection.earthquakes[1]
        assert eq.felt == 0
        assert eq.cdi == 0
        assert eq.alert == ""


class TestGetSignificantEarthquakes:
    def test_returns_collection(self, service):
        resp = service.GetSignificantEarthquakes(pb.GetSignificantEarthquakesRequest())
        assert resp.collection.count == 1
        assert "Significant" in resp.collection.title

    def test_significant_earthquake(self, service):
        resp = service.GetSignificantEarthquakes(pb.GetSignificantEarthquakesRequest())
        eq = resp.collection.earthquakes[0]
        assert eq.id == "us7000sig01"
        assert eq.magnitude == 7.1
        assert eq.alert == "yellow"
        assert eq.tsunami == 1
        assert eq.sig == 965

    def test_significant_location(self, service):
        resp = service.GetSignificantEarthquakes(pb.GetSignificantEarthquakesRequest())
        eq = resp.collection.earthquakes[0]
        assert eq.longitude == 140.6917
        assert eq.latitude == 34.6937
        assert eq.depth == 45.0


class TestSearchEarthquakes:
    def test_returns_results(self, service):
        req = pb.SearchEarthquakesRequest(
            start_time="2024-01-01",
            end_time="2024-01-31",
            min_magnitude=4.0,
        )
        resp = service.SearchEarthquakes(req)
        assert resp.collection.count == 1
        assert resp.collection.earthquakes[0].id == "us7000test1"

    def test_passes_params(self, service, mock_http):
        req = pb.SearchEarthquakesRequest(
            start_time="2024-01-01",
            end_time="2024-01-31",
            min_magnitude=4.0,
            limit=10,
        )
        service.SearchEarthquakes(req)
        call_args = mock_http.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params["format"] == "geojson"
        assert params["starttime"] == "2024-01-01"
        assert params["endtime"] == "2024-01-31"
        assert params["minmagnitude"] == 4.0
        assert params["limit"] == 10


class TestGetEarthquakeDetail:
    def test_returns_earthquake(self, service):
        req = pb.GetEarthquakeDetailRequest(event_id="us7000test1")
        resp = service.GetEarthquakeDetail(req)
        assert resp.earthquake.id == "us7000test1"
        assert resp.earthquake.magnitude == 4.5

    def test_earthquake_title(self, service):
        req = pb.GetEarthquakeDetailRequest(event_id="us7000test1")
        resp = service.GetEarthquakeDetail(req)
        assert resp.earthquake.title == "M 4.5 - 10 km SSW of Los Angeles, CA"

    def test_calls_correct_url(self, service, mock_http):
        req = pb.GetEarthquakeDetailRequest(event_id="us7000test1")
        service.GetEarthquakeDetail(req)
        url = mock_http.get.call_args[0][0]
        assert "detail/us7000test1.geojson" in url


class TestGetWaterLevels:
    def test_returns_site(self, service):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        resp = service.GetWaterLevels(req)
        assert resp.site.site_number == "01646500"
        assert "POTOMAC" in resp.site.site_name

    def test_site_location(self, service):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        resp = service.GetWaterLevels(req)
        assert abs(resp.site.latitude - 38.9498) < 0.01
        assert abs(resp.site.longitude - (-77.1276)) < 0.01

    def test_readings(self, service):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        resp = service.GetWaterLevels(req)
        assert len(resp.site.readings) == 3
        assert resp.site.readings[0].value == "3.45"
        assert resp.site.readings[1].value == "3.48"
        assert resp.site.readings[2].value == "3.52"

    def test_reading_timestamps(self, service):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        resp = service.GetWaterLevels(req)
        assert "2024-01-01T00:00:00" in resp.site.readings[0].datetime

    def test_variable_info(self, service):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        resp = service.GetWaterLevels(req)
        assert resp.site.variable_description == "Gage height, ft"
        assert resp.site.unit == "ft"

    def test_passes_site_number(self, service, mock_http):
        req = pb.GetWaterLevelsRequest(site_number="01646500")
        service.GetWaterLevels(req)
        call_args = mock_http.get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params", {})
        assert params["sites"] == "01646500"
        assert params["parameterCd"] == "00065"
