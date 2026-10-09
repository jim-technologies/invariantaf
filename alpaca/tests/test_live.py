import asyncio
import os
from pathlib import Path

import httpx
import pytest
from invariant import Server

from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2 as pb
from alpaca_mcp.gen.alpaca.v1 import alpaca_pb2_grpc as rpc
from alpaca_mcp.service import AlpacaService


def test_canonical_registration_and_client_lifecycle():
    async def check():
        service = AlpacaService()
        try:
            server = Server.from_descriptor(
                str(Path(__file__).parents[1] / "descriptor.binpb")
            )
            descriptor = pb.DESCRIPTOR.services_by_name["AlpacaService"]
            rpc.add_AlpacaServiceServicer_to_server(service, server)
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
    if os.getenv("ALPACA_RUN_LIVE_TESTS") != "1":
        pytest.skip("set ALPACA_RUN_LIVE_TESTS=1 for the real provider integration")
    required = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
    if any(not os.getenv(key) for key in required):
        pytest.skip("provider integration requires its existing API credentials")

    async def check():
        service = AlpacaService()
        try:
            try:
                response = await service.GetAccount(pb.GetAccountRequest())
            except httpx.TimeoutException:
                pytest.skip("provider timed out")
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429:
                    pytest.skip("provider rate limit")
                raise
            assert response.id and response.currency
        finally:
            await service.aclose()

    asyncio.run(check())
