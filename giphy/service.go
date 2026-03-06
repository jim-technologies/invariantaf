package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"

	"google.golang.org/protobuf/types/known/structpb"
)

// GiphyService implements the giphy.v1.GiphyService RPCs.
// Each method takes a *structpb.Struct request and returns a *structpb.Struct response.
// The struct fields correspond to the proto request/response message fields.
type GiphyService struct {
	apiKey  string
	baseURL string
	client  *http.Client
}

// NewGiphyService creates a new GiphyService. It reads the GIPHY_API_KEY
// environment variable, falling back to the free public beta key.
func NewGiphyService() *GiphyService {
	key := os.Getenv("GIPHY_API_KEY")
	if key == "" {
		key = "dc6zaTOxFJmzC" // public beta key
	}
	return &GiphyService{
		apiKey:  key,
		baseURL: "https://api.giphy.com",
		client:  &http.Client{},
	}
}

// get performs an HTTP GET to the Giphy API and returns the raw JSON as a map.
func (s *GiphyService) get(path string, params url.Values) (map[string]any, error) {
	params.Set("api_key", s.apiKey)
	u := fmt.Sprintf("%s%s?%s", s.baseURL, path, params.Encode())
	resp, err := s.client.Get(u)
	if err != nil {
		return nil, fmt.Errorf("giphy request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("giphy API returned status %d", resp.StatusCode)
	}
	var result map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode giphy response: %w", err)
	}
	return result, nil
}

// parseGif extracts a Gif proto-like struct from a raw Giphy API GIF object.
func parseGif(raw map[string]any) map[string]any {
	gif := map[string]any{
		"id":                str(raw, "id"),
		"url":               str(raw, "url"),
		"title":             str(raw, "title"),
		"rating":            str(raw, "rating"),
		"import_datetime":   str(raw, "import_datetime"),
		"trending_datetime": str(raw, "trending_datetime"),
		"source":            str(raw, "source"),
		"bitly_url":         str(raw, "bitly_url"),
		"embed_url":         str(raw, "embed_url"),
		"username":          str(raw, "username"),
		"slug":              str(raw, "slug"),
		"type":              str(raw, "type"),
	}

	if images, ok := raw["images"].(map[string]any); ok {
		if orig, ok := images["original"].(map[string]any); ok {
			gif["original_url"] = str(orig, "url")
			gif["original_width"] = str(orig, "width")
			gif["original_height"] = str(orig, "height")
		}
		if fw, ok := images["fixed_width"].(map[string]any); ok {
			gif["fixed_width_url"] = str(fw, "url")
		}
		if fh, ok := images["fixed_height"].(map[string]any); ok {
			gif["fixed_height_url"] = str(fh, "url")
		}
		if ds, ok := images["downsized"].(map[string]any); ok {
			gif["downsized_url"] = str(ds, "url")
		}
		if pv, ok := images["preview_gif"].(map[string]any); ok {
			gif["preview_url"] = str(pv, "url")
		}
	}

	return gif
}

// parseGifList extracts a list of Gif maps from the "data" array in a Giphy response.
func parseGifList(raw map[string]any) []any {
	dataRaw, ok := raw["data"].([]any)
	if !ok {
		return nil
	}
	var gifs []any
	for _, item := range dataRaw {
		if gifMap, ok := item.(map[string]any); ok {
			gifs = append(gifs, parseGif(gifMap))
		}
	}
	return gifs
}

// parsePagination extracts pagination metadata from a Giphy response.
func parsePagination(raw map[string]any) map[string]any {
	p, ok := raw["pagination"].(map[string]any)
	if !ok {
		return map[string]any{"total_count": 0.0, "count": 0.0, "offset": 0.0}
	}
	return map[string]any{
		"total_count": num(p, "total_count"),
		"count":       num(p, "count"),
		"offset":      num(p, "offset"),
	}
}

// str safely extracts a string value from a map.
func str(m map[string]any, key string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

// num safely extracts a float64 value from a map.
func num(m map[string]any, key string) float64 {
	if v, ok := m[key]; ok {
		if f, ok := v.(float64); ok {
			return f
		}
	}
	return 0
}

// addSearchParams adds common search query parameters to url.Values.
func addSearchParams(params url.Values, fields map[string]*structpb.Value) {
	if v, ok := fields["limit"]; ok && v.GetNumberValue() > 0 {
		params.Set("limit", fmt.Sprintf("%.0f", v.GetNumberValue()))
	}
	if v, ok := fields["offset"]; ok && v.GetNumberValue() > 0 {
		params.Set("offset", fmt.Sprintf("%.0f", v.GetNumberValue()))
	}
	if v, ok := fields["rating"]; ok && v.GetStringValue() != "" {
		params.Set("rating", v.GetStringValue())
	}
	if v, ok := fields["lang"]; ok && v.GetStringValue() != "" {
		params.Set("lang", v.GetStringValue())
	}
}

// Search searches for GIFs by keyword or phrase.
func (s *GiphyService) Search(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := fields["query"].GetStringValue()
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{"q": {query}}
	addSearchParams(params, fields)

	raw, err := s.get("/v1/gifs/search", params)
	if err != nil {
		return nil, err
	}

	result, err := structpb.NewStruct(map[string]any{
		"data":       parseGifList(raw),
		"pagination": parsePagination(raw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// Trending gets currently trending GIFs.
func (s *GiphyService) Trending(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	addSearchParams(params, fields)

	raw, err := s.get("/v1/gifs/trending", params)
	if err != nil {
		return nil, err
	}

	result, err := structpb.NewStruct(map[string]any{
		"data":       parseGifList(raw),
		"pagination": parsePagination(raw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// GetGifById gets a single GIF by its unique Giphy ID.
func (s *GiphyService) GetGifById(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := fields["id"].GetStringValue()
	if id == "" {
		return nil, fmt.Errorf("id is required")
	}

	raw, err := s.get(fmt.Sprintf("/v1/gifs/%s", url.PathEscape(id)), url.Values{})
	if err != nil {
		return nil, err
	}

	dataRaw, ok := raw["data"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("unexpected response format: missing data")
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": parseGif(dataRaw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// GetGifsByIds gets multiple GIFs by their Giphy IDs.
func (s *GiphyService) GetGifsByIds(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	idsValue, ok := fields["ids"]
	if !ok {
		return nil, fmt.Errorf("ids is required")
	}

	var ids []string
	for _, v := range idsValue.GetListValue().GetValues() {
		ids = append(ids, v.GetStringValue())
	}
	if len(ids) == 0 {
		return nil, fmt.Errorf("ids must not be empty")
	}

	params := url.Values{"ids": {strings.Join(ids, ",")}}
	raw, err := s.get("/v1/gifs", params)
	if err != nil {
		return nil, err
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": parseGifList(raw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// Random gets a random GIF, optionally filtered by tag.
func (s *GiphyService) Random(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	if v, ok := fields["tag"]; ok && v.GetStringValue() != "" {
		params.Set("tag", v.GetStringValue())
	}
	if v, ok := fields["rating"]; ok && v.GetStringValue() != "" {
		params.Set("rating", v.GetStringValue())
	}

	raw, err := s.get("/v1/gifs/random", params)
	if err != nil {
		return nil, err
	}

	dataRaw, ok := raw["data"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("unexpected response format: missing data")
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": parseGif(dataRaw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// SearchStickers searches for stickers by keyword.
func (s *GiphyService) SearchStickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := fields["query"].GetStringValue()
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{"q": {query}}
	addSearchParams(params, fields)

	raw, err := s.get("/v1/stickers/search", params)
	if err != nil {
		return nil, err
	}

	result, err := structpb.NewStruct(map[string]any{
		"data":       parseGifList(raw),
		"pagination": parsePagination(raw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// TrendingStickers gets currently trending stickers.
func (s *GiphyService) TrendingStickers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	addSearchParams(params, fields)

	raw, err := s.get("/v1/stickers/trending", params)
	if err != nil {
		return nil, err
	}

	result, err := structpb.NewStruct(map[string]any{
		"data":       parseGifList(raw),
		"pagination": parsePagination(raw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// RandomSticker gets a random sticker, optionally filtered by tag.
func (s *GiphyService) RandomSticker(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	if v, ok := fields["tag"]; ok && v.GetStringValue() != "" {
		params.Set("tag", v.GetStringValue())
	}
	if v, ok := fields["rating"]; ok && v.GetStringValue() != "" {
		params.Set("rating", v.GetStringValue())
	}

	raw, err := s.get("/v1/stickers/random", params)
	if err != nil {
		return nil, err
	}

	dataRaw, ok := raw["data"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("unexpected response format: missing data")
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": parseGif(dataRaw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// Translate translates text into the most relevant GIF.
func (s *GiphyService) Translate(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	query := fields["query"].GetStringValue()
	if query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := url.Values{"s": {query}}
	if v, ok := fields["weirdness"]; ok && v.GetNumberValue() > 0 {
		params.Set("weirdness", fmt.Sprintf("%.0f", v.GetNumberValue()))
	}
	if v, ok := fields["rating"]; ok && v.GetStringValue() != "" {
		params.Set("rating", v.GetStringValue())
	}

	raw, err := s.get("/v1/gifs/translate", params)
	if err != nil {
		return nil, err
	}

	dataRaw, ok := raw["data"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("unexpected response format: missing data")
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": parseGif(dataRaw),
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}

// GetCategories gets the list of GIF content categories.
func (s *GiphyService) GetCategories(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	if v, ok := fields["limit"]; ok && v.GetNumberValue() > 0 {
		params.Set("limit", fmt.Sprintf("%.0f", v.GetNumberValue()))
	}
	if v, ok := fields["offset"]; ok && v.GetNumberValue() > 0 {
		params.Set("offset", fmt.Sprintf("%.0f", v.GetNumberValue()))
	}

	raw, err := s.get("/v1/gifs/categories", params)
	if err != nil {
		return nil, err
	}

	dataRaw, ok := raw["data"].([]any)
	if !ok {
		return nil, fmt.Errorf("unexpected response format: missing data array")
	}

	var categories []any
	for _, item := range dataRaw {
		catMap, ok := item.(map[string]any)
		if !ok {
			continue
		}
		cat := map[string]any{
			"name": str(catMap, "name"),
		}
		if gifRaw, ok := catMap["gif"].(map[string]any); ok {
			cat["gif"] = parseGif(gifRaw)
		}
		categories = append(categories, cat)
	}

	result, err := structpb.NewStruct(map[string]any{
		"data": categories,
	})
	if err != nil {
		return nil, fmt.Errorf("build response: %w", err)
	}
	return result, nil
}
