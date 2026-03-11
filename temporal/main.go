package main

import (
	"context"
	"crypto/tls"
	_ "embed"
	"fmt"
	"os"
	"strconv"

	invariant "github.com/jim-technologies/invariantprotocol/go"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
)

//go:embed descriptor.binpb
var descriptorBytes []byte

func main() {
	server, err := invariant.ServerFromBytes(descriptorBytes)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	server.Name = "temporal-mcp"
	server.Version = "0.1.0"

	target := os.Getenv("TEMPORAL_ADDRESS")
	if target == "" {
		target = "localhost:7233"
	}

	dialOpts, err := buildDialOptions()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	conn, err := grpc.NewClient(target, dialOpts...)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	defer conn.Close()

	if err := server.Connect(conn); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	args := os.Args[1:]
	if len(args) > 0 && args[0] == "--cli" {
		os.Args = append([]string{os.Args[0]}, args[1:]...)
		if err := server.Serve(invariant.CLI()); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}

	if len(args) > 0 && args[0] == "--http" {
		port := 8080
		if len(args) > 1 {
			if p, err := strconv.Atoi(args[1]); err == nil {
				port = p
			}
		}
		if err := server.Serve(invariant.HTTP(port)); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}

	if len(args) > 0 && args[0] == "--grpc" {
		port := 50051
		if len(args) > 1 {
			if p, err := strconv.Atoi(args[1]); err == nil {
				port = p
			}
		}
		if err := server.Serve(invariant.GRPC(port)); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}

	if err := server.Serve(invariant.MCP()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// buildDialOptions returns gRPC dial options based on environment variables.
//
// Local (default):
//
//	TEMPORAL_ADDRESS=localhost:7233 (insecure)
//
// Temporal Cloud with API key:
//
//	TEMPORAL_ADDRESS=<namespace>.<account>.tmprl.cloud:7233
//	TEMPORAL_API_KEY=<key>
//	TEMPORAL_NAMESPACE=<namespace>.<account>
//
// Temporal Cloud with mTLS:
//
//	TEMPORAL_ADDRESS=<namespace>.<account>.tmprl.cloud:7233
//	TEMPORAL_TLS_CERT=/path/to/client.pem
//	TEMPORAL_TLS_KEY=/path/to/client.key
//	TEMPORAL_NAMESPACE=<namespace>.<account>
func buildDialOptions() ([]grpc.DialOption, error) {
	apiKey := os.Getenv("TEMPORAL_API_KEY")
	certPath := os.Getenv("TEMPORAL_TLS_CERT")
	keyPath := os.Getenv("TEMPORAL_TLS_KEY")
	namespace := os.Getenv("TEMPORAL_NAMESPACE")

	switch {
	case apiKey != "":
		// API key auth: TLS + Authorization header + namespace header
		opts := []grpc.DialOption{
			grpc.WithTransportCredentials(credentials.NewTLS(&tls.Config{})),
			grpc.WithUnaryInterceptor(apiKeyInterceptor(apiKey, namespace)),
		}
		return opts, nil

	case certPath != "" && keyPath != "":
		// mTLS auth: client certificate + namespace header
		cert, err := tls.LoadX509KeyPair(certPath, keyPath)
		if err != nil {
			return nil, fmt.Errorf("load TLS cert/key: %w", err)
		}
		tlsConfig := &tls.Config{Certificates: []tls.Certificate{cert}}
		opts := []grpc.DialOption{
			grpc.WithTransportCredentials(credentials.NewTLS(tlsConfig)),
		}
		if namespace != "" {
			opts = append(opts, grpc.WithUnaryInterceptor(namespaceInterceptor(namespace)))
		}
		return opts, nil

	default:
		// Local: insecure
		return []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}, nil
	}
}

func apiKeyInterceptor(apiKey, namespace string) grpc.UnaryClientInterceptor {
	return func(ctx context.Context, method string, req, reply any, cc *grpc.ClientConn, invoker grpc.UnaryInvoker, opts ...grpc.CallOption) error {
		ctx = metadata.AppendToOutgoingContext(ctx, "authorization", "Bearer "+apiKey)
		if namespace != "" {
			ctx = metadata.AppendToOutgoingContext(ctx, "temporal-namespace", namespace)
		}
		return invoker(ctx, method, req, reply, cc, opts...)
	}
}

func namespaceInterceptor(namespace string) grpc.UnaryClientInterceptor {
	return func(ctx context.Context, method string, req, reply any, cc *grpc.ClientConn, invoker grpc.UnaryInvoker, opts ...grpc.CallOption) error {
		ctx = metadata.AppendToOutgoingContext(ctx, "temporal-namespace", namespace)
		return invoker(ctx, method, req, reply, cc, opts...)
	}
}
