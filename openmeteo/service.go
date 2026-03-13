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
	"strings"

	"google.golang.org/protobuf/types/known/structpb"
)

var defaultModels = []string{
	"ecmwf_ifs025",
	"gfs_seamless",
	"icon_seamless",
	"jma_seamless",
	"gem_seamless",
	"meteofrance_seamless",
}

// OpenMeteoService implements the OpenMeteoService RPCs defined in the proto
// descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type OpenMeteoService struct {
	baseURL           string
	archiveBaseURL    string
	airQualityBaseURL string
	marineBaseURL     string
	client            *http.Client
}

// NewOpenMeteoService creates a new service with default settings.
// No authentication required. Base URLs can be overridden via environment variables.
func NewOpenMeteoService() *OpenMeteoService {
	base := os.Getenv("OPENMETEO_BASE_URL")
	if base == "" {
		base = "https://api.open-meteo.com"
	}
	archive := os.Getenv("OPENMETEO_ARCHIVE_BASE_URL")
	if archive == "" {
		archive = "https://archive-api.open-meteo.com"
	}
	airQuality := os.Getenv("OPENMETEO_AIR_QUALITY_BASE_URL")
	if airQuality == "" {
		airQuality = "https://air-quality-api.open-meteo.com"
	}
	marine := os.Getenv("OPENMETEO_MARINE_BASE_URL")
	if marine == "" {
		marine = "https://marine-api.open-meteo.com"
	}
	return &OpenMeteoService{
		baseURL:           strings.TrimRight(base, "/"),
		archiveBaseURL:    strings.TrimRight(archive, "/"),
		airQualityBaseURL: strings.TrimRight(airQuality, "/"),
		marineBaseURL:     strings.TrimRight(marine, "/"),
		client:            &http.Client{},
	}
}

// get performs a GET request to an Open-Meteo API endpoint and returns the decoded JSON.
func (s *OpenMeteoService) get(baseURL, path string, params url.Values) (map[string]any, error) {
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

	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode response: %w (body: %s)", err, string(body))
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

// helper: get a float field from structpb.
func getFloat(fields map[string]*structpb.Value, key string) float64 {
	if v, ok := fields[key]; ok {
		return v.GetNumberValue()
	}
	return 0
}

// helper: get a string list field from structpb.
func getStringList(fields map[string]*structpb.Value, key string) []string {
	v, ok := fields[key]
	if !ok {
		return nil
	}
	lv := v.GetListValue()
	if lv == nil {
		return nil
	}
	var result []string
	for _, item := range lv.GetValues() {
		if s := item.GetStringValue(); s != "" {
			result = append(result, s)
		}
	}
	return result
}

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// ensureFloats converts a slice of any to []float64, replacing nil with 0.0.
func ensureFloats(values []any) []any {
	result := make([]any, len(values))
	for i, v := range values {
		switch n := v.(type) {
		case float64:
			result[i] = n
		case nil:
			result[i] = float64(0)
		default:
			result[i] = v
		}
	}
	return result
}

// toAnySlice converts []any JSON arrays from the API response.
func toAnySlice(v any) []any {
	if v == nil {
		return nil
	}
	arr, ok := v.([]any)
	if !ok {
		return nil
	}
	return arr
}

// toStringSlice converts []any to []any preserving strings for structpb.
func toStringSlice(v any) []any {
	arr := toAnySlice(v)
	if arr == nil {
		return []any{}
	}
	result := make([]any, len(arr))
	for i, item := range arr {
		if s, ok := item.(string); ok {
			result[i] = s
		} else {
			result[i] = fmt.Sprintf("%v", item)
		}
	}
	return result
}

// toIntSlice converts []any of float64 to []any of int-like float64 for weather codes.
func toIntSlice(v any) []any {
	arr := toAnySlice(v)
	if arr == nil {
		return []any{}
	}
	result := make([]any, len(arr))
	for i, item := range arr {
		switch n := item.(type) {
		case float64:
			result[i] = n
		case nil:
			result[i] = float64(0)
		default:
			result[i] = item
		}
	}
	return result
}

// GetForecast gets hourly and daily weather forecasts for a location.
func (s *OpenMeteoService) GetForecast(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "latitude")
	lon := getFloat(fields, "longitude")

	forecastDays := getInt(fields, "forecast_days")
	if forecastDays == 0 {
		forecastDays = 7
	}
	timezone := getString(fields, "timezone", "auto")

	params := url.Values{}
	params.Set("latitude", strconv.FormatFloat(lat, 'f', -1, 64))
	params.Set("longitude", strconv.FormatFloat(lon, 'f', -1, 64))
	params.Set("hourly", "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code")
	params.Set("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max")
	params.Set("timezone", timezone)
	params.Set("forecast_days", strconv.FormatInt(forecastDays, 10))

	data, err := s.get(s.baseURL, "/v1/forecast", params)
	if err != nil {
		return nil, err
	}

	return toStruct(buildForecastResponse(data))
}

// GetHistoricalWeather gets historical weather data for backtesting.
func (s *OpenMeteoService) GetHistoricalWeather(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "latitude")
	lon := getFloat(fields, "longitude")
	startDate := getString(fields, "start_date", "")
	if startDate == "" {
		return nil, fmt.Errorf("start_date is required")
	}
	endDate := getString(fields, "end_date", "")
	if endDate == "" {
		return nil, fmt.Errorf("end_date is required")
	}
	timezone := getString(fields, "timezone", "auto")

	params := url.Values{}
	params.Set("latitude", strconv.FormatFloat(lat, 'f', -1, 64))
	params.Set("longitude", strconv.FormatFloat(lon, 'f', -1, 64))
	params.Set("start_date", startDate)
	params.Set("end_date", endDate)
	params.Set("hourly", "temperature_2m,precipitation")
	params.Set("daily", "temperature_2m_max,temperature_2m_min,precipitation_sum")
	params.Set("timezone", timezone)

	data, err := s.get(s.archiveBaseURL, "/v1/archive", params)
	if err != nil {
		return nil, err
	}

	return toStruct(buildForecastResponse(data))
}

// GetMultiModelForecast gets forecasts from multiple weather models simultaneously.
func (s *OpenMeteoService) GetMultiModelForecast(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "latitude")
	lon := getFloat(fields, "longitude")

	forecastDays := getInt(fields, "forecast_days")
	if forecastDays == 0 {
		forecastDays = 7
	}

	models := getStringList(fields, "models")
	if len(models) == 0 {
		models = defaultModels
	}

	params := url.Values{}
	params.Set("latitude", strconv.FormatFloat(lat, 'f', -1, 64))
	params.Set("longitude", strconv.FormatFloat(lon, 'f', -1, 64))
	params.Set("hourly", "temperature_2m")
	params.Set("models", strings.Join(models, ","))
	params.Set("forecast_days", strconv.FormatInt(forecastDays, 10))

	data, err := s.get(s.baseURL, "/v1/forecast", params)
	if err != nil {
		return nil, err
	}

	return toStruct(buildMultiModelResponse(data, models))
}

// GetAirQuality gets air quality data for a location.
func (s *OpenMeteoService) GetAirQuality(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "latitude")
	lon := getFloat(fields, "longitude")

	params := url.Values{}
	params.Set("latitude", strconv.FormatFloat(lat, 'f', -1, 64))
	params.Set("longitude", strconv.FormatFloat(lon, 'f', -1, 64))
	params.Set("hourly", "pm2_5,pm10,us_aqi")

	data, err := s.get(s.airQualityBaseURL, "/v1/air-quality", params)
	if err != nil {
		return nil, err
	}

	return toStruct(buildAirQualityResponse(data))
}

// GetMarineWeather gets marine/ocean weather data for a location.
func (s *OpenMeteoService) GetMarineWeather(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	lat := getFloat(fields, "latitude")
	lon := getFloat(fields, "longitude")

	params := url.Values{}
	params.Set("latitude", strconv.FormatFloat(lat, 'f', -1, 64))
	params.Set("longitude", strconv.FormatFloat(lon, 'f', -1, 64))
	params.Set("hourly", "wave_height,wave_period,wind_wave_height")

	data, err := s.get(s.marineBaseURL, "/v1/marine", params)
	if err != nil {
		return nil, err
	}

	return toStruct(buildMarineResponse(data))
}

// --- Response builders ---

func getMap(data map[string]any, key string) map[string]any {
	v, ok := data[key]
	if !ok {
		return nil
	}
	m, ok := v.(map[string]any)
	if !ok {
		return nil
	}
	return m
}

func buildForecastResponse(data map[string]any) map[string]any {
	result := map[string]any{}

	hourlyRaw := getMap(data, "hourly")
	if hourlyRaw != nil {
		result["hourly"] = map[string]any{
			"times":                toStringSlice(hourlyRaw["time"]),
			"temperature_2m":      ensureFloats(toAnySlice(hourlyRaw["temperature_2m"])),
			"relative_humidity_2m": ensureFloats(toAnySlice(hourlyRaw["relative_humidity_2m"])),
			"precipitation":       ensureFloats(toAnySlice(hourlyRaw["precipitation"])),
			"wind_speed_10m":      ensureFloats(toAnySlice(hourlyRaw["wind_speed_10m"])),
			"weather_code":        toIntSlice(hourlyRaw["weather_code"]),
		}
	}

	dailyRaw := getMap(data, "daily")
	if dailyRaw != nil {
		result["daily"] = map[string]any{
			"dates":              toStringSlice(dailyRaw["time"]),
			"temperature_2m_max": ensureFloats(toAnySlice(dailyRaw["temperature_2m_max"])),
			"temperature_2m_min": ensureFloats(toAnySlice(dailyRaw["temperature_2m_min"])),
			"precipitation_sum":  ensureFloats(toAnySlice(dailyRaw["precipitation_sum"])),
			"wind_speed_10m_max": ensureFloats(toAnySlice(dailyRaw["wind_speed_10m_max"])),
		}
	}

	return result
}

func buildMultiModelResponse(data map[string]any, models []string) map[string]any {
	hourlyRaw := getMap(data, "hourly")
	if hourlyRaw == nil {
		hourlyRaw = map[string]any{}
	}

	times := toStringSlice(hourlyRaw["time"])

	var modelForecasts []any
	for _, model := range models {
		key := fmt.Sprintf("temperature_2m_%s", model)
		temps := ensureFloats(toAnySlice(hourlyRaw[key]))
		if len(temps) > 0 {
			modelForecasts = append(modelForecasts, map[string]any{
				"model_name":     model,
				"times":          times,
				"temperature_2m": temps,
			})
		}
	}

	// Fallback: if no per-model keys found, use plain temperature_2m
	if len(modelForecasts) == 0 {
		if rawTemps := toAnySlice(hourlyRaw["temperature_2m"]); len(rawTemps) > 0 {
			temps := ensureFloats(rawTemps)
			for _, model := range models {
				modelForecasts = append(modelForecasts, map[string]any{
					"model_name":     model,
					"times":          times,
					"temperature_2m": temps,
				})
			}
		}
	}

	return map[string]any{
		"model_forecasts": modelForecasts,
	}
}

func buildAirQualityResponse(data map[string]any) map[string]any {
	result := map[string]any{}

	hourlyRaw := getMap(data, "hourly")
	if hourlyRaw != nil {
		result["hourly"] = map[string]any{
			"times":  toStringSlice(hourlyRaw["time"]),
			"pm2_5":  ensureFloats(toAnySlice(hourlyRaw["pm2_5"])),
			"pm10":   ensureFloats(toAnySlice(hourlyRaw["pm10"])),
			"us_aqi": ensureFloats(toAnySlice(hourlyRaw["us_aqi"])),
		}
	}

	return result
}

func buildMarineResponse(data map[string]any) map[string]any {
	result := map[string]any{}

	hourlyRaw := getMap(data, "hourly")
	if hourlyRaw != nil {
		result["hourly"] = map[string]any{
			"times":            toStringSlice(hourlyRaw["time"]),
			"wave_height":      ensureFloats(toAnySlice(hourlyRaw["wave_height"])),
			"wave_period":      ensureFloats(toAnySlice(hourlyRaw["wave_period"])),
			"wind_wave_height": ensureFloats(toAnySlice(hourlyRaw["wind_wave_height"])),
		}
	}

	return result
}
