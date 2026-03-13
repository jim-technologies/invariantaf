package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"

	"google.golang.org/protobuf/types/known/structpb"
)

// DriftService implements the DriftService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type DriftService struct {
	baseURL string
	client  *http.Client
}

// NewDriftService creates a new service with default settings.
// No authentication is required for the Drift public data API.
func NewDriftService() *DriftService {
	return &DriftService{
		baseURL: "https://data.api.drift.trade",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Drift API and returns the decoded JSON
// as a map. If the response is a JSON array, it is wrapped under the key
// "items".
func (s *DriftService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. candles, trades).
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

// ListMarkets lists all markets with live stats.
func (s *DriftService) ListMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/stats/markets", nil)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetCandles gets OHLCV candlestick data for a market.
func (s *DriftService) GetCandles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	symbol := getString(fields, "symbol", "")
	if symbol == "" {
		return nil, fmt.Errorf("symbol is required")
	}
	resolution := getString(fields, "resolution", "")
	if resolution == "" {
		return nil, fmt.Errorf("resolution is required")
	}

	params := url.Values{}
	if startTs := getInt(fields, "start_ts"); startTs > 0 {
		params.Set("startTs", strconv.FormatInt(startTs, 10))
	}
	if endTs := getInt(fields, "end_ts"); endTs > 0 {
		params.Set("endTs", strconv.FormatInt(endTs, 10))
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	path := fmt.Sprintf("/market/%s/candles/%s", url.PathEscape(symbol), url.PathEscape(resolution))
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTrades gets recent trades for a market.
func (s *DriftService) GetTrades(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	symbol := getString(fields, "symbol", "")
	if symbol == "" {
		return nil, fmt.Errorf("symbol is required")
	}

	params := url.Values{}
	if page := getString(fields, "page", ""); page != "" {
		params.Set("page", page)
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	path := fmt.Sprintf("/market/%s/trades", url.PathEscape(symbol))
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFundingRates gets funding rate history for a perpetual market.
func (s *DriftService) GetFundingRates(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	symbol := getString(fields, "symbol", "")
	if symbol == "" {
		return nil, fmt.Errorf("symbol is required")
	}

	params := url.Values{}
	if page := getString(fields, "page", ""); page != "" {
		params.Set("page", page)
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	path := fmt.Sprintf("/market/%s/fundingRates", url.PathEscape(symbol))
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFundingRateStats gets aggregated funding rate statistics across all
// perp markets.
func (s *DriftService) GetFundingRateStats(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/stats/fundingRates", nil)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
