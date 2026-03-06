package main

import (
	"compress/gzip"
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

// StackExchangeService implements the StackExchangeService RPCs defined in the
// proto descriptor. Each method takes a structpb.Struct request and returns a
// structpb.Struct response, allowing the invariant protocol SDK to handle
// serialization/deserialization transparently.
type StackExchangeService struct {
	baseURL string
	key     string // optional API key for higher rate limits
	client  *http.Client
}

// NewStackExchangeService creates a new service with default settings.
// Set STACKEXCHANGE_API_KEY environment variable for higher rate limits.
func NewStackExchangeService() *StackExchangeService {
	return &StackExchangeService{
		baseURL: "https://api.stackexchange.com/2.3",
		key:     os.Getenv("STACKEXCHANGE_API_KEY"),
		client:  &http.Client{},
	}
}

// get performs a GET request to the Stack Exchange API, handling gzip decompression.
func (s *StackExchangeService) get(path string, params url.Values) (map[string]any, error) {
	if s.key != "" {
		params.Set("key", s.key)
	}
	u := fmt.Sprintf("%s%s?%s", s.baseURL, path, params.Encode())
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Accept-Encoding", "gzip")

	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	var reader io.Reader = resp.Body
	if resp.Header.Get("Content-Encoding") == "gzip" {
		gr, err := gzip.NewReader(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("gzip reader: %w", err)
		}
		defer gr.Close()
		reader = gr
	}

	var result map[string]any
	if err := json.NewDecoder(reader).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}

	if errMsg, ok := result["error_message"]; ok {
		return nil, fmt.Errorf("API error: %v", errMsg)
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

// helper: add pagination params.
func addPagination(params url.Values, fields map[string]*structpb.Value) {
	if p := getInt(fields, "page"); p > 0 {
		params.Set("page", strconv.FormatInt(p, 10))
	}
	if ps := getInt(fields, "pagesize"); ps > 0 {
		params.Set("pagesize", strconv.FormatInt(ps, 10))
	}
}

// helper: add filter param.
func addFilter(params url.Values, fields map[string]*structpb.Value) {
	if f := getString(fields, "filter", ""); f != "" {
		params.Set("filter", f)
	}
}

// helper: convert API response to structpb.Struct.
func toStruct(data map[string]any) (*structpb.Struct, error) {
	result, err := structpb.NewStruct(data)
	if err != nil {
		return nil, fmt.Errorf("convert to struct: %w", err)
	}
	return result, nil
}

// SearchQuestions searches for questions matching a query string.
func (s *StackExchangeService) SearchQuestions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	if intitle := getString(fields, "intitle", ""); intitle != "" {
		params.Set("intitle", intitle)
	}
	if tagged := getString(fields, "tagged", ""); tagged != "" {
		params.Set("tagged", tagged)
	}
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	data, err := s.get("/search", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetQuestion gets a single question by its numeric ID.
func (s *StackExchangeService) GetQuestion(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getInt(fields, "id")
	if id == 0 {
		return nil, fmt.Errorf("id is required")
	}

	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))
	addFilter(params, fields)

	path := fmt.Sprintf("/questions/%d", id)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	// Extract the first item as the question.
	result := map[string]any{}
	if items, ok := data["items"].([]any); ok && len(items) > 0 {
		result["question"] = items[0]
	}
	return toStruct(result)
}

// GetAnswers gets the answers posted to a specific question.
func (s *StackExchangeService) GetAnswers(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	questionID := getInt(fields, "question_id")
	if questionID == 0 {
		return nil, fmt.Errorf("question_id is required")
	}

	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	path := fmt.Sprintf("/questions/%d/answers", questionID)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetUser gets a user's profile by their numeric user ID.
func (s *StackExchangeService) GetUser(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getInt(fields, "id")
	if id == 0 {
		return nil, fmt.Errorf("id is required")
	}

	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	path := fmt.Sprintf("/users/%d", id)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	// Extract the first item as the user.
	result := map[string]any{}
	if items, ok := data["items"].([]any); ok && len(items) > 0 {
		result["user"] = items[0]
	}
	return toStruct(result)
}

// GetTags gets popular tags on a Stack Exchange site.
func (s *StackExchangeService) GetTags(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	if inname := getString(fields, "inname", ""); inname != "" {
		params.Set("inname", inname)
	}
	addPagination(params, fields)

	data, err := s.get("/tags", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetTopQuestions gets top questions, optionally filtered by tag.
func (s *StackExchangeService) GetTopQuestions(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	if tagged := getString(fields, "tagged", ""); tagged != "" {
		params.Set("tagged", tagged)
	}
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	data, err := s.get("/questions", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// SearchAdvanced performs an advanced search with multiple filters.
func (s *StackExchangeService) SearchAdvanced(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	if q := getString(fields, "q", ""); q != "" {
		params.Set("q", q)
	}
	if title := getString(fields, "title", ""); title != "" {
		params.Set("title", title)
	}
	if tagged := getString(fields, "tagged", ""); tagged != "" {
		params.Set("tagged", tagged)
	}
	if nottagged := getString(fields, "nottagged", ""); nottagged != "" {
		params.Set("nottagged", nottagged)
	}
	if v, ok := fields["accepted"]; ok {
		params.Set("accepted", strconv.FormatBool(v.GetBoolValue()))
	}
	if answers := getInt(fields, "answers"); answers > 0 {
		params.Set("answers", strconv.FormatInt(answers, 10))
	}
	if views := getInt(fields, "views"); views > 0 {
		params.Set("views", strconv.FormatInt(views, 10))
	}
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	data, err := s.get("/search/advanced", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetUserReputation gets a user's reputation change history.
func (s *StackExchangeService) GetUserReputation(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	id := getInt(fields, "id")
	if id == 0 {
		return nil, fmt.Errorf("id is required")
	}

	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))
	addPagination(params, fields)

	path := fmt.Sprintf("/users/%d/reputation", id)
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetSimilar finds questions similar to a given title.
func (s *StackExchangeService) GetSimilar(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	title := getString(fields, "title", "")
	if title == "" {
		return nil, fmt.Errorf("title is required")
	}

	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))
	params.Set("title", title)

	if tagged := getString(fields, "tagged", ""); tagged != "" {
		params.Set("tagged", tagged)
	}
	if nottagged := getString(fields, "nottagged", ""); nottagged != "" {
		params.Set("nottagged", nottagged)
	}
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	data, err := s.get("/similar", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}

// GetUnanswered gets unanswered questions, optionally filtered by tag.
func (s *StackExchangeService) GetUnanswered(_ context.Context, req *structpb.Struct) (*structpb.Struct, error) {
	fields := req.GetFields()
	params := url.Values{}
	params.Set("site", getString(fields, "site", "stackoverflow"))

	if tagged := getString(fields, "tagged", ""); tagged != "" {
		params.Set("tagged", tagged)
	}
	if sort := getString(fields, "sort", ""); sort != "" {
		params.Set("sort", sort)
		params.Set("order", "desc")
	}
	addPagination(params, fields)
	addFilter(params, fields)

	data, err := s.get("/questions/unanswered", params)
	if err != nil {
		return nil, err
	}
	return toStruct(data)
}
