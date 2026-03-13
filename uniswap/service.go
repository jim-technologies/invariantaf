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

// UniswapService implements the UniswapService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type UniswapService struct {
	baseURL string
	client  *http.Client
}

// NewUniswapService creates a new service with default settings.
// No authentication is required for the GeckoTerminal public API.
func NewUniswapService() *UniswapService {
	return &UniswapService{
		baseURL: "https://api.geckoterminal.com/api/v2",
		client:  &http.Client{},
	}
}

// get performs a GET request to the GeckoTerminal API and returns the decoded JSON.
func (s *UniswapService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. search endpoint).
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

// ListTopPools lists the top Uniswap V3 pools on Ethereum.
func (s *UniswapService) ListTopPools(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if page := getInt(fields, "page"); page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	}

	data, err := s.get("/networks/eth/dexes/uniswap_v3/pools", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetPool gets detailed data for a specific pool by address.
func (s *UniswapService) GetPool(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	poolAddress := getString(fields, "pool_address", "")
	if poolAddress == "" {
		return nil, fmt.Errorf("pool_address is required")
	}

	path := fmt.Sprintf("/networks/eth/pools/%s", poolAddress)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTokenPrice gets the current USD price for a token.
func (s *UniswapService) GetTokenPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tokenAddress := getString(fields, "token_address", "")
	if tokenAddress == "" {
		return nil, fmt.Errorf("token_address is required")
	}

	path := fmt.Sprintf("/simple/networks/eth/token_price/%s", tokenAddress)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// ListTrendingPools lists currently trending pools on Ethereum.
func (s *UniswapService) ListTrendingPools(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if page := getInt(fields, "page"); page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	}

	data, err := s.get("/networks/eth/trending_pools", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetOHLCV gets OHLCV candlestick data for a pool.
func (s *UniswapService) GetOHLCV(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	poolAddress := getString(fields, "pool_address", "")
	if poolAddress == "" {
		return nil, fmt.Errorf("pool_address is required")
	}

	params := url.Values{}
	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	path := fmt.Sprintf("/networks/eth/pools/%s/ohlcv/day", poolAddress)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// SearchPools searches for pools by name, symbol, or token address.
func (s *UniswapService) SearchPools(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := getString(fields, "query", "")
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{}
	params.Set("query", query)
	if network := getString(fields, "network", ""); network != "" {
		params.Set("network", network)
	}
	if page := getInt(fields, "page"); page > 0 {
		params.Set("page", strconv.FormatInt(page, 10))
	}

	data, err := s.get("/search/pools", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
