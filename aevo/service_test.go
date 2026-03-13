package main

import (
	"context"
	"os"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

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
