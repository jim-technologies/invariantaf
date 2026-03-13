"""Shared fixtures for Curve Finance MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from curve_mcp.gen.curve.v1 import curve_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Curve Finance API return shapes
# ---------------------------------------------------------------------------

FAKE_POOLS = {
    "success": True,
    "data": {
        "poolData": [
            {
                "id": "0",
                "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
                "coinsAddresses": [
                    "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                ],
                "decimals": ["18", "6", "6"],
                "virtualPrice": "1039823717130252926",
                "amplificationCoefficient": "4000",
                "totalSupply": "156223868197810822899967769",
                "name": "Curve.fi DAI/USDC/USDT",
                "assetType": "0",
                "lpTokenAddress": "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
                "symbol": "3Crv",
                "implementation": "",
                "assetTypeName": "usd",
                "coins": [
                    {
                        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                        "usdPrice": 1.0001,
                        "decimals": "18",
                        "isBasePoolLpToken": False,
                        "symbol": "DAI",
                        "name": "Dai Stablecoin",
                        "poolBalance": "58523366064329938326677617",
                    },
                    {
                        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                        "usdPrice": 1.0,
                        "decimals": "6",
                        "isBasePoolLpToken": False,
                        "symbol": "USDC",
                        "name": "USD Coin",
                        "poolBalance": "59160817816905",
                    },
                    {
                        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                        "usdPrice": 1.0001,
                        "decimals": "6",
                        "isBasePoolLpToken": False,
                        "symbol": "USDT",
                        "name": "Tether USD",
                        "poolBalance": "44761430414639",
                    },
                ],
                "poolUrls": {
                    "swap": ["https://curve.finance/dex/#/ethereum/pools/3pool/swap"],
                    "deposit": ["https://curve.finance/dex/#/ethereum/pools/3pool/deposit"],
                    "withdraw": ["https://curve.finance/dex/#/ethereum/pools/3pool/withdraw"],
                },
                "usdTotal": 162456848.37,
                "isMetaPool": False,
                "usdTotalExcludingBasePool": 162456848.37,
                "gaugeAddress": "0xbfcf63294ad7105dea65aa58f8ae5be2d9d0952a",
                "gaugeRewards": [],
                "gaugeCrvApy": [0.00003641, 0.00009103],
                "gaugeFutureCrvApy": [0.00003554, 0.00008885],
                "usesRateOracle": False,
                "isBroken": False,
                "creationTs": 1600000000,
                "creationBlockNumber": 10809473,
            },
            {
                "id": "1",
                "address": "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE",
                "coinsAddresses": [
                    "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                ],
                "decimals": ["18", "6"],
                "virtualPrice": "1233637604772585500",
                "amplificationCoefficient": "100",
                "totalSupply": "1000000000000000000",
                "name": "Curve.fi aDAI/aUSDC",
                "assetType": "0",
                "lpTokenAddress": "0xFd2a8fA60Abd58Efe3EeE34dd494cD491dC14900",
                "symbol": "a3Crv",
                "implementation": "",
                "assetTypeName": "usd",
                "coins": [
                    {
                        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                        "usdPrice": 1.0,
                        "decimals": "18",
                        "isBasePoolLpToken": False,
                        "symbol": "aDAI",
                        "name": "Aave DAI",
                        "poolBalance": "5000000000000000000000",
                    },
                ],
                "poolUrls": {
                    "swap": [],
                    "deposit": [],
                    "withdraw": [],
                },
                "usdTotal": 5000000.0,
                "isMetaPool": False,
                "usdTotalExcludingBasePool": 5000000.0,
                "gaugeAddress": "0x0000000000000000000000000000000000000000",
                "gaugeRewards": [
                    {
                        "gaugeAddress": "0x0000000000000000000000000000000000000000",
                        "tokenPrice": 0.5,
                        "name": "Curve DAO Token",
                        "symbol": "CRV",
                        "decimals": "18",
                        "apy": 5.2,
                        "tokenAddress": "0xD533a949740bb3306d119CC777fa900bA034cd52",
                    },
                ],
                "gaugeCrvApy": [1.5, 3.75],
                "gaugeFutureCrvApy": [],
                "usesRateOracle": False,
                "isBroken": False,
                "creationTs": 1610000000,
                "creationBlockNumber": 11700000,
            },
        ],
    },
}

FAKE_SUBGRAPH_DATA = {
    "success": True,
    "data": {
        "poolList": [
            {
                "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
                "latestDailyApy": 1.49,
                "latestWeeklyApy": 1.47,
                "rawVolume": None,
                "type": "main",
                "virtualPrice": 1039823717130228200,
                "volumeUSD": 396294.19,
            },
            {
                "address": "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE",
                "latestDailyApy": 0.28,
                "latestWeeklyApy": 0.28,
                "rawVolume": None,
                "type": "main",
                "virtualPrice": 1233637604772585500,
                "volumeUSD": 0,
            },
        ],
    },
}

FAKE_VOLUMES = {
    "success": True,
    "data": {
        "pools": [
            {
                "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
                "type": "main",
                "volumeUSD": 396294.19,
                "latestDailyApyPcent": 1.49,
                "latestWeeklyApyPcent": 1.47,
                "includedApyPcentFromLsts": 0,
                "virtualPrice": 1039823717130228200,
            },
            {
                "address": "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE",
                "type": "main",
                "volumeUSD": 0,
                "latestDailyApyPcent": 0.28,
                "latestWeeklyApyPcent": 0.28,
                "includedApyPcentFromLsts": 0,
                "virtualPrice": 1233637604772585500,
            },
        ],
    },
}

FAKE_FACTORY_TVL = {
    "success": True,
    "data": {
        "factoryBalances": 81615253.25,
    },
    "generatedTimeMs": 1773322708597,
}

FAKE_WEEKLY_FEES = {
    "success": True,
    "data": {
        "weeklyFeesTable": [
            {
                "date": "Thu Mar 12 2026",
                "ts": 1773273600000,
                "rawFees": 0,
            },
            {
                "date": "Thu Mar 05 2026",
                "ts": 1772668800000,
                "rawFees": 79144.67,
            },
            {
                "date": "Thu Feb 26 2026",
                "ts": 1772064000000,
                "rawFees": 110431.77,
            },
        ],
        "totalFees": {
            "fees": 170504253.43,
        },
    },
    "generatedTimeMs": 1773321851903,
}

FAKE_ETH_PRICE = {
    "success": True,
    "data": {
        "price": 2028.76,
    },
    "generatedTimeMs": 1773289218315,
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/getPools/ethereum/main": FAKE_POOLS,
        "/getSubgraphData/ethereum": FAKE_SUBGRAPH_DATA,
        "/getVolumes": FAKE_VOLUMES,
        "/getTVL": FAKE_POOLS,
        "/getFactoryTVL": FAKE_FACTORY_TVL,
        "/getWeeklyFees": FAKE_WEEKLY_FEES,
        "/getETHprice": FAKE_ETH_PRICE,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None, follow_redirects=True):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        # Match on path suffix.
        for path, data in defaults.items():
            if url.endswith(path):
                resp.json.return_value = data
                return resp
        resp.json.return_value = {}
        return resp

    http.get = MagicMock(side_effect=mock_get)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """CurveService with mocked HTTP client."""
    from curve_mcp.service import CurveService

    svc = CurveService.__new__(CurveService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked CurveService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-curve", version="0.0.1")
    srv.register(service)
    return srv
