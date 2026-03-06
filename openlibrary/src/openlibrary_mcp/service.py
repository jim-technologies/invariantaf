"""OpenLibraryService — wraps the Open Library API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as pb

_BASE_URL = "https://openlibrary.org"


class OpenLibraryService:
    """Implements OpenLibraryService RPCs via the free Open Library API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30, follow_redirects=True)

    def _get(self, path: str, params: dict | None = None) -> Any:
        resp = self._http.get(f"{_BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    def SearchBooks(self, request: Any, context: Any = None) -> pb.SearchBooksResponse:
        limit = request.limit or 10
        raw = self._get("/search.json", params={"q": request.query, "limit": limit})

        resp = pb.SearchBooksResponse(num_found=raw.get("numFound", 0))
        for doc in raw.get("docs", []):
            resp.books.append(pb.BookResult(
                title=doc.get("title", ""),
                author_name=doc.get("author_name", []) or [],
                first_publish_year=doc.get("first_publish_year") or 0,
                isbn=doc.get("isbn", []) or [],
                cover_i=doc.get("cover_i") or 0,
                number_of_pages=doc.get("number_of_pages_median") or 0,
                subject=doc.get("subject", [])[:10] if doc.get("subject") else [],
                key=doc.get("key", ""),
            ))
        return resp

    def SearchByAuthor(self, request: Any, context: Any = None) -> pb.SearchByAuthorResponse:
        limit = request.limit or 10
        raw = self._get("/search.json", params={"author": request.name, "limit": limit})

        resp = pb.SearchByAuthorResponse(num_found=raw.get("numFound", 0))
        for doc in raw.get("docs", []):
            resp.books.append(pb.BookResult(
                title=doc.get("title", ""),
                author_name=doc.get("author_name", []) or [],
                first_publish_year=doc.get("first_publish_year") or 0,
                isbn=doc.get("isbn", []) or [],
                cover_i=doc.get("cover_i") or 0,
                number_of_pages=doc.get("number_of_pages_median") or 0,
                subject=doc.get("subject", [])[:10] if doc.get("subject") else [],
                key=doc.get("key", ""),
            ))
        return resp

    def SearchBySubject(self, request: Any, context: Any = None) -> pb.SearchBySubjectResponse:
        limit = request.limit or 10
        raw = self._get(f"/subjects/{request.subject}.json", params={"limit": limit})

        resp = pb.SearchBySubjectResponse(
            name=raw.get("name", ""),
            work_count=raw.get("work_count", 0),
        )
        for work in raw.get("works", []):
            authors = []
            for a in work.get("authors", []):
                name = a.get("name", "")
                if name:
                    authors.append(name)
            resp.works.append(pb.SubjectWork(
                title=work.get("title", ""),
                authors=authors,
                key=work.get("key", ""),
                cover_id=work.get("cover_id") or 0,
                edition_count=work.get("edition_count") or 0,
                first_publish_year=work.get("first_publish_year") or 0,
            ))
        return resp

    def GetBook(self, request: Any, context: Any = None) -> pb.GetBookResponse:
        raw = self._get(f"/works/{request.work_id}.json")

        desc = raw.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("value", "")

        covers = raw.get("covers", []) or []

        created = raw.get("created", "")
        if isinstance(created, dict):
            created = created.get("value", "")

        return pb.GetBookResponse(
            title=raw.get("title", ""),
            description=str(desc),
            subjects=raw.get("subjects", []) or [],
            covers=[c for c in covers if isinstance(c, int)],
            created=str(created),
            key=raw.get("key", ""),
        )

    def GetEdition(self, request: Any, context: Any = None) -> pb.GetEditionResponse:
        raw = self._get(f"/books/{request.edition_id}.json")

        covers = raw.get("covers", []) or []

        return pb.GetEditionResponse(
            title=raw.get("title", ""),
            publishers=raw.get("publishers", []) or [],
            publish_date=raw.get("publish_date", "") or "",
            isbn_13=raw.get("isbn_13", []) or [],
            isbn_10=raw.get("isbn_10", []) or [],
            number_of_pages=raw.get("number_of_pages") or 0,
            covers=[c for c in covers if isinstance(c, int)],
            key=raw.get("key", ""),
        )

    def GetAuthor(self, request: Any, context: Any = None) -> pb.GetAuthorResponse:
        raw = self._get(f"/authors/{request.author_id}.json")

        bio = raw.get("bio", "")
        if isinstance(bio, dict):
            bio = bio.get("value", "")

        photos = raw.get("photos", []) or []
        links_raw = raw.get("links", []) or []
        links = []
        for link in links_raw:
            if isinstance(link, dict):
                links.append(pb.AuthorLink(
                    title=link.get("title", ""),
                    url=link.get("url", ""),
                ))

        return pb.GetAuthorResponse(
            name=raw.get("name", ""),
            bio=str(bio),
            birth_date=raw.get("birth_date", "") or "",
            death_date=raw.get("death_date", "") or "",
            photos=[p for p in photos if isinstance(p, int)],
            links=links,
            key=raw.get("key", ""),
        )

    def GetAuthorWorks(self, request: Any, context: Any = None) -> pb.GetAuthorWorksResponse:
        limit = request.limit or 10
        raw = self._get(f"/authors/{request.author_id}/works.json", params={"limit": limit})

        resp = pb.GetAuthorWorksResponse(size=raw.get("size", 0))
        for entry in raw.get("entries", []):
            covers = entry.get("covers", []) or []
            resp.works.append(pb.AuthorWork(
                title=entry.get("title", ""),
                key=entry.get("key", ""),
                covers=[c for c in covers if isinstance(c, int)],
                first_publish_year=entry.get("first_publish_year") or 0,
            ))
        return resp

    def GetBookByISBN(self, request: Any, context: Any = None) -> pb.GetBookByISBNResponse:
        raw = self._get(f"/isbn/{request.isbn}.json")

        covers = raw.get("covers", []) or []

        return pb.GetBookByISBNResponse(
            title=raw.get("title", ""),
            publishers=raw.get("publishers", []) or [],
            publish_date=raw.get("publish_date", "") or "",
            isbn_13=raw.get("isbn_13", []) or [],
            isbn_10=raw.get("isbn_10", []) or [],
            number_of_pages=raw.get("number_of_pages") or 0,
            covers=[c for c in covers if isinstance(c, int)],
            key=raw.get("key", ""),
        )

    def GetRecentChanges(self, request: Any, context: Any = None) -> pb.GetRecentChangesResponse:
        limit = request.limit or 10
        raw = self._get("/recentchanges.json", params={"limit": limit})

        resp = pb.GetRecentChangesResponse()
        if isinstance(raw, list):
            for change in raw:
                author_data = change.get("author", {})
                author_str = author_data.get("key", "") if isinstance(author_data, dict) else str(author_data)
                resp.changes.append(pb.RecentChange(
                    kind=change.get("kind", ""),
                    author=author_str,
                    timestamp=change.get("timestamp", "") or "",
                    comment=change.get("comment", "") or "",
                    id=str(change.get("id", "")),
                ))
        return resp

    def GetTrendingBooks(self, request: Any, context: Any = None) -> pb.GetTrendingBooksResponse:
        limit = request.limit or 10
        raw = self._get("/trending/daily.json", params={"limit": limit})

        resp = pb.GetTrendingBooksResponse()
        for work in raw.get("works", []):
            author_name = ""
            author_names = work.get("author_name", [])
            if author_names:
                author_name = author_names[0]
            availability = work.get("availability", {})
            avail_str = ""
            if isinstance(availability, dict):
                avail_str = availability.get("status", "")

            resp.books.append(pb.TrendingBook(
                title=work.get("title", ""),
                author_name=author_name,
                key=work.get("key", ""),
                cover_i=work.get("cover_i") or 0,
                first_publish_year=work.get("first_publish_year") or 0,
                availability=avail_str,
            ))
        return resp
