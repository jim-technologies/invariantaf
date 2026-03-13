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

// TheOddsApiService implements the TheOddsApiService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns
// a structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type TheOddsApiService struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

// NewTheOddsApiService creates a new service with default settings.
// The API key is read from the ODDS_API_KEY environment variable.
func NewTheOddsApiService() *TheOddsApiService {
	return &TheOddsApiService{
		baseURL: "https://api.the-odds-api.com/v4",
		apiKey:  os.Getenv("ODDS_API_KEY"),
		client:  &http.Client{},
	}
}

// get performs a GET request to The Odds API and returns the decoded JSON.
func (s *TheOddsApiService) get(path string, params url.Values) (map[string]any, error) {
	// Always include the API key.
	if s.apiKey != "" {
		params.Set("apiKey", s.apiKey)
	}

	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")

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
		// The response may be an array (e.g. sports, odds endpoints).
		// Try wrapping in a map.
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

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// ListSports lists all available sports and leagues.
func (s *TheOddsApiService) ListSports(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	params := url.Values{}

	data, err := s.get("/sports", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetOdds gets odds from multiple bookmakers for a given sport.
func (s *TheOddsApiService) GetOdds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	sport := getString(fields, "sport", "")
	if sport == "" {
		return nil, fmt.Errorf("sport is required")
	}

	params := url.Values{}
	params.Set("regions", getString(fields, "regions", "us"))
	params.Set("markets", getString(fields, "markets", "h2h,spreads,totals"))

	path := fmt.Sprintf("/sports/%s/odds", sport)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetScores gets live and recently completed scores for a given sport.
func (s *TheOddsApiService) GetScores(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	sport := getString(fields, "sport", "")
	if sport == "" {
		return nil, fmt.Errorf("sport is required")
	}

	params := url.Values{}
	daysFrom := getInt(fields, "days_from")
	if daysFrom > 0 {
		params.Set("daysFrom", strconv.FormatInt(daysFrom, 10))
	} else {
		params.Set("daysFrom", "1")
	}

	path := fmt.Sprintf("/sports/%s/scores", sport)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetEvents gets upcoming events for a given sport.
func (s *TheOddsApiService) GetEvents(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	sport := getString(fields, "sport", "")
	if sport == "" {
		return nil, fmt.Errorf("sport is required")
	}

	params := url.Values{}

	path := fmt.Sprintf("/sports/%s/events", sport)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetEventOdds gets odds for a specific event from multiple bookmakers.
func (s *TheOddsApiService) GetEventOdds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	sport := getString(fields, "sport", "")
	if sport == "" {
		return nil, fmt.Errorf("sport is required")
	}
	eventID := getString(fields, "event_id", "")
	if eventID == "" {
		return nil, fmt.Errorf("event_id is required")
	}

	params := url.Values{}
	params.Set("regions", getString(fields, "regions", "us"))
	params.Set("markets", getString(fields, "markets", "h2h"))

	path := fmt.Sprintf("/sports/%s/events/%s/odds", sport, eventID)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetHistoricalOdds gets a historical odds snapshot for a given sport and date.
func (s *TheOddsApiService) GetHistoricalOdds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	sport := getString(fields, "sport", "")
	if sport == "" {
		return nil, fmt.Errorf("sport is required")
	}
	date := getString(fields, "date", "")
	if date == "" {
		return nil, fmt.Errorf("date is required")
	}

	params := url.Values{}
	params.Set("date", date)
	params.Set("regions", getString(fields, "regions", "us"))
	params.Set("markets", getString(fields, "markets", "h2h"))

	path := fmt.Sprintf("/sports/%s/odds-history", sport)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
