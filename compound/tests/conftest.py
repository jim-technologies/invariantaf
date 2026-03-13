"""Shared fixtures for Compound MCP tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compound_mcp.gen.compound.v1 import compound_pb2 as pb

DESCRIPTOR_PATH = str(Path(__file__).parent.parent / "descriptor.binpb")

# ---------------------------------------------------------------------------
# Fake API data -- matches real Compound v2 API return shapes
# ---------------------------------------------------------------------------

FAKE_CTOKEN_DAI = {
    "token_address": "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
    "name": "Compound Dai",
    "symbol": "cDAI",
    "underlying": {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "name": "Dai",
        "symbol": "DAI",
        "decimals": "18",
        "price": {"value": "1.00"},
    },
    "supply_rate": {"value": "0.032"},
    "borrow_rate": {"value": "0.055"},
    "total_supply": {"value": "350000000.123456"},
    "total_borrows": {"value": "210000000.654321"},
    "reserves": {"value": "5000000.789"},
    "cash": {"value": "145000000.000"},
    "collateral_factor": {"value": "0.75"},
    "exchange_rate": {"value": "0.022"},
    "number_of_suppliers": 12345,
    "number_of_borrowers": 6789,
    "reserve_factor": {"value": "0.15"},
    "borrow_cap": {"value": "0"},
}

FAKE_CTOKEN_ETH = {
    "token_address": "0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5",
    "name": "Compound Ether",
    "symbol": "cETH",
    "underlying": {
        "address": "0x0000000000000000000000000000000000000000",
        "name": "Ether",
        "symbol": "ETH",
        "decimals": "18",
        "price": {"value": "3200.50"},
    },
    "supply_rate": {"value": "0.018"},
    "borrow_rate": {"value": "0.042"},
    "total_supply": {"value": "1500000.5"},
    "total_borrows": {"value": "800000.25"},
    "reserves": {"value": "30000.1"},
    "cash": {"value": "730000.15"},
    "collateral_factor": {"value": "0.82"},
    "exchange_rate": {"value": "0.020"},
    "number_of_suppliers": 45678,
    "number_of_borrowers": 23456,
    "reserve_factor": {"value": "0.20"},
    "borrow_cap": {"value": "100000"},
}

FAKE_CTOKEN_USDC = {
    "token_address": "0x39AA39c021dfbaE8faC545936693aC917d5E7563",
    "name": "Compound USD Coin",
    "symbol": "cUSDC",
    "underlying": {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "name": "USD Coin",
        "symbol": "USDC",
        "decimals": "6",
        "price": {"value": "1.00"},
    },
    "supply_rate": {"value": "0.028"},
    "borrow_rate": {"value": "0.048"},
    "total_supply": {"value": "500000000.00"},
    "total_borrows": {"value": "300000000.00"},
    "reserves": {"value": "8000000.00"},
    "cash": {"value": "208000000.00"},
    "collateral_factor": {"value": "0.80"},
    "exchange_rate": {"value": "0.021"},
    "number_of_suppliers": 34567,
    "number_of_borrowers": 12345,
    "reserve_factor": {"value": "0.10"},
    "borrow_cap": {"value": "0"},
}

FAKE_CTOKENS_RESPONSE = {
    "cToken": [FAKE_CTOKEN_DAI, FAKE_CTOKEN_ETH, FAKE_CTOKEN_USDC],
    "error": None,
    "request": {"addresses": [], "block_timestamp": 0, "network": "mainnet"},
}

FAKE_MARKET_HISTORY = {
    "market_history": [
        {
            "block_number": 18000000,
            "block_timestamp": 1700000000,
            "rates": [{"rate": "0.031"}],
            "total_supply": {"value": "340000000.00"},
            "total_borrows": {"value": "200000000.00"},
        },
        {
            "block_number": 18100000,
            "block_timestamp": 1700100000,
            "rates": [{"rate": "0.033"}],
            "total_supply": {"value": "345000000.00"},
            "total_borrows": {"value": "205000000.00"},
        },
        {
            "block_number": 18200000,
            "block_timestamp": 1700200000,
            "rates": [{"rate": "0.032"}],
            "total_supply": {"value": "350000000.00"},
            "total_borrows": {"value": "210000000.00"},
        },
    ],
    "error": None,
}

FAKE_PROPOSALS = {
    "proposals": [
        {
            "id": 130,
            "title": "Add WBTC Market",
            "description": "Proposal to add WBTC as a supported collateral asset.",
            "state": "Executed",
            "proposer": "0x1234567890abcdef1234567890abcdef12345678",
            "for_votes": "500000",
            "against_votes": "10000",
            "start_block": 17900000,
            "end_block": 17920000,
            "created_at": 1699500000,
        },
        {
            "id": 131,
            "title": "Update Interest Rate Model",
            "description": "Update the interest rate model for USDC market.",
            "state": "Active",
            "proposer": "0xabcdef1234567890abcdef1234567890abcdef12",
            "for_votes": "300000",
            "against_votes": "50000",
            "start_block": 18100000,
            "end_block": 18120000,
            "created_at": 1700000000,
        },
        {
            "id": 132,
            "title": "Reduce COMP Rewards",
            "description": "Reduce COMP distribution rate to preserve token reserves.",
            "state": "Defeated",
            "proposer": "0x9876543210fedcba9876543210fedcba98765432",
            "for_votes": "100000",
            "against_votes": "400000",
            "start_block": 18050000,
            "end_block": 18070000,
            "created_at": 1699800000,
        },
    ],
    "error": None,
    "request": {"page_size": 10, "page_number": 1},
}


def _make_mock_http(url_responses: dict | None = None):
    """Create a mock httpx.Client with configurable responses."""
    defaults = {
        "/ctoken": FAKE_CTOKENS_RESPONSE,
        "/market_history/graph": FAKE_MARKET_HISTORY,
        "/governance/proposals": FAKE_PROPOSALS,
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
    """CompoundService with mocked HTTP client."""
    from compound_mcp.service import CompoundService

    svc = CompoundService.__new__(CompoundService)
    svc._http = mock_http
    return svc


@pytest.fixture
def server(service):
    """Invariant Server with the mocked CompoundService registered."""
    from invariant import Server

    srv = Server.from_descriptor(DESCRIPTOR_PATH, name="test-compound", version="0.0.1")
    srv.register(service)
    return srv
