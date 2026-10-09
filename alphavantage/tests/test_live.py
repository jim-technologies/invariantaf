import asyncio
import os
from pathlib import Path

import httpx
import pytest
from invariant import Server

from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2 as pb
from alphavantage_mcp.gen.alphavantage.v1 import alphavantage_pb2_grpc as rpc
from alphavantage_mcp.service import AlphaVantageService


def test_canonical_registration_and_client_lifecycle():
    async def check():
        service = AlphaVantageService()
        try:
            server = Server.from_descriptor(
                str(Path(__file__).parents[1] / "descriptor.binpb")
            )
            descriptor = pb.DESCRIPTOR.services_by_name["AlphaVantageService"]
            rpc.add_AlphaVantageServiceServicer_to_server(service, server)
            assert set(server.tools) == {
                f"{descriptor.full_name}.{method.name}" for method in descriptor.methods
            }
            for method in descriptor.methods:
                tool = server.tools[f"{descriptor.full_name}.{method.name}"]
                assert tool.input_type == method.input_type.full_name
                assert tool.output_type == method.output_type.full_name
        finally:
            await service.aclose()

    asyncio.run(check())


def test_live_read_only_provider_contract():
    if os.getenv("ALPHAVANTAGE_RUN_LIVE_TESTS") != "1":
        pytest.skip(
            "set ALPHAVANTAGE_RUN_LIVE_TESTS=1 for the real provider integration"
        )
    required = ["ALPHAVANTAGE_API_KEY"]
    if any(not os.getenv(key) for key in required):
        pytest.skip("provider integration requires its existing API credentials")

    async def check():
        service = AlphaVantageService()
        try:
            try:
                response = await service.GetQuote(pb.GetQuoteRequest(symbol="IBM"))
            except httpx.TimeoutException:
                pytest.skip("provider timed out")
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429:
                    pytest.skip("provider rate limit")
                raise
            assert response.symbol == "IBM" and response.price > 0
        finally:
            await service.aclose()

    asyncio.run(check())
