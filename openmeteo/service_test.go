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
	if os.Getenv("OPENMETEO_RUN_LIVE_TESTS") == "" {
		t.Skip("set OPENMETEO_RUN_LIVE_TESTS=1 to run live integration tests (hits real Open-Meteo API)")
	}
}

func liveService() *OpenMeteoService { return NewOpenMeteoService() }

func TestLiveGetForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetForecast(context.Background(), mustStruct(t, map[string]any{"latitude": float64(52.52), "longitude": float64(13.41)}))
	if err != nil { t.Fatalf("GetForecast: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetForecast") }
	t.Logf("GetForecast response keys: %v", keysOf(fields))
}

func TestLiveGetHistoricalWeather(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetHistoricalWeather(context.Background(), mustStruct(t, map[string]any{"latitude": float64(52.52), "longitude": float64(13.41), "start_date": "2024-01-01", "end_date": "2024-01-03"}))
	if err != nil { t.Fatalf("GetHistoricalWeather: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetHistoricalWeather") }
	t.Logf("GetHistoricalWeather response keys: %v", keysOf(fields))
}

func TestLiveGetMultiModelForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMultiModelForecast(context.Background(), mustStruct(t, map[string]any{"latitude": float64(52.52), "longitude": float64(13.41), "models": []any{"ecmwf_ifs025", "gfs_seamless"}}))
	if err != nil { t.Fatalf("GetMultiModelForecast: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMultiModelForecast") }
	t.Logf("GetMultiModelForecast response keys: %v", keysOf(fields))
}

func TestLiveGetAirQuality(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetAirQuality(context.Background(), mustStruct(t, map[string]any{"latitude": float64(52.52), "longitude": float64(13.41)}))
	if err != nil { t.Fatalf("GetAirQuality: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetAirQuality") }
	t.Logf("GetAirQuality response keys: %v", keysOf(fields))
}

func TestLiveGetMarineWeather(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.GetMarineWeather(context.Background(), mustStruct(t, map[string]any{"latitude": float64(54.32), "longitude": float64(10.13)}))
	if err != nil { t.Fatalf("GetMarineWeather: %v", err) }
	fields := resp.GetFields()
	if len(fields) == 0 { t.Fatal("empty response from GetMarineWeather") }
	t.Logf("GetMarineWeather response keys: %v", keysOf(fields))
}

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields { keys = append(keys, k) }
	return keys
}
