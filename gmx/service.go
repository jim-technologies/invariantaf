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

// chainBaseURLs maps chain names to their GMX v2 API base URLs.
var chainBaseURLs = map[string]string{
	"arbitrum":  "https://arbitrum-api.gmxinfra.io",
	"avalanche": "https://avalanche-api.gmxinfra.io",
}

// GmxService implements the GmxService RPCs defined in the proto descriptor.
// Each method takes a structpb.Struct request and returns a structpb.Struct
// response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type GmxService struct {
	client *http.Client
}

// NewGmxService creates a new service with default settings.
// No authentication is required for the GMX public API.
func NewGmxService() *GmxService {
	return &GmxService{
		client: &http.Client{},
	}
}

// resolveBaseURL returns the API base URL for the given chain name.
// Defaults to Arbitrum if the chain is empty or unknown.
func resolveBaseURL(chain string) string {
	if u, ok := chainBaseURLs[chain]; ok {
		return u
	}
	return chainBaseURLs["arbitrum"]
}

// get performs a GET request and returns the raw body bytes.
func (s *GmxService) get(baseURL, path string, params url.Values) ([]byte, error) {
	u := fmt.Sprintf("%s%s", baseURL, path)
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

// helper: convert a map to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// ListMarkets lists all perpetual markets with liquidity, open interest,
// funding/borrowing rates, and net rates.
func (s *GmxService) ListMarkets(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chain := getString(fields, "chain", "arbitrum")
	baseURL := resolveBaseURL(chain)

	body, err := s.get(baseURL, "/markets/info", nil)
	if err != nil {
		return nil, err
	}

	// The response is {"markets": [...]}
	var raw map[string]any
	if err := json.Unmarshal(body, &raw); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	return toStruct(raw)
}

// GetTickers gets current price tickers for all tokens on the specified chain.
func (s *GmxService) GetTickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chain := getString(fields, "chain", "arbitrum")
	baseURL := resolveBaseURL(chain)

	body, err := s.get(baseURL, "/prices/tickers", nil)
	if err != nil {
		return nil, err
	}

	// The response is an array of ticker objects.
	var arr []any
	if err := json.Unmarshal(body, &arr); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	return toStruct(map[string]any{"tickers": arr})
}

// GetCandles gets historical OHLC price candles for a token.
func (s *GmxService) GetCandles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	chain := getString(fields, "chain", "arbitrum")
	baseURL := resolveBaseURL(chain)

	tokenSymbol := getString(fields, "token_symbol", "")
	if tokenSymbol == "" {
		return nil, fmt.Errorf("token_symbol is required")
	}

	period := getString(fields, "period", "1h")

	params := url.Values{}
	params.Set("tokenSymbol", tokenSymbol)
	params.Set("period", period)

	body, err := s.get(baseURL, "/prices/candles", params)
	if err != nil {
		return nil, err
	}

	// The response is {"period": "1h", "candles": [[ts, o, h, l, c], ...]}
	var raw struct {
		Period  string      `json:"period"`
		Candles [][]float64 `json:"candles"`
	}
	if err := json.Unmarshal(body, &raw); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	// Convert array-of-arrays into array-of-objects for structpb compatibility.
	candles := make([]any, 0, len(raw.Candles))
	for _, c := range raw.Candles {
		if len(c) < 5 {
			continue
		}
		candles = append(candles, map[string]any{
			"timestamp": c[0],
			"open":      c[1],
			"high":      c[2],
			"low":       c[3],
			"close":     c[4],
		})
	}

	return toStruct(map[string]any{
		"period":  raw.Period,
		"candles": candles,
	})
}
