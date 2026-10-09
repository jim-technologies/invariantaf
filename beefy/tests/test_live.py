import asyncio
import os
from pathlib import Path

import httpx
import pytest
from invariant import Server

from beefy_mcp.gen.beefy.v1 import beefy_pb2 as pb
from beefy_mcp.gen.beefy.v1 import beefy_pb2_grpc as rpc
from beefy_mcp.service import BeefyService


def test_canonical_registration_and_client_lifecycle():
    async def check():
        service = BeefyService()
        try:
            server = Server.from_descriptor(
                str(Path(__file__).parents[1] / "descriptor.binpb")
            )
            descriptor = pb.DESCRIPTOR.services_by_name["BeefyService"]
            rpc.add_BeefyServiceServicer_to_server(service, server)
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
    if os.getenv("BEEFY_RUN_LIVE_TESTS") != "1":
        pytest.skip("set BEEFY_RUN_LIVE_TESTS=1 for the real provider integration")
    required = []
    if any(not os.getenv(key) for key in required):
        pytest.skip("provider integration requires its existing API credentials")

    async def check():
        service = BeefyService()
        try:
            try:
                response = await service.ListVaults(pb.ListVaultsRequest())
            except httpx.TimeoutException:
                pytest.skip("provider timed out")
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 429:
                    pytest.skip("provider rate limit")
                raise
            assert response.vaults and response.vaults[0].id
        finally:
            await service.aclose()

    asyncio.run(check())
