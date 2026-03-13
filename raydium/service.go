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

// RaydiumService implements the RaydiumService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type RaydiumService struct {
	baseURL string
	client  *http.Client
}

// NewRaydiumService creates a new service with default settings.
// No authentication is required for the Raydium public API.
func NewRaydiumService() *RaydiumService {
	return &RaydiumService{
		baseURL: "https://api-v3.raydium.io",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Raydium API and returns the decoded JSON.
func (s *RaydiumService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array. Try wrapping in a map.
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

// GetPoolInfo gets pool information by pool ID.
func (s *RaydiumService) GetPoolInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	poolID := getString(fields, "pool_id", "")
	if poolID == "" {
		return nil, fmt.Errorf("pool_id is required")
	}

	params := url.Values{}
	params.Set("ids", poolID)

	data, err := s.get("/pools/info/ids", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ListPools lists pools with sorting and pagination.
func (s *RaydiumService) ListPools(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	params.Set("poolType", getString(fields, "pool_type", "all"))
	params.Set("poolSortField", getString(fields, "pool_sort_field", "volume"))
	params.Set("sortType", getString(fields, "sort_type", "desc"))

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("pageSize", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("pageSize", "10")
	}

	page := getInt(fields, "page")
	if page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	} else {
		params.Set("page", "1")
	}

	data, err := s.get("/pools/info/list", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPoolByMints finds pools by token mint address.
func (s *RaydiumService) GetPoolByMints(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	mint1 := getString(fields, "mint1", "")
	if mint1 == "" {
		return nil, fmt.Errorf("mint1 is required")
	}

	params := url.Values{}
	params.Set("mint1", mint1)

	if mint2 := getString(fields, "mint2", ""); mint2 != "" {
		params.Set("mint2", mint2)
	}

	params.Set("poolType", getString(fields, "pool_type", "all"))
	params.Set("poolSortField", getString(fields, "pool_sort_field", "liquidity"))
	params.Set("sortType", getString(fields, "sort_type", "desc"))

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("pageSize", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("pageSize", "10")
	}

	page := getInt(fields, "page")
	if page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	} else {
		params.Set("page", "1")
	}

	data, err := s.get("/pools/info/mint", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFarmInfo gets farm information by farm ID.
func (s *RaydiumService) GetFarmInfo(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	farmID := getString(fields, "farm_id", "")
	if farmID == "" {
		return nil, fmt.Errorf("farm_id is required")
	}

	params := url.Values{}
	params.Set("ids", farmID)

	data, err := s.get("/farm/info/ids", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ListFarms lists farms with pagination.
func (s *RaydiumService) ListFarms(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	pageSize := getInt(fields, "page_size")
	if pageSize > 0 {
		params.Set("pageSize", strconv.FormatInt(pageSize, 10))
	} else {
		params.Set("pageSize", "10")
	}

	page := getInt(fields, "page")
	if page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	} else {
		params.Set("page", "1")
	}

	data, err := s.get("/farm/info/list", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTokenPrice gets token prices by mint address.
func (s *RaydiumService) GetTokenPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	mints := getString(fields, "mints", "")
	if mints == "" {
		return nil, fmt.Errorf("mints is required")
	}

	params := url.Values{}
	params.Set("mints", mints)

	data, err := s.get("/mint/price", params)
	if err != nil {
		return nil, err
	}

	// The response is {"id": "...", "success": true, "data": {"mint": price, ...}}.
	// Extract the "data" map and wrap as "prices" for consistency.
	if dataField, ok := data["data"]; ok {
		if priceMap, ok := dataField.(map[string]any); ok {
			return toStruct(map[string]any{"prices": priceMap})
		}
	}

	// Fallback: return the raw response.
	return toStruct(data)
}
