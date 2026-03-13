package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"

	"google.golang.org/protobuf/types/known/structpb"
)

// NOAAService implements the NOAAService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type NOAAService struct {
	nwsBaseURL string
	cdoBaseURL string
	cdoToken   string
	client     *http.Client
}

// NewNOAAService creates a new service with default settings.
// The NWS API requires no authentication. The CDO API requires
// NOAA_API_TOKEN environment variable.
func NewNOAAService() *NOAAService {
	return &NOAAService{
		nwsBaseURL: "https://api.weather.gov",
		cdoBaseURL: "https://www.ncdc.noaa.gov/cdo-web/api/v2",
		cdoToken:   os.Getenv("NOAA_API_TOKEN"),
		client:     &http.Client{},
	}
}

// getNWS performs a GET request to the NWS API and returns the decoded JSON.
func (s *NOAAService) getNWS(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.nwsBaseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "(invariantaf, contact@example.com)")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		var arr []any
		if err2 := json.Unmarshal(body, &arr); err2 == nil {
			result = map[string]any{"items": arr}
		} else {
			return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
		}
	}

	return result, nil
}

// getCDO performs a GET request to the NOAA Climate Data Online API.
func (s *NOAAService) getCDO(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.cdoBaseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("token", s.cdoToken)

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		var arr []any
		if err2 := json.Unmarshal(body, &arr); err2 == nil {
			result = map[string]any{"items": arr}
		} else {
			return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
		}
	}

	return result, nil
}

// helper: get a string field from structpb, with a default.
func getString(fields map[string]*structpb.Value, key, def string) string {
	if v, ok := fields[key]; ok && v.GetStringValue() != "" {
		return v.GetStringValue()
	}
	return def
}

// helper: get an int field from structpb (numbers come as float64).
func getInt(fields map[string]*structpb.Value, key string) int64 {
	if v, ok := fields[key]; ok {
		return int64(v.GetNumberValue())
	}
	return 0
}

// helper: get a float field from structpb.
func getFloat(fields map[string]*structpb.Value, key string) float64 {
	if v, ok := fields[key]; ok {
		return v.GetNumberValue()
	}
	return 0
}

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// GetForecast gets a detailed forecast for a specific NWS grid point.
func (s *NOAAService) GetForecast(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	office := getString(fields, "office", "")
	if office == "" {
		return nil, fmt.Errorf("office is required")
	}
	gridX := getInt(fields, "grid_x")
	gridY := getInt(fields, "grid_y")
	if gridX == 0 && gridY == 0 {
		return nil, fmt.Errorf("grid_x and grid_y are required")
	}

	path := fmt.Sprintf("/gridpoints/%s/%d,%d/forecast", office, gridX, gridY)
	data, err := s.getNWS(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetForecastByStation gets the latest observation from a weather station.
func (s *NOAAService) GetForecastByStation(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	stationID := getString(fields, "station_id", "")
	if stationID == "" {
		return nil, fmt.Errorf("station_id is required")
	}

	path := fmt.Sprintf("/stations/%s/observations/latest", stationID)
	data, err := s.getNWS(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetHourlyForecast gets an hourly forecast for a specific NWS grid point.
func (s *NOAAService) GetHourlyForecast(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	office := getString(fields, "office", "")
	if office == "" {
		return nil, fmt.Errorf("office is required")
	}
	gridX := getInt(fields, "grid_x")
	gridY := getInt(fields, "grid_y")
	if gridX == 0 && gridY == 0 {
		return nil, fmt.Errorf("grid_x and grid_y are required")
	}

	path := fmt.Sprintf("/gridpoints/%s/%d,%d/forecast/hourly", office, gridX, gridY)
	data, err := s.getNWS(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetAlerts gets active weather alerts for a US state.
func (s *NOAAService) GetAlerts(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	state := getString(fields, "state", "")
	if state == "" {
		return nil, fmt.Errorf("state is required")
	}

	params := url.Values{}
	params.Set("area", state)

	data, err := s.getNWS("/alerts/active", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetStations finds weather stations in a US state.
func (s *NOAAService) GetStations(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	state := getString(fields, "state", "")
	if state == "" {
		return nil, fmt.Errorf("state is required")
	}

	params := url.Values{}
	params.Set("state", state)

	limit := getInt(fields, "limit")
	if limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	} else {
		params.Set("limit", "10")
	}

	data, err := s.getNWS("/stations", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPointInfo gets NWS grid point and station info from lat/lon coordinates.
func (s *NOAAService) GetPointInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "lat")
	lon := getFloat(fields, "lon")
	if lat == 0 && lon == 0 {
		return nil, fmt.Errorf("lat and lon are required")
	}

	path := fmt.Sprintf("/points/%.4f,%.4f", lat, lon)
	data, err := s.getNWS(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetClimateData gets historical daily climate observations from NOAA CDO.
func (s *NOAAService) GetClimateData(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	station := getString(fields, "station", "")
	if station == "" {
		return nil, fmt.Errorf("station is required")
	}
	startDate := getString(fields, "start_date", "")
	if startDate == "" {
		return nil, fmt.Errorf("start_date is required")
	}
	endDate := getString(fields, "end_date", "")
	if endDate == "" {
		return nil, fmt.Errorf("end_date is required")
	}

	params := url.Values{}
	params.Set("datasetid", "GHCND")
	params.Set("stationid", station)
	params.Set("startdate", startDate)
	params.Set("enddate", endDate)
	params.Set("datatypeid", "TMAX,TMIN")
	params.Set("limit", "100")

	data, err := s.getCDO("/data", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
