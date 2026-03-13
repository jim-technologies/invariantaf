"""Live integration tests for Dune Analytics API -- hits the real API.

Run with:
    DUNE_RUN_LIVE_TESTS=1 DUNE_API_KEY=<your-key> uv run python -m pytest tests/test_live.py -v

Requires a valid DUNE_API_KEY environment variable.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

pytestmark = pytest.mark.skipif(
    os.getenv("DUNE_RUN_LIVE_TESTS") != "1",
    reason="Set DUNE_RUN_LIVE_TESTS=1 and DUNE_API_KEY to run live Dune API tests",
)


@pytest.fixture(scope="module")
def live_server():
    from invariant import Server

    from dune_mcp.service import DuneService

    srv = Server.from_descriptor(
        DESCRIPTOR_PATH, name="test-dune-live", version="0.0.1"
    )
    servicer = DuneService()
    srv.register(servicer)
    yield srv
    srv.stop()


# --- ExecuteQuery + GetExecutionStatus + GetExecutionResults ---


class TestLiveExecuteAndGetResults:
    """End-to-end: execute a simple public query, poll, and fetch results."""

    def test_execute_query(self, live_server):
        # Query 1234567 is a placeholder -- use a known public query ID.
        result = live_server._cli(
            [
                "DuneService",
                "ExecuteQuery",
                "-r",
                json.dumps({"queryId": "4"}),
            ]
        )
        assert "executionId" in result or "execution_id" in result

    def test_get_execution_status(self, live_server):
        # First execute, then check status.
        exec_result = live_server._cli(
            [
                "DuneService",
                "ExecuteQuery",
                "-r",
                json.dumps({"queryId": "4"}),
            ]
        )
        exec_id = exec_result.get("executionId") or exec_result.get("execution_id")
        assert exec_id

        status = live_server._cli(
            [
                "DuneService",
                "GetExecutionStatus",
                "-r",
                json.dumps({"executionId": exec_id}),
            ]
        )
        assert "execution" in status
        assert "state" in status["execution"]


# --- GetLatestResults ---


class TestLiveGetLatestResults:
    def test_get_latest_results(self, live_server):
        result = live_server._cli(
            [
                "DuneService",
                "GetLatestResults",
                "-r",
                json.dumps({"queryId": "4"}),
            ]
        )
        assert "execution" in result or "rows" in result
