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

// CryptoSignalService implements the CryptoSignalService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type CryptoSignalService struct {
	fngBaseURL       string
	coingeckoBaseURL string
	etherscanBaseURL string
	client           *http.Client
}

// NewCryptoSignalService creates a new service with default settings.
// No authentication is required for any of the public APIs used.
func NewCryptoSignalService() *CryptoSignalService {
	return &CryptoSignalService{
		fngBaseURL:       "https://api.alternative.me",
		coingeckoBaseURL: "https://api.coingecko.com/api/v3",
		etherscanBaseURL: "https://api.etherscan.io/api",
		client:           &http.Client{},
	}
}

// get performs a GET request to the given URL and returns the decoded JSON as a map.
func (s *CryptoSignalService) get(rawURL string) (map[string]any, error) {
	req, err := http.NewRequest("GET", rawURL, nil)
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
		// The response may be an array (e.g. trending endpoint).
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

// GetFearGreedIndex returns the crypto Fear & Greed Index with historical data.
func (s *CryptoSignalService) GetFearGreedIndex(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	limit := getInt(fields, "limit")
	if limit <= 0 {
		limit = 10
	}
	if limit > 30 {
		limit = 30
	}

	params := url.Values{}
	params.Set("limit", strconv.FormatInt(limit, 10))
	params.Set("format", "json")

	u := fmt.Sprintf("%s/fng/?%s", s.fngBaseURL, params.Encode())
	data, err := s.get(u)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetGlobalMetrics returns global cryptocurrency market metrics.
func (s *CryptoSignalService) GetGlobalMetrics(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	_ = getString(req.GetFields(), "", "") // consume req to match pattern

	u := fmt.Sprintf("%s/global", s.coingeckoBaseURL)
	data, err := s.get(u)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTrendingCoins returns trending coins by search volume on CoinGecko.
func (s *CryptoSignalService) GetTrendingCoins(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	_ = getString(req.GetFields(), "", "") // consume req to match pattern

	u := fmt.Sprintf("%s/search/trending", s.coingeckoBaseURL)
	data, err := s.get(u)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetGasPrice returns current Ethereum gas prices from Etherscan.
func (s *CryptoSignalService) GetGasPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	_ = getString(req.GetFields(), "", "") // consume req to match pattern

	params := url.Values{}
	params.Set("module", "gastracker")
	params.Set("action", "gasoracle")

	u := fmt.Sprintf("%s?%s", s.etherscanBaseURL, params.Encode())
	data, err := s.get(u)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
