package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"

	pb "github.com/jim-technologies/invariantaf/unsplash/unsplash/v1"
)

// UnsplashService implements the UnsplashService RPCs defined in the proto.
type UnsplashService struct {
	accessKey string
	baseURL   string
	client    *http.Client
}

// NewUnsplashService creates a new UnsplashService reading the access key
// from the UNSPLASH_ACCESS_KEY environment variable.
func NewUnsplashService() *UnsplashService {
	return &UnsplashService{
		accessKey: os.Getenv("UNSPLASH_ACCESS_KEY"),
		baseURL:   "https://api.unsplash.com",
		client:    &http.Client{},
	}
}

// get performs an authenticated GET request against the Unsplash API.
func (s *UnsplashService) get(path string, params url.Values) (any, error) {
	u := fmt.Sprintf("%s%s", s.baseURL, path)
	if len(params) > 0 {
		u += "?" + params.Encode()
	}
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Authorization", "Client-ID "+s.accessKey)
	req.Header.Set("Accept-Version", "v1")
	resp, err := s.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		var errBody map[string]any
		json.NewDecoder(resp.Body).Decode(&errBody)
		return nil, fmt.Errorf("unsplash API error (status %d): %v", resp.StatusCode, errBody)
	}
	var result any
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return result, nil
}

// --- Helper functions for parsing API responses ---

func toString(v any) string {
	if v == nil {
		return ""
	}
	switch val := v.(type) {
	case string:
		return val
	case float64:
		return fmt.Sprintf("%.0f", val)
	default:
		return fmt.Sprintf("%v", val)
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

func toFloat64(v any) float64 {
	if v == nil {
		return 0
	}
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
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

func parsePhotoUrls(data map[string]any) *pb.PhotoUrls {
	urls := toMap(data["urls"])
	if urls == nil {
		return nil
	}
	return &pb.PhotoUrls{
		Raw:     toString(urls["raw"]),
		Full:    toString(urls["full"]),
		Regular: toString(urls["regular"]),
		Small:   toString(urls["small"]),
		Thumb:   toString(urls["thumb"]),
	}
}

func parseExif(data map[string]any) *pb.Exif {
	exif := toMap(data["exif"])
	if exif == nil {
		return nil
	}
	return &pb.Exif{
		Make:         toString(exif["make"]),
		Model:        toString(exif["model"]),
		Aperture:     toString(exif["aperture"]),
		ExposureTime: toString(exif["exposure_time"]),
		FocalLength:  toString(exif["focal_length"]),
		Iso:          toInt32(exif["iso"]),
	}
}

func parseLocation(data map[string]any) *pb.Location {
	loc := toMap(data["location"])
	if loc == nil {
		return nil
	}
	result := &pb.Location{
		City:    toString(loc["city"]),
		Country: toString(loc["country"]),
		Name:    toString(loc["name"]),
	}
	if pos := toMap(loc["position"]); pos != nil {
		result.Latitude = toFloat64(pos["latitude"])
		result.Longitude = toFloat64(pos["longitude"])
	}
	return result
}

func parseTags(data map[string]any) []*pb.Tag {
	tagsRaw := toSlice(data["tags"])
	if tagsRaw == nil {
		return nil
	}
	var tags []*pb.Tag
	for _, t := range tagsRaw {
		tm := toMap(t)
		if tm == nil {
			continue
		}
		tags = append(tags, &pb.Tag{Title: toString(tm["title"])})
	}
	return tags
}

func parseUser(data map[string]any) *pb.User {
	u := toMap(data["user"])
	if u == nil {
		return nil
	}
	return parseUserFromMap(u)
}

func parseUserFromMap(u map[string]any) *pb.User {
	if u == nil {
		return nil
	}
	user := &pb.User{
		Id:               toString(u["id"]),
		Username:         toString(u["username"]),
		Name:             toString(u["name"]),
		Bio:              toString(u["bio"]),
		Location:         toString(u["location"]),
		PortfolioUrl:     toString(u["portfolio_url"]),
		TotalPhotos:      toInt32(u["total_photos"]),
		TotalLikes:       toInt32(u["total_likes"]),
		TotalCollections: toInt32(u["total_collections"]),
		TotalDownloads:   toInt32(u["total_downloads"]),
		FollowersCount:   toInt32(u["followers_count"]),
		FollowingCount:   toInt32(u["following_count"]),
	}
	if pi := toMap(u["profile_image"]); pi != nil {
		user.ProfileImageSmall = toString(pi["small"])
		user.ProfileImageMedium = toString(pi["medium"])
		user.ProfileImageLarge = toString(pi["large"])
	}
	return user
}

func parsePhoto(data map[string]any) *pb.Photo {
	if data == nil {
		return nil
	}
	return &pb.Photo{
		Id:             toString(data["id"]),
		CreatedAt:      toString(data["created_at"]),
		UpdatedAt:      toString(data["updated_at"]),
		Width:          toInt32(data["width"]),
		Height:         toInt32(data["height"]),
		Description:    toString(data["description"]),
		AltDescription: toString(data["alt_description"]),
		Urls:           parsePhotoUrls(data),
		Likes:          toInt32(data["likes"]),
		User:           parseUser(data),
		Color:          toString(data["color"]),
		Downloads:      toInt32(data["downloads"]),
		Views:          toInt32(data["views"]),
		Exif:           parseExif(data),
		Location:       parseLocation(data),
		Tags:           parseTags(data),
	}
}

func parsePhotos(items []any) []*pb.Photo {
	var photos []*pb.Photo
	for _, item := range items {
		if m := toMap(item); m != nil {
			photos = append(photos, parsePhoto(m))
		}
	}
	return photos
}

func parseCollection(data map[string]any) *pb.Collection {
	if data == nil {
		return nil
	}
	col := &pb.Collection{
		Id:          toString(data["id"]),
		Title:       toString(data["title"]),
		Description: toString(data["description"]),
		PublishedAt: toString(data["published_at"]),
		UpdatedAt:   toString(data["updated_at"]),
		TotalPhotos: toInt32(data["total_photos"]),
		Tags:        parseTags(data),
	}
	if cp := toMap(data["cover_photo"]); cp != nil {
		col.CoverPhoto = parsePhoto(cp)
	}
	if u := toMap(data["user"]); u != nil {
		col.User = parseUserFromMap(u)
	}
	return col
}

// --- Helper for setting pagination params ---

func setPagination(params url.Values, page, perPage int32) {
	if page > 0 {
		params.Set("page", fmt.Sprintf("%d", page))
	}
	if perPage > 0 {
		params.Set("per_page", fmt.Sprintf("%d", perPage))
	}
}

// --- RPC implementations ---

// SearchPhotos searches for photos by keyword.
func (s *UnsplashService) SearchPhotos(_ context.Context, req *pb.SearchPhotosRequest) (*pb.SearchPhotosResponse, error) {
	params := url.Values{"query": {req.GetQuery()}}
	setPagination(params, req.GetPage(), req.GetPerPage())
	if req.GetOrderBy() != "" {
		params.Set("order_by", req.GetOrderBy())
	}
	if req.GetOrientation() != "" {
		params.Set("orientation", req.GetOrientation())
	}
	if req.GetColor() != "" {
		params.Set("color", req.GetColor())
	}

	raw, err := s.get("/search/photos", params)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.SearchPhotosResponse{
		Total:      toInt32(data["total"]),
		TotalPages: toInt32(data["total_pages"]),
		Results:    parsePhotos(toSlice(data["results"])),
	}, nil
}

// GetPhoto retrieves a single photo by ID.
func (s *UnsplashService) GetPhoto(_ context.Context, req *pb.GetPhotoRequest) (*pb.GetPhotoResponse, error) {
	raw, err := s.get("/photos/"+req.GetId(), nil)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.GetPhotoResponse{
		Photo: parsePhoto(data),
	}, nil
}

// GetRandomPhoto retrieves one or more random photos.
func (s *UnsplashService) GetRandomPhoto(_ context.Context, req *pb.GetRandomPhotoRequest) (*pb.GetRandomPhotoResponse, error) {
	params := url.Values{}
	if req.GetQuery() != "" {
		params.Set("query", req.GetQuery())
	}
	if req.GetCount() > 0 {
		params.Set("count", fmt.Sprintf("%d", req.GetCount()))
	}
	if req.GetOrientation() != "" {
		params.Set("orientation", req.GetOrientation())
	}
	if req.GetCollections() != "" {
		params.Set("collections", req.GetCollections())
	}
	if req.GetTopics() != "" {
		params.Set("topics", req.GetTopics())
	}

	raw, err := s.get("/photos/random", params)
	if err != nil {
		return nil, err
	}

	// Unsplash returns an array when count > 1, or a single object when count <= 1.
	var photos []*pb.Photo
	switch v := raw.(type) {
	case []any:
		photos = parsePhotos(v)
	case map[string]any:
		photos = []*pb.Photo{parsePhoto(v)}
	}

	return &pb.GetRandomPhotoResponse{
		Photos: photos,
	}, nil
}

// ListPhotos lists editorial photos curated by the Unsplash team.
func (s *UnsplashService) ListPhotos(_ context.Context, req *pb.ListPhotosRequest) (*pb.ListPhotosResponse, error) {
	params := url.Values{}
	setPagination(params, req.GetPage(), req.GetPerPage())
	if req.GetOrderBy() != "" {
		params.Set("order_by", req.GetOrderBy())
	}

	raw, err := s.get("/photos", params)
	if err != nil {
		return nil, err
	}
	items := toSlice(raw)
	if items == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.ListPhotosResponse{
		Photos: parsePhotos(items),
	}, nil
}

// SearchCollections searches for photo collections by keyword.
func (s *UnsplashService) SearchCollections(_ context.Context, req *pb.SearchCollectionsRequest) (*pb.SearchCollectionsResponse, error) {
	params := url.Values{"query": {req.GetQuery()}}
	setPagination(params, req.GetPage(), req.GetPerPage())

	raw, err := s.get("/search/collections", params)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	var collections []*pb.Collection
	for _, item := range toSlice(data["results"]) {
		if m := toMap(item); m != nil {
			collections = append(collections, parseCollection(m))
		}
	}

	return &pb.SearchCollectionsResponse{
		Total:      toInt32(data["total"]),
		TotalPages: toInt32(data["total_pages"]),
		Results:    collections,
	}, nil
}

// GetCollection retrieves a single collection by ID.
func (s *UnsplashService) GetCollection(_ context.Context, req *pb.GetCollectionRequest) (*pb.GetCollectionResponse, error) {
	raw, err := s.get("/collections/"+req.GetId(), nil)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.GetCollectionResponse{
		Collection: parseCollection(data),
	}, nil
}

// GetCollectionPhotos retrieves photos from a specific collection.
func (s *UnsplashService) GetCollectionPhotos(_ context.Context, req *pb.GetCollectionPhotosRequest) (*pb.GetCollectionPhotosResponse, error) {
	params := url.Values{}
	setPagination(params, req.GetPage(), req.GetPerPage())

	raw, err := s.get("/collections/"+req.GetId()+"/photos", params)
	if err != nil {
		return nil, err
	}
	items := toSlice(raw)
	if items == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.GetCollectionPhotosResponse{
		Photos: parsePhotos(items),
	}, nil
}

// SearchUsers searches for Unsplash users (photographers) by keyword.
func (s *UnsplashService) SearchUsers(_ context.Context, req *pb.SearchUsersRequest) (*pb.SearchUsersResponse, error) {
	params := url.Values{"query": {req.GetQuery()}}
	setPagination(params, req.GetPage(), req.GetPerPage())

	raw, err := s.get("/search/users", params)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	var users []*pb.User
	for _, item := range toSlice(data["results"]) {
		if m := toMap(item); m != nil {
			users = append(users, parseUserFromMap(m))
		}
	}

	return &pb.SearchUsersResponse{
		Total:      toInt32(data["total"]),
		TotalPages: toInt32(data["total_pages"]),
		Results:    users,
	}, nil
}

// GetUser retrieves a user's public profile by username.
func (s *UnsplashService) GetUser(_ context.Context, req *pb.GetUserRequest) (*pb.GetUserResponse, error) {
	raw, err := s.get("/users/"+req.GetUsername(), nil)
	if err != nil {
		return nil, err
	}
	data := toMap(raw)
	if data == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.GetUserResponse{
		User: parseUserFromMap(data),
	}, nil
}

// GetUserPhotos retrieves photos uploaded by a specific user.
func (s *UnsplashService) GetUserPhotos(_ context.Context, req *pb.GetUserPhotosRequest) (*pb.GetUserPhotosResponse, error) {
	params := url.Values{}
	setPagination(params, req.GetPage(), req.GetPerPage())
	if req.GetOrderBy() != "" {
		params.Set("order_by", req.GetOrderBy())
	}
	if req.GetOrientation() != "" {
		params.Set("orientation", req.GetOrientation())
	}

	raw, err := s.get("/users/"+req.GetUsername()+"/photos", params)
	if err != nil {
		return nil, err
	}
	items := toSlice(raw)
	if items == nil {
		return nil, fmt.Errorf("unexpected response format")
	}

	return &pb.GetUserPhotosResponse{
		Photos: parsePhotos(items),
	}, nil
}
