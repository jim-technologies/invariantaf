"""SECEdgarService -- wraps the SEC EDGAR API into proto RPCs."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from secedgar_mcp.gen.secedgar.v1 import secedgar_pb2 as pb

_DATA_URL = "https://data.sec.gov"
_EFTS_URL = "https://efts.sec.gov/LATEST"


class SECEdgarService:
    """Implements SECEdgarService RPCs via the free SEC EDGAR API."""

    def __init__(self):
        user_agent = os.environ.get(
            "SEC_EDGAR_USER_AGENT", "InvariantMCP/1.0 (contact@example.com)"
        )
        self._http = httpx.Client(
            timeout=30,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
        )
        self._data_url = _DATA_URL
        self._efts_url = _EFTS_URL

    # ── helpers ──────────────────────────────────────────────────────────

    def _get_data(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{self._data_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _get_efts(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{self._efts_url}{path}", params=params or {})
        resp.raise_for_status()
        return resp.json()

    def _pad_cik(self, cik: str) -> str:
        """SEC requires CIK padded to 10 digits."""
        return str(cik).zfill(10)

    def _normalize_accession(self, accession: str) -> str:
        """Normalize accession number to dashed format (e.g., 0000320193-23-000077)."""
        digits = re.sub(r"[^0-9]", "", accession)
        if len(digits) == 18:
            return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"
        return accession

    # ── RPCs ─────────────────────────────────────────────────────────────

    def SearchCompany(self, request: Any, context: Any = None) -> pb.SearchCompanyResponse:
        params: dict[str, Any] = {"q": request.query}
        if request.limit and request.limit > 0:
            params["count"] = request.limit
        else:
            params["count"] = 10

        raw = self._get_efts("/search-index", params=params)
        resp = pb.SearchCompanyResponse()

        for hit in raw.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            entity_name = src.get("entity_name", "") or src.get("display_names", [""])[0] if src.get("display_names") else src.get("entity_name", "")
            resp.companies.append(pb.Company(
                cik=str(src.get("entity_id", "")),
                name=entity_name,
                ticker=",".join(src.get("tickers", [])) if src.get("tickers") else "",
                exchange="",
            ))

        return resp

    def GetCompanyFilings(self, request: Any, context: Any = None) -> pb.GetCompanyFilingsResponse:
        cik = self._pad_cik(request.cik)
        raw = self._get_data(f"/submissions/CIK{cik}.json")

        resp = pb.GetCompanyFilingsResponse(
            company_name=raw.get("name", ""),
            cik=cik,
        )

        recent = raw.get("filings", {}).get("recent", {})
        if not recent:
            return resp

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])
        report_dates = recent.get("reportDate", [])

        limit = request.limit if request.limit > 0 else 40
        count = 0

        for i in range(len(forms)):
            if request.form_type and forms[i] != request.form_type:
                continue
            if count >= limit:
                break

            acc = accessions[i] if i < len(accessions) else ""
            acc_no_dashes = acc.replace("-", "")
            doc = primary_docs[i] if i < len(primary_docs) else ""
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/{doc}" if doc else ""

            resp.filings.append(pb.Filing(
                accession_number=acc,
                form_type=forms[i],
                filing_date=dates[i] if i < len(dates) else "",
                description=descriptions[i] if i < len(descriptions) else "",
                document_url=doc_url,
                cik=cik,
                company_name=raw.get("name", ""),
                report_date=report_dates[i] if i < len(report_dates) else "",
            ))
            count += 1

        resp.total_filings = len(forms)
        return resp

    def GetCompanyFacts(self, request: Any, context: Any = None) -> pb.GetCompanyFactsResponse:
        cik = self._pad_cik(request.cik)
        raw = self._get_data(f"/api/xbrl/companyfacts/CIK{cik}.json")

        resp = pb.GetCompanyFactsResponse(
            cik=cik,
            company_name=raw.get("entityName", ""),
        )

        facts_data = raw.get("facts", {})
        for taxonomy, concepts in facts_data.items():
            for concept_name, concept_data in concepts.items():
                label = concept_data.get("label", concept_name)
                for unit_key, entries in concept_data.get("units", {}).items():
                    for entry in entries:
                        resp.facts.append(pb.FinancialFact(
                            concept=concept_name,
                            label=label,
                            value=float(entry.get("val", 0)),
                            unit=unit_key,
                            start_date=entry.get("start", ""),
                            end_date=entry.get("end", ""),
                            filed=entry.get("filed", ""),
                            form=entry.get("form", ""),
                            accession_number=entry.get("accn", ""),
                            fiscal_year=entry.get("fy", 0) or 0,
                            fiscal_period=entry.get("fp", ""),
                        ))

        return resp

    def GetCompanyConcept(self, request: Any, context: Any = None) -> pb.GetCompanyConceptResponse:
        cik = self._pad_cik(request.cik)
        taxonomy = request.taxonomy or "us-gaap"
        concept = request.concept

        raw = self._get_data(f"/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json")

        resp = pb.GetCompanyConceptResponse(
            cik=cik,
            taxonomy=raw.get("taxonomy", taxonomy),
            concept=raw.get("tag", concept),
            label=raw.get("label", ""),
            description=raw.get("description", "") or "",
        )

        for unit_key, entries in raw.get("units", {}).items():
            for entry in entries:
                resp.values.append(pb.FinancialFact(
                    concept=concept,
                    label=raw.get("label", ""),
                    value=float(entry.get("val", 0)),
                    unit=unit_key,
                    start_date=entry.get("start", ""),
                    end_date=entry.get("end", ""),
                    filed=entry.get("filed", ""),
                    form=entry.get("form", ""),
                    accession_number=entry.get("accn", ""),
                    fiscal_year=entry.get("fy", 0) or 0,
                    fiscal_period=entry.get("fp", ""),
                ))

        return resp

    def SearchFullText(self, request: Any, context: Any = None) -> pb.SearchFullTextResponse:
        params: dict[str, Any] = {"q": request.query}
        if request.form_type:
            params["forms"] = request.form_type
        if request.start_date or request.end_date:
            params["dateRange"] = "custom"
            if request.start_date:
                params["startdt"] = request.start_date
            if request.end_date:
                params["enddt"] = request.end_date
        if request.limit and request.limit > 0:
            params["count"] = request.limit
        else:
            params["count"] = 10

        raw = self._get_efts("/search-index", params=params)

        resp = pb.SearchFullTextResponse(
            total_hits=raw.get("hits", {}).get("total", {}).get("value", 0),
        )

        for hit in raw.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            file_date = src.get("file_date", "")

            resp.hits.append(pb.FullTextHit(
                accession_number=src.get("file_num", ""),
                company_name=src.get("entity_name", ""),
                cik=str(src.get("entity_id", "")),
                form_type=src.get("form_type", ""),
                filing_date=file_date,
                document_url=src.get("file_url", ""),
                snippet="; ".join(hit.get("highlight", {}).get("full_text", [])) if hit.get("highlight") else "",
            ))

        return resp

    def GetFiling(self, request: Any, context: Any = None) -> pb.GetFilingResponse:
        accession = self._normalize_accession(request.accession_number)
        acc_no_dashes = accession.replace("-", "")
        # Extract CIK from first 10 digits of accession
        cik = accession[:10]

        raw = self._get_data(f"/submissions/CIK{cik}.json")

        resp = pb.GetFilingResponse(
            accession_number=accession,
            company_name=raw.get("name", ""),
            cik=cik,
        )

        # Search through recent filings for matching accession
        recent = raw.get("filings", {}).get("recent", {})
        accessions = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        descriptions = recent.get("primaryDocDescription", [])
        primary_docs = recent.get("primaryDocument", [])

        for i, acc in enumerate(accessions):
            if acc == accession:
                resp.form_type = forms[i] if i < len(forms) else ""
                resp.filing_date = dates[i] if i < len(dates) else ""
                resp.description = descriptions[i] if i < len(descriptions) else ""

                doc = primary_docs[i] if i < len(primary_docs) else ""
                if doc:
                    resp.documents.append(pb.FilingDocument(
                        filename=doc,
                        description=descriptions[i] if i < len(descriptions) else "",
                        type=forms[i] if i < len(forms) else "",
                        url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/{doc}",
                    ))
                break

        return resp

    def GetInsiderTransactions(self, request: Any, context: Any = None) -> pb.GetInsiderTransactionsResponse:
        cik = self._pad_cik(request.cik)
        limit = request.limit if request.limit > 0 else 20

        # Get company name from submissions
        sub_raw = self._get_data(f"/submissions/CIK{cik}.json")
        company_name = sub_raw.get("name", "")

        # Search for Form 4 filings for this company
        params: dict[str, Any] = {
            "q": "\"Form 4\"",
            "forms": "4",
            "count": limit,
        }
        # Filter by entity CIK
        raw = self._get_efts("/search-index", params=params)

        resp = pb.GetInsiderTransactionsResponse(
            company_name=company_name,
        )

        for hit in raw.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            if str(src.get("entity_id", "")) == str(int(cik)):
                resp.transactions.append(pb.InsiderTransaction(
                    insider_name=src.get("entity_name", ""),
                    title="",
                    transaction_date=src.get("file_date", ""),
                    transaction_type="",
                    shares=0,
                    price_per_share=0,
                    total_value=0,
                    shares_owned_after=0,
                ))

        return resp

    def GetInstitutionalHoldings(self, request: Any, context: Any = None) -> pb.GetInstitutionalHoldingsResponse:
        cik = self._pad_cik(request.cik)
        limit = request.limit if request.limit > 0 else 20

        # Get company name from submissions
        sub_raw = self._get_data(f"/submissions/CIK{cik}.json")
        company_name = sub_raw.get("name", "")

        # Search for 13F filings mentioning this company
        params: dict[str, Any] = {
            "q": company_name,
            "forms": "13F-HR",
            "count": limit,
        }
        raw = self._get_efts("/search-index", params=params)

        resp = pb.GetInstitutionalHoldingsResponse(
            company_name=company_name,
        )

        for hit in raw.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            resp.holdings.append(pb.InstitutionalHolding(
                institution_name=src.get("entity_name", ""),
                shares=0,
                value_usd=0,
                report_date=src.get("file_date", ""),
                institution_cik=str(src.get("entity_id", "")),
            ))

        return resp

    def GetTickerToCIK(self, request: Any, context: Any = None) -> pb.GetTickerToCIKResponse:
        ticker = request.ticker.upper()

        raw = self._get_data("/files/company_tickers.json")

        for entry in raw.values():
            if entry.get("ticker", "").upper() == ticker:
                cik = self._pad_cik(str(entry.get("cik_str", "")))
                return pb.GetTickerToCIKResponse(
                    cik=cik,
                    company_name=entry.get("title", ""),
                    ticker=ticker,
                )

        return pb.GetTickerToCIKResponse(ticker=ticker)

    def GetRecentFilings(self, request: Any, context: Any = None) -> pb.GetRecentFilingsResponse:
        params: dict[str, Any] = {}
        if request.form_type:
            params["forms"] = request.form_type
        if request.limit and request.limit > 0:
            params["count"] = request.limit
        else:
            params["count"] = 20

        raw = self._get_efts("/search-index", params=params)

        resp = pb.GetRecentFilingsResponse()

        for hit in raw.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            resp.filings.append(pb.Filing(
                accession_number=src.get("file_num", ""),
                form_type=src.get("form_type", ""),
                filing_date=src.get("file_date", ""),
                description=src.get("display_names", [""])[0] if src.get("display_names") else "",
                document_url=src.get("file_url", ""),
                cik=str(src.get("entity_id", "")),
                company_name=src.get("entity_name", ""),
                report_date=src.get("period_of_report", ""),
            ))

        return resp
