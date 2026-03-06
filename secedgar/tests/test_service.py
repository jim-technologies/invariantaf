"""Unit tests -- every SECEdgarService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as pb
from tests.conftest import (
    FAKE_SEARCH_COMPANY,
    FAKE_COMPANY_SUBMISSIONS,
    FAKE_COMPANY_FACTS,
    FAKE_COMPANY_CONCEPT,
    FAKE_FULL_TEXT_SEARCH,
    FAKE_COMPANY_TICKERS,
    FAKE_RECENT_FILINGS,
    FAKE_INSIDER_SEARCH,
    FAKE_INSTITUTIONAL_SEARCH,
)


class TestSearchCompany:
    def test_returns_companies(self, service):
        resp = service.SearchCompany(pb.SearchCompanyRequest(query="Apple"))
        assert len(resp.companies) == 2

    def test_first_company_fields(self, service):
        resp = service.SearchCompany(pb.SearchCompanyRequest(query="Apple"))
        c = resp.companies[0]
        assert c.cik == "320193"
        assert c.name == "Apple Inc."
        assert "AAPL" in c.ticker

    def test_second_company(self, service):
        resp = service.SearchCompany(pb.SearchCompanyRequest(query="Apple"))
        c = resp.companies[1]
        assert c.cik == "1018724"
        assert "Apple Hospitality" in c.name

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"hits": {"total": {"value": 0}, "hits": []}}),
        )
        resp = service.SearchCompany(pb.SearchCompanyRequest(query="zzzznonexistent"))
        assert len(resp.companies) == 0


class TestGetCompanyFilings:
    def test_returns_filings(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(cik="320193"))
        assert len(resp.filings) == 3

    def test_company_name(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(cik="320193"))
        assert resp.company_name == "Apple Inc."
        assert resp.cik == "0000320193"

    def test_filing_fields(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(cik="320193"))
        f = resp.filings[0]
        assert f.accession_number == "0000320193-23-000077"
        assert f.form_type == "10-K"
        assert f.filing_date == "2023-11-03"
        assert f.description == "10-K Annual Report"
        assert "aapl-20230930.htm" in f.document_url

    def test_form_type_filter(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(
            cik="320193", form_type="10-K",
        ))
        assert len(resp.filings) == 2
        for f in resp.filings:
            assert f.form_type == "10-K"

    def test_limit(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(
            cik="320193", limit=1,
        ))
        assert len(resp.filings) == 1

    def test_total_filings(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(cik="320193"))
        assert resp.total_filings == 3

    def test_cik_padded(self, service):
        resp = service.GetCompanyFilings(pb.GetCompanyFilingsRequest(cik="320193"))
        assert resp.cik == "0000320193"


class TestGetCompanyFacts:
    def test_returns_facts(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        assert len(resp.facts) > 0

    def test_company_name(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        assert resp.company_name == "Apple Inc."
        assert resp.cik == "0000320193"

    def test_revenue_fact(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        revenue_facts = [f for f in resp.facts if f.concept == "Revenues"]
        assert len(revenue_facts) == 2
        assert revenue_facts[0].value == 394328000000
        assert revenue_facts[0].unit == "USD"
        assert revenue_facts[0].fiscal_year == 2023
        assert revenue_facts[0].fiscal_period == "FY"
        assert revenue_facts[0].form == "10-K"

    def test_net_income_fact(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        ni_facts = [f for f in resp.facts if f.concept == "NetIncomeLoss"]
        assert len(ni_facts) == 1
        assert ni_facts[0].value == 96995000000
        assert ni_facts[0].label == "Net Income (Loss)"

    def test_assets_fact(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        asset_facts = [f for f in resp.facts if f.concept == "Assets"]
        assert len(asset_facts) == 1
        assert asset_facts[0].value == 352583000000

    def test_filing_metadata(self, service):
        resp = service.GetCompanyFacts(pb.GetCompanyFactsRequest(cik="320193"))
        rev = [f for f in resp.facts if f.concept == "Revenues"][0]
        assert rev.filed == "2023-11-03"
        assert rev.accession_number == "0000320193-23-000077"
        assert rev.start_date == "2022-10-01"
        assert rev.end_date == "2023-09-30"


class TestGetCompanyConcept:
    def test_returns_values(self, service):
        resp = service.GetCompanyConcept(pb.GetCompanyConceptRequest(
            cik="320193", taxonomy="us-gaap", concept="Revenues",
        ))
        assert len(resp.values) == 2

    def test_metadata(self, service):
        resp = service.GetCompanyConcept(pb.GetCompanyConceptRequest(
            cik="320193", taxonomy="us-gaap", concept="Revenues",
        ))
        assert resp.cik == "0000320193"
        assert resp.taxonomy == "us-gaap"
        assert resp.concept == "Revenues"
        assert resp.label == "Revenues"
        assert "revenue" in resp.description.lower()

    def test_value_fields(self, service):
        resp = service.GetCompanyConcept(pb.GetCompanyConceptRequest(
            cik="320193", taxonomy="us-gaap", concept="Revenues",
        ))
        v = resp.values[0]
        assert v.value == 394328000000
        assert v.unit == "USD"
        assert v.fiscal_year == 2023
        assert v.fiscal_period == "FY"
        assert v.end_date == "2023-09-30"

    def test_second_value(self, service):
        resp = service.GetCompanyConcept(pb.GetCompanyConceptRequest(
            cik="320193", taxonomy="us-gaap", concept="Revenues",
        ))
        v = resp.values[1]
        assert v.value == 383285000000
        assert v.fiscal_year == 2022

    def test_default_taxonomy(self, service):
        resp = service.GetCompanyConcept(pb.GetCompanyConceptRequest(
            cik="320193", concept="Revenues",
        ))
        # Should still work -- taxonomy defaults to "us-gaap" in service
        assert len(resp.values) == 2


class TestSearchFullText:
    def test_returns_hits(self, service):
        resp = service.SearchFullText(pb.SearchFullTextRequest(
            query="artificial intelligence",
        ))
        assert resp.total_hits == 42
        assert len(resp.hits) == 1

    def test_hit_fields(self, service):
        resp = service.SearchFullText(pb.SearchFullTextRequest(
            query="artificial intelligence",
        ))
        hit = resp.hits[0]
        assert hit.company_name == "Apple Inc."
        assert hit.cik == "320193"
        assert hit.form_type == "10-K"
        assert hit.filing_date == "2023-11-03"

    def test_snippet(self, service):
        resp = service.SearchFullText(pb.SearchFullTextRequest(
            query="artificial intelligence",
        ))
        assert "artificial intelligence" in resp.hits[0].snippet

    def test_document_url(self, service):
        resp = service.SearchFullText(pb.SearchFullTextRequest(
            query="artificial intelligence",
        ))
        assert resp.hits[0].document_url.startswith("https://")


class TestGetFiling:
    def test_returns_filing(self, service):
        resp = service.GetFiling(pb.GetFilingRequest(
            accession_number="0000320193-23-000077",
        ))
        assert resp.accession_number == "0000320193-23-000077"
        assert resp.form_type == "10-K"
        assert resp.company_name == "Apple Inc."

    def test_filing_date(self, service):
        resp = service.GetFiling(pb.GetFilingRequest(
            accession_number="0000320193-23-000077",
        ))
        assert resp.filing_date == "2023-11-03"

    def test_documents(self, service):
        resp = service.GetFiling(pb.GetFilingRequest(
            accession_number="0000320193-23-000077",
        ))
        assert len(resp.documents) >= 1
        doc = resp.documents[0]
        assert doc.filename == "aapl-20230930.htm"
        assert "sec.gov" in doc.url


class TestGetInsiderTransactions:
    def test_returns_transactions(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(
            cik="320193",
        ))
        assert resp.company_name == "Apple Inc."
        assert len(resp.transactions) == 2

    def test_transaction_fields(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(
            cik="320193",
        ))
        t = resp.transactions[0]
        assert t.insider_name == "Cook Timothy D"
        assert t.transaction_date == "2023-10-05"

    def test_second_insider(self, service):
        resp = service.GetInsiderTransactions(pb.GetInsiderTransactionsRequest(
            cik="320193",
        ))
        t = resp.transactions[1]
        assert t.insider_name == "Williams Jeffrey E"


class TestGetInstitutionalHoldings:
    def test_returns_holdings(self, service):
        resp = service.GetInstitutionalHoldings(pb.GetInstitutionalHoldingsRequest(
            cik="320193",
        ))
        assert resp.company_name == "Apple Inc."
        assert len(resp.holdings) == 2

    def test_holding_fields(self, service):
        resp = service.GetInstitutionalHoldings(pb.GetInstitutionalHoldingsRequest(
            cik="320193",
        ))
        h = resp.holdings[0]
        assert h.institution_name == "VANGUARD GROUP INC"
        assert h.report_date == "2023-11-14"

    def test_second_holder(self, service):
        resp = service.GetInstitutionalHoldings(pb.GetInstitutionalHoldingsRequest(
            cik="320193",
        ))
        h = resp.holdings[1]
        assert h.institution_name == "BLACKROCK INC."
        assert h.institution_cik == "1364742"


class TestGetTickerToCIK:
    def test_returns_apple(self, service):
        resp = service.GetTickerToCIK(pb.GetTickerToCIKRequest(ticker="AAPL"))
        assert resp.cik == "0000320193"
        assert resp.company_name == "Apple Inc."
        assert resp.ticker == "AAPL"

    def test_returns_microsoft(self, service):
        resp = service.GetTickerToCIK(pb.GetTickerToCIKRequest(ticker="MSFT"))
        assert resp.cik == "0000789019"
        assert resp.company_name == "MICROSOFT CORP"
        assert resp.ticker == "MSFT"

    def test_case_insensitive(self, service):
        resp = service.GetTickerToCIK(pb.GetTickerToCIKRequest(ticker="aapl"))
        assert resp.cik == "0000320193"
        assert resp.ticker == "AAPL"

    def test_not_found(self, service):
        resp = service.GetTickerToCIK(pb.GetTickerToCIKRequest(ticker="ZZZZZ"))
        assert resp.cik == ""
        assert resp.ticker == "ZZZZZ"


class TestGetRecentFilings:
    def test_returns_filings(self, service):
        resp = service.GetRecentFilings(pb.GetRecentFilingsRequest())
        assert len(resp.filings) == 2

    def test_filing_fields(self, service):
        resp = service.GetRecentFilings(pb.GetRecentFilingsRequest())
        f = resp.filings[0]
        assert f.form_type == "10-K"
        assert f.company_name == "Apple Inc."
        assert f.cik == "320193"
        assert f.filing_date == "2023-11-03"

    def test_second_filing(self, service):
        resp = service.GetRecentFilings(pb.GetRecentFilingsRequest())
        f = resp.filings[1]
        assert f.form_type == "10-Q"
        assert f.company_name == "MICROSOFT CORP"

    def test_document_url(self, service):
        resp = service.GetRecentFilings(pb.GetRecentFilingsRequest())
        assert resp.filings[0].document_url.startswith("https://")
