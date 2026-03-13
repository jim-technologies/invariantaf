package main

import (
	_ "embed"
	"fmt"
	"os"
	"strconv"

	invariant "github.com/jim-technologies/invariantprotocol/go"
)

//go:embed descriptor.binpb
var descriptorBytes []byte

func main() {
	server, err := invariant.ServerFromBytes(descriptorBytes)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	server.Name = "alternativeme-mcp"
	server.Version = "0.1.0"

	if err := server.Register(NewAlternativeMeService()); err != nil {
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
