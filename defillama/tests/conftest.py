"""Shared fixtures for DeFiLlama MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from defillama_mcp.gen.defillama.v1 import defillama_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real DeFiLlama API return shapes
# ---------------------------------------------------------------------------

FAKE_PROTOCOLS = [
    {
        "id": "2269",
        "name": "Aave",
        "symbol": "AAVE",
        "url": "https://aave.com",
        "description": "Aave is an open-source lending protocol.",
        "chain": "Multi-Chain",
        "logo": "https://icons.llama.fi/aave.jpg",
        "category": "Lending",
        "chains": ["Ethereum", "Polygon", "Avalanche"],
        "tvl": 26000000000,
        "change_1h": 0.1,
        "change_1d": 1.5,
        "change_7d": 5.2,
        "slug": "aave",
        "twitter": "AaveAave",
        "mcap": 4500000000,
    },
    {
        "id": "119",
        "name": "Lido",
        "symbol": "LDO",
        "url": "https://lido.fi",
        "description": "Lido is a liquid staking solution.",
        "chain": "Multi-Chain",
        "logo": "https://icons.llama.fi/lido.jpg",
        "category": "Liquid Staking",
        "chains": ["Ethereum", "Polygon"],
        "tvl": 18000000000,
        "change_1h": -0.05,
        "change_1d": 0.8,
        "change_7d": 3.1,
        "slug": "lido",
        "twitter": "LidoFinance",
        "mcap": 2000000000,
    },
]

FAKE_PROTOCOL_DETAIL = {
    "id": "111",
    "name": "Aave",
    "url": "https://aave.com",
    "description": "Aave is an open-source lending protocol.",
    "logo": "https://icons.llama.fi/aave.jpg",
    "symbol": "AAVE",
    "chains": ["Ethereum", "Polygon", "Avalanche"],
    "gecko_id": "aave",
    "twitter": "AaveAave",
    "tvl": [
        {"date": 1589932800, "totalLiquidityUSD": 54026260},
        {"date": 1590019200, "totalLiquidityUSD": 55000000},
        {"date": 1590105600, "totalLiquidityUSD": 56000000},
    ],
    "currentChainTvls": {
        "Ethereum": 20000000000,
        "Polygon": 3000000000,
        "Avalanche": 3000000000,
    },
    "mcap": 4500000000,
    "category": "Lending",
}

FAKE_TVL = 26446474028

FAKE_CHAINS = [
    {
        "gecko_id": "ethereum",
        "tvl": 60000000000,
        "tokenSymbol": "ETH",
        "cmcId": "1027",
        "name": "Ethereum",
        "chainId": 1,
    },
    {
        "gecko_id": "binancecoin",
        "tvl": 5000000000,
        "tokenSymbol": "BNB",
        "cmcId": "1839",
        "name": "BSC",
        "chainId": 56,
    },
]

FAKE_GLOBAL_TVL = [
    {"date": 1506470400, "tvl": 0},
    {"date": 1506556800, "tvl": 100000},
    {"date": 1506643200, "tvl": 250000},
]

FAKE_STABLECOINS = {
    "peggedAssets": [
        {
            "id": "1",
            "name": "Tether",
            "symbol": "USDT",
            "gecko_id": "tether",
            "pegType": "peggedUSD",
            "pegMechanism": "fiat-backed",
            "circulating": {"peggedUSD": 183620774070.14},
            "circulatingPrevDay": {"peggedUSD": 183458165919.49},
            "circulatingPrevWeek": {"peggedUSD": 183576475732.69},
            "circulatingPrevMonth": {"peggedUSD": 185318552614.40},
        },
        {
            "id": "2",
            "name": "USD Coin",
            "symbol": "USDC",
            "gecko_id": "usd-coin",
            "pegType": "peggedUSD",
            "pegMechanism": "fiat-backed",
            "circulating": {"peggedUSD": 45000000000},
            "circulatingPrevDay": {"peggedUSD": 44900000000},
            "circulatingPrevWeek": {"peggedUSD": 44500000000},
            "circulatingPrevMonth": {"peggedUSD": 43000000000},
        },
    ],
    "chains": [],
}

FAKE_YIELD_POOLS = {
    "status": "success",
    "data": [
        {
            "chain": "Ethereum",
            "project": "lido",
            "symbol": "STETH",
            "tvlUsd": 18312039691,
            "apyBase": 2.501,
            "apyReward": None,
            "apy": 2.501,
            "pool": "747c1d2a-c668-4682-b9f9-296708a3dd90",
            "apyPct1D": 0.122,
            "apyPct7D": 0.134,
            "apyPct30D": -1.116,
            "stablecoin": False,
            "ilRisk": "no",
            "exposure": "single",
            "predictions": {
                "predictedClass": "Stable/Up",
                "predictedProbability": 73,
                "binnedConfidence": 2,
            },
        },
        {
            "chain": "Ethereum",
            "project": "aave-v3",
            "symbol": "USDC",
            "tvlUsd": 5000000000,
            "apyBase": 3.5,
            "apyReward": 0.5,
            "apy": 4.0,
            "pool": "abc-def-123",
            "apyPct1D": 0.05,
            "apyPct7D": 0.1,
            "apyPct30D": -0.2,
            "stablecoin": True,
            "ilRisk": "no",
            "exposure": "single",
            "predictions": {
                "predictedClass": "Down",
                "predictedProbability": 55,
                "binnedConfidence": 1,
            },
        },
    ],
}

FAKE_DEX_VOLUMES = {
    "total24h": 9702385010,
    "total7d": 59826406024,
    "total30d": 200000000000,
    "change_1d": 17.74,
    "change_7d": 5.2,
    "change_1m": -10.3,
    "allChains": ["Ethereum", "Solana", "BSC", "Base", "Arbitrum"],
    "protocols": [
        {
            "name": "Uniswap",
            "slug": "uniswap",
            "logo": "https://icons.llama.fi/uniswap.jpg",
            "category": "Dexes",
            "chains": ["Ethereum", "Polygon", "Arbitrum"],
            "total24h": 3000000000,
            "total7d": 20000000000,
            "total30d": 80000000000,
            "change_1d": 10.5,
            "change_7d": 3.2,
            "change_1m": -5.1,
        },
        {
            "name": "Raydium",
            "slug": "raydium",
            "logo": "https://icons.llama.fi/raydium.jpg",
            "category": "Dexes",
            "chains": ["Solana"],
            "total24h": 2000000000,
            "total7d": 15000000000,
            "total30d": 60000000000,
            "change_1d": 25.0,
            "change_7d": 8.1,
            "change_1m": -2.0,
        },
    ],
    "totalDataChart": [],
    "totalDataChartBreakdown": [],
}

FAKE_FEES = {
    "total24h": 50000000,
    "total7d": 350000000,
    "total30d": 1500000000,
    "change_1d": 5.5,
    "change_7d": -2.3,
    "change_1m": 12.0,
    "protocols": [
        {
            "name": "Ethereum",
            "slug": "ethereum",
            "logo": "https://icons.llama.fi/ethereum.jpg",
            "category": "Chain",
            "chains": ["Ethereum"],
            "total24h": 20000000,
            "total7d": 140000000,
            "total30d": 600000000,
            "change_1d": 3.0,
            "change_7d": -1.5,
            "change_1m": 8.0,
        },
        {
            "name": "Lido",
            "slug": "lido",
            "logo": "https://icons.llama.fi/lido.jpg",
            "category": "Liquid Staking",
            "chains": ["Ethereum"],
            "total24h": 5000000,
            "total7d": 35000000,
            "total30d": 150000000,
            "change_1d": 1.2,
            "change_7d": 0.5,
            "change_1m": 3.0,
        },
    ],
    "totalDataChart": [],
    "totalDataChartBreakdown": [],
}

FAKE_STABLECOIN_CHAINS = [
    {
        "gecko_id": "ethereum",
        "totalCirculatingUSD": {"peggedUSD": 100000000000},
        "tokenSymbol": "ETH",
        "name": "Ethereum",
    },
    {
        "gecko_id": "tron",
        "totalCirculatingUSD": {"peggedUSD": 60000000000},
        "tokenSymbol": "TRX",
        "name": "Tron",
    },
    {
        "gecko_id": "binancecoin",
        "totalCirculatingUSD": {"peggedUSD": 8000000000},
        "tokenSymbol": "BNB",
        "name": "BSC",
    },
]


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/protocols": FAKE_PROTOCOLS,
        "/protocol/aave": FAKE_PROTOCOL_DETAIL,
        "/tvl/aave": FAKE_TVL,
        "/v2/chains": FAKE_CHAINS,
        "/v2/historicalChainTvl": FAKE_GLOBAL_TVL,
        "/stablecoins": FAKE_STABLECOINS,
        "/pools": FAKE_YIELD_POOLS,
        "/overview/dexs": FAKE_DEX_VOLUMES,
        "/overview/fees": FAKE_FEES,
        "/stablecoinchains": FAKE_STABLECOIN_CHAINS,
    }
    if url_responses:
        defaults.update(url_responses)

    http = MagicMock()

    def mock_get(url, params=None):
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
    """DefiLlamaService with mocked HTTP client."""
    from defillama_mcp.service import DefiLlamaService

    svc = DefiLlamaService.__new__(DefiLlamaService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked DefiLlamaService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-dl", version="0.0.1")
    srv.register(service)
    return srv
