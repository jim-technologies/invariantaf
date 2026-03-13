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
	if os.Getenv("CRYPTOCOMPARE_RUN_LIVE_TESTS") == "" {
		t.Skip("set CRYPTOCOMPARE_RUN_LIVE_TESTS=1 to run live integration tests (hits real CryptoCompare API)")
	}
}

func liveService() *CryptoCompareService {
	return NewCryptoCompareService()
}

func TestLiveGetPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPrice(context.Background(), mustStruct(t, map[string]any{"fsym": "BTC", "tsyms": "USD,EUR"}))
	if err != nil { t.Fatalf("GetPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPrice") }
	t.Logf("GetPrice response keys: %v", keysOf(fields))
}

func TestLiveGetMultiPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMultiPrice(context.Background(), mustStruct(t, map[string]any{"fsyms": "BTC,ETH", "tsyms": "USD"}))
	if err != nil { t.Fatalf("GetMultiPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMultiPrice") }
	t.Logf("GetMultiPrice response keys: %v", keysOf(fields))
}

func TestLiveGetFullPrice(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFullPrice(context.Background(), mustStruct(t, map[string]any{"fsyms": "BTC", "tsyms": "USD"}))
	if err != nil { t.Fatalf("GetFullPrice: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFullPrice") }
	t.Logf("GetFullPrice response keys: %v", keysOf(fields))
}

func TestLiveGetHistoHour(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHistoHour(context.Background(), mustStruct(t, map[string]any{"fsym": "BTC", "tsym": "USD", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetHistoHour: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHistoHour") }
	t.Logf("GetHistoHour response keys: %v", keysOf(fields))
}

func TestLiveGetHistoDay(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHistoDay(context.Background(), mustStruct(t, map[string]any{"fsym": "BTC", "tsym": "USD", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetHistoDay: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHistoDay") }
	t.Logf("GetHistoDay response keys: %v", keysOf(fields))
}

func TestLiveGetTopByVolume(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTopByVolume(context.Background(), mustStruct(t, map[string]any{"tsym": "USD", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetTopByVolume: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTopByVolume") }
	t.Logf("GetTopByVolume response keys: %v", keysOf(fields))
}



func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
