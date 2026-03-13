"""Shared fixtures for USGS MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usgs_mcp.gen.usgs.v1 import usgs_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real USGS API return shapes
# ---------------------------------------------------------------------------

FAKE_EARTHQUAKE_1 = {
    "type": "Feature",
    "properties": {
        "mag": 4.5,
        "magType": "mw",
        "place": "10 km SSW of Los Angeles, CA",
        "time": 1704067200000,
        "updated": 1704070800000,
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000test1",
        "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us7000test1.geojson",
        "felt": 1500,
        "cdi": 5.2,
        "mmi": 4.8,
        "alert": "green",
        "status": "reviewed",
        "tsunami": 0,
        "sig": 612,
        "net": "us",
        "code": "7000test1",
        "nst": 45,
        "dmin": 0.05,
        "rms": 0.87,
        "horizontalError": 3.2,
        "depthError": 1.5,
        "magError": 0.12,
        "magNst": 30,
        "type": "earthquake",
        "title": "M 4.5 - 10 km SSW of Los Angeles, CA",
    },
    "geometry": {
        "type": "Point",
        "coordinates": [-118.2437, 33.9425, 12.5],
    },
    "id": "us7000test1",
}

FAKE_EARTHQUAKE_2 = {
    "type": "Feature",
    "properties": {
        "mag": 2.1,
        "magType": "ml",
        "place": "5 km NE of San Francisco, CA",
        "time": 1704063600000,
        "updated": 1704067200000,
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/nc73000test2",
        "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/nc73000test2.geojson",
        "felt": None,
        "cdi": None,
        "mmi": None,
        "alert": None,
        "status": "automatic",
        "tsunami": 0,
        "sig": 72,
        "net": "nc",
        "code": "73000test2",
        "nst": 20,
        "dmin": 0.02,
        "rms": 0.45,
        "horizontalError": 1.1,
        "depthError": 0.8,
        "magError": 0.25,
        "magNst": 12,
        "type": "earthquake",
        "title": "M 2.1 - 5 km NE of San Francisco, CA",
    },
    "geometry": {
        "type": "Point",
        "coordinates": [-122.4194, 37.8044, 8.3],
    },
    "id": "nc73000test2",
}

FAKE_SIGNIFICANT_EARTHQUAKE = {
    "type": "Feature",
    "properties": {
        "mag": 7.1,
        "magType": "mww",
        "place": "120 km SE of Tokyo, Japan",
        "time": 1703980800000,
        "updated": 1704067200000,
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000sig01",
        "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us7000sig01.geojson",
        "felt": 25000,
        "cdi": 7.5,
        "mmi": 6.9,
        "alert": "yellow",
        "status": "reviewed",
        "tsunami": 1,
        "sig": 965,
        "net": "us",
        "code": "7000sig01",
        "nst": 120,
        "dmin": 1.2,
        "rms": 1.05,
        "horizontalError": 5.0,
        "depthError": 3.2,
        "magError": 0.06,
        "magNst": 85,
        "type": "earthquake",
        "title": "M 7.1 - 120 km SE of Tokyo, Japan",
    },
    "geometry": {
        "type": "Point",
        "coordinates": [140.6917, 34.6937, 45.0],
    },
    "id": "us7000sig01",
}

FAKE_RECENT_COLLECTION = {
    "type": "FeatureCollection",
    "metadata": {
        "generated": 1704070800000,
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
        "title": "USGS All Earthquakes, Past Hour",
        "status": 200,
        "api": "1.10.3",
        "count": 2,
    },
    "features": [FAKE_EARTHQUAKE_1, FAKE_EARTHQUAKE_2],
}

FAKE_SIGNIFICANT_COLLECTION = {
    "type": "FeatureCollection",
    "metadata": {
        "generated": 1704070800000,
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson",
        "title": "USGS Significant Earthquakes, Past Month",
        "status": 200,
        "api": "1.10.3",
        "count": 1,
    },
    "features": [FAKE_SIGNIFICANT_EARTHQUAKE],
}

FAKE_SEARCH_COLLECTION = {
    "type": "FeatureCollection",
    "metadata": {
        "generated": 1704070800000,
        "url": "https://earthquake.usgs.gov/fdsnws/event/1/query",
        "title": "USGS Earthquakes",
        "status": 200,
        "api": "1.14.1",
        "count": 1,
    },
    "features": [FAKE_EARTHQUAKE_1],
}

FAKE_WATER_LEVELS = {
    "name": "ns1:timeSeriesResponseType",
    "declaredType": "org.cuahsi.waterml.TimeSeriesResponseType",
    "scope": "javax.xml.bind.JAXBElement$GlobalScope",
    "value": {
        "queryInfo": {
            "queryURL": "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00065&period=P1D",
            "criteria": {
                "locationParam": "[ALL:01646500]",
                "variableParam": "[00065]",
                "timeParam": {
                    "beginDT": "2024-01-01T00:00:00.000",
                    "endDT": "2024-01-02T00:00:00.000",
                },
                "parameter": [],
            },
            "note": [],
        },
        "timeSeries": [
            {
                "sourceInfo": {
                    "siteName": "POTOMAC RIVER NEAR WASH, DC LITTLE FALLS PUMP STA",
                    "siteCode": [
                        {
                            "value": "01646500",
                            "network": "NWIS",
                            "agencyCode": "USGS",
                        }
                    ],
                    "timeZoneInfo": {
                        "defaultTimeZone": {
                            "zoneOffset": "-05:00",
                            "zoneAbbreviation": "EST",
                        },
                        "daylightSavingsTimeZone": {
                            "zoneOffset": "-04:00",
                            "zoneAbbreviation": "EDT",
                        },
                        "siteUsesDaylightSavingsTime": True,
                    },
                    "geoLocation": {
                        "geogLocation": {
                            "srs": "EPSG:4326",
                            "latitude": 38.94977778,
                            "longitude": -77.12763889,
                        },
                        "localSiteXY": [],
                    },
                    "note": [],
                    "siteType": [],
                    "siteProperty": [],
                },
                "variable": {
                    "variableCode": [
                        {
                            "value": "00065",
                            "network": "NWIS",
                            "vocabulary": "NWIS:UnitValues",
                            "variableID": 45807202,
                            "default": True,
                        }
                    ],
                    "variableName": "Gage height",
                    "variableDescription": "Gage height, ft",
                    "valueType": "Derived Value",
                    "unit": {"unitCode": "ft"},
                    "options": {"option": []},
                    "note": [],
                    "noDataValue": -999999.0,
                },
                "values": [
                    {
                        "value": [
                            {
                                "value": "3.45",
                                "qualifiers": ["P"],
                                "dateTime": "2024-01-01T00:00:00.000-05:00",
                            },
                            {
                                "value": "3.48",
                                "qualifiers": ["P"],
                                "dateTime": "2024-01-01T00:15:00.000-05:00",
                            },
                            {
                                "value": "3.52",
                                "qualifiers": ["P"],
                                "dateTime": "2024-01-01T00:30:00.000-05:00",
                            },
                        ],
                        "qualifier": [],
                        "qualityControlLevel": [],
                        "method": [],
                        "source": [],
                        "offset": [],
                        "sample": [],
                        "censorCode": [],
                    }
                ],
                "name": "USGS:01646500:00065:00000",
            }
        ],
    },
}

FAKE_EMPTY_WATER_LEVELS = {
    "name": "ns1:timeSeriesResponseType",
    "declaredType": "org.cuahsi.waterml.TimeSeriesResponseType",
    "scope": "javax.xml.bind.JAXBElement$GlobalScope",
    "value": {
        "queryInfo": {},
        "timeSeries": [],
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/summary/all_hour.geojson": FAKE_RECENT_COLLECTION,
        "/summary/significant_month.geojson": FAKE_SIGNIFICANT_COLLECTION,
        "/fdsnws/event/1/query": FAKE_SEARCH_COLLECTION,
        "/detail/us7000test1.geojson": FAKE_EARTHQUAKE_1,
        "/nwis/iv/": FAKE_WATER_LEVELS,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """USGSService with mocked HTTP client."""
    from usgs_mcp.service import USGSService

    svc = USGSService.__new__(USGSService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked USGSService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-usgs", version="0.0.1")
    srv.register(service)
    return srv
