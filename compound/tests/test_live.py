"""Live integration tests for Compound Finance API -- hits the real API.

Run with:
    COMPOUND_RUN_LIVE_TESTS=1 uv run python -m pytest tests/test_live.py -v

NOTE: The Compound v2 API (api.compound.finance) may return 410 Gone as it
has been deprecated.  Tests skip gracefully when the API is unavailable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("COMPOUND_RUN_LIVE_TESTS") != "1",
    reason="Set COMPOUND_RUN_LIVE_TESTS=1 to run live Compound API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from compound_mcp.service import CompoundService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-compound-live", version="0.0.1"
    )
    servicer = CompoundService()
    srv.register(servicer)
    yield srv
    srv.stop()


def _cli_or_skip(live_server, args):
    """Call CLI and skip if the API returns an HTTP error (410 Gone, etc)."""
    try:
        return live_server._cli(args)
    except Exception as exc:
        msg = str(exc)
        if "410" in msg or "Gone" in msg or "503" in msg or "502" in msg:
            pytest.skip(f"Compound API unavailable: {msg[:120]}")
        raise


class TestLiveListCTokens:
    def test_returns_ctokens(self, live_server):
        result = _cli_or_skip(live_server, ["CompoundService", "ListCTokens"])
        assert "ctokens" in result
        ctokens = result["ctokens"]
        assert isinstance(ctokens, list)
        assert len(ctokens) > 0

    def test_ctoken_has_address(self, live_server):
        result = _cli_or_skip(live_server, ["CompoundService", "ListCTokens"])
        ct = result["ctokens"][0]
        assert "address" in ct or "token_address" in ct


class TestLiveListProposals:
    def test_returns_proposals(self, live_server):
        result = _cli_or_skip(live_server, ["CompoundService", "ListProposals"])
        assert "proposals" in result
        proposals = result["proposals"]
        assert isinstance(proposals, list)
        assert len(proposals) > 0

    def test_proposal_has_title(self, live_server):
        result = _cli_or_skip(live_server, ["CompoundService", "ListProposals"])
        p = result["proposals"][0]
        assert "title" in p
