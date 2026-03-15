"""Live integration tests for GeminiPredictionsService.

Gate: set GEMINI_RUN_LIVE_TESTS=1 to run (hits real Gemini API).
"""

from __future__ import annotations

import os

import pytest

from geminipredictions_mcp.gen.geminipredictions.v1 import geminipredictions_pb2 as pb
from geminipredictions_mcp.service import GeminiPredictionsService

LIVE = os.getenv("GEMINI_RUN_LIVE_TESTS") == "1"
skip_unless_live = pytest.mark.skipif(
    not LIVE,
    reason="set GEMINI_RUN_LIVE_TESTS=1 to run live integration tests",
)


@pytest.fixture
def svc() -> GeminiPredictionsService:
    base_url = (os.getenv("GEMINI_BASE_URL") or "").strip() or None
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip() or ""
    kwargs: dict = {}
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return GeminiPredictionsService(**kwargs)


# ------------------------------------------------------------------
# Smoke test (always runs)
# ------------------------------------------------------------------


def test_smoke_service_init():
    svc = GeminiPredictionsService()
    assert svc is not None
    assert svc._base_url == "https://api.gemini.com"


# ------------------------------------------------------------------
# Live tests
# ------------------------------------------------------------------


@skip_unless_live
def test_live_list_events(svc: GeminiPredictionsService):
    resp = svc.ListEvents(pb.ListEventsRequest())
    assert len(resp.events) > 0
    first = resp.events[0]
    assert first.title
    assert first.ticker
    print(f"ListEvents: {len(resp.events)} events; first: {first.title}")


@skip_unless_live
def test_live_list_events_with_filters(svc: GeminiPredictionsService):
    req = pb.ListEventsRequest(status="active", category="Crypto")
    resp = svc.ListEvents(req)
    print(f"ListEvents (active, Crypto): {len(resp.events)} events")
    for e in resp.events:
        assert e.category == "Crypto", f"expected Crypto, got {e.category}"


@skip_unless_live
def test_live_get_event(svc: GeminiPredictionsService):
    # First get an event ticker
    list_resp = svc.ListEvents(pb.ListEventsRequest(status="active"))
    if not list_resp.events:
        pytest.skip("no active events")
    ticker = list_resp.events[0].ticker
    if not ticker:
        pytest.skip("first event has no ticker")

    resp = svc.GetEvent(pb.GetEventRequest(event_ticker=ticker))
    assert resp.event.title
    print(f"GetEvent({ticker}): {resp.event.title}")


@skip_unless_live
def test_live_list_newly_listed_events(svc: GeminiPredictionsService):
    resp = svc.ListNewlyListedEvents(pb.ListNewlyListedEventsRequest())
    print(f"ListNewlyListedEvents: {len(resp.events)} events")


@skip_unless_live
def test_live_list_recently_settled_events(svc: GeminiPredictionsService):
    resp = svc.ListRecentlySettledEvents(pb.ListRecentlySettledEventsRequest())
    print(f"ListRecentlySettledEvents: {len(resp.events)} events")


@skip_unless_live
def test_live_list_upcoming_events(svc: GeminiPredictionsService):
    resp = svc.ListUpcomingEvents(pb.ListUpcomingEventsRequest())
    print(f"ListUpcomingEvents: {len(resp.events)} events")


@skip_unless_live
def test_live_list_categories(svc: GeminiPredictionsService):
    resp = svc.ListCategories(pb.ListCategoriesRequest())
    assert len(resp.categories) > 0
    print(f"ListCategories: {resp.categories}")
