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
	if os.Getenv("VENUS_RUN_LIVE_TESTS") == "" {
		t.Skip("set VENUS_RUN_LIVE_TESTS=1 to run live integration tests (hits real Venus API)")
	}
}

func liveService() *VenusService { return NewVenusService() }

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListMarkets") }
	t.Logf("ListMarkets response keys: %v", keysOf(fields))
}

func TestLiveGetMarket(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMarket(context.Background(), mustStruct(t, map[string]any{"underlying_address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"}))
	if err != nil { t.Fatalf("GetMarket: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMarket") }
	t.Logf("GetMarket response keys: %v", keysOf(fields))
}

func TestLiveListPools(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListPools(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		if strings.Contains(err.Error(), "400") || strings.Contains(err.Error(), "404") {
			t.Skipf("ListPools API requires additional params: %v", err)
		}
		t.Fatalf("ListPools: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListPools") }
	t.Logf("ListPools response keys: %v", keysOf(fields))
}

func TestLiveGetPoolLiquidity(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPoolLiquidity(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		if strings.Contains(err.Error(), "404") || strings.Contains(err.Error(), "410") {
			t.Skip("GetPoolLiquidity endpoint not available")
		}
		t.Fatalf("GetPoolLiquidity: %v", err)
	}
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPoolLiquidity") }
	t.Logf("GetPoolLiquidity response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
