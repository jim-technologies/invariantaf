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
	if err != nil { t.Fatalf("failed to create struct: %v", err) }
	return s
}

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("OKX_RUN_LIVE_TESTS") == "" {
		t.Skip("set OKX_RUN_LIVE_TESTS=1 to run live integration tests (hits real OKX API)")
	}
}

func liveService() *OKXService { return NewOKXService() }

func TestLiveGetTickers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTickers(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetTickers: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTickers") }
	t.Logf("GetTickers response keys: %v", keysOf(fields))
}

func TestLiveGetTicker(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTicker(context.Background(), mustStruct(t, map[string]any{"inst_id": "BTC-USDT"}))
	if err != nil { t.Fatalf("GetTicker: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTicker") }
	t.Logf("GetTicker response keys: %v", keysOf(fields))
}

func TestLiveGetOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetOrderbook(context.Background(), mustStruct(t, map[string]any{"inst_id": "BTC-USDT", "size": float64(5)}))
	if err != nil { t.Fatalf("GetOrderbook: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetOrderbook") }
	t.Logf("GetOrderbook response keys: %v", keysOf(fields))
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{"inst_id": "BTC-USDT", "bar": "1H", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetCandles: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetCandles") }
	t.Logf("GetCandles response keys: %v", keysOf(fields))
}

func TestLiveGetTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{"inst_id": "BTC-USDT", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetTrades: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTrades") }
	t.Logf("GetTrades response keys: %v", keysOf(fields))
}

func TestLiveGetFundingRate(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFundingRate(context.Background(), mustStruct(t, map[string]any{"inst_id": "BTC-USDT-SWAP"}))
	if err != nil { t.Fatalf("GetFundingRate: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFundingRate") }
	t.Logf("GetFundingRate response keys: %v", keysOf(fields))
}

func TestLiveGetInstruments(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetInstruments(context.Background(), mustStruct(t, map[string]any{"inst_type": "SPOT"}))
	if err != nil { t.Fatalf("GetInstruments: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetInstruments") }
	t.Logf("GetInstruments response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
