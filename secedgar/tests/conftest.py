"""Shared fixtures for SEC EDGAR MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real SEC EDGAR API return shapes
# ---------------------------------------------------------------------------

FAKE_SEARCH_COMPANY = {
    "hits": {
        "total": {"value": 2, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "entity_id": 320193,
                    "entity_name": "Apple Inc.",
                    "tickers": ["AAPL"],
                    "display_names": ["Apple Inc."],
                },
            },
            {
                "_source": {
                    "entity_id": 1018724,
                    "entity_name": "Apple Hospitality REIT Inc.",
                    "tickers": ["APLE"],
                    "display_names": ["Apple Hospitality REIT Inc."],
                },
            },
        ],
    }
}

FAKE_COMPANY_SUBMISSIONS = {
    "cik": "320193",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "exchanges": ["Nasdaq"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-23-000077",
                "0000320193-23-000065",
                "0000320193-22-000108",
            ],
            "form": ["10-K", "10-Q", "10-K"],
            "filingDate": ["2023-11-03", "2023-08-04", "2022-10-28"],
            "primaryDocument": [
                "aapl-20230930.htm",
                "aapl-20230701.htm",
                "aapl-20220924.htm",
            ],
            "primaryDocDescription": [
                "10-K Annual Report",
                "10-Q Quarterly Report",
                "10-K Annual Report",
            ],
            "reportDate": ["2023-09-30", "2023-07-01", "2022-09-24"],
        },
    },
}

FAKE_COMPANY_FACTS = {
    "cik": 320193,
    "entityName": "Apple Inc.",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "units": {
                    "USD": [
                        {
                            "val": 394328000000,
                            "accn": "0000320193-23-000077",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "start": "2022-10-01",
                            "end": "2023-09-30",
                        },
                        {
                            "val": 383285000000,
                            "accn": "0000320193-22-000108",
                            "fy": 2022,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2022-10-28",
                            "start": "2021-09-26",
                            "end": "2022-09-24",
                        },
                    ],
                },
            },
            "NetIncomeLoss": {
                "label": "Net Income (Loss)",
                "units": {
                    "USD": [
                        {
                            "val": 96995000000,
                            "accn": "0000320193-23-000077",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "start": "2022-10-01",
                            "end": "2023-09-30",
                        },
                    ],
                },
            },
            "Assets": {
                "label": "Assets",
                "units": {
                    "USD": [
                        {
                            "val": 352583000000,
                            "accn": "0000320193-23-000077",
                            "fy": 2023,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-11-03",
                            "end": "2023-09-30",
                        },
                    ],
                },
            },
        },
    },
}

FAKE_COMPANY_CONCEPT = {
    "cik": 320193,
    "taxonomy": "us-gaap",
    "tag": "Revenues",
    "label": "Revenues",
    "description": "Amount of revenue recognized from goods sold, services rendered, or other activities.",
    "entityName": "Apple Inc.",
    "units": {
        "USD": [
            {
                "val": 394328000000,
                "accn": "0000320193-23-000077",
                "fy": 2023,
                "fp": "FY",
                "form": "10-K",
                "filed": "2023-11-03",
                "start": "2022-10-01",
                "end": "2023-09-30",
            },
            {
                "val": 383285000000,
                "accn": "0000320193-22-000108",
                "fy": 2022,
                "fp": "FY",
                "form": "10-K",
                "filed": "2022-10-28",
                "start": "2021-09-26",
                "end": "2022-09-24",
            },
        ],
    },
}

FAKE_FULL_TEXT_SEARCH = {
    "hits": {
        "total": {"value": 42, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "file_num": "0000320193-23-000077",
                    "entity_name": "Apple Inc.",
                    "entity_id": 320193,
                    "form_type": "10-K",
                    "file_date": "2023-11-03",
                    "file_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
                },
                "highlight": {
                    "full_text": [
                        "The Company continues to invest in <em>artificial intelligence</em> and machine learning."
                    ],
                },
            },
        ],
    }
}

FAKE_COMPANY_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    "2": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
}

FAKE_RECENT_FILINGS = {
    "hits": {
        "total": {"value": 1000, "relation": "gte"},
        "hits": [
            {
                "_source": {
                    "file_num": "0000320193-23-000077",
                    "form_type": "10-K",
                    "file_date": "2023-11-03",
                    "entity_name": "Apple Inc.",
                    "entity_id": 320193,
                    "display_names": ["Apple Inc. 10-K"],
                    "file_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
                    "period_of_report": "2023-09-30",
                },
            },
            {
                "_source": {
                    "file_num": "0000789019-23-000080",
                    "form_type": "10-Q",
                    "file_date": "2023-10-25",
                    "entity_name": "MICROSOFT CORP",
                    "entity_id": 789019,
                    "display_names": ["MICROSOFT CORP 10-Q"],
                    "file_url": "https://www.sec.gov/Archives/edgar/data/789019/000078901923000080/msft-20230930.htm",
                    "period_of_report": "2023-09-30",
                },
            },
        ],
    }
}

FAKE_INSIDER_SEARCH = {
    "hits": {
        "total": {"value": 5, "relation": "eq"},
        "hits": [
            {
                "_source": {
                    "entity_name": "Cook Timothy D",
                    "entity_id": 320193,
                    "form_type": "4",
                    "file_date": "2023-10-05",
                },
            },
            {
                "_source": {
                    "entity_name": "Williams Jeffrey E",
                    "entity_id": 320193,
                    "form_type": "4",
                    "file_date": "2023-09-15",
                },
            },
        ],
    }
}

FAKE_INSTITUTIONAL_SEARCH = {
    "hits": {
        "total": {"value": 100, "relation": "gte"},
        "hits": [
            {
                "_source": {
                    "entity_name": "VANGUARD GROUP INC",
                    "entity_id": 102909,
                    "form_type": "13F-HR",
                    "file_date": "2023-11-14",
                },
            },
            {
                "_source": {
                    "entity_name": "BLACKROCK INC.",
                    "entity_id": 1364742,
                    "form_type": "13F-HR",
                    "file_date": "2023-11-13",
                },
            },
        ],
    }
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        # EFTS endpoints (search)
        "efts:search-index:q=Apple": FAKE_SEARCH_COMPANY,
        "efts:search-index:q=%22Form+4%22": FAKE_INSIDER_SEARCH,
        "efts:search-index:q=Apple+Inc.": FAKE_INSTITUTIONAL_SEARCH,
        "efts:search-index:q=artificial+intelligence": FAKE_FULL_TEXT_SEARCH,
        "efts:search-index:default": FAKE_RECENT_FILINGS,
        # Data endpoints
        "data:submissions": FAKE_COMPANY_SUBMISSIONS,
        "data:companyfacts": FAKE_COMPANY_FACTS,
        "data:companyconcept": FAKE_COMPANY_CONCEPT,
        "data:company_tickers": FAKE_COMPANY_TICKERS,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()

        # Match data.sec.gov endpoints by URL path
        if "data.sec.gov" in url or "data_url" in str(url):
            if "/submissions/" in url:
                resp.json.return_value = defaults["data:submissions"]
                return resp
            if "/companyfacts/" in url:
                resp.json.return_value = defaults["data:companyfacts"]
                return resp
            if "/companyconcept/" in url:
                resp.json.return_value = defaults["data:companyconcept"]
                return resp
            if "/company_tickers" in url:
                resp.json.return_value = defaults["data:company_tickers"]
                return resp

        # Match efts.sec.gov endpoints
        if "efts.sec.gov" in url or "efts_url" in str(url):
            if "/search-index" in url:
                q = (params or {}).get("q", "")
                forms = (params or {}).get("forms", "")
                if q == "Apple" and not forms:
                    resp.json.return_value = defaults["efts:search-index:q=Apple"]
                elif "Form 4" in q or forms == "4":
                    resp.json.return_value = defaults["efts:search-index:q=%22Form+4%22"]
                elif q == "Apple Inc." and forms == "13F-HR":
                    resp.json.return_value = defaults["efts:search-index:q=Apple+Inc."]
                elif q == "artificial intelligence":
                    resp.json.return_value = defaults["efts:search-index:q=artificial+intelligence"]
                else:
                    resp.json.return_value = defaults["efts:search-index:default"]
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
    """SECEdgarService with mocked HTTP client."""
    from secedgar_mcp.service import SECEdgarService

    svc = SECEdgarService.__new__(SECEdgarService)
    svc._http = mock_http
    svc._data_url = "https://data.sec.gov"
    svc._efts_url = "https://efts.sec.gov/LATEST"
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked SECEdgarService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-secedgar", version="0.0.1")
    srv.register(service)
    return srv
