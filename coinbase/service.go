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

// CoinbaseService implements the CoinbaseService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type CoinbaseService struct {
	baseURL string
	client  *http.Client
}

// NewCoinbaseService creates a new service with default settings.
// No authentication is required for the Coinbase public API.
func NewCoinbaseService() *CoinbaseService {
	return &CoinbaseService{
		baseURL: "https://api.exchange.coinbase.com",
		client:  &http.Client{},
	}
}

// get performs a GET request to the Coinbase API and returns the decoded JSON.
func (s *CoinbaseService) get(path string, params url.Values) (map[string]any, error) {
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
		// The response may be an array (e.g. products endpoint).
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

// ListProducts lists all available trading pairs on Coinbase Exchange.
func (s *CoinbaseService) ListProducts(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	data, err := s.get("/products", url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProduct gets details for a single trading pair.
func (s *CoinbaseService) GetProduct(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	path := fmt.Sprintf("/products/%s", productID)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProductTicker gets the latest ticker for a trading pair.
func (s *CoinbaseService) GetProductTicker(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	path := fmt.Sprintf("/products/%s/ticker", productID)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProductOrderbook gets the order book for a trading pair.
func (s *CoinbaseService) GetProductOrderbook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	params := url.Values{}
	level := getInt(fields, "level")
	if level > 0 {
		params.Set("level", strconv.FormatInt(level, 10))
	} else {
		params.Set("level", "2")
	}

	path := fmt.Sprintf("/products/%s/book", productID)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProductCandles gets OHLCV candles for a trading pair.
func (s *CoinbaseService) GetProductCandles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	params := url.Values{}
	granularity := getInt(fields, "granularity")
	if granularity > 0 {
		params.Set("granularity", strconv.FormatInt(granularity, 10))
	} else {
		params.Set("granularity", "3600")
	}
	if start := getString(fields, "start", ""); start != "" {
		params.Set("start", start)
	}
	if end := getString(fields, "end", ""); end != "" {
		params.Set("end", end)
	}

	path := fmt.Sprintf("/products/%s/candles", productID)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProductTrades gets recent trades for a trading pair.
func (s *CoinbaseService) GetProductTrades(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	params := url.Values{}
	limit := getInt(fields, "limit")
	if limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	} else {
		params.Set("limit", "100")
	}

	path := fmt.Sprintf("/products/%s/trades", productID)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetProductStats gets 24-hour rolling statistics for a trading pair.
func (s *CoinbaseService) GetProductStats(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	productID := getString(fields, "product_id", "")
	if productID == "" {
		return nil, fmt.Errorf("product_id is required")
	}

	path := fmt.Sprintf("/products/%s/stats", productID)
	data, err := s.get(path, url.Values{})
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
