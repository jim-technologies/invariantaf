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

// mockGmxServer creates a test server that returns realistic GMX API responses.
func mockGmxServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.HasPrefix(r.URL.Path, "/markets/info"):
			json.NewEncoder(w).Encode(map[string]any{
				"markets": []any{
					map[string]any{
						"name":                    "ETH/USD [WETH-USDC]",
						"marketToken":             "0x70d95587d40A2caf56bd97485aB3Eec10Bee6336",
						"indexToken":              "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
						"longToken":               "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
						"shortToken":              "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
						"isListed":                true,
						"listingDate":             "2023-08-01T00:00:00.000Z",
						"openInterestLong":        "50000000000000000000000000000000000",
						"openInterestShort":       "45000000000000000000000000000000000",
						"availableLiquidityLong":  "200000000000000000000000000000000000",
						"availableLiquidityShort": "180000000000000000000000000000000000",
						"poolAmountLong":          "100000000000000000000",
						"poolAmountShort":         "300000000000",
						"fundingRateLong":         "34603857548209449337764384000",
						"fundingRateShort":        "-44948298165466366028916229945",
						"borrowingRateLong":       "78699752500621771110414672000",
						"borrowingRateShort":      "0",
						"netRateLong":             "113303610048831220448179056000",
						"netRateShort":            "-44948298165466366028916229945",
					},
					map[string]any{
						"name":                    "BTC/USD [WBTC-USDC]",
						"marketToken":             "0x47c031236e19d024b42f8AE6DA7A02CAe28C4445",
						"indexToken":              "0x47904963fc8b2340414262125aF798B9655E58Cd",
						"longToken":               "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
						"shortToken":              "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
						"isListed":                true,
						"listingDate":             "2023-08-01T00:00:00.000Z",
						"openInterestLong":        "80000000000000000000000000000000000",
						"openInterestShort":       "70000000000000000000000000000000000",
						"availableLiquidityLong":  "400000000000000000000000000000000000",
						"availableLiquidityShort": "350000000000000000000000000000000000",
						"poolAmountLong":          "500000000",
						"poolAmountShort":         "500000000000",
						"fundingRateLong":         "20000000000000000000000000000",
						"fundingRateShort":        "-25000000000000000000000000000",
						"borrowingRateLong":       "50000000000000000000000000000",
						"borrowingRateShort":      "0",
						"netRateLong":             "70000000000000000000000000000",
						"netRateShort":            "-25000000000000000000000000000",
					},
				},
			})

		case strings.HasPrefix(r.URL.Path, "/prices/tickers"):
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"tokenAddress": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
					"tokenSymbol":  "ETH",
					"minPrice":     "207261000000",
					"maxPrice":     "207463000000",
					"updatedAt":    float64(1773331501049),
					"timestamp":    float64(1773331500),
				},
				map[string]any{
					"tokenAddress": "0x47904963fc8b2340414262125aF798B9655E58Cd",
					"tokenSymbol":  "BTC",
					"minPrice":     "8350000000000",
					"maxPrice":     "8355000000000",
					"updatedAt":    float64(1773331501049),
					"timestamp":    float64(1773331500),
				},
			})

		case strings.HasPrefix(r.URL.Path, "/prices/candles"):
			tokenSymbol := r.URL.Query().Get("tokenSymbol")
			if tokenSymbol == "" {
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]any{"error": "tokenSymbol is required"})
				return
			}
			period := r.URL.Query().Get("period")
			if period == "" {
				period = "1h"
			}
			json.NewEncoder(w).Encode(map[string]any{
				"period": period,
				"candles": []any{
					[]any{float64(1773331200), 2072.61, 2074.63, 2069.65, 2074.44},
					[]any{float64(1773327600), 2045.45, 2082.27, 2039.19, 2072.61},
					[]any{float64(1773324000), 2065.68, 2095.18, 2038.45, 2046.35},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"error": "not found"})
		}
	}))
}

func newTestService() *GmxService {
	return &GmxService{
		client: &http.Client{},
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

// setTestBaseURL temporarily overrides the base URL for a chain.
func setTestBaseURL(chain, url string) func() {
	old := chainBaseURLs[chain]
	chainBaseURLs[chain] = url
	return func() { chainBaseURLs[chain] = old }
}

// --- Mock Tests ---

func TestListMarkets(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("arbitrum", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 markets, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "ETH/USD [WETH-USDC]" {
		t.Errorf("name = %q, want %q", got, "ETH/USD [WETH-USDC]")
	}
	if got := first["marketToken"].GetStringValue(); got != "0x70d95587d40A2caf56bd97485aB3Eec10Bee6336" {
		t.Errorf("marketToken = %q", got)
	}
	if got := first["isListed"].GetBoolValue(); !got {
		t.Errorf("isListed = %v, want true", got)
	}
	if got := first["fundingRateLong"].GetStringValue(); got != "34603857548209449337764384000" {
		t.Errorf("fundingRateLong = %q", got)
	}
	if got := first["netRateShort"].GetStringValue(); got != "-44948298165466366028916229945" {
		t.Errorf("netRateShort = %q", got)
	}

	second := items[1].GetStructValue().GetFields()
	if got := second["name"].GetStringValue(); got != "BTC/USD [WBTC-USDC]" {
		t.Errorf("second market name = %q", got)
	}
}

func TestListMarketsWithChain(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("avalanche", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain": "avalanche",
	}))
	if err != nil {
		t.Fatalf("ListMarkets (avalanche): %v", err)
	}

	markets := resp.GetFields()["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	if len(markets.GetListValue().GetValues()) == 0 {
		t.Fatal("expected at least 1 market")
	}
}

func TestGetTickers(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("arbitrum", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	fields := resp.GetFields()
	tickers := fields["tickers"]
	if tickers == nil {
		t.Fatal("response has no 'tickers' field")
	}
	items := tickers.GetListValue().GetValues()
	if len(items) != 2 {
		t.Fatalf("expected 2 tickers, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["tokenSymbol"].GetStringValue(); got != "ETH" {
		t.Errorf("tokenSymbol = %q, want %q", got, "ETH")
	}
	if got := first["tokenAddress"].GetStringValue(); got != "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1" {
		t.Errorf("tokenAddress = %q", got)
	}
	if got := first["minPrice"].GetStringValue(); got != "207261000000" {
		t.Errorf("minPrice = %q, want %q", got, "207261000000")
	}
	if got := first["maxPrice"].GetStringValue(); got != "207463000000" {
		t.Errorf("maxPrice = %q, want %q", got, "207463000000")
	}
	if got := first["timestamp"].GetNumberValue(); got != 1773331500 {
		t.Errorf("timestamp = %v, want 1773331500", got)
	}
}

func TestGetCandles(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("arbitrum", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"token_symbol": "ETH",
		"period":       "1h",
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["period"].GetStringValue(); got != "1h" {
		t.Errorf("period = %q, want %q", got, "1h")
	}

	candles := fields["candles"]
	if candles == nil {
		t.Fatal("response has no 'candles' field")
	}
	items := candles.GetListValue().GetValues()
	if len(items) != 3 {
		t.Fatalf("expected 3 candles, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["timestamp"].GetNumberValue(); got != 1773331200 {
		t.Errorf("timestamp = %v, want 1773331200", got)
	}
	if got := first["open"].GetNumberValue(); got != 2072.61 {
		t.Errorf("open = %v, want 2072.61", got)
	}
	if got := first["high"].GetNumberValue(); got != 2074.63 {
		t.Errorf("high = %v, want 2074.63", got)
	}
	if got := first["low"].GetNumberValue(); got != 2069.65 {
		t.Errorf("low = %v, want 2069.65", got)
	}
	if got := first["close"].GetNumberValue(); got != 2074.44 {
		t.Errorf("close = %v, want 2074.44", got)
	}
}

func TestGetCandlesDefaultPeriod(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("arbitrum", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"token_symbol": "ETH",
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	if got := resp.GetFields()["period"].GetStringValue(); got != "1h" {
		t.Errorf("default period = %q, want %q", got, "1h")
	}
}

func TestGetCandlesRequiresTokenSymbol(t *testing.T) {
	svc := newTestService()

	_, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing token_symbol")
	}
	if !strings.Contains(err.Error(), "token_symbol is required") {
		t.Errorf("error = %q, want to contain 'token_symbol is required'", err.Error())
	}
}

func TestGetCandlesCustomPeriod(t *testing.T) {
	ts := mockGmxServer()
	defer ts.Close()
	restore := setTestBaseURL("arbitrum", ts.URL)
	defer restore()
	svc := newTestService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"token_symbol": "BTC",
		"period":       "4h",
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	if got := resp.GetFields()["period"].GetStringValue(); got != "4h" {
		t.Errorf("period = %q, want %q", got, "4h")
	}
}

func TestDefaultChainIsArbitrum(t *testing.T) {
	if got := resolveBaseURL(""); got != chainBaseURLs["arbitrum"] {
		t.Errorf("empty chain resolved to %q, want arbitrum URL", got)
	}
	if got := resolveBaseURL("unknown"); got != chainBaseURLs["arbitrum"] {
		t.Errorf("unknown chain resolved to %q, want arbitrum URL", got)
	}
	if got := resolveBaseURL("avalanche"); got != chainBaseURLs["avalanche"] {
		t.Errorf("avalanche chain resolved to %q, want avalanche URL", got)
	}
}

// --- Live integration tests (hit the real GMX API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("GMX_RUN_LIVE_TESTS") != "1" {
		t.Skip("set GMX_RUN_LIVE_TESTS=1 to run live integration tests (hits real GMX API)")
	}
}

func liveService() *GmxService {
	return NewGmxService()
}

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	markets := fields["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 market")
	}
	t.Logf("ListMarkets returned %d markets", len(items))

	// Verify first market has expected fields.
	first := items[0].GetStructValue().GetFields()
	if first["name"].GetStringValue() == "" {
		t.Error("first market has no name")
	}
	if first["marketToken"].GetStringValue() == "" {
		t.Error("first market has no marketToken")
	}
	t.Logf("First market: %s", first["name"].GetStringValue())
}

func TestLiveListMarketsAvalanche(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"chain": "avalanche",
	}))
	if err != nil {
		t.Fatalf("ListMarkets (avalanche): %v", err)
	}

	markets := resp.GetFields()["markets"]
	if markets == nil {
		t.Fatal("response has no 'markets' field")
	}
	items := markets.GetListValue().GetValues()
	t.Logf("Avalanche ListMarkets returned %d markets", len(items))
}

func TestLiveGetTickers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	fields := resp.GetFields()
	tickers := fields["tickers"]
	if tickers == nil {
		t.Fatal("response has no 'tickers' field")
	}
	items := tickers.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 ticker")
	}
	t.Logf("GetTickers returned %d tickers", len(items))

	// Verify structure of first ticker.
	first := items[0].GetStructValue().GetFields()
	if first["tokenSymbol"].GetStringValue() == "" {
		t.Error("first ticker has no tokenSymbol")
	}
	if first["minPrice"].GetStringValue() == "" {
		t.Error("first ticker has no minPrice")
	}
	t.Logf("First ticker: %s minPrice=%s",
		first["tokenSymbol"].GetStringValue(),
		first["minPrice"].GetStringValue())
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"token_symbol": "ETH",
		"period":       "1h",
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["period"].GetStringValue(); got != "1h" {
		t.Errorf("period = %q, want %q", got, "1h")
	}

	candles := fields["candles"]
	if candles == nil {
		t.Fatal("response has no 'candles' field")
	}
	items := candles.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 candle")
	}
	t.Logf("GetCandles returned %d candles", len(items))

	// Verify structure of first candle.
	first := items[0].GetStructValue().GetFields()
	if first["timestamp"].GetNumberValue() == 0 {
		t.Error("first candle has no timestamp")
	}
	if first["open"].GetNumberValue() == 0 {
		t.Error("first candle has no open price")
	}
	t.Logf("First candle: ts=%.0f open=%.2f high=%.2f low=%.2f close=%.2f",
		first["timestamp"].GetNumberValue(),
		first["open"].GetNumberValue(),
		first["high"].GetNumberValue(),
		first["low"].GetNumberValue(),
		first["close"].GetNumberValue())
}

func TestLiveGetCandlesBTC(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"token_symbol": "BTC",
		"period":       "4h",
	}))
	if err != nil {
		t.Fatalf("GetCandles (BTC/4h): %v", err)
	}

	candles := resp.GetFields()["candles"]
	if candles == nil {
		t.Fatal("response has no 'candles' field")
	}
	items := candles.GetListValue().GetValues()
	if len(items) == 0 {
		t.Fatal("expected at least 1 candle for BTC")
	}
	t.Logf("BTC 4h candles: %d entries", len(items))
}

// --- helpers ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
