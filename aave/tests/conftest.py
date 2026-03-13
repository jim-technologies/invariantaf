"""Shared fixtures for Aave tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

FAKE_MARKETS_RESPONSE = {
    "data": {
        "markets": [
            {
                "name": "AaveV3Ethereum",
                "chain": {"chainId": 1},
                "totalMarketSize": "34000000000",
                "totalAvailableLiquidity": "20000000000",
                "reserves": [
                    {
                        "underlyingToken": {"symbol": "WETH", "name": "Wrapped Ether"},
                        "supplyInfo": {
                            "apy": {"value": "0.02"},
                            "total": {"value": "5000000"},
                        },
                        "borrowInfo": {
                            "apy": {"value": "0.03"},
                            "total": {"amount": {"value": "3000000"}},
                            "utilizationRate": {"value": "0.6"},
                        },
                        "usdExchangeRate": "2100.50",
                        "isFrozen": False,
                    },
                    {
                        "underlyingToken": {"symbol": "USDC", "name": "USD Coin"},
                        "supplyInfo": {
                            "apy": {"value": "0.05"},
                            "total": {"value": "10000000"},
                        },
                        "borrowInfo": {
                            "apy": {"value": "0.07"},
                            "total": {"amount": {"value": "7000000"}},
                            "utilizationRate": {"value": "0.7"},
                        },
                        "usdExchangeRate": "1.0",
                        "isFrozen": False,
                    },
                ],
            }
        ]
    }
}

FAKE_SUPPLY_APY_HISTORY = {
    "data": {
        "supplyAPYHistory": [
            {"timestamp": 1700000000, "apy": {"value": "0.02"}},
            {"timestamp": 1700100000, "apy": {"value": "0.025"}},
        ]
    }
}

FAKE_BORROW_APY_HISTORY = {
    "data": {
        "borrowAPYHistory": [
            {"timestamp": 1700000000, "apy": {"value": "0.03"}},
            {"timestamp": 1700100000, "apy": {"value": "0.035"}},
        ]
    }
}

FAKE_RESERVE = {
    "data": {
        "reserve": {
            "underlyingToken": {"symbol": "WETH", "name": "Wrapped Ether"},
            "supplyInfo": {
                "apy": {"value": "0.02"},
                "total": {"value": "5000000"},
            },
            "borrowInfo": {
                "apy": {"value": "0.03"},
                "total": {"amount": {"value": "3000000"}},
                "availableLiquidity": {"amount": {"value": "2000000"}},
                "utilizationRate": {"value": "0.6"},
                "reserveFactor": {"value": "0.15"},
            },
            "usdExchangeRate": "2100.50",
            "isFrozen": False,
            "flashLoanEnabled": True,
        }
    }
}


@pytest.fixture(scope="module")
def service():
    from aave_mcp.service import AaveService

    svc = AaveService()

    mock_http = MagicMock()

    def _mock_post(url, json=None):
        query = (json or {}).get("query", "")
        if "markets" in query:
            data = FAKE_MARKETS_RESPONSE
        elif "supplyAPYHistory" in query:
            data = FAKE_SUPPLY_APY_HISTORY
        elif "borrowAPYHistory" in query:
            data = FAKE_BORROW_APY_HISTORY
        elif "reserve" in query:
            data = FAKE_RESERVE
        else:
            data = {"data": {}}

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    mock_http.post = _mock_post
    svc._http = mock_http
    return svc
