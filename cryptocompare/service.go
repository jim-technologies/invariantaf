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

// CryptoCompareService implements the CryptoCompareService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type CryptoCompareService struct {
	baseURL string
	client  *http.Client
}

// NewCryptoCompareService creates a new service with default settings.
// Uses CRYPTOCOMPARE_BASE_URL env var or falls back to the public API.
func NewCryptoCompareService() *CryptoCompareService {
	base := os.Getenv("CRYPTOCOMPARE_BASE_URL")
	if base == "" {
		base = "https://min-api.cryptocompare.com"
	}
	return &CryptoCompareService{
		baseURL: base,
		client:  &http.Client{},
	}
}

// get performs a GET request to the CryptoCompare API and returns the decoded JSON.
func (s *CryptoCompareService) get(path string, params url.Values) (map[string]any, error) {
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

// GetPrice gets the price of a single cryptocurrency in multiple currencies.
func (s *CryptoCompareService) GetPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	fsym := getString(fields, "fsym", "")
	if fsym == "" {
		return nil, fmt.Errorf("fsym is required")
	}
	tsyms := getString(fields, "tsyms", "")
	if tsyms == "" {
		return nil, fmt.Errorf("tsyms is required")
	}

	params := url.Values{}
	params.Set("fsym", fsym)
	params.Set("tsyms", tsyms)

	data, err := s.get("/data/price", params)
	if err != nil {
		return nil, err
	}

	// Response is like {"USD": 64500, "EUR": 59000}
	prices := map[string]any{}
	for k, v := range data {
		switch n := v.(type) {
		case float64:
			prices[k] = n
		case json.Number:
			if f, err := n.Float64(); err == nil {
				prices[k] = f
			}
		}
	}

	return toStruct(map[string]any{"prices": prices})
}

// GetMultiPrice gets a price matrix for multiple cryptocurrencies in multiple currencies.
func (s *CryptoCompareService) GetMultiPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	fsyms := getString(fields, "fsyms", "")
	if fsyms == "" {
		return nil, fmt.Errorf("fsyms is required")
	}
	tsyms := getString(fields, "tsyms", "")
	if tsyms == "" {
		return nil, fmt.Errorf("tsyms is required")
	}

	params := url.Values{}
	params.Set("fsyms", fsyms)
	params.Set("tsyms", tsyms)

	data, err := s.get("/data/pricemulti", params)
	if err != nil {
		return nil, err
	}

	// Response is like {"BTC": {"USD": 64500}, "ETH": {"USD": 2500}}
	var rows []any
	for fromSym, pricesMap := range data {
		pm, ok := pricesMap.(map[string]any)
		if !ok {
			continue
		}
		prices := map[string]any{}
		for k, v := range pm {
			if n, ok := v.(float64); ok {
				prices[k] = n
			}
		}
		rows = append(rows, map[string]any{
			"from_symbol": fromSym,
			"prices":      prices,
		})
	}

	return toStruct(map[string]any{"rows": rows})
}

// GetFullPrice gets full price data (volume, market cap, etc.) for multiple cryptocurrencies.
func (s *CryptoCompareService) GetFullPrice(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	fsyms := getString(fields, "fsyms", "")
	if fsyms == "" {
		return nil, fmt.Errorf("fsyms is required")
	}
	tsyms := getString(fields, "tsyms", "")
	if tsyms == "" {
		return nil, fmt.Errorf("tsyms is required")
	}

	params := url.Values{}
	params.Set("fsyms", fsyms)
	params.Set("tsyms", tsyms)

	data, err := s.get("/data/pricemultifull", params)
	if err != nil {
		return nil, err
	}

	// Response is {"RAW": {"BTC": {"USD": {...fields...}}}}
	raw, _ := data["RAW"].(map[string]any)
	var coins []any
	for fromSym, toMap := range raw {
		tm, ok := toMap.(map[string]any)
		if !ok {
			continue
		}
		for toSym, d := range tm {
			dd, ok := d.(map[string]any)
			if !ok {
				continue
			}
			coins = append(coins, map[string]any{
				"from_symbol":    fromSym,
				"to_symbol":      toSym,
				"price":          toFloat(dd, "PRICE"),
				"volume_24h":     toFloat(dd, "VOLUME24HOUR"),
				"market_cap":     toFloat(dd, "MKTCAP"),
				"change_pct_24h": toFloat(dd, "CHANGEPCT24HOUR"),
				"high_24h":       toFloat(dd, "HIGH24HOUR"),
				"low_24h":        toFloat(dd, "LOW24HOUR"),
				"open_24h":       toFloat(dd, "OPEN24HOUR"),
				"supply":         toFloat(dd, "SUPPLY"),
			})
		}
	}

	return toStruct(map[string]any{"coins": coins})
}

// GetHistoHour gets hourly OHLCV history for a cryptocurrency pair.
func (s *CryptoCompareService) GetHistoHour(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	fsym := getString(fields, "fsym", "")
	if fsym == "" {
		return nil, fmt.Errorf("fsym is required")
	}
	tsym := getString(fields, "tsym", "")
	if tsym == "" {
		return nil, fmt.Errorf("tsym is required")
	}

	params := url.Values{}
	params.Set("fsym", fsym)
	params.Set("tsym", tsym)

	limit := getInt(fields, "limit")
	if limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	data, err := s.get("/data/v2/histohour", params)
	if err != nil {
		return nil, err
	}

	candles := extractHistoData(data)
	return toStruct(map[string]any{"candles": candles})
}

// GetHistoDay gets daily OHLCV history for a cryptocurrency pair.
func (s *CryptoCompareService) GetHistoDay(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	fsym := getString(fields, "fsym", "")
	if fsym == "" {
		return nil, fmt.Errorf("fsym is required")
	}
	tsym := getString(fields, "tsym", "")
	if tsym == "" {
		return nil, fmt.Errorf("tsym is required")
	}

	params := url.Values{}
	params.Set("fsym", fsym)
	params.Set("tsym", tsym)

	limit := getInt(fields, "limit")
	if limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	data, err := s.get("/data/v2/histoday", params)
	if err != nil {
		return nil, err
	}

	candles := extractHistoData(data)
	return toStruct(map[string]any{"candles": candles})
}

// GetTopByVolume gets top coins ranked by total volume.
func (s *CryptoCompareService) GetTopByVolume(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	tsym := getString(fields, "tsym", "")
	if tsym == "" {
		return nil, fmt.Errorf("tsym is required")
	}

	params := url.Values{}
	params.Set("tsym", tsym)

	limit := getInt(fields, "limit")
	if limit > 0 {
		params.Set("limit", strconv.FormatInt(limit, 10))
	}

	data, err := s.get("/data/top/totalvolfull", params)
	if err != nil {
		return nil, err
	}

	// Response is {"Data": [{...}]}
	dataArr, _ := data["Data"].([]any)
	var coins []any
	for _, item := range dataArr {
		itemMap, ok := item.(map[string]any)
		if !ok {
			continue
		}
		coinInfo, _ := itemMap["CoinInfo"].(map[string]any)
		rawData, _ := itemMap["RAW"].(map[string]any)
		tsymData, _ := rawData[tsym].(map[string]any)

		coins = append(coins, map[string]any{
			"name":            toStringField(coinInfo, "FullName"),
			"symbol":          toStringField(coinInfo, "Name"),
			"price":           toFloat(tsymData, "PRICE"),
			"volume_24h":      toFloat(tsymData, "VOLUME24HOUR"),
			"market_cap":      toFloat(tsymData, "MKTCAP"),
			"change_pct_24h":  toFloat(tsymData, "CHANGEPCT24HOUR"),
		})
	}

	return toStruct(map[string]any{"coins": coins})
}

// extractHistoData extracts OHLCV candles from CryptoCompare's nested response.
func extractHistoData(payload map[string]any) []any {
	dataWrapper, _ := payload["Data"].(map[string]any)
	rawCandles, _ := dataWrapper["Data"].([]any)

	var candles []any
	for _, c := range rawCandles {
		cm, ok := c.(map[string]any)
		if !ok {
			continue
		}
		candles = append(candles, map[string]any{
			"time":       toFloat(cm, "time"),
			"open":       toFloat(cm, "open"),
			"high":       toFloat(cm, "high"),
			"low":        toFloat(cm, "low"),
			"close":      toFloat(cm, "close"),
			"volumefrom": toFloat(cm, "volumefrom"),
			"volumeto":   toFloat(cm, "volumeto"),
		})
	}
	return candles
}

// toFloat safely extracts a float64 from a map.
func toFloat(m map[string]any, key string) float64 {
	if m == nil {
		return 0
	}
	v, ok := m[key]
	if !ok {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	case int64:
		return float64(n)
	}
	return 0
}

// toStringField safely extracts a string from a map.
func toStringField(m map[string]any, key string) string {
	if m == nil {
		return ""
	}
	v, ok := m[key]
	if !ok {
		return ""
	}
	s, ok := v.(string)
	if !ok {
		return ""
	}
	return s
}
