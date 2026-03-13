"""Unit tests -- every DuneService RPC method, mocked HTTP."""

import json

import pytest
from unittest.mock import MagicMock, patch

from dune_mcp.gen.dune.v1 import dune_pb2 as pb
from tests.conftest import (
    FAKE_EXECUTE_RESPONSE,
    FAKE_STATUS_COMPLETED,
    FAKE_STATUS_PENDING,
    FAKE_RESULTS,
    FAKE_LATEST_RESULTS,
    FAKE_CANCEL_RESPONSE,
)


class TestExecuteQuery:
    def test_returns_execution_id(self, service):
        resp = service.ExecuteQuery(pb.ExecuteQueryRequest(query_id="1234567"))
        assert resp.execution_id == "01HN7ABCDEF123456789"

    def test_returns_pending_state(self, service):
        resp = service.ExecuteQuery(pb.ExecuteQueryRequest(query_id="1234567"))
        assert resp.state == "QUERY_STATE_PENDING"

    def test_posts_to_correct_url(self, service, mock_http):
        service.ExecuteQuery(pb.ExecuteQueryRequest(query_id="1234567"))
        call_url = mock_http.post.call_args[0][0]
        assert "/query/1234567/execute" in call_url

    def test_sends_api_key_header(self, service, mock_http):
        with patch.dict("os.environ", {"DUNE_API_KEY": "test_api_key_123"}):
            service.ExecuteQuery(pb.ExecuteQueryRequest(query_id="1234567"))
            call_headers = mock_http.post.call_args[1].get("headers") or mock_http.post.call_args[1].get("headers", {})
            assert call_headers.get("X-Dune-API-Key") == "test_api_key_123"

    def test_with_query_parameters(self, service, mock_http):
        params = [
            pb.QueryParameter(key="token_address", value="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", type="text"),
            pb.QueryParameter(key="days", value="7", type="number"),
        ]
        service.ExecuteQuery(pb.ExecuteQueryRequest(
            query_id="1234567",
            query_parameters=params,
        ))
        call_json = mock_http.post.call_args[1].get("json")
        assert call_json is not None
        assert "query_parameters" in call_json
        assert call_json["query_parameters"]["token_address"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        assert call_json["query_parameters"]["days"] == "7"

    def test_without_query_parameters(self, service, mock_http):
        service.ExecuteQuery(pb.ExecuteQueryRequest(query_id="1234567"))
        call_json = mock_http.post.call_args[1].get("json")
        assert call_json is None


class TestGetExecutionStatus:
    def test_returns_completed_status(self, service):
        resp = service.GetExecutionStatus(
            pb.GetExecutionStatusRequest(execution_id="01HN7ABCDEF123456789")
        )
        assert resp.execution.state == "QUERY_STATE_COMPLETED"

    def test_returns_execution_metadata(self, service):
        resp = service.GetExecutionStatus(
            pb.GetExecutionStatusRequest(execution_id="01HN7ABCDEF123456789")
        )
        meta = resp.execution
        assert meta.execution_id == "01HN7ABCDEF123456789"
        assert meta.query_id == "1234567"
        assert meta.submitted_at == "2024-01-15T10:30:00.000Z"
        assert meta.execution_started_at == "2024-01-15T10:30:01.000Z"
        assert meta.execution_ended_at == "2024-01-15T10:30:05.000Z"
        assert meta.expires_at == "2024-01-15T22:30:05.000Z"

    def test_pending_status(self, service):
        resp = service.GetExecutionStatus(
            pb.GetExecutionStatusRequest(execution_id="01HN7PENDING")
        )
        assert resp.execution.state == "QUERY_STATE_EXECUTING"
        assert resp.execution.execution_ended_at == ""

    def test_calls_correct_url(self, service, mock_http):
        service.GetExecutionStatus(
            pb.GetExecutionStatusRequest(execution_id="01HN7ABCDEF123456789")
        )
        call_url = mock_http.get.call_args[0][0]
        assert "/execution/01HN7ABCDEF123456789/status" in call_url


class TestGetExecutionResults:
    def test_returns_rows(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        assert len(resp.rows) == 3

    def test_rows_are_json_strings(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        row = json.loads(resp.rows[0])
        assert row["block_date"] == "2024-01-15"
        assert row["volume_usd"] == 1500000000.50
        assert row["tx_count"] == 42000

    def test_result_metadata(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        meta = resp.result_metadata
        assert meta.column_names == ["block_date", "volume_usd", "tx_count"]
        assert meta.row_count == 3
        assert meta.result_set_bytes == 1024
        assert meta.truncated is False
        assert meta.execution_time_millis == 3200.8

    def test_execution_metadata(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        meta = resp.execution
        assert meta.state == "QUERY_STATE_COMPLETED"
        assert meta.execution_id == "01HN7ABCDEF123456789"

    def test_calls_correct_url(self, service, mock_http):
        service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        call_url = mock_http.get.call_args[0][0]
        assert "/execution/01HN7ABCDEF123456789/results" in call_url

    def test_second_row(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        row = json.loads(resp.rows[1])
        assert row["block_date"] == "2024-01-14"
        assert row["volume_usd"] == 1350000000.75
        assert row["tx_count"] == 39500

    def test_third_row(self, service):
        resp = service.GetExecutionResults(
            pb.GetExecutionResultsRequest(execution_id="01HN7ABCDEF123456789")
        )
        row = json.loads(resp.rows[2])
        assert row["block_date"] == "2024-01-13"


class TestGetLatestResults:
    def test_returns_rows(self, service):
        resp = service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        assert len(resp.rows) == 2

    def test_rows_are_json_strings(self, service):
        resp = service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        row = json.loads(resp.rows[0])
        assert row["token"] == "WETH"
        assert row["holders"] == 500000
        assert row["market_cap"] == 250000000000

    def test_result_metadata(self, service):
        resp = service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        meta = resp.result_metadata
        assert meta.column_names == ["token", "holders", "market_cap"]
        assert meta.row_count == 2
        assert meta.total_row_count == 2
        assert meta.truncated is False

    def test_execution_metadata(self, service):
        resp = service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        meta = resp.execution
        assert meta.execution_id == "01HN7XYZABC987654321"
        assert meta.query_id == "7654321"
        assert meta.state == "QUERY_STATE_COMPLETED"

    def test_calls_correct_url(self, service, mock_http):
        service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        call_url = mock_http.get.call_args[0][0]
        assert "/query/7654321/results" in call_url

    def test_second_row(self, service):
        resp = service.GetLatestResults(
            pb.GetLatestResultsRequest(query_id="7654321")
        )
        row = json.loads(resp.rows[1])
        assert row["token"] == "USDC"
        assert row["holders"] == 1200000


class TestCancelExecution:
    def test_returns_success(self, service):
        resp = service.CancelExecution(
            pb.CancelExecutionRequest(execution_id="01HN7ABCDEF123456789")
        )
        assert resp.success is True

    def test_calls_correct_url(self, service, mock_http):
        service.CancelExecution(
            pb.CancelExecutionRequest(execution_id="01HN7ABCDEF123456789")
        )
        call_url = mock_http.post.call_args[0][0]
        assert "/execution/01HN7ABCDEF123456789/cancel" in call_url

    def test_posts_with_api_key(self, service, mock_http):
        with patch.dict("os.environ", {"DUNE_API_KEY": "test_api_key_123"}):
            service.CancelExecution(
                pb.CancelExecutionRequest(execution_id="01HN7ABCDEF123456789")
            )
            call_headers = mock_http.post.call_args[1].get("headers") or {}
            assert call_headers.get("X-Dune-API-Key") == "test_api_key_123"
