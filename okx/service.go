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

// OKXService implements the OKXService RPCs defined in the proto descriptor.
// Each method takes a structpb.Struct request and returns a structpb.Struct
// response, allowing the invariant protocol SDK to handle serialization/
// deserialization transparently.
type OKXService struct {
	baseURL string
	client  *http.Client
}

// NewOKXService creates a new service with default settings.
// No authentication is required for the OKX public API.
func NewOKXService() *OKXService {
	return &OKXService{
		baseURL: "https://www.okx.com",
		client:  &http.Client{},
	}
}

// get performs a GET request to the OKX API, unwraps the standard
// {"code":"0","msg":"","data":[...]} envelope, and returns the data field
// wrapped in a map.
func (s *OKXService) get(path string, params url.Values) (map[string]any, error) {
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

	var envelope struct {
		Code string `json:"code"`
		Msg  string `json:"msg"`
		Data json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(body, &envelope); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
	}

	if envelope.Code != "0" {
		return nil, fmt.Errorf("OKX API error (code %s): %s", envelope.Code, envelope.Msg)
	}

	// Data is typically an array. Parse it and wrap in a map.
	var items []any
	if err := json.Unmarshal(envelope.Data, &items); err != nil {
		// Try as a single object.
		var obj map[string]any
		if err2 := json.Unmarshal(envelope.Data, &obj); err2 != nil {
			return nil, fmt.Errorf("decode data: %w (raw: %s)", err, string(envelope.Data))
		}
		return obj, nil
	}

	return map[string]any{"items": items}, nil
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

// GetTickers returns all tickers for the given instrument type.
func (s *OKXService) GetTickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}

	instType := getString(fields, "inst_type", "SPOT")
	params.Set("instType", instType)

	data, err := s.get("/api/v5/market/tickers", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetTicker returns a single ticker by instrument ID.
func (s *OKXService) GetTicker(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instID := getString(fields, "inst_id", "")
	if instID == "" {
		return nil, fmt.Errorf("inst_id is required")
	}

	params := url.Values{}
	params.Set("instId", instID)

	data, err := s.get("/api/v5/market/ticker", params)
	if err != nil {
		return nil, err
	}

	// The API returns data as an array with a single element.
	// Extract the first item if present.
	if items, ok := data["items"]; ok {
		if arr, ok := items.([]any); ok && len(arr) > 0 {
			if obj, ok := arr[0].(map[string]any); ok {
				return toStruct(obj)
			}
		}
	}

	return toStruct(data)
}

// GetOrderbook returns the orderbook for a specific instrument.
func (s *OKXService) GetOrderbook(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instID := getString(fields, "inst_id", "")
	if instID == "" {
		return nil, fmt.Errorf("inst_id is required")
	}

	params := url.Values{}
	params.Set("instId", instID)

	if sz := getInt(fields, "size"); sz > 0 {
		params.Set("sz", strconv.FormatInt(sz, 10))
	} else {
		params.Set("sz", "20")
	}

	data, err := s.get("/api/v5/market/books", params)
	if err != nil {
		return nil, err
	}

	// The API returns data as an array with a single element containing asks/bids.
	if items, ok := data["items"]; ok {
		if arr, ok := items.([]any); ok && len(arr) > 0 {
			if obj, ok := arr[0].(map[string]any); ok {
				obj["instId"] = instID
				return toStruct(obj)
			}
		}
	}

	return toStruct(data)
}

// GetCandles returns OHLCV candlestick data for a specific instrument.
func (s *OKXService) GetCandles(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instID := getString(fields, "inst_id", "")
	if instID == "" {
		return nil, fmt.Errorf("inst_id is required")
	}

	params := url.Values{}
	params.Set("instId", instID)

	bar := getString(fields, "bar", "1H")
	params.Set("bar", bar)

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	} else {
		params.Set("limit", "100")
	}

	data, err := s.get("/api/v5/market/candles", params)
	if err != nil {
		return nil, err
	}

	// Candles come as arrays of arrays: [[ts, o, h, l, c, vol, volCcy, ...], ...]
	// Convert to structured objects.
	if items, ok := data["items"]; ok {
		if arr, ok := items.([]any); ok {
			candles := make([]any, 0, len(arr))
			for _, item := range arr {
				if row, ok := item.([]any); ok && len(row) >= 7 {
					candle := map[string]any{
						"ts":     fmt.Sprintf("%v", row[0]),
						"open":   fmt.Sprintf("%v", row[1]),
						"high":   fmt.Sprintf("%v", row[2]),
						"low":    fmt.Sprintf("%v", row[3]),
						"close":  fmt.Sprintf("%v", row[4]),
						"vol":    fmt.Sprintf("%v", row[5]),
						"volCcy": fmt.Sprintf("%v", row[6]),
					}
					candles = append(candles, candle)
				}
			}
			return toStruct(map[string]any{"items": candles})
		}
	}

	return toStruct(data)
}

// GetTrades returns recent trades for a specific instrument.
func (s *OKXService) GetTrades(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instID := getString(fields, "inst_id", "")
	if instID == "" {
		return nil, fmt.Errorf("inst_id is required")
	}

	params := url.Values{}
	params.Set("instId", instID)

	if limit := getInt(fields, "limit"); limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	} else {
		params.Set("limit", "100")
	}

	data, err := s.get("/api/v5/market/trades", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}

// GetFundingRate returns the current funding rate for a perpetual swap.
func (s *OKXService) GetFundingRate(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instID := getString(fields, "inst_id", "")
	if instID == "" {
		return nil, fmt.Errorf("inst_id is required")
	}

	params := url.Values{}
	params.Set("instId", instID)

	data, err := s.get("/api/v5/public/funding-rate", params)
	if err != nil {
		return nil, err
	}

	// The API returns data as an array with a single element.
	if items, ok := data["items"]; ok {
		if arr, ok := items.([]any); ok && len(arr) > 0 {
			if obj, ok := arr[0].(map[string]any); ok {
				return toStruct(obj)
			}
		}
	}

	return toStruct(data)
}

// GetInstruments returns all instruments of the given type.
func (s *OKXService) GetInstruments(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	instType := getString(fields, "inst_type", "")
	if instType == "" {
		return nil, fmt.Errorf("inst_type is required")
	}

	params := url.Values{}
	params.Set("instType", instType)

	data, err := s.get("/api/v5/public/instruments", params)
	if err != nil {
		return nil, err
	}

	return toStruct(data)
}
