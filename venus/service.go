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

// VenusService implements the VenusService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type VenusService struct {
	baseURL string
	client  *http.Client
}

// NewVenusService creates a new service with default settings.
// No authentication is required for the Venus public API.
func NewVenusService() *VenusService {
	return &VenusService{
		baseURL: "https://api.venus.io",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Venus API and returns the decoded JSON.
func (s *VenusService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. pools endpoint).
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

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// ListMarkets lists all lending markets in the Venus core pool.
func (s *VenusService) ListMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/markets/core-pool", url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetMarket gets details for a specific lending market by underlying token address.
func (s *VenusService) GetMarket(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	underlyingAddress := getString(fields, "underlying_address", "")
	if underlyingAddress == "" {
		return nil, fmt.Errorf("underlying_address is required")
	}

	params := url.Values{}
	params.Set("underlyingAddress", underlyingAddress)

	data, err := s.get("/markets/core-pool", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ListPools lists all lending pools on Venus Protocol.
func (s *VenusService) ListPools(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/pools", url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPoolLiquidity gets pool liquidity data across Venus lending pools.
func (s *VenusService) GetPoolLiquidity(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/pools/liquidity", url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
