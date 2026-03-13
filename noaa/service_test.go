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
	if os.Getenv("NOAA_RUN_LIVE_TESTS") == "" {
		t.Skip("set NOAA_RUN_LIVE_TESTS=1 to run live integration tests (hits real NOAA API)")
	}
}

func liveService() *NOAAService {
	return NewNOAAService()
}

func TestLiveGetPointInfo(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetPointInfo(context.Background(), mustStruct(t, map[string]any{"lat": float64(40.7128), "lon": float64(-74.0060)}))
	if err != nil { t.Fatalf("GetPointInfo: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetPointInfo") }
	t.Logf("GetPointInfo response keys: %v", keysOf(fields))
}

func TestLiveGetStations(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetStations(context.Background(), mustStruct(t, map[string]any{"state": "NY", "limit": float64(3)}))
	if err != nil { t.Fatalf("GetStations: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetStations") }
	t.Logf("GetStations response keys: %v", keysOf(fields))
}

func TestLiveGetAlerts(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetAlerts(context.Background(), mustStruct(t, map[string]any{"state": "NY"}))
	if err != nil { t.Fatalf("GetAlerts: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetAlerts") }
	t.Logf("GetAlerts response keys: %v", keysOf(fields))
}

func TestLiveGetForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetForecast(context.Background(), mustStruct(t, map[string]any{"office": "OKX", "grid_x": float64(33), "grid_y": float64(37)}))
	if err != nil { t.Fatalf("GetForecast: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetForecast") }
	t.Logf("GetForecast response keys: %v", keysOf(fields))
}

func TestLiveGetHourlyForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHourlyForecast(context.Background(), mustStruct(t, map[string]any{"office": "OKX", "grid_x": float64(33), "grid_y": float64(37)}))
	if err != nil { t.Fatalf("GetHourlyForecast: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHourlyForecast") }
	t.Logf("GetHourlyForecast response keys: %v", keysOf(fields))
}

func TestLiveGetForecastByStation(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetForecastByStation(context.Background(), mustStruct(t, map[string]any{"station_id": "KJFK"}))
	if err != nil { t.Fatalf("GetForecastByStation: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetForecastByStation") }
	t.Logf("GetForecastByStation response keys: %v", keysOf(fields))
}

func TestLiveGetClimateData(t *testing.T) {
	skipUnlessLive(t)
	if os.Getenv("NOAA_API_TOKEN") == "" {
		t.Skip("NOAA_API_TOKEN not set, skipping CDO live test")
	}
	svc := liveService()
	resp, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{"station": "GHCND:USW00094728", "start_date": "2024-07-01", "end_date": "2024-07-03"}))
	if err != nil { t.Fatalf("GetClimateData: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetClimateData") }
	t.Logf("GetClimateData response keys: %v", keysOf(fields))
}



func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
