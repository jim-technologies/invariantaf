package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	pb "github.com/jim-technologies/invariantaf/unsplash/unsplash/v1"
)

// mockPhoto returns a representative Unsplash photo JSON object.
func mockPhoto() map[string]any {
	return map[string]any{
		"id":              "abc123",
		"created_at":      "2024-01-15T10:30:00Z",
		"updated_at":      "2024-01-16T12:00:00Z",
		"width":           float64(4000),
		"height":          float64(3000),
		"description":     "Beautiful sunset over the ocean",
		"alt_description": "A golden sunset with waves crashing on rocks",
		"color":           "#6E633A",
		"likes":           float64(500),
		"downloads":       float64(1200),
		"views":           float64(50000),
		"urls": map[string]any{
			"raw":     "https://images.unsplash.com/photo-abc123",
			"full":    "https://images.unsplash.com/photo-abc123?q=100",
			"regular": "https://images.unsplash.com/photo-abc123?w=1080",
			"small":   "https://images.unsplash.com/photo-abc123?w=400",
			"thumb":   "https://images.unsplash.com/photo-abc123?w=200",
		},
		"user": map[string]any{
			"id":                "user1",
			"username":          "john_doe",
			"name":              "John Doe",
			"bio":               "Landscape photographer",
			"location":          "San Francisco, CA",
			"portfolio_url":     "https://johndoe.com",
			"total_photos":      float64(150),
			"total_likes":       float64(3000),
			"total_collections": float64(10),
			"total_downloads":   float64(50000),
			"followers_count":   float64(1200),
			"following_count":   float64(50),
			"profile_image": map[string]any{
				"small":  "https://images.unsplash.com/profile-user1-small",
				"medium": "https://images.unsplash.com/profile-user1-medium",
				"large":  "https://images.unsplash.com/profile-user1-large",
			},
		},
		"exif": map[string]any{
			"make":          "Canon",
			"model":         "EOS R5",
			"aperture":      "2.8",
			"exposure_time": "1/250",
			"focal_length":  "85.0",
			"iso":           float64(400),
		},
		"location": map[string]any{
			"city":    "San Francisco",
			"country": "United States",
			"name":    "Golden Gate Bridge",
			"position": map[string]any{
				"latitude":  37.8199,
				"longitude": -122.4783,
			},
		},
		"tags": []any{
			map[string]any{"title": "sunset"},
			map[string]any{"title": "ocean"},
		},
	}
}

// mockUser returns a representative Unsplash user JSON object.
func mockUser() map[string]any {
	return map[string]any{
		"id":                "user1",
		"username":          "john_doe",
		"name":              "John Doe",
		"bio":               "Landscape photographer",
		"location":          "San Francisco, CA",
		"portfolio_url":     "https://johndoe.com",
		"total_photos":      float64(150),
		"total_likes":       float64(3000),
		"total_collections": float64(10),
		"total_downloads":   float64(50000),
		"followers_count":   float64(1200),
		"following_count":   float64(50),
		"profile_image": map[string]any{
			"small":  "https://images.unsplash.com/profile-user1-small",
			"medium": "https://images.unsplash.com/profile-user1-medium",
			"large":  "https://images.unsplash.com/profile-user1-large",
		},
	}
}

// mockCollection returns a representative Unsplash collection JSON object.
func mockCollection() map[string]any {
	return map[string]any{
		"id":           "12345",
		"title":        "Nature Photography",
		"description":  "Beautiful landscapes and wildlife",
		"published_at": "2024-01-01T00:00:00Z",
		"updated_at":   "2024-06-15T12:00:00Z",
		"total_photos": float64(42),
		"cover_photo":  mockPhoto(),
		"user":         mockUser(),
		"tags": []any{
			map[string]any{"title": "nature"},
			map[string]any{"title": "landscape"},
		},
	}
}

func mockUnsplashServer() *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		auth := r.Header.Get("Authorization")
		if auth == "" || !strings.HasPrefix(auth, "Client-ID ") {
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(map[string]any{"errors": []string{"OAuth error"}})
			return
		}

		w.Header().Set("Content-Type", "application/json")

		switch {
		case r.URL.Path == "/search/photos":
			json.NewEncoder(w).Encode(map[string]any{
				"total":       float64(1000),
				"total_pages": float64(100),
				"results":     []any{mockPhoto()},
			})

		case r.URL.Path == "/search/collections":
			json.NewEncoder(w).Encode(map[string]any{
				"total":       float64(50),
				"total_pages": float64(5),
				"results":     []any{mockCollection()},
			})

		case r.URL.Path == "/search/users":
			json.NewEncoder(w).Encode(map[string]any{
				"total":       float64(25),
				"total_pages": float64(3),
				"results":     []any{mockUser()},
			})

		case r.URL.Path == "/photos/random":
			count := r.URL.Query().Get("count")
			if count != "" && count != "1" {
				json.NewEncoder(w).Encode([]any{mockPhoto(), mockPhoto()})
			} else {
				json.NewEncoder(w).Encode(mockPhoto())
			}

		case r.URL.Path == "/photos" && !strings.Contains(r.URL.Path, "/photos/"):
			json.NewEncoder(w).Encode([]any{mockPhoto()})

		case strings.HasPrefix(r.URL.Path, "/photos/"):
			json.NewEncoder(w).Encode(mockPhoto())

		case strings.HasPrefix(r.URL.Path, "/collections/") && strings.HasSuffix(r.URL.Path, "/photos"):
			json.NewEncoder(w).Encode([]any{mockPhoto()})

		case strings.HasPrefix(r.URL.Path, "/collections/"):
			json.NewEncoder(w).Encode(mockCollection())

		case strings.HasPrefix(r.URL.Path, "/users/") && strings.HasSuffix(r.URL.Path, "/photos"):
			json.NewEncoder(w).Encode([]any{mockPhoto()})

		case strings.HasPrefix(r.URL.Path, "/users/"):
			json.NewEncoder(w).Encode(mockUser())

		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]any{"errors": []string{"Not found"}})
		}
	}))
}

func testService(t *testing.T) (*UnsplashService, *httptest.Server) {
	t.Helper()
	ts := mockUnsplashServer()
	svc := &UnsplashService{
		accessKey: "test-key",
		baseURL:   ts.URL,
		client:    http.DefaultClient,
	}
	return svc, ts
}

func TestSearchPhotos(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query:   "sunset",
		Page:    1,
		PerPage: 10,
	})
	if err != nil {
		t.Fatalf("SearchPhotos failed: %v", err)
	}
	if resp.Total != 1000 {
		t.Errorf("expected total=1000, got %d", resp.Total)
	}
	if resp.TotalPages != 100 {
		t.Errorf("expected total_pages=100, got %d", resp.TotalPages)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(resp.Results))
	}
	photo := resp.Results[0]
	if photo.Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", photo.Id)
	}
	if photo.Description != "Beautiful sunset over the ocean" {
		t.Errorf("unexpected description: %s", photo.Description)
	}
	if photo.Width != 4000 || photo.Height != 3000 {
		t.Errorf("unexpected dimensions: %dx%d", photo.Width, photo.Height)
	}
	if photo.Likes != 500 {
		t.Errorf("expected likes=500, got %d", photo.Likes)
	}
	if photo.Urls == nil {
		t.Fatal("expected urls to be non-nil")
	}
	if photo.Urls.Regular != "https://images.unsplash.com/photo-abc123?w=1080" {
		t.Errorf("unexpected regular url: %s", photo.Urls.Regular)
	}
	if photo.User == nil {
		t.Fatal("expected user to be non-nil")
	}
	if photo.User.Name != "John Doe" {
		t.Errorf("expected user name=John Doe, got %s", photo.User.Name)
	}
}

func TestSearchPhotosWithFilters(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query:       "mountains",
		Page:        2,
		PerPage:     5,
		OrderBy:     "latest",
		Orientation: "landscape",
		Color:       "blue",
	})
	if err != nil {
		t.Fatalf("SearchPhotos with filters failed: %v", err)
	}
	if resp.Total != 1000 {
		t.Errorf("expected total=1000, got %d", resp.Total)
	}
}

func TestGetPhoto(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetPhoto(context.Background(), &pb.GetPhotoRequest{
		Id: "abc123",
	})
	if err != nil {
		t.Fatalf("GetPhoto failed: %v", err)
	}
	if resp.Photo == nil {
		t.Fatal("expected photo to be non-nil")
	}
	if resp.Photo.Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", resp.Photo.Id)
	}
	if resp.Photo.Exif == nil {
		t.Fatal("expected exif to be non-nil")
	}
	if resp.Photo.Exif.Make != "Canon" {
		t.Errorf("expected exif make=Canon, got %s", resp.Photo.Exif.Make)
	}
	if resp.Photo.Exif.Model != "EOS R5" {
		t.Errorf("expected exif model=EOS R5, got %s", resp.Photo.Exif.Model)
	}
	if resp.Photo.Location == nil {
		t.Fatal("expected location to be non-nil")
	}
	if resp.Photo.Location.City != "San Francisco" {
		t.Errorf("expected city=San Francisco, got %s", resp.Photo.Location.City)
	}
	if resp.Photo.Location.Latitude != 37.8199 {
		t.Errorf("expected latitude=37.8199, got %f", resp.Photo.Location.Latitude)
	}
	if len(resp.Photo.Tags) != 2 {
		t.Errorf("expected 2 tags, got %d", len(resp.Photo.Tags))
	}
}

func TestGetRandomPhoto(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	// Single random photo (no count or count=1).
	resp, err := svc.GetRandomPhoto(context.Background(), &pb.GetRandomPhotoRequest{
		Query: "nature",
	})
	if err != nil {
		t.Fatalf("GetRandomPhoto failed: %v", err)
	}
	if len(resp.Photos) != 1 {
		t.Fatalf("expected 1 photo, got %d", len(resp.Photos))
	}
	if resp.Photos[0].Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", resp.Photos[0].Id)
	}
}

func TestGetRandomPhotoMultiple(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	// Multiple random photos.
	resp, err := svc.GetRandomPhoto(context.Background(), &pb.GetRandomPhotoRequest{
		Query: "nature",
		Count: 2,
	})
	if err != nil {
		t.Fatalf("GetRandomPhoto (multiple) failed: %v", err)
	}
	if len(resp.Photos) != 2 {
		t.Fatalf("expected 2 photos, got %d", len(resp.Photos))
	}
}

func TestListPhotos(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.ListPhotos(context.Background(), &pb.ListPhotosRequest{
		Page:    1,
		PerPage: 10,
		OrderBy: "popular",
	})
	if err != nil {
		t.Fatalf("ListPhotos failed: %v", err)
	}
	if len(resp.Photos) != 1 {
		t.Fatalf("expected 1 photo, got %d", len(resp.Photos))
	}
	if resp.Photos[0].Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", resp.Photos[0].Id)
	}
}

func TestSearchCollections(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.SearchCollections(context.Background(), &pb.SearchCollectionsRequest{
		Query:   "nature",
		Page:    1,
		PerPage: 10,
	})
	if err != nil {
		t.Fatalf("SearchCollections failed: %v", err)
	}
	if resp.Total != 50 {
		t.Errorf("expected total=50, got %d", resp.Total)
	}
	if resp.TotalPages != 5 {
		t.Errorf("expected total_pages=5, got %d", resp.TotalPages)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 collection, got %d", len(resp.Results))
	}
	col := resp.Results[0]
	if col.Id != "12345" {
		t.Errorf("expected id=12345, got %s", col.Id)
	}
	if col.Title != "Nature Photography" {
		t.Errorf("expected title=Nature Photography, got %s", col.Title)
	}
	if col.TotalPhotos != 42 {
		t.Errorf("expected total_photos=42, got %d", col.TotalPhotos)
	}
	if col.User == nil || col.User.Username != "john_doe" {
		t.Error("expected collection user with username john_doe")
	}
}

func TestGetCollection(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetCollection(context.Background(), &pb.GetCollectionRequest{
		Id: "12345",
	})
	if err != nil {
		t.Fatalf("GetCollection failed: %v", err)
	}
	if resp.Collection == nil {
		t.Fatal("expected collection to be non-nil")
	}
	if resp.Collection.Title != "Nature Photography" {
		t.Errorf("expected title=Nature Photography, got %s", resp.Collection.Title)
	}
	if resp.Collection.CoverPhoto == nil {
		t.Error("expected cover photo to be non-nil")
	}
	if len(resp.Collection.Tags) != 2 {
		t.Errorf("expected 2 tags, got %d", len(resp.Collection.Tags))
	}
}

func TestGetCollectionPhotos(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetCollectionPhotos(context.Background(), &pb.GetCollectionPhotosRequest{
		Id:      "12345",
		Page:    1,
		PerPage: 10,
	})
	if err != nil {
		t.Fatalf("GetCollectionPhotos failed: %v", err)
	}
	if len(resp.Photos) != 1 {
		t.Fatalf("expected 1 photo, got %d", len(resp.Photos))
	}
	if resp.Photos[0].Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", resp.Photos[0].Id)
	}
}

func TestSearchUsers(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.SearchUsers(context.Background(), &pb.SearchUsersRequest{
		Query:   "landscape",
		Page:    1,
		PerPage: 10,
	})
	if err != nil {
		t.Fatalf("SearchUsers failed: %v", err)
	}
	if resp.Total != 25 {
		t.Errorf("expected total=25, got %d", resp.Total)
	}
	if resp.TotalPages != 3 {
		t.Errorf("expected total_pages=3, got %d", resp.TotalPages)
	}
	if len(resp.Results) != 1 {
		t.Fatalf("expected 1 user, got %d", len(resp.Results))
	}
	user := resp.Results[0]
	if user.Username != "john_doe" {
		t.Errorf("expected username=john_doe, got %s", user.Username)
	}
	if user.Name != "John Doe" {
		t.Errorf("expected name=John Doe, got %s", user.Name)
	}
	if user.TotalPhotos != 150 {
		t.Errorf("expected total_photos=150, got %d", user.TotalPhotos)
	}
}

func TestGetUser(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetUser(context.Background(), &pb.GetUserRequest{
		Username: "john_doe",
	})
	if err != nil {
		t.Fatalf("GetUser failed: %v", err)
	}
	if resp.User == nil {
		t.Fatal("expected user to be non-nil")
	}
	if resp.User.Username != "john_doe" {
		t.Errorf("expected username=john_doe, got %s", resp.User.Username)
	}
	if resp.User.Bio != "Landscape photographer" {
		t.Errorf("unexpected bio: %s", resp.User.Bio)
	}
	if resp.User.ProfileImageSmall != "https://images.unsplash.com/profile-user1-small" {
		t.Errorf("unexpected profile image small: %s", resp.User.ProfileImageSmall)
	}
	if resp.User.FollowersCount != 1200 {
		t.Errorf("expected followers=1200, got %d", resp.User.FollowersCount)
	}
}

func TestGetUserPhotos(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetUserPhotos(context.Background(), &pb.GetUserPhotosRequest{
		Username:    "john_doe",
		Page:        1,
		PerPage:     10,
		OrderBy:     "popular",
		Orientation: "landscape",
	})
	if err != nil {
		t.Fatalf("GetUserPhotos failed: %v", err)
	}
	if len(resp.Photos) != 1 {
		t.Fatalf("expected 1 photo, got %d", len(resp.Photos))
	}
	if resp.Photos[0].Id != "abc123" {
		t.Errorf("expected id=abc123, got %s", resp.Photos[0].Id)
	}
}

func TestAuthenticationRequired(t *testing.T) {
	ts := mockUnsplashServer()
	defer ts.Close()

	// Service with empty access key.
	svc := &UnsplashService{
		accessKey: "",
		baseURL:   ts.URL,
		client:    http.DefaultClient,
	}

	_, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query: "test",
	})
	if err == nil {
		t.Fatal("expected error for missing auth, got nil")
	}
	if !strings.Contains(err.Error(), "401") {
		t.Errorf("expected 401 error, got: %v", err)
	}
}

func TestPhotoUrlsParsing(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetPhoto(context.Background(), &pb.GetPhotoRequest{Id: "abc123"})
	if err != nil {
		t.Fatalf("GetPhoto failed: %v", err)
	}
	urls := resp.Photo.Urls
	if urls == nil {
		t.Fatal("urls is nil")
	}
	if urls.Raw != "https://images.unsplash.com/photo-abc123" {
		t.Errorf("unexpected raw url: %s", urls.Raw)
	}
	if urls.Full != "https://images.unsplash.com/photo-abc123?q=100" {
		t.Errorf("unexpected full url: %s", urls.Full)
	}
	if urls.Small != "https://images.unsplash.com/photo-abc123?w=400" {
		t.Errorf("unexpected small url: %s", urls.Small)
	}
	if urls.Thumb != "https://images.unsplash.com/photo-abc123?w=200" {
		t.Errorf("unexpected thumb url: %s", urls.Thumb)
	}
}

func TestExifParsing(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetPhoto(context.Background(), &pb.GetPhotoRequest{Id: "abc123"})
	if err != nil {
		t.Fatalf("GetPhoto failed: %v", err)
	}
	exif := resp.Photo.Exif
	if exif == nil {
		t.Fatal("exif is nil")
	}
	if exif.Aperture != "2.8" {
		t.Errorf("expected aperture=2.8, got %s", exif.Aperture)
	}
	if exif.ExposureTime != "1/250" {
		t.Errorf("expected exposure_time=1/250, got %s", exif.ExposureTime)
	}
	if exif.FocalLength != "85.0" {
		t.Errorf("expected focal_length=85.0, got %s", exif.FocalLength)
	}
	if exif.Iso != 400 {
		t.Errorf("expected iso=400, got %d", exif.Iso)
	}
}

func TestLocationParsing(t *testing.T) {
	svc, ts := testService(t)
	defer ts.Close()

	resp, err := svc.GetPhoto(context.Background(), &pb.GetPhotoRequest{Id: "abc123"})
	if err != nil {
		t.Fatalf("GetPhoto failed: %v", err)
	}
	loc := resp.Photo.Location
	if loc == nil {
		t.Fatal("location is nil")
	}
	if loc.City != "San Francisco" {
		t.Errorf("expected city=San Francisco, got %s", loc.City)
	}
	if loc.Country != "United States" {
		t.Errorf("expected country=United States, got %s", loc.Country)
	}
	if loc.Name != "Golden Gate Bridge" {
		t.Errorf("expected name=Golden Gate Bridge, got %s", loc.Name)
	}
	if loc.Longitude != -122.4783 {
		t.Errorf("expected longitude=-122.4783, got %f", loc.Longitude)
	}
}

// --- Live integration tests (hit the real Unsplash API) ---
// These require UNSPLASH_ACCESS_KEY to be set. Unsplash does not provide
// a public/demo key, so these tests only run when you have a valid key.

func skipUnlessIntegration(t *testing.T) {
	t.Helper()
	if os.Getenv("TEST_UNSPLASH") == "" {
		t.Skip("set TEST_UNSPLASH=1 to run integration tests (hits real Unsplash API)")
	}
	if os.Getenv("UNSPLASH_ACCESS_KEY") == "" {
		t.Skip("UNSPLASH_ACCESS_KEY is required for live Unsplash tests")
	}
}

func liveService() *UnsplashService {
	return NewUnsplashService()
}

func TestLiveSearchPhotos(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query:   "mountains",
		Page:    1,
		PerPage: 5,
	})
	if err != nil {
		t.Fatalf("SearchPhotos: %v", err)
	}
	if resp.Total == 0 {
		t.Fatal("expected total > 0 for 'mountains' search")
	}
	if resp.TotalPages == 0 {
		t.Fatal("expected total_pages > 0")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 result")
	}

	photo := resp.Results[0]
	if photo.Id == "" {
		t.Error("photo missing id")
	}
	if photo.Urls == nil {
		t.Error("photo missing urls")
	} else if photo.Urls.Regular == "" {
		t.Error("photo missing regular url")
	}
	if photo.User == nil {
		t.Error("photo missing user")
	} else if photo.User.Username == "" {
		t.Error("photo user missing username")
	}
}

func TestLiveSearchPhotosWithFilters(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query:       "ocean",
		Page:        1,
		PerPage:     3,
		Orientation: "landscape",
		OrderBy:     "relevant",
	})
	if err != nil {
		t.Fatalf("SearchPhotos with filters: %v", err)
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 result for landscape ocean photos")
	}
}

func TestLiveGetPhoto(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	// First search for a photo to get a real ID
	searchResp, err := svc.SearchPhotos(context.Background(), &pb.SearchPhotosRequest{
		Query:   "nature",
		Page:    1,
		PerPage: 1,
	})
	if err != nil {
		t.Fatalf("SearchPhotos (setup): %v", err)
	}
	if len(searchResp.Results) == 0 {
		t.Skip("no photos available for setup")
	}
	photoID := searchResp.Results[0].Id

	resp, err := svc.GetPhoto(context.Background(), &pb.GetPhotoRequest{
		Id: photoID,
	})
	if err != nil {
		t.Fatalf("GetPhoto(%s): %v", photoID, err)
	}
	if resp.Photo == nil {
		t.Fatal("expected photo to be non-nil")
	}
	if resp.Photo.Id != photoID {
		t.Errorf("expected id=%s, got %s", photoID, resp.Photo.Id)
	}
	if resp.Photo.Width == 0 || resp.Photo.Height == 0 {
		t.Error("photo missing dimensions")
	}
	if resp.Photo.Urls == nil {
		t.Error("photo missing urls")
	}
}

func TestLiveGetRandomPhoto(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetRandomPhoto(context.Background(), &pb.GetRandomPhotoRequest{
		Query: "sunset",
	})
	if err != nil {
		t.Fatalf("GetRandomPhoto: %v", err)
	}
	if len(resp.Photos) == 0 {
		t.Fatal("expected at least 1 random photo")
	}

	photo := resp.Photos[0]
	if photo.Id == "" {
		t.Error("random photo missing id")
	}
	if photo.Urls == nil {
		t.Error("random photo missing urls")
	}
}

func TestLiveListPhotos(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.ListPhotos(context.Background(), &pb.ListPhotosRequest{
		Page:    1,
		PerPage: 5,
		OrderBy: "latest",
	})
	if err != nil {
		t.Fatalf("ListPhotos: %v", err)
	}
	if len(resp.Photos) == 0 {
		t.Fatal("expected at least 1 editorial photo")
	}

	photo := resp.Photos[0]
	if photo.Id == "" {
		t.Error("photo missing id")
	}
	if photo.CreatedAt == "" {
		t.Error("photo missing created_at")
	}
}

func TestLiveSearchCollections(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchCollections(context.Background(), &pb.SearchCollectionsRequest{
		Query:   "travel",
		Page:    1,
		PerPage: 3,
	})
	if err != nil {
		t.Fatalf("SearchCollections: %v", err)
	}
	if resp.Total == 0 {
		t.Fatal("expected total > 0 for 'travel' collections")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 collection")
	}

	col := resp.Results[0]
	if col.Id == "" {
		t.Error("collection missing id")
	}
	if col.Title == "" {
		t.Error("collection missing title")
	}
}

func TestLiveSearchUsers(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.SearchUsers(context.Background(), &pb.SearchUsersRequest{
		Query:   "landscape",
		Page:    1,
		PerPage: 3,
	})
	if err != nil {
		t.Fatalf("SearchUsers: %v", err)
	}
	if resp.Total == 0 {
		t.Fatal("expected total > 0 for 'landscape' user search")
	}
	if len(resp.Results) == 0 {
		t.Fatal("expected at least 1 user")
	}

	user := resp.Results[0]
	if user.Username == "" {
		t.Error("user missing username")
	}
	if user.Name == "" {
		t.Error("user missing name")
	}
}

func TestLiveGetUser(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	// "unsplash" is the official Unsplash user
	resp, err := svc.GetUser(context.Background(), &pb.GetUserRequest{
		Username: "unsplash",
	})
	if err != nil {
		t.Fatalf("GetUser: %v", err)
	}
	if resp.User == nil {
		t.Fatal("expected user to be non-nil")
	}
	if resp.User.Username != "unsplash" {
		t.Errorf("expected username=unsplash, got %s", resp.User.Username)
	}
	if resp.User.Name == "" {
		t.Error("user missing name")
	}
}

func TestLiveGetUserPhotos(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	resp, err := svc.GetUserPhotos(context.Background(), &pb.GetUserPhotosRequest{
		Username: "unsplash",
		Page:     1,
		PerPage:  3,
	})
	if err != nil {
		t.Fatalf("GetUserPhotos: %v", err)
	}
	if len(resp.Photos) == 0 {
		t.Skip("unsplash user has no photos (unexpected)")
	}

	photo := resp.Photos[0]
	if photo.Id == "" {
		t.Error("photo missing id")
	}
}

func TestLiveGetCollectionAndPhotos(t *testing.T) {
	skipUnlessIntegration(t)
	svc := liveService()

	// Search for a collection first
	searchResp, err := svc.SearchCollections(context.Background(), &pb.SearchCollectionsRequest{
		Query:   "nature",
		Page:    1,
		PerPage: 1,
	})
	if err != nil {
		t.Fatalf("SearchCollections (setup): %v", err)
	}
	if len(searchResp.Results) == 0 {
		t.Skip("no collections found for setup")
	}
	colID := searchResp.Results[0].Id

	// Get the collection
	colResp, err := svc.GetCollection(context.Background(), &pb.GetCollectionRequest{
		Id: colID,
	})
	if err != nil {
		t.Fatalf("GetCollection(%s): %v", colID, err)
	}
	if colResp.Collection == nil {
		t.Fatal("expected collection to be non-nil")
	}
	if colResp.Collection.Id != colID {
		t.Errorf("expected id=%s, got %s", colID, colResp.Collection.Id)
	}
	if colResp.Collection.Title == "" {
		t.Error("collection missing title")
	}

	// Get collection photos
	photosResp, err := svc.GetCollectionPhotos(context.Background(), &pb.GetCollectionPhotosRequest{
		Id:      colID,
		Page:    1,
		PerPage: 3,
	})
	if err != nil {
		t.Fatalf("GetCollectionPhotos(%s): %v", colID, err)
	}
	if len(photosResp.Photos) == 0 {
		t.Skip("collection has no photos")
	}

	photo := photosResp.Photos[0]
	if photo.Id == "" {
		t.Error("collection photo missing id")
	}
}
