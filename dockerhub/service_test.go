package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	pb "github.com/jim-technologies/invariantaf/dockerhub/dockerhub/v1"
)

func mockDockerHubServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch {
		// SearchRepositories
		case strings.Contains(r.URL.Path, "/v2/search/repositories"):
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(1),
				"results": []any{
					map[string]any{
						"repo_name":         "library/nginx",
						"short_description": "Official Nginx image",
						"star_count":        float64(18000),
						"pull_count":        float64(1000000000),
						"is_official":       true,
						"is_automated":      false,
					},
				},
			})

		// GetTag (specific tag - must match before /tags)
		case strings.Contains(r.URL.Path, "/tags/") && !strings.HasSuffix(r.URL.Path, "/tags"):
			json.NewEncoder(w).Encode(map[string]any{
				"name":         "latest",
				"full_size":    float64(50000000),
				"last_updated": "2025-01-15T10:00:00Z",
				"digest":       "sha256:abc123def456",
			})

		// GetTags (list tags)
		case strings.HasSuffix(r.URL.Path, "/tags"):
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(2),
				"next":  "https://hub.docker.com/v2/repositories/library/nginx/tags?page=2",
				"results": []any{
					map[string]any{
						"name":         "latest",
						"full_size":    float64(50000000),
						"last_updated": "2025-01-15T10:00:00Z",
						"digest":       "sha256:abc123",
					},
					map[string]any{
						"name":         "1.25",
						"full_size":    float64(48000000),
						"last_updated": "2025-01-10T10:00:00Z",
						"digest":       "sha256:def456",
					},
				},
			})

		// GetBuildHistory
		case strings.HasSuffix(r.URL.Path, "/buildhistory"):
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(1),
				"results": []any{
					map[string]any{
						"id":           "build-123",
						"status":       "Success",
						"created_date": "2025-01-14T08:00:00Z",
						"last_updated": "2025-01-14T08:05:00Z",
						"build_tag":    "latest",
					},
				},
			})

		// GetDockerfileContent
		case strings.HasSuffix(r.URL.Path, "/dockerfile"):
			json.NewEncoder(w).Encode(map[string]any{
				"contents": "FROM debian:bookworm-slim\nRUN apt-get update\n",
			})

		// GetCategories
		case r.URL.Path == "/v2/categories":
			json.NewEncoder(w).Encode([]any{
				map[string]any{"name": "Databases", "slug": "databases"},
				map[string]any{"name": "Web Servers", "slug": "web-servers"},
			})

		// GetExtensions
		case r.URL.Path == "/v2/extensions":
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(1),
				"results": []any{
					map[string]any{
						"name":        "Disk Usage",
						"slug":        "docker/disk-usage-extension",
						"description": "View disk space used by Docker",
						"publisher":   "Docker Inc.",
						"created_at":  "2024-06-01T00:00:00Z",
						"updated_at":  "2025-01-10T00:00:00Z",
					},
				},
			})

		// GetTopImages (matches /v2/repositories/library exactly)
		case r.URL.Path == "/v2/repositories/library":
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(2),
				"next":  "https://hub.docker.com/v2/repositories/library?page=2",
				"results": []any{
					map[string]any{
						"name":         "nginx",
						"namespace":    "library",
						"description":  "Official Nginx image",
						"star_count":   float64(18000),
						"pull_count":   float64(1000000000),
						"last_updated": "2025-01-15T10:00:00Z",
						"is_official":  true,
					},
					map[string]any{
						"name":         "postgres",
						"namespace":    "library",
						"description":  "Official PostgreSQL image",
						"star_count":   float64(12000),
						"pull_count":   float64(500000000),
						"last_updated": "2025-01-14T10:00:00Z",
						"is_official":  true,
					},
				},
			})

		// GetRepository (specific repo) - matches /v2/repositories/{ns}/{name}
		case strings.HasPrefix(r.URL.Path, "/v2/repositories/") && strings.Count(r.URL.Path, "/") == 4:
			json.NewEncoder(w).Encode(map[string]any{
				"namespace":        "library",
				"name":             "nginx",
				"full_description": "# Nginx\nOfficial Nginx image with full documentation.",
				"description":      "Official Nginx image",
				"star_count":       float64(18000),
				"pull_count":       float64(1000000000),
				"last_updated":     "2025-01-15T10:00:00Z",
				"is_official":      true,
				"is_automated":     false,
				"status":           float64(1),
			})

		// GetNamespaceRepositories - matches /v2/repositories/{ns}
		case strings.HasPrefix(r.URL.Path, "/v2/repositories/") && strings.Count(r.URL.Path, "/") == 3:
			json.NewEncoder(w).Encode(map[string]any{
				"count": float64(1),
				"results": []any{
					map[string]any{
						"name":         "myapp",
						"namespace":    "myorg",
						"description":  "My application image",
						"star_count":   float64(50),
						"pull_count":   float64(10000),
						"last_updated": "2025-01-15T10:00:00Z",
						"is_official":  false,
					},
				},
			})

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"message": "not found"})
		}
	}))
}

func newTestService(serverURL string) *DockerHubService {
	return &DockerHubService{
		baseURL: serverURL,
		client:  &http.Client{},
	}
}

func TestSearchRepositories(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.SearchRepositories(context.Background(), &pb.SearchRepositoriesRequest{
		Query:    "nginx",
		PageSize: 10,
		Page:     1,
	})
	if err != nil {
		t.Fatalf("SearchRepositories: %v", err)
	}
	if resp.Count != 1 {
		t.Errorf("expected count=1, got %d", resp.Count)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(resp.Results))
	}
	r := resp.Results[0]
	if r.RepoName != "library/nginx" {
		t.Errorf("expected repo_name=library/nginx, got %s", r.RepoName)
	}
	if r.ShortDescription != "Official Nginx image" {
		t.Errorf("expected short_description=Official Nginx image, got %s", r.ShortDescription)
	}
	if r.StarCount != 18000 {
		t.Errorf("expected star_count=18000, got %d", r.StarCount)
	}
	if r.PullCount != 1000000000 {
		t.Errorf("expected pull_count=1000000000, got %d", r.PullCount)
	}
	if !r.IsOfficial {
		t.Error("expected is_official=true")
	}
}

func TestGetRepository(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetRepository(context.Background(), &pb.GetRepositoryRequest{
		Namespace: "library",
		Name:      "nginx",
	})
	if err != nil {
		t.Fatalf("GetRepository: %v", err)
	}
	if resp.Namespace != "library" {
		t.Errorf("expected namespace=library, got %s", resp.Namespace)
	}
	if resp.Name != "nginx" {
		t.Errorf("expected name=nginx, got %s", resp.Name)
	}
	if resp.StarCount != 18000 {
		t.Errorf("expected star_count=18000, got %d", resp.StarCount)
	}
	if resp.PullCount != 1000000000 {
		t.Errorf("expected pull_count=1000000000, got %d", resp.PullCount)
	}
	if !resp.IsOfficial {
		t.Error("expected is_official=true")
	}
	if resp.Status != 1 {
		t.Errorf("expected status=1, got %d", resp.Status)
	}
	if !strings.Contains(resp.FullDescription, "Nginx") {
		t.Errorf("expected full_description to contain Nginx, got %s", resp.FullDescription)
	}
}

func TestGetTags(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTags(context.Background(), &pb.GetTagsRequest{
		Namespace: "library",
		Name:      "nginx",
		PageSize:  10,
	})
	if err != nil {
		t.Fatalf("GetTags: %v", err)
	}
	if resp.Count != 2 {
		t.Errorf("expected count=2, got %d", resp.Count)
	}
	if len(resp.Results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(resp.Results))
	}
	if resp.Results[0].Name != "latest" {
		t.Errorf("expected first tag=latest, got %s", resp.Results[0].Name)
	}
	if resp.Results[0].FullSize != 50000000 {
		t.Errorf("expected full_size=50000000, got %d", resp.Results[0].FullSize)
	}
	if resp.Results[1].Name != "1.25" {
		t.Errorf("expected second tag=1.25, got %s", resp.Results[1].Name)
	}
	if resp.Next == "" {
		t.Error("expected non-empty next URL")
	}
}

func TestGetTag(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTag(context.Background(), &pb.GetTagRequest{
		Namespace: "library",
		Name:      "nginx",
		Tag:       "latest",
	})
	if err != nil {
		t.Fatalf("GetTag: %v", err)
	}
	if resp.Name != "latest" {
		t.Errorf("expected name=latest, got %s", resp.Name)
	}
	if resp.FullSize != 50000000 {
		t.Errorf("expected full_size=50000000, got %d", resp.FullSize)
	}
	if resp.Digest != "sha256:abc123def456" {
		t.Errorf("expected digest=sha256:abc123def456, got %s", resp.Digest)
	}
	if resp.LastUpdated != "2025-01-15T10:00:00Z" {
		t.Errorf("expected last_updated=2025-01-15T10:00:00Z, got %s", resp.LastUpdated)
	}
}

func TestGetNamespaceRepositories(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetNamespaceRepositories(context.Background(), &pb.GetNamespaceRepositoriesRequest{
		Namespace: "myorg",
		PageSize:  10,
	})
	if err != nil {
		t.Fatalf("GetNamespaceRepositories: %v", err)
	}
	if resp.Count != 1 {
		t.Errorf("expected count=1, got %d", resp.Count)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(resp.Results))
	}
	r := resp.Results[0]
	if r.Name != "myapp" {
		t.Errorf("expected name=myapp, got %s", r.Name)
	}
	if r.Namespace != "myorg" {
		t.Errorf("expected namespace=myorg, got %s", r.Namespace)
	}
	if r.PullCount != 10000 {
		t.Errorf("expected pull_count=10000, got %d", r.PullCount)
	}
}

func TestGetTopImages(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetTopImages(context.Background(), &pb.GetTopImagesRequest{
		PageSize: 10,
	})
	if err != nil {
		t.Fatalf("GetTopImages: %v", err)
	}
	if resp.Count != 2 {
		t.Errorf("expected count=2, got %d", resp.Count)
	}
	if len(resp.Results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(resp.Results))
	}
	if resp.Results[0].Name != "nginx" {
		t.Errorf("expected first=nginx, got %s", resp.Results[0].Name)
	}
	if resp.Results[1].Name != "postgres" {
		t.Errorf("expected second=postgres, got %s", resp.Results[1].Name)
	}
	if resp.Next == "" {
		t.Error("expected non-empty next URL")
	}
}

func TestGetBuildHistory(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetBuildHistory(context.Background(), &pb.GetBuildHistoryRequest{
		Namespace: "library",
		Name:      "nginx",
	})
	if err != nil {
		t.Fatalf("GetBuildHistory: %v", err)
	}
	if resp.Count != 1 {
		t.Errorf("expected count=1, got %d", resp.Count)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(resp.Results))
	}
	b := resp.Results[0]
	if b.Id != "build-123" {
		t.Errorf("expected id=build-123, got %s", b.Id)
	}
	if b.Status != "Success" {
		t.Errorf("expected status=Success, got %s", b.Status)
	}
	if b.BuildTag != "latest" {
		t.Errorf("expected build_tag=latest, got %s", b.BuildTag)
	}
}

func TestGetDockerfileContent(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetDockerfileContent(context.Background(), &pb.GetDockerfileContentRequest{
		Namespace: "library",
		Name:      "nginx",
	})
	if err != nil {
		t.Fatalf("GetDockerfileContent: %v", err)
	}
	if !strings.Contains(resp.Contents, "FROM debian:bookworm-slim") {
		t.Errorf("expected Dockerfile content to contain FROM, got %s", resp.Contents)
	}
}

func TestGetCategories(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetCategories(context.Background(), &pb.GetCategoriesRequest{})
	if err != nil {
		t.Fatalf("GetCategories: %v", err)
	}
	if len(resp.Categories) != 2 {
		t.Fatalf("expected 2 categories, got %d", len(resp.Categories))
	}
	if resp.Categories[0].Name != "Databases" {
		t.Errorf("expected first category=Databases, got %s", resp.Categories[0].Name)
	}
	if resp.Categories[0].Slug != "databases" {
		t.Errorf("expected slug=databases, got %s", resp.Categories[0].Slug)
	}
	if resp.Categories[1].Name != "Web Servers" {
		t.Errorf("expected second category=Web Servers, got %s", resp.Categories[1].Name)
	}
}

func TestGetExtensions(t *testing.T) {
	ts := mockDockerHubServer()
	defer ts.Close()
	svc := newTestService(ts.URL)

	resp, err := svc.GetExtensions(context.Background(), &pb.GetExtensionsRequest{
		PageSize: 10,
	})
	if err != nil {
		t.Fatalf("GetExtensions: %v", err)
	}
	if resp.Count != 1 {
		t.Errorf("expected count=1, got %d", resp.Count)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(resp.Results))
	}
	ext := resp.Results[0]
	if ext.Name != "Disk Usage" {
		t.Errorf("expected name=Disk Usage, got %s", ext.Name)
	}
	if ext.Slug != "docker/disk-usage-extension" {
		t.Errorf("expected slug=docker/disk-usage-extension, got %s", ext.Slug)
	}
	if ext.Publisher != "Docker Inc." {
		t.Errorf("expected publisher=Docker Inc., got %s", ext.Publisher)
	}
}

func TestErrorHandling(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte(`{"message": "not found"}`))
	}))
	defer ts.Close()
	svc := newTestService(ts.URL)

	_, err := svc.SearchRepositories(context.Background(), &pb.SearchRepositoriesRequest{
		Query: "nonexistent",
	})
	if err == nil {
		t.Fatal("expected error for 404 response")
	}
	if !strings.Contains(err.Error(), "404") {
		t.Errorf("expected error to contain 404, got %s", err.Error())
	}
}

// --- Live integration tests (hit the real Docker Hub API) ---

func skipUnlessIntegration(t *testing.T) {
	t.Helper()
	if os.Getenv("TEST_DOCKERHUB") == "" {
		t.Skip("set TEST_DOCKERHUB=1 to run integration tests (hits real Docker Hub API)")
	}
}

func liveService() *DockerHubService {
	return NewDockerHubService()
}

func TestLiveSearchRepositories(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchRepositories(context.Background(), &pb.SearchRepositoriesRequest{
		Query:    "nginx",
		PageSize: 5,
		Page:     1,
	})
	if err != nil {
		t.Fatalf("SearchRepositories: %v", err)
	}
	if resp.Count == 0 {
		t.Fatal("expected count > 0")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 result")
	}

	r := resp.Results[0]
	if r.RepoName == "" {
		t.Error("result missing repo_name")
	}
	if r.ShortDescription == "" {
		t.Log("result has empty short_description (may be expected)")
	}
}

func TestLiveGetRepository(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetRepository(context.Background(), &pb.GetRepositoryRequest{
		Namespace: "library",
		Name:      "nginx",
	})
	if err != nil {
		t.Fatalf("GetRepository: %v", err)
	}
	if resp.Name != "nginx" {
		t.Errorf("expected name=nginx, got %s", resp.Name)
	}
	if resp.PullCount == 0 {
		t.Error("expected pull_count > 0 for nginx")
	}
	if resp.StarCount == 0 {
		t.Error("expected star_count > 0 for nginx")
	}
	if resp.Description == "" {
		t.Error("expected non-empty description for nginx")
	}
}

func TestLiveGetTags(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetTags(context.Background(), &pb.GetTagsRequest{
		Namespace: "library",
		Name:      "alpine",
		PageSize:  5,
	})
	if err != nil {
		t.Fatalf("GetTags: %v", err)
	}
	if resp.Count == 0 {
		t.Fatal("expected count > 0 for alpine tags")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 tag")
	}

	tag := resp.Results[0]
	if tag.Name == "" {
		t.Error("tag missing name")
	}
	if tag.LastUpdated == "" {
		t.Error("tag missing last_updated")
	}
}

func TestLiveGetTag(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetTag(context.Background(), &pb.GetTagRequest{
		Namespace: "library",
		Name:      "alpine",
		Tag:       "latest",
	})
	if err != nil {
		t.Fatalf("GetTag: %v", err)
	}
	if resp.Name != "latest" {
		t.Errorf("expected name=latest, got %s", resp.Name)
	}
	if resp.LastUpdated == "" {
		t.Error("expected non-empty last_updated")
	}
}

func TestLiveGetTopImages(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetTopImages(context.Background(), &pb.GetTopImagesRequest{
		PageSize: 5,
	})
	if err != nil {
		t.Fatalf("GetTopImages: %v", err)
	}
	if resp.Count == 0 {
		t.Fatal("expected count > 0 for library images")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 library image")
	}

	img := resp.Results[0]
	if img.Name == "" {
		t.Error("image missing name")
	}
	if img.Namespace == "" {
		t.Error("image missing namespace")
	}
}

func TestLiveGetCategories(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetCategories(context.Background(), &pb.GetCategoriesRequest{})
	if err != nil {
		t.Fatalf("GetCategories: %v", err)
	}
	if len(resp.Categories) == 0 {
		t.Fatal("expected at least 1 category")
	}

	cat := resp.Categories[0]
	if cat.Name == "" {
		t.Error("category missing name")
	}
	if cat.Slug == "" {
		t.Error("category missing slug")
	}
}

func TestLiveSearchRepositoriesPagination(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp1, err := svc.SearchRepositories(context.Background(), &pb.SearchRepositoriesRequest{
		Query:    "python",
		PageSize: 2,
		Page:     1,
	})
	if err != nil {
		t.Fatalf("SearchRepositories page 1: %v", err)
	}
	if len(resp1.Results) == 0 {
		t.Skip("no results for python search")
	}

	resp2, err := svc.SearchRepositories(context.Background(), &pb.SearchRepositoriesRequest{
		Query:    "python",
		PageSize: 2,
		Page:     2,
	})
	if err != nil {
		t.Fatalf("SearchRepositories page 2: %v", err)
	}
	if len(resp2.Results) == 0 {
		t.Skip("no results on page 2")
	}

	// Verify pages return different results
	if len(resp1.Results) > 0 && len(resp2.Results) > 0 {
		if resp1.Results[0].RepoName == resp2.Results[0].RepoName {
			t.Error("page 1 and page 2 returned the same first result; expected different pages")
		}
	}
}
