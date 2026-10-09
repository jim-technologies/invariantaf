package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	pb "github.com/jim-technologies/invariantaf/jito/proto/jito/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/reflect/protodesc"
	"google.golang.org/protobuf/reflect/protoreflect"
	"google.golang.org/protobuf/types/descriptorpb"
	"google.golang.org/protobuf/types/dynamicpb"
	"google.golang.org/protobuf/types/known/structpb"
)

func TestTypedRegistrationPreservesProviderIntegerThroughGRPCAndConnect(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("provider method = %s", r.Method)
		}
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, `{"jsonrpc":"2.0","id":1,"result":{"value":[{"bundle_id":"fixture","slot":9007199254740993,"confirmation_status":"finalized","err":null,"transactions":[]}]}}`)
	}))
	defer upstream.Close()
	server, err := providerServer(&JitoService{bundleURL: upstream.URL, client: upstream.Client()})
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
	request := &pb.GetBundleStatusesRequest{BundleIds: []string{"fixture"}}
	result, err := pb.NewJitoServiceClient(connection).GetBundleStatuses(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	assertBundle := func(result *pb.GetBundleStatusesResponse) {
		t.Helper()
		if len(result.Statuses) != 1 || result.Statuses[0].GetLandedSlot() != 9007199254740993 || result.Statuses[0].GetStatus() != "finalized" {
			t.Fatalf("typed response lost provider values: %v", result)
		}
	}
	assertBundle(result)
	host := httptest.NewServer(server.HTTPHandler())
	defer host.Close()
	body, err := protojson.Marshal(request)
	if err != nil {
		t.Fatal(err)
	}
	response, err := http.Post(host.URL+"/jito.v1.JitoService/GetBundleStatuses", "application/json", bytes.NewReader(body))
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
	assertBundle(result)
}

func numericContract(t *testing.T) protoreflect.MessageDescriptor {
	t.Helper()
	file, err := protodesc.NewFile(&descriptorpb.FileDescriptorProto{
		Name: proto.String("codec_fixture.proto"), Package: proto.String("fixture.v1"), Syntax: proto.String("proto3"),
		EnumType: []*descriptorpb.EnumDescriptorProto{{Name: proto.String("State"), Value: []*descriptorpb.EnumValueDescriptorProto{
			{Name: proto.String("STATE_UNSPECIFIED"), Number: proto.Int32(0)}, {Name: proto.String("STATE_READY"), Number: proto.Int32(1)},
		}}},
		MessageType: []*descriptorpb.DescriptorProto{{Name: proto.String("Contract"), OneofDecl: []*descriptorpb.OneofDescriptorProto{{Name: proto.String("_optional_id")}}, Field: []*descriptorpb.FieldDescriptorProto{
			{Name: proto.String("record_id"), JsonName: proto.String("recordId"), Number: proto.Int32(1), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum()},
			{Name: proto.String("counter"), Number: proto.Int32(2), Type: descriptorpb.FieldDescriptorProto_TYPE_UINT64.Enum()},
			{Name: proto.String("state"), Number: proto.Int32(3), Type: descriptorpb.FieldDescriptorProto_TYPE_ENUM.Enum(), TypeName: proto.String(".fixture.v1.State")},
			{Name: proto.String("optional_id"), Number: proto.Int32(4), Type: descriptorpb.FieldDescriptorProto_TYPE_INT64.Enum(), Proto3Optional: proto.Bool(true), OneofIndex: proto.Int32(0)},
		}}},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	return file.Messages().Get(0)
}

func TestCodecPreservesCanonicalNamesEnumsAndIntegerBounds(t *testing.T) {
	descriptor := numericContract(t)
	request := dynamicpb.NewMessage(descriptor)
	request.Set(descriptor.Fields().ByName("record_id"), protoreflect.ValueOfInt64(9007199254740993))
	request.Set(descriptor.Fields().ByName("counter"), protoreflect.ValueOfUint64(^uint64(0)))
	request.Set(descriptor.Fields().ByName("state"), protoreflect.ValueOfEnum(1))
	fields, err := requestStruct(request)
	if err != nil {
		t.Fatal(err)
	}
	if fields.Fields["record_id"].GetStringValue() != "9007199254740993" || fields.Fields["counter"].GetStringValue() != "18446744073709551615" || fields.Fields["state"].GetStringValue() != "STATE_READY" {
		t.Fatal("request conversion changed canonical scalar values or names")
	}
	if _, exists := fields.Fields["optional_id"]; exists {
		t.Fatal("absent optional request field was materialized")
	}
	response := dynamicpb.NewMessage(descriptor)
	if err := typedResponse([]byte(`{"recordId":9007199254740993,"counter":"18446744073709551615","state":"STATE_READY"}`), response); err != nil {
		t.Fatal(err)
	}
	if !proto.Equal(request, response) {
		t.Fatalf("typed reply changed values: %v", response)
	}
	for _, body := range []string{
		`{"unknown":1}`, `{"record_id":9223372036854775808}`, `{"counter":18446744073709551616}`,
		`{"counter":-1}`, `{"state":"STATE_INVALID"}`, `{"record_id":"not-a-number"}`,
	} {
		if err := typedResponse([]byte(body), dynamicpb.NewMessage(descriptor)); err == nil {
			t.Fatalf("invalid provider fields accepted: %s", body)
		}
	}
}

func TestDeclaredListEnvelopeAndScalarValidation(t *testing.T) {
	response := new(pb.GetBundleStatusesResponse)
	if err := typedResponse([]byte(`{"items":[{"bundle_id":"fixture","landed_slot":9007199254740993}]}`), response); err != nil {
		t.Fatal(err)
	}
	if len(response.Statuses) != 1 || response.Statuses[0].LandedSlot != 9007199254740993 {
		t.Fatalf("declared list envelope changed exact provider value: %v", response)
	}
	for _, body := range []string{
		`{"items":[{"unknown":1}]}`, `{"items":"wrong-kind"}`, `{"items":[],"unknown":1}`,
	} {
		if err := typedResponse([]byte(body), new(pb.GetBundleStatusesResponse)); err == nil {
			t.Fatalf("malformed list envelope accepted: %s", body)
		}
	}
	if err := typedResponse([]byte(`{"items":"fixture"}`), new(pb.SendBundleResponse)); err == nil {
		t.Fatal("unnamed provider field was guessed into a scalar response")
	}
}

func TestNativeProjectionDrainsOnContextCancellation(t *testing.T) {
	server, err := providerServer(&JitoService{})
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Millisecond)
	defer cancel()
	finished := make(chan error, 1)
	go func() { finished <- serveAdapter(ctx, server, []string{"--grpc", "0"}) }()
	select {
	case err := <-finished:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(time.Second):
		server.Stop()
		t.Fatal("native gRPC did not drain after cancellation")
	}
}

func TestProviderStatusNormalizationRejectsUnknownOrMalformedEnvelope(t *testing.T) {
	for _, result := range []string{
		`{"value":[{"bundle_id":"fixture","unknown":1}]}`,
		`{"value":[{"bundle_id":"fixture","transactions":"wrong-kind"}]}`,
		`{"value":[null]}`, `{"value":"wrong-kind"}`, `{"unknown":[]}`,
		`{"value":[],"context":{"slot":-1}}`,
		`{"value":[],"context":{"slot":1,"unknown":1}}`,
	} {
		t.Run(result, func(t *testing.T) {
			provider := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				io.WriteString(w, `{"jsonrpc":"2.0","id":1,"result":`+result+`}`)
			}))
			defer provider.Close()
			backend := &JitoService{bundleURL: provider.URL, client: provider.Client()}
			service := &typedJitoService{backend: backend}
			if _, err := service.GetBundleStatuses(context.Background(), &pb.GetBundleStatusesRequest{BundleIds: []string{"fixture"}}); err == nil {
				t.Fatal("unsupported provider shape was accepted")
			}
		})
	}
}

func TestGeneratedBindingsMatchEmbeddedDescriptor(t *testing.T) {
	var embedded descriptorpb.FileDescriptorSet
	if err := proto.Unmarshal(descriptorBytes, &embedded); err != nil {
		t.Fatal(err)
	}
	generated := protodesc.ToFileDescriptorProto(pb.File_jito_v1_jito_proto)
	for _, file := range embedded.File {
		if file.GetName() == generated.GetName() {
			file.SourceCodeInfo = nil
			if !proto.Equal(file, generated) {
				t.Fatal("Go bindings were not generated from the embedded descriptor graph")
			}
			return
		}
	}
	t.Fatal("generated provider file absent from embedded descriptor")
}

func TestNumericHelpersRejectMalformedOrInexactValues(t *testing.T) {
	for _, invoke := range []func(){
		func() { requestInteger(structpb.NewStringValue("invalid")) },
		func() { requestInteger(structpb.NewNumberValue(9007199254740992)) },
		func() { requestNumber(structpb.NewStringValue("9007199254740993")) },
		func() { requestNumber(structpb.NewStringValue("18446744073709551615")) },
		func() { requestNumber(structpb.NewStringValue("NaN")) },
		func() { requestNumber(structpb.NewStringValue("+Inf")) },
		func() { providerInteger(json.Number("9223372036854775808")) },
		func() { providerInteger32(json.Number("2147483648")) },
	} {
		func() {
			defer func() {
				if recover() == nil {
					t.Fatal("invalid numeric conversion was accepted")
				}
			}()
			invoke()
		}()
	}
}
