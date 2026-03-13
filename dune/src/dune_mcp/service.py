"""DuneService -- wraps the Dune Analytics API into proto RPCs."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from dune_mcp.gen.dune.v1 import dune_pb2 as pb

_BASE_URL = "https://api.dune.com/api/v1"


def _get_api_key() -> str:
    key = os.environ.get("DUNE_API_KEY", "")
    if not key:
        raise RuntimeError("DUNE_API_KEY environment variable is not set")
    return key


def _parse_execution_metadata(raw: dict) -> pb.ExecutionMetadata:
    """Parse raw execution JSON into an ExecutionMetadata proto."""
    return pb.ExecutionMetadata(
        execution_id=raw.get("execution_id", "") or "",
        query_id=str(raw.get("query_id", "")) or "",
        state=raw.get("state", "") or "",
        submitted_at=raw.get("submitted_at", "") or "",
        execution_started_at=raw.get("execution_started_at", "") or "",
        execution_ended_at=raw.get("execution_ended_at", "") or "",
        expires_at=raw.get("expires_at", "") or "",
    )


def _parse_result_metadata(raw: dict) -> pb.ResultMetadata:
    """Parse raw result metadata JSON into a ResultMetadata proto."""
    return pb.ResultMetadata(
        column_names=raw.get("column_names") or [],
        row_count=raw.get("row_count") or 0,
        result_set_bytes=raw.get("result_set_bytes") or 0,
        total_row_count=raw.get("total_row_count") or 0,
        truncated=bool(raw.get("truncated")),
        pending_time_millis=raw.get("pending_time_millis") or 0,
        execution_time_millis=raw.get("execution_time_millis") or 0,
    )


def _rows_to_json_strings(rows: list) -> list[str]:
    """Convert a list of row dicts to JSON-encoded strings."""
    return [json.dumps(r) for r in (rows or [])]


class DuneService:
    """Implements DuneService RPCs via the Dune Analytics API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    def _headers(self) -> dict[str, str]:
        return {"X-Dune-API-Key": _get_api_key()}

    def _get(self, url: str, params: dict | None = None) -> Any:
        resp = self._http.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, json_body: dict | None = None) -> Any:
        resp = self._http.post(url, headers=self._headers(), json=json_body)
        resp.raise_for_status()
        return resp.json()

    def ExecuteQuery(self, request: Any, context: Any = None) -> pb.ExecuteQueryResponse:
        body: dict[str, Any] = {}
        if request.query_parameters:
            params = {}
            for p in request.query_parameters:
                params[p.key] = p.value
            body["query_parameters"] = params

        raw = self._post(f"{_BASE_URL}/query/{request.query_id}/execute", json_body=body or None)
        return pb.ExecuteQueryResponse(
            execution_id=raw.get("execution_id", "") or "",
            state=raw.get("state", "QUERY_STATE_PENDING") or "",
        )

    def GetExecutionStatus(self, request: Any, context: Any = None) -> pb.GetExecutionStatusResponse:
        raw = self._get(f"{_BASE_URL}/execution/{request.execution_id}/status")
        return pb.GetExecutionStatusResponse(
            execution=_parse_execution_metadata(raw),
        )

    def GetExecutionResults(self, request: Any, context: Any = None) -> pb.GetExecutionResultsResponse:
        raw = self._get(f"{_BASE_URL}/execution/{request.execution_id}/results")
        result = raw.get("result") or {}
        return pb.GetExecutionResultsResponse(
            execution=_parse_execution_metadata(raw),
            result_metadata=_parse_result_metadata(result.get("metadata") or {}),
            rows=_rows_to_json_strings(result.get("rows")),
        )

    def GetLatestResults(self, request: Any, context: Any = None) -> pb.GetLatestResultsResponse:
        raw = self._get(f"{_BASE_URL}/query/{request.query_id}/results")
        result = raw.get("result") or {}
        return pb.GetLatestResultsResponse(
            execution=_parse_execution_metadata(raw),
            result_metadata=_parse_result_metadata(result.get("metadata") or {}),
            rows=_rows_to_json_strings(result.get("rows")),
        )

    def CancelExecution(self, request: Any, context: Any = None) -> pb.CancelExecutionResponse:
        raw = self._post(f"{_BASE_URL}/execution/{request.execution_id}/cancel")
        return pb.CancelExecutionResponse(
            success=bool(raw.get("success", True)),
        )
