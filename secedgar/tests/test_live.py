"""Live integration tests for SEC EDGAR API -- hits the real API.

Run with:
    SECEDGAR_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

All tests hit public (unauthenticated) SEC EDGAR endpoints.
The SEC requires a User-Agent header; set SEC_EDGAR_USER_AGENT env var
(e.g., "MyApp/1.0 (email@example.com)") or the default will be used.
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
    os.getenv("SECEDGAR_RUN_LIVE_TESTS") != "1",
    reason="Set SECEDGAR_RUN_LIVE_TESTS=1 to run live SEC EDGAR API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server
    from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as _pb  # noqa: F401
    from secedgar_mcp.service import SECEdgarService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-secedgar-live", version="0.0.1"
    )
    servicer = SECEdgarService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- Shared fixtures for data discovery ---


@pytest.fixture(scope="module")
def apple_cik(live_server):
    """Look up Apple's CIK once for all tests that need it."""
    result = live_server._cli(
        ["SECEdgarService", "GetTickerToCIK", "-r", json.dumps({"ticker": "AAPL"})]
    )
    cik = result.get("cik", "")
    assert cik, "expected a CIK for AAPL"
    return cik


@pytest.fixture(scope="module")
def recent_filing_accession(live_server, apple_cik):
    """Discover a valid accession number from Apple's filings."""
    result = live_server._cli(
        [
            "SECEdgarService",
            "GetCompanyFilings",
            "-r",
            json.dumps({"cik": apple_cik, "limit": 1}),
        ]
    )
    filings = result.get("filings", [])
    if not filings:
        pytest.skip("no filings found for Apple")
    accession = filings[0].get("accessionNumber") or filings[0].get("accession_number", "")
    assert accession, "expected an accession number"
    return accession


# --- Ticker/CIK lookup ---


class TestLiveTickerLookup:
    def test_get_ticker_to_cik(self, live_server):
        result = live_server._cli(
            ["SECEdgarService", "GetTickerToCIK", "-r", json.dumps({"ticker": "AAPL"})]
        )
        cik = result.get("cik", "")
        assert cik
        # Apple's CIK is 320193
        assert "320193" in cik
        name = result.get("companyName") or result.get("company_name", "")
        assert name  # Should have a company name

    def test_get_ticker_to_cik_microsoft(self, live_server):
        result = live_server._cli(
            ["SECEdgarService", "GetTickerToCIK", "-r", json.dumps({"ticker": "MSFT"})]
        )
        cik = result.get("cik", "")
        assert cik
        assert "789019" in cik


# --- Company search ---


class TestLiveSearchCompany:
    def test_search_company(self, live_server):
        result = live_server._cli(
            ["SECEdgarService", "SearchCompany", "-r", json.dumps({"query": "Apple", "limit": 5})]
        )
        companies = result.get("companies", [])
        assert isinstance(companies, list)
        assert len(companies) > 0
        c = companies[0]
        assert "name" in c or "cik" in c

    def test_search_company_by_ticker(self, live_server):
        result = live_server._cli(
            ["SECEdgarService", "SearchCompany", "-r", json.dumps({"query": "TSLA", "limit": 3})]
        )
        companies = result.get("companies", [])
        assert isinstance(companies, list)
        assert len(companies) > 0


# --- Company filings ---


class TestLiveCompanyFilings:
    def test_get_company_filings(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetCompanyFilings",
                "-r",
                json.dumps({"cik": apple_cik, "limit": 5}),
            ]
        )
        filings = result.get("filings", [])
        assert isinstance(filings, list)
        assert len(filings) > 0
        f = filings[0]
        acc = f.get("accessionNumber") or f.get("accession_number", "")
        assert acc
        form = f.get("formType") or f.get("form_type", "")
        assert form

    def test_get_company_filings_by_form_type(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetCompanyFilings",
                "-r",
                json.dumps({"cik": apple_cik, "form_type": "10-K", "limit": 3}),
            ]
        )
        filings = result.get("filings", [])
        assert isinstance(filings, list)
        if filings:
            for f in filings:
                form = f.get("formType") or f.get("form_type", "")
                assert form == "10-K"


# --- Company financial data ---


class TestLiveCompanyFacts:
    def test_get_company_facts(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetCompanyFacts",
                "-r",
                json.dumps({"cik": apple_cik}),
            ]
        )
        facts = result.get("facts", [])
        assert isinstance(facts, list)
        assert len(facts) > 0
        f = facts[0]
        assert "concept" in f
        assert "unit" in f

    def test_get_company_concept(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetCompanyConcept",
                "-r",
                json.dumps({
                    "cik": apple_cik,
                    "taxonomy": "us-gaap",
                    "concept": "Revenues",
                }),
            ]
        )
        values = result.get("values", [])
        assert isinstance(values, list)
        assert len(values) > 0
        v = values[0]
        assert v.get("value", 0) > 0
        assert v.get("unit") == "USD"


# --- Full-text search ---


class TestLiveFullTextSearch:
    def test_search_full_text(self, live_server):
        result = live_server._cli(
            [
                "SECEdgarService",
                "SearchFullText",
                "-r",
                json.dumps({"query": "artificial intelligence", "limit": 3}),
            ]
        )
        total = result.get("totalHits") or result.get("total_hits", 0)
        assert int(total) > 0
        hits = result.get("hits", [])
        assert isinstance(hits, list)
        assert len(hits) > 0


# --- Filing detail ---


class TestLiveFiling:
    def test_get_filing(self, live_server, recent_filing_accession):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetFiling",
                "-r",
                json.dumps({"accession_number": recent_filing_accession}),
            ]
        )
        acc = result.get("accessionNumber") or result.get("accession_number", "")
        assert acc
        name = result.get("companyName") or result.get("company_name", "")
        assert name


# --- Recent filings feed ---


class TestLiveRecentFilings:
    def test_get_recent_filings(self, live_server):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetRecentFilings",
                "-r",
                json.dumps({"limit": 5}),
            ]
        )
        filings = result.get("filings", [])
        assert isinstance(filings, list)
        assert len(filings) > 0
        f = filings[0]
        form = f.get("formType") or f.get("form_type", "")
        assert form

    def test_get_recent_filings_by_form(self, live_server):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetRecentFilings",
                "-r",
                json.dumps({"form_type": "10-K", "limit": 3}),
            ]
        )
        filings = result.get("filings", [])
        assert isinstance(filings, list)
        # May be empty if no recent 10-K filings, but should succeed
        if filings:
            form = filings[0].get("formType") or filings[0].get("form_type", "")
            assert form


# --- Insider transactions ---


class TestLiveInsiderTransactions:
    def test_get_insider_transactions(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetInsiderTransactions",
                "-r",
                json.dumps({"cik": apple_cik, "limit": 5}),
            ]
        )
        name = result.get("companyName") or result.get("company_name", "")
        assert name
        # Transactions may or may not be present depending on API data
        transactions = result.get("transactions", [])
        assert isinstance(transactions, list)


# --- Institutional holdings ---


class TestLiveInstitutionalHoldings:
    def test_get_institutional_holdings(self, live_server, apple_cik):
        result = live_server._cli(
            [
                "SECEdgarService",
                "GetInstitutionalHoldings",
                "-r",
                json.dumps({"cik": apple_cik, "limit": 5}),
            ]
        )
        name = result.get("companyName") or result.get("company_name", "")
        assert name
        holdings = result.get("holdings", [])
        assert isinstance(holdings, list)
