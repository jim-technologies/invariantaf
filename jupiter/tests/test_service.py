"""Unit tests for JupiterService — uses mocked HTTP responses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jupiter_mcp.gen.jupiter.v1 import jupiter_pb2 as pb
from tests.conftest import SOL_MINT, USDC_MINT


class TestGetPrice:
    def test_returns_prices(self, service):
        req = pb.GetPriceRequest(ids=f"{SOL_MINT},{USDC_MINT}")
        resp = service.GetPrice(req)
        assert len(resp.prices) == 2
        mints = {p.mint for p in resp.prices}
        assert SOL_MINT in mints
        assert USDC_MINT in mints
        sol_price = next(p for p in resp.prices if p.mint == SOL_MINT)
        assert sol_price.price == pytest.approx(172.50)
        assert sol_price.liquidity > 0
        assert sol_price.price_change_24h == pytest.approx(1.29)


class TestGetQuote:
    def test_returns_quote(self, service):
        req = pb.GetQuoteRequest(
            input_mint=SOL_MINT,
            output_mint=USDC_MINT,
            amount="1000000000",
            slippage_bps=50,
        )
        resp = service.GetQuote(req)
        assert resp.input_mint == SOL_MINT
        assert resp.output_mint == USDC_MINT
        assert resp.in_amount == "1000000000"
        assert resp.out_amount == "172350000"
        assert resp.swap_mode == "ExactIn"
        assert resp.slippage_bps == 50
        assert len(resp.route_plan) == 1
        step = resp.route_plan[0]
        assert step.label == "Raydium"
        assert step.percent == 100


class TestSwap:
    def test_returns_transaction(self, service):
        quote_json = json.dumps({
            "inputMint": SOL_MINT,
            "outputMint": USDC_MINT,
            "inAmount": "1000000000",
            "outAmount": "172350000",
        })
        req = pb.SwapRequest(
            quote_response=quote_json,
            user_public_key="5ZWj7a1f8tWkjBESHKgrLmXshuXxqeY9SYcfbshpAqPG",
            wrap_and_unwrap_sol=True,
        )
        resp = service.Swap(req)
        assert resp.swap_transaction != ""
        assert resp.last_valid_block_height == 280000000


class TestListTokens:
    def test_returns_tokens(self, service):
        req = pb.ListTokensRequest(query="SOL")
        resp = service.ListTokens(req)
        assert len(resp.tokens) == 3
        symbols = {t.symbol for t in resp.tokens}
        assert "SOL" in symbols
        assert "USDC" in symbols
        assert "JUP" in symbols

    def test_token_fields(self, service):
        req = pb.ListTokensRequest(query="SOL")
        resp = service.ListTokens(req)
        sol = next(t for t in resp.tokens if t.symbol == "SOL")
        assert sol.address == SOL_MINT
        assert sol.name == "Wrapped SOL"
        assert sol.decimals == 9
        assert sol.logo_uri != ""
        assert sol.is_verified is True


class TestListVerifiedTokens:
    def test_returns_verified_only(self, service):
        req = pb.ListVerifiedTokensRequest()
        resp = service.ListVerifiedTokens(req)
        assert len(resp.tokens) == 2
        symbols = {t.symbol for t in resp.tokens}
        assert "SOL" in symbols
        assert "USDC" in symbols
        for t in resp.tokens:
            assert t.is_verified is True


class TestListMarkets:
    def test_returns_markets(self, service):
        req = pb.ListMarketsRequest()
        resp = service.ListMarkets(req)
        assert len(resp.markets) == 2
        labels = {m.label for m in resp.markets}
        assert "Raydium" in labels
        assert "Orca" in labels

    def test_market_fields(self, service):
        req = pb.ListMarketsRequest()
        resp = service.ListMarkets(req)
        m = resp.markets[0]
        assert m.id != ""
        assert m.base_mint == SOL_MINT
        assert m.quote_mint == USDC_MINT
        assert m.liquidity > 0
