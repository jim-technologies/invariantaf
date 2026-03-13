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
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	fields := resp.GetFields()
	markets := fields["markets"]
	if markets == nil { t.Fatal("response has no 'markets' field") }
	items := markets.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 market") }
	t.Logf("ListMarkets returned %d markets", len(items))
	first := items[0].GetStructValue().GetFields()
	if first["name"].GetStringValue() == "" { t.Error("first market has no name") }
	if first["marketToken"].GetStringValue() == "" { t.Error("first market has no marketToken") }
	t.Logf("First market: %s", first["name"].GetStringValue())
}

func TestLiveListMarketsAvalanche(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{"chain": "avalanche"}))
	if err != nil { t.Fatalf("ListMarkets (avalanche): %v", err) }
	markets := resp.GetFields()["markets"]
	if markets == nil { t.Fatal("response has no 'markets' field") }
	items := markets.GetListValue().GetValues()
	t.Logf("Avalanche ListMarkets returned %d markets", len(items))
}

func TestLiveGetTickers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetTickers: %v", err) }
	fields := resp.GetFields()
	tickers := fields["tickers"]
	if tickers == nil { t.Fatal("response has no 'tickers' field") }
	items := tickers.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 ticker") }
	t.Logf("GetTickers returned %d tickers", len(items))
	first := items[0].GetStructValue().GetFields()
	if first["tokenSymbol"].GetStringValue() == "" { t.Error("first ticker has no tokenSymbol") }
	if first["minPrice"].GetStringValue() == "" { t.Error("first ticker has no minPrice") }
	t.Logf("First ticker: %s minPrice=%s", first["tokenSymbol"].GetStringValue(), first["minPrice"].GetStringValue())
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{"token_symbol": "ETH", "period": "1h"}))
	if err != nil { t.Fatalf("GetCandles: %v", err) }
	fields := resp.GetFields()
	if got := fields["period"].GetStringValue(); got != "1h" { t.Errorf("period = %q, want %q", got, "1h") }
	candles := fields["candles"]
	if candles == nil { t.Fatal("response has no 'candles' field") }
	items := candles.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 candle") }
	t.Logf("GetCandles returned %d candles", len(items))
	first := items[0].GetStructValue().GetFields()
	if first["timestamp"].GetNumberValue() == 0 { t.Error("first candle has no timestamp") }
	if first["open"].GetNumberValue() == 0 { t.Error("first candle has no open price") }
	t.Logf("First candle: ts=%.0f open=%.2f high=%.2f low=%.2f close=%.2f", first["timestamp"].GetNumberValue(), first["open"].GetNumberValue(), first["high"].GetNumberValue(), first["low"].GetNumberValue(), first["close"].GetNumberValue())
}

func TestLiveGetCandlesBTC(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{"token_symbol": "BTC", "period": "4h"}))
	if err != nil { t.Fatalf("GetCandles (BTC/4h): %v", err) }
	candles := resp.GetFields()["candles"]
	if candles == nil { t.Fatal("response has no 'candles' field") }
	items := candles.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 candle for BTC") }
	t.Logf("BTC 4h candles: %d entries", len(items))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
