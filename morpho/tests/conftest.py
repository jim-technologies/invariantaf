"""Shared fixtures for Morpho MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from morpho_mcp.gen.morpho.v1 import morpho_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake GraphQL response data -- matches real Morpho API shapes
# ---------------------------------------------------------------------------

FAKE_MARKET_ITEM = {
    "uniqueKey": "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc",
    "lltv": "860000000000000000",
    "loanAsset": {
        "symbol": "USDC",
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "decimals": 6,
    },
    "collateralAsset": {
        "symbol": "WETH",
        "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "decimals": 18,
    },
    "morphoBlue": {"chain": {"id": 1, "network": "Ethereum"}},
    "state": {
        "supplyApy": 0.035,
        "borrowApy": 0.045,
        "netSupplyApy": 0.038,
        "netBorrowApy": 0.042,
        "supplyAssetsUsd": 150000000.0,
        "borrowAssetsUsd": 120000000.0,
        "utilization": 0.80,
        "fee": 0.0,
        "liquidityAssetsUsd": 30000000.0,
        "collateralAssetsUsd": 200000000.0,
        "rewards": [
            {
                "supplyApr": 0.01,
                "borrowApr": 0.005,
                "asset": {
                    "symbol": "MORPHO",
                    "address": "0x9994E35Db50125E0DF82e4c2dde62496CE330999",
                    "decimals": 18,
                },
            }
        ],
    },
}

FAKE_MARKET_ITEM_2 = {
    "uniqueKey": "0xaabbccddee11223344556677889900aabbccddee11223344556677889900aabb",
    "lltv": "770000000000000000",
    "loanAsset": {
        "symbol": "DAI",
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "decimals": 18,
    },
    "collateralAsset": {
        "symbol": "wstETH",
        "address": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",
        "decimals": 18,
    },
    "morphoBlue": {"chain": {"id": 1, "network": "Ethereum"}},
    "state": {
        "supplyApy": 0.028,
        "borrowApy": 0.039,
        "netSupplyApy": 0.030,
        "netBorrowApy": 0.037,
        "supplyAssetsUsd": 80000000.0,
        "borrowAssetsUsd": 60000000.0,
        "utilization": 0.75,
        "fee": 0.01,
        "liquidityAssetsUsd": 20000000.0,
        "collateralAssetsUsd": 100000000.0,
        "rewards": [],
    },
}

FAKE_VAULT_ITEM = {
    "address": "0xBEEF01735c132Ada46AA9aA9cE6E9faA753e1076",
    "name": "Steakhouse Prime USDC",
    "symbol": "steakUSDC",
    "asset": {
        "symbol": "USDC",
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "decimals": 6,
    },
    "chain": {"id": 1, "network": "Ethereum"},
    "state": {
        "apy": 0.055,
        "netApy": 0.05,
        "totalAssetsUsd": 250000000.0,
        "totalAssets": "250000000000000",
        "totalSupply": "240000000000000",
        "fee": 0.10,
        "rewards": [
            {
                "supplyApr": 0.008,
                "asset": {
                    "symbol": "MORPHO",
                    "address": "0x9994E35Db50125E0DF82e4c2dde62496CE330999",
                    "decimals": 18,
                },
            }
        ],
    },
}

FAKE_VAULT_ITEM_2 = {
    "address": "0x1234567890abcdef1234567890abcdef12345678",
    "name": "Gauntlet WETH Prime",
    "symbol": "gWETH",
    "asset": {
        "symbol": "WETH",
        "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "decimals": 18,
    },
    "chain": {"id": 1, "network": "Ethereum"},
    "state": {
        "apy": 0.032,
        "netApy": 0.028,
        "totalAssetsUsd": 180000000.0,
        "totalAssets": "75000000000000000000000",
        "totalSupply": "73000000000000000000000",
        "fee": 0.15,
        "rewards": [],
    },
}

FAKE_POSITION_ITEM = {
    "healthFactor": 1.85,
    "user": {"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"},
    "market": FAKE_MARKET_ITEM,
    "state": {
        "supplyAssets": "50000000000",
        "supplyAssetsUsd": 50000.0,
        "borrowAssets": "30000000000",
        "borrowAssetsUsd": 30000.0,
        "collateral": "20000000000000000000",
        "collateralUsd": 60000.0,
    },
}

# GraphQL response wrappers
FAKE_MARKETS_RESPONSE = {"markets": {"items": [FAKE_MARKET_ITEM, FAKE_MARKET_ITEM_2]}}
FAKE_MARKET_BY_KEY_RESPONSE = {"marketByUniqueKey": FAKE_MARKET_ITEM}
FAKE_VAULTS_RESPONSE = {"vaults": {"items": [FAKE_VAULT_ITEM, FAKE_VAULT_ITEM_2]}}
FAKE_VAULT_BY_ADDRESS_RESPONSE = {"vaultByAddress": FAKE_VAULT_ITEM}
FAKE_POSITIONS_RESPONSE = {"marketPositions": {"items": [FAKE_POSITION_ITEM]}}


def _make_mock_http():
    """Create a mock httpx.Client that intercepts post() for GraphQL."""
    http = MagicMock()

    def mock_post(url, json=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        query = (json or {}).get("query", "")
        if "marketPositions" in query:
            resp.json.return_value = {"data": FAKE_POSITIONS_RESPONSE}
        elif "marketByUniqueKey" in query:
            resp.json.return_value = {"data": FAKE_MARKET_BY_KEY_RESPONSE}
        elif "markets" in query:
            resp.json.return_value = {"data": FAKE_MARKETS_RESPONSE}
        elif "vaultByAddress" in query:
            resp.json.return_value = {"data": FAKE_VAULT_BY_ADDRESS_RESPONSE}
        elif "vaults" in query:
            resp.json.return_value = {"data": FAKE_VAULTS_RESPONSE}
        else:
            resp.json.return_value = {"data": {}}
        return resp

    http.post = MagicMock(side_effect=mock_post)
    return http


@pytest.fixture
def mock_http():
    return _make_mock_http()


@pytest.fixture
def service(mock_http):
    """MorphoService with mocked HTTP client."""
    from morpho_mcp.service import MorphoService

    svc = MorphoService.__new__(MorphoService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked MorphoService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-morpho", version="0.0.1")
    srv.register(service)
    return srv
