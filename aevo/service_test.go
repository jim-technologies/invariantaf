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

// mockAevoServer creates a test server that returns realistic Aevo API responses.
func mockAevoServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/assets":
			json.NewEncoder(w).Encode([]string{
				"ETH", "BTC", "SOL", "ARB", "OP", "DOGE",
			})

		case r.URL.Path == "/markets":
			json.NewEncoder(w).Encode([]any{
				map[string]any{
					"instrument_id":     "1",
					"instrument_name":   "ETH-PERP",
					"instrument_type":   "PERPETUAL",
					"underlying_asset":  "ETH",
					"quote_asset":       "USDC",
					"price_step":        "0.01",
					"amount_step":       "0.01",
					"min_order_value":   "10",
					"max_order_value":   "1000000",
					"max_notional_value": "5000000",
					"mark_price":        "2073.53",
					"index_price":       "2075.43",
					"is_active":         true,
					"max_leverage":      "20",
				},
				map[string]any{
					"instrument_id":     "2",
					"instrument_name":   "BTC-PERP",
					"instrument_type":   "PERPETUAL",
					"underlying_asset":  "BTC",
					"quote_asset":       "USDC",
					"price_step":        "0.1",
					"amount_step":       "0.001",
					"min_order_value":   "10",
					"max_order_value":   "5000000",
					"max_notional_value": "10000000",
					"mark_price":        "43250.50",
					"index_price":       "43260.00",
					"is_active":         true,
					"max_leverage":      "50",
				},
			})

		case r.URL.Path == "/orderbook":
			json.NewEncoder(w).Encode(map[string]any{
				"type":            "snapshot",
				"instrument_id":   "1",
				"instrument_name": "ETH-PERP",
				"instrument_type": "PERPETUAL",
				"bids": []any{
					[]any{"2073.53", "1.21"},
					[]any{"2073.42", "1.21"},
					[]any{"2073.00", "5.50"},
				},
				"asks": []any{
					[]any{"2073.60", "2.15"},
					[]any{"2073.61", "1.21"},
					[]any{"2074.00", "3.00"},
				},
				"last_updated": "1773331511399046895",
				"checksum":     "abc123",
			})

		case r.URL.Path == "/funding":
			json.NewEncoder(w).Encode(map[string]any{
				"funding_rate": "-0.000002",
				"next_epoch":   "1773334800000000000",
			})

		case r.URL.Path == "/funding-history":
			json.NewEncoder(w).Encode(map[string]any{
				"funding_history": []any{
					[]any{"ETH-PERP", "1773331200000000000", "-0.000002", "2072.438615"},
					[]any{"ETH-PERP", "1773327600000000000", "-0.000003", "2045.596793"},
					[]any{"ETH-PERP", "1773324000000000000", "0.000001", "2050.123456"},
				},
			})

		case r.URL.Path == "/index":
			json.NewEncoder(w).Encode(map[string]any{
				"timestamp": "1773331511399046895",
				"price":     "2075.432636",
			})

		case r.URL.Path == "/statistics":
			json.NewEncoder(w).Encode(map[string]any{
				"asset":                 "ETH",
				"open_interest":         map[string]any{"total": "15000000.50"},
				"index_price":           "2073.337311",
				"index_daily_change":    "21.155894",
				"mark_price":            "2073.53",
				"mark_price_24h_ago":    "2052.38",
				"mark_daily_change":     "21.15",
				"funding_daily_avg":     "-0.000002",
				"daily_buy_volume":      "5000000.00",
				"daily_sell_volume":     "4800000.00",
				"daily_volume":          "9800000.00",
				"daily_volume_contracts": "4730.50",
				"total_volume":          "1500000000.00",
			})

		case strings.Contains(r.URL.Path, "/trade-history"):
			json.NewEncoder(w).Encode(map[string]any{
				"count": "3",
				"trade_history": []any{
					map[string]any{
						"trade_id":          "Ei8ktaf6HMa9FaSXDEPCdyE8Gk14RmhhipEvwuzrUA15",
						"instrument_id":     "1",
						"instrument_name":   "ETH-PERP",
						"instrument_type":   "PERPETUAL",
						"amount":            "0.79",
						"side":              "buy",
						"created_timestamp": "1773327142834917917",
						"price":             "2043.01",
					},
					map[string]any{
						"trade_id":          "DLPcNXchaa31yXekCYgjC3HM59eZj1uiNYP7uqtYWKQT",
						"instrument_id":     "1",
						"instrument_name":   "ETH-PERP",
						"instrument_type":   "PERPETUAL",
						"amount":            "1.23",
						"side":              "sell",
						"created_timestamp": "1773326521801605603",
						"price":             "2038.01",
					},
					map[string]any{
						"trade_id":          "abc123def456",
						"instrument_id":     "1",
						"instrument_name":   "ETH-PERP",
						"instrument_type":   "PERPETUAL",
						"amount":            "2.50",
						"side":              "buy",
						"created_timestamp": "1773325000000000000",
						"price":             "2040.00",
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

func newTestService(serverURL string) *AevoService {
	return &AevoService{
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

func TestListAssets(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListAssets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListAssets: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	assets := items.GetListValue().GetValues()
	if len(assets) != 6 {
		t.Fatalf("expected 6 assets, got %d", len(assets))
	}
	if got := assets[0].GetStringValue(); got != "ETH" {
		t.Errorf("first asset = %q, want %q", got, "ETH")
	}
	if got := assets[1].GetStringValue(); got != "BTC" {
		t.Errorf("second asset = %q, want %q", got, "BTC")
	}
}

func TestListMarkets(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	markets := items.GetListValue().GetValues()
	if len(markets) != 2 {
		t.Fatalf("expected 2 markets, got %d", len(markets))
	}

	first := markets[0].GetStructValue().GetFields()
	if got := first["instrument_name"].GetStringValue(); got != "ETH-PERP" {
		t.Errorf("instrument_name = %q, want %q", got, "ETH-PERP")
	}
	if got := first["instrument_type"].GetStringValue(); got != "PERPETUAL" {
		t.Errorf("instrument_type = %q, want %q", got, "PERPETUAL")
	}
	if got := first["underlying_asset"].GetStringValue(); got != "ETH" {
		t.Errorf("underlying_asset = %q, want %q", got, "ETH")
	}
	if got := first["is_active"].GetBoolValue(); got != true {
		t.Errorf("is_active = %v, want true", got)
	}
	if got := first["mark_price"].GetStringValue(); got != "2073.53" {
		t.Errorf("mark_price = %q, want %q", got, "2073.53")
	}
}

func TestListMarketsWithAssetFilter(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"asset": "ETH",
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	if len(items.GetListValue().GetValues()) == 0 {
		t.Fatal("expected at least 1 market")
	}
}

func TestGetOrderbook(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["instrument_name"].GetStringValue(); got != "ETH-PERP" {
		t.Errorf("instrument_name = %q, want %q", got, "ETH-PERP")
	}
	if got := fields["instrument_type"].GetStringValue(); got != "PERPETUAL" {
		t.Errorf("instrument_type = %q, want %q", got, "PERPETUAL")
	}

	bids := fields["bids"].GetListValue().GetValues()
	if len(bids) != 3 {
		t.Fatalf("expected 3 bids, got %d", len(bids))
	}
	firstBid := bids[0].GetStructValue().GetFields()
	if got := firstBid["price"].GetStringValue(); got != "2073.53" {
		t.Errorf("bid price = %q, want %q", got, "2073.53")
	}
	if got := firstBid["quantity"].GetStringValue(); got != "1.21" {
		t.Errorf("bid quantity = %q, want %q", got, "1.21")
	}

	asks := fields["asks"].GetListValue().GetValues()
	if len(asks) != 3 {
		t.Fatalf("expected 3 asks, got %d", len(asks))
	}
	firstAsk := asks[0].GetStructValue().GetFields()
	if got := firstAsk["price"].GetStringValue(); got != "2073.60" {
		t.Errorf("ask price = %q, want %q", got, "2073.60")
	}
}

func TestGetOrderbookRequiresInstrumentName(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing instrument_name")
	}
	if !strings.Contains(err.Error(), "instrument_name is required") {
		t.Errorf("error = %q, want to contain 'instrument_name is required'", err.Error())
	}
}

func TestGetFunding(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFunding(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetFunding: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["funding_rate"].GetStringValue(); got != "-0.000002" {
		t.Errorf("funding_rate = %q, want %q", got, "-0.000002")
	}
	if got := fields["next_epoch"].GetStringValue(); got != "1773334800000000000" {
		t.Errorf("next_epoch = %q, want %q", got, "1773334800000000000")
	}
}

func TestGetFundingRequiresInstrumentName(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetFunding(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing instrument_name")
	}
	if !strings.Contains(err.Error(), "instrument_name is required") {
		t.Errorf("error = %q, want to contain 'instrument_name is required'", err.Error())
	}
}

func TestGetFundingHistory(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetFundingHistory(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetFundingHistory: %v", err)
	}

	fields := resp.GetFields()
	history := fields["funding_history"]
	if history == nil {
		t.Fatal("response has no 'funding_history' field")
	}
	records := history.GetListValue().GetValues()
	if len(records) != 3 {
		t.Fatalf("expected 3 records, got %d", len(records))
	}

	first := records[0].GetStructValue().GetFields()
	if got := first["instrument_name"].GetStringValue(); got != "ETH-PERP" {
		t.Errorf("instrument_name = %q, want %q", got, "ETH-PERP")
	}
	if got := first["funding_rate"].GetStringValue(); got != "-0.000002" {
		t.Errorf("funding_rate = %q, want %q", got, "-0.000002")
	}
	if got := first["mark_price"].GetStringValue(); got != "2072.438615" {
		t.Errorf("mark_price = %q, want %q", got, "2072.438615")
	}
	if got := first["timestamp"].GetStringValue(); got != "1773331200000000000" {
		t.Errorf("timestamp = %q, want %q", got, "1773331200000000000")
	}
}

func TestGetFundingHistoryRequiresInstrumentName(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetFundingHistory(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing instrument_name")
	}
}

func TestGetIndex(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetIndex(context.Background(), mustStruct(t, map[string]any{
		"asset": "ETH",
	}))
	if err != nil {
		t.Fatalf("GetIndex: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["price"].GetStringValue(); got != "2075.432636" {
		t.Errorf("price = %q, want %q", got, "2075.432636")
	}
	if got := fields["timestamp"].GetStringValue(); got != "1773331511399046895" {
		t.Errorf("timestamp = %q, want %q", got, "1773331511399046895")
	}
}

func TestGetIndexRequiresAsset(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetIndex(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing asset")
	}
	if !strings.Contains(err.Error(), "asset is required") {
		t.Errorf("error = %q, want to contain 'asset is required'", err.Error())
	}
}

func TestGetStatistics(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetStatistics(context.Background(), mustStruct(t, map[string]any{
		"asset": "ETH",
	}))
	if err != nil {
		t.Fatalf("GetStatistics: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["asset"].GetStringValue(); got != "ETH" {
		t.Errorf("asset = %q, want %q", got, "ETH")
	}
	// open_interest should be flattened from {total: "..."} to the string value.
	if got := fields["open_interest"].GetStringValue(); got != "15000000.50" {
		t.Errorf("open_interest = %q, want %q", got, "15000000.50")
	}
	if got := fields["index_price"].GetStringValue(); got != "2073.337311" {
		t.Errorf("index_price = %q, want %q", got, "2073.337311")
	}
	if got := fields["daily_volume"].GetStringValue(); got != "9800000.00" {
		t.Errorf("daily_volume = %q, want %q", got, "9800000.00")
	}
	if got := fields["funding_daily_avg"].GetStringValue(); got != "-0.000002" {
		t.Errorf("funding_daily_avg = %q, want %q", got, "-0.000002")
	}
	if got := fields["total_volume"].GetStringValue(); got != "1500000000.00" {
		t.Errorf("total_volume = %q, want %q", got, "1500000000.00")
	}
}

func TestGetStatisticsRequiresAsset(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetStatistics(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing asset")
	}
	if !strings.Contains(err.Error(), "asset is required") {
		t.Errorf("error = %q, want to contain 'asset is required'", err.Error())
	}
}

func TestGetTradeHistory(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTradeHistory(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetTradeHistory: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["count"].GetStringValue(); got != "3" {
		t.Errorf("count = %q, want %q", got, "3")
	}

	trades := fields["trade_history"].GetListValue().GetValues()
	if len(trades) != 3 {
		t.Fatalf("expected 3 trades, got %d", len(trades))
	}

	first := trades[0].GetStructValue().GetFields()
	if got := first["instrument_name"].GetStringValue(); got != "ETH-PERP" {
		t.Errorf("instrument_name = %q, want %q", got, "ETH-PERP")
	}
	if got := first["side"].GetStringValue(); got != "buy" {
		t.Errorf("side = %q, want %q", got, "buy")
	}
	if got := first["price"].GetStringValue(); got != "2043.01" {
		t.Errorf("price = %q, want %q", got, "2043.01")
	}
	if got := first["amount"].GetStringValue(); got != "0.79" {
		t.Errorf("amount = %q, want %q", got, "0.79")
	}
}

func TestGetTradeHistoryRequiresInstrumentName(t *testing.T) {
	ts := mockAevoServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetTradeHistory(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing instrument_name")
	}
	if !strings.Contains(err.Error(), "instrument_name is required") {
		t.Errorf("error = %q, want to contain 'instrument_name is required'", err.Error())
	}
}

// --- Live integration tests (hit the real Aevo API) ---

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("AEVO_RUN_LIVE_TESTS") == "" {
		t.Skip("set AEVO_RUN_LIVE_TESTS=1 to run live integration tests (hits real Aevo API)")
	}
}

func liveService() *AevoService {
	return NewAevoService()
}

func TestLiveListAssets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListAssets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("ListAssets: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	assets := items.GetListValue().GetValues()
	if len(assets) == 0 {
		t.Fatal("expected at least 1 asset")
	}
	t.Logf("ListAssets returned %d assets, first: %s", len(assets), assets[0].GetStringValue())
}

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{
		"asset":           "ETH",
		"instrument_type": "PERPETUAL",
	}))
	if err != nil {
		t.Fatalf("ListMarkets: %v", err)
	}

	fields := resp.GetFields()
	items := fields["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	markets := items.GetListValue().GetValues()
	if len(markets) == 0 {
		t.Fatal("expected at least 1 ETH PERPETUAL market")
	}
	first := markets[0].GetStructValue().GetFields()
	t.Logf("First market: %s (type=%s, mark_price=%s)",
		first["instrument_name"].GetStringValue(),
		first["instrument_type"].GetStringValue(),
		first["mark_price"].GetStringValue())
}

func TestLiveGetOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetOrderbook: %v", err)
	}

	fields := resp.GetFields()
	if got := fields["instrument_name"].GetStringValue(); got != "ETH-PERP" {
		t.Errorf("instrument_name = %q, want %q", got, "ETH-PERP")
	}

	bids := fields["bids"].GetListValue().GetValues()
	asks := fields["asks"].GetListValue().GetValues()
	if len(bids) == 0 {
		t.Fatal("expected at least 1 bid")
	}
	if len(asks) == 0 {
		t.Fatal("expected at least 1 ask")
	}
	firstBid := bids[0].GetStructValue().GetFields()
	firstAsk := asks[0].GetStructValue().GetFields()
	t.Logf("Top bid: %s x %s, Top ask: %s x %s",
		firstBid["price"].GetStringValue(), firstBid["quantity"].GetStringValue(),
		firstAsk["price"].GetStringValue(), firstAsk["quantity"].GetStringValue())
}

func TestLiveGetFunding(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFunding(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetFunding: %v", err)
	}

	fields := resp.GetFields()
	if fields["funding_rate"].GetStringValue() == "" {
		t.Fatal("funding_rate is empty")
	}
	if fields["next_epoch"].GetStringValue() == "" {
		t.Fatal("next_epoch is empty")
	}
	t.Logf("Funding rate: %s, next epoch: %s",
		fields["funding_rate"].GetStringValue(),
		fields["next_epoch"].GetStringValue())
}

func TestLiveGetFundingHistory(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFundingHistory(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
		"limit":           float64(5),
	}))
	if err != nil {
		t.Fatalf("GetFundingHistory: %v", err)
	}

	fields := resp.GetFields()
	history := fields["funding_history"]
	if history == nil {
		t.Fatal("response has no 'funding_history' field")
	}
	records := history.GetListValue().GetValues()
	if len(records) == 0 {
		t.Fatal("expected at least 1 funding record")
	}
	first := records[0].GetStructValue().GetFields()
	t.Logf("First funding record: instrument=%s rate=%s price=%s",
		first["instrument_name"].GetStringValue(),
		first["funding_rate"].GetStringValue(),
		first["mark_price"].GetStringValue())
}

func TestLiveGetIndex(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetIndex(context.Background(), mustStruct(t, map[string]any{
		"asset": "ETH",
	}))
	if err != nil {
		t.Fatalf("GetIndex: %v", err)
	}

	fields := resp.GetFields()
	if fields["price"].GetStringValue() == "" {
		t.Fatal("price is empty")
	}
	t.Logf("ETH index price: %s", fields["price"].GetStringValue())
}

func TestLiveGetStatistics(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetStatistics(context.Background(), mustStruct(t, map[string]any{
		"asset":           "ETH",
		"instrument_type": "PERPETUAL",
	}))
	if err != nil {
		t.Fatalf("GetStatistics: %v", err)
	}

	fields := resp.GetFields()
	if fields["asset"].GetStringValue() != "ETH" {
		t.Errorf("asset = %q, want %q", fields["asset"].GetStringValue(), "ETH")
	}
	if fields["daily_volume"].GetStringValue() == "" {
		t.Fatal("daily_volume is empty")
	}
	t.Logf("ETH stats: OI=%s, volume=%s, funding_avg=%s",
		fields["open_interest"].GetStringValue(),
		fields["daily_volume"].GetStringValue(),
		fields["funding_daily_avg"].GetStringValue())
}

func TestLiveGetTradeHistory(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTradeHistory(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "ETH-PERP",
	}))
	if err != nil {
		t.Fatalf("GetTradeHistory: %v", err)
	}

	fields := resp.GetFields()
	trades := fields["trade_history"].GetListValue().GetValues()
	if len(trades) == 0 {
		t.Fatal("expected at least 1 trade")
	}
	first := trades[0].GetStructValue().GetFields()
	t.Logf("Latest trade: side=%s price=%s amount=%s",
		first["side"].GetStringValue(),
		first["price"].GetStringValue(),
		first["amount"].GetStringValue())
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
