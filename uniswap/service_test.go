package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockUniswapServer creates a test server that returns realistic GeckoTerminal API responses.
func mockUniswapServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/dexes/uniswap_v3/pools"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"id":   "eth_0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
						"type": "pool",
						"attributes": map[string]any{
							"address":              "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
							"name":                 "WETH / USDC 0.3%",
							"base_token_price_usd": "3500.25",
							"quote_token_price_usd": "1.00",
							"volume_usd": map[string]any{
								"h24": "125000000.50",
							},
							"reserve_in_usd": "350000000.00",
							"price_change_percentage": map[string]any{
								"h24": "2.5",
							},
						},
						"relationships": map[string]any{
							"base_token": map[string]any{
								"data": map[string]any{
									"id":   "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
									"type": "token",
								},
							},
							"quote_token": map[string]any{
								"data": map[string]any{
									"id":   "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
									"type": "token",
								},
							},
						},
					},
					map[string]any{
						"id":   "eth_0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
						"type": "pool",
						"attributes": map[string]any{
							"address":              "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
							"name":                 "WETH / USDT 0.3%",
							"base_token_price_usd": "3500.25",
							"quote_token_price_usd": "1.00",
							"volume_usd": map[string]any{
								"h24": "85000000.00",
							},
							"reserve_in_usd": "200000000.00",
							"price_change_percentage": map[string]any{
								"h24": "1.8",
							},
						},
						"relationships": map[string]any{
							"base_token": map[string]any{
								"data": map[string]any{
									"id":   "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
									"type": "token",
								},
							},
							"quote_token": map[string]any{
								"data": map[string]any{
									"id":   "eth_0xdac17f958d2ee523a2206206994597c13d831ec7",
									"type": "token",
								},
							},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/ohlcv/day"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": map[string]any{
					"id":   "eth_0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
					"type": "pool_ohlcv",
					"attributes": map[string]any{
						"ohlcv_list": []any{
							[]any{float64(1704067200), 3400.0, 3550.0, 3380.0, 3500.0, 125000000.0},
							[]any{float64(1704153600), 3500.0, 3600.0, 3450.0, 3580.0, 130000000.0},
							[]any{float64(1704240000), 3580.0, 3620.0, 3500.0, 3550.0, 110000000.0},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/trending_pools"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"id":   "eth_0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
						"type": "pool",
						"attributes": map[string]any{
							"address":              "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
							"name":                 "WETH / USDC 0.3%",
							"base_token_price_usd": "3500.25",
							"quote_token_price_usd": "1.00",
							"volume_usd": map[string]any{
								"h24": "125000000.50",
							},
							"reserve_in_usd": "350000000.00",
							"price_change_percentage": map[string]any{
								"h24": "5.2",
							},
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/token_price/"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": map[string]any{
					"id":   "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
					"type": "token_price",
					"attributes": map[string]any{
						"token_prices": map[string]any{
							"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "3500.25",
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/search/pools"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"id":   "eth_0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
						"type": "pool",
						"attributes": map[string]any{
							"address":              "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
							"name":                 "WETH / USDC 0.3%",
							"base_token_price_usd": "3500.25",
							"quote_token_price_usd": "1.00",
							"volume_usd": map[string]any{
								"h24": "125000000.50",
							},
							"reserve_in_usd": "350000000.00",
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/pools/"):
			json.NewEncoder(w).Encode(map[string]any{
				"data": map[string]any{
					"id":   "eth_0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
					"type": "pool",
					"attributes": map[string]any{
						"address":              "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
						"name":                 "WETH / USDC 0.3%",
						"base_token_price_usd": "3500.25",
						"quote_token_price_usd": "1.00",
						"volume_usd": map[string]any{
							"h24": "125000000.50",
						},
						"reserve_in_usd":  "350000000.00",
						"pool_fee":        "0.3%",
						"price_change_percentage": map[string]any{
							"h24": "2.5",
						},
					},
					"relationships": map[string]any{
						"base_token": map[string]any{
							"data": map[string]any{
								"id":   "eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
								"type": "token",
							},
						},
						"quote_token": map[string]any{
							"data": map[string]any{
								"id":   "eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
								"type": "token",
							},
						},
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

func newTestService(serverURL string) *UniswapService {
	return &UniswapService{
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

func TestListTopPools(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListTopPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListTopPools: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 pools, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	attrs := first["attributes"].GetStructValue().GetFields()
	if got := attrs["name"].GetStringValue(); got != "WETH / USDC 0.3%" {
		t.Errorf("name = %q, want %q", got, "WETH / USDC 0.3%")
	}
	if got := attrs["address"].GetStringValue(); got != "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8" {
		t.Errorf("address = %q, want %q", got, "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8")
	}
	if got := attrs["reserve_in_usd"].GetStringValue(); got != "350000000.00" {
		t.Errorf("reserve_in_usd = %q, want %q", got, "350000000.00")
	}
}

func TestListTopPoolsWithPage(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListTopPools(context.Background(), mustStruct(t, map[string]any{
		"page": float64(1),
	}))
	if err != nil {
		t.Fatalf("ListTopPools: %v", err)
	}

	data := resp.GetFields()["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 pool")
	}
}

func TestGetPool(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetPool(context.Background(), mustStruct(t, map[string]any{
		"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
	}))
	if err != nil {
		t.Fatalf("GetPool: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetStructValue().GetFields()
	attrs := data["attributes"].GetStructValue().GetFields()
	if got := attrs["name"].GetStringValue(); got != "WETH / USDC 0.3%" {
		t.Errorf("name = %q, want %q", got, "WETH / USDC 0.3%")
	}
	if got := attrs["base_token_price_usd"].GetStringValue(); got != "3500.25" {
		t.Errorf("base_token_price_usd = %q, want %q", got, "3500.25")
	}
	if got := attrs["reserve_in_usd"].GetStringValue(); got != "350000000.00" {
		t.Errorf("reserve_in_usd = %q, want %q", got, "350000000.00")
	}
	if got := attrs["pool_fee"].GetStringValue(); got != "0.3%" {
		t.Errorf("pool_fee = %q, want %q", got, "0.3%")
	}

	volUsd := attrs["volume_usd"].GetStructValue().GetFields()
	if got := volUsd["h24"].GetStringValue(); got != "125000000.50" {
		t.Errorf("volume_usd.h24 = %q, want %q", got, "125000000.50")
	}
}

func TestGetPoolRequiresAddress(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetPool(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing pool_address")
	}
	if !strings.Contains(err.Error(), "pool_address is required") {
		t.Errorf("error = %q, want to contain 'pool_address is required'", err.Error())
	}
}

func TestGetTokenPrice(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{
		"token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
	}))
	if err != nil {
		t.Fatalf("GetTokenPrice: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetStructValue().GetFields()
	attrs := data["attributes"].GetStructValue().GetFields()
	tokenPrices := attrs["token_prices"].GetStructValue().GetFields()
	if got := tokenPrices["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"].GetStringValue(); got != "3500.25" {
		t.Errorf("token price = %q, want %q", got, "3500.25")
	}
}

func TestGetTokenPriceRequiresAddress(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing token_address")
	}
	if !strings.Contains(err.Error(), "token_address is required") {
		t.Errorf("error = %q, want to contain 'token_address is required'", err.Error())
	}
}

func TestListTrendingPools(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListTrendingPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListTrendingPools: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 trending pool, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	attrs := first["attributes"].GetStructValue().GetFields()
	if got := attrs["name"].GetStringValue(); got != "WETH / USDC 0.3%" {
		t.Errorf("name = %q, want %q", got, "WETH / USDC 0.3%")
	}

	priceChange := attrs["price_change_percentage"].GetStructValue().GetFields()
	if got := priceChange["h24"].GetStringValue(); got != "5.2" {
		t.Errorf("price_change_percentage.h24 = %q, want %q", got, "5.2")
	}
}

func TestGetOHLCV(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetOHLCV(context.Background(), mustStruct(t, map[string]any{
		"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
		"limit":        float64(30),
	}))
	if err != nil {
		t.Fatalf("GetOHLCV: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetStructValue().GetFields()
	attrs := data["attributes"].GetStructValue().GetFields()
	ohlcvList := attrs["ohlcv_list"].GetListValue().GetValues()
	if len(ohlcvList) != 3 {
		t.Fatalf("expected 3 candles, got %d", len(ohlcvList))
	}

	firstCandle := ohlcvList[0].GetListValue().GetValues()
	if len(firstCandle) != 6 {
		t.Fatalf("expected 6 values per candle, got %d", len(firstCandle))
	}
	if got := firstCandle[0].GetNumberValue(); got != 1704067200 {
		t.Errorf("timestamp = %v, want 1704067200", got)
	}
	if got := firstCandle[1].GetNumberValue(); got != 3400.0 {
		t.Errorf("open = %v, want 3400.0", got)
	}
	if got := firstCandle[4].GetNumberValue(); got != 3500.0 {
		t.Errorf("close = %v, want 3500.0", got)
	}
}

func TestGetOHLCVRequiresAddress(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetOHLCV(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing pool_address")
	}
	if !strings.Contains(err.Error(), "pool_address is required") {
		t.Errorf("error = %q, want to contain 'pool_address is required'", err.Error())
	}
}

func TestSearchPools(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchPools(context.Background(), mustStruct(t, map[string]any{
		"query":   "WETH",
		"network": "eth",
	}))
	if err != nil {
		t.Fatalf("SearchPools: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"]
	if data == nil {
		t.Fatal("response has no 'data' field")
	}
	items := data.GetListValue().GetValues()
	if len(items) != 1 {
		t.Fatalf("expected 1 search result, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	attrs := first["attributes"].GetStructValue().GetFields()
	if got := attrs["name"].GetStringValue(); got != "WETH / USDC 0.3%" {
		t.Errorf("name = %q, want %q", got, "WETH / USDC 0.3%")
	}
}

func TestSearchPoolsRequiresQuery(t *testing.T) {
	ts := mockUniswapServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.SearchPools(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing query")
	}
	if !strings.Contains(err.Error(), "query is required") {
		t.Errorf("error = %q, want to contain 'query is required'", err.Error())
	}
}

// --- Live integration tests (hit the real GeckoTerminal API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("UNISWAP_RUN_LIVE_TESTS") == "" {
		t.Skip("set UNISWAP_RUN_LIVE_TESTS=1 to run live integration tests (hits real GeckoTerminal API)")
	}
}

func liveService() *UniswapService {
	return NewUniswapService()
}

func TestLiveListTopPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListTopPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListTopPools: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListTopPools")
	}
	t.Logf("ListTopPools response keys: %v", keysOf(fields))
}

func TestLiveGetPool(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// WETH/USDC 0.3% pool on Uniswap V3
	resp, err := svc.GetPool(context.Background(), mustStruct(t, map[string]any{
		"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
	}))
	if err != nil {
		t.Fatalf("GetPool: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPool")
	}
	t.Logf("GetPool response keys: %v", keysOf(fields))
}

func TestLiveGetTokenPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// WETH address
	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{
		"token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
	}))
	if err != nil {
		t.Fatalf("GetTokenPrice: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTokenPrice")
	}
	t.Logf("GetTokenPrice response keys: %v", keysOf(fields))
}

func TestLiveListTrendingPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListTrendingPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListTrendingPools: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from ListTrendingPools")
	}
	t.Logf("ListTrendingPools response keys: %v", keysOf(fields))
}

func TestLiveGetOHLCV(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetOHLCV(context.Background(), mustStruct(t, map[string]any{
		"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8",
		"limit":        float64(7),
	}))
	if err != nil {
		if strings.Contains(err.Error(), "429") {
			t.Skip("GetOHLCV rate limited (429)")
		}
		t.Fatalf("GetOHLCV: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetOHLCV")
	}
	t.Logf("GetOHLCV response keys: %v", keysOf(fields))
}

func TestLiveSearchPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.SearchPools(context.Background(), mustStruct(t, map[string]any{
		"query":   "WETH",
		"network": "eth",
	}))
	if err != nil {
		if strings.Contains(err.Error(), "429") {
			t.Skip("SearchPools rate limited (429)")
		}
		t.Fatalf("SearchPools: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from SearchPools")
	}
	t.Logf("SearchPools response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
