package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockVenusServer creates a test server that returns realistic Venus API responses.
func mockVenusServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.HasPrefix(r.URL.Path, "/markets/core-pool"):
			underlyingAddr := r.URL.Query().Get("underlyingAddress")
			if underlyingAddr != "" {
				// GetMarket: return a single market filtered by underlying address
				json.NewEncoder(w).Encode(map[string]any{
					"result": []any{
						map[string]any{
							"address":          "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63",
							"underlyingSymbol": "BNB",
							"underlyingAddress": underlyingAddr,
							"underlyingName":   "BNB",
							"supplyApy":        float64(2.45),
							"borrowApy":        float64(4.12),
							"totalSupplyUsd":   float64(1250000000),
							"totalBorrowsUsd":  float64(890000000),
							"liquidityUsd":     float64(360000000),
							"underlyingPriceUsd": float64(312.50),
							"collateralFactor": 0.80,
						},
					},
				})
			} else {
				// ListMarkets: return all markets
				json.NewEncoder(w).Encode(map[string]any{
					"result": []any{
						map[string]any{
							"address":          "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63",
							"underlyingSymbol": "BNB",
							"underlyingAddress": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
							"underlyingName":   "BNB",
							"supplyApy":        float64(2.45),
							"borrowApy":        float64(4.12),
							"totalSupplyUsd":   float64(1250000000),
							"totalBorrowsUsd":  float64(890000000),
							"liquidityUsd":     float64(360000000),
							"underlyingPriceUsd": float64(312.50),
							"collateralFactor": 0.80,
						},
						map[string]any{
							"address":          "0xfD5840Cd36d94D7229439859C0112a4185BC0255",
							"underlyingSymbol": "USDT",
							"underlyingAddress": "0x55d398326f99059fF775485246999027B3197955",
							"underlyingName":   "Tether USD",
							"supplyApy":        float64(3.18),
							"borrowApy":        float64(5.67),
							"totalSupplyUsd":   float64(980000000),
							"totalBorrowsUsd":  float64(720000000),
							"liquidityUsd":     float64(260000000),
							"underlyingPriceUsd": float64(1.00),
							"collateralFactor": 0.80,
						},
						map[string]any{
							"address":          "0x882C173bC7Ff3b7786CA16dfeD3DFFfb9Ee7847B",
							"underlyingSymbol": "BTCB",
							"underlyingAddress": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
							"underlyingName":   "Bitcoin BEP2",
							"supplyApy":        float64(0.85),
							"borrowApy":        float64(2.34),
							"totalSupplyUsd":   float64(450000000),
							"totalBorrowsUsd":  float64(180000000),
							"liquidityUsd":     float64(270000000),
							"underlyingPriceUsd": float64(67500.00),
							"collateralFactor": 0.75,
						},
					},
				})
			}

		case r.URL.Path == "/pools/liquidity":
			json.NewEncoder(w).Encode(map[string]any{
				"result": []any{
					map[string]any{
						"name":                  "Core Pool",
						"totalSupplyUsd":        float64(3500000000),
						"totalBorrowsUsd":       float64(2100000000),
						"availableLiquidityUsd": float64(1400000000),
					},
					map[string]any{
						"name":                  "DeFi Pool",
						"totalSupplyUsd":        float64(250000000),
						"totalBorrowsUsd":       float64(120000000),
						"availableLiquidityUsd": float64(130000000),
					},
				},
			})

		case r.URL.Path == "/pools":
			json.NewEncoder(w).Encode(map[string]any{
				"result": []any{
					map[string]any{
						"name":         "Core Pool",
						"description":  "The main Venus lending pool with major assets",
						"comptroller":  "0xfD36E2c2a6789Db23113685031d7F16329158384",
					},
					map[string]any{
						"name":         "DeFi Pool",
						"description":  "Isolated lending pool for DeFi tokens",
						"comptroller":  "0x3344417c9360b963ca93A4e8305361AEde340Ab9",
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(serverURL string) *VenusService {
	return &VenusService{
		baseURL: serverURL,
		client:  &http.Client{},
	}
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

// --- Mock Tests ---

func TestListMarkets(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	result := fields["result"]
	if result == nil {
		t.Fatal("response has no 'result' field")
	}
	items := result.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 markets, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["underlyingSymbol"].GetStringValue(); got != "BNB" {
		t.Errorf("underlyingSymbol = %q, want %q", got, "BNB")
	}
	if got := first["supplyApy"].GetNumberValue(); got != 2.45 {
		t.Errorf("supplyApy = %v, want 2.45", got)
	}
	if got := first["borrowApy"].GetNumberValue(); got != 4.12 {
		t.Errorf("borrowApy = %v, want 4.12", got)
	}
	if got := first["totalSupplyUsd"].GetNumberValue(); got != 1250000000 {
		t.Errorf("totalSupplyUsd = %v, want 1250000000", got)
	}
	if got := first["collateralFactor"].GetNumberValue(); got != 0.80 {
		t.Errorf("collateralFactor = %v, want 0.80", got)
	}

	third := items[2].GetStructValue().GetFields()
	if got := third["underlyingSymbol"].GetStringValue(); got != "BTCB" {
		t.Errorf("underlyingSymbol = %q, want %q", got, "BTCB")
	}
	if got := third["underlyingPriceUsd"].GetNumberValue(); got != 67500.00 {
		t.Errorf("underlyingPriceUsd = %v, want 67500.00", got)
	}
}

func TestGetMarket(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{
		"underlying_address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
	}))
	if err != nil {
		t.Fatalf("GetMarket: %v", err)
	}

	fields := resp.GetFields()
	result := fields["result"]
	if result == nil {
		t.Fatal("response has no 'result' field")
	}
	items := result.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 market, got %d", len(items))
	}

	market := items[0].GetStructValue().GetFields()
	if got := market["underlyingSymbol"].GetStringValue(); got != "BNB" {
		t.Errorf("underlyingSymbol = %q, want %q", got, "BNB")
	}
	if got := market["underlyingAddress"].GetStringValue(); got != "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" {
		t.Errorf("underlyingAddress = %q, want %q", got, "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
	}
	if got := market["supplyApy"].GetNumberValue(); got != 2.45 {
		t.Errorf("supplyApy = %v, want 2.45", got)
	}
	if got := market["liquidityUsd"].GetNumberValue(); got != 360000000 {
		t.Errorf("liquidityUsd = %v, want 360000000", got)
	}
}

func TestGetMarketRequiresAddress(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing underlying_address")
	}
	if !strings.Contains(err.Error(), "underlying_address is required") {
		t.Errorf("error = %q, want to contain 'underlying_address is required'", err.Error())
	}
}

func TestListPools(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListPools: %v", err)
	}

	fields := resp.GetFields()
	result := fields["result"]
	if result == nil {
		t.Fatal("response has no 'result' field")
	}
	items := result.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 pools, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "Core Pool" {
		t.Errorf("name = %q, want %q", got, "Core Pool")
	}
	if got := first["description"].GetStringValue(); got != "The main Venus lending pool with major assets" {
		t.Errorf("description = %q, want %q", got, "The main Venus lending pool with major assets")
	}
	if got := first["comptroller"].GetStringValue(); got != "0xfD36E2c2a6789Db23113685031d7F16329158384" {
		t.Errorf("comptroller = %q, want %q", got, "0xfD36E2c2a6789Db23113685031d7F16329158384")
	}

	second := items[1].GetStructValue().GetFields()
	if got := second["name"].GetStringValue(); got != "DeFi Pool" {
		t.Errorf("name = %q, want %q", got, "DeFi Pool")
	}
}

func TestGetPoolLiquidity(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPoolLiquidity(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetPoolLiquidity: %v", err)
	}

	fields := resp.GetFields()
	result := fields["result"]
	if result == nil {
		t.Fatal("response has no 'result' field")
	}
	items := result.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 pools, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "Core Pool" {
		t.Errorf("name = %q, want %q", got, "Core Pool")
	}
	if got := first["totalSupplyUsd"].GetNumberValue(); got != 3500000000 {
		t.Errorf("totalSupplyUsd = %v, want 3500000000", got)
	}
	if got := first["totalBorrowsUsd"].GetNumberValue(); got != 2100000000 {
		t.Errorf("totalBorrowsUsd = %v, want 2100000000", got)
	}
	if got := first["availableLiquidityUsd"].GetNumberValue(); got != 1400000000 {
		t.Errorf("availableLiquidityUsd = %v, want 1400000000", got)
	}

	second := items[1].GetStructValue().GetFields()
	if got := second["name"].GetStringValue(); got != "DeFi Pool" {
		t.Errorf("name = %q, want %q", got, "DeFi Pool")
	}
}

func TestAPIError(t *testing.T) {
	ts := mockVenusServer()
	defer ts.Close()
	svc := &VenusService{
		baseURL: ts.URL,
		client:  &http.Client{},
	}

	// Hit a path that returns 404.
	_, err := svc.get("/nonexistent", url.Values{})
	if err == nil {
		t.Fatal("expected error for 404 response")
	}
	if !strings.Contains(err.Error(), "API error (status 404)") {
		t.Errorf("error = %q, want to contain 'API error (status 404)'", err.Error())
	}
}

// --- Live integration tests (hit the real Venus API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("VENUS_RUN_LIVE_TESTS") == "" {
		t.Skip("set VENUS_RUN_LIVE_TESTS=1 to run live integration tests (hits real Venus API)")
	}
}

func liveService() *VenusService {
	return NewVenusService()
}

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListMarkets")
	}
	t.Logf("ListMarkets response keys: %v", keysOf(fields))
}

func TestLiveGetMarket(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// Query BNB market by underlying address.
	resp, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{
		"underlying_address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
	}))
	if err != nil {
		t.Fatalf("GetMarket: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetMarket")
	}
	t.Logf("GetMarket response keys: %v", keysOf(fields))
}

func TestLiveListPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		if strings.Contains(err.Error(), "400") || strings.Contains(err.Error(), "404") {
			t.Skipf("ListPools API requires additional params: %v", err)
		}
		t.Fatalf("ListPools: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListPools")
	}
	t.Logf("ListPools response keys: %v", keysOf(fields))
}

func TestLiveGetPoolLiquidity(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetPoolLiquidity(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		if strings.Contains(err.Error(), "404") || strings.Contains(err.Error(), "410") {
			t.Skip("GetPoolLiquidity endpoint not available")
		}
		t.Fatalf("GetPoolLiquidity: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPoolLiquidity")
	}
	t.Logf("GetPoolLiquidity response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
