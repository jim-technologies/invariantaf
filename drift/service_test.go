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

// mockDriftServer creates a test server that returns realistic Drift API responses.
func mockDriftServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/stats/markets":
			json.NewEncoder(w).Encode(map[string]any{
				"success": true,
				"markets": []any{
					map[string]any{
						"symbol":      "SOL-PERP",
						"marketIndex": float64(0),
						"marketType":  "perp",
						"baseAsset":   "SOL",
						"quoteAsset":  "USDC",
						"status":      "active",
						"oraclePrice": "128.50",
						"markPrice":   "128.45",
						"baseVolume":  "500000.00",
						"quoteVolume": "64000000.00",
						"openInterest": map[string]any{
							"long":  "250000.00",
							"short": "-260000.00",
						},
						"fundingRate": map[string]any{
							"long":  "0.003",
							"short": "-0.003",
						},
						"fundingRate24h":        "-0.002",
						"fundingRateUpdateTs":   float64(1700000000),
						"price":                 "128.50",
						"priceChange24h":        "2.50",
						"priceChange24hPercent": "1.98",
						"fees": map[string]any{
							"maker": -0.00002,
							"taker": 0.00035,
						},
					},
					map[string]any{
						"symbol":      "BTC-PERP",
						"marketIndex": float64(1),
						"marketType":  "perp",
						"baseAsset":   "BTC",
						"quoteAsset":  "USDC",
						"status":      "active",
						"oraclePrice": "43000.00",
						"markPrice":   "42995.00",
						"baseVolume":  "150.00",
						"quoteVolume": "6450000.00",
						"openInterest": map[string]any{
							"long":  "500.00",
							"short": "-520.00",
						},
						"fundingRate": map[string]any{
							"long":  "0.001",
							"short": "-0.001",
						},
						"fundingRate24h":        "0.001",
						"fundingRateUpdateTs":   float64(1700000000),
						"price":                 "43000.00",
						"priceChange24h":        "500.00",
						"priceChange24hPercent": "1.18",
						"fees": map[string]any{
							"maker": -0.00002,
							"taker": 0.00035,
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/candles/"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"ts":          float64(1700000000),
					"fillOpen":    128.00,
					"fillHigh":    129.50,
					"fillLow":     127.50,
					"fillClose":   128.50,
					"oracleOpen":  128.10,
					"oracleHigh":  129.40,
					"oracleLow":   127.60,
					"oracleClose": 128.45,
					"quoteVolume": 5000000.0,
					"baseVolume":  39000.0,
				},
				map[string]any{
					"ts":          float64(1700003600),
					"fillOpen":    128.50,
					"fillHigh":    130.00,
					"fillLow":     128.00,
					"fillClose":   129.80,
					"oracleOpen":  128.45,
					"oracleHigh":  129.90,
					"oracleLow":   128.10,
					"oracleClose": 129.75,
					"quoteVolume": 6000000.0,
					"baseVolume":  46000.0,
				},
			})

		case strings.HasSuffix(r.URL.Path, "/trades"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"ts":                      float64(1700000100),
					"txSig":                   "5abc123def456...",
					"baseAssetAmountFilled":   "10.500",
					"quoteAssetAmountFilled":  "1349.25",
					"takerFee":               "0.472",
					"makerRebate":            "0.027",
					"oraclePrice":            "128.50",
					"action":                 "fill",
					"takerOrderDirection":    "long",
					"makerOrderDirection":    "short",
					"symbol":                "SOL-PERP",
				},
				map[string]any{
					"ts":                      float64(1700000200),
					"txSig":                   "6def789abc012...",
					"baseAssetAmountFilled":   "5.000",
					"quoteAssetAmountFilled":  "642.50",
					"takerFee":               "0.225",
					"makerRebate":            "0.013",
					"oraclePrice":            "128.50",
					"action":                 "fill",
					"takerOrderDirection":    "short",
					"makerOrderDirection":    "long",
					"symbol":                "SOL-PERP",
				},
			})

		case r.URL.Path == "/stats/fundingRates":
			json.NewEncoder(w).Encode(map[string]any{
				"success": true,
				"markets": []any{
					map[string]any{
						"marketIndex": float64(0),
						"symbol":      "SOL-PERP",
						"fundingRates": map[string]any{
							"24h": "0.003",
							"7d":  "0.002",
							"30d": "0.0025",
							"1y":  "0.0022",
						},
					},
					map[string]any{
						"marketIndex": float64(1),
						"symbol":      "BTC-PERP",
						"fundingRates": map[string]any{
							"24h": "0.001",
							"7d":  "0.0015",
							"30d": "0.0012",
							"1y":  "0.001",
						},
					},
				},
			})

		case strings.HasSuffix(r.URL.Path, "/fundingRates"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"ts":                            float64(1700000000),
					"txSig":                         "7ghi345jkl678...",
					"recordId":                      float64(12345),
					"marketIndex":                   float64(0),
					"symbol":                        "SOL-PERP",
					"fundingRate":                   "0.000125",
					"fundingRateLong":               "0.000125",
					"fundingRateShort":              "-0.000125",
					"cumulativeFundingRateLong":     "1.234567",
					"cumulativeFundingRateShort":    "-1.234567",
					"oraclePriceTwap":              "128.45",
					"markPriceTwap":                "128.50",
					"periodRevenue":                "5000",
					"baseAssetAmountWithAmm":       "10000",
				},
				map[string]any{
					"ts":                            float64(1699996400),
					"txSig":                         "8mno901pqr234...",
					"recordId":                      float64(12344),
					"marketIndex":                   float64(0),
					"symbol":                        "SOL-PERP",
					"fundingRate":                   "0.000100",
					"fundingRateLong":               "0.000100",
					"fundingRateShort":              "-0.000100",
					"cumulativeFundingRateLong":     "1.234442",
					"cumulativeFundingRateShort":    "-1.234442",
					"oraclePriceTwap":              "128.00",
					"markPriceTwap":                "128.05",
					"periodRevenue":                "4500",
					"baseAssetAmountWithAmm":       "10000",
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

func newTestService(serverURL string) *DriftService {
	return &DriftService{
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
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	if fields["success"] == nil || !fields["success"].GetBoolValue() {
		t.Fatal("expected success: true")
	}

	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 markets, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["symbol"].GetStringValue(); got != "SOL-PERP" {
		t.Errorf("symbol = %q, want %q", got, "SOL-PERP")
	}
	if got := first["marketType"].GetStringValue(); got != "perp" {
		t.Errorf("marketType = %q, want %q", got, "perp")
	}
	if got := first["oraclePrice"].GetStringValue(); got != "128.50" {
		t.Errorf("oraclePrice = %q, want %q", got, "128.50")
	}
	if got := first["baseAsset"].GetStringValue(); got != "SOL" {
		t.Errorf("baseAsset = %q, want %q", got, "SOL")
	}

	second := items[1].GetStructValue().GetFields()
	if got := second["symbol"].GetStringValue(); got != "BTC-PERP" {
		t.Errorf("symbol = %q, want %q", got, "BTC-PERP")
	}
}

func TestGetCandles(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"symbol":     "SOL-PERP",
		"resolution": "60",
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	candles := items.GetListValue().GetValues()
	if len(candles) != 2 {
		t.Fatalf("expected 2 candles, got %d", len(candles))
	}

	first := candles[0].GetStructValue().GetFields()
	if got := first["ts"].GetNumberValue(); got != 1700000000 {
		t.Errorf("ts = %v, want 1700000000", got)
	}
	if got := first["fillOpen"].GetNumberValue(); got != 128.00 {
		t.Errorf("fillOpen = %v, want 128.00", got)
	}
	if got := first["fillHigh"].GetNumberValue(); got != 129.50 {
		t.Errorf("fillHigh = %v, want 129.50", got)
	}
	if got := first["fillClose"].GetNumberValue(); got != 128.50 {
		t.Errorf("fillClose = %v, want 128.50", got)
	}
	if got := first["quoteVolume"].GetNumberValue(); got != 5000000.0 {
		t.Errorf("quoteVolume = %v, want 5000000.0", got)
	}
}

func TestGetCandlesWithParams(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"symbol":     "SOL-PERP",
		"resolution": "D",
		"start_ts":   float64(1699900000),
		"end_ts":     float64(1700100000),
		"limit":      float64(50),
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	if len(items.GetListValue().GetValues()) == 0 {
		t.Fatal("expected at least 1 candle")
	}
}

func TestGetCandlesRequiresSymbol(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"resolution": "60",
	}))
	if err == nil {
		t.Fatal("expected error for missing symbol")
	}
	if !strings.Contains(err.Error(), "symbol is required") {
		t.Errorf("error = %q, want to contain 'symbol is required'", err.Error())
	}
}

func TestGetCandlesRequiresResolution(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
	}))
	if err == nil {
		t.Fatal("expected error for missing resolution")
	}
	if !strings.Contains(err.Error(), "resolution is required") {
		t.Errorf("error = %q, want to contain 'resolution is required'", err.Error())
	}
}

func TestGetTrades(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
	}))
	if err != nil {
		t.Fatalf("GetTrades: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	trades := items.GetListValue().GetValues()
	if len(trades) != 2 {
		t.Fatalf("expected 2 trades, got %d", len(trades))
	}

	first := trades[0].GetStructValue().GetFields()
	if got := first["ts"].GetNumberValue(); got != 1700000100 {
		t.Errorf("ts = %v, want 1700000100", got)
	}
	if got := first["baseAssetAmountFilled"].GetStringValue(); got != "10.500" {
		t.Errorf("baseAssetAmountFilled = %q, want %q", got, "10.500")
	}
	if got := first["takerOrderDirection"].GetStringValue(); got != "long" {
		t.Errorf("takerOrderDirection = %q, want %q", got, "long")
	}
	if got := first["symbol"].GetStringValue(); got != "SOL-PERP" {
		t.Errorf("symbol = %q, want %q", got, "SOL-PERP")
	}
}

func TestGetTradesRequiresSymbol(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing symbol")
	}
	if !strings.Contains(err.Error(), "symbol is required") {
		t.Errorf("error = %q, want to contain 'symbol is required'", err.Error())
	}
}

func TestGetTradesWithPagination(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
		"limit":  float64(10),
	}))
	if err != nil {
		t.Fatalf("GetTrades: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
}

func TestGetFundingRates(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFundingRates(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
	}))
	if err != nil {
		t.Fatalf("GetFundingRates: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	records := items.GetListValue().GetValues()
	if len(records) != 2 {
		t.Fatalf("expected 2 records, got %d", len(records))
	}

	first := records[0].GetStructValue().GetFields()
	if got := first["ts"].GetNumberValue(); got != 1700000000 {
		t.Errorf("ts = %v, want 1700000000", got)
	}
	if got := first["symbol"].GetStringValue(); got != "SOL-PERP" {
		t.Errorf("symbol = %q, want %q", got, "SOL-PERP")
	}
	if got := first["fundingRate"].GetStringValue(); got != "0.000125" {
		t.Errorf("fundingRate = %q, want %q", got, "0.000125")
	}
	if got := first["fundingRateLong"].GetStringValue(); got != "0.000125" {
		t.Errorf("fundingRateLong = %q, want %q", got, "0.000125")
	}
	if got := first["fundingRateShort"].GetStringValue(); got != "-0.000125" {
		t.Errorf("fundingRateShort = %q, want %q", got, "-0.000125")
	}
	if got := first["oraclePriceTwap"].GetStringValue(); got != "128.45" {
		t.Errorf("oraclePriceTwap = %q, want %q", got, "128.45")
	}
}

func TestGetFundingRatesRequiresSymbol(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetFundingRates(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing symbol")
	}
	if !strings.Contains(err.Error(), "symbol is required") {
		t.Errorf("error = %q, want to contain 'symbol is required'", err.Error())
	}
}

func TestGetFundingRatesWithLimit(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFundingRates(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
		"limit":  float64(100),
	}))
	if err != nil {
		t.Fatalf("GetFundingRates: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
}

func TestGetFundingRateStats(t *testing.T) {
	ts := mockDriftServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFundingRateStats(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetFundingRateStats: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFundingRateStats")
	}

	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 market stats, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["symbol"].GetStringValue(); got != "SOL-PERP" {
		t.Errorf("symbol = %q, want %q", got, "SOL-PERP")
	}

	rates := first["fundingRates"].GetStructValue().GetFields()
	if got := rates["24h"].GetStringValue(); got != "0.003" {
		t.Errorf("24h rate = %q, want %q", got, "0.003")
	}
	if got := rates["7d"].GetStringValue(); got != "0.002" {
		t.Errorf("7d rate = %q, want %q", got, "0.002")
	}
}

// --- Live integration tests (hit the real Drift API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("DRIFT_RUN_LIVE_TESTS") == "" {
		t.Skip("set DRIFT_RUN_LIVE_TESTS=1 to run live integration tests (hits real Drift API)")
	}
}

func liveService() *DriftService {
	return NewDriftService()
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

	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 market")
	}

	// Check that SOL-PERP exists
	found := false
	for _, item := range items {
		m := item.GetStructValue().GetFields()
		if m["symbol"].GetStringValue() == "SOL-PERP" {
			found = true
			t.Logf("SOL-PERP oraclePrice=%s fundingRate24h=%s",
				m["oraclePrice"].GetStringValue(),
				m["fundingRate24h"].GetStringValue())
			break
		}
	}
	if !found {
		t.Error("SOL-PERP not found in market list")
	}

	t.Logf("ListMarkets returned %d markets", len(items))
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"symbol":     "SOL-PERP",
		"resolution": "60",
		"limit":      float64(5),
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetCandles")
	}
	t.Logf("GetCandles response keys: %v", keysOf(fields))

	// The live API wraps results under "records" or "items".
	var candles []*structpb.Value
	if records, ok := fields["records"]; ok {
		candles = records.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok {
		candles = items.GetListValue().GetValues()
	}
	if len(candles) == 0 {
		t.Fatal("expected at least 1 candle")
	}

	first := candles[0].GetStructValue().GetFields()
	if first["ts"].GetNumberValue() == 0 {
		t.Error("candle ts should not be 0")
	}
	t.Logf("First candle: ts=%v fillOpen=%v fillClose=%v quoteVolume=%v",
		first["ts"].GetNumberValue(),
		first["fillOpen"].GetNumberValue(),
		first["fillClose"].GetNumberValue(),
		first["quoteVolume"].GetNumberValue())
}

func TestLiveGetTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
		"limit":  float64(5),
	}))
	if err != nil {
		t.Fatalf("GetTrades: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTrades")
	}
	t.Logf("GetTrades response keys: %v", keysOf(fields))

	var trades []*structpb.Value
	if records, ok := fields["records"]; ok {
		trades = records.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok {
		trades = items.GetListValue().GetValues()
	}
	if len(trades) == 0 {
		t.Fatal("expected at least 1 trade")
	}

	first := trades[0].GetStructValue().GetFields()
	t.Logf("First trade: ts=%v oraclePrice=%s takerDir=%s",
		first["ts"].GetNumberValue(),
		first["oraclePrice"].GetStringValue(),
		first["takerOrderDirection"].GetStringValue())
}

func TestLiveGetFundingRates(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFundingRates(context.Background(), mustStruct(t, map[string]any{
		"symbol": "SOL-PERP",
		"limit":  float64(5),
	}))
	if err != nil {
		t.Fatalf("GetFundingRates: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFundingRates")
	}
	t.Logf("GetFundingRates response keys: %v", keysOf(fields))

	var fundingRecords []*structpb.Value
	if recs, ok := fields["records"]; ok {
		fundingRecords = recs.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok {
		fundingRecords = items.GetListValue().GetValues()
	}
	if len(fundingRecords) == 0 {
		t.Fatal("expected at least 1 funding rate record")
	}

	first := fundingRecords[0].GetStructValue().GetFields()
	t.Logf("First funding rate: ts=%v rate=%s rateLong=%s rateShort=%s oracleTwap=%s",
		first["ts"].GetNumberValue(),
		first["fundingRate"].GetStringValue(),
		first["fundingRateLong"].GetStringValue(),
		first["fundingRateShort"].GetStringValue(),
		first["oraclePriceTwap"].GetStringValue())
}

func TestLiveGetFundingRateStats(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFundingRateStats(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetFundingRateStats: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFundingRateStats")
	}

	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 market in funding rate stats")
	}

	// Check SOL-PERP exists in stats
	found := false
	for _, item := range items {
		m := item.GetStructValue().GetFields()
		if m["symbol"].GetStringValue() == "SOL-PERP" {
			found = true
			rates := m["fundingRates"].GetStructValue().GetFields()
			t.Logf("SOL-PERP funding stats: 24h=%s 7d=%s 30d=%s 1y=%s",
				rates["24h"].GetStringValue(),
				rates["7d"].GetStringValue(),
				rates["30d"].GetStringValue(),
				rates["1y"].GetStringValue())
			break
		}
	}
	if !found {
		t.Error("SOL-PERP not found in funding rate stats")
	}

	t.Logf("GetFundingRateStats returned %d markets", len(items))
}

// --- helpers ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
