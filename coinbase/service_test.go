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
	if os.Getenv("COINBASE_RUN_LIVE_TESTS") == "" {
		t.Skip("set COINBASE_RUN_LIVE_TESTS=1 to run live integration tests (hits real Coinbase API)")
	}
}

func liveService() *CoinbaseService {
	return NewCoinbaseService()
}

func TestLiveListProducts(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListProducts(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListProducts: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListProducts") }
	t.Logf("ListProducts response keys: %v", keysOf(fields))
}

func TestLiveGetProduct(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProduct(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD"}))
	if err != nil { t.Fatalf("GetProduct: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProduct") }
	t.Logf("GetProduct response keys: %v", keysOf(fields))
}

func TestLiveGetProductTicker(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProductTicker(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD"}))
	if err != nil { t.Fatalf("GetProductTicker: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProductTicker") }
	t.Logf("GetProductTicker response keys: %v", keysOf(fields))
}

func TestLiveGetProductOrderbook(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProductOrderbook(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD"}))
	if err != nil { t.Fatalf("GetProductOrderbook: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProductOrderbook") }
	t.Logf("GetProductOrderbook response keys: %v", keysOf(fields))
}

func TestLiveGetProductCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProductCandles(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD", "granularity": float64(3600)}))
	if err != nil { t.Fatalf("GetProductCandles: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProductCandles") }
	t.Logf("GetProductCandles response keys: %v", keysOf(fields))
}

func TestLiveGetProductTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProductTrades(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD", "limit": float64(10)}))
	if err != nil { t.Fatalf("GetProductTrades: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProductTrades") }
	t.Logf("GetProductTrades response keys: %v", keysOf(fields))
}

func TestLiveGetProductStats(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetProductStats(context.Background(), mustStruct(t, map[string]any{"product_id": "BTC-USD"}))
	if err != nil { t.Fatalf("GetProductStats: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetProductStats") }
	t.Logf("GetProductStats response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
