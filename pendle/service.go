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

// PendleService implements the PendleService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type PendleService struct {
	baseURL string
	client  *http.Client
}

// NewPendleService creates a new service with default settings.
// No authentication is required for the Pendle public API.
func NewPendleService() *PendleService {
	return &PendleService{
		baseURL: "https://api-v2.pendle.finance/core",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Pendle API and returns the decoded JSON.
func (s *PendleService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. prices endpoint).
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

// getRaw performs a GET request and returns the raw body bytes for custom parsing.
func (s *PendleService) getRaw(path string, params url.Values) ([]byte, error) {
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

	return body, nil
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

// ListMarkets lists all yield markets across supported chains.
func (s *PendleService) ListMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if chainID := getInt(fields, "chain_id"); chainID > 0 {
		params.Set("chainId", strconv.FormatInt(chainID, 10))
	}
	if skip := getInt(fields, "skip"); skip > 0 {
		params.Set("skip", strconv.FormatInt(skip, 10))
	}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	data, err := s.get("/v1/markets/all", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetMarketData gets detailed market data for a specific market.
func (s *PendleService) GetMarketData(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chainID := getInt(fields, "chain_id")
	if chainID == 0 {
		return nil, fmt.Errorf("chain_id is required")
	}
	address := getString(fields, "address", "")
	if address == "" {
		return nil, fmt.Errorf("address is required")
	}

	path := fmt.Sprintf("/v2/%d/markets/%s/data", chainID, address)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPrices gets current prices for Pendle assets/tokens.
func (s *PendleService) GetPrices(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if chainID := getInt(fields, "chain_id"); chainID > 0 {
		params.Set("chainId", strconv.FormatInt(chainID, 10))
	}
	if addresses := getString(fields, "addresses", ""); addresses != "" {
		params.Set("addresses", addresses)
	}

	body, err := s.getRaw("/v1/prices/assets", params)
	if err != nil {
		return nil, err
	}

	// The prices endpoint may return either a map or an object with a "prices" key.
	var result map[string]any

	// Try parsing as a direct map of address -> price.
	var priceMap map[string]any
	if err := json.Unmarshal(body, &priceMap); err != nil {
		return nil, fmt.Errorf("decode prices response: %w", err)
	}

	// If the response has a "prices" key, use that; otherwise wrap the whole thing.
	if _, ok := priceMap["prices"]; ok {
		result = priceMap
	} else {
		result = map[string]any{"prices": priceMap}
	}

	return toStruct(result)
}

// GetHistoricalData gets historical market data for a specific market.
func (s *PendleService) GetHistoricalData(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chainID := getInt(fields, "chain_id")
	if chainID == 0 {
		return nil, fmt.Errorf("chain_id is required")
	}
	address := getString(fields, "address", "")
	if address == "" {
		return nil, fmt.Errorf("address is required")
	}

	params := url.Values{}
	if timeRange := getString(fields, "time_range", ""); timeRange != "" {
		params.Set("timeRange", timeRange)
	}

	path := fmt.Sprintf("/v2/%d/markets/%s/historical-data", chainID, address)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetSwapPrices gets swap pricing for PT/YT tokens in a specific market.
func (s *PendleService) GetSwapPrices(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chainID := getInt(fields, "chain_id")
	if chainID == 0 {
		return nil, fmt.Errorf("chain_id is required")
	}
	market := getString(fields, "market", "")
	if market == "" {
		return nil, fmt.Errorf("market is required")
	}

	path := fmt.Sprintf("/v1/sdk/%d/markets/%s/swapping-prices", chainID, market)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
