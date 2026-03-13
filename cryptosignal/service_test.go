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
	if os.Getenv("CRYPTOSIGNAL_RUN_LIVE_TESTS") == "" {
		t.Skip("set CRYPTOSIGNAL_RUN_LIVE_TESTS=1 to run live integration tests (hits real CryptoSignal API)")
	}
}

func liveService() *CryptoSignalService {
	return NewCryptoSignalService()
}

func TestLiveGetFearGreedIndex(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{"limit": float64(5)}))
	if err != nil { t.Fatalf("GetFearGreedIndex: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFearGreedIndex") }
	t.Logf("GetFearGreedIndex response keys: %v", keysOf(fields))
}

func TestLiveGetGlobalMetrics(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetGlobalMetrics(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetGlobalMetrics: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetGlobalMetrics") }
	t.Logf("GetGlobalMetrics response keys: %v", keysOf(fields))
}

func TestLiveGetTrendingCoins(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTrendingCoins(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetTrendingCoins: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTrendingCoins") }
	t.Logf("GetTrendingCoins response keys: %v", keysOf(fields))
}

func TestLiveGetGasPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetGasPrice(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetGasPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetGasPrice") }
	t.Logf("GetGasPrice response keys: %v", keysOf(fields))
}



func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
