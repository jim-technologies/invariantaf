"""Live integration tests for Polling API -- hits PredictIt and Metaculus.

Run with:
    POLLING_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

Both PredictIt and Metaculus are public, unauthenticated APIs.
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
    os.getenv("POLLING_RUN_LIVE_TESTS") != "1",
    reason="Set POLLING_RUN_LIVE_TESTS=1 to run live Polling API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from polling_mcp.service import PollingService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-polling-live", version="0.0.1"
    )
    servicer = PollingService()
    srv.register(servicer)
    yield srv
    srv.stop()


def _cli_or_skip(live_server, args):
    """Call CLI and skip if the API returns an HTTP error."""
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("403", "404", "410", "429", "500", "502", "503")):
            pytest.skip(f"API unavailable: {msg[:120]}")
        raise


class TestLivePredictIt:
    def test_list_markets(self, live_server):
        result = _cli_or_skip(live_server, ["PollingService", "ListPredictItMarkets"])
        assert "markets" in result
        markets = result["markets"]
        assert isinstance(markets, list)
        # PredictIt may have no active markets -- just check the shape
        if len(markets) > 0:
            m = markets[0]
            assert "id" in m
            assert "name" in m

    def test_market_has_contracts(self, live_server):
        result = _cli_or_skip(live_server, ["PollingService", "ListPredictItMarkets"])
        markets = result.get("markets", [])
        if len(markets) == 0:
            pytest.skip("No PredictIt markets available")
        m = markets[0]
        assert "contracts" in m
        if len(m["contracts"]) > 0:
            c = m["contracts"][0]
            assert "name" in c
            assert "last_trade_price" in c or "lastTradePrice" in c


class TestLiveMetaculus:
    def test_list_questions(self, live_server):
        result = _cli_or_skip(
            live_server,
            ["PollingService", "ListMetaculusQuestions", "-r", json.dumps({"limit": 5})],
        )
        assert "questions" in result
        questions = result["questions"]
        assert isinstance(questions, list)
        assert len(questions) > 0

    def test_question_has_fields(self, live_server):
        result = _cli_or_skip(
            live_server,
            ["PollingService", "ListMetaculusQuestions", "-r", json.dumps({"limit": 3})],
        )
        questions = result.get("questions", [])
        if len(questions) == 0:
            pytest.skip("No Metaculus questions returned")
        q = questions[0]
        assert "id" in q
        assert "title" in q

    def test_get_question(self, live_server):
        # First get a question ID from the list
        result = _cli_or_skip(
            live_server,
            ["PollingService", "ListMetaculusQuestions", "-r", json.dumps({"limit": 1})],
        )
        questions = result.get("questions", [])
        if len(questions) == 0:
            pytest.skip("No Metaculus questions to look up")
        qid = questions[0]["id"]
        detail = _cli_or_skip(
            live_server,
            ["PollingService", "GetMetaculusQuestion", "-r", json.dumps({"id": qid})],
        )
        assert "question" in detail
        assert detail["question"]["id"] == qid
