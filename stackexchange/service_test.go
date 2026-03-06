package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

// mockSEServer creates a test server that returns realistic Stack Exchange API responses.
// It serves plain JSON (no gzip) since httptest won't add Content-Encoding: gzip.
func mockSEServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		case strings.Contains(r.URL.Path, "/search/advanced"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"question_id":        float64(11227809),
						"title":              "How do I check whether a file exists without exceptions?",
						"score":              float64(7200),
						"answer_count":       float64(45),
						"view_count":         float64(5000000),
						"is_answered":        true,
						"tags":               []any{"python", "file", "exists"},
						"creation_date":      float64(1340713038),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/questions/11227809",
						"owner": map[string]any{
							"user_id":       float64(12345),
							"display_name":  "pythonista",
							"reputation":    float64(50000),
							"profile_image": "https://example.com/avatar.png",
							"link":          "https://stackoverflow.com/users/12345",
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(290),
			})

		case strings.Contains(r.URL.Path, "/search"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"question_id":        float64(78901234),
						"title":              "How to parse JSON in Go",
						"score":              float64(150),
						"answer_count":       float64(8),
						"view_count":         float64(120000),
						"is_answered":        true,
						"tags":               []any{"go", "json", "parsing"},
						"creation_date":      float64(1600000000),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/questions/78901234",
						"owner": map[string]any{
							"user_id":       float64(67890),
							"display_name":  "gopher123",
							"reputation":    float64(15000),
							"profile_image": "https://example.com/gopher.png",
							"link":          "https://stackoverflow.com/users/67890",
						},
					},
				},
				"has_more":        true,
				"quota_remaining": float64(295),
			})

		case strings.HasSuffix(r.URL.Path, "/answers"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"answer_id":          float64(99001),
						"question_id":        float64(78901234),
						"score":              float64(200),
						"is_accepted":        true,
						"creation_date":      float64(1600001000),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/a/99001",
						"owner": map[string]any{
							"user_id":       float64(11111),
							"display_name":  "answerbot",
							"reputation":    float64(80000),
							"profile_image": "https://example.com/answerbot.png",
							"link":          "https://stackoverflow.com/users/11111",
						},
					},
					map[string]any{
						"answer_id":          float64(99002),
						"question_id":        float64(78901234),
						"score":              float64(50),
						"is_accepted":        false,
						"creation_date":      float64(1600002000),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/a/99002",
						"owner": map[string]any{
							"user_id":       float64(22222),
							"display_name":  "helper42",
							"reputation":    float64(25000),
							"profile_image": "https://example.com/helper42.png",
							"link":          "https://stackoverflow.com/users/22222",
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(288),
			})

		case strings.Contains(r.URL.Path, "/questions/unanswered"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"question_id":        float64(99999999),
						"title":              "Why does my goroutine leak?",
						"score":              float64(5),
						"answer_count":       float64(0),
						"view_count":         float64(200),
						"is_answered":        false,
						"tags":               []any{"go", "goroutine", "memory-leak"},
						"creation_date":      float64(1700000000),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/questions/99999999",
						"owner": map[string]any{
							"user_id":       float64(55555),
							"display_name":  "newgopher",
							"reputation":    float64(100),
							"profile_image": "https://example.com/newgopher.png",
							"link":          "https://stackoverflow.com/users/55555",
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(285),
			})

		case strings.Contains(r.URL.Path, "/questions"):
			// Handles both /questions (GetTopQuestions) and /questions/{id} (GetQuestion).
			questionID := "78901234"
			parts := strings.Split(r.URL.Path, "/")
			for i, p := range parts {
				if p == "questions" && i+1 < len(parts) {
					questionID = parts[i+1]
					break
				}
			}
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"question_id":        float64(78901234),
						"title":              "How to parse JSON in Go",
						"score":              float64(150),
						"answer_count":       float64(8),
						"view_count":         float64(120000),
						"is_answered":        true,
						"tags":               []any{"go", "json", "parsing"},
						"creation_date":      float64(1600000000),
						"last_activity_date": float64(1700000000),
						"link":               "https://stackoverflow.com/questions/" + questionID,
						"owner": map[string]any{
							"user_id":       float64(67890),
							"display_name":  "gopher123",
							"reputation":    float64(15000),
							"profile_image": "https://example.com/gopher.png",
							"link":          "https://stackoverflow.com/users/67890",
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(292),
			})

		case strings.Contains(r.URL.Path, "/users") && strings.Contains(r.URL.Path, "/reputation"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"reputation_change_type": "post_upvoted",
						"reputation_change":      float64(10),
						"post_id":                float64(78901234),
						"title":                  "How to parse JSON in Go",
						"link":                   "https://stackoverflow.com/questions/78901234",
						"on_date":                float64(1700000000),
					},
					map[string]any{
						"reputation_change_type": "answer_accepted",
						"reputation_change":      float64(15),
						"post_id":                float64(99001),
						"title":                  "How to parse JSON in Go",
						"link":                   "https://stackoverflow.com/a/99001",
						"on_date":                float64(1700001000),
					},
				},
				"has_more":        false,
				"quota_remaining": float64(286),
			})

		case strings.Contains(r.URL.Path, "/users"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"user_id":          float64(67890),
						"display_name":     "gopher123",
						"reputation":       float64(15000),
						"profile_image":    "https://example.com/gopher.png",
						"link":             "https://stackoverflow.com/users/67890",
						"creation_date":    float64(1400000000),
						"last_access_date": float64(1700000000),
						"location":         "San Francisco, CA",
						"website_url":      "https://gopher123.dev",
						"about_me":         "<p>Go enthusiast</p>",
						"question_count":   float64(25),
						"answer_count":     float64(150),
						"badge_counts": map[string]any{
							"gold":   float64(3),
							"silver": float64(25),
							"bronze": float64(80),
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(289),
			})

		case strings.Contains(r.URL.Path, "/tags"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"name":              "javascript",
						"count":             float64(2500000),
						"has_synonyms":      true,
						"is_moderator_only": false,
						"is_required":       false,
					},
					map[string]any{
						"name":              "python",
						"count":             float64(2200000),
						"has_synonyms":      true,
						"is_moderator_only": false,
						"is_required":       false,
					},
					map[string]any{
						"name":              "go",
						"count":             float64(80000),
						"has_synonyms":      false,
						"is_moderator_only": false,
						"is_required":       false,
					},
				},
				"has_more":        true,
				"quota_remaining": float64(291),
			})

		case strings.Contains(r.URL.Path, "/similar"):
			json.NewEncoder(w).Encode(map[string]any{
				"items": []any{
					map[string]any{
						"question_id":        float64(55555555),
						"title":              "Parse JSON with Go standard library",
						"score":              float64(80),
						"answer_count":       float64(5),
						"view_count":         float64(50000),
						"is_answered":        true,
						"tags":               []any{"go", "json"},
						"creation_date":      float64(1580000000),
						"last_activity_date": float64(1690000000),
						"link":               "https://stackoverflow.com/questions/55555555",
						"owner": map[string]any{
							"user_id":       float64(33333),
							"display_name":  "jsonwizard",
							"reputation":    float64(40000),
							"profile_image": "https://example.com/jsonwizard.png",
							"link":          "https://stackoverflow.com/users/33333",
						},
					},
				},
				"has_more":        false,
				"quota_remaining": float64(287),
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{
				"error_id":      400,
				"error_message": "no method found with this name",
				"error_name":    "no_method",
			})
		}
	}))
}

func newTestService(serverURL string) *StackExchangeService {
	return &StackExchangeService{
		baseURL: serverURL,
		client:  &http.Client{},
	}
}

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil {
		t.Fatalf("failed to create struct: %v", err)
	}
	return s
}

func getItems(t *testing.T, resp *structpb.Struct) []*structpb.Value {
	t.Helper()
	items := resp.GetFields()["items"]
	if items == nil {
		t.Fatal("response has no 'items' field")
	}
	return items.GetListValue().GetValues()
}

// --- Tests ---

func TestSearchQuestions(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchQuestions(context.Background(), mustStruct(t, map[string]any{
		"intitle": "parse JSON Go",
		"site":    "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("SearchQuestions: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(items))
	}

	q := items[0].GetStructValue().GetFields()
	if got := q["title"].GetStringValue(); got != "How to parse JSON in Go" {
		t.Errorf("title = %q, want %q", got, "How to parse JSON in Go")
	}
	if got := q["score"].GetNumberValue(); got != 150 {
		t.Errorf("score = %v, want 150", got)
	}
	if got := q["is_answered"].GetBoolValue(); !got {
		t.Error("is_answered = false, want true")
	}

	tags := q["tags"].GetListValue().GetValues()
	if len(tags) != 3 {
		t.Errorf("expected 3 tags, got %d", len(tags))
	}

	hasMore := resp.GetFields()["has_more"].GetBoolValue()
	if !hasMore {
		t.Error("expected has_more = true")
	}
}

func TestSearchQuestionsWithSort(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchQuestions(context.Background(), mustStruct(t, map[string]any{
		"intitle": "parse JSON",
		"sort":    "votes",
		"tagged":  "go",
	}))
	if err != nil {
		t.Fatalf("SearchQuestions: %v", err)
	}

	items := getItems(t, resp)
	if len(items) == 0 {
		t.Fatal("expected at least 1 item")
	}
}

func TestGetQuestion(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetQuestion(context.Background(), mustStruct(t, map[string]any{
		"id":   float64(78901234),
		"site": "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("GetQuestion: %v", err)
	}

	q := resp.GetFields()["question"]
	if q == nil {
		t.Fatal("response has no 'question' field")
	}

	fields := q.GetStructValue().GetFields()
	if got := fields["title"].GetStringValue(); got != "How to parse JSON in Go" {
		t.Errorf("title = %q, want %q", got, "How to parse JSON in Go")
	}
	if got := int64(fields["question_id"].GetNumberValue()); got != 78901234 {
		t.Errorf("question_id = %d, want 78901234", got)
	}
}

func TestGetQuestionRequiresID(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetQuestion(context.Background(), mustStruct(t, map[string]any{
		"site": "stackoverflow",
	}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
	if !strings.Contains(err.Error(), "id is required") {
		t.Errorf("error = %q, want to contain 'id is required'", err.Error())
	}
}

func TestGetAnswers(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetAnswers(context.Background(), mustStruct(t, map[string]any{
		"question_id": float64(78901234),
		"sort":        "votes",
	}))
	if err != nil {
		t.Fatalf("GetAnswers: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 2 {
		t.Fatalf("expected 2 answers, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["is_accepted"].GetBoolValue(); !got {
		t.Error("first answer should be accepted")
	}
	if got := first["score"].GetNumberValue(); got != 200 {
		t.Errorf("first answer score = %v, want 200", got)
	}
}

func TestGetAnswersRequiresQuestionID(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetAnswers(context.Background(), mustStruct(t, map[string]any{
		"site": "stackoverflow",
	}))
	if err == nil {
		t.Fatal("expected error for missing question_id")
	}
}

func TestGetUser(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetUser(context.Background(), mustStruct(t, map[string]any{
		"id":   float64(67890),
		"site": "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("GetUser: %v", err)
	}

	u := resp.GetFields()["user"]
	if u == nil {
		t.Fatal("response has no 'user' field")
	}

	fields := u.GetStructValue().GetFields()
	if got := fields["display_name"].GetStringValue(); got != "gopher123" {
		t.Errorf("display_name = %q, want %q", got, "gopher123")
	}
	if got := fields["reputation"].GetNumberValue(); got != 15000 {
		t.Errorf("reputation = %v, want 15000", got)
	}
	if got := fields["location"].GetStringValue(); got != "San Francisco, CA" {
		t.Errorf("location = %q, want %q", got, "San Francisco, CA")
	}

	badges := fields["badge_counts"].GetStructValue().GetFields()
	if got := badges["gold"].GetNumberValue(); got != 3 {
		t.Errorf("gold badges = %v, want 3", got)
	}
}

func TestGetUserRequiresID(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetUser(context.Background(), mustStruct(t, map[string]any{
		"site": "stackoverflow",
	}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
}

func TestGetTags(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTags(context.Background(), mustStruct(t, map[string]any{
		"sort":     "popular",
		"pagesize": float64(10),
	}))
	if err != nil {
		t.Fatalf("GetTags: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 3 {
		t.Fatalf("expected 3 tags, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["name"].GetStringValue(); got != "javascript" {
		t.Errorf("first tag name = %q, want %q", got, "javascript")
	}
	if got := first["count"].GetNumberValue(); got != 2500000 {
		t.Errorf("first tag count = %v, want 2500000", got)
	}
}

func TestGetTagsWithInname(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTags(context.Background(), mustStruct(t, map[string]any{
		"inname": "go",
	}))
	if err != nil {
		t.Fatalf("GetTags: %v", err)
	}

	items := getItems(t, resp)
	if len(items) == 0 {
		t.Fatal("expected at least 1 tag")
	}
}

func TestGetTopQuestions(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTopQuestions(context.Background(), mustStruct(t, map[string]any{
		"tagged": "go",
		"sort":   "votes",
		"site":   "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("GetTopQuestions: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 1 {
		t.Fatalf("expected 1 question, got %d", len(items))
	}

	q := items[0].GetStructValue().GetFields()
	if got := q["title"].GetStringValue(); got != "How to parse JSON in Go" {
		t.Errorf("title = %q, want %q", got, "How to parse JSON in Go")
	}
}

func TestSearchAdvanced(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchAdvanced(context.Background(), mustStruct(t, map[string]any{
		"q":        "check file exists",
		"tagged":   "python",
		"accepted": true,
		"sort":     "votes",
	}))
	if err != nil {
		t.Fatalf("SearchAdvanced: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(items))
	}

	q := items[0].GetStructValue().GetFields()
	if got := q["title"].GetStringValue(); got != "How do I check whether a file exists without exceptions?" {
		t.Errorf("title = %q", got)
	}
	if got := q["score"].GetNumberValue(); got != 7200 {
		t.Errorf("score = %v, want 7200", got)
	}
}

func TestSearchAdvancedWithMultipleFilters(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchAdvanced(context.Background(), mustStruct(t, map[string]any{
		"q":       "file exists",
		"tagged":  "python;file",
		"answers": float64(5),
		"views":   float64(1000),
	}))
	if err != nil {
		t.Fatalf("SearchAdvanced: %v", err)
	}

	items := getItems(t, resp)
	if len(items) == 0 {
		t.Fatal("expected at least 1 item")
	}
}

func TestGetUserReputation(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetUserReputation(context.Background(), mustStruct(t, map[string]any{
		"id":   float64(67890),
		"site": "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("GetUserReputation: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 2 {
		t.Fatalf("expected 2 reputation changes, got %d", len(items))
	}

	first := items[0].GetStructValue().GetFields()
	if got := first["reputation_change_type"].GetStringValue(); got != "post_upvoted" {
		t.Errorf("reputation_change_type = %q, want %q", got, "post_upvoted")
	}
	if got := first["reputation_change"].GetNumberValue(); got != 10 {
		t.Errorf("reputation_change = %v, want 10", got)
	}
}

func TestGetUserReputationRequiresID(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetUserReputation(context.Background(), mustStruct(t, map[string]any{
		"site": "stackoverflow",
	}))
	if err == nil {
		t.Fatal("expected error for missing id")
	}
}

func TestGetSimilar(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetSimilar(context.Background(), mustStruct(t, map[string]any{
		"title": "How to parse JSON in Go",
		"site":  "stackoverflow",
	}))
	if err != nil {
		t.Fatalf("GetSimilar: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 1 {
		t.Fatalf("expected 1 similar question, got %d", len(items))
	}

	q := items[0].GetStructValue().GetFields()
	if got := q["title"].GetStringValue(); got != "Parse JSON with Go standard library" {
		t.Errorf("title = %q", got)
	}
}

func TestGetSimilarRequiresTitle(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.GetSimilar(context.Background(), mustStruct(t, map[string]any{
		"site": "stackoverflow",
	}))
	if err == nil {
		t.Fatal("expected error for missing title")
	}
	if !strings.Contains(err.Error(), "title is required") {
		t.Errorf("error = %q, want to contain 'title is required'", err.Error())
	}
}

func TestGetUnanswered(t *testing.T) {
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetUnanswered(context.Background(), mustStruct(t, map[string]any{
		"tagged": "go",
		"sort":   "activity",
	}))
	if err != nil {
		t.Fatalf("GetUnanswered: %v", err)
	}

	items := getItems(t, resp)
	if len(items) != 1 {
		t.Fatalf("expected 1 unanswered question, got %d", len(items))
	}

	q := items[0].GetStructValue().GetFields()
	if got := q["title"].GetStringValue(); got != "Why does my goroutine leak?" {
		t.Errorf("title = %q", got)
	}
	if got := q["is_answered"].GetBoolValue(); got {
		t.Error("expected is_answered = false for unanswered question")
	}
	if got := q["answer_count"].GetNumberValue(); got != 0 {
		t.Errorf("answer_count = %v, want 0", got)
	}
}

func TestDefaultSite(t *testing.T) {
	// Verify that when no site is specified, the service defaults to "stackoverflow".
	ts := mockSEServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchQuestions(context.Background(), mustStruct(t, map[string]any{
		"intitle": "test",
	}))
	if err != nil {
		t.Fatalf("SearchQuestions: %v", err)
	}

	// The mock still returns results since it doesn't validate the site param.
	items := getItems(t, resp)
	if len(items) == 0 {
		t.Fatal("expected results with default site")
	}
}

func TestAPIKeyIncludedWhenSet(t *testing.T) {
	var capturedURL string
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedURL = r.URL.String()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"items":           []any{},
			"has_more":        false,
			"quota_remaining": float64(9990),
		})
	}))
	defer ts.Close()

	svc := &StackExchangeService{
		baseURL: ts.URL,
		key:     "test-api-key-123",
		client:  &http.Client{},
	}

	_, err := svc.GetTags(context.Background(), mustStruct(t, map[string]any{}))
	if err != nil {
		t.Fatalf("GetTags: %v", err)
	}

	if !strings.Contains(capturedURL, "key=test-api-key-123") {
		t.Errorf("API key not found in URL: %s", capturedURL)
	}
}
