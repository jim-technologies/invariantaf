package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockNOAAServer creates a test server that returns realistic NOAA API responses.
func mockNOAAServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/gridpoints/") && strings.HasSuffix(r.URL.Path, "/forecast/hourly"):
			json.NewEncoder(w).Encode(map[string]any{
				"properties": map[string]any{
					"periods": []any{
						map[string]any{
							"name":             "This Hour",
							"temperature":      float64(72),
							"temperatureUnit":  "F",
							"windSpeed":        "5 mph",
							"windDirection":    "NW",
							"shortForecast":    "Sunny",
							"detailedForecast": "Sunny with a high near 72.",
							"isDaytime":        true,
							"startTime":        "2024-07-15T14:00:00-05:00",
							"endTime":          "2024-07-15T15:00:00-05:00",
						},
						map[string]any{
							"name":             "Next Hour",
							"temperature":      float64(73),
							"temperatureUnit":  "F",
							"windSpeed":        "6 mph",
							"windDirection":    "NW",
							"shortForecast":    "Sunny",
							"detailedForecast": "Sunny with a high near 73.",
							"isDaytime":        true,
							"startTime":        "2024-07-15T15:00:00-05:00",
							"endTime":          "2024-07-15T16:00:00-05:00",
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/gridpoints/") && strings.HasSuffix(r.URL.Path, "/forecast"):
			json.NewEncoder(w).Encode(map[string]any{
				"properties": map[string]any{
					"periods": []any{
						map[string]any{
							"name":             "Tonight",
							"temperature":      float64(65),
							"temperatureUnit":  "F",
							"windSpeed":        "5 to 10 mph",
							"windDirection":    "NW",
							"shortForecast":    "Partly Cloudy",
							"detailedForecast": "Partly cloudy, with a low around 65.",
							"isDaytime":        false,
							"startTime":        "2024-07-15T18:00:00-05:00",
							"endTime":          "2024-07-16T06:00:00-05:00",
						},
						map[string]any{
							"name":             "Monday",
							"temperature":      float64(88),
							"temperatureUnit":  "F",
							"windSpeed":        "10 to 15 mph",
							"windDirection":    "S",
							"shortForecast":    "Mostly Sunny",
							"detailedForecast": "Mostly sunny, with a high near 88.",
							"isDaytime":        true,
							"startTime":        "2024-07-16T06:00:00-05:00",
							"endTime":          "2024-07-16T18:00:00-05:00",
						},
					},
				},
			})

		case strings.Contains(r.URL.Path, "/stations/") && strings.Contains(r.URL.Path, "/observations/latest"):
			json.NewEncoder(w).Encode(map[string]any{
				"properties": map[string]any{
					"station":         "https://api.weather.gov/stations/KJFK",
					"timestamp":       "2024-07-15T14:53:00+00:00",
					"textDescription": "Fair",
					"temperature": map[string]any{
						"value":    float64(28.3),
						"unitCode": "wmoUnit:degC",
					},
					"windSpeed": map[string]any{
						"value":    float64(18.5),
						"unitCode": "wmoUnit:km_h-1",
					},
					"windDirection": map[string]any{
						"value":    float64(220),
						"unitCode": "wmoUnit:degree_(angle)",
					},
					"barometricPressure": map[string]any{
						"value":    float64(101320),
						"unitCode": "wmoUnit:Pa",
					},
					"relativeHumidity": map[string]any{
						"value":    float64(55.2),
						"unitCode": "wmoUnit:percent",
					},
					"visibility": map[string]any{
						"value":    float64(16090),
						"unitCode": "wmoUnit:m",
					},
				},
			})

		case r.URL.Path == "/alerts/active":
			json.NewEncoder(w).Encode(map[string]any{
				"features": []any{
					map[string]any{
						"properties": map[string]any{
							"id":          "urn:oid:2.49.0.1.840.0.abc123",
							"event":       "Heat Advisory",
							"severity":    "Moderate",
							"urgency":     "Expected",
							"certainty":   "Likely",
							"headline":    "Heat Advisory issued July 15 at 2:00PM EDT",
							"description": "Dangerously hot conditions with heat index values up to 110.",
							"areaDesc":    "New York City",
							"effective":   "2024-07-15T14:00:00-04:00",
							"expires":     "2024-07-16T20:00:00-04:00",
						},
					},
					map[string]any{
						"properties": map[string]any{
							"id":          "urn:oid:2.49.0.1.840.0.def456",
							"event":       "Severe Thunderstorm Watch",
							"severity":    "Severe",
							"urgency":     "Expected",
							"certainty":   "Possible",
							"headline":    "Severe Thunderstorm Watch until 10:00PM EDT",
							"description": "Conditions are favorable for severe thunderstorms.",
							"areaDesc":    "Northern New Jersey; Southern New York",
							"effective":   "2024-07-15T16:00:00-04:00",
							"expires":     "2024-07-15T22:00:00-04:00",
						},
					},
				},
			})

		case r.URL.Path == "/stations" && r.URL.Query().Get("state") != "":
			json.NewEncoder(w).Encode(map[string]any{
				"features": []any{
					map[string]any{
						"properties": map[string]any{
							"stationIdentifier": "KJFK",
							"name":              "New York City, John F. Kennedy International Airport",
						},
						"geometry": map[string]any{
							"coordinates": []any{float64(-73.7781), float64(40.6413)},
						},
					},
					map[string]any{
						"properties": map[string]any{
							"stationIdentifier": "KLGA",
							"name":              "New York City, LaGuardia Airport",
						},
						"geometry": map[string]any{
							"coordinates": []any{float64(-73.8803), float64(40.7769)},
						},
					},
					map[string]any{
						"properties": map[string]any{
							"stationIdentifier": "KNYC",
							"name":              "New York City, Central Park",
						},
						"geometry": map[string]any{
							"coordinates": []any{float64(-73.9654), float64(40.7829)},
						},
					},
				},
			})

		case strings.HasPrefix(r.URL.Path, "/points/"):
			json.NewEncoder(w).Encode(map[string]any{
				"properties": map[string]any{
					"gridId":                  "OKX",
					"gridX":                   float64(33),
					"gridY":                   float64(37),
					"observationStations":     "https://api.weather.gov/gridpoints/OKX/33,37/stations",
					"relativeLocation": map[string]any{
						"properties": map[string]any{
							"city":  "New York",
							"state": "NY",
						},
					},
				},
			})

		case r.URL.Path == "/data":
			// CDO API endpoint
			token := r.Header.Get("token")
			if token == "" {
				w.WriteHeader(http.StatusUnauthorized)
				json.NewEncoder(w).Encode(map[string]any{
					"message": "No token provided",
				})
				return
			}
			json.NewEncoder(w).Encode(map[string]any{
				"results": []any{
					map[string]any{
						"date":     "2024-07-14T00:00:00",
						"datatype": "TMAX",
						"station":  "GHCND:USW00094728",
						"value":    float64(322),
					},
					map[string]any{
						"date":     "2024-07-14T00:00:00",
						"datatype": "TMIN",
						"station":  "GHCND:USW00094728",
						"value":    float64(228),
					},
					map[string]any{
						"date":     "2024-07-15T00:00:00",
						"datatype": "TMAX",
						"station":  "GHCND:USW00094728",
						"value":    float64(335),
					},
					map[string]any{
						"date":     "2024-07-15T00:00:00",
						"datatype": "TMIN",
						"station":  "GHCND:USW00094728",
						"value":    float64(244),
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error": "not found",
			})
		}
	}))
}

func newTestService(nwsURL, cdoURL string) *NOAAService {
	return &NOAAService{
		nwsBaseURL: nwsURL,
		cdoBaseURL: cdoURL,
		cdoToken:   "test-token",
		client:     &http.Client{},
	}
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

// --- Mock Tests ---

func TestGetForecast(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetForecast(context.Background(), mustStruct(t, map[string]any{
		"office": "TOP",
		"grid_x": float64(31),
		"grid_y": float64(80),
	}))
	if err != nil {
		t.Fatalf("GetForecast: %v", err)
	}

	fields := resp.GetFields()
	props := fields["properties"].GetStructValue().GetFields()
	periods := props["periods"].GetListValue().GetValues()
	if len(periods) != 2 {
		t.Fatalf("expected 2 periods, got %d", len(periods))
	}

	first := periods[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "Tonight" {
		t.Errorf("name = %q, want %q", got, "Tonight")
	}
	if got := first["temperature"].GetNumberValue(); got != 65 {
		t.Errorf("temperature = %v, want 65", got)
	}
	if got := first["temperatureUnit"].GetStringValue(); got != "F" {
		t.Errorf("temperatureUnit = %q, want %q", got, "F")
	}
	if got := first["windSpeed"].GetStringValue(); got != "5 to 10 mph" {
		t.Errorf("windSpeed = %q, want %q", got, "5 to 10 mph")
	}
}

func TestGetForecastRequiresOffice(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetForecast(context.Background(), mustStruct(t, map[string]any{
		"grid_x": float64(31),
		"grid_y": float64(80),
	}))
	if err == nil {
		t.Fatal("expected error for missing office")
	}
	if !strings.Contains(err.Error(), "office is required") {
		t.Errorf("error = %q, want to contain 'office is required'", err.Error())
	}
}

func TestGetForecastByStation(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetForecastByStation(context.Background(), mustStruct(t, map[string]any{
		"station_id": "KJFK",
	}))
	if err != nil {
		t.Fatalf("GetForecastByStation: %v", err)
	}

	fields := resp.GetFields()
	props := fields["properties"].GetStructValue().GetFields()
	if got := props["textDescription"].GetStringValue(); got != "Fair" {
		t.Errorf("textDescription = %q, want %q", got, "Fair")
	}
	temp := props["temperature"].GetStructValue().GetFields()
	if got := temp["value"].GetNumberValue(); got != 28.3 {
		t.Errorf("temperature value = %v, want 28.3", got)
	}
}

func TestGetForecastByStationRequiresStationID(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetForecastByStation(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing station_id")
	}
	if !strings.Contains(err.Error(), "station_id is required") {
		t.Errorf("error = %q, want to contain 'station_id is required'", err.Error())
	}
}

func TestGetHourlyForecast(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetHourlyForecast(context.Background(), mustStruct(t, map[string]any{
		"office": "TOP",
		"grid_x": float64(31),
		"grid_y": float64(80),
	}))
	if err != nil {
		t.Fatalf("GetHourlyForecast: %v", err)
	}

	fields := resp.GetFields()
	props := fields["properties"].GetStructValue().GetFields()
	periods := props["periods"].GetListValue().GetValues()
	if len(periods) != 2 {
		t.Fatalf("expected 2 periods, got %d", len(periods))
	}

	first := periods[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "This Hour" {
		t.Errorf("name = %q, want %q", got, "This Hour")
	}
	if got := first["temperature"].GetNumberValue(); got != 72 {
		t.Errorf("temperature = %v, want 72", got)
	}
}

func TestGetHourlyForecastRequiresOffice(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetHourlyForecast(context.Background(), mustStruct(t, map[string]any{
		"grid_x": float64(31),
		"grid_y": float64(80),
	}))
	if err == nil {
		t.Fatal("expected error for missing office")
	}
	if !strings.Contains(err.Error(), "office is required") {
		t.Errorf("error = %q, want to contain 'office is required'", err.Error())
	}
}

func TestGetAlerts(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetAlerts(context.Background(), mustStruct(t, map[string]any{
		"state": "NY",
	}))
	if err != nil {
		t.Fatalf("GetAlerts: %v", err)
	}

	fields := resp.GetFields()
	features := fields["features"].GetListValue().GetValues()
	if len(features) != 2 {
		t.Fatalf("expected 2 alerts, got %d", len(features))
	}

	first := features[0].GetStructValue().GetFields()
	props := first["properties"].GetStructValue().GetFields()
	if got := props["event"].GetStringValue(); got != "Heat Advisory" {
		t.Errorf("event = %q, want %q", got, "Heat Advisory")
	}
	if got := props["severity"].GetStringValue(); got != "Moderate" {
		t.Errorf("severity = %q, want %q", got, "Moderate")
	}
	if got := props["headline"].GetStringValue(); !strings.Contains(got, "Heat Advisory") {
		t.Errorf("headline = %q, want to contain 'Heat Advisory'", got)
	}
}

func TestGetAlertsRequiresState(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetAlerts(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing state")
	}
	if !strings.Contains(err.Error(), "state is required") {
		t.Errorf("error = %q, want to contain 'state is required'", err.Error())
	}
}

func TestGetStations(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetStations(context.Background(), mustStruct(t, map[string]any{
		"state": "NY",
	}))
	if err != nil {
		t.Fatalf("GetStations: %v", err)
	}

	fields := resp.GetFields()
	features := fields["features"].GetListValue().GetValues()
	if len(features) != 3 {
		t.Fatalf("expected 3 stations, got %d", len(features))
	}

	first := features[0].GetStructValue().GetFields()
	props := first["properties"].GetStructValue().GetFields()
	if got := props["stationIdentifier"].GetStringValue(); got != "KJFK" {
		t.Errorf("stationIdentifier = %q, want %q", got, "KJFK")
	}
	if got := props["name"].GetStringValue(); !strings.Contains(got, "Kennedy") {
		t.Errorf("name = %q, want to contain 'Kennedy'", got)
	}
}

func TestGetStationsRequiresState(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetStations(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing state")
	}
	if !strings.Contains(err.Error(), "state is required") {
		t.Errorf("error = %q, want to contain 'state is required'", err.Error())
	}
}

func TestGetStationsWithLimit(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetStations(context.Background(), mustStruct(t, map[string]any{
		"state": "NY",
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetStations: %v", err)
	}

	fields := resp.GetFields()
	features := fields["features"].GetListValue().GetValues()
	if len(features) == 0 {
		t.Fatal("expected at least 1 station")
	}
}

func TestGetPointInfo(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetPointInfo(context.Background(), mustStruct(t, map[string]any{
		"lat": float64(40.7128),
		"lon": float64(-74.0060),
	}))
	if err != nil {
		t.Fatalf("GetPointInfo: %v", err)
	}

	fields := resp.GetFields()
	props := fields["properties"].GetStructValue().GetFields()
	if got := props["gridId"].GetStringValue(); got != "OKX" {
		t.Errorf("gridId = %q, want %q", got, "OKX")
	}
	if got := props["gridX"].GetNumberValue(); got != 33 {
		t.Errorf("gridX = %v, want 33", got)
	}
	if got := props["gridY"].GetNumberValue(); got != 37 {
		t.Errorf("gridY = %v, want 37", got)
	}
}

func TestGetPointInfoRequiresCoordinates(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetPointInfo(context.Background(), mustStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing lat/lon")
	}
	if !strings.Contains(err.Error(), "lat and lon are required") {
		t.Errorf("error = %q, want to contain 'lat and lon are required'", err.Error())
	}
}

func TestGetClimateData(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	resp, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{
		"station":    "GHCND:USW00094728",
		"start_date": "2024-07-14",
		"end_date":   "2024-07-15",
	}))
	if err != nil {
		t.Fatalf("GetClimateData: %v", err)
	}

	fields := resp.GetFields()
	results := fields["results"].GetListValue().GetValues()
	if len(results) != 4 {
		t.Fatalf("expected 4 observations, got %d", len(results))
	}

	first := results[0].GetStructValue().GetFields()
	if got := first["datatype"].GetStringValue(); got != "TMAX" {
		t.Errorf("datatype = %q, want %q", got, "TMAX")
	}
	if got := first["value"].GetNumberValue(); got != 322 {
		t.Errorf("value = %v, want 322", got)
	}
	if got := first["station"].GetStringValue(); got != "GHCND:USW00094728" {
		t.Errorf("station = %q, want %q", got, "GHCND:USW00094728")
	}
}

func TestGetClimateDataRequiresStation(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{
		"start_date": "2024-07-14",
		"end_date":   "2024-07-15",
	}))
	if err == nil {
		t.Fatal("expected error for missing station")
	}
	if !strings.Contains(err.Error(), "station is required") {
		t.Errorf("error = %q, want to contain 'station is required'", err.Error())
	}
}

func TestGetClimateDataRequiresStartDate(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{
		"station":  "GHCND:USW00094728",
		"end_date": "2024-07-15",
	}))
	if err == nil {
		t.Fatal("expected error for missing start_date")
	}
	if !strings.Contains(err.Error(), "start_date is required") {
		t.Errorf("error = %q, want to contain 'start_date is required'", err.Error())
	}
}

func TestGetClimateDataRequiresEndDate(t *testing.T) {
	ts := mockNOAAServer()
	defer ts.Close()
	svc := newTestService(ts.URL, ts.URL)

	_, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{
		"station":    "GHCND:USW00094728",
		"start_date": "2024-07-14",
	}))
	if err == nil {
		t.Fatal("expected error for missing end_date")
	}
	if !strings.Contains(err.Error(), "end_date is required") {
		t.Errorf("error = %q, want to contain 'end_date is required'", err.Error())
	}
}

// --- Live integration tests (hit the real NOAA API) ---

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

	resp, err := svc.GetPointInfo(context.Background(), mustStruct(t, map[string]any{
		"lat": float64(40.7128),
		"lon": float64(-74.0060),
	}))
	if err != nil {
		t.Fatalf("GetPointInfo: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetPointInfo")
	}
	t.Logf("GetPointInfo response keys: %v", keysOf(fields))
}

func TestLiveGetStations(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetStations(context.Background(), mustStruct(t, map[string]any{
		"state": "NY",
		"limit": float64(3),
	}))
	if err != nil {
		t.Fatalf("GetStations: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetStations")
	}
	t.Logf("GetStations response keys: %v", keysOf(fields))
}

func TestLiveGetAlerts(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetAlerts(context.Background(), mustStruct(t, map[string]any{
		"state": "NY",
	}))
	if err != nil {
		t.Fatalf("GetAlerts: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetAlerts")
	}
	t.Logf("GetAlerts response keys: %v", keysOf(fields))
}

func TestLiveGetForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	// Use NYC coordinates: OKX office, grid 33,37
	resp, err := svc.GetForecast(context.Background(), mustStruct(t, map[string]any{
		"office": "OKX",
		"grid_x": float64(33),
		"grid_y": float64(37),
	}))
	if err != nil {
		t.Fatalf("GetForecast: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetForecast")
	}
	t.Logf("GetForecast response keys: %v", keysOf(fields))
}

func TestLiveGetHourlyForecast(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetHourlyForecast(context.Background(), mustStruct(t, map[string]any{
		"office": "OKX",
		"grid_x": float64(33),
		"grid_y": float64(37),
	}))
	if err != nil {
		t.Fatalf("GetHourlyForecast: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetHourlyForecast")
	}
	t.Logf("GetHourlyForecast response keys: %v", keysOf(fields))
}

func TestLiveGetForecastByStation(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()

	resp, err := svc.GetForecastByStation(context.Background(), mustStruct(t, map[string]any{
		"station_id": "KJFK",
	}))
	if err != nil {
		t.Fatalf("GetForecastByStation: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetForecastByStation")
	}
	t.Logf("GetForecastByStation response keys: %v", keysOf(fields))
}

func TestLiveGetClimateData(t *testing.T) {
	skipUnlessLive(t)
	if os.Getenv("NOAA_API_TOKEN") == "" {
		t.Skip("NOAA_API_TOKEN not set, skipping CDO live test")
	}
	svc := liveService()

	resp, err := svc.GetClimateData(context.Background(), mustStruct(t, map[string]any{
		"station":    "GHCND:USW00094728",
		"start_date": "2024-07-01",
		"end_date":   "2024-07-03",
	}))
	if err != nil {
		t.Fatalf("GetClimateData: %v", err)
	}

	fields := resp.GetFields()
	if len(fields) == 0 {
		t.Fatal("empty response from GetClimateData")
	}
	t.Logf("GetClimateData response keys: %v", keysOf(fields))
}

// --- helpers for live tests ---

func keysOf(fields map[string]*structpb.Value) []string {
	keys := make([]string, 0, len(fields))
	for k := range fields {
		keys = append(keys, k)
	}
	return keys
}
