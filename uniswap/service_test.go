package main

import (
	"context"
	"os"
	"strings"
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
	if os.Getenv("UNISWAP_RUN_LIVE_TESTS") == "" {
		t.Skip("set UNISWAP_RUN_LIVE_TESTS=1 to run live integration tests (hits real GeckoTerminal API)")
	}
}

func liveService() *UniswapService { return NewUniswapService() }

func TestLiveListTopPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListTopPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListTopPools: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListTopPools") }
	t.Logf("ListTopPools response keys: %v", keysOf(fields))
}

func TestLiveGetPool(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPool(context.Background(), mustStruct(t, map[string]any{"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"}))
	if err != nil { t.Fatalf("GetPool: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPool") }
	t.Logf("GetPool response keys: %v", keysOf(fields))
}

func TestLiveGetTokenPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTokenPrice(context.Background(), mustStruct(t, map[string]any{"token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"}))
	if err != nil { t.Fatalf("GetTokenPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTokenPrice") }
	t.Logf("GetTokenPrice response keys: %v", keysOf(fields))
}

func TestLiveListTrendingPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListTrendingPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListTrendingPools: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListTrendingPools") }
	t.Logf("ListTrendingPools response keys: %v", keysOf(fields))
}

func TestLiveGetOHLCV(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetOHLCV(context.Background(), mustStruct(t, map[string]any{"pool_address": "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8", "limit": float64(7)}))
	if err != nil {
		if strings.Contains(err.Error(), "429") { t.Skip("GetOHLCV rate limited (429)") }
		t.Fatalf("GetOHLCV: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetOHLCV") }
	t.Logf("GetOHLCV response keys: %v", keysOf(fields))
}

func TestLiveSearchPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.SearchPools(context.Background(), mustStruct(t, map[string]any{"query": "WETH", "network": "eth"}))
	if err != nil {
		if strings.Contains(err.Error(), "429") { t.Skip("SearchPools rate limited (429)") }
		t.Fatalf("SearchPools: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from SearchPools") }
	t.Logf("SearchPools response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
