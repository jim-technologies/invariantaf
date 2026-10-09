import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import grpc
from invariant import Server

from bindings import ClobBindings
from gen.polymarket.v1 import polymarket_pb2 as pb
from gen.polymarket.v1 import polymarket_pb2_grpc as rpc
from main import _PolymarketClobCompositeService


def test_native_registration_refuses_private_operations_without_credentials():
    async def check():
        descriptor = str(Path(__file__).parents[1] / "descriptor.binpb")
        proxy = Server.from_descriptor(descriptor)
        proxy.connect_http(
            "https://clob.polymarket.com",
            service_name="polymarket.v1.PolymarketClobService",
        )
        server = Server.from_descriptor(descriptor)
        rpc.add_PolymarketClobServiceServicer_to_server(
            ClobBindings(_PolymarketClobCompositeService(None, 0), proxy), server
        )
        assert len(server.tools) == 13
        try:
            await server.invoke(
                "polymarket.v1.PolymarketClobService.CancelAllOrders",
                pb.CancelAllOrdersRequest(),
            )
        except Exception as error:
            assert error.code == grpc.StatusCode.UNAUTHENTICATED
        else:
            raise AssertionError("private call succeeded without credentials")

    asyncio.run(check())


def test_sync_private_dependency_is_serialized_without_blocking_the_event_loop():
    class Composite:
        def __init__(self):
            self.active = 0
            self.peak = 0

        def CancelAllOrders(self, request, context):
            self.active += 1
            self.peak = max(self.peak, self.active)
            time.sleep(0.03)
            self.active -= 1
            return pb.CancelAllOrdersResponse()

    async def check():
        composite = Composite()
        binding = ClobBindings(composite, None)
        ticks = 0

        async def ticker():
            nonlocal ticks
            for _ in range(10):
                ticks += 1
                await asyncio.sleep(0.005)

        await asyncio.gather(
            binding.CancelAllOrders(pb.CancelAllOrdersRequest(), None),
            binding.CancelAllOrders(pb.CancelAllOrdersRequest(), None),
            ticker(),
        )
        assert composite.peak == 1
        assert ticks == 10

    asyncio.run(check())
