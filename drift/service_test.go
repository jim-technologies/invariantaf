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
	if os.Getenv("DRIFT_RUN_LIVE_TESTS") == "" {
		t.Skip("set DRIFT_RUN_LIVE_TESTS=1 to run live integration tests (hits real Drift API)")
	}
}

func liveService() *DriftService {
	return NewDriftService()
}

func TestLiveListMarkets(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMarkets(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("ListMarkets: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from ListMarkets") }
	markets := fields["markets"]
	if markets == nil { t.Fatal("response has no 'markets' field") }
	items := markets.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 market") }
	found := false
	for _, item := range items {
		m := item.GetStructValue().GetFields()
		if m["symbol"].GetStringValue() == "SOL-PERP" {
			found = true
			t.Logf("SOL-PERP oraclePrice=%s fundingRate24h=%s", m["oraclePrice"].GetStringValue(), m["fundingRate24h"].GetStringValue())
			break
		}
	}
	if !found { t.Error("SOL-PERP not found in market list") }
	t.Logf("ListMarkets returned %d markets", len(items))
}

func TestLiveGetCandles(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetCandles(context.Background(), mustStruct(t, map[string]any{"symbol": "SOL-PERP", "resolution": "60", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetCandles: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetCandles") }
	t.Logf("GetCandles response keys: %v", keysOf(fields))
	var candles []*structpb.Value
	if records, ok := fields["records"]; ok { candles = records.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok { candles = items.GetListValue().GetValues() }
	if len(candles) == 0 { t.Fatal("expected at least 1 candle") }
	first := candles[0].GetStructValue().GetFields()
	if first["ts"].GetNumberValue() == 0 { t.Error("candle ts should not be 0") }
	t.Logf("First candle: ts=%v fillOpen=%v fillClose=%v quoteVolume=%v", first["ts"].GetNumberValue(), first["fillOpen"].GetNumberValue(), first["fillClose"].GetNumberValue(), first["quoteVolume"].GetNumberValue())
}

func TestLiveGetTrades(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetTrades(context.Background(), mustStruct(t, map[string]any{"symbol": "SOL-PERP", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetTrades: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetTrades") }
	t.Logf("GetTrades response keys: %v", keysOf(fields))
	var trades []*structpb.Value
	if records, ok := fields["records"]; ok { trades = records.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok { trades = items.GetListValue().GetValues() }
	if len(trades) == 0 { t.Fatal("expected at least 1 trade") }
	first := trades[0].GetStructValue().GetFields()
	t.Logf("First trade: ts=%v oraclePrice=%s takerDir=%s", first["ts"].GetNumberValue(), first["oraclePrice"].GetStringValue(), first["takerOrderDirection"].GetStringValue())
}

func TestLiveGetFundingRates(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFundingRates(context.Background(), mustStruct(t, map[string]any{"symbol": "SOL-PERP", "limit": float64(5)}))
	if err != nil { t.Fatalf("GetFundingRates: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFundingRates") }
	t.Logf("GetFundingRates response keys: %v", keysOf(fields))
	var fundingRecords []*structpb.Value
	if recs, ok := fields["records"]; ok { fundingRecords = recs.GetListValue().GetValues()
	} else if items, ok := fields["items"]; ok { fundingRecords = items.GetListValue().GetValues() }
	if len(fundingRecords) == 0 { t.Fatal("expected at least 1 funding rate record") }
	first := fundingRecords[0].GetStructValue().GetFields()
	t.Logf("First funding rate: ts=%v rate=%s rateLong=%s rateShort=%s oracleTwap=%s", first["ts"].GetNumberValue(), first["fundingRate"].GetStringValue(), first["fundingRateLong"].GetStringValue(), first["fundingRateShort"].GetStringValue(), first["oraclePriceTwap"].GetStringValue())
}

func TestLiveGetFundingRateStats(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetFundingRateStats(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil { t.Fatalf("GetFundingRateStats: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetFundingRateStats") }
	markets := fields["markets"]
	if markets == nil { t.Fatal("response has no 'markets' field") }
	items := markets.GetListValue().GetValues()
	if len(items) == 0 { t.Fatal("expected at least 1 market in funding rate stats") }
	found := false
	for _, item := range items {
		m := item.GetStructValue().GetFields()
		if m["symbol"].GetStringValue() == "SOL-PERP" {
			found = true
			rates := m["fundingRates"].GetStructValue().GetFields()
			t.Logf("SOL-PERP funding stats: 24h=%s 7d=%s 30d=%s 1y=%s", rates["24h"].GetStringValue(), rates["7d"].GetStringValue(), rates["30d"].GetStringValue(), rates["1y"].GetStringValue())
			break
		}
	}
	if !found { t.Error("SOL-PERP not found in funding rate stats") }
	t.Logf("GetFundingRateStats returned %d markets", len(items))
}



func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
