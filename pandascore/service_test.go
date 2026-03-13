package main

import (
	"context"
	"os"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"
)

func mustStruct(t *testing.T, m map[string]any) *structpb.Struct {
	t.Helper()
	s, err := structpb.NewStruct(m)
	if err != nil { t.Fatalf("failed to create struct: %v", err) }
	return s
}

func skipUnlessLive(t *testing.T) {
	t.Helper()
	if os.Getenv("PANDASCORE_RUN_LIVE_TESTS") == "" {
		t.Skip("set PANDASCORE_RUN_LIVE_TESTS=1 to run live integration tests (hits real PandaScore API)")
	}
	if os.Getenv("PANDASCORE_API_KEY") == "" {
		t.Skip("PANDASCORE_API_KEY not set, skipping live tests")
	}
}

func liveService() *PandaScoreService { return NewPandaScoreService() }

func TestLiveListMatches(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListMatches(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListMatches: %v", err) }
	fields := resp.GetFields()
	matches := fields["matches"].GetListValue().GetValues()
	if len(matches) == 0 { t.Fatal("expected at least 1 match from live API") }
	t.Logf("Got %d matches from live API", len(matches))
}

func TestLiveListUpcomingMatches(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListUpcomingMatches(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListUpcomingMatches: %v", err) }
	fields := resp.GetFields()
	matches := fields["matches"].GetListValue().GetValues()
	t.Logf("Got %d upcoming matches from live API", len(matches))
}

func TestLiveListTeams(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListTeams(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListTeams: %v", err) }
	fields := resp.GetFields()
	teams := fields["teams"].GetListValue().GetValues()
	if len(teams) == 0 { t.Fatal("expected at least 1 team from live API") }
	t.Logf("Got %d teams from live API", len(teams))
}

func TestLiveListHeroes(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListHeroes(context.Background(), mustStruct(t, map[string]any{"per_page": float64(5)}))
	if err != nil { t.Fatalf("ListHeroes: %v", err) }
	fields := resp.GetFields()
	heroes := fields["heroes"].GetListValue().GetValues()
	if len(heroes) == 0 { t.Fatal("expected at least 1 hero from live API") }
	t.Logf("Got %d heroes from live API", len(heroes))
}

func TestLiveListLeagues(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListLeagues(context.Background(), mustStruct(t, map[string]any{"per_page": float64(5)}))
	if err != nil { t.Fatalf("ListLeagues: %v", err) }
	fields := resp.GetFields()
	leagues := fields["leagues"].GetListValue().GetValues()
	if len(leagues) == 0 { t.Fatal("expected at least 1 league from live API") }
	t.Logf("Got %d leagues from live API", len(leagues))
}

func TestLiveListTournaments(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListTournaments(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListTournaments: %v", err) }
	fields := resp.GetFields()
	tournaments := fields["tournaments"].GetListValue().GetValues()
	if len(tournaments) == 0 { t.Fatal("expected at least 1 tournament from live API") }
	t.Logf("Got %d tournaments from live API", len(tournaments))
}

func TestLiveListPlayers(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListPlayers(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListPlayers: %v", err) }
	fields := resp.GetFields()
	players := fields["players"].GetListValue().GetValues()
	if len(players) == 0 { t.Fatal("expected at least 1 player from live API") }
	t.Logf("Got %d players from live API", len(players))
}

func TestLiveListSeries(t *testing.T) {
	skipUnlessLive(t)
	svc := liveService()
	resp, err := svc.ListSeries(context.Background(), mustStruct(t, map[string]any{"per_page": float64(3)}))
	if err != nil { t.Fatalf("ListSeries: %v", err) }
	fields := resp.GetFields()
	series := fields["series"].GetListValue().GetValues()
	t.Logf("Got %d series from live API", len(series))
}
