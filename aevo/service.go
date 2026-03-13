package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"google.golang.org/protobuf/types/known/structpb"
)

// AevoService implements the AevoService RPCs defined in the proto descriptor.
// Each method takes a structpb.Struct request and returns a structpb.Struct
// response, allowing the invariant protocol SDK to handle serialization
// transparently.
type AevoService struct {
	baseURL string
	client  *http.Client
}

// NewAevoService creates a new service with default settings.
// No authentication is required for the Aevo public API.
func NewAevoService() *AevoService {
	return &AevoService{
		baseURL: "https://api.aevo.xyz",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Aevo API and returns the decoded JSON as a
// map. If the response is a JSON array, it is wrapped as {"items": [...]}.
func (s *AevoService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. /assets endpoint).
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

// ListAssets returns all tradeable asset symbols on Aevo.
func (s *AevoService) ListAssets(_ context.Context, _ *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/assets", nil)
	if err != nil {
		return nil, err
	}

	// Response is an array of strings, wrapped as {"items": [...]}.
	return toStruct(data)
}

// ListMarkets returns all markets (perps + options) on Aevo.
func (s *AevoService) ListMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if asset := getString(fields, "asset", ""); asset != "" {
		params.Set("asset", asset)
	}
	if instType := getString(fields, "instrument_type", ""); instType != "" {
		params.Set("instrument_type", instType)
	}

	data, err := s.get("/markets", params)
	if err != nil {
		return nil, err
	}

	// Response is an array of market objects, wrapped as {"items": [...]}.
	return toStruct(data)
}

// GetOrderbook returns the orderbook for a specific instrument.
func (s *AevoService) GetOrderbook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instrumentName := getString(fields, "instrument_name", "")
	if instrumentName == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", instrumentName)

	data, err := s.get("/orderbook", params)
	if err != nil {
		return nil, err
	}

	// Convert bids/asks from [[price, qty], ...] to [{price, quantity}, ...]
	// for cleaner proto mapping.
	for _, side := range []string{"bids", "asks"} {
		if raw, ok := data[side]; ok {
			if levels, ok := raw.([]any); ok {
				converted := make([]any, 0, len(levels))
				for _, level := range levels {
					if pair, ok := level.([]any); ok && len(pair) >= 2 {
						converted = append(converted, map[string]any{
							"price":    pair[0],
							"quantity": pair[1],
						})
					}
				}
				data[side] = converted
			}
		}
	}

	return toStruct(data)
}

// GetFunding returns the current funding rate for a perpetual instrument.
func (s *AevoService) GetFunding(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instrumentName := getString(fields, "instrument_name", "")
	if instrumentName == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", instrumentName)

	data, err := s.get("/funding", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFundingHistory returns historical funding rates for a perpetual instrument.
func (s *AevoService) GetFundingHistory(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instrumentName := getString(fields, "instrument_name", "")
	if instrumentName == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", instrumentName)

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", fmt.Sprintf("%d", limit))
	}
	if startTime := getString(fields, "start_time", ""); startTime != "" {
		params.Set("start_time", startTime)
	}
	if endTime := getString(fields, "end_time", ""); endTime != "" {
		params.Set("end_time", endTime)
	}

	data, err := s.get("/funding-history", params)
	if err != nil {
		return nil, err
	}

	// The response has "funding_history" as an array of arrays:
	// [[instrument_name, timestamp, funding_rate, mark_price], ...]
	// Convert to structured records.
	if raw, ok := data["funding_history"]; ok {
		if records, ok := raw.([]any); ok {
			converted := make([]any, 0, len(records))
			for _, record := range records {
				if arr, ok := record.([]any); ok && len(arr) >= 4 {
					converted = append(converted, map[string]any{
						"instrument_name": arr[0],
						"timestamp":       arr[1],
						"funding_rate":    arr[2],
						"mark_price":      arr[3],
					})
				}
			}
			data["funding_history"] = converted
		}
	}

	return toStruct(data)
}

// GetIndex returns the current index price for an asset.
func (s *AevoService) GetIndex(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	asset := getString(fields, "asset", "")
	if asset == "" {
		return nil, fmt.Errorf("asset is required")
	}

	params := url.Values{}
	params.Set("asset", asset)

	data, err := s.get("/index", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetStatistics returns market statistics for an asset.
func (s *AevoService) GetStatistics(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	asset := getString(fields, "asset", "")
	if asset == "" {
		return nil, fmt.Errorf("asset is required")
	}

	params := url.Values{}
	params.Set("asset", asset)

	if instType := getString(fields, "instrument_type", ""); instType != "" {
		params.Set("instrument_type", instType)
	}

	data, err := s.get("/statistics", params)
	if err != nil {
		return nil, err
	}

	// Flatten "open_interest.total" to "open_interest" string.
	if oi, ok := data["open_interest"]; ok {
		if oiMap, ok := oi.(map[string]any); ok {
			if total, ok := oiMap["total"]; ok {
				data["open_interest"] = total
			}
		}
	}

	return toStruct(data)
}

// GetTradeHistory returns recent trade history for an instrument.
func (s *AevoService) GetTradeHistory(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instrumentName := getString(fields, "instrument_name", "")
	if instrumentName == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	path := fmt.Sprintf("/instrument/%s/trade-history", instrumentName)

	data, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
