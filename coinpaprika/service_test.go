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
	if os.Getenv("COINPAPRIKA_RUN_LIVE_TESTS") == "" {
		t.Skip("set COINPAPRIKA_RUN_LIVE_TESTS=1 to run live integration tests (hits real CoinPaprika API)")
	}
}

func liveService() *CoinpaprikaService { return NewCoinpaprikaService() }

func TestLiveGetGlobal(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetGlobal(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetGlobal: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetGlobal") }
	t.Logf("GetGlobal response keys: %v", keysOf(fields))
}

func TestLiveListCoins(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListCoins(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListCoins: %v", err) }
	fields := resp.GetFields()
	coins := fields["coins"].GetListValue().GetValues()
	if len(coins) == 0 { t.Fatal("expected at least 1 coin") }
	t.Logf("ListCoins returned %d coins", len(coins))
}

func TestLiveGetCoinById(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetCoinById(context.Background(), mustStruct(t, map[string]any{"coin_id": "btc-bitcoin"}))
	if err != nil { t.Fatalf("GetCoinById: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetCoinById") }
	t.Logf("GetCoinById response keys: %v", keysOf(fields))
}

func TestLiveGetTickerById(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTickerById(context.Background(), mustStruct(t, map[string]any{"coin_id": "btc-bitcoin"}))
	if err != nil { t.Fatalf("GetTickerById: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTickerById") }
	t.Logf("GetTickerById response keys: %v", keysOf(fields))
}

func TestLiveSearchCoins(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.SearchCoins(context.Background(), mustStruct(t, map[string]any{"query": "bitcoin"}))
	if err != nil { t.Fatalf("SearchCoins: %v", err) }
	fields := resp.GetFields()
	currencies := fields["currencies"].GetListValue().GetValues()
	if len(currencies) == 0 { t.Fatal("expected at least 1 search result") }
	t.Logf("SearchCoins returned %d results", len(currencies))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
