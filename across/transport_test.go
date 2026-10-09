package main

import (
	"bytes"
	"context"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	pb "github.com/jim-technologies/invariantaf/across/proto/across/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/encoding/protojson"
)

func TestCanonicalRequestIntegerAndDeclaredEnvelopeThroughTransports(t *testing.T) {
	provider := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/limits" || r.URL.Query().Get("originChainId") != "9007199254740993" || r.URL.Query().Get("destinationChainId") != "9007199254740995" {
			t.Errorf("provider request lost canonical integer fields: %s", r.URL)
		}
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, `{"minDeposit":"1","maxDeposit":"999","maxDepositInstant":"100","maxDepositShortDelay":"500"}`)
	}))
	defer provider.Close()
	server, err := providerServer(&AcrossService{baseURL: provider.URL, client: provider.Client()})
	if err != nil {
		t.Fatal(err)
	}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer server.Stop()
	go server.Serve(listener)
	connection, err := grpc.NewClient(listener.Addr().String(), grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		t.Fatal(err)
	}
	defer connection.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	request := &pb.GetLimitsRequest{Token: "fixture-token", OriginChainId: 9007199254740993, DestinationChainId: 9007199254740995}
	result, err := pb.NewAcrossServiceClient(connection).GetLimits(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	check := func(result *pb.GetLimitsResponse) {
		t.Helper()
		if result.GetLimits().GetMinDeposit() != "1" || result.GetLimits().GetMaxDeposit() != "999" || result.GetLimits().GetMaxDepositInstant() != "100" {
			t.Fatalf("declared envelope or provider fields lost: %v", result)
		}
	}
	check(result)
	host := httptest.NewServer(server.HTTPHandler())
	defer host.Close()
	body, err := protojson.Marshal(request)
	if err != nil {
		t.Fatal(err)
	}
	response, err := http.Post(host.URL+"/across.v1.AcrossService/GetLimits", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	data, err := io.ReadAll(response.Body)
	if err != nil || response.StatusCode != http.StatusOK {
		t.Fatalf("Connect response = %d, %v", response.StatusCode, err)
	}
	if err := protojson.Unmarshal(data, result); err != nil {
		t.Fatal(err)
	}
	check(result)
}
