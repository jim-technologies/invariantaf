package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockGiphyServer returns an httptest.Server that simulates Giphy API responses.
func mockGiphyServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		// Verify api_key is always present.
		if r.URL.Query().Get("api_key") == "" {
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]any{"message": "missing api_key"})
			return
		}

		switch r.URL.Path {
		case "/v1/gifs/search":
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					gifFixture("abc123", "Funny Cat"),
					gifFixture("def456", "Dancing Dog"),
				},
				"pagination": map[string]any{
					"total_count": float64(200),
					"count":       float64(2),
					"offset":      float64(0),
				},
			})

		case "/v1/gifs/trending":
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					gifFixture("trend1", "Trending GIF 1"),
					gifFixture("trend2", "Trending GIF 2"),
					gifFixture("trend3", "Trending GIF 3"),
				},
				"pagination": map[string]any{
					"total_count": float64(50),
					"count":       float64(3),
					"offset":      float64(0),
				},
			})

		case "/v1/gifs/abc123":
			json.NewEncoder(w).Encode(map[string]any{
				"data": gifFixture("abc123", "Funny Cat"),
			})

		case "/v1/gifs":
			ids := r.URL.Query().Get("ids")
			if ids == "" {
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					gifFixture("abc123", "Funny Cat"),
					gifFixture("def456", "Dancing Dog"),
				},
			})

		case "/v1/gifs/random":
			json.NewEncoder(w).Encode(map[string]any{
				"data": gifFixture("rand1", "Random GIF"),
			})

		case "/v1/stickers/search":
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					gifFixture("stk1", "Happy Sticker"),
				},
				"pagination": map[string]any{
					"total_count": float64(10),
					"count":       float64(1),
					"offset":      float64(0),
				},
			})

		case "/v1/stickers/trending":
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					gifFixture("stk_trend1", "Trending Sticker"),
				},
				"pagination": map[string]any{
					"total_count": float64(5),
					"count":       float64(1),
					"offset":      float64(0),
				},
			})

		case "/v1/stickers/random":
			json.NewEncoder(w).Encode(map[string]any{
				"data": gifFixture("stk_rand1", "Random Sticker"),
			})

		case "/v1/gifs/translate":
			json.NewEncoder(w).Encode(map[string]any{
				"data": gifFixture("trans1", "Translated GIF"),
			})

		case "/v1/gifs/categories":
			json.NewEncoder(w).Encode(map[string]any{
				"data": []any{
					map[string]any{
						"name": "Animals",
						"gif":  gifFixture("cat_anim", "Animals Category"),
					},
					map[string]any{
						"name": "Actions",
						"gif":  gifFixture("cat_act", "Actions Category"),
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"message": "not found"})
		}
	}))
}

// gifFixture returns a Giphy-API-shaped GIF object for testing.
func gifFixture(id, title string) map[string]any {
	return map[string]any{
		"id":                id,
		"url":               "https://giphy.com/gifs/" + id,
		"title":             title,
		"rating":            "g",
		"import_datetime":   "2024-01-01 00:00:00",
		"trending_datetime": "2024-06-15 12:00:00",
		"source":            "https://example.com",
		"bitly_url":         "https://gph.is/" + id,
		"embed_url":         "https://giphy.com/embed/" + id,
		"username":          "testuser",
		"slug":              title + "-" + id,
		"type":              "gif",
		"images": map[string]any{
			"original": map[string]any{
				"url":    "https://media.giphy.com/" + id + ".gif",
				"width":  "480",
				"height": "360",
			},
			"fixed_width": map[string]any{
				"url": "https://media.giphy.com/" + id + "_200w.gif",
			},
			"fixed_height": map[string]any{
				"url": "https://media.giphy.com/" + id + "_200h.gif",
			},
			"downsized": map[string]any{
				"url": "https://media.giphy.com/" + id + "_downsized.gif",
			},
			"preview_gif": map[string]any{
				"url": "https://media.giphy.com/" + id + "_preview.gif",
			},
		},
	}
}

// testService creates a GiphyService pointing at the mock server.
func testService(t *testing.T) (*GiphyService, *httptest.Server) {
	t.Helper()
	ts := mockGiphyServer()
	svc := &GiphyService{
		apiKey:  "test-key",
		baseURL: ts.URL,
		client:  http.DefaultClient,
	}
	return svc, ts
}

// reqStruct is a helper to build a *structpb.Struct from a map.
func reqStruct(t *testing.T, fields map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(fields)
	if err != nil {
		t.Fatalf("reqStruct: %v", err)
	}
	return s
}

// gifData extracts the "data" field as a map from a response struct.
func gifData(t *testing.T, resp *structpb.Struct) map[string]any {
	t.Helper()
	d := resp.GetFields()["data"].GetStructValue()
	if d == nil {
		t.Fatal("response missing data struct")
	}
	result := make(map[string]any)
	for k, v := range d.GetFields() {
		result[k] = v.AsInterface()
	}
	return result
}

// gifList extracts the "data" field as a list of maps from a response struct.
func gifList(t *testing.T, resp *structpb.Struct) []map[string]any {
	t.Helper()
	list := resp.GetFields()["data"].GetListValue()
	if list == nil {
		t.Fatal("response missing data list")
	}
	var result []map[string]any
	for _, v := range list.GetValues() {
		m := make(map[string]any)
		for k, val := range v.GetStructValue().GetFields() {
			m[k] = val.AsInterface()
		}
		result = append(result, m)
	}
	return result
}

// paginationData extracts pagination metadata from a response.
func paginationData(t *testing.T, resp *structpb.Struct) map[string]any {
	t.Helper()
	p := resp.GetFields()["pagination"].GetStructValue()
	if p == nil {
		t.Fatal("response missing pagination")
	}
	result := make(map[string]any)
	for k, v := range p.GetFields() {
		result[k] = v.AsInterface()
	}
	return result
}

func TestSearch(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.Search(context.Background(), reqStruct(t, map[string]any{
		"query": "funny cats",
		"limit": 10.0,
	}))
	if err != nil {
		t.Fatalf("Search: %v", err)
	}

	gifs := gifList(t, resp)
	if len(gifs) != 2 {
		t.Fatalf("expected 2 gifs, got %d", len(gifs))
	}
	if gifs[0]["id"] != "abc123" {
		t.Errorf("expected id abc123, got %v", gifs[0]["id"])
	}
	if gifs[0]["title"] != "Funny Cat" {
		t.Errorf("expected title Funny Cat, got %v", gifs[0]["title"])
	}
	if gifs[0]["original_url"] != "https://media.giphy.com/abc123.gif" {
		t.Errorf("unexpected original_url: %v", gifs[0]["original_url"])
	}

	pg := paginationData(t, resp)
	if pg["total_count"] != 200.0 {
		t.Errorf("expected total_count 200, got %v", pg["total_count"])
	}
}

func TestSearchMissingQuery(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	_, err := svc.Search(context.Background(), reqStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing query")
	}
}

func TestTrending(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.Trending(context.Background(), reqStruct(t, map[string]any{
		"limit": 3.0,
	}))
	if err != nil {
		t.Fatalf("Trending: %v", err)
	}

	gifs := gifList(t, resp)
	if len(gifs) != 3 {
		t.Fatalf("expected 3 trending gifs, got %d", len(gifs))
	}
	if gifs[0]["id"] != "trend1" {
		t.Errorf("expected id trend1, got %v", gifs[0]["id"])
	}
}

func TestGetGifById(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetGifById(context.Background(), reqStruct(t, map[string]any{
		"id": "abc123",
	}))
	if err != nil {
		t.Fatalf("GetGifById: %v", err)
	}

	gif := gifData(t, resp)
	if gif["id"] != "abc123" {
		t.Errorf("expected id abc123, got %v", gif["id"])
	}
	if gif["title"] != "Funny Cat" {
		t.Errorf("expected title Funny Cat, got %v", gif["title"])
	}
	if gif["rating"] != "g" {
		t.Errorf("expected rating g, got %v", gif["rating"])
	}
	if gif["original_width"] != "480" {
		t.Errorf("expected original_width 480, got %v", gif["original_width"])
	}
}

func TestGetGifByIdMissingId(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	_, err := svc.GetGifById(context.Background(), reqStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
}

func TestGetGifsByIds(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetGifsByIds(context.Background(), reqStruct(t, map[string]any{
		"ids": []any{"abc123", "def456"},
	}))
	if err != nil {
		t.Fatalf("GetGifsByIds: %v", err)
	}

	gifs := gifList(t, resp)
	if len(gifs) != 2 {
		t.Fatalf("expected 2 gifs, got %d", len(gifs))
	}
	if gifs[0]["id"] != "abc123" {
		t.Errorf("expected first id abc123, got %v", gifs[0]["id"])
	}
	if gifs[1]["id"] != "def456" {
		t.Errorf("expected second id def456, got %v", gifs[1]["id"])
	}
}

func TestGetGifsByIdsMissingIds(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	_, err := svc.GetGifsByIds(context.Background(), reqStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing ids")
	}
}

func TestRandom(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.Random(context.Background(), reqStruct(t, map[string]any{
		"tag": "cats",
	}))
	if err != nil {
		t.Fatalf("Random: %v", err)
	}

	gif := gifData(t, resp)
	if gif["id"] != "rand1" {
		t.Errorf("expected id rand1, got %v", gif["id"])
	}
	if gif["title"] != "Random GIF" {
		t.Errorf("expected title Random GIF, got %v", gif["title"])
	}
}

func TestRandomNoTag(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.Random(context.Background(), reqStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("Random (no tag): %v", err)
	}

	gif := gifData(t, resp)
	if gif["id"] != "rand1" {
		t.Errorf("expected id rand1, got %v", gif["id"])
	}
}

func TestSearchStickers(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.SearchStickers(context.Background(), reqStruct(t, map[string]any{
		"query": "happy",
	}))
	if err != nil {
		t.Fatalf("SearchStickers: %v", err)
	}

	gifs := gifList(t, resp)
	if len(gifs) != 1 {
		t.Fatalf("expected 1 sticker, got %d", len(gifs))
	}
	if gifs[0]["id"] != "stk1" {
		t.Errorf("expected id stk1, got %v", gifs[0]["id"])
	}

	pg := paginationData(t, resp)
	if pg["total_count"] != 10.0 {
		t.Errorf("expected total_count 10, got %v", pg["total_count"])
	}
}

func TestSearchStickersMissingQuery(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	_, err := svc.SearchStickers(context.Background(), reqStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing query")
	}
}

func TestTrendingStickers(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.TrendingStickers(context.Background(), reqStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("TrendingStickers: %v", err)
	}

	gifs := gifList(t, resp)
	if len(gifs) != 1 {
		t.Fatalf("expected 1 trending sticker, got %d", len(gifs))
	}
	if gifs[0]["id"] != "stk_trend1" {
		t.Errorf("expected id stk_trend1, got %v", gifs[0]["id"])
	}
}

func TestRandomSticker(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.RandomSticker(context.Background(), reqStruct(t, map[string]any{
		"tag":    "love",
		"rating": "g",
	}))
	if err != nil {
		t.Fatalf("RandomSticker: %v", err)
	}

	gif := gifData(t, resp)
	if gif["id"] != "stk_rand1" {
		t.Errorf("expected id stk_rand1, got %v", gif["id"])
	}
}

func TestTranslate(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.Translate(context.Background(), reqStruct(t, map[string]any{
		"query":     "excited",
		"weirdness": 5.0,
		"rating":    "pg",
	}))
	if err != nil {
		t.Fatalf("Translate: %v", err)
	}

	gif := gifData(t, resp)
	if gif["id"] != "trans1" {
		t.Errorf("expected id trans1, got %v", gif["id"])
	}
	if gif["title"] != "Translated GIF" {
		t.Errorf("expected title Translated GIF, got %v", gif["title"])
	}
}

func TestTranslateMissingQuery(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	_, err := svc.Translate(context.Background(), reqStruct(t, map[string]any{}))
	if err == nil {
		t.Fatal("expected error for missing query")
	}
}

func TestGetCategories(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetCategories(context.Background(), reqStruct(t, map[string]any{
		"limit": 10.0,
	}))
	if err != nil {
		t.Fatalf("GetCategories: %v", err)
	}

	list := resp.GetFields()["data"].GetListValue()
	if list == nil {
		t.Fatal("response missing data list")
	}
	cats := list.GetValues()
	if len(cats) != 2 {
		t.Fatalf("expected 2 categories, got %d", len(cats))
	}

	first := cats[0].GetStructValue().GetFields()
	if first["name"].GetStringValue() != "Animals" {
		t.Errorf("expected first category Animals, got %v", first["name"].GetStringValue())
	}
	gifFields := first["gif"].GetStructValue().GetFields()
	if gifFields["id"].GetStringValue() != "cat_anim" {
		t.Errorf("expected gif id cat_anim, got %v", gifFields["id"].GetStringValue())
	}
}

func TestSearchWithAllParams(t *testing.T) {
	// This test verifies that search parameters are correctly forwarded.
	var capturedURL *url.URL
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedURL = r.URL
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"data":       []any{},
			"pagination": map[string]any{"total_count": 0.0, "count": 0.0, "offset": 0.0},
		})
	}))
	defer ts.Close()

	svc := &GiphyService{
		apiKey:  "test-key",
		baseURL: ts.URL,
		client:  http.DefaultClient,
	}

	_, err := svc.Search(context.Background(), reqStruct(t, map[string]any{
		"query":  "test",
		"limit":  15.0,
		"offset": 30.0,
		"rating": "pg-13",
		"lang":   "es",
	}))
	if err != nil {
		t.Fatalf("Search with all params: %v", err)
	}

	if capturedURL == nil {
		t.Fatal("no request was made")
	}
	q := capturedURL.Query()
	if q.Get("q") != "test" {
		t.Errorf("expected q=test, got %v", q.Get("q"))
	}
	if q.Get("limit") != "15" {
		t.Errorf("expected limit=15, got %v", q.Get("limit"))
	}
	if q.Get("offset") != "30" {
		t.Errorf("expected offset=30, got %v", q.Get("offset"))
	}
	if q.Get("rating") != "pg-13" {
		t.Errorf("expected rating=pg-13, got %v", q.Get("rating"))
	}
	if q.Get("lang") != "es" {
		t.Errorf("expected lang=es, got %v", q.Get("lang"))
	}
	if q.Get("api_key") != "test-key" {
		t.Errorf("expected api_key=test-key, got %v", q.Get("api_key"))
	}
}

func TestImageRenditions(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetGifById(context.Background(), reqStruct(t, map[string]any{
		"id": "abc123",
	}))
	if err != nil {
		t.Fatalf("GetGifById: %v", err)
	}

	gif := gifData(t, resp)
	checks := map[string]string{
		"original_url":     "https://media.giphy.com/abc123.gif",
		"original_width":   "480",
		"original_height":  "360",
		"fixed_width_url":  "https://media.giphy.com/abc123_200w.gif",
		"fixed_height_url": "https://media.giphy.com/abc123_200h.gif",
		"downsized_url":    "https://media.giphy.com/abc123_downsized.gif",
		"preview_url":      "https://media.giphy.com/abc123_preview.gif",
	}
	for field, expected := range checks {
		if gif[field] != expected {
			t.Errorf("%s: expected %q, got %v", field, expected, gif[field])
		}
	}
}

func TestAPIErrorHandling(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer ts.Close()

	svc := &GiphyService{
		apiKey:  "test-key",
		baseURL: ts.URL,
		client:  http.DefaultClient,
	}

	_, err := svc.Search(context.Background(), reqStruct(t, map[string]any{
		"query": "test",
	}))
	if err == nil {
		t.Fatal("expected error for 500 response")
	}
}

func TestNewGiphyServiceDefaultKey(t *testing.T) {
	// Unset the env var to test default key.
	t.Setenv("GIPHY_API_KEY", "")
	svc := NewGiphyService()
	if svc.apiKey != "dc6zaTOxFJmzC" {
		t.Errorf("expected default api key, got %v", svc.apiKey)
	}
}

func TestNewGiphyServiceCustomKey(t *testing.T) {
	t.Setenv("GIPHY_API_KEY", "my-custom-key")
	svc := NewGiphyService()
	if svc.apiKey != "my-custom-key" {
		t.Errorf("expected my-custom-key, got %v", svc.apiKey)
	}
}

// --- Live integration tests (hit the real Giphy API) ---
// These use the public beta key (dc6zaTOxFJmzC) which is the default
// in NewGiphyService when GIPHY_API_KEY is not set.

func skipUnlessIntegration(t *testing.T) {
	t.Helper()
	if os.Getenv("TEST_GIPHY") == "" {
		t.Skip("set TEST_GIPHY=1 to run integration tests (hits real Giphy API)")
	}
}

func liveService() *GiphyService {
	return NewGiphyService()
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

func TestLiveSearch(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.Search(context.Background(), mustStruct(t, map[string]any{
		"query": "cats",
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("Search: %v", err)
	}

	gifs := resp.GetFields()["data"].GetListValue().GetValues()
	if len(gifs) == 0 {
		t.Fatal("expected at least 1 gif for 'cats' search")
	}

	gif := gifs[0].GetStructValue().GetFields()
	if gif["id"].GetStringValue() == "" {
		t.Error("gif missing id")
	}
	if gif["title"].GetStringValue() == "" {
		t.Error("gif missing title")
	}
	if gif["url"].GetStringValue() == "" {
		t.Error("gif missing url")
	}
	if gif["original_url"].GetStringValue() == "" {
		t.Error("gif missing original_url")
	}

	// Check pagination
	pg := resp.GetFields()["pagination"].GetStructValue().GetFields()
	if pg["total_count"].GetNumberValue() == 0 {
		t.Error("expected total_count > 0 for cats search")
	}
}

func TestLiveTrending(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.Trending(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("Trending: %v", err)
	}

	gifs := resp.GetFields()["data"].GetListValue().GetValues()
	if len(gifs) == 0 {
		t.Fatal("expected at least 1 trending gif")
	}

	gif := gifs[0].GetStructValue().GetFields()
	if gif["id"].GetStringValue() == "" {
		t.Error("trending gif missing id")
	}
	if gif["type"].GetStringValue() != "gif" {
		t.Errorf("expected type=gif, got %s", gif["type"].GetStringValue())
	}
}

func TestLiveGetGifById(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	// First get a trending gif to use its ID
	trendResp, err := svc.Trending(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(1),
	}))
	if err != nil {
		t.Fatalf("Trending (setup): %v", err)
	}

	trendGifs := trendResp.GetFields()["data"].GetListValue().GetValues()
	if len(trendGifs) == 0 {
		t.Skip("no trending gifs available")
	}
	gifID := trendGifs[0].GetStructValue().GetFields()["id"].GetStringValue()

	resp, err := svc.GetGifById(context.Background(), mustStruct(t, map[string]any{
		"id": gifID,
	}))
	if err != nil {
		t.Fatalf("GetGifById(%s): %v", gifID, err)
	}

	gif := resp.GetFields()["data"].GetStructValue().GetFields()
	if gif["id"].GetStringValue() != gifID {
		t.Errorf("expected id=%s, got %s", gifID, gif["id"].GetStringValue())
	}
	if gif["url"].GetStringValue() == "" {
		t.Error("gif missing url")
	}
	if gif["original_url"].GetStringValue() == "" {
		t.Error("gif missing original_url")
	}
}

func TestLiveRandom(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.Random(context.Background(), mustStruct(t, map[string]any{
		"tag": "funny",
	}))
	if err != nil {
		t.Fatalf("Random: %v", err)
	}

	gif := resp.GetFields()["data"].GetStructValue().GetFields()
	if gif["id"].GetStringValue() == "" {
		t.Error("random gif missing id")
	}
	if gif["url"].GetStringValue() == "" {
		t.Error("random gif missing url")
	}
}

func TestLiveTranslate(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.Translate(context.Background(), mustStruct(t, map[string]any{
		"query": "excited",
	}))
	if err != nil {
		t.Fatalf("Translate: %v", err)
	}

	gif := resp.GetFields()["data"].GetStructValue().GetFields()
	if gif["id"].GetStringValue() == "" {
		t.Error("translated gif missing id")
	}
}

func TestLiveSearchStickers(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchStickers(context.Background(), mustStruct(t, map[string]any{
		"query": "happy",
		"limit": float64(3),
	}))
	if err != nil {
		t.Fatalf("SearchStickers: %v", err)
	}

	stickers := resp.GetFields()["data"].GetListValue().GetValues()
	if len(stickers) == 0 {
		t.Fatal("expected at least 1 sticker for 'happy' search")
	}

	sticker := stickers[0].GetStructValue().GetFields()
	if sticker["id"].GetStringValue() == "" {
		t.Error("sticker missing id")
	}
}

func TestLiveTrendingStickers(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.TrendingStickers(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(3),
	}))
	if err != nil {
		t.Fatalf("TrendingStickers: %v", err)
	}

	stickers := resp.GetFields()["data"].GetListValue().GetValues()
	if len(stickers) == 0 {
		t.Fatal("expected at least 1 trending sticker")
	}
}

func TestLiveRandomSticker(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.RandomSticker(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("RandomSticker: %v", err)
	}

	sticker := resp.GetFields()["data"].GetStructValue().GetFields()
	if sticker["id"].GetStringValue() == "" {
		t.Error("random sticker missing id")
	}
}

func TestLiveGetCategories(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetCategories(context.Background(), mustStruct(t, map[string]any{
		"limit": float64(5),
	}))
	if err != nil {
		t.Fatalf("GetCategories: %v", err)
	}

	cats := resp.GetFields()["data"].GetListValue().GetValues()
	if len(cats) == 0 {
		t.Fatal("expected at least 1 category")
	}

	cat := cats[0].GetStructValue().GetFields()
	if cat["name"].GetStringValue() == "" {
		t.Error("category missing name")
	}
}

func TestLiveSearchWithPagination(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp1, err := svc.Search(context.Background(), mustStruct(t, map[string]any{
		"query":  "dogs",
		"limit":  float64(2),
		"offset": float64(0),
	}))
	if err != nil {
		t.Fatalf("Search page 1: %v", err)
	}

	resp2, err := svc.Search(context.Background(), mustStruct(t, map[string]any{
		"query":  "dogs",
		"limit":  float64(2),
		"offset": float64(2),
	}))
	if err != nil {
		t.Fatalf("Search page 2: %v", err)
	}

	gifs1 := resp1.GetFields()["data"].GetListValue().GetValues()
	gifs2 := resp2.GetFields()["data"].GetListValue().GetValues()
	if len(gifs1) == 0 || len(gifs2) == 0 {
		t.Skip("not enough results for pagination test")
	}

	id1 := gifs1[0].GetStructValue().GetFields()["id"].GetStringValue()
	id2 := gifs2[0].GetStructValue().GetFields()["id"].GetStringValue()
	if id1 == id2 {
		t.Error("page 1 and page 2 returned the same first gif; expected different offsets")
	}
}
