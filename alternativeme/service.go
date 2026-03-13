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

// AlternativeMeService implements the AlternativeMeService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type AlternativeMeService struct {
	baseURL string
	client  *http.Client
}

// NewAlternativeMeService creates a new service with default settings.
// The Alternative.me API requires no authentication.
func NewAlternativeMeService() *AlternativeMeService {
	base := os.Getenv("ALTERNATIVEME_BASE_URL")
	if base == "" {
		base = "https://api.alternative.me"
	}
	return &AlternativeMeService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// get performs a GET request to the Alternative.me API and returns the decoded JSON.
func (s *AlternativeMeService) get(path string, params url.Values) (map[string]any, error) {
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

// GetFearGreedIndex returns the Fear & Greed Index (current + historical).
func (s *AlternativeMeService) GetFearGreedIndex(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("format", "json")

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	payload, err := s.get("/fng/", params)
	if err != nil {
		return nil, err
	}

	rawData, _ := payload["data"].([]any)
	entries := make([]any, 0, len(rawData))
	for _, item := range rawData {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		entry := map[string]any{
			"value":                fmt.Sprintf("%v", m["value"]),
			"value_classification": stringVal(m, "value_classification"),
			"timestamp":            intVal(m, "timestamp"),
			"time_until_update":    fmt.Sprintf("%v", m["time_until_update"]),
		}
		entries = append(entries, entry)
	}

	return toStruct(map[string]any{"data": entries})
}

// GetGlobalMarketData returns global crypto market data (top coins).
func (s *AlternativeMeService) GetGlobalMarketData(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("convert", "USD")

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	payload, err := s.get("/v2/ticker/", params)
	if err != nil {
		return nil, err
	}

	rawData := extractTickerData(payload)
	tickers := make([]any, 0, len(rawData))
	for _, item := range rawData {
		tickers = append(tickers, transformCoinTicker(item))
	}

	return toStruct(map[string]any{"data": tickers})
}

// GetCoinData returns data for a specific coin by CoinMarketCap ID.
func (s *AlternativeMeService) GetCoinData(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getString(fields, "id", "")
	if id == "" {
		return nil, fmt.Errorf("id is required")
	}

	params := url.Values{}
	params.Set("convert", "USD")

	path := fmt.Sprintf("/v2/ticker/%s/", id)
	payload, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	rawData, _ := payload["data"].(map[string]any)
	// The API wraps single coin in {"data": {"<id>": {...}}}
	if rawData != nil {
		if _, hasName := rawData["name"]; !hasName {
			for _, v := range rawData {
				if inner, ok := v.(map[string]any); ok {
					rawData = inner
					break
				}
			}
		}
	}

	ticker := transformCoinTicker(rawData)
	return toStruct(map[string]any{"data": ticker})
}

// GetListings returns all coin listings.
func (s *AlternativeMeService) GetListings(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("convert", "USD")

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	payload, err := s.get("/v2/listings/", params)
	if err != nil {
		return nil, err
	}

	rawData, _ := payload["data"].([]any)
	listings := make([]any, 0, len(rawData))
	for _, item := range rawData {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		listing := map[string]any{
			"id":           fmt.Sprintf("%v", m["id"]),
			"name":         stringVal(m, "name"),
			"symbol":       stringVal(m, "symbol"),
			"website_slug": stringVal(m, "website_slug"),
			"rank":         intVal(m, "rank"),
		}
		listings = append(listings, listing)
	}

	return toStruct(map[string]any{"data": listings})
}

// extractTickerData extracts ticker list from the v2/ticker response envelope.
// The API returns {"data": {"<id>": {...}, ...}} -- a dict keyed by id.
func extractTickerData(payload map[string]any) []map[string]any {
	data, ok := payload["data"]
	if !ok {
		return nil
	}
	switch d := data.(type) {
	case map[string]any:
		result := make([]map[string]any, 0, len(d))
		for _, v := range d {
			if m, ok := v.(map[string]any); ok {
				result = append(result, m)
			}
		}
		return result
	case []any:
		result := make([]map[string]any, 0, len(d))
		for _, v := range d {
			if m, ok := v.(map[string]any); ok {
				result = append(result, m)
			}
		}
		return result
	}
	return nil
}

// transformCoinTicker normalizes a coin ticker entry into proto-compatible fields.
func transformCoinTicker(item map[string]any) map[string]any {
	if item == nil {
		return map[string]any{}
	}
	quotes, _ := item["quotes"].(map[string]any)
	usd := map[string]any{}
	if quotes != nil {
		usd, _ = quotes["USD"].(map[string]any)
		if usd == nil {
			usd = map[string]any{}
		}
	}

	return map[string]any{
		"id":                  fmt.Sprintf("%v", item["id"]),
		"name":                stringVal(item, "name"),
		"symbol":              stringVal(item, "symbol"),
		"rank":                intVal(item, "rank"),
		"price_usd":          fmt.Sprintf("%v", usd["price"]),
		"price_btc":          "",
		"market_cap_usd":     fmt.Sprintf("%v", usd["market_cap"]),
		"volume_24h_usd":     fmt.Sprintf("%v", usd["volume_24h"]),
		"percent_change_1h":  percentChangeVal(usd, "percentage_change_1h", "percent_change_1h"),
		"percent_change_24h": percentChangeVal(usd, "percentage_change_24h", "percent_change_24h"),
		"percent_change_7d":  percentChangeVal(usd, "percentage_change_7d", "percent_change_7d"),
		"last_updated":       intVal(item, "last_updated"),
	}
}

// stringVal returns a string value from a map, defaulting to "".
func stringVal(m map[string]any, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
		return fmt.Sprintf("%v", v)
	}
	return ""
}

// intVal returns an int64 value from a map, handling both float64 and string.
func intVal(m map[string]any, key string) int64 {
	if v, ok := m[key]; ok {
		switch n := v.(type) {
		case float64:
			return int64(n)
		case string:
			if i, err := strconv.ParseInt(n, 10, 64); err == nil {
				return i
			}
		}
	}
	return 0
}

// percentChangeVal returns a percentage change string, trying primary key then fallback.
func percentChangeVal(m map[string]any, primary, fallback string) string {
	if v, ok := m[primary]; ok && v != nil {
		return fmt.Sprintf("%v", v)
	}
	if v, ok := m[fallback]; ok && v != nil {
		return fmt.Sprintf("%v", v)
	}
	return ""
}
