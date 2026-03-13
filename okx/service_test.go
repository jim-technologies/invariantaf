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

// mockOKXServer creates a test server that returns realistic OKX API responses.
func mockOKXServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/api/v5/market/tickers"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"instId":    "BTC-USDT",
						"last":      "67500.5",
						"lastSz":    "0.001",
						"askPx":     "67501.0",
						"askSz":     "0.5",
						"bidPx":     "67500.0",
						"bidSz":     "0.3",
						"open24h":   "66000.0",
						"high24h":   "68000.0",
						"low24h":    "65500.0",
						"vol24h":    "12345.67",
						"volCcy24h": "834000000",
						"ts":        "1700000000000",
					},
					map[string]any{
						"instId":    "ETH-USDT",
						"last":      "3500.25",
						"lastSz":    "0.01",
						"askPx":     "3500.50",
						"askSz":     "1.0",
						"bidPx":     "3500.00",
						"bidSz":     "0.8",
						"open24h":   "3400.00",
						"high24h":   "3550.00",
						"low24h":    "3380.00",
						"vol24h":    "98765.43",
						"volCcy24h": "345000000",
						"ts":        "1700000000000",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/market/ticker"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"instId":    "BTC-USDT",
						"last":      "67500.5",
						"lastSz":    "0.001",
						"askPx":     "67501.0",
						"askSz":     "0.5",
						"bidPx":     "67500.0",
						"bidSz":     "0.3",
						"open24h":   "66000.0",
						"high24h":   "68000.0",
						"low24h":    "65500.0",
						"vol24h":    "12345.67",
						"volCcy24h": "834000000",
						"ts":        "1700000000000",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/market/books"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"asks": []any{
							[]any{"67501.0", "0.5", "3", "0"},
							[]any{"67502.0", "1.2", "5", "0"},
						},
						"bids": []any{
							[]any{"67500.0", "0.3", "2", "0"},
							[]any{"67499.0", "0.8", "4", "0"},
						},
						"ts": "1700000000000",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/market/candles"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					[]any{"1700000000000", "67000.0", "67500.0", "66800.0", "67200.0", "100.5", "6750000"},
					[]any{"1699996400000", "66800.0", "67100.0", "66500.0", "67000.0", "95.2", "6380000"},
					[]any{"1699992800000", "66500.0", "66900.0", "66200.0", "66800.0", "88.3", "5870000"},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/market/trades"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"instId":  "BTC-USDT",
						"tradeId": "123456",
						"px":      "67500.5",
						"sz":      "0.001",
						"side":    "buy",
						"ts":      "1700000000000",
					},
					map[string]any{
						"instId":  "BTC-USDT",
						"tradeId": "123457",
						"px":      "67499.0",
						"sz":      "0.005",
						"side":    "sell",
						"ts":      "1700000001000",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/public/funding-rate"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"instId":          "BTC-USDT-SWAP",
						"instType":        "SWAP",
						"fundingRate":     "0.0001",
						"nextFundingRate": "0.00015",
						"fundingTime":     "1700000000000",
						"nextFundingTime": "1700028800000",
					},
				},
			})

		case strings.Contains(r.URL.Path, "/api/v5/public/instruments"):
			json.NewEncoder(w).Encode(map[string]any{
				"code": "0",
				"msg":  "",
				"data": []any{
					map[string]any{
						"instId":   "BTC-USDT",
						"instType": "SPOT",
						"baseCcy":  "BTC",
						"quoteCcy": "USDT",
						"tickSz":   "0.1",
						"lotSz":    "0.00000001",
						"minSz":    "0.00001",
						"state":    "live",
					},
					map[string]any{
						"instId":   "ETH-USDT",
						"instType": "SPOT",
						"baseCcy":  "ETH",
						"quoteCcy": "USDT",
						"tickSz":   "0.01",
						"lotSz":    "0.000001",
						"minSz":    "0.001",
						"state":    "live",
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"code": "51001",
				"msg":  "instrument not found",
				"data": []any{},
			})
		}
	}))
}

func newTestService(serverURL string) *OKXService {
	return &OKXService{
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

func TestGetTickers(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	tickers := items.GetListValue().GetValues()
	if len(tickers) != 2 {
		t.Fatalf("expected 2 tickers, got %d", len(tickers))
	}

	first := tickers[0].GetStructValue().GetFields()
	if got := first["instId"].GetStringValue(); got != "BTC-USDT" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT")
	}
	if got := first["last"].GetStringValue(); got != "67500.5" {
		t.Errorf("last = %q, want %q", got, "67500.5")
	}
	if got := first["high24h"].GetStringValue(); got != "68000.0" {
		t.Errorf("high24h = %q, want %q", got, "68000.0")
	}

	second := tickers[1].GetStructValue().GetFields()
	if got := second["instId"].GetStringValue(); got != "ETH-USDT" {
		t.Errorf("instId = %q, want %q", got, "ETH-USDT")
	}
}

func TestGetTickersWithInstType(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{
		"inst_type": "SPOT",
	}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	tickers := items.GetListValue().GetValues()
	if len(tickers) == 0 {
		t.Fatal("expected at least 1 ticker")
	}
}

func TestGetTicker(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTicker(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
	}))
	if err != nil {
		t.Fatalf("GetTicker: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["instId"].GetStringValue(); got != "BTC-USDT" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT")
	}
	if got := fields["last"].GetStringValue(); got != "67500.5" {
		t.Errorf("last = %q, want %q", got, "67500.5")
	}
	if got := fields["askPx"].GetStringValue(); got != "67501.0" {
		t.Errorf("askPx = %q, want %q", got, "67501.0")
	}
	if got := fields["bidPx"].GetStringValue(); got != "67500.0" {
		t.Errorf("bidPx = %q, want %q", got, "67500.0")
	}
}

func TestGetTickerRequiresInstID(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTicker(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_id")
	}
	if !strings.Contains(err.Error(), "inst_id is required") {
		t.Errorf("error = %q, want to contain 'inst_id is required'", err.Error())
	}
}

func TestGetOrderbook(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"size":    float64(20),
	}))
	if err != nil {
		t.Fatalf("GetOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["instId"].GetStringValue(); got != "BTC-USDT" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT")
	}

	asks := fields["asks"]
	if asks == nil {
		t.Fatal("response has no 'asks' field")
	}
	askLevels := asks.GetListValue().GetValues()
	if len(askLevels) != 2 {
		t.Fatalf("expected 2 ask levels, got %d", len(askLevels))
	}

	bids := fields["bids"]
	if bids == nil {
		t.Fatal("response has no 'bids' field")
	}
	bidLevels := bids.GetListValue().GetValues()
	if len(bidLevels) != 2 {
		t.Fatalf("expected 2 bid levels, got %d", len(bidLevels))
	}
}

func TestGetOrderbookRequiresInstID(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_id")
	}
	if !strings.Contains(err.Error(), "inst_id is required") {
		t.Errorf("error = %q, want to contain 'inst_id is required'", err.Error())
	}
}

func TestGetCandles(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"bar":     "1H",
		"limit":   float64(100),
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
	if len(candles) != 3 {
		t.Fatalf("expected 3 candles, got %d", len(candles))
	}

	first := candles[0].GetStructValue().GetFields()
	if got := first["ts"].GetStringValue(); got != "1700000000000" {
		t.Errorf("ts = %q, want %q", got, "1700000000000")
	}
	if got := first["open"].GetStringValue(); got != "67000.0" {
		t.Errorf("open = %q, want %q", got, "67000.0")
	}
	if got := first["high"].GetStringValue(); got != "67500.0" {
		t.Errorf("high = %q, want %q", got, "67500.0")
	}
	if got := first["close"].GetStringValue(); got != "67200.0" {
		t.Errorf("close = %q, want %q", got, "67200.0")
	}
}

func TestGetCandlesRequiresInstID(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_id")
	}
	if !strings.Contains(err.Error(), "inst_id is required") {
		t.Errorf("error = %q, want to contain 'inst_id is required'", err.Error())
	}
}

func TestGetTrades(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"limit":   float64(100),
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
	if got := first["instId"].GetStringValue(); got != "BTC-USDT" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT")
	}
	if got := first["px"].GetStringValue(); got != "67500.5" {
		t.Errorf("px = %q, want %q", got, "67500.5")
	}
	if got := first["side"].GetStringValue(); got != "buy" {
		t.Errorf("side = %q, want %q", got, "buy")
	}

	second := trades[1].GetStructValue().GetFields()
	if got := second["side"].GetStringValue(); got != "sell" {
		t.Errorf("side = %q, want %q", got, "sell")
	}
}

func TestGetTradesRequiresInstID(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_id")
	}
	if !strings.Contains(err.Error(), "inst_id is required") {
		t.Errorf("error = %q, want to contain 'inst_id is required'", err.Error())
	}
}

func TestGetFundingRate(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFundingRate(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT-SWAP",
	}))
	if err != nil {
		t.Fatalf("GetFundingRate: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["instId"].GetStringValue(); got != "BTC-USDT-SWAP" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT-SWAP")
	}
	if got := fields["fundingRate"].GetStringValue(); got != "0.0001" {
		t.Errorf("fundingRate = %q, want %q", got, "0.0001")
	}
	if got := fields["nextFundingRate"].GetStringValue(); got != "0.00015" {
		t.Errorf("nextFundingRate = %q, want %q", got, "0.00015")
	}
	if got := fields["instType"].GetStringValue(); got != "SWAP" {
		t.Errorf("instType = %q, want %q", got, "SWAP")
	}
}

func TestGetFundingRateRequiresInstID(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetFundingRate(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_id")
	}
	if !strings.Contains(err.Error(), "inst_id is required") {
		t.Errorf("error = %q, want to contain 'inst_id is required'", err.Error())
	}
}

func TestGetInstruments(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetInstruments(context.Background(), mustStruct(t, map[string]any{
		"inst_type": "SPOT",
	}))
	if err != nil {
		t.Fatalf("GetInstruments: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	instruments := items.GetListValue().GetValues()
	if len(instruments) != 2 {
		t.Fatalf("expected 2 instruments, got %d", len(instruments))
	}

	first := instruments[0].GetStructValue().GetFields()
	if got := first["instId"].GetStringValue(); got != "BTC-USDT" {
		t.Errorf("instId = %q, want %q", got, "BTC-USDT")
	}
	if got := first["instType"].GetStringValue(); got != "SPOT" {
		t.Errorf("instType = %q, want %q", got, "SPOT")
	}
	if got := first["baseCcy"].GetStringValue(); got != "BTC" {
		t.Errorf("baseCcy = %q, want %q", got, "BTC")
	}
	if got := first["quoteCcy"].GetStringValue(); got != "USDT" {
		t.Errorf("quoteCcy = %q, want %q", got, "USDT")
	}
	if got := first["state"].GetStringValue(); got != "live" {
		t.Errorf("state = %q, want %q", got, "live")
	}
}

func TestGetInstrumentsRequiresInstType(t *testing.T) {
	ts := mockOKXServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetInstruments(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing inst_type")
	}
	if !strings.Contains(err.Error(), "inst_type is required") {
		t.Errorf("error = %q, want to contain 'inst_type is required'", err.Error())
	}
}

func TestOKXAPIError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"code": "51001",
			"msg":  "Instrument ID does not exist",
			"data": []any{},
		})
	}))
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTicker(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "INVALID-PAIR",
	}))
	if err == nil {
		t.Fatal("expected error for invalid instrument")
	}
	if !strings.Contains(err.Error(), "51001") {
		t.Errorf("error = %q, want to contain '51001'", err.Error())
	}
}

// --- Live integration tests (hit the real OKX API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("OKX_RUN_LIVE_TESTS") == "" {
		t.Skip("set OKX_RUN_LIVE_TESTS=1 to run live integration tests (hits real OKX API)")
	}
}

func liveService() *OKXService {
	return NewOKXService()
}

func TestLiveGetTickers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTickers")
	}
	t.Logf("GetTickers response keys: %v", keysOf(fields))
}

func TestLiveGetTicker(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTicker(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
	}))
	if err != nil {
		t.Fatalf("GetTicker: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTicker")
	}
	t.Logf("GetTicker response keys: %v", keysOf(fields))
}

func TestLiveGetOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"size":    float64(5),
	}))
	if err != nil {
		t.Fatalf("GetOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetOrderbook")
	}
	t.Logf("GetOrderbook response keys: %v", keysOf(fields))
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"bar":     "1H",
		"limit":   float64(5),
	}))
	if err != nil {
		t.Fatalf("GetCandles: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetCandles")
	}
	t.Logf("GetCandles response keys: %v", keysOf(fields))
}

func TestLiveGetTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT",
		"limit":   float64(5),
	}))
	if err != nil {
		t.Fatalf("GetTrades: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetTrades")
	}
	t.Logf("GetTrades response keys: %v", keysOf(fields))
}

func TestLiveGetFundingRate(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFundingRate(context.Background(), mustStruct(t, map[string]any{
		"inst_id": "BTC-USDT-SWAP",
	}))
	if err != nil {
		t.Fatalf("GetFundingRate: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetFundingRate")
	}
	t.Logf("GetFundingRate response keys: %v", keysOf(fields))
}

func TestLiveGetInstruments(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetInstruments(context.Background(), mustStruct(t, map[string]any{
		"inst_type": "SPOT",
	}))
	if err != nil {
		t.Fatalf("GetInstruments: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetInstruments")
	}
	t.Logf("GetInstruments response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
