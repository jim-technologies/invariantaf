package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"

	pb "github.com/jim-technologies/invariantaf/dockerhub/dockerhub/v1"
)

// DockerHubService implements dockerhub.v1.DockerHubService RPCs by calling
// the Docker Hub public API (hub.docker.com/v2).
type DockerHubService struct {
	baseURL string
	client  *http.Client
}

// NewDockerHubService creates a service pointing at the real Docker Hub API.
func NewDockerHubService() *DockerHubService {
	return &DockerHubService{
		baseURL: "https://hub.docker.com",
		client:  &http.Client{},
	}
}

// get fetches a JSON response from the Docker Hub API.
func (s *DockerHubService) get(path string, params url.Values) (map[string]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	resp, err := s.client.Get(u)
	if err != nil {
		return nil, fmt.Errorf("http get %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("docker hub api returned %d: %s", resp.StatusCode, string(body))
	}
	var result map[string]any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json: %w", err)
	}
	return result, nil
}

// getString fetches a plain text response from the Docker Hub API.
func (s *DockerHubService) getString(path string) (string, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	resp, err := s.client.Get(u)
	if err != nil {
		return "", fmt.Errorf("http get %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("docker hub api returned %d: %s", resp.StatusCode, string(body))
	}
	return string(body), nil
}

// getList fetches a JSON array response from the Docker Hub API.
func (s *DockerHubService) getList(path string, params url.Values) ([]any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	resp, err := s.client.Get(u)
	if err != nil {
		return nil, fmt.Errorf("http get %s: %w", u, err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("docker hub api returned %d: %s", resp.StatusCode, string(body))
	}
	var result []any
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode json array: %w", err)
	}
	return result, nil
}

func paginationParams(pageSize, page int32) url.Values {
	params := url.Values{}
	if pageSize > 0 {
		params.Set("page_size", strconv.Itoa(int(pageSize)))
	}
	if page > 0 {
		params.Set("page", strconv.Itoa(int(page)))
	}
	return params
}

func toStr(v any) string {
	if v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	default:
		return fmt.Sprintf("%v", v)
	}
}

func toInt32(v any) int32 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return int32(f)
	}
	return 0
}

func toInt64(v any) int64 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return int64(f)
	}
	return 0
}

func toBool(v any) bool {
	if v == nil {
		return false
	}
	if b, ok := v.(bool); ok {
		return b
	}
	return false
}

func toMap(v any) map[string]any {
	if v == nil {
		return nil
	}
	if m, ok := v.(map[string]any); ok {
		return m
	}
	return nil
}

func toSlice(v any) []any {
	if v == nil {
		return nil
	}
	if s, ok := v.([]any); ok {
		return s
	}
	return nil
}

// SearchRepositories searches Docker Hub for repositories matching a query.
func (s *DockerHubService) SearchRepositories(_ context.Context, req *pb.SearchRepositoriesRequest) (*pb.SearchRepositoriesResponse, error) {
	params := paginationParams(req.GetPageSize(), req.GetPage())
	if req.GetQuery() != "" {
		params.Set("query", req.GetQuery())
	}
	data, err := s.get("/v2/search/repositories", params)
	if err != nil {
		return nil, err
	}

	resp := &pb.SearchRepositoriesResponse{
		Count: toInt32(data["count"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.RepositorySearchResult{
			RepoName:         toStr(m["repo_name"]),
			ShortDescription: toStr(m["short_description"]),
			StarCount:        toInt32(m["star_count"]),
			PullCount:        toInt64(m["pull_count"]),
			IsOfficial:       toBool(m["is_official"]),
			IsAutomated:      toBool(m["is_automated"]),
		})
	}
	return resp, nil
}

// GetRepository gets detailed information about a specific repository.
func (s *DockerHubService) GetRepository(_ context.Context, req *pb.GetRepositoryRequest) (*pb.GetRepositoryResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s/%s", req.GetNamespace(), req.GetName())
	data, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetRepositoryResponse{
		Namespace:       toStr(data["namespace"]),
		Name:            toStr(data["name"]),
		FullDescription: toStr(data["full_description"]),
		Description:     toStr(data["description"]),
		StarCount:       toInt32(data["star_count"]),
		PullCount:       toInt64(data["pull_count"]),
		LastUpdated:     toStr(data["last_updated"]),
		IsOfficial:      toBool(data["is_official"]),
		IsAutomated:     toBool(data["is_automated"]),
		Status:          toInt32(data["status"]),
	}, nil
}

// GetTags lists tags for a repository.
func (s *DockerHubService) GetTags(_ context.Context, req *pb.GetTagsRequest) (*pb.GetTagsResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s/%s/tags", req.GetNamespace(), req.GetName())
	params := paginationParams(req.GetPageSize(), req.GetPage())
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetTagsResponse{
		Count:    toInt32(data["count"]),
		Next:     toStr(data["next"]),
		Previous: toStr(data["previous"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.Tag{
			Name:        toStr(m["name"]),
			FullSize:    toInt64(m["full_size"]),
			LastUpdated: toStr(m["last_updated"]),
			Digest:      toStr(m["digest"]),
		})
	}
	return resp, nil
}

// GetTag gets a specific tag for a repository.
func (s *DockerHubService) GetTag(_ context.Context, req *pb.GetTagRequest) (*pb.GetTagResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s/%s/tags/%s", req.GetNamespace(), req.GetName(), req.GetTag())
	data, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetTagResponse{
		Name:        toStr(data["name"]),
		FullSize:    toInt64(data["full_size"]),
		LastUpdated: toStr(data["last_updated"]),
		Digest:      toStr(data["digest"]),
	}, nil
}

// GetNamespaceRepositories lists repositories in a namespace.
func (s *DockerHubService) GetNamespaceRepositories(_ context.Context, req *pb.GetNamespaceRepositoriesRequest) (*pb.GetNamespaceRepositoriesResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s", req.GetNamespace())
	params := paginationParams(req.GetPageSize(), req.GetPage())
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetNamespaceRepositoriesResponse{
		Count:    toInt32(data["count"]),
		Next:     toStr(data["next"]),
		Previous: toStr(data["previous"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.NamespaceRepository{
			Name:        toStr(m["name"]),
			Namespace:   toStr(m["namespace"]),
			Description: toStr(m["description"]),
			StarCount:   toInt32(m["star_count"]),
			PullCount:   toInt64(m["pull_count"]),
			LastUpdated: toStr(m["last_updated"]),
			IsOfficial:  toBool(m["is_official"]),
		})
	}
	return resp, nil
}

// GetTopImages gets the most popular official Docker images.
func (s *DockerHubService) GetTopImages(_ context.Context, req *pb.GetTopImagesRequest) (*pb.GetTopImagesResponse, error) {
	params := paginationParams(req.GetPageSize(), req.GetPage())
	data, err := s.get("/v2/repositories/library", params)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetTopImagesResponse{
		Count:    toInt32(data["count"]),
		Next:     toStr(data["next"]),
		Previous: toStr(data["previous"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.NamespaceRepository{
			Name:        toStr(m["name"]),
			Namespace:   toStr(m["namespace"]),
			Description: toStr(m["description"]),
			StarCount:   toInt32(m["star_count"]),
			PullCount:   toInt64(m["pull_count"]),
			LastUpdated: toStr(m["last_updated"]),
			IsOfficial:  toBool(m["is_official"]),
		})
	}
	return resp, nil
}

// GetBuildHistory gets automated build history for a repository.
func (s *DockerHubService) GetBuildHistory(_ context.Context, req *pb.GetBuildHistoryRequest) (*pb.GetBuildHistoryResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s/%s/buildhistory", req.GetNamespace(), req.GetName())
	params := paginationParams(req.GetPageSize(), req.GetPage())
	data, err := s.get(path, params)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetBuildHistoryResponse{
		Count: toInt32(data["count"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.BuildRecord{
			Id:          toStr(m["id"]),
			Status:      toStr(m["status"]),
			CreatedDate: toStr(m["created_date"]),
			LastUpdated: toStr(m["last_updated"]),
			BuildTag:    toStr(m["build_tag"]),
		})
	}
	return resp, nil
}

// GetDockerfileContent gets the Dockerfile content for a repository.
func (s *DockerHubService) GetDockerfileContent(_ context.Context, req *pb.GetDockerfileContentRequest) (*pb.GetDockerfileContentResponse, error) {
	path := fmt.Sprintf("/v2/repositories/%s/%s/dockerfile", req.GetNamespace(), req.GetName())
	data, err := s.get(path, nil)
	if err != nil {
		return nil, err
	}
	return &pb.GetDockerfileContentResponse{
		Contents: toStr(data["contents"]),
	}, nil
}

// GetCategories gets Docker Hub content categories.
func (s *DockerHubService) GetCategories(_ context.Context, _ *pb.GetCategoriesRequest) (*pb.GetCategoriesResponse, error) {
	items, err := s.getList("/v2/categories", nil)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetCategoriesResponse{}
	for _, item := range items {
		m := toMap(item)
		resp.Categories = append(resp.Categories, &pb.Category{
			Name: toStr(m["name"]),
			Slug: toStr(m["slug"]),
		})
	}
	return resp, nil
}

// GetExtensions gets the Docker extensions catalog.
func (s *DockerHubService) GetExtensions(_ context.Context, req *pb.GetExtensionsRequest) (*pb.GetExtensionsResponse, error) {
	params := paginationParams(req.GetPageSize(), req.GetPage())
	data, err := s.get("/v2/extensions", params)
	if err != nil {
		return nil, err
	}

	resp := &pb.GetExtensionsResponse{
		Count: toInt32(data["count"]),
	}
	for _, item := range toSlice(data["results"]) {
		m := toMap(item)
		resp.Results = append(resp.Results, &pb.Extension{
			Name:        toStr(m["name"]),
			Slug:        toStr(m["slug"]),
			Description: toStr(m["description"]),
			Publisher:   toStr(m["publisher"]),
			CreatedAt:   toStr(m["created_at"]),
			UpdatedAt:   toStr(m["updated_at"]),
		})
	}
	return resp, nil
}
