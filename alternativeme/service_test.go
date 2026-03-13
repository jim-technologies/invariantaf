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
	if os.Getenv("ALTERNATIVEME_RUN_LIVE_TESTS") == "" {
		t.Skip("set ALTERNATIVEME_RUN_LIVE_TESTS=1 to run live integration tests (hits real Alternative.me API)")
	}
}

func liveService() *AlternativeMeService {
	return NewAlternativeMeService()
}

func TestLiveGetFearGreedIndex(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetFearGreedIndex(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(1),
	}))
	if err != nil {
		t.Fatalf("GetFearGreedIndex: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetFearGreedIndex")
	}
	first := data[0].GetStructValue().GetFields()
	t.Logf("Fear & Greed value=%s classification=%s",
		first["value"].GetStringValue(),
		first["value_classification"].GetStringValue())
}

func TestLiveGetGlobalMarketData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetGlobalMarketData(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(3),
	}))
	if err != nil {
		t.Fatalf("GetGlobalMarketData: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetGlobalMarketData")
	}
	t.Logf("GetGlobalMarketData returned %d tickers", len(data))
}

func TestLiveGetCoinData(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetCoinData(context.Background(), mustStruct(t, map[string]any{
		"id": "1",
	}))
	if err != nil {
		t.Fatalf("GetCoinData: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetStructValue().GetFields()
	if len(data) == 0 {
		t.Fatal("empty response from GetCoinData")
	}
	t.Logf("GetCoinData: name=%s symbol=%s price=%s",
		data["name"].GetStringValue(),
		data["symbol"].GetStringValue(),
		data["price_usd"].GetStringValue())
}

func TestLiveGetListings(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetListings(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetListings: %v", err)
	}

	fields := resp.GetFields()
	data := fields["data"].GetListValue().GetValues()
	if len(data) == 0 {
		t.Fatal("empty response from GetListings")
	}
	t.Logf("GetListings returned %d listings", len(data))
}


