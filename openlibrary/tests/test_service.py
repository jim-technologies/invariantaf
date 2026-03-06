"""Unit tests — every OpenLibraryService RPC method, mocked HTTP."""

import pytest
from unittest.mock import MagicMock

from openlibrary_mcp.gen.openlibrary.v1 import openlibrary_pb2 as pb
from tests.conftest import (
    FAKE_AUTHOR,
    FAKE_AUTHOR_WORKS,
    FAKE_BOOK,
    FAKE_EDITION,
    FAKE_ISBN,
    FAKE_RECENT_CHANGES,
    FAKE_SEARCH,
    FAKE_SEARCH_BY_AUTHOR,
    FAKE_SUBJECT,
    FAKE_TRENDING,
)


class TestSearchBooks:
    def test_returns_books(self, service):
        resp = service.SearchBooks(pb.SearchBooksRequest(query="lord of the rings", limit=10))
        assert len(resp.books) == 2
        assert resp.num_found == 2

    def test_first_book_fields(self, service):
        resp = service.SearchBooks(pb.SearchBooksRequest(query="lord of the rings"))
        book = resp.books[0]
        assert book.title == "The Lord of the Rings"
        assert "J.R.R. Tolkien" in book.author_name
        assert book.first_publish_year == 1954
        assert "9780261103573" in book.isbn
        assert book.cover_i == 8474036
        assert book.number_of_pages == 1216
        assert "Fantasy" in book.subject
        assert book.key == "/works/OL45883W"

    def test_second_book(self, service):
        resp = service.SearchBooks(pb.SearchBooksRequest(query="hobbit"))
        book = resp.books[1]
        assert book.title == "The Hobbit"
        assert book.first_publish_year == 1937

    def test_default_limit(self, service, mock_http):
        service.SearchBooks(pb.SearchBooksRequest(query="test"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("limit") == 10

    def test_empty_response(self, service, mock_http):
        mock_http.get.side_effect = lambda url, params=None: MagicMock(
            raise_for_status=MagicMock(), json=MagicMock(return_value={"numFound": 0, "docs": []})
        )
        resp = service.SearchBooks(pb.SearchBooksRequest(query="nonexistent"))
        assert len(resp.books) == 0
        assert resp.num_found == 0


class TestSearchByAuthor:
    def test_returns_books(self, service):
        resp = service.SearchByAuthor(pb.SearchByAuthorRequest(name="George Orwell"))
        assert len(resp.books) == 1
        assert resp.num_found == 1

    def test_book_fields(self, service):
        resp = service.SearchByAuthor(pb.SearchByAuthorRequest(name="George Orwell"))
        book = resp.books[0]
        assert book.title == "1984"
        assert "George Orwell" in book.author_name
        assert book.first_publish_year == 1949

    def test_passes_author_param(self, service, mock_http):
        service.SearchByAuthor(pb.SearchByAuthorRequest(name="tolkien"))
        call_args = mock_http.get.call_args
        assert call_args[1].get("params", {}).get("author") == "tolkien"


class TestSearchBySubject:
    def test_returns_works(self, service):
        resp = service.SearchBySubject(pb.SearchBySubjectRequest(subject="fantasy"))
        assert len(resp.works) == 2
        assert resp.name == "Fantasy"
        assert resp.work_count == 50000

    def test_work_fields(self, service):
        resp = service.SearchBySubject(pb.SearchBySubjectRequest(subject="fantasy"))
        work = resp.works[0]
        assert work.title == "A Game of Thrones"
        assert "George R.R. Martin" in work.authors
        assert work.key == "/works/OL17346379W"
        assert work.cover_id == 8451036
        assert work.edition_count == 85
        assert work.first_publish_year == 1996

    def test_second_work(self, service):
        resp = service.SearchBySubject(pb.SearchBySubjectRequest(subject="fantasy"))
        work = resp.works[1]
        assert work.title == "The Name of the Wind"
        assert work.first_publish_year == 2007


class TestGetBook:
    def test_basic_fields(self, service):
        resp = service.GetBook(pb.GetBookRequest(work_id="OL45883W"))
        assert resp.title == "The Lord of the Rings"
        assert resp.key == "/works/OL45883W"

    def test_description(self, service):
        resp = service.GetBook(pb.GetBookRequest(work_id="OL45883W"))
        assert "epic high-fantasy" in resp.description

    def test_subjects(self, service):
        resp = service.GetBook(pb.GetBookRequest(work_id="OL45883W"))
        assert "Fantasy" in resp.subjects
        assert "Fiction" in resp.subjects
        assert "Adventure" in resp.subjects

    def test_covers(self, service):
        resp = service.GetBook(pb.GetBookRequest(work_id="OL45883W"))
        assert 8474036 in resp.covers
        assert 12345 in resp.covers

    def test_created(self, service):
        resp = service.GetBook(pb.GetBookRequest(work_id="OL45883W"))
        assert "2008-04-01" in resp.created


class TestGetEdition:
    def test_basic_fields(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert resp.title == "The Lord of the Rings"
        assert resp.key == "/books/OL7353617M"

    def test_publishers(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert "Houghton Mifflin" in resp.publishers

    def test_publish_date(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert resp.publish_date == "2004"

    def test_isbn_fields(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert "9780618640157" in resp.isbn_13
        assert "0618640150" in resp.isbn_10

    def test_page_count(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert resp.number_of_pages == 1216

    def test_covers(self, service):
        resp = service.GetEdition(pb.GetEditionRequest(edition_id="OL7353617M"))
        assert 8474036 in resp.covers


class TestGetAuthor:
    def test_basic_fields(self, service):
        resp = service.GetAuthor(pb.GetAuthorRequest(author_id="OL23919A"))
        assert resp.name == "J.R.R. Tolkien"
        assert resp.key == "/authors/OL23919A"

    def test_bio(self, service):
        resp = service.GetAuthor(pb.GetAuthorRequest(author_id="OL23919A"))
        assert "English writer" in resp.bio

    def test_dates(self, service):
        resp = service.GetAuthor(pb.GetAuthorRequest(author_id="OL23919A"))
        assert resp.birth_date == "3 January 1892"
        assert resp.death_date == "2 September 1973"

    def test_photos(self, service):
        resp = service.GetAuthor(pb.GetAuthorRequest(author_id="OL23919A"))
        assert 6304727 in resp.photos
        assert 6271462 in resp.photos

    def test_links(self, service):
        resp = service.GetAuthor(pb.GetAuthorRequest(author_id="OL23919A"))
        assert len(resp.links) == 1
        assert resp.links[0].title == "Wikipedia"
        assert "wikipedia.org" in resp.links[0].url


class TestGetAuthorWorks:
    def test_returns_works(self, service):
        resp = service.GetAuthorWorks(pb.GetAuthorWorksRequest(author_id="OL23919A"))
        assert resp.size == 50
        assert len(resp.works) == 2

    def test_work_fields(self, service):
        resp = service.GetAuthorWorks(pb.GetAuthorWorksRequest(author_id="OL23919A"))
        work = resp.works[0]
        assert work.title == "The Lord of the Rings"
        assert work.key == "/works/OL45883W"
        assert 8474036 in work.covers
        assert work.first_publish_year == 1954

    def test_second_work(self, service):
        resp = service.GetAuthorWorks(pb.GetAuthorWorksRequest(author_id="OL23919A"))
        work = resp.works[1]
        assert work.title == "The Hobbit"
        assert work.first_publish_year == 1937


class TestGetBookByISBN:
    def test_basic_fields(self, service):
        resp = service.GetBookByISBN(pb.GetBookByISBNRequest(isbn="9780261103573"))
        assert resp.title == "The Lord of the Rings"
        assert resp.key == "/books/OL7353617M"

    def test_isbn_fields(self, service):
        resp = service.GetBookByISBN(pb.GetBookByISBNRequest(isbn="9780261103573"))
        assert "9780618640157" in resp.isbn_13
        assert "0618640150" in resp.isbn_10

    def test_publishers(self, service):
        resp = service.GetBookByISBN(pb.GetBookByISBNRequest(isbn="9780261103573"))
        assert "Houghton Mifflin" in resp.publishers

    def test_page_count(self, service):
        resp = service.GetBookByISBN(pb.GetBookByISBNRequest(isbn="9780261103573"))
        assert resp.number_of_pages == 1216


class TestGetRecentChanges:
    def test_returns_changes(self, service):
        resp = service.GetRecentChanges(pb.GetRecentChangesRequest())
        assert len(resp.changes) == 2

    def test_change_fields(self, service):
        resp = service.GetRecentChanges(pb.GetRecentChangesRequest())
        change = resp.changes[0]
        assert change.kind == "edit-book"
        assert "/people/ImportBot" in change.author
        assert "2025-01-15" in change.timestamp
        assert change.comment == "Updated book metadata"
        assert change.id == "12345"

    def test_second_change(self, service):
        resp = service.GetRecentChanges(pb.GetRecentChangesRequest())
        change = resp.changes[1]
        assert change.kind == "add-book"
        assert change.comment == "Added new book"


class TestGetTrendingBooks:
    def test_returns_books(self, service):
        resp = service.GetTrendingBooks(pb.GetTrendingBooksRequest())
        assert len(resp.books) == 2

    def test_book_fields(self, service):
        resp = service.GetTrendingBooks(pb.GetTrendingBooksRequest())
        book = resp.books[0]
        assert book.title == "Dune"
        assert book.author_name == "Frank Herbert"
        assert book.key == "/works/OL893415W"
        assert book.cover_i == 8231856
        assert book.first_publish_year == 1965
        assert book.availability == "borrow_available"

    def test_second_book(self, service):
        resp = service.GetTrendingBooks(pb.GetTrendingBooksRequest())
        book = resp.books[1]
        assert book.title == "Project Hail Mary"
        assert book.author_name == "Andy Weir"
        assert book.first_publish_year == 2021
