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
	if os.Getenv("CRYPTODOTCOM_RUN_LIVE_TESTS") == "" {
		t.Skip("set CRYPTODOTCOM_RUN_LIVE_TESTS=1 to run live integration tests (hits real Crypto.com API)")
	}
}

func liveService() *CryptoDotComService {
	return NewCryptoDotComService()
}

// TestSmoke verifies the service can be instantiated.
func TestSmoke(t *testing.T) {
	svc := NewCryptoDotComService()
	if svc == nil {
		t.Fatal("NewCryptoDotComService returned nil")
	}
	if svc.baseURL == "" {
		t.Fatal("baseURL is empty")
	}
}

func TestLiveGetInstruments(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetInstruments(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetInstruments: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetInstruments")
	}
	first := data[0].GetStructValue().GetFields()
	t.Logf("GetInstruments: first instrument=%s base=%s quote=%s",
		first["instrument_name"].GetStringValue(),
		first["base_currency"].GetStringValue(),
		first["quote_currency"].GetStringValue())
}

func TestLiveGetTickers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "BTC_USDT",
	}))
	if err != nil {
		t.Fatalf("GetTickers: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetTickers")
	}
	first := data[0].GetStructValue().GetFields()
	t.Logf("GetTickers: instrument=%s latest_trade=%s volume=%s",
		first["instrument_name"].GetStringValue(),
		first["latest_trade"].GetStringValue(),
		first["volume"].GetStringValue())
}

func TestLiveGetOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "BTC_USDT",
		"depth":           float64(5),
	}))
	if err != nil {
		t.Fatalf("GetOrderbook: %v", err)
	}

	fields := resp.GetFields()
	book := fields["data"].GetStructValue().GetFields()
	bids := book["bids"].GetListValue().GetValues()
	asks := book["asks"].GetListValue().GetValues()
	t.Logf("GetOrderbook: %d bids, %d asks", len(bids), len(asks))
	if len(bids) == 0 {
		t.Fatal("no bids in orderbook")
	}
	if len(asks) == 0 {
		t.Fatal("no asks in orderbook")
	}
}

func TestLiveGetCandlestick(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCandlestick(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "BTC_USDT",
		"timeframe":       "1D",
	}))
	if err != nil {
		t.Fatalf("GetCandlestick: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetCandlestick")
	}
	first := data[0].GetStructValue().GetFields()
	t.Logf("GetCandlestick: open=%s high=%s low=%s close=%s volume=%s",
		first["open"].GetStringValue(),
		first["high"].GetStringValue(),
		first["low"].GetStringValue(),
		first["close"].GetStringValue(),
		first["volume"].GetStringValue())
}

func TestLiveGetTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{
		"instrument_name": "BTC_USDT",
	}))
	if err != nil {
		t.Fatalf("GetTrades: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetTrades")
	}
	first := data[0].GetStructValue().GetFields()
	t.Logf("GetTrades: trade_id=%s side=%s price=%s quantity=%s",
		first["trade_id"].GetStringValue(),
		first["side"].GetStringValue(),
		first["price"].GetStringValue(),
		first["quantity"].GetStringValue())
}
