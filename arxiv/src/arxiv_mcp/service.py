"""ArxivService — wraps the arXiv API into proto RPCs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from arxiv_mcp.gen.arxiv.v1 import arxiv_pb2 as pb

_BASE_URL = "http://export.arxiv.org/api/query"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

# Built-in category reference list.
_CATEGORIES = [
    ("cs.AI", "Artificial Intelligence", "Covers all areas of AI except Vision, Robotics, Machine Learning, Multiagent Systems, and Computation and Language."),
    ("cs.CL", "Computation and Language", "Natural language processing and computational linguistics."),
    ("cs.CV", "Computer Vision and Pattern Recognition", "Image processing, computer vision, pattern recognition, and scene understanding."),
    ("cs.LG", "Machine Learning", "Papers on all aspects of machine learning research."),
    ("cs.CR", "Cryptography and Security", "Covers all areas of cryptography and security."),
    ("cs.DB", "Databases", "Database management, data mining, and data processing."),
    ("cs.DC", "Distributed, Parallel, and Cluster Computing", "Distributed computing, parallel algorithms, and fault tolerance."),
    ("cs.DS", "Data Structures and Algorithms", "Algorithms and data structures for computational problems."),
    ("cs.IR", "Information Retrieval", "Search engines, document analysis, and information filtering."),
    ("cs.NE", "Neural and Evolutionary Computing", "Neural networks, genetic algorithms, and artificial life."),
    ("cs.PL", "Programming Languages", "Programming language design, implementation, and analysis."),
    ("cs.RO", "Robotics", "Covers all areas of robotics research."),
    ("cs.SE", "Software Engineering", "Software development, testing, maintenance, and evolution."),
    ("cs.SI", "Social and Information Networks", "Social networks, information diffusion, and graph mining."),
    ("cs.SY", "Systems and Control", "Control theory, systems engineering, and automation."),
    ("math.AG", "Algebraic Geometry", "Algebraic varieties, schemes, sheaves, and related topics."),
    ("math.AP", "Analysis of PDEs", "Partial differential equations and their applications."),
    ("math.CO", "Combinatorics", "Discrete mathematics and combinatorial optimization."),
    ("math.NA", "Numerical Analysis", "Numerical methods and scientific computing."),
    ("math.OC", "Optimization and Control", "Mathematical optimization, operations research, and control."),
    ("math.PR", "Probability", "Probability theory and stochastic processes."),
    ("math.ST", "Statistics Theory", "Statistical theory, methodology, and applications."),
    ("stat.ML", "Machine Learning (Statistics)", "Statistical approaches to machine learning."),
    ("stat.ME", "Methodology", "Statistical methodology and applications."),
    ("physics.hep-th", "High Energy Physics - Theory", "Theoretical high energy physics and quantum field theory."),
    ("physics.hep-ph", "High Energy Physics - Phenomenology", "Phenomenological studies of high energy physics."),
    ("quant-ph", "Quantum Physics", "Quantum information, quantum computation, and quantum mechanics."),
    ("cond-mat.stat-mech", "Statistical Mechanics", "Statistical mechanics and thermodynamics."),
    ("astro-ph", "Astrophysics", "Astrophysics and astronomy research."),
    ("q-fin.ST", "Statistical Finance", "Statistical analysis of financial markets."),
    ("q-fin.PM", "Portfolio Management", "Portfolio optimization and management."),
    ("q-fin.TR", "Trading and Market Microstructure", "Trading strategies and market microstructure."),
    ("eess.SP", "Signal Processing", "Signal processing theory and applications."),
    ("eess.AS", "Audio and Speech Processing", "Audio and speech signal processing."),
]


def _parse_entries(xml_text: str) -> list[pb.Paper]:
    """Parse Atom XML response from arXiv into Paper protos."""
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title = entry.findtext(f"{ATOM_NS}title", "").strip().replace("\n", " ")
        summary = entry.findtext(f"{ATOM_NS}summary", "").strip()
        published = entry.findtext(f"{ATOM_NS}published", "")
        updated = entry.findtext(f"{ATOM_NS}updated", "")

        # Extract arxiv ID from the entry id URL.
        raw_id = entry.findtext(f"{ATOM_NS}id", "")
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

        authors = [
            a.findtext(f"{ATOM_NS}name", "")
            for a in entry.findall(f"{ATOM_NS}author")
        ]

        # Collect categories: primary + all others.
        categories = []
        primary = entry.find(f"{ARXIV_NS}primary_category")
        if primary is not None:
            term = primary.get("term", "")
            if term:
                categories.append(term)
        for cat in entry.findall(f"{ATOM_NS}category"):
            term = cat.get("term", "")
            if term and term not in categories:
                categories.append(term)

        # Find PDF link.
        pdf_url = ""
        arxiv_url = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
            if link.get("rel") == "alternate":
                arxiv_url = link.get("href", "")

        papers.append(pb.Paper(
            arxiv_id=arxiv_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            published=published,
            updated=updated,
            pdf_url=pdf_url,
            arxiv_url=arxiv_url,
        ))
    return papers


class ArxivService:
    """Implements ArxivService RPCs via the free arXiv API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _get(self, params: dict) -> str:
        resp = self._http.get(_BASE_URL, params=params)
        resp.raise_for_status()
        return resp.text

    def Search(self, request: Any, context: Any = None) -> pb.SearchResponse:
        limit = request.limit or 10
        xml = self._get({"search_query": f"all:{request.query}", "max_results": limit})
        return pb.SearchResponse(papers=_parse_entries(xml))

    def GetPaper(self, request: Any, context: Any = None) -> pb.GetPaperResponse:
        xml = self._get({"id_list": request.arxiv_id})
        papers = _parse_entries(xml)
        return pb.GetPaperResponse(paper=papers[0] if papers else None)

    def SearchByAuthor(self, request: Any, context: Any = None) -> pb.SearchByAuthorResponse:
        limit = request.limit or 10
        xml = self._get({"search_query": f"au:{request.author}", "max_results": limit})
        return pb.SearchByAuthorResponse(papers=_parse_entries(xml))

    def SearchByTitle(self, request: Any, context: Any = None) -> pb.SearchByTitleResponse:
        limit = request.limit or 10
        xml = self._get({"search_query": f"ti:{request.title}", "max_results": limit})
        return pb.SearchByTitleResponse(papers=_parse_entries(xml))

    def SearchByCategory(self, request: Any, context: Any = None) -> pb.SearchByCategoryResponse:
        limit = request.limit or 10
        xml = self._get({"search_query": f"cat:{request.category}", "max_results": limit})
        return pb.SearchByCategoryResponse(papers=_parse_entries(xml))

    def SearchByAbstract(self, request: Any, context: Any = None) -> pb.SearchByAbstractResponse:
        limit = request.limit or 10
        xml = self._get({"search_query": f"abs:{request.query}", "max_results": limit})
        return pb.SearchByAbstractResponse(papers=_parse_entries(xml))

    def GetRecent(self, request: Any, context: Any = None) -> pb.GetRecentResponse:
        limit = request.limit or 10
        xml = self._get({
            "search_query": f"cat:{request.category}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit,
        })
        return pb.GetRecentResponse(papers=_parse_entries(xml))

    def GetMultiple(self, request: Any, context: Any = None) -> pb.GetMultipleResponse:
        id_list = ",".join(request.arxiv_ids)
        xml = self._get({"id_list": id_list})
        return pb.GetMultipleResponse(papers=_parse_entries(xml))

    def AdvancedSearch(self, request: Any, context: Any = None) -> pb.AdvancedSearchResponse:
        parts = []
        if request.author:
            parts.append(f"au:{request.author}")
        if request.title:
            parts.append(f"ti:{request.title}")
        if request.abstract:
            parts.append(f"abs:{request.abstract}")
        if request.category:
            parts.append(f"cat:{request.category}")

        query = "+AND+".join(parts) if parts else "all:*"
        limit = request.limit or 10
        xml = self._get({"search_query": query, "max_results": limit})
        return pb.AdvancedSearchResponse(papers=_parse_entries(xml))

    def GetCategories(self, request: Any, context: Any = None) -> pb.GetCategoriesResponse:
        resp = pb.GetCategoriesResponse()
        for code, name, description in _CATEGORIES:
            resp.categories.append(pb.ArxivCategory(
                code=code,
                name=name,
                description=description,
            ))
        return resp
