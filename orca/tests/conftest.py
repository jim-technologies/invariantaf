"""Shared fixtures for Orca MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orca_mcp.gen.orca.v1 import orca_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data — matches real Orca API return shapes
# ---------------------------------------------------------------------------

FAKE_POOL_TOKEN_A = {
    "address": "So11111111111111111111111111111111111111112",
    "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "imageUrl": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
    "name": "Wrapped SOL",
    "symbol": "SOL",
    "decimals": 9,
    "tags": ["solana"],
}

FAKE_POOL_TOKEN_B = {
    "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "imageUrl": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png",
    "name": "USD Coin",
    "symbol": "USDC",
    "decimals": 6,
    "tags": ["stablecoin"],
}

FAKE_POOL = {
    "address": "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE",
    "whirlpoolsConfig": "2LecshUwPfjNagMbGICGBisCkfbs6QPAzp7CaNyVHcxy",
    "whirlpoolBump": [255],
    "tickSpacing": 64,
    "tickSpacingSeed": [0, 64],
    "feeRate": 2000,
    "protocolFeeRate": 300,
    "liquidity": "717668795506101",
    "sqrtPrice": "7545573697073867",
    "tickCurrentIndex": -22740,
    "protocolFeeOwedA": "123456",
    "protocolFeeOwedB": "789012",
    "tokenMintA": "So11111111111111111111111111111111111111112",
    "tokenVaultA": "3YQm7ujtXWJU2e9jhp2QGHpkwJnXeW3JXBi1YGUzPwrt",
    "feeGrowthGlobalA": "10000000000",
    "tokenMintB": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "tokenVaultB": "2JTw1fE2wz1SymWUQ7UqpVtrTuKjcd6mWwYwUJUCh2rq",
    "feeGrowthGlobalB": "20000000000",
    "rewardLastUpdatedTimestamp": "2026-03-10T12:00:00.000Z",
    "updatedAt": "2026-03-10T15:30:00.000Z",
    "updatedSlot": 350000000,
    "writeVersion": 1,
    "hasWarning": False,
    "poolType": "concentrated",
    "tokenA": FAKE_POOL_TOKEN_A,
    "tokenB": FAKE_POOL_TOKEN_B,
    "price": "135.50",
    "tvlUsdc": "12500000.00",
    "yieldOverTvl": "0.0523",
    "tokenBalanceA": "46200.123",
    "tokenBalanceB": "6260000.456",
    "stats": {
        "24h": {
            "volume": "15000000.00",
            "fees": "30000.00",
            "rewards": "5000.00",
            "yieldOverTvl": "0.0028",
        },
        "7d": {
            "volume": "95000000.00",
            "fees": "190000.00",
            "rewards": "35000.00",
            "yieldOverTvl": "0.018",
        },
        "30d": {
            "volume": "400000000.00",
            "fees": "800000.00",
            "rewards": "150000.00",
            "yieldOverTvl": "0.076",
        },
    },
    "rewards": [
        {
            "mint": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
            "vault": "9tnHkQ4M7gyd73WhPvAcjpJpbiyh3jGRE4o9LjrPzZXj",
            "authority": "GwH3Hiv5mACLX3ufTw1pFsrhSPon5tdw252DBs4Rx4PV",
            "emissions_per_second_x64": "184467440737095",
            "growth_global_x64": "999999999",
            "active": True,
            "emissionsPerSecond": "0.00001",
        },
    ],
    "lockedLiquidityPercent": [
        {"name": "OrcaLock", "locked_percentage": "0.00000068", "lockedPercentage": "0.00000068"},
    ],
    "addressLookupTable": "ALT111111111111111111111111111111111111111",
    "feeTierIndex": 2,
    "adaptiveFeeEnabled": False,
    "adaptiveFee": None,
    "tradeEnableTimestamp": "2024-01-01T00:00:00.000Z",
}

FAKE_POOL_2 = {
    "address": "HJPjoWUrhoZzkNfRpHuieeFk9WGRBBNRYgLKr3Cp2Jc2",
    "whirlpoolsConfig": "2LecshUwPfjNagMbGICGBisCkfbs6QPAzp7CaNyVHcxy",
    "whirlpoolBump": [254],
    "tickSpacing": 1,
    "tickSpacingSeed": [0, 1],
    "feeRate": 100,
    "protocolFeeRate": 300,
    "liquidity": "500000000000",
    "sqrtPrice": "18446744073709551616",
    "tickCurrentIndex": 0,
    "protocolFeeOwedA": "0",
    "protocolFeeOwedB": "0",
    "tokenMintA": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "tokenVaultA": "vault_a_2",
    "feeGrowthGlobalA": "0",
    "tokenMintB": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "tokenVaultB": "vault_b_2",
    "feeGrowthGlobalB": "0",
    "rewardLastUpdatedTimestamp": "2026-03-10T12:00:00.000Z",
    "updatedAt": "2026-03-10T14:00:00.000Z",
    "updatedSlot": 349000000,
    "writeVersion": 1,
    "hasWarning": False,
    "poolType": "concentrated",
    "tokenA": FAKE_POOL_TOKEN_B,
    "tokenB": {
        "address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "imageUrl": "",
        "name": "USDT",
        "symbol": "USDT",
        "decimals": 6,
        "tags": ["stablecoin"],
    },
    "price": "1.0001",
    "tvlUsdc": "8000000.00",
    "yieldOverTvl": "0.012",
    "tokenBalanceA": "4000000.00",
    "tokenBalanceB": "4000000.00",
    "stats": {
        "24h": {"volume": "5000000.00", "fees": "500.00", "rewards": None, "yieldOverTvl": "0.0001"},
        "7d": {"volume": "35000000.00", "fees": "3500.00", "rewards": None, "yieldOverTvl": "0.0004"},
        "30d": {"volume": "150000000.00", "fees": "15000.00", "rewards": None, "yieldOverTvl": "0.0019"},
    },
    "rewards": [],
    "lockedLiquidityPercent": [],
    "addressLookupTable": None,
    "feeTierIndex": 0,
    "adaptiveFeeEnabled": False,
    "adaptiveFee": None,
    "tradeEnableTimestamp": "2024-06-01T00:00:00.000Z",
}

FAKE_POOLS_RESPONSE = {"data": [FAKE_POOL, FAKE_POOL_2]}

FAKE_TOKEN = {
    "address": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "mintAuthority": "GwH3Hiv5mACLX3ufTw1pFsrhSPon5tdw252DBs4Rx4PV",
    "supply": 74999565293160,
    "decimals": 6,
    "isInitialized": True,
    "freezeAuthority": None,
    "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "extensions": {},
    "tags": [],
    "updatedEpoch": 939,
    "updatedAt": "2026-03-12T10:52:00.212390Z",
    "priceUsdc": "3.45",
    "metadata": {
        "image": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE/logo.png",
        "name": "Orca",
        "risk": 2,
        "symbol": "ORCA",
    },
    "stats": {
        "24h": {
            "volume": 433016.17,
        },
    },
}

FAKE_TOKEN_2 = {
    "address": "So11111111111111111111111111111111111111112",
    "mintAuthority": None,
    "supply": 600000000000000000,
    "decimals": 9,
    "isInitialized": True,
    "freezeAuthority": None,
    "tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "extensions": {},
    "tags": ["solana"],
    "updatedEpoch": 939,
    "updatedAt": "2026-03-12T10:52:00.000Z",
    "priceUsdc": "135.50",
    "metadata": {
        "image": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
        "name": "Wrapped SOL",
        "risk": 1,
        "symbol": "SOL",
    },
    "stats": {
        "24h": {
            "volume": 850000000.0,
        },
    },
}

FAKE_TOKENS_RESPONSE = {"data": [FAKE_TOKEN, FAKE_TOKEN_2], "meta": {"cursor": {"previous": None, "next": "abc"}}}

FAKE_PROTOCOL_STATS = {
    "tvl": "1250000000.00",
    "volume24hUsdc": "350000000.00",
    "fees24hUsdc": "700000.00",
    "revenue24hUsdc": "210000.00",
}

FAKE_PROTOCOL_TOKEN = {
    "symbol": "ORCA",
    "name": "Orca",
    "description": "Orca is a DEX on Solana.",
    "imageUrl": "https://arweave.net/orca-logo.png",
    "price": "3.45",
    "circulatingSupply": "50000000",
    "totalSupply": "100000000",
    "stats": {
        "24h": {
            "volume": "433016.17",
        },
    },
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/pools": FAKE_POOLS_RESPONSE,
        "/pools/Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE": {"data": FAKE_POOL},
        "/pools/search": FAKE_POOLS_RESPONSE,
        "/tokens": FAKE_TOKENS_RESPONSE,
        "/tokens/orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE": {"data": FAKE_TOKEN},
        "/tokens/search": FAKE_TOKENS_RESPONSE,
        "/protocol": FAKE_PROTOCOL_STATS,
        "/protocol/token": FAKE_PROTOCOL_TOKEN,
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
    """OrcaService with mocked HTTP client."""
    from orca_mcp.service import OrcaService

    svc = OrcaService.__new__(OrcaService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked OrcaService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-orca", version="0.0.1")
    srv.register(service)
    return srv
