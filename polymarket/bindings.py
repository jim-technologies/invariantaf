import asyncio


class ClobBindings:
    def __init__(self, composite, public_proxy):
        self._composite = composite
        self._public_proxy = public_proxy
        self._private_lock = asyncio.Lock()

    async def GetOrderbook(self, request, context):
        return await self._public_proxy.invoke(
            "polymarket.v1.PolymarketClobService.GetOrderbook", request, context
        )

    async def GetPrice(self, request, context):
        return await self._public_proxy.invoke(
            "polymarket.v1.PolymarketClobService.GetPrice", request, context
        )

    async def GetMidpoint(self, request, context):
        return await self._public_proxy.invoke(
            "polymarket.v1.PolymarketClobService.GetMidpoint", request, context
        )

    async def GetSpread(self, request, context):
        return await self._public_proxy.invoke(
            "polymarket.v1.PolymarketClobService.GetSpread", request, context
        )

    async def GetPriceHistory(self, request, context):
        return await self._public_proxy.invoke(
            "polymarket.v1.PolymarketClobService.GetPriceHistory", request, context
        )

    async def PlaceOrder(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(self._composite.PlaceOrder, request, context)

    async def CreateAndPostOrder(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(
                self._composite.CreateAndPostOrder, request, context
            )

    async def CancelOrder(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(
                self._composite.CancelOrder, request, context
            )

    async def CancelAllOrders(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(
                self._composite.CancelAllOrders, request, context
            )

    async def GetOpenOrders(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(
                self._composite.GetOpenOrders, request, context
            )

    async def GetTrades(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(self._composite.GetTrades, request, context)

    async def GetBalance(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(self._composite.GetBalance, request, context)

    async def GetBalanceAllowance(self, request, context):
        async with self._private_lock:
            return await asyncio.to_thread(
                self._composite.GetBalanceAllowance, request, context
            )
