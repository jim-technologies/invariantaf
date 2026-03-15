package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"

	"google.golang.org/protobuf/types/known/structpb"
)

// CryptoDotComService implements the CryptoDotComService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type CryptoDotComService struct {
	baseURL string
	client  *http.Client
}

// NewCryptoDotComService creates a new service with default settings.
// The Crypto.com Exchange public API requires no authentication.
func NewCryptoDotComService() *CryptoDotComService {
	base := os.Getenv("CRYPTODOTCOM_BASE_URL")
	if base == "" {
		base = "https://api.crypto.com/exchange/v1"
	}
	return &CryptoDotComService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// apiResponse represents the Crypto.com API response envelope.
type apiResponse struct {
	Code   int    `json:"code"`
	Method string `json:"method"`
	Result struct {
		Data json.RawMessage `json:"data"`
	} `json:"result"`
}

// get performs a GET request to the Crypto.com Exchange API and returns the
// unwrapped data from the {"code":0,"result":{"data":[...]}} envelope.
func (s *CryptoDotComService) get(path string, params url.Values) (any, error) {
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

	var envelope apiResponse
	if err := json.Unmarshal(body, &envelope); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	if envelope.Code != 0 {
		return nil, fmt.Errorf("API error (code %d): %s", envelope.Code, string(body))
	}

	var data any
	if err := json.Unmarshal(envelope.Result.Data, &data); err != nil {
		return nil, fmt.Errorf("decode result data: %w", err)
	}

	return data, nil
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

// helper: convert any value to structpb.Struct wrapping it in {"data": ...}.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// GetInstruments returns all available trading instruments.
func (s *CryptoDotComService) GetInstruments(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	raw, err := s.get("/public/get-instruments", nil)
	if err != nil {
		return nil, err
	}

	items, _ := raw.([]any)
	instruments := make([]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		instruments = append(instruments, map[string]any{
			"instrument_name":       stringVal(m, "instrument_name"),
			"quote_currency":        stringVal(m, "quote_currency"),
			"base_currency":         stringVal(m, "base_currency"),
			"price_decimals":        fmt.Sprintf("%v", m["price_decimals"]),
			"quantity_decimals":     fmt.Sprintf("%v", m["quantity_decimals"]),
			"margin_trading_enabled": boolVal(m, "margin_trading_enabled"),
		})
	}

	return toStruct(map[string]any{"data": instruments})
}

// GetTickers returns ticker data for one or all instruments.
func (s *CryptoDotComService) GetTickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	if name := getString(fields, "instrument_name", ""); name != "" {
		params.Set("instrument_name", name)
	}

	raw, err := s.get("/public/get-tickers", params)
	if err != nil {
		return nil, err
	}

	items, _ := raw.([]any)
	tickers := make([]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		tickers = append(tickers, map[string]any{
			"instrument_name":      stringVal(m, "instrument_name"),
			"high":                 fmt.Sprintf("%v", m["h"]),
			"low":                  fmt.Sprintf("%v", m["l"]),
			"latest_trade":         fmt.Sprintf("%v", m["a"]),
			"volume":               fmt.Sprintf("%v", m["v"]),
			"best_bid":             fmt.Sprintf("%v", m["b"]),
			"best_ask":             fmt.Sprintf("%v", m["k"]),
			"price_change":         fmt.Sprintf("%v", m["c"]),
			"price_change_percent": fmt.Sprintf("%v", m["cp"]),
			"timestamp":            intVal(m, "t"),
		})
	}

	return toStruct(map[string]any{"data": tickers})
}

// GetOrderbook returns the order book for an instrument.
func (s *CryptoDotComService) GetOrderbook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	name := getString(fields, "instrument_name", "")
	if name == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", name)
	if depth := getInt(fields, "depth"); depth > 0 {
		params.Set("depth", fmt.Sprintf("%d", depth))
	}

	raw, err := s.get("/public/get-book", params)
	if err != nil {
		return nil, err
	}

	items, _ := raw.([]any)
	if len(items) == 0 {
		return toStruct(map[string]any{"data": map[string]any{
			"bids": []any{}, "asks": []any{}, "timestamp": int64(0),
		}})
	}

	book, _ := items[0].(map[string]any)
	if book == nil {
		book = map[string]any{}
	}

	bids := parseLevels(book, "bids")
	asks := parseLevels(book, "asks")

	return toStruct(map[string]any{"data": map[string]any{
		"bids":      bids,
		"asks":      asks,
		"timestamp": intVal(book, "t"),
	}})
}

// GetCandlestick returns OHLCV candlestick data for an instrument.
func (s *CryptoDotComService) GetCandlestick(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	name := getString(fields, "instrument_name", "")
	if name == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", name)
	if tf := getString(fields, "timeframe", ""); tf != "" {
		params.Set("timeframe", tf)
	}

	raw, err := s.get("/public/get-candlestick", params)
	if err != nil {
		return nil, err
	}

	items, _ := raw.([]any)
	candles := make([]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		candles = append(candles, map[string]any{
			"timestamp": intVal(m, "t"),
			"open":      fmt.Sprintf("%v", m["o"]),
			"high":      fmt.Sprintf("%v", m["h"]),
			"low":       fmt.Sprintf("%v", m["l"]),
			"close":     fmt.Sprintf("%v", m["c"]),
			"volume":    fmt.Sprintf("%v", m["v"]),
		})
	}

	return toStruct(map[string]any{"data": candles})
}

// GetTrades returns recent trades for an instrument.
func (s *CryptoDotComService) GetTrades(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	name := getString(fields, "instrument_name", "")
	if name == "" {
		return nil, fmt.Errorf("instrument_name is required")
	}

	params := url.Values{}
	params.Set("instrument_name", name)

	raw, err := s.get("/public/get-trades", params)
	if err != nil {
		return nil, err
	}

	items, _ := raw.([]any)
	trades := make([]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			continue
		}
		trades = append(trades, map[string]any{
			"trade_id":        fmt.Sprintf("%v", m["d"]),
			"instrument_name": stringVal(m, "i"),
			"side":            stringVal(m, "s"),
			"price":           fmt.Sprintf("%v", m["p"]),
			"quantity":        fmt.Sprintf("%v", m["q"]),
			"timestamp":       intVal(m, "t"),
		})
	}

	return toStruct(map[string]any{"data": trades})
}

// parseLevels extracts bid/ask levels from the orderbook response.
func parseLevels(book map[string]any, key string) []any {
	raw, _ := book[key].([]any)
	levels := make([]any, 0, len(raw))
	for _, item := range raw {
		arr, ok := item.([]any)
		if !ok || len(arr) < 3 {
			continue
		}
		levels = append(levels, map[string]any{
			"price":    fmt.Sprintf("%v", arr[0]),
			"quantity": fmt.Sprintf("%v", arr[1]),
			"count":    fmt.Sprintf("%v", arr[2]),
		})
	}
	return levels
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
			return 0
		}
	}
	return 0
}

// boolVal returns a bool value from a map, defaulting to false.
func boolVal(m map[string]any, key string) bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return false
}
