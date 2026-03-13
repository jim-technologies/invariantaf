"""MorphoService — wraps the Morpho GraphQL API into proto RPCs."""

from __future__ import annotations

from typing import Any

import httpx

from morpho_mcp.gen.morpho.v1 import morpho_pb2 as pb

_GRAPHQL_URL = "https://api.morpho.org/graphql"

# --- GraphQL query templates ---

_MARKETS_QUERY = """
query ListMarkets($first: Int, $skip: Int, $orderBy: MarketOrderBy,
                   $orderDirection: OrderDirection, $where: MarketFilters) {
  markets(first: $first, skip: $skip, orderBy: $orderBy,
          orderDirection: $orderDirection, where: $where) {
    items {
      uniqueKey
      lltv
      loanAsset { symbol address decimals }
      collateralAsset { symbol address decimals }
      morphoBlue { chain { id network } }
      state {
        supplyApy borrowApy netSupplyApy netBorrowApy
        supplyAssetsUsd borrowAssetsUsd
        utilization fee
        liquidityAssetsUsd collateralAssetsUsd
        rewards { supplyApr borrowApr asset { symbol address decimals } }
      }
    }
  }
}
"""

_MARKET_BY_KEY_QUERY = """
query GetMarket($uniqueKey: String!, $chainId: Int) {
  marketByUniqueKey(uniqueKey: $uniqueKey, chainId: $chainId) {
    uniqueKey
    lltv
    loanAsset { symbol address decimals }
    collateralAsset { symbol address decimals }
    morphoBlue { chain { id network } }
    state {
      supplyApy borrowApy netSupplyApy netBorrowApy
      supplyAssetsUsd borrowAssetsUsd
      utilization fee
      liquidityAssetsUsd collateralAssetsUsd
      rewards { supplyApr borrowApr asset { symbol address decimals } }
    }
  }
}
"""

_VAULTS_QUERY = """
query ListVaults($first: Int, $skip: Int, $orderBy: VaultOrderBy,
                  $orderDirection: OrderDirection, $where: VaultFilters) {
  vaults(first: $first, skip: $skip, orderBy: $orderBy,
         orderDirection: $orderDirection, where: $where) {
    items {
      address name symbol
      asset { symbol address decimals }
      chain { id network }
      state {
        apy netApy totalAssetsUsd
        totalAssets totalSupply fee
        rewards { supplyApr asset { symbol address decimals } }
      }
    }
  }
}
"""

_VAULT_BY_ADDRESS_QUERY = """
query GetVault($address: String!, $chainId: Int) {
  vaultByAddress(address: $address, chainId: $chainId) {
    address name symbol
    asset { symbol address decimals }
    chain { id network }
    state {
      apy netApy totalAssetsUsd
      totalAssets totalSupply fee
      rewards { supplyApr asset { symbol address decimals } }
    }
  }
}
"""

_MARKET_POSITIONS_QUERY = """
query ListMarketPositions($first: Int, $skip: Int,
                           $where: MarketPositionFilters) {
  marketPositions(first: $first, skip: $skip, where: $where) {
    items {
      healthFactor
      user { address }
      market {
        uniqueKey lltv
        loanAsset { symbol address decimals }
        collateralAsset { symbol address decimals }
        morphoBlue { chain { id network } }
        state {
          supplyApy borrowApy netSupplyApy netBorrowApy
          supplyAssetsUsd borrowAssetsUsd
          utilization fee
          liquidityAssetsUsd collateralAssetsUsd
          rewards { supplyApr borrowApr asset { symbol address decimals } }
        }
      }
      state {
        supplyAssets supplyAssetsUsd
        borrowAssets borrowAssetsUsd
        collateral collateralUsd
      }
    }
  }
}
"""


class MorphoService:
    """Implements MorphoService RPCs via the Morpho GraphQL API."""

    def __init__(self):
        self._http = httpx.Client(timeout=30)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gql(self, query: str, variables: dict | None = None) -> dict:
        """Execute a GraphQL query and return the data dict."""
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        resp = self._http.post(_GRAPHQL_URL, json=body)
        resp.raise_for_status()
        result = resp.json()
        if "errors" in result:
            raise RuntimeError(f"GraphQL errors: {result['errors']}")
        return result.get("data", {})

    @staticmethod
    def _parse_asset(raw: dict | None) -> pb.Asset | None:
        if not raw:
            return None
        return pb.Asset(
            symbol=raw.get("symbol", ""),
            address=raw.get("address", ""),
            decimals=int(raw.get("decimals", 0)),
        )

    @staticmethod
    def _parse_chain(raw: dict | None) -> pb.Chain | None:
        if not raw:
            return None
        return pb.Chain(
            id=int(raw.get("id", 0)),
            network=raw.get("network", ""),
        )

    @staticmethod
    def _parse_reward(raw: dict) -> pb.Reward:
        asset_raw = raw.get("asset", {})
        return pb.Reward(
            supply_apr=raw.get("supplyApr") or 0.0,
            borrow_apr=raw.get("borrowApr") or 0.0,
            asset=pb.Asset(
                symbol=asset_raw.get("symbol", ""),
                address=asset_raw.get("address", ""),
                decimals=int(asset_raw.get("decimals", 0)),
            ),
        )

    @classmethod
    def _parse_market_state(cls, raw: dict | None) -> pb.MarketState | None:
        if not raw:
            return None
        rewards = [cls._parse_reward(r) for r in raw.get("rewards", [])]
        return pb.MarketState(
            supply_apy=raw.get("supplyApy") or 0.0,
            borrow_apy=raw.get("borrowApy") or 0.0,
            net_supply_apy=raw.get("netSupplyApy") or 0.0,
            net_borrow_apy=raw.get("netBorrowApy") or 0.0,
            supply_assets_usd=raw.get("supplyAssetsUsd") or 0.0,
            borrow_assets_usd=raw.get("borrowAssetsUsd") or 0.0,
            utilization=raw.get("utilization") or 0.0,
            fee=raw.get("fee") or 0.0,
            rewards=rewards,
            liquidity_assets_usd=raw.get("liquidityAssetsUsd") or 0.0,
            collateral_assets_usd=raw.get("collateralAssetsUsd") or 0.0,
        )

    @classmethod
    def _parse_market(cls, raw: dict) -> pb.Market:
        chain_raw = (raw.get("morphoBlue") or {}).get("chain")
        return pb.Market(
            unique_key=raw.get("uniqueKey", ""),
            loan_asset=cls._parse_asset(raw.get("loanAsset")),
            collateral_asset=cls._parse_asset(raw.get("collateralAsset")),
            lltv=str(raw.get("lltv", "")),
            state=cls._parse_market_state(raw.get("state")),
            chain=cls._parse_chain(chain_raw),
        )

    @classmethod
    def _parse_vault_state(cls, raw: dict | None) -> pb.VaultState | None:
        if not raw:
            return None
        rewards = [cls._parse_reward(r) for r in raw.get("rewards", [])]
        return pb.VaultState(
            apy=raw.get("apy") or 0.0,
            net_apy=raw.get("netApy") or 0.0,
            total_assets_usd=raw.get("totalAssetsUsd") or 0.0,
            total_assets=str(raw.get("totalAssets", "")),
            total_supply=str(raw.get("totalSupply", "")),
            fee=raw.get("fee") or 0.0,
            rewards=rewards,
        )

    @classmethod
    def _parse_vault(cls, raw: dict) -> pb.Vault:
        return pb.Vault(
            address=raw.get("address", ""),
            name=raw.get("name", ""),
            symbol=raw.get("symbol", ""),
            asset=cls._parse_asset(raw.get("asset")),
            chain=cls._parse_chain(raw.get("chain")),
            state=cls._parse_vault_state(raw.get("state")),
        )

    # ------------------------------------------------------------------
    # RPC implementations
    # ------------------------------------------------------------------

    def ListMarkets(self, request: Any, context: Any = None) -> pb.ListMarketsResponse:
        first = request.first if hasattr(request, "first") and request.first else 10
        first = min(first, 100)
        skip = request.skip if hasattr(request, "skip") and request.skip else 0

        variables: dict[str, Any] = {"first": first, "skip": skip}

        order_by = getattr(request, "order_by", "") or "SupplyAssetsUsd"
        order_dir = getattr(request, "order_direction", "") or "Desc"
        variables["orderBy"] = order_by
        variables["orderDirection"] = order_dir

        where: dict[str, Any] = {}
        chain_ids = list(getattr(request, "chain_id_in", []) or [])
        if chain_ids:
            where["chainId_in"] = chain_ids
        search = getattr(request, "search", "") or ""
        if search:
            where["search"] = search
        if where:
            variables["where"] = where

        data = self._gql(_MARKETS_QUERY, variables)
        items = (data.get("markets") or {}).get("items", [])
        markets = [self._parse_market(m) for m in items]
        return pb.ListMarketsResponse(markets=markets)

    def GetMarket(self, request: Any, context: Any = None) -> pb.GetMarketResponse:
        unique_key = getattr(request, "unique_key", "") or ""
        if not unique_key:
            raise ValueError("unique_key is required")

        variables: dict[str, Any] = {"uniqueKey": unique_key}
        chain_id = getattr(request, "chain_id", 0) or 0
        if chain_id:
            variables["chainId"] = chain_id

        data = self._gql(_MARKET_BY_KEY_QUERY, variables)
        raw = data.get("marketByUniqueKey", {})
        return pb.GetMarketResponse(market=self._parse_market(raw))

    def ListVaults(self, request: Any, context: Any = None) -> pb.ListVaultsResponse:
        first = request.first if hasattr(request, "first") and request.first else 10
        first = min(first, 100)
        skip = request.skip if hasattr(request, "skip") and request.skip else 0

        variables: dict[str, Any] = {"first": first, "skip": skip}

        order_by = getattr(request, "order_by", "") or "TotalAssetsUsd"
        order_dir = getattr(request, "order_direction", "") or "Desc"
        variables["orderBy"] = order_by
        variables["orderDirection"] = order_dir

        where: dict[str, Any] = {}
        chain_ids = list(getattr(request, "chain_id_in", []) or [])
        if chain_ids:
            where["chainId_in"] = chain_ids
        total_usd_gte = getattr(request, "total_assets_usd_gte", 0) or 0
        if total_usd_gte:
            where["totalAssetsUsd_gte"] = total_usd_gte
        search = getattr(request, "search", "") or ""
        if search:
            where["search"] = search
        if where:
            variables["where"] = where

        data = self._gql(_VAULTS_QUERY, variables)
        items = (data.get("vaults") or {}).get("items", [])
        vaults = [self._parse_vault(v) for v in items]
        return pb.ListVaultsResponse(vaults=vaults)

    def GetVault(self, request: Any, context: Any = None) -> pb.GetVaultResponse:
        address = getattr(request, "address", "") or ""
        if not address:
            raise ValueError("address is required")

        variables: dict[str, Any] = {"address": address}
        chain_id = getattr(request, "chain_id", 0) or 0
        if chain_id:
            variables["chainId"] = chain_id

        data = self._gql(_VAULT_BY_ADDRESS_QUERY, variables)
        raw = data.get("vaultByAddress", {})
        return pb.GetVaultResponse(vault=self._parse_vault(raw))

    def ListMarketPositions(
        self, request: Any, context: Any = None
    ) -> pb.ListMarketPositionsResponse:
        user_address = getattr(request, "user_address", "") or ""
        if not user_address:
            raise ValueError("user_address is required")

        first = request.first if hasattr(request, "first") and request.first else 10
        first = min(first, 100)
        skip = request.skip if hasattr(request, "skip") and request.skip else 0

        where: dict[str, Any] = {"userAddress_in": [user_address]}
        chain_ids = list(getattr(request, "chain_id_in", []) or [])
        if chain_ids:
            where["chainId_in"] = chain_ids

        variables: dict[str, Any] = {"first": first, "skip": skip, "where": where}

        data = self._gql(_MARKET_POSITIONS_QUERY, variables)
        items = (data.get("marketPositions") or {}).get("items", [])

        positions = []
        for item in items:
            state_raw = item.get("state") or {}
            pos_state = pb.MarketPositionState(
                supply_assets=str(state_raw.get("supplyAssets") or ""),
                supply_assets_usd=state_raw.get("supplyAssetsUsd") or 0.0,
                borrow_assets=str(state_raw.get("borrowAssets") or ""),
                borrow_assets_usd=state_raw.get("borrowAssetsUsd") or 0.0,
                collateral=str(state_raw.get("collateral") or ""),
                collateral_usd=state_raw.get("collateralUsd") or 0.0,
            )
            user_raw = item.get("user") or {}
            positions.append(
                pb.MarketPosition(
                    health_factor=item.get("healthFactor") or 0.0,
                    market=self._parse_market(item.get("market") or {}),
                    user_address=user_raw.get("address", ""),
                    state=pos_state,
                )
            )
        return pb.ListMarketPositionsResponse(positions=positions)
